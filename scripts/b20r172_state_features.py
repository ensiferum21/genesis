#!/usr/bin/env python3
"""B20_R172 (Foundry G4): does the Frontier, replaying its own allocation decisions, find a state feature its index
lacks, and does that feature pay at matched total compute? (DEV, preregistered; a calibration domain)

    taskset -c 0 python3 scripts/b20r172_state_features.py evidence/state_features_b20r172   run ALONE (resumable; slices exit 3)

**Why.** Daniel's Foundry proposal (28 Oct 2026; `docs/OMEGA_FOUNDRY.md` §3, G4): decision-relevant state abstraction
by counterexamples. Where two branches look alike to the allocator's index but advancing them yields different
gains, the index is missing a distinction (ARA's SENSE_BLIND class, turned on the engine's own controller). The
machinery is `frontier/statefeat.py`: the policy logs its two leading candidates at each exploitation decision; each
is replayed alone for k quanta through the domain's public step (paid compute); a cross-validated search over 697
feature expressions proposes a feature only if its held-out agreement with the replays beats the index alone (by
0.02, one-sided z >= 1.645). It is a calibration of the machinery on planted worlds: **nothing here is evidence about
real problems.**

**The search (on sealed training worlds).** The kernel draws TRAIN = 2 worlds of family Ka from the sealed seed. On
each, the full engine (defaults, abstraction and branching out on, decision logging on) runs at B = 12,000 units;
PAIRS = 120 of its logged decisions, evenly spaced, are replayed with K_REPLAY = 10 quanta per candidate. The pooled
pairs go to `statefeat.propose`. **C_search** = the training runs' spend plus every replay's compute. If nothing is
proposed, P is the defaults and the study says NOTHING_PROPOSED.

**Evaluation (held out).** 24 worlds of two held-out families, La and Lb (12 each), and 6 null worlds (3 each), from
the sealed seed. Ka, La and Lb differ from development, the test suite and F3's, F6's and B20_R170's families.
Arms, each run once per world with the world's index as its seed, full engine:
  * P:  the defaults with the proposed feature in the index (`state_feature`), at B;
  * D:  the defaults, at B + C_search / 24 rounded down to a quantum: matched total compute;
  * D0: the defaults, at B (with decision logging on, which changes nothing; its decisions serve S7).
A run's value is its total verified value over the world's reference at B (`PlantedWorld.oracle(B)`).

**Primary.** P1: P against D on value, one-sided Wilcoxon signed-rank over the 24 worlds.
**Verdict:**
  * INVALID if validity fails;
  * FEATURE_PAYS if p < 0.05 and the mean difference is at least MATERIAL (0.02);
  * otherwise NOT_SHOWN, with NOTHING_PROPOSED noted when the search proposed nothing.
**Secondary (reported, not in the family):**
  * S1: P against D0 on value, two-sided (the feature at equal budget: FEATURE_BETTER, FEATURE_WORSE or TIE);
  * S2: D against D0, one-sided (what the extra budget buys);
  * S3: per-family means of every arm;
  * S4: the feature, its held-out agreement and z in the search, C_search and the extra budget per world;
  * S7 (does the distinction hold on new worlds?): on every held-out world, up to S7_PAIRS of D0's logged decisions,
    evenly spaced, are replayed (K_REPLAY quanta; analysis compute, charged to no arm); the agreement of the index
    with the feature against the index alone, one-sided Wilcoxon over worlds (FEATURE_GENERALISES if p < 0.05).
**Validity:**
  * in every null world, every arm's total is exactly 0;
  * every run spent its budget to within one quantum plus its last step's verifications;
  * the proposed feature, if any, is in the feature language;
  * the pinned digests of the engine's modules are the ones at preregistration.

**Expectation, stated before running, informed by the development look (disclosed).** A feature is proposed (the
look: two of three single worlds proposed one). P1 NOT_SHOWN: D has about a quarter more budget per world, and the
look found the index already agreeing with the replays on 0.82-0.92 of weighted pairs, so the room is small. S1 TIE.
S7 FEATURE_GENERALISES, low confidence. So NOT_SHOWN.

**Development looks (disclosed).** 29 Oct 2026 (`scratchpad`, not committed): three planted worlds of seeds
887021-887023 (3 problems, sigma 0.02, the default types, budget 12,000, allocation only), 200 replayed pairs each
(k = 20). The index agreed with the replays on 0.83, 0.92 and 0.82; features were proposed on two (held-out 0.90
and 0.92: `slope16 - curv` and `t / index`). The test suite's worlds (seeds 887011) are not this study's. The
cross-validation of the whole search and the z threshold were added before this preregistration, after a unit test
showed the earlier rule proposing features on noise.

**Cost.** The search: two engine runs and 48,000 units of replay (minutes). The evaluation: 3 arms x 30 worlds x
10-25 s, and S7's replays (24 x 80 x 200 units, seconds each). Under 1 h, in slices of 6,600 s. **Status.** DEV; a
calibration; licenses nothing. Runs after B20_R170.
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

STUDY = 'b20r172'
OUTPUT = ROOT / 'evidence' / 'state_features_b20r172'
SEALED_SEED = 17201729
B, QUANTUM = 12000, 10
TRAIN, PAIRS, K_REPLAY, S7_PAIRS = 2, 120, 10, 80
FAMILIES = {
    'Ka': {'problems': 5, 'sigma': 0.02, 'types': (('dead', 0.44), ('decoy', 0.26), ('vein', 0.17), ('slow', 0.13))},
    'La': {'problems': 4, 'sigma': 0.02, 'types': (('dead', 0.38), ('decoy', 0.32), ('vein', 0.16), ('slow', 0.14))},
    'Lb': {'problems': 6, 'sigma': 0.025, 'types': (('dead', 0.46), ('decoy', 0.24), ('vein', 0.16), ('slow', 0.14))},
}
HELD_OUT = ('La', 'Lb')
WORLDS_PER_FAMILY, NULLS_PER_FAMILY = 12, 3
ARMS = ('P', 'D', 'D0')
MATERIAL, ALPHA = 0.02, 0.05
SLICE_S, PAUSED = 6600, 3
MODULES = ('direction.py', 'curves.py', 'converge.py', 'allocate.py', 'engine.py', 'manifest.py', 'world.py',
           'calibrate.py', 'statefeat.py')
PINNED = {             # `pins()` at preregistration; checked at run time
    'direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'allocate.py': '5518affe5f521d20288d2f1982f2016efe9641222954e2782d6473b7be07d9e9',
    'engine.py': 'bbea0852b1ecaec56ffa4ac669a6ef5e1375f47b5fcb4f71289af62c8b0ef150',
    'manifest.py': 'c9fb74568982cb8c554311559eba29d2c7fc6c30194f99229a71b63ac54a2a46',
    'world.py': 'afec2f2f31dbca49eff5561b129c72435403725ed222b389a12742c2f6ac8579',
    'calibrate.py': 'c3bd3d8be1975318d6d63ff189a8cd3a9393e14850c701eef2dfdf71c3f92b25',
    'statefeat.py': '5e17431bd812bdee00eaa20dd598786742271889b0067deb52459678ef53ca1d',
}


def h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12], 16)


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis/frontier' / m).read_bytes()).hexdigest() for m in MODULES}


def training_worlds():
    return [(f'Ka-{i}', 'Ka', h(STUDY, SEALED_SEED, 'Ka', i), False) for i in range(TRAIN)]


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


def engine(fam, seed, null, index, params, budget):
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    w = make_world(fam, seed, null, B)
    m = Manifest(w, w.verify, budget, quantum=QUANTUM, description={'study': STUDY, 'family': fam})
    e = Frontier(m, 'frontier', seed=index, policy_params=dict(params))
    e.run()
    return e, w


def spaced(decisions, n):
    """n decisions evenly spaced over the run (all of them if fewer)."""
    if len(decisions) <= n:
        return list(decisions)
    return [decisions[int(i * len(decisions) / n)] for i in range(n)]


# --------------------------------------------------------------------------------------------- the search

def search(train=None, budget=B, pairs_per=PAIRS, k=K_REPLAY):
    from genesis.frontier import statefeat as SF
    pairs, c_search, per = [], 0, []
    for i, (key, fam, seed, null) in enumerate(train or training_worlds()):
        e, w = engine(fam, seed, null, 1000 + i, {'log_decisions': True}, budget)
        got, used = SF.counterexamples(w, spaced(e.policy.decisions, pairs_per), k, QUANTUM)
        pairs += got
        c_search += e.spent + used
        per.append({'world': key, 'spent': e.spent, 'replay': used, 'decisions': len(e.policy.decisions),
                    'pairs': len(got), 'agreement_index': SF.agreement(got)})
    feature = SF.propose(pairs)
    return {'feature': feature, 'nothing_proposed': feature is None, 'c_search': c_search, 'pairs': len(pairs),
            'per_world': per, 'agreement_index': SF.agreement(pairs),
            'in_language': feature is None or SF.check(feature['expr'])}


# --------------------------------------------------------------------------------------------- evaluation

def run_one(fam, seed, null, arm, index, params, budget, feature):
    from genesis.frontier import statefeat as SF
    c0 = time.process_time()
    e, w = engine(fam, seed, null, index, params, budget)
    cpu = time.process_time() - c0
    s = e.summary()
    ref = w.oracle(B)
    row = {'arm': arm, 'family': fam, 'seed': seed, 'null': null, 'total': s['total'], 'reference': ref,
           'value': s['total'] / ref if ref > 0 else None, 'spent': s['spent'], 'budget': budget,
           'branches': s['branches'], 'verify_calls': s['verify_calls'], 'cpu_s': round(cpu, 3)}
    if arm == 'D0' and not null and feature is not None:
        pairs, used = SF.counterexamples(w, spaced(e.policy.decisions, S7_PAIRS), K_REPLAY, QUANTUM)
        row['S7'] = {'pairs': len(pairs), 'replay': used, 'index': SF.agreement(pairs),
                     'feature': SF.agreement(pairs, feature['expr'], feature['weight'])}
    return row


def extra_budget(c_search, n_worlds=None):
    n = n_worlds or sum(1 for w in worlds() if not w[3])
    return int(c_search / n) // QUANTUM * QUANTUM


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def analyse(rows, ws=None):
    ws = ws or worlds()
    keys = [k for k, fam, s, null in ws if not null]
    val = lambda arm: [rows[(k, arm)]['value'] for k in keys]          # noqa: E731
    P, D, D0 = val('P'), val('D'), val('D0')
    p1 = wilcoxon([a - b for a, b in zip(P, D)], 'greater')
    p1['label'] = 'FEATURE_PAYS' if p1['p'] < ALPHA and p1['mean'] >= MATERIAL else 'NOT_SHOWN'
    s1 = wilcoxon([a - b for a, b in zip(P, D0)], 'two-sided')
    s1['label'] = ('FEATURE_BETTER' if s1['p'] < ALPHA and s1['mean'] >= MATERIAL else
                   'FEATURE_WORSE' if s1['p'] < ALPHA and s1['mean'] <= -MATERIAL else 'TIE')
    fams = sorted({f for k, f, s, null in ws})
    s3 = {fam: {a: statistics.mean(rows[(k, a)]['value'] for k, f, s, null in ws if f == fam and not null)
                for a in ARMS} for fam in fams}
    s7rows = [rows[(k, 'D0')]['S7'] for k in keys if 'S7' in rows[(k, 'D0')]]
    if s7rows:
        s7 = wilcoxon([r['feature'] - r['index'] for r in s7rows], 'greater')
        s7.update({'label': 'FEATURE_GENERALISES' if s7['p'] < ALPHA else 'NOT_SHOWN',
                   'index': statistics.mean(r['index'] for r in s7rows),
                   'feature': statistics.mean(r['feature'] for r in s7rows), 'worlds': len(s7rows)})
    else:
        s7 = {'label': 'NOT_RUN', 'worlds': 0}
    cpu = {a: statistics.mean(rows[(k, a)]['cpu_s'] for k in keys) for a in ARMS}
    return {'P1': p1, 'S1': s1, 'S2': wilcoxon([a - b for a, b in zip(D, D0)], 'greater'), 'S3': s3, 'S7': s7,
            'means': {a: statistics.mean(val(a)) for a in ARMS}, 'cpu_mean_s': cpu}


def verdict(valid, res, nothing):
    if not valid:
        return 'INVALID'
    v = res['P1']['label']
    return v + (' (NOTHING_PROPOSED)' if nothing and v == 'NOT_SHOWN' else '')


def main(argv=None, registered=True, world_list=None, train=None, budget=B, pairs_per=PAIRS, output=OUTPUT,
         pinned=None):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. A design test may redirect the
    output, the worlds and the budgets while keeping registered=True, so that the registered path's validity is
    itself tested (B20_R141's lesson); `pinned` stands in for PINNED only there."""
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
    spath = out / 'search.json'
    if spath.exists():
        sr = json.loads(spath.read_text())
    else:
        sr = search(train, budget=budget, pairs_per=pairs_per)
        spath.write_text(json.dumps(sr, indent=1, sort_keys=True) + '\n')
    ws = world_list if world_list is not None else worlds()
    n_eval = sum(1 for w in ws if not w[3])
    extra = extra_budget(sr['c_search'], n_eval)
    feature = sr['feature']
    p_params = {'state_feature': {'expr': feature['expr'], 'weight': feature['weight']}} if feature else {}
    plan = {'P': (p_params, budget), 'D': ({}, budget + extra), 'D0': ({'log_decisions': True}, budget)}
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
            r = run_one(fam, seed, null, arm, idx, params, bud, feature)
            r['world'] = key
            rows[(key, arm)] = r
            with path.open('a') as f:
                f.write(json.dumps(r, sort_keys=True) + '\n')
            new += 1
    nulls_ok = all(rows[(k, a)]['total'] == 0.0 for k, fam, s, null in ws if null for a in ARMS)
    spent_ok = all(r['spent'] >= r['budget'] - QUANTUM - 1 for r in rows.values())
    pins_ok = (not registered) or pins() == pinned
    valid = nulls_ok and spent_ok and pins_ok and sr['in_language']
    res = analyse(rows, ws)
    v = verdict(valid, res, sr['nothing_proposed'])
    summary = {'study': STUDY, 'schema': 'genesis-b20r172-state-features-v1', 'verdict': v, 'valid': valid,
               'nulls_ok': nulls_ok, 'spent_ok': spent_ok, 'pins_ok': pins_ok, 'results': res,
               'S4': {'feature': feature, 'c_search': sr['c_search'], 'extra_budget_per_world': extra,
                      'pairs': sr['pairs'], 'agreement_index_training': sr['agreement_index'],
                      'per_world': sr['per_world'], 'nothing_proposed': sr['nothing_proposed']},
               'worlds': [list(x) for x in ws], 'budget': budget,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; a calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('worlds', 'results')}, indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
