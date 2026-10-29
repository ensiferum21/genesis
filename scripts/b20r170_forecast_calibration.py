#!/usr/bin/env python3
"""B20_R170 (Foundry G2): does the Frontier, searching a grammar of forecast-update rules, invent one that repairs its
forecasts' calibration, and does that pay at matched total compute? (DEV, preregistered; a calibration domain)

    taskset -c 0 python3 scripts/b20r170_forecast_calibration.py evidence/forecast_calibration_b20r170   run ALONE (resumable; slices exit 3)

**Why.** F3 (B20_R156) found the Frontier's 90% forecast intervals covering 66%, biased low, and a textbook correction
did not repair them (`docs/checkpoints/B20_R156_RECORD.md`). Daniel's Foundry proposal (28 Oct 2026; `docs/
OMEGA_FOUNDRY.md` §3, G2) asks for the repair to be invented, not written: the engine searches a small grammar of
update rules, each mapping its own resolved forecasts to an adjustment of its future intervals
(`frontier/calibrate.py`: signal none, resolved or hindcast; form scale, shift or both; sides; conditioning;
adaptive-conformal or split-conformal quantile updates; rate). A rule sees only what the engine sees: its own
observations. It is a calibration of the machinery on planted worlds: **nothing here is evidence about real
problems.**

**Meta-search (on one sealed meta-training world).** The kernel draws one world of family Ga (6 problems) from the
sealed seed SEALED_SEED. `MetaDomain` poses it as the only meta-task, with the approaches = the 144 points of
`calibrate.GRID` (81 distinct behaviours, the identity among them); every other engine setting is the default. Each
inner run is the full engine (abstraction and branching out on) at B_IN = 18,000 units, quantum 10. The outer
Frontier (defaults, seed 0) spends META_BUDGET = 144,000 inner units, outer quantum 600. **The promoted rule** is
the rule of the outer engine's best verified artifact (the inner engine's total verified value per problem); if
nothing was verified, the identity, and the study says so. **C_meta** is the meta-search's true compute
(`MetaDomain.inner_compute()`).

**Evaluation (held out).** 24 worlds of two held-out families, Ja and Jb (12 each), and 6 null worlds (3 each),
from the sealed seed. Ga, Ja and Jb differ from development, from the test suite and from F3's and F6's families.
Budget B = 12,000 units. Arms, each run once per world with the world's index as its seed, full engine:
  * P:  the promoted rule, at B;
  * D:  the identity (the fixed forecaster), at B + C_meta / 24 rounded down to a quantum: matched total compute;
  * D0: the identity, at B.
A run's value is its total verified value over the world's reference at B (`PlantedWorld.oracle(B)`). A run's
coverage is measured by the kernel as F3's S2: every forecast the run used (P: as calibrated; D, D0: raw) that was
made once at least a quarter of its horizon had been observed, checked against the hidden curve at its horizon.

**Primary (Holm over the two).**
  * **P1 (pays at matched total compute):** P against D on value, one-sided Wilcoxon signed-rank over the 24 worlds;
    passes if p_Holm < 0.05 and the mean difference is at least MATERIAL (0.02).
  * **P2 (calibration repaired):** per-world coverage of P against D0, one-sided Wilcoxon over the worlds where both
    have at least MIN_CHECKED (10) checked forecasts (at least 12 such worlds, else P2 fails); passes if p_Holm < 0.05
    AND the 95% bootstrap interval (over those worlds, 2,000 resamples, seeded) of P's mean per-world coverage lies
    inside BAND = [0.80, 0.97] (the forecaster's own acceptance band, `docs/OMEGA_FRONTIER.md` §4.3).
**Verdict:**
  * INVALID if validity fails;
  * CALIBRATION_INVENTED_AND_PAYS if P1 and P2 pass;
  * CALIBRATION_INVENTED if only P2 passes;
  * PAYS_WITHOUT_CALIBRATION if only P1 passes;
  * otherwise NOT_SHOWN, with IDENTITY_PROMOTED noted when the promoted rule is the identity.
**Secondary (reported, not in the family):**
  * S1: P against D0 on value, two-sided (the rule's effect at equal budget: RULE_BETTER, RULE_WORSE or TIE);
  * S2: D against D0 on value, one-sided (what the extra budget buys);
  * S3: per-family means of value and coverage for every arm;
  * S4: the promoted rule, C_meta, the extra budget per world, CPU per arm (the hindcast signal costs CPU, not
    evaluations; CPU is reported, not matched);
  * S5: the meta-search's curve and the number of rules it opened;
  * S6: D's coverage against D0's (does budget alone change calibration?).
**Validity:**
  * in every null world, every arm's total is exactly 0;
  * every run spent its budget to within one quantum plus its last step's verifications;
  * the promoted rule lies on the grid;
  * the pinned digests of the engine's modules are the ones at preregistration.

**Expectation, stated before running, informed by the development look (disclosed).** P2 passes if a non-identity
rule is promoted (the look: coverage 0.70 for the identity, 0.83-0.90 for four active rules); P1 NOT_SHOWN (D has
about 50% more budget per world; the look's value gains were +0.01 to +0.02 at equal budget, within noise); S1 TIE.
So CALIBRATION_INVENTED, moderate confidence. If the meta-search promotes the identity, NOT_SHOWN
(IDENTITY_PROMOTED).

**Development looks (disclosed).** 29 Oct 2026 (`scratchpad/devG2/look.py`, not committed): six planted worlds of
seeds 881000-881005 (4 problems, sigma 0.02, the default types, budget 12,000; no study's seeds), the identity and
four hand-picked rules, allocation policy only (no abstraction or branching out). Mean value 0.843 (identity) against
0.837-0.866; mean coverage 0.697 against 0.827-0.904. Two of the four rules used an earlier form of the quantile
update (residuals about a moving shifted median), replaced before this preregistration because a unit test showed it
under-covered when the shift moved; the look was not repeated. The test suite's worlds (seeds 887001) are not this
study's.

**Cost.** The meta-search: about 12 inner runs' worth (a few minutes). The evaluation: 3 arms x 30 worlds x 10-25 s.
Under 1 h, in slices of 6,600 s. **Status.** DEV; a calibration; licenses nothing. Runs after B20_R163 (F6).
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

STUDY = 'b20r170'
OUTPUT = ROOT / 'evidence' / 'forecast_calibration_b20r170'
SEALED_SEED = 17001703
B, QUANTUM = 12000, 10
B_IN, META_BUDGET, META_QUANTUM = 18000, 144000, 600
FAMILIES = {
    'Ga': {'problems': 6, 'sigma': 0.02, 'types': (('dead', 0.42), ('decoy', 0.28), ('vein', 0.17), ('slow', 0.13))},
    'Ja': {'problems': 4, 'sigma': 0.015, 'types': (('dead', 0.40), ('decoy', 0.30), ('vein', 0.15), ('slow', 0.15))},
    'Jb': {'problems': 5, 'sigma': 0.03, 'types': (('dead', 0.45), ('decoy', 0.22), ('vein', 0.18), ('slow', 0.15))},
}
HELD_OUT = ('Ja', 'Jb')
WORLDS_PER_FAMILY, NULLS_PER_FAMILY = 12, 3
ARMS = ('P', 'D', 'D0')
MATERIAL, ALPHA = 0.02, 0.05
BAND, MIN_CHECKED, MIN_WORLDS, BOOT = (0.80, 0.97), 10, 12, 2000
SLICE_S, PAUSED = 6600, 3
MODULES = ('direction.py', 'curves.py', 'converge.py', 'allocate.py', 'engine.py', 'manifest.py', 'world.py',
           'meta.py', 'calibrate.py')
PINNED = {             # `pins()` at preregistration; checked at run time
    'direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'allocate.py': '333f2d78ff6dda87909620ddc6435a607bf4c54508a0fe0e6b562ee549c0285a',
    'engine.py': 'bbea0852b1ecaec56ffa4ac669a6ef5e1375f47b5fcb4f71289af62c8b0ef150',
    'manifest.py': 'c9fb74568982cb8c554311559eba29d2c7fc6c30194f99229a71b63ac54a2a46',
    'world.py': 'afec2f2f31dbca49eff5561b129c72435403725ed222b389a12742c2f6ac8579',
    'meta.py': 'ec1946c17f4cb816224a3d095abda4f0ffec89a131c85c6d069e9a7a8c710c28',
    'calibrate.py': 'c3bd3d8be1975318d6d63ff189a8cd3a9393e14850c701eef2dfdf71c3f92b25',
}


def h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12], 16)


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis/frontier' / m).read_bytes()).hexdigest() for m in MODULES}


def meta_world():
    return ('Ga-0', 'Ga', h(STUDY, SEALED_SEED, 'Ga', 0), False)


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
    """Returns the promoted rule and the meta-search's record. The meta verifier (kernel side) answers from its own
    record of what the inner verifier confirmed for that run."""
    from genesis.frontier import calibrate as CAL
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
    dom = MT.MetaDomain({'T0': factory}, policies=('frontier',), grid=CAL.GRID)
    e = Frontier(Manifest(dom, meta_verify, budget, quantum=quantum, description={'study': STUDY, 'level': 'meta'}),
                 'frontier', seed=0)
    e.run()
    art = e.best_artifact.get('T0')
    promoted = dict(art['config']['params']) if art else dict(CAL.DEFAULT)
    rules = {json.dumps(CAL.canonical(b['direction']['params']), sort_keys=True) for b in e.branches.values()}
    return {'promoted': promoted, 'canonical': CAL.canonical(promoted), 'nothing_promoted': art is None,
            'identity_promoted': CAL.canonical(promoted) == CAL.DEFAULT,
            'best_value': e.best_verified.get('T0', 0.0), 'c_meta': dom.inner_compute(), 'opened': len(e.branches),
            'distinct_rules_opened': len(rules), 'outer_spent': e.spent, 'curve': [list(x) for x in e.curve[::10]],
            'on_grid': set(promoted) == set(CAL.GRID) and all(promoted[k] in v for k, v in CAL.GRID.items())}


# --------------------------------------------------------------------------------------------- evaluation

def coverage_of(e, w):
    """The kernel's check of every forecast the run used (calibrated if the rule is active), as F3's S2."""
    pol = e.policy
    used = pol._fc_used if pol.calib.active else pol._fc_cache
    hits = n = 0
    for (bid, npts, k), fc in sorted(used.items()):
        H = pol._fc_cache[(bid, npts, k)]['H']
        b = e.branches[bid]
        t_obs = b['ts'][npts - 1] if npts else 0
        if npts >= 4 and H > 0 and t_obs / H >= 0.25 and b['direction']['problem'] in w.problems():
            truth = w.truth(b['direction']['problem'], b['direction'], H)
            n += 1
            hits += fc['lo'] <= truth <= fc['hi']
    return {'n': n, 'hits': hits}


def run_one(fam, seed, null, arm, index, params, budget):
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    w = make_world(fam, seed, null, B)
    m = Manifest(w, w.verify, budget, quantum=QUANTUM, description={'study': STUDY, 'family': fam, 'arm': arm})
    c0 = time.process_time()
    e = Frontier(m, 'frontier', seed=index, policy_params=dict(params))
    e.run()
    cpu = time.process_time() - c0
    s = e.summary()
    ref = w.oracle(B)
    return {'arm': arm, 'family': fam, 'seed': seed, 'null': null, 'total': s['total'], 'reference': ref,
            'value': s['total'] / ref if ref > 0 else None, 'spent': s['spent'], 'budget': budget,
            'branches': s['branches'], 'verify_calls': s['verify_calls'], 'coverage': coverage_of(e, w),
            'resolved': e.policy.calib.resolved, 'cpu_s': round(cpu, 3)}


def extra_budget(c_meta, n_worlds=None):
    n = n_worlds or sum(1 for w in worlds() if not w[3])
    return int(c_meta / n) // QUANTUM * QUANTUM


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def holm(ps):
    """Holm-adjusted p-values for a dict {name: p}."""
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[k]))
        out[k] = run
    return out


def boot_ci(xs, seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    x = np.asarray(xs, float)
    m = x[rng.integers(0, len(x), size=(BOOT, len(x)))].mean(axis=1)
    return [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))]


def analyse(rows, ws=None):
    ws = ws or worlds()
    keys = [k for k, fam, s, null in ws if not null]
    val = lambda arm: [rows[(k, arm)]['value'] for k in keys]          # noqa: E731
    cov = lambda k, arm: rows[(k, arm)]['coverage']['hits'] / rows[(k, arm)]['coverage']['n']   # noqa: E731
    P, D, D0 = val('P'), val('D'), val('D0')
    p1 = wilcoxon([a - b for a, b in zip(P, D)], 'greater')
    both = [k for k in keys if rows[(k, 'P')]['coverage']['n'] >= MIN_CHECKED
            and rows[(k, 'D0')]['coverage']['n'] >= MIN_CHECKED]
    cp, c0 = [cov(k, 'P') for k in both], [cov(k, 'D0') for k in both]
    p2 = wilcoxon([a - b for a, b in zip(cp, c0)], 'greater') if len(both) >= MIN_WORLDS else \
        {'n': 0, 'p': 1.0, 'mean': None}
    p2['worlds'] = len(both)
    p2['coverage_P'] = statistics.mean(cp) if cp else None
    p2['coverage_D0'] = statistics.mean(c0) if c0 else None
    p2['ci_P'] = boot_ci(cp, h(STUDY, 'boot')) if len(cp) >= 2 else None
    adj = holm({'P1': p1['p'], 'P2': p2['p']})
    p1['p_holm'], p2['p_holm'] = adj['P1'], adj['P2']
    p1['pass'] = p1['p_holm'] < ALPHA and p1['mean'] >= MATERIAL
    p2['in_band'] = bool(p2['ci_P'] and BAND[0] <= p2['ci_P'][0] and p2['ci_P'][1] <= BAND[1])
    p2['pass'] = len(both) >= MIN_WORLDS and p2['p_holm'] < ALPHA and p2['in_band']
    s1 = wilcoxon([a - b for a, b in zip(P, D0)], 'two-sided')
    s1['label'] = ('RULE_BETTER' if s1['p'] < ALPHA and s1['mean'] >= MATERIAL else
                   'RULE_WORSE' if s1['p'] < ALPHA and s1['mean'] <= -MATERIAL else 'TIE')
    fams = sorted({f for k, f, s, null in ws})
    s3 = {fam: {a: {'value': statistics.mean(rows[(k, a)]['value'] for k, f, s, null in ws if f == fam and not null),
                    'coverage': sum(rows[(k, a)]['coverage']['hits'] for k, f, s, null in ws if f == fam and not null)
                    / max(1, sum(rows[(k, a)]['coverage']['n'] for k, f, s, null in ws if f == fam and not null))}
                for a in ARMS} for fam in fams}
    dd = [k for k in keys if rows[(k, 'D')]['coverage']['n'] >= MIN_CHECKED
          and rows[(k, 'D0')]['coverage']['n'] >= MIN_CHECKED]
    s6 = wilcoxon([cov(k, 'D') - cov(k, 'D0') for k in dd], 'two-sided') if dd else {'n': 0, 'p': 1.0, 'mean': None}
    cpu = {a: statistics.mean(rows[(k, a)]['cpu_s'] for k in keys) for a in ARMS}
    return {'P1': p1, 'P2': p2, 'S1': s1, 'S2': wilcoxon([a - b for a, b in zip(D, D0)], 'greater'), 'S3': s3,
            'S6': s6, 'means': {a: statistics.mean(val(a)) for a in ARMS}, 'cpu_mean_s': cpu}


def verdict(valid, res, identity):
    if not valid:
        return 'INVALID'
    p1, p2 = res['P1']['pass'], res['P2']['pass']
    if p1 and p2:
        return 'CALIBRATION_INVENTED_AND_PAYS'
    if p2:
        return 'CALIBRATION_INVENTED'
    if p1:
        return 'PAYS_WITHOUT_CALIBRATION'
    return 'NOT_SHOWN' + (' (IDENTITY_PROMOTED)' if identity else '')


def main(argv=None, registered=True, world_list=None, meta=None, b_in=B_IN, meta_budget=META_BUDGET, budget=B,
         output=OUTPUT, pinned=None):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. A design test may redirect the
    output, the worlds and the budgets while keeping registered=True, so that the registered path's validity is
    itself tested (B20_R141's lesson); `pinned` stands in for PINNED only there."""
    from genesis.frontier import calibrate as CAL
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[3])
    out = Path(argv[0]).resolve()
    pinned = PINNED if pinned is None else pinned
    if registered and out != Path(output).resolve():
        raise SystemExit(f'the registered output is {output}')
    if registered and (pinned is None or pins() != pinned):
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
    plan = {'P': (ms['promoted'], budget), 'D': (CAL.DEFAULT, budget + extra), 'D0': (CAL.DEFAULT, budget)}
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
    pins_ok = (not registered) or pins() == pinned
    valid = nulls_ok and spent_ok and pins_ok and ms['on_grid']
    res = analyse(rows, ws)
    v = verdict(valid, res, ms['identity_promoted'])
    changed = {k: [CAL.DEFAULT[k], ms['promoted'][k]] for k in CAL.DEFAULT if ms['promoted'].get(k) != CAL.DEFAULT[k]}
    summary = {'study': STUDY, 'schema': 'genesis-b20r170-forecast-calibration-v1', 'verdict': v, 'valid': valid,
               'nulls_ok': nulls_ok, 'spent_ok': spent_ok, 'pins_ok': pins_ok, 'results': res,
               'S4': {'promoted': ms['promoted'], 'canonical': ms['canonical'], 'changed_from_identity': changed,
                      'c_meta': ms['c_meta'], 'extra_budget_per_world': extra,
                      'nothing_promoted': ms['nothing_promoted'], 'identity_promoted': ms['identity_promoted']},
               'S5': {'best_meta_value': ms['best_value'], 'opened': ms['opened'],
                      'distinct_rules_opened': ms['distinct_rules_opened'], 'curve': ms['curve']},
               'worlds': [list(x) for x in ws], 'budget': budget,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; a calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('worlds', 'results', 'S5')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
