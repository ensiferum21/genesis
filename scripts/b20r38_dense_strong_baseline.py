#!/usr/bin/env python3
"""B20_R38: are the frozen E1 and E1b candidates beyond an exact MIP solver in the dense regime?
(DEV; GV3 path, B20R33-OPEN-1)

    b20r38_dense_strong_baseline.py OUT_DIR            run (resumable) and analyse

**Why.** On the decided `e1b` family, an exact MIP (HiGHS) proves every optimum within 0.36 CPU s.
There it dominates E1's frozen candidate and is never below E1b's (B20_R33). B20_R34 and B20_R36
found, exploratorily, a dense planted regime where:
  * the MIP at 2 s proves nothing;
  * E1's representation `cross_2` reached the certified optimum on all 10 certified hosts;
  * the MIP was 13.9 below it there.
This step tests that observation prospectively with the packages' own frozen descriptors. It
changes no package, comparator or rule. Everything below is fixed before running.

**Hosts.** 20 fresh DEV hosts per setting, generator seeds 20263801 and 20263811:
  * planted_cluster n40 p_in 0.8 p_out 0.06, the regime of the observation;
  * erdos n30 p0.42, the other B20_R35 setting.
They exclude every identity b20r24_repilots.exposure excludes, and are reloaded on resume.

**Process.** One pinned core, set before any library is imported (as in B20_R33).

**Arms.** As B20_R33:
  * the frozen `handoff/e1` candidate and baselines at 0.5 CPU s, and the frozen `handoff/e1b`
    candidate and baselines at 2.0 CPU s, all in runc, each descriptor checked first;
  * the exact MIP arm `b20r33_strong_baseline_audit.mip` at 0.5 s and at 2.0 s.
Seeds are digest({'pilot': 'b20r38', 'task': id}).

**Reference (descriptive).** B20_R37's generator-v2 certification route at 60 s, with B20_R37's v2
limits, seeded with the best arm witness. It gives distances to a certified optimum where one
exists. The contrasts do not need it.

**Analysis.** Per study s ∈ {e1, e1b} and per setting, D = candidate − mip. The mean is
bootstrapped (4000 resamples, seed 20263899) with a 90% interval. Candidate − best baseline is
also reported.

**Verdict per study and setting (fixed here):**
  CANDIDATE_BEYOND_MIP     mean D ≥ 0.5 and the interval's lower bound > 0
  MIP_DOMINATES            mean D ≤ −0.5 and the interval's upper bound < 0
  NO_MATERIAL_DIFFERENCE   otherwise
These are four descriptive DEV verdicts, with no multiplicity correction. A positive verdict would
mean that a regime exists where a frozen candidate is beyond a strong baseline. Using that regime
for a real run still needs a certifiable calibration: the evaluator's reference would have to
certify it, which is B20R35-OPEN-1, a trust-path decision.

**Development look before preregistration.** The builder ran this code path once on a B20_R37
planted host (excluded here), with the reference at 30 s. The values were: E1 candidate 124, MIP
at 0.5 s 33, E1b candidate 116, MIP at 2.0 s 124, and a certified optimum of 124. The design was
not changed after this look.

A DEV audit. It licenses no claim.
"""
import os

if __name__ == '__main__':                      # pin before any library starts a thread
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

import json  # noqa: E402
from pathlib import Path  # noqa: E402
import random  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_certify as GC  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402

TF = RD.TF
SETTINGS = [('planted_cluster', {'n': 40, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 30, 'p': 0.42})]
PER, SEEDS = 20, (20263801, 20263811)
REFERENCE_S = 60
BOOT, BOOT_SEED = 4000, 20263899
STUDIES = R33.STUDIES
R37_PACKAGE = ROOT / 'evidence' / 'generator_v2_b20r37' / 'package.json'


def hosts(out, log):
    path = out / 'hosts.json'
    excluded, scan, _ = R24.exposure(log)
    if path.exists():
        log('resume: hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']], scan
    seen, tasks = set(excluded), []
    for seed, (family, params) in zip(SEEDS, SETTINGS):
        ts, seen, _ = ADAPTERS[TF].generate(seed, PER, 'DEV', family, params, excluded=seen)
        tasks += ts
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    R11.dump(path, {'seeds': list(SEEDS), 'settings': [{'family': f, 'params': p} for f, p in SETTINGS],
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks, scan


def run_host(task, arms, registry):
    from genesis import candidates as C
    seed = int(digest({'pilot': 'b20r38', 'task': task.task_id})[:12], 16)
    res, best = {}, None
    for name, desc in arms.items():
        r = C.run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
        ok = r['status'] == 'SUCCESS'
        res[name] = {'value': r['result']['value'] if ok else 0, 'status': r['status']}
        if ok and (best is None or r['result']['value'] > best[0]):
            best = (r['result']['value'], [tuple(e) for e in r['result']['selected']], name)
    for s, seconds in STUDIES.items():
        m = R33.mip(task, seconds)
        res[f'{s}:mip'] = {k: m[k] for k in ('value', 'raw_value', 'cpu_s', 'wall_s', 'status', 'overrun',
                                             'proved_optimal')}
        if m['value'] and (best is None or m['value'] > best[0]):
            best = (m['value'], m['selected'], f'{s}:mip')
    rec = GC.certify_with_rows(task, best[1] if best else [], registry, seconds=REFERENCE_S, **R37.V2)
    return {'task_id': task.task_id, 'stratum': task.family, 'edges': len(task.edges), 'arms': res,
            'reference': {'seeded_from': best and best[2], 'lower': rec['lower'], 'upper': rec['upper'],
                          'method': rec['method'], 'wall_s': rec['wall_s']},
            'optimum': rec['lower'] if rec['lower'] == rec['upper'] else None}


def boot(by):
    rng = random.Random(BOOT_SEED)
    strata = sorted(by)
    est = statistics.fmean(statistics.fmean(by[s]) for s in strata)
    sims = sorted(statistics.fmean(statistics.fmean(rng.choice(by[s]) for _ in by[s]) for s in strata)
                  for _ in range(BOOT))
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def contrast(rows, f):
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(f(r))
    est, ci = boot(by)
    flat = [d for ds in by.values() for d in ds]
    return {'mean': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
            'wins_ties_losses': [sum(d > 0 for d in flat), sum(d == 0 for d in flat), sum(d < 0 for d in flat)]}


def verdict(c):
    if c['mean'] >= 0.5 and c['interval_90'][0] > 0:
        return 'CANDIDATE_BEYOND_MIP'
    if c['mean'] <= -0.5 and c['interval_90'][1] < 0:
        return 'MIP_DOMINATES'
    return 'NO_MATERIAL_DIFFERENCE'


def analyse(out, tasks, scan, arms, registry):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    result = {}
    for s in STUDIES:
        base = [k for k in arms if k.startswith(f'{s}:') and k != f'{s}:candidate']
        cand = lambda r: r['arms'][f'{s}:candidate']['value']
        mp = lambda r: r['arms'][f'{s}:mip']['value']
        bb = lambda r: max(r['arms'][k]['value'] for k in base)
        for stratum in sorted({r['stratum'] for r in rows}):
            rs = [r for r in rows if r['stratum'] == stratum]
            d = contrast(rs, lambda r: cand(r) - mp(r))
            scored = [r for r in rs if r['optimum'] is not None]
            result[f'{s}|{stratum}'] = {
                'budget_s': STUDIES[s], 'candidate_minus_mip': d, 'verdict': verdict(d),
                'candidate_minus_best_baseline': contrast(rs, lambda r: cand(r) - bb(r)),
                'certified_hosts': len(scored),
                'at_certified_optimum': {'candidate': sum(cand(r) == r['optimum'] for r in scored),
                                         'mip': sum(mp(r) == r['optimum'] for r in scored),
                                         'best_baseline': sum(bb(r) == r['optimum'] for r in scored)},
                'mip_proved_optimal': sum(r['arms'][f'{s}:mip']['proved_optimal'] for r in rs),
                'mip_overruns': sum(r['arms'][f'{s}:mip']['overrun'] for r in rs),
                'failed_runs': sum(r['arms'][k]['status'] != 'SUCCESS' for r in rs for k in arms if k.startswith(f'{s}:'))}
    summary = {'schema': 'genesis-b20r38-dense-strong-baseline-v1', 'seeds': list(SEEDS),
               'settings': [{'family': f, 'params': p} for f, p in SETTINGS],
               'descriptors': {k: v['descriptor_id'] for k, v in arms.items()},
               'reference': {'route': 'generator v2 (B20_R37)', 'seconds': REFERENCE_S, 'registry_sha256': digest(registry)},
               'results': result, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV audit; licenses no claim; changes no package, comparator or rule'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    arms = R33.frozen_arms()
    registry = R37.registry_v2(json.loads(R37_PACKAGE.read_text()))
    tasks, scan = hosts(out, log)
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            r = run_host(t, arms, registry)
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id}: opt {r["optimum"]} ' + json.dumps({k: a['value'] for k, a in r['arms'].items()}))
    s = analyse(out, tasks, scan, arms, registry)
    log('verdicts ' + json.dumps({k: (v['verdict'], v['candidate_minus_mip']['mean'], v['candidate_minus_mip']['interval_90'])
                                  for k, v in s['results'].items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
