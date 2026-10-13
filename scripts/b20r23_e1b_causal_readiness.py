#!/usr/bin/env python3
"""B20_R23: E1b causal readiness (DEV). Is the LP signal the active ingredient of the E1b candidate?

    b20r23_e1b_causal_readiness.py OUT_DIR            run (resumable) and summarise
    b20r23_e1b_causal_readiness.py OUT_DIR --summary  summarise existing rows only

Why. A better-solver claim reaches the causal levels (ABLATION_SUPPORTED, PLACEBO_CONTROLLED) only
through signed ablation and placebo evaluations of registered interventions. B20_R23 registered,
for construct-pipeline-v1, the LP guidance of an lp_greedy initialiser:
  ablation  init random_greedy       no LP ordering, the same stage budget
  placebo   init lp_shuffled_greedy  the same LP solve and restarts, LP values permuted among edges
This DEV pilot asks whether those follow-ups would be ready for review under the same design as the
E1b readiness pilot (scripts/b20r23_e1b_readiness.py). It was written, and its rules fixed, while
that pilot was still running; its outcome does not depend on that pilot's verdicts.

Everything below is fixed before running.

Settings: as in the readiness pilot (C1 triangle-free erdos n30 p0.3, C2 triangle-free erdos n40
p0.2, C3 C4 erdos n30 p0.2). 10 fresh DEV hosts per setting, generator seed 20262501 + 10 i, each
excluding the exposure identities of every graph host recorded in any JSON or JSONL file under
evidence/ and handoff/ (the readiness pilot's hosts included), the E1 exposure set
(b20r12_e1_redo.exposure), and the hosts of earlier settings of this pilot.

Arms, all through candidates.run(isolation='runc'), the readiness pilot's profile {cpu 4 s,
2048 MiB, wall 20 s, 1000 queries}; per-host seed digest({'pilot': 'b20r23-causal', 'task': id})[:12]:
  candidate  construct-pipeline-v1 {init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0, seed 0}
  ablation   the registered ablation of the candidate (init random_greedy)
  placebo    the registered placebo of the candidate (init lp_shuffled_greedy)
Both intervened descriptors are checked with replay_contracts.intervention_problems before any run.
A failed run scores 0.

Reference optimum: discovery.obstruction.certify, seeded with the best arm witness, 120 s per host;
an optimum only if lower == upper. A domain is scored only if each stratum has at least 8 of 10 hosts
certified (75%, rounded up); otherwise UNSETTLED_REFERENCE.

Analysis, per domain and per contrast (candidate vs ablation; candidate vs placebo): the B19 DRAFT
plan core unchanged except the multiplicity family_id, which names the domain (as in the readiness
pilot); kernel.analysis.analyze as a dry run; power.required_sample(..., sims=1000,
min_tasks_per_stratum=10, headroom='centred').

Verdict per domain and contrast (mean = mean paired difference over scored hosts, strata pooled):
  UNSETTLED_REFERENCE  a stratum has fewer than 8 certified hosts
  EFFECT_BELOW_MUE     mean < 0.5 (the intervention does not remove a useful part of the effect)
  COST_RULE_FAILS      cgroup CPU ratio candidate / intervened arm > 3.0
  UNDERPOWERED         the centred power model chooses no size in its grid
  READY_FOR_REVIEW     otherwise
A DEV diagnostic: it licenses no claim, and a causal level needs signed custodian evaluations.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C  # noqa: E402
from genesis.common import code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.kernel import replay_contracts as RC  # noqa: E402
from genesis.kernel.analysis import analyze  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r12_e1_redo as R12  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402

TF, C4 = RD.TF, RD.C4
SETTINGS = RD.SETTINGS
HOSTS, SEED_BASE = 10, 20262501
PROFILE, CERTIFY_S = RD.PROFILE, RD.CERTIFY_S
MIN_CERTIFIED = 8
CANDIDATE = RD.CANDIDATE
CONTRASTS = ('ablation', 'placebo')


def arms(domain):
    cand = C.build_descriptor('construct-pipeline-v1', domain, CANDIDATE, **PROFILE)
    out = {'candidate': cand}
    for kind, init in (('ablation', 'random_greedy'), ('placebo', 'lp_shuffled_greedy')):
        d = C.build_descriptor('construct-pipeline-v1', domain, dict(CANDIDATE, init=init), **PROFILE)
        why, path = RC.intervention_problems(kind, cand, d)
        if why or path != ('init',):
            raise RuntimeError(f'{kind} is not the registered intervention: {why}')
        out[kind] = d
    return out


def hosts(log):
    named, scan = RD.named_hosts()
    e1_excluded, e1_named = R12.exposure(CAL.load(TF, ROOT, study='e1'))
    excluded = RD.identities(named) | set(e1_excluded)
    readiness = json.loads((ROOT / 'evidence/e1b_readiness_b20r23/hosts.json').read_text())
    n_ready = sum(len(s['tasks']) for s in readiness.values())
    scan.update(e1_named_hosts=len(e1_named), excluded_identities=len(excluded), readiness_pilot_hosts=n_ready)
    log(f'exposure: {scan["distinct_hosts"]} hosts named in {scan["files_scanned"]} files (the readiness pilot\'s '
        f'{n_ready} included), {len(e1_named)} E1 hosts regenerated; {len(excluded)} identities excluded')
    out = {}
    for i, (sid, domain, family, params) in enumerate(SETTINGS):
        tasks, seen, gen = ADAPTERS[domain].generate(SEED_BASE + 10 * i, HOSTS, 'DEV', family, params,
                                                     excluded=excluded)
        if RD.identities(tasks) & excluded:
            raise RuntimeError('a generated host collides with a named host')
        excluded = set(seen)
        out[sid] = {'domain': domain, 'family': family, 'params': params, 'seed': SEED_BASE + 10 * i,
                    'generator': gen, 'tasks': tasks}
    return out, scan


def run_host(task, all_arms):
    """As in the readiness pilot, with this pilot's seed tag."""
    seed = int(digest({'pilot': 'b20r23-causal', 'task': task.task_id})[:12], 16)
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
    rec = O.certify(task, best[1], seconds=CERTIFY_S)
    cert = {'seeded_from': best[2], 'seed_value': best[0], 'lower': rec['lower'], 'upper': rec['upper'],
            'upper_method': rec['upper_evidence']['method'], 'status': rec['status'], 'wall_s': rec['wall_s']}
    return {'task_id': task.task_id, 'stratum': task.family, 'split': task.split, 'arms': res, 'certify': cert,
            'optimum': rec['lower'] if rec['lower'] == rec['upper'] else None}


def run(out, H, log):
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        done = {json.loads(line)['task_id'] for line in rows_path.read_text().splitlines() if line.strip()}
    t0 = time.monotonic()
    with rows_path.open('a') as fh:
        for sid, s in H.items():
            all_arms = arms(s['domain'])
            for t in s['tasks']:
                if t.task_id in done:
                    continue
                r = run_host(t, all_arms)
                r.update(setting=sid, domain=s['domain'])
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                log(f'{sid} {t.task_id}: opt {r["optimum"]} (L{r["certify"]["lower"]}/U{r["certify"]["upper"]} '
                    f'{r["certify"]["wall_s"]:.0f}s) ' + ', '.join(f'{n} {a["value"]}' for n, a in r['arms'].items())
                    + f' [{time.monotonic() - t0:.0f}s]')


def contrast(domain, drows, other, certified):
    cpu = {n: sum(r['arms'][n]['cpu_ns'] for r in drows) for n in ('candidate', other)}
    ratio = cpu['candidate'] / cpu[other] if cpu[other] else None
    plan = dict(R11.draft_record()['analysis_plan_core'], decision_record_sha256='0' * 64)
    plan['multiplicity'] = dict(plan['multiplicity'], family_id=f'sealed_evaluation:{domain}')
    mue, max_ratio = plan['minimum_useful_effect'], plan['cost']['max_ratio']
    out = {'cpu_ns': cpu, 'cpu_ratio_candidate_to_intervened': round(ratio, 4) if ratio else None,
           'failures': {n: sum(r['arms'][n]['run'] == 'FAILED' for r in drows) for n in ('candidate', other)}}
    if min(certified.values()) < MIN_CERTIFIED:
        return dict(out, verdict='UNSETTLED_REFERENCE'), None, None
    scored = [r for r in drows if r['optimum'] is not None]
    prow = [{'task_id': r['task_id'], 'stratum': r['stratum'], 'status': 'SCORED', 'split': r['split'],
             'optimum': r['optimum'],
             'candidate': {k: r['arms']['candidate'][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: r['arms'][other][k] for k in ('value', 'run', 'cpu_ns')}} for r in scored]
    result = analyze(prow, plan)
    power = required_sample(prow, plan, sims=1000, min_tasks_per_stratum=10, headroom='centred')
    chosen = (power.get('chosen') or {}).get('tasks_per_stratum')
    diffs = [r['candidate']['value'] - r['baseline']['value'] for r in prow]
    mean = statistics.fmean(diffs)
    verdict = ('EFFECT_BELOW_MUE' if mean < mue else 'COST_RULE_FAILS' if ratio is None or ratio > max_ratio else
               'UNDERPOWERED' if not chosen else 'READY_FOR_REVIEW')
    strata = {}
    for r in prow:
        strata.setdefault(r['stratum'], []).append(r['candidate']['value'] - r['baseline']['value'])
    out.update({'mean_difference': round(mean, 4),
                'stratum_mean_differences': {s: round(statistics.fmean(v), 4) for s, v in sorted(strata.items())},
                'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
                'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value',
                                                                   'checks', 'cost_ratio')},
                'power_centred': {k: power.get(k) for k in ('status', 'chosen', 'power_at_minimum_useful_effect',
                                                             'false_positive_rate_at_zero_effect', 'pilot_strata')},
                'approximation_agreement': (approximation_check(prow, plan, chosen, sims=40, headroom='centred')
                                            if chosen else None),
                'verdict': verdict})
    return out, prow, power


def analyse(out, H, scan):
    rows = [json.loads(line) for line in (out / 'rows.jsonl').read_text().splitlines() if line.strip()]
    want = {t.task_id for s in H.values() for t in s['tasks']}
    if {r['task_id'] for r in rows} != want:
        raise RuntimeError(f'{len(want - {r["task_id"] for r in rows})} hosts not yet run')
    summary = {'schema': 'genesis-b20r23-e1b-causal-readiness-v1', 'domains': {}, 'exposure_scan': scan,
               'profile': PROFILE, 'certify_seconds': CERTIFY_S, 'min_certified_per_stratum': MIN_CERTIFIED,
               'descriptors': {d: {n: a['descriptor_id'] for n, a in arms(d).items()} for d in (TF, C4)},
               'interventions': {k: RC.INTERVENTIONS[('construct-pipeline-v1', ('init',))]['meaning']
                                 for k in ('meaning',)},
               'status': 'DEV causal readiness diagnostic; no sealed task; licenses no claim'}
    for domain in (TF, C4):
        sids = [sid for sid, s in H.items() if s['domain'] == domain]
        drows = [r for r in rows if r['setting'] in sids]
        certified = {sid: sum(r['optimum'] is not None for r in drows if r['setting'] == sid) for sid in sids}
        scored = [r for r in drows if r['optimum'] is not None]
        d = {'hosts': len(drows), 'certified_by_setting': certified, 'scored': len(scored),
             'totals': {n: sum(r['arms'][n]['value'] for r in drows) for n in ('candidate', *CONTRASTS)},
             'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in scored)
                              for n in ('candidate', *CONTRASTS)}}
        for other in CONTRASTS:
            c, prow, power = contrast(domain, drows, other, certified)
            d[other] = c
            if prow is not None:
                R11.dump(out / f'pilot_rows_{domain}_{other}.json', prow)
                R11.dump(out / f'power_analysis_centred_{domain}_{other}.json', power)
        if scored:
            d['placebo_minus_ablation_mean'] = round(statistics.fmean(
                r['arms']['placebo']['value'] - r['arms']['ablation']['value'] for r in scored), 4)
        summary['domains'][domain] = d
    summary['verdicts'] = {f'{d}:{k}': summary['domains'][d][k]['verdict'] for d in (TF, C4) for k in CONTRASTS}
    summary['code_identity'] = code_identity(ROOT)['sha256']
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
    H, scan = hosts(log)
    R11.dump(out / 'hosts.json', {sid: dict({k: v for k, v in s.items() if k != 'tasks'},
                                            tasks=[t.model_dump(mode='json') for t in s['tasks']])
                                  for sid, s in H.items()})
    if '--summary' not in argv:
        run(out, H, log)
    s = analyse(out, H, scan)
    log(f'verdicts {s["verdicts"]}')
    for d, x in s['domains'].items():
        log(f'{d}: certified {x["certified_by_setting"]}; ' + '; '.join(
            f'{k}: mean {x[k].get("mean_difference")} W/T/L {x[k].get("wins_ties_losses")} power '
            f'{(x[k].get("power_centred") or {}).get("status")} {(x[k].get("power_centred") or {}).get("chosen")}'
            for k in CONTRASTS) + f'; placebo-ablation {x.get("placebo_minus_ablation_mean")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
