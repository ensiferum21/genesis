#!/usr/bin/env python3
"""B20_R156 (F3): does the Frontier's allocation beat standard allocators on sealed planted worlds? (DEV,
preregistered; a calibration domain)

    taskset -c 0 python3 scripts/b20r156_frontier_worlds.py evidence/frontier_worlds_b20r156     run ALONE (resumable; slices exit 3)

**Why.** Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md`): Genesis should imagine, mutate,
extrapolate, branch out, see convergence and put its effort behind the best, without handholding. F1 (B20_R160)
built the engine and a planted world whose keys only the kernel holds. On 8 development worlds the engine's
allocation alone reached 0.774 of the reference against UCB1's 0.652 and successive halving's 0.563 (disclosed,
licenses nothing). This study tests that on worlds nothing has seen. It is a calibration of the machinery, like
the Limitation Zoo for ARA: **nothing here is evidence about real problems.**

**Worlds.** Drawn by the kernel (`frontier.world.PlantedWorld`) from three HELD-OUT families, which differ from
development in the number of problems, the noise and the type weights, from the sealed seed SEALED_SEED. There
are 8 worlds per family (24) and 2 null worlds per family (6). Budget 12,000 units, quantum 10, verification 1 unit
per call. Development used 4 problems, noise 0.02, the default weights, budget 8,000 and seeds 1001-1008.

**Arms** (each run once per world, with the world's index as its seed, so arms share their random streams where
they can; all at the same budget, verification included):
  * F:   the Frontier's allocation alone (`allocate.FrontierPolicy`; no abstraction, no branching out);
  * F+:  the Frontier with abstraction and branching out (secondary);
  * the comparators, from the same engine: successive halving across directions (`HalvingPolicy`, as
    `autonomy.portfolio`'s G2), UCB1 on current levels (`UCBPolicy`), uniform (`UniformPolicy`) and random
    (`RandomPolicy`).
The value of a run is its total verified value divided by the world's reference (`PlantedWorld.oracle`: each
initial problem's best planted curve at an equal share of the budget).

**Primary (Holm over three comparators, alpha 0.05).** P1 is F against halving, UCB1 and uniform, each by a
one-sided Wilcoxon signed-rank test over the 24 worlds. Comparator c is BEATEN if p_Holm < 0.05 and the mean
difference is at least MATERIAL (0.02).
**Verdict:** INVALID if validity fails; else FRONTIER_BETTER if all three are beaten; PARTIAL (naming those
beaten) if some are; NOT_SHOWN if none is.

**Secondary (reported, not in the family):**
  * S1: F+ against F, two-sided: do abstraction and branching out add value here?
  * S2: calibration of F's forecasts. Every forecast F used, made once at least a quarter of its horizon had been
    observed, is checked against the hidden curve at that horizon: the coverage of the 90% intervals, with a
    Wilson interval;
  * S3: recombination veins: the share of planted pairs that F, and UCB1, ever opened;
  * S4: F against random; per-family means of every arm.
**Validity:**
  * in every null world, every arm's total is exactly 0;
  * every run spent its budget to within one quantum plus one verification;
  * the pinned digests of the engine's modules are the ones at preregistration.

**Expectation, stated before running (moderate confidence).** P1: halving and uniform BEATEN; UCB1 beaten or close
(the engine led UCB1 in 7 of 8 development worlds, by 0.12 on average). Verdict FRONTIER_BETTER or PARTIAL (halving,
uniform). S1: F+ above F (the worlds reward abstraction and successors). S2: coverage near or above 0.9. S3: F
opens more planted pairs than UCB1.

**Development looks (disclosed).** The development look of B20_R160 (worlds 1001-1008 of the default family) shaped
the policy. No world of the held-out families was generated before preregistration. The test suite generates
other worlds (seeds 3001-3006, 7, 11, 31, 41, 51).

**Amendment (27 Oct 2026, 21:35 SGT, before it ran; disclosed).** As preregistered (`5c3e236`, sha256
e0ed7ae7...82f7), the engine recomputed every branch's forecast whenever its fair-share horizon moved. That is
correct, but too slow for F4's scale. Now the horizon is rounded up to a geometric grid (ratio 1.25) above the
branch's compute, and forecasts are cached per grid step (`allocate.GRID`). The pins below are the new module
digests. The coverage check (S2) reads each forecast's own horizon. The design, the worlds, the arms and the
analysis are unchanged, and no world of the held-out families has been generated.

**Cost.** About 6 arms x 30 worlds x 5-20 s: under 1 h, in slices of 6,600 s. **Status.** DEV; a calibration;
licenses nothing.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r156'
SEALED_SEED = 29427971
BUDGET, QUANTUM = 12000, 10
FAMILIES = {
    'Fa': {'problems': 3, 'sigma': 0.01, 'types': (('dead', 0.40), ('decoy', 0.30), ('vein', 0.15), ('slow', 0.15))},
    'Fb': {'problems': 5, 'sigma': 0.03, 'types': (('dead', 0.50), ('decoy', 0.20), ('vein', 0.15), ('slow', 0.15))},
    'Fc': {'problems': 3, 'sigma': 0.02, 'types': (('dead', 0.35), ('decoy', 0.35), ('vein', 0.20), ('slow', 0.10))},
}
WORLDS_PER_FAMILY, NULLS_PER_FAMILY = 8, 2
ARMS = ('F', 'F+', 'halving', 'ucb', 'uniform', 'random')
PRIMARY = ('halving', 'ucb', 'uniform')
MATERIAL, ALPHA = 0.02, 0.05
SLICE_S, PAUSED = 6600, 3
MODULES = ('direction.py', 'curves.py', 'converge.py', 'allocate.py', 'engine.py', 'manifest.py', 'world.py')
PINNED = {             # `pins()` at the amended preregistration; checked at run time
    'direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'allocate.py': 'd28d0d8bd9a85f38d335f5680ad24a444ed5f5cad5420fa075c8079ccde28177',
    'engine.py': '849b9bfd611c5cbc8899a55e9ec11348741ecdb7e93e47f10d606ff117e84fe3',
    'manifest.py': '75587e359fcb37a9ab97109a79f1ec5d3417e9618d3bc52cc9f9be8a134055e1',
    'world.py': 'afec2f2f31dbca49eff5561b129c72435403725ed222b389a12742c2f6ac8579',
}


def h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12], 16)


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis/frontier' / m).read_bytes()).hexdigest() for m in MODULES}


def worlds():
    """[(world key, family, seed, null)] in a fixed order."""
    out = []
    for fam in FAMILIES:
        for i in range(WORLDS_PER_FAMILY):
            out.append((f'{fam}-{i}', fam, h(STUDY, SEALED_SEED, fam, i), False))
        for i in range(NULLS_PER_FAMILY):
            out.append((f'{fam}-null{i}', fam, h(STUDY, SEALED_SEED, fam, 'null', i), True))
    return out


def make_world(fam, seed, null):
    from genesis.frontier.world import PlantedWorld
    spec = FAMILIES[fam]
    return PlantedWorld(seed, problems=spec['problems'], horizon=BUDGET, sigma=spec['sigma'], null=null,
                        types=spec['types'])


def run_one(fam, seed, null, arm, index, budget=BUDGET):
    """One run: its row (value, totals, forecasts checked against the truth, recombination pairs opened)."""
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    w = make_world(fam, seed, null)
    m = Manifest(w, w.verify, budget, quantum=QUANTUM, description={'study': STUDY, 'family': fam})
    full = arm == 'F+'
    policy = 'frontier' if arm in ('F', 'F+') else arm
    e = Frontier(m, policy, seed=index, abstraction=full, branch_out=full)
    e.run()
    s = e.summary()
    ref = w.oracle(budget)
    row = {'arm': arm, 'family': fam, 'seed': seed, 'null': null, 'total': s['total'], 'reference': ref,
           'value': s['total'] / ref if ref > 0 else None, 'spent': s['spent'], 'branches': s['branches'],
           'verify_calls': s['verify_calls'], 'abstracted': s['abstracted'], 'revealed': s['revealed']}
    if policy == 'frontier':
        hits = n = 0
        for (bid, npts, k), fc in sorted(e.policy._fc_cache.items()):
            H = fc['H']
            b = e.branches[bid]
            t_obs = b['ts'][npts - 1] if npts else 0
            if npts >= 4 and H > 0 and t_obs / H >= 0.25 and b['direction']['problem'] in w.problems():
                truth = w.truth(b['direction']['problem'], b['direction'], H)
                n += 1
                hits += fc['lo'] <= truth <= fc['hi']
        row['coverage'] = {'n': n, 'hits': hits}
    keys = w.keys()
    pairs = [(p, k) for p, key in keys.items() for k, v in key.items() if v == 'recomb' and p in w.problems()]
    opened = {(b['direction']['problem'], f"{b['direction']['representation']}|{b['direction']['method']}")
              for b in e.branches.values()}
    row['recomb'] = {'planted': len(pairs), 'opened': sum(1 for x in pairs if x in opened)}
    return row


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def wilson(hits, n, z=1.959964):
    if n == 0:
        return (0.0, 1.0)
    p = hits / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    r = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (c - r, c + r)


def analyse(rows):
    """rows: {(world key, arm): row}. The primary family, the secondaries, the verdict's inputs."""
    keys = [k for k, fam, s, null in worlds() if not null]
    val = lambda arm: [rows[(k, arm)]['value'] for k in keys]
    F = val('F')
    p1 = {c: wilcoxon([a - b for a, b in zip(F, val(c))], 'greater') for c in PRIMARY}
    ph = holm({c: p1[c]['p'] for c in PRIMARY})
    for c in PRIMARY:
        p1[c]['p_holm'] = ph[c]
        p1[c]['label'] = 'BEATEN' if ph[c] < ALPHA and p1[c]['mean'] >= MATERIAL else 'NOT_BEATEN'
    cov = [rows[(k, a)]['coverage'] for k in keys for a in ('F',)]
    hits, n = sum(c['hits'] for c in cov), sum(c['n'] for c in cov)
    rec = {a: {'planted': sum(rows[(k, a)]['recomb']['planted'] for k in keys),
               'opened': sum(rows[(k, a)]['recomb']['opened'] for k in keys)} for a in ('F', 'ucb')}
    fam_means = {fam: {a: statistics.mean(rows[(k, a)]['value'] for k, f, s, null in worlds()
                                          if f == fam and not null) for a in ARMS} for fam in FAMILIES}
    return {'P1': p1, 'S1': wilcoxon([a - b for a, b in zip(val('F+'), F)], 'two-sided'),
            'S2': {'hits': hits, 'n': n, 'coverage': hits / n if n else None, 'wilson95': wilson(hits, n)},
            'S3': rec, 'S4': {'random': wilcoxon([a - b for a, b in zip(F, val('random'))], 'greater'),
                              'family_means': fam_means},
            'means': {a: statistics.mean(val(a)) for a in ARMS}}


def verdict(valid, res):
    if not valid:
        return 'INVALID', []
    beaten = [c for c in PRIMARY if res['P1'][c]['label'] == 'BEATEN']
    if len(beaten) == len(PRIMARY):
        return 'FRONTIER_BETTER', beaten
    return ('PARTIAL' if beaten else 'NOT_SHOWN'), beaten


def main(argv=None, registered=True, budget=BUDGET, world_list=None):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'frontier_worlds_b20r156').resolve():
        raise SystemExit('the registered output is evidence/frontier_worlds_b20r156')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    rows = {}
    path = out / 'rows.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[(r['world'], r['arm'])] = r
    ws = world_list if world_list is not None else worlds()
    new = 0
    for idx, (key, fam, seed, null) in enumerate(ws):
        for arm in ARMS:
            if (key, arm) in rows:
                continue
            if new and time.monotonic() - t0 > SLICE_S:
                return PAUSED
            r = run_one(fam, seed, null, arm, idx, budget)
            r['world'] = key
            rows[(key, arm)] = r
            with path.open('a') as f:
                f.write(json.dumps(r, sort_keys=True) + '\n')
            new += 1
    nulls_ok = all(rows[(k, a)]['total'] == 0.0 for k, fam, s, null in ws if null for a in ARMS)
    spent_ok = all(r['spent'] >= budget - QUANTUM - 1 for r in rows.values())
    pins_ok = (not registered) or pins() == PINNED
    valid = nulls_ok and spent_ok and pins_ok
    res = analyse(rows) if world_list is None else None
    v, beaten = verdict(valid, res) if res else ('INVALID' if not valid else 'DESIGN_TEST', [])
    summary = {'study': STUDY, 'schema': 'genesis-b20r156-frontier-worlds-v1', 'verdict': v, 'beaten': beaten,
               'valid': valid, 'nulls_ok': nulls_ok, 'spent_ok': spent_ok, 'pins_ok': pins_ok, 'results': res,
               'worlds': [list(x) for x in ws], 'budget': budget, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV; a calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('worlds', 'results')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
