#!/usr/bin/env python3
"""B20_R163 (F6): does the Frontier, searching its own configurations, find one that beats its defaults on held-out
planted worlds at matched total compute? (DEV, preregistered; a calibration domain)

    taskset -c 0 python3 scripts/b20r163_frontier_meta.py evidence/frontier_meta_b20r163     run ALONE (resumable; slices exit 3)

**Why.** Daniel's directive of 27 Oct 2026, 19:55 asks for a system that "recursively improves its own discovery
processes". The Frontier's design (`docs/OMEGA_FRONTIER.md` §4.8) says how that is bounded: the engine's
configuration is a research object, the same Frontier searches it, and a new configuration is promoted only by the
kernel on held-out worlds, at matched total compute with the meta-search counted. The machinery is built
(`frontier/meta.py`, 28 Oct 2026). This study asks whether it pays here. It is a calibration of the machinery on
planted worlds, like F3: **nothing here is evidence about real problems.**

**Meta-search (on one sealed meta-training world).** The kernel draws one world of family Ma (6 problems) from the
sealed seed SEALED_SEED. `MetaDomain` poses it as the only meta-task. Its approaches are the Frontier's
configurations: the policy 'frontier' with the grid `meta.GRID` (eps, lam_lp, lam_con, k_imagine, patience,
stall; 729 configurations, the defaults among them). Each inner run has the inner budget B_IN (18,000 units,
quantum 10, verification 1 per call). The outer Frontier (its defaults, seed 0) spends META_BUDGET (144,000 inner
units; outer quantum 600). The kernel's meta verifier answers from its own record of what the inner verifier
confirmed. **The promoted configuration** is the configuration of the outer engine's best verified artifact; if
nothing was verified, it is the defaults, and the study says so. **C_meta** is the meta-search's true compute
(`MetaDomain.inner_compute()`: every inner run's spend, each run counted once).

**Evaluation (held out).** 24 worlds from two held-out families, Ha and Hb (12 each), and 6 null worlds (3 each),
from the sealed seed. Families Ma, Ha and Hb differ from development, from the test suite and from F3's. Budget B
is 12,000 units. The arms, each run once per world with the world's index as its seed, all with the full engine
(abstraction and branching out on, as in the meta-search):
  * P:  the promoted configuration, at B;
  * D:  the defaults, at B plus C_meta / 24, rounded down to a quantum: matched total compute, with the
        meta-search's cost spread over the evaluation worlds;
  * D0: the defaults, at B.
The value of a run is its total verified value divided by the world's reference at B (`PlantedWorld.oracle(B)`),
the same reference for every arm.

**Primary.** P1 is P against D, by a one-sided Wilcoxon signed-rank test over the 24 worlds.
**Verdict:**
  * INVALID if validity fails;
  * SELF_IMPROVED if p < 0.05 and the mean difference is at least MATERIAL (0.02);
  * otherwise NOT_SHOWN, with NOTHING_PROMOTED noted if the meta-search verified nothing.
**Secondary (reported, not in the family):**
  * S1: P against D0, two-sided: the configuration's effect at equal per-world budget (CONFIG_BETTER, CONFIG_WORSE
    or TIE, by the same p and material rules);
  * S2: D against D0, one-sided: what the extra budget alone buys;
  * S3: per-family means of every arm;
  * S4: the promoted configuration, how it differs from the defaults, C_meta and the extra budget per world;
  * S5: the meta-search's verified curve and the number of configurations it opened.
**Validity:**
  * in every null world, every arm's total is exactly 0;
  * every run spent its budget to within one quantum plus its last step's verifications (11 units);
  * the promoted configuration lies on the grid;
  * the pinned digests of the engine's modules are the ones at preregistration.

**Expectation, stated before running (moderate confidence).** P1 NOT_SHOWN. D has about 50% more budget per world,
and on planted worlds budget is worth more than a different configuration. S1 TIE or a small CONFIG_BETTER (low
confidence). S2 clearly positive. If SELF_IMPROVED, it would be the first time a configuration found by Genesis's
own meta-search paid for its search at matched total compute, in a calibration domain only.

**Development looks (disclosed).** None of this study's worlds was generated before preregistration. The test suite
generates other worlds (seeds 101, 202, 777xxx). F1's development look (B20_R160) shaped the defaults.

**Cost.** The meta-search is about 12 inner runs' worth, a few minutes. The evaluation is 3 arms x 30 worlds x
5-25 s. Under 1 h, in slices of 6,600 s. **Status.** DEV; a calibration; licenses nothing. Runs after B20_R158.
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

STUDY = 'b20r163'
SEALED_SEED = 41102559
B, QUANTUM = 12000, 10
B_IN, META_BUDGET, META_QUANTUM = 18000, 144000, 600
FAMILIES = {
    'Ma': {'problems': 6, 'sigma': 0.02, 'types': (('dead', 0.40), ('decoy', 0.30), ('vein', 0.17), ('slow', 0.13))},
    'Ha': {'problems': 3, 'sigma': 0.015, 'types': (('dead', 0.45), ('decoy', 0.25), ('vein', 0.15), ('slow', 0.15))},
    'Hb': {'problems': 5, 'sigma': 0.025, 'types': (('dead', 0.38), ('decoy', 0.32), ('vein', 0.18), ('slow', 0.12))},
}
HELD_OUT = ('Ha', 'Hb')
WORLDS_PER_FAMILY, NULLS_PER_FAMILY = 12, 3
ARMS = ('P', 'D', 'D0')
MATERIAL, ALPHA = 0.02, 0.05
SLICE_S, PAUSED = 6600, 3
MODULES = ('direction.py', 'curves.py', 'converge.py', 'allocate.py', 'engine.py', 'manifest.py', 'world.py',
           'meta.py')
PINNED = {             # `pins()` at preregistration; checked at run time
    'direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'allocate.py': 'd28d0d8bd9a85f38d335f5680ad24a444ed5f5cad5420fa075c8079ccde28177',
    'engine.py': '849b9bfd611c5cbc8899a55e9ec11348741ecdb7e93e47f10d606ff117e84fe3',
    'manifest.py': '75587e359fcb37a9ab97109a79f1ec5d3417e9618d3bc52cc9f9be8a134055e1',
    'world.py': 'afec2f2f31dbca49eff5561b129c72435403725ed222b389a12742c2f6ac8579',
    'meta.py': 'ec1946c17f4cb816224a3d095abda4f0ffec89a131c85c6d069e9a7a8c710c28',
}


def h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12], 16)


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis/frontier' / m).read_bytes()).hexdigest() for m in MODULES}


def meta_world():
    return ('Ma-0', 'Ma', h(STUDY, SEALED_SEED, 'Ma', 0), False)


def worlds():
    """The held-out evaluation worlds: [(world key, family, seed, null)] in a fixed order."""
    out = []
    for fam in HELD_OUT:
        for i in range(WORLDS_PER_FAMILY):
            out.append((f'{fam}-{i}', fam, h(STUDY, SEALED_SEED, fam, i), False))
        for i in range(NULLS_PER_FAMILY):
            out.append((f'{fam}-null{i}', fam, h(STUDY, SEALED_SEED, fam, 'null', i), True))
    return out


def make_world(fam, seed, null, horizon):
    from genesis.frontier.world import PlantedWorld
    spec = FAMILIES[fam]
    return PlantedWorld(seed, problems=spec['problems'], horizon=horizon, sigma=spec['sigma'], null=null,
                        types=spec['types'])


# --------------------------------------------------------------------------------------------- the meta-search

def meta_search(world=None, b_in=B_IN, budget=META_BUDGET, quantum=META_QUANTUM):
    """The kernel's side and the research plane's: returns the promoted configuration and the meta-search's record."""
    from genesis.frontier import meta as MT
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    key, fam, seed, null = world or meta_world()
    records, sizes = {}, {}

    def factory(run_key):
        w = make_world(fam, seed, null, b_in)
        rec = records.setdefault(run_key, {})
        sizes['n'] = len(w.problems())

        def verify(p, a):
            v = w.verify(p, a)
            rec[p] = max(rec.get(p, 0.0), v)
            return v
        return Manifest(w, verify, b_in, quantum=QUANTUM, description={'study': STUDY, 'meta_task': key})

    def meta_verify(task, art):
        rec = records.get(art.get('run'))
        return sum(rec.values()) / sizes['n'] if rec else 0.0
    dom = MT.MetaDomain({'T0': factory}, policies=('frontier',))
    e = Frontier(Manifest(dom, meta_verify, budget, quantum=quantum, description={'study': STUDY, 'level': 'meta'}),
                 'frontier', seed=0)
    e.run()
    art = e.best_artifact.get('T0')
    promoted = dict(art['config']['params']) if art else dict(MT.DEFAULT)
    return {'promoted': promoted, 'nothing_promoted': art is None, 'best_value': e.best_verified.get('T0', 0.0),
            'c_meta': dom.inner_compute(), 'opened': len(e.branches), 'outer_spent': e.spent,
            'curve': [list(x) for x in e.curve[::10]],
            'on_grid': all(promoted.get(k) in v for k, v in MT.GRID.items()) and set(promoted) == set(MT.GRID)}


# --------------------------------------------------------------------------------------------- evaluation

def run_one(fam, seed, null, arm, index, params, budget):
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    w = make_world(fam, seed, null, B)
    m = Manifest(w, w.verify, budget, quantum=QUANTUM, description={'study': STUDY, 'family': fam, 'arm': arm})
    e = Frontier(m, 'frontier', seed=index, policy_params=dict(params))
    e.run()
    s = e.summary()
    ref = w.oracle(B)
    return {'arm': arm, 'family': fam, 'seed': seed, 'null': null, 'total': s['total'], 'reference': ref,
            'value': s['total'] / ref if ref > 0 else None, 'spent': s['spent'], 'budget': budget,
            'branches': s['branches'], 'verify_calls': s['verify_calls'], 'abstracted': s['abstracted'],
            'revealed': s['revealed']}


def extra_budget(c_meta, n_worlds=None):
    n = n_worlds or sum(1 for w in worlds() if not w[3])
    return int(c_meta / n) // QUANTUM * QUANTUM


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def analyse(rows, ws=None):
    ws = ws or worlds()
    keys = [k for k, fam, s, null in ws if not null]
    val = lambda arm: [rows[(k, arm)]['value'] for k in keys]
    P, D, D0 = val('P'), val('D'), val('D0')
    p1 = wilcoxon([a - b for a, b in zip(P, D)], 'greater')
    p1['label'] = 'SELF_IMPROVED' if p1['p'] < ALPHA and p1['mean'] >= MATERIAL else 'NOT_SHOWN'
    s1 = wilcoxon([a - b for a, b in zip(P, D0)], 'two-sided')
    s1['label'] = ('CONFIG_BETTER' if s1['p'] < ALPHA and s1['mean'] >= MATERIAL else
                   'CONFIG_WORSE' if s1['p'] < ALPHA and s1['mean'] <= -MATERIAL else 'TIE')
    fams = sorted({f for k, f, s, null in ws})
    fam_means = {fam: {a: statistics.mean(rows[(k, a)]['value'] for k, f, s, null in ws if f == fam and not null)
                       for a in ARMS} for fam in fams}
    return {'P1': p1, 'S1': s1, 'S2': wilcoxon([a - b for a, b in zip(D, D0)], 'greater'), 'S3': fam_means,
            'means': {a: statistics.mean(val(a)) for a in ARMS}}


def verdict(valid, res, nothing_promoted):
    if not valid:
        return 'INVALID'
    v = res['P1']['label']
    return v + (' (NOTHING_PROMOTED)' if nothing_promoted and v == 'NOT_SHOWN' else '')


def main(argv=None, registered=True, world_list=None, meta=None, b_in=B_IN, meta_budget=META_BUDGET, budget=B):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    from genesis.frontier import meta as MT
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'frontier_meta_b20r163').resolve():
        raise SystemExit('the registered output is evidence/frontier_meta_b20r163')
    if registered and pins() != PINNED:
        raise SystemExit('the engine modules differ from the preregistered pins')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    mpath = out / 'meta.json'
    if mpath.exists():
        ms = json.loads(mpath.read_text())
    else:
        ms = meta_search(meta, b_in=b_in, budget=meta_budget)
        mpath.write_text(json.dumps(ms, indent=1, sort_keys=True) + '\n')
    ws = world_list if world_list is not None else worlds()
    n_eval = sum(1 for w in ws if not w[3])
    extra = extra_budget(ms['c_meta'], n_eval)
    plan = {'P': (ms['promoted'], budget), 'D': (MT.DEFAULT, budget + extra), 'D0': (MT.DEFAULT, budget)}
    rows = {}
    path = out / 'rows.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[(r['world'], r['arm'])] = r
    new = 0
    for idx, (key, fam, seed, null) in enumerate(ws):
        for arm in ARMS:
            if (key, arm) in rows:
                continue
            if new and time.monotonic() - t0 > SLICE_S:
                return PAUSED
            params, bud = plan[arm]
            r = run_one(fam, seed, null, arm, idx, params, bud)
            r['world'] = key
            rows[(key, arm)] = r
            with path.open('a') as f:
                f.write(json.dumps(r, sort_keys=True) + '\n')
            new += 1
    nulls_ok = all(rows[(k, a)]['total'] == 0.0 for k, fam, s, null in ws if null for a in ARMS)
    spent_ok = all(r['spent'] >= r['budget'] - QUANTUM - 1 for r in rows.values())
    pins_ok = (not registered) or pins() == PINNED
    valid = nulls_ok and spent_ok and pins_ok and ms['on_grid']
    res = analyse(rows, ws)
    v = verdict(valid, res, ms['nothing_promoted'])
    changed = {k: [MT.DEFAULT[k], ms['promoted'][k]] for k in MT.DEFAULT if ms['promoted'].get(k) != MT.DEFAULT[k]}
    summary = {'study': STUDY, 'schema': 'genesis-b20r163-frontier-meta-v1', 'verdict': v, 'valid': valid,
               'nulls_ok': nulls_ok, 'spent_ok': spent_ok, 'pins_ok': pins_ok, 'results': res,
               'S4': {'promoted': ms['promoted'], 'changed_from_defaults': changed, 'c_meta': ms['c_meta'],
                      'extra_budget_per_world': extra, 'nothing_promoted': ms['nothing_promoted']},
               'S5': {'best_meta_value': ms['best_value'], 'opened': ms['opened'], 'curve': ms['curve']},
               'worlds': [list(x) for x in ws], 'budget': budget,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; a calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('worlds', 'results', 'S5')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
