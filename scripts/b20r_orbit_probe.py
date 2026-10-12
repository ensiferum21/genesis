#!/usr/bin/env python3
"""CRPD-3 (B20_R2): orbit-sensitivity probe of E proof cost. DEV diagnostic, no claim.

    b20r_orbit_probe.py OUT_DIR [--targets 20] [--wolfram-targets 10]

Question. Does E's outcome or cost change across presentations of the same problem that
are equivalent by construction (alpha-renaming, conjunct order, equality orientation)?
If it does more than repeated identical runs do, the prover is presentation-sensitive:
there is room for normalisation or a presentation portfolio, and single-presentation
measurements under-state run-to-run variance (B20-OPEN-3).

Presentations (each preserves the problem syntactically up to renaming/order/symmetry of =;
no theory-dependent transformation such as commutativity is used):
  p0 canonical              p1 goal sides swapped        p2 axioms in reverse order
  p3 goal variables cycled  p4 axiom variables cycled    p5 p1 + p2 + p3 + p4
  r1, r2 identical repeats of p0 (run-to-run noise)
Every attempt is a bounded, metered E run (learning.budget.run_bounded through
eprover.prove_bounded) at a fixed per-attempt limit; outcomes are E's own claims, used
only as a diagnostic (no proof is admitted anywhere).

Decision rule, fixed before running: presentation sensitivity is REPORTED for a system if
the share of targets with mixed outcomes across p0..p5 exceeds the share with mixed
outcomes across p0, r1, r2 by at least 0.10; otherwise NOT_DETECTED. Either way this is
a DEV diagnostic on fresh targets (seeds 401/402, recorded so later studies can exclude them).
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning.budget import NS  # noqa: E402
from genesis.verification.eprover import prove_bounded  # noqa: E402

SETTINGS = {'ba_sheffer': {'seed': 401, 'range': (5, 8), 'max_term': 5, 'limit_s': 1},
            'ba_wolfram': {'seed': 402, 'range': (5, 8), 'max_term': 5, 'limit_s': 3},
            'ba_huntington': {'seed': 403, 'range': (6, 9), 'max_term': 4, 'limit_s': 1}}
PRESENTATIONS = ('p0', 'p1', 'p2', 'p3', 'p4', 'p5')
REPEATS = ('r1', 'r2')
THRESHOLD = 0.10


def rename(f, m):
    if f[0] == 'all':
        return ('all', m.get(f[1], f[1]), rename(f[2], m))
    if f[0] == 'eq':
        return ('eq', rename(f[1], m), rename(f[2], m))
    if f[0] == 'var':
        return ('var', m.get(f[1], f[1]))
    if f[0] == 'fn':
        return ('fn', f[1], tuple(rename(a, m) for a in f[2]))
    raise ValueError(f'unexpected node {f[0]}')


def swap_eq(f):
    if f[0] == 'all':
        return ('all', f[1], swap_eq(f[2]))
    return ('eq', f[2], f[1])


CYCLE_GOAL = {'X': 'Y', 'Y': 'Z', 'Z': 'X'}
CYCLE_AX = {'X': 'Z', 'Y': 'X', 'Z': 'Y'}


def presentation(name, axioms, goal):
    if name in ('p0', 'r1', 'r2'):
        return axioms, goal
    if name == 'p1':
        return axioms, swap_eq(goal)
    if name == 'p2':
        return list(reversed(axioms)), goal
    if name == 'p3':
        return axioms, rename(goal, CYCLE_GOAL)
    if name == 'p4':
        return [rename(a, CYCLE_AX) for a in axioms], goal
    if name == 'p5':
        return [rename(a, CYCLE_AX) for a in reversed(axioms)], rename(swap_eq(goal), CYCLE_GOAL)
    raise ValueError(name)


def attempt(axioms, goal, limit_s):
    r = prove_bounded(axioms, goal, limit_s=limit_s, cpu_ns=limit_s * NS + 250_000_000,
                      wall_ns=(limit_s + 10) * NS)
    res = r['resource']
    return {'status': r['status'], 'proved': r['status'] == 'THEOREM' and bool(r['proof']),
            'cpu_ns': res['cpu_ns'], 'termination': res['termination'], 'meter': res['meter']['kind'],
            'problem_sha256': digest(r['problem'])}


def mixed(outcomes):
    return len(set(outcomes)) > 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--targets', type=int, default=20)
    ap.add_argument('--wolfram-targets', type=int, default=10)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    rows, summary = [], {}
    for system, cfg in SETTINGS.items():
        n = a.wolfram_targets if system == 'ba_wolfram' else a.targets
        lo, hi = cfg['range']
        targets = Q.sample_targets(system, n, min_total=lo, max_total=hi, max_term=cfg['max_term'], seed=cfg['seed'])
        ax = Q.axioms(system)
        for i, t in enumerate(targets):
            goal = Q.closed(t)
            res = {}
            for p in PRESENTATIONS + REPEATS:
                axs, g = presentation(p, ax, goal)
                res[p] = attempt(axs, g, cfg['limit_s'])
            row = {'system': system, 'index': i, 'target': Q.text(t), 'limit_s': cfg['limit_s'], 'runs': res,
                   'mixed_presentations': mixed([res[p]['proved'] for p in PRESENTATIONS]),
                   'mixed_repeats': mixed([res[p]['proved'] for p in ('p0',) + REPEATS])}
            proved_cpu = [res[p]['cpu_ns'] for p in PRESENTATIONS if res[p]['proved']]
            row['cpu_ratio_max_min'] = (round(max(proved_cpu) / max(1, min(proved_cpu)), 3)
                                        if len(proved_cpu) == len(PRESENTATIONS) else None)
            rep_cpu = [res[p]['cpu_ns'] for p in ('p0',) + REPEATS if res[p]['proved']]
            row['repeat_cpu_ratio_max_min'] = (round(max(rep_cpu) / max(1, min(rep_cpu)), 3)
                                               if len(rep_cpu) == 1 + len(REPEATS) else None)
            rows.append(row)
            log(f'{system}[{i}] proved {sum(res[p]["proved"] for p in PRESENTATIONS)}/{len(PRESENTATIONS)} '
                f'presentations, repeats {sum(res[p]["proved"] for p in ("p0",) + REPEATS)}/3')
        mine = [r for r in rows if r['system'] == system]
        mp = sum(r['mixed_presentations'] for r in mine) / len(mine)
        mr = sum(r['mixed_repeats'] for r in mine) / len(mine)
        ratios = [r['cpu_ratio_max_min'] for r in mine if r['cpu_ratio_max_min']]
        rratios = [r['repeat_cpu_ratio_max_min'] for r in mine if r['repeat_cpu_ratio_max_min']]
        per_p = {p: sum(r['runs'][p]['proved'] for r in mine) for p in PRESENTATIONS + REPEATS}
        summary[system] = {
            'targets': len(mine), 'limit_s': cfg['limit_s'], 'proved_by_presentation': per_p,
            'proved_by_some_presentation': sum(any(r['runs'][p]['proved'] for p in PRESENTATIONS) for r in mine),
            'proved_by_all_presentations': sum(all(r['runs'][p]['proved'] for p in PRESENTATIONS) for r in mine),
            'share_mixed_across_presentations': round(mp, 3), 'share_mixed_across_repeats': round(mr, 3),
            'median_cpu_ratio_presentations': round(statistics.median(ratios), 3) if ratios else None,
            'median_cpu_ratio_repeats': round(statistics.median(rratios), 3) if rratios else None,
            'verdict': 'REPORTED' if mp - mr >= THRESHOLD else 'NOT_DETECTED'}
        log(f'{system}: {summary[system]}')
    report = {'schema': 'genesis-orbit-probe-v1', 'decision_rule': f'REPORTED iff mixed(presentations) - '
              f'mixed(repeats) >= {THRESHOLD}', 'presentations': PRESENTATIONS, 'repeats': REPEATS,
              'settings': SETTINGS, 'summary': summary, 'rows': rows,
              'exposure': {s: [r['target'] for r in rows if r['system'] == s] for s in SETTINGS},
              'scope': 'DEV diagnostic of E --auto on fresh targets; E outcomes are prover claims; no proof admitted',
              'wall_s': round(time.monotonic() - t0, 1)}
    (out / 'probe.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
