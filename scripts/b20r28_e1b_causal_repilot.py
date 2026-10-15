#!/usr/bin/env python3
"""B20_R28: E1b causal re-pilot on the e1b family (DEV). Is the LP signal the active ingredient?

    b20r28_e1b_causal_repilot.py OUT_DIR            run (resumable) and summarise
    b20r28_e1b_causal_repilot.py OUT_DIR --summary  summarise existing rows only

B20_R23 piloted the registered causal follow-ups of the E1b candidate, construct-pipeline-v1 with an
lp_greedy initialiser, on builder-chosen settings:
  * ablation: init random_greedy;
  * placebo: init lp_shuffled_greedy.
B20_R24 then moved E1b to the e1b family, the settings the versioned rule e1-hard-v2 selected for
study 'e1b'. NEXT_ACTIONS item 2 asks for the causal follow-ups to be re-piloted on that family.
This script does that.

Everything below is fixed before running.

Study and domain: 'e1b', triangle_free_host_v1. C4 has no adopted e1b calibration (B20_R24:
NO_ELIGIBLE_SETTING) and is NOT_RUN.

Hosts: 30 fresh DEV hosts, drawn round-robin from the adopted e1b calibration's selected settings
(calibration.calibrated_panel), generator seed 20262951. They exclude:
  * the exposure identities of every graph host named in any JSON or JSONL file under evidence/
    and handoff/ (the B20_R24 pilots and rehearsals, and B20_R26/R27 if present);
  * the regenerated E1 hosts (b20r12_e1_redo.exposure);
  * the e1-hard-v1 and e1-hard-v2 calibration hosts, regenerated and checked against their digests
    (b20r24_repilots.exposure).

Arms: all through candidates.run(isolation='runc') with the E1b profile {cpu 4 s, 2048 MiB,
wall 20 s, 1000 queries}, and per-host seed digest({'pilot': 'b20r28', 'task': id})[:12]:
  * candidate: construct-pipeline-v1 {init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0, seed 0};
  * ablation: the registered ablation (init random_greedy);
  * placebo: the registered placebo (init lp_shuffled_greedy).
Both intervened descriptors are checked with replay_contracts.intervention_problems before any run.
A failed run scores 0.

Reference: discovery.obstruction.certify (joint LP/SAT), seeded with the best arm witness, with
120 s per host. A host has an optimum only if lower == upper. The domain is scored only if every
stratum (calibration setting) has at least 75% of its hosts certified, rounded up; otherwise it
is UNSETTLED_REFERENCE.

Analysis per contrast (candidate vs ablation; candidate vs placebo), as in B20_R23/R24:
  * the B19 DRAFT plan core, with the multiplicity family_id naming the domain;
  * kernel.analysis.analyze as a dry run;
  * power.required_sample(..., sims=1000, min_tasks_per_stratum=10, headroom='centred').
Verdict per contrast (mean = mean paired difference over scored hosts, strata pooled):
  UNSETTLED_REFERENCE  a stratum has fewer than 75% certified hosts
  EFFECT_BELOW_MUE     mean < 0.5 (the intervention does not remove a useful part of the effect)
  COST_RULE_FAILS      cgroup CPU ratio candidate / intervened arm > 3.0
  UNDERPOWERED         the centred power model chooses no size in its grid
  READY_FOR_REVIEW     otherwise
A DEV diagnostic. It licenses no claim, and a causal level needs signed custodian evaluations.
"""
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis.common import code_identity, digest  # noqa: E402
from genesis.kernel import replay_contracts as RC  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_causal_readiness as R23C  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402

TF = RD.TF
STUDY, HOSTS, SEED = 'e1b', 30, 20262951
CONTRASTS = R23C.CONTRASTS


def hosts(log):
    excluded, scan, _ = R24.exposure(log)
    record = CAL.load(TF, ROOT, study=STUDY)
    tasks, _ = CAL.calibrated_panel(record, SEED, HOSTS, 'DEV', excluded=excluded)
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    return tasks, scan, record


def run_host(task, all_arms):
    """B20_R23's host routine with this pilot's seed tag."""
    seed = int(digest({'pilot': 'b20r28', 'task': task.task_id})[:12], 16)
    from genesis import candidates as C
    res, best = {}, None
    for name, desc in all_arms.items():
        r = C.run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
        ok = r['status'] == 'SUCCESS'
        res[name] = {'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED',
                     'status': r['status'], 'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0,
                     'meter': r.get('meter'), 'isolation': r.get('isolation')}
        if ok and (best is None or r['result']['value'] > best[0]):
            best = (r['result']['value'], [tuple(e) for e in r['result']['selected']], name)
    from genesis.discovery import obstruction as O
    rec = O.certify(task, best[1] if best else [], seconds=RD.CERTIFY_S)
    cert = {'seeded_from': best and best[2], 'seed_value': best and best[0], 'lower': rec['lower'],
            'upper': rec['upper'], 'upper_method': rec['upper_evidence']['method'], 'status': rec['status'],
            'wall_s': rec['wall_s']}
    return {'task_id': task.task_id, 'stratum': task.family, 'split': task.split, 'arms': res, 'certify': cert,
            'optimum': rec['lower'] if rec['lower'] == rec['upper'] else None}


def run(out, tasks, log):
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        done = {json.loads(line)['task_id'] for line in rows_path.read_text().splitlines() if line.strip()}
    all_arms = R23C.arms(TF)
    t0 = time.monotonic()
    with rows_path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            r = run_host(t, all_arms)
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id}: opt {r["optimum"]} (L{r["certify"]["lower"]}/U{r["certify"]["upper"]} '
                f'{r["certify"]["wall_s"]:.0f}s) ' + ', '.join(f'{n} {a["value"]}' for n, a in r['arms'].items())
                + f' [{time.monotonic() - t0:.0f}s]')


def certified_by_stratum(rows):
    strata = sorted({r['stratum'] for r in rows})
    return {s: [sum(r['optimum'] is not None for r in rows if r['stratum'] == s), sum(r['stratum'] == s for r in rows)]
            for s in strata}


def analyse(out, tasks, scan, record):
    rows = [json.loads(line) for line in (out / 'rows.jsonl').read_text().splitlines() if line.strip()]
    want = {t.task_id for t in tasks}
    if {r['task_id'] for r in rows} != want:
        raise RuntimeError(f'{len(want - {r["task_id"] for r in rows})} hosts not yet run')
    cert = certified_by_stratum(rows)
    unsettled = any(c < math.ceil(0.75 * n) for c, n in cert.values())
    # B20_R23's contrast() gates on a per-setting minimum count; here the gate is 75% per stratum,
    # applied above, so contrast() is given a passing count when this gate passes.
    gate = {s: (R23C.MIN_CERTIFIED if not unsettled else 0) for s in cert}
    scored = [r for r in rows if r['optimum'] is not None]
    d = {'hosts': len(rows), 'certified_by_stratum': cert, 'scored': len(scored),
         'totals': {n: sum(r['arms'][n]['value'] for r in rows) for n in ('candidate', *CONTRASTS)},
         'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in scored) for n in ('candidate', *CONTRASTS)}}
    for other in CONTRASTS:
        c, prow, power = R23C.contrast(TF, rows, other, gate)
        d[other] = c
        if prow is not None:
            R11.dump(out / f'pilot_rows_{other}.json', prow)
            R11.dump(out / f'power_analysis_centred_{other}.json', power)
    if scored:
        d['placebo_minus_ablation_mean'] = round(statistics.fmean(
            r['arms']['placebo']['value'] - r['arms']['ablation']['value'] for r in scored), 4)
    summary = {'schema': 'genesis-b20r28-e1b-causal-repilot-v1', 'study': STUDY, 'domain': TF,
               'c4': {'verdict': 'NOT_RUN', 'reason': 'no adopted e1b calibration for c4_host_v2 (B20_R24)'},
               'calibration': {'record_sha256': digest(record), 'rule': record['rule']['name'],
                               'selected': record['selected']},
               'seed': SEED, 'exposure_scan': scan, 'profile': RD.PROFILE, 'certify_seconds': RD.CERTIFY_S,
               'certified_gate': '75% per stratum, rounded up',
               'descriptors': {n: a['descriptor_id'] for n, a in R23C.arms(TF).items()},
               'triangle_free': d, 'verdicts': {k: d[k]['verdict'] for k in CONTRASTS},
               'r23_builder_settings_pilot': 'evidence/e1b_causal_readiness_b20r23 (kept; builder-chosen settings)',
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV causal readiness diagnostic; no sealed task; licenses no claim'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    tasks, scan, record = hosts(log)
    R11.dump(out / 'hosts.json', {'study': STUDY, 'seed': SEED, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    for kind in CONTRASTS:                                  # the registered interventions, checked before any run
        arms = R23C.arms(TF)
        why, path = RC.intervention_problems(kind, arms['candidate'], arms[kind])
        if why or path != ('init',):
            raise RuntimeError(f'{kind} is not the registered intervention: {why}')
    if '--summary' not in argv:
        run(out, tasks, log)
    s = analyse(out, tasks, scan, record)
    x = s['triangle_free']
    log(f'verdicts {s["verdicts"]}; certified {x["certified_by_stratum"]}; ' + '; '.join(
        f'{k}: mean {x[k].get("mean_difference")} W/T/L {x[k].get("wins_ties_losses")} power '
        f'{(x[k].get("power_centred") or {}).get("status")} {(x[k].get("power_centred") or {}).get("chosen")}'
        for k in CONTRASTS) + f'; placebo-ablation {x.get("placebo_minus_ablation_mean")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
