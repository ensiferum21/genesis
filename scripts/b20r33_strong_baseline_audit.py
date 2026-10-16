#!/usr/bin/env python3
"""B20_R33: strong-baseline audit of the E1 and E1b candidates with an exact MIP arm (DEV; GV3 path).

    b20r33_strong_baseline_audit.py OUT_DIR            run (resumable) and analyse
    b20r33_strong_baseline_audit.py OUT_DIR --summary  analyse existing rows only

GV3 asks that a discovery help "beyond strong baselines". E1 and E1b compare their frozen
candidates only with time-matched fixed DSL programs. After the fact, B20_R32 found that an
off-the-shelf exact MILP solver (HiGHS through the pinned scipy) solved and proved each of the
21 hardest `e1b` hosts tried within 0.72 s wall (B20R32-OPEN-2). This step measures, on fresh
hosts, a MIP arm at each candidate's own budget. It changes no package and no comparator. The
reviewer decides what follows. Everything below is fixed before running.

**Hosts.** 60 fresh DEV hosts, drawn round-robin from the adopted `e1b` calibration's three
selected settings, which are also E1's study `e1-v2` (calibration.calibrated_panel). Generator
seed 20263301. They exclude every identity b20r24_repilots.exposure excludes: every graph host
named under evidence/ and handoff/ (B20_R30–R32 included), the regenerated E1 hosts, and the
calibration hosts.

**Process.** The whole study runs on one CPU core: os.sched_setaffinity is set before any
library is imported, and the study checks it. A multithreaded solver therefore gains nothing from
extra cores. Child processes and containers inherit the affinity.

**Arms.** Per host, seed = digest({'pilot': 'b20r33', 'task': id})[:12]:
  * The frozen packages' own descriptors, unchanged, run by candidates.run(isolation='runc').
    Each is checked with candidates.descriptor_problems first; a descriptor that does not
    rebuild stops the study.
      e1:   the candidate `handoff/e1/candidate_descriptor.json` (represent-and-repair cross_2,
            0.5 CPU s) and the three time-matched baselines (0.5 CPU s each);
      e1b:  the candidate `handoff/e1b/candidate_descriptor.json` (construct-pipeline lp_greedy,
            2.0 CPU s) and the three time-matched baselines (2.0 CPU s each).
    A failed run scores 0.
  * mip_<budget>, for budgets 0.5 s (against E1) and 2.0 s (against E1b). This is
    `scipy.optimize.milp` (HiGHS) on max Σ x_e s.t. x(T) ≤ 2 for every host triangle T,
    x ∈ {0,1}, with time_limit = budget, run in this process on the one core. It returns the
    best incumbent at the limit, and the domain checker re-checks it. Its CPU is measured
    (discovery.construct.Budget, threads included), and a run over 1.25 × budget scores 0. The
    MIP also needs the triangle list, built before the solve and counted in its CPU.

**Reference.** discovery.obstruction.certify (the evaluator's joint LP/SAT certification), seeded
with the best witness of any arm, at 600 s. Hosts without a certified optimum are reported; the
value contrasts do not need the optimum.

**Analysis, per study s ∈ {e1, e1b}.**
  * best_baseline: the per-host maximum of the three baselines, an upper envelope of the
    custodian's SELECT comparator.
  * Contrasts are paired per-host differences, with the mean stratified by setting and a
    bootstrap of 4000 resamples (seed 20263399), 90% interval:
    mip − candidate, candidate − best_baseline, mip − best_baseline.
  * The share of certified hosts at the optimum, per arm.

**Verdict per study (fixed here)**, from D = mip − candidate:
  MIP_DOMINATES            mean D ≥ 0.5 and the interval's lower bound > 0
  MIP_WORSE                mean D ≤ −0.5 and the interval's upper bound < 0
  NO_MATERIAL_DIFFERENCE   otherwise

Development look before preregistration: the builder ran this code path, with the reference at
60 s, on two B20_R32 hosts, which are excluded here. On both, the MIP reached the certified
optimum in under 0.04 CPU s at either budget. The E1 candidate was at the optimum on one host and
2 below it on the other; the E1b candidate was at the optimum on both. The design was not changed
after this look.

A DEV audit. It licenses no claim and changes no package. MIP_DOMINATES would mean that a GV3
"beyond strong baselines" reading of E1 or E1b needs an exact-solver comparator or harder families.
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

from genesis import calibration as CAL  # noqa: E402
from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.discovery.construct import Budget  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402

TF = RD.TF
STUDY, HOSTS, SEED = 'e1b', 60, 20263301
REFERENCE_S = 600
BOOT, BOOT_SEED = 4000, 20263399
OVERRUN = 1.25
STUDIES = {'e1': 0.5, 'e1b': 2.0}


def pinned_core():
    cores = os.sched_getaffinity(0)
    if len(cores) != 1:
        raise RuntimeError(f'the study must run on one core, not {sorted(cores)}')
    return min(cores)


def frozen_arms():
    from genesis import candidates as C
    arms = {}
    for s in STUDIES:
        d = ROOT / 'handoff' / s
        cand = json.loads((d / 'candidate_descriptor.json').read_text())
        base = json.loads((d / 'time_matched_baselines.json').read_text())
        for name, desc in [('candidate', cand)] + sorted(base.items()):
            problems = C.descriptor_problems(desc)
            if problems:
                raise RuntimeError(f'frozen {s} descriptor {name} does not rebuild: {problems}')
            arms[f'{s}:{name}'] = desc
    return arms


def hosts(log):
    excluded, scan, _ = R24.exposure(log)
    record = CAL.load(TF, ROOT, study=STUDY)
    tasks, _ = CAL.calibrated_panel(record, SEED, HOSTS, 'DEV', excluded=excluded)
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    return tasks, scan, record


def mip(task, seconds):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    b = Budget(seconds)
    w0 = time.monotonic()
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    T = O.triangles(task)
    A = lil_matrix((max(1, len(T)), len(E)))
    for j, t in enumerate(T):
        for e in t:
            A[j, idx[e]] = 1
    left = max(0.05, seconds - b.used())
    res = milp(-np.ones(len(E)), constraints=LinearConstraint(A.tocsr(), -np.inf, 2), integrality=np.ones(len(E)),
               bounds=Bounds(0, 1), options={'time_limit': left})
    cpu, wall = b.used(), time.monotonic() - w0
    sel = [E[i] for i in range(len(E)) if res.x is not None and res.x[i] > 0.5]
    value = check_witness(task, sel)['value'] if res.x is not None else 0
    over = cpu > OVERRUN * seconds
    return {'value': 0 if over else value, 'raw_value': value, 'selected': sel, 'cpu_s': round(cpu, 3),
            'wall_s': round(wall, 3), 'status': int(res.status), 'overrun': over,
            'proved_optimal': int(res.status) == 0}


def run_host(task, arms):
    from genesis import candidates as C
    seed = int(digest({'pilot': 'b20r33', 'task': task.task_id})[:12], 16)
    res, best = {}, None
    for name, desc in arms.items():
        r = C.run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
        ok = r['status'] == 'SUCCESS'
        res[name] = {'value': r['result']['value'] if ok else 0, 'status': r['status'],
                     'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0}
        if ok and (best is None or r['result']['value'] > best[0]):
            best = (r['result']['value'], [tuple(e) for e in r['result']['selected']], name)
    for s, seconds in STUDIES.items():
        m = mip(task, seconds)
        res[f'{s}:mip'] = {k: m[k] for k in ('value', 'raw_value', 'cpu_s', 'wall_s', 'status', 'overrun',
                                             'proved_optimal')}
        if m['value'] and (best is None or m['value'] > best[0]):
            best = (m['value'], m['selected'], f'{s}:mip')
    rec = O.certify(task, best[1] if best else [], seconds=REFERENCE_S)
    return {'task_id': task.task_id, 'stratum': task.family, 'edges': len(task.edges), 'arms': res,
            'reference': {'seeded_from': best and best[2], 'lower': rec['lower'], 'upper': rec['upper'],
                          'method': rec['upper_evidence']['method'], 'wall_s': rec['wall_s']},
            'optimum': rec['lower'] if rec['lower'] == rec['upper'] else None}


def run(out, tasks, arms, log):
    path = out / 'rows.jsonl'
    done = set()
    if path.exists():
        done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()}
    t0 = time.monotonic()
    with path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            r = run_host(t, arms)
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            v = {k: a['value'] for k, a in r['arms'].items()}
            log(f'{t.task_id}: opt {r["optimum"]} {v} [{time.monotonic() - t0:.0f}s]')


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
            'by_stratum': {k: round(statistics.fmean(v), 4) for k, v in sorted(by.items())},
            'wins_ties_losses': [sum(d > 0 for d in flat), sum(d == 0 for d in flat), sum(d < 0 for d in flat)]}


def analyse(out, tasks, scan, record, arms):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    studies = {}
    for s in STUDIES:
        base = [k for k in arms if k.startswith(f'{s}:') and k != f'{s}:candidate']
        bb = lambda r: max(r['arms'][k]['value'] for k in base)
        cand = lambda r: r['arms'][f'{s}:candidate']['value']
        mp = lambda r: r['arms'][f'{s}:mip']['value']
        d = contrast(rows, lambda r: mp(r) - cand(r))
        verdict = ('MIP_DOMINATES' if d['mean'] >= 0.5 and d['interval_90'][0] > 0 else
                   'MIP_WORSE' if d['mean'] <= -0.5 and d['interval_90'][1] < 0 else 'NO_MATERIAL_DIFFERENCE')
        scored = [r for r in rows if r['optimum'] is not None]
        at_opt = {name: sum(f(r) == r['optimum'] for r in scored) for name, f in
                  (('candidate', cand), ('best_baseline', bb), ('mip', mp))}
        studies[s] = {'budget_s': STUDIES[s], 'mip_minus_candidate': d,
                      'candidate_minus_best_baseline': contrast(rows, lambda r: cand(r) - bb(r)),
                      'mip_minus_best_baseline': contrast(rows, lambda r: mp(r) - bb(r)),
                      'at_certified_optimum': dict(at_opt, of=len(scored)),
                      'mip_proved_optimal': sum(r['arms'][f'{s}:mip']['proved_optimal'] for r in rows),
                      'mip_overruns': sum(r['arms'][f'{s}:mip']['overrun'] for r in rows),
                      'mip_cpu_s_max': max(r['arms'][f'{s}:mip']['cpu_s'] for r in rows),
                      'failed_runs': {k: sum(r['arms'][k]['status'] != 'SUCCESS' for r in rows)
                                      for k in arms if k.startswith(f'{s}:')},
                      'verdict': verdict}
    summary = {'schema': 'genesis-b20r33-strong-baseline-audit-v1', 'study_hosts': STUDY, 'seed': SEED,
               'descriptors': {k: v['descriptor_id'] for k, v in arms.items()},
               'calibration': {'record_sha256': digest(record), 'selected': record['selected']},
               'certified_hosts': sum(r['optimum'] is not None for r in rows), 'hosts': len(rows),
               'studies': studies, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV audit; licenses no claim; changes no package or comparator'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    arms = frozen_arms()
    tasks, scan, record = hosts(log)
    R11.dump(out / 'hosts.json', {'study': STUDY, 'seed': SEED, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    if '--summary' not in argv:
        run(out, tasks, arms, log)
    s = analyse(out, tasks, scan, record, arms)
    log('verdicts ' + json.dumps({k: (v['verdict'], v['mip_minus_candidate']['mean'],
                                      v['mip_minus_candidate']['interval_90']) for k, v in s['studies'].items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
