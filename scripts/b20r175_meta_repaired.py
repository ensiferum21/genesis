#!/usr/bin/env python3
"""B20_R175 (F6b): with its meta-search repaired, does the Frontier find a configuration of its own that beats its
defaults on held-out planted worlds? (DEV, preregistered; a calibration domain)

    taskset -c 0 python3 scripts/b20r175_meta_repaired.py evidence/meta_repaired_b20r175     run ALONE (resumable)

**Why.** F6 (B20_R163) was NOT_SHOWN, and a diagnosis after it was recorded (B20R163-META,
`docs/BLOCKING_DEFECTS.md`; `evidence/frontier_meta_b20r163_diagnosis/`) showed that its meta-search did not
compare configurations: the outer Frontier policy gave the first configuration it opened 17,992 inner units and
most of the others about 2,400, then promoted the best verified artifact, which compares values at those unequal
spends. The defaults were never opened, and about half the outer budget was spent stepping an inner run that had
already finished. F6 therefore says little about whether a configuration search pays. This study repeats the
question with the repair (`frontier/meta.py`, `SuiteMetaDomain` and `halving_bracket`):
  * the meta-task is a suite of K_TRAIN = 4 sealed training worlds of family Ma, so a configuration is judged on
    four worlds at once, not fitted to one;
  * the outer engine uses its successive-halving policy for one bracket (POOL 27 configurations, ETA 3, RUNG 1),
    so configurations are compared only at equal inner spend on the same worlds, and the survivor ends with the
    whole inner budget B_IN = B on every member (the deployment budget; F6 trained at 18,000 and deployed at
    12,000);
  * the kernel's guard: the survivor and the defaults each run once more on every training world at B, with fresh
    seeds; the survivor is promoted only if its mean value there is higher. Otherwise the defaults stay
    (NOTHING_PROMOTED).
F6's own procedure is repeated here on the first training world as the arm P1, so the repair is compared with it
on the same held-out worlds. The study cannot say which part of the repair matters.

**The meta-search (kernel side and research plane).** The kernel draws the K_TRAIN training worlds of family Ma
(6 problems each) from SEALED_SEED. `SuiteMetaDomain` poses them as one meta-task; the configurations are the
policy 'frontier' on `meta.GRID` (729 points). The outer quantum is K_TRAIN x Q_MEMBER (300 inner units per
member), and the outer budget is one halving bracket (`halving_bracket(27, 3, 1)`: 135 outer quanta; stages of 27
configurations at 600 units per member, 9 at 1,500, 3 at 4,200, and the survivor to 12,000). The policy draws its 27
configurations at random from the grid (a configuration may be drawn twice). The kernel's meta verifier answers
from its own record of what the members' verifiers confirmed. **The survivor** is the branch the bracket gave the most
compute. **C_K**, charged, is the search's inner compute plus the guard's.

**Evaluation (held out).** 24 worlds of families Ha and Hb (12 each) and 6 null worlds (3 each), from the sealed
seed; the families and their parameters are F6's. B = 12,000. Arms, each run once per world with the world's index
as its seed, full engine:
  * PK:  the promoted configuration (the survivor, or the defaults if the guard kept them), at B;
  * P1:  F6's procedure on the first training world (`MetaDomain`, B_IN 18,000, 144,000 outer units, quantum 600,
         the best verified artifact promoted), at B;
  * D0:  the defaults, at B;
  * D24: the defaults at B + C_K / 24, rounded down to a quantum: matched total compute over these 24 worlds.
The value of a run is its verified total over the world's reference at B (`PlantedWorld.oracle(B)`).

**Primary.** P1: PK against D0, one-sided Wilcoxon signed-rank over the 24 worlds. **Verdict:**
  * INVALID if validity fails;
  * CONFIG_TRANSFERS if p < 0.05 and the mean difference is at least MATERIAL (0.02);
  * otherwise NOT_SHOWN, with NOTHING_PROMOTED noted if the guard kept the defaults.
**Secondary (reported, not in the family):**
  * S1: PK against D24, one-sided: does the configuration pay for its search over these 24 worlds (PAYS or not);
  * S2: PK against P1, two-sided: the repaired search against F6's (REPAIR_BETTER, REPAIR_WORSE or TIE);
  * S3: P1 against D0, two-sided: F6's S1 on new worlds;
  * S4: D24 against D0, one-sided: what the extra budget buys;
  * S5: per-family means of every arm;
  * S6: the search's record: the bracket's stages, the configurations at each stage with their suite values, the
    survivor, the guard's values, the promoted configuration and how it differs from the defaults, C_K (search and
    guard), P1's configuration and its meta-search's compute;
  * S7: break-even: if g = mean(PK - D0) is at least MATERIAL and s = mean(D24 - D0) > 0, the number of worlds
    over which the configuration would repay C_K, 24 s / g (assuming value grows linearly in budget between B and
    B + C_K / 24); otherwise none.
**Validity:**
  * in every null world, every arm's total is exactly 0;
  * every run spent its budget to within one quantum plus its last step's verifications (11 units);
  * the bracket ran as scheduled: POOL configurations opened, the stage sizes as `halving_bracket`, and the
    survivor's members each spent their inner budget;
  * the promoted configuration and P1's lie on the grid;
  * the pinned digests of the engine's modules are the ones at preregistration.

**Expectation, stated before running (low confidence).** The defaults were shaped by F1's development look and
held their own against F6's arbitrary configuration (a tie). A bracket over 27 configurations on four worlds should
find one at least as good as the defaults on family Ma, but the guard may keep the defaults (about one chance in
three), and a configuration that wins on Ma need not win on Ha and Hb. So P1 NOT_SHOWN is more likely than
CONFIG_TRANSFERS (about 0.65 against 0.35). S1: not PAYS (C_K / 24 is about 10,000 units per world, close to doubling
the budget, and S4 in F6 was +0.148 for 3,200). S2: TIE or a small REPAIR_BETTER. S3: TIE, as in F6.

**Development looks (disclosed).** The diagnosis of F6's meta-search (above) was made on F6's training world after
F6 was recorded. The repaired machinery was developed on the test suite's worlds (seeds 101, 202, 303) and timed
once on development worlds of family Ma drawn from seeds 990001-990004 (none of this study's worlds), at the full
bracket, on CPU 1 (30 Oct 2026, 15:21-15:26 SGT): the bracket ran as scheduled (161,319 inner units, 123 s); the
guard promoted its survivor (eps 0.4, lam_con 0; 2.294 against the defaults' 2.222, 95,964 units, 111 s); one run of
the defaults at 22,750 took 44 s. Nothing was compared on held-out worlds. None of this study's worlds was generated
before preregistration.

**Cost.** The bracket: about 161,000 inner units (2 min); the guard: 96,000 (2 min); P1's meta-search: about 77,000
(about 5 min, as in F6). The evaluation: 4 arms x 30 worlds, about 50 min (D24's runs take about 45 s). About 1 h, in
slices of 6,600 s. **Status.** DEV; a
calibration; licenses nothing. Runs after PT-1 (B20_R159).
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

STUDY = 'b20r175'
SEALED_SEED = 41751593
B, QUANTUM = 12000, 10
K_TRAIN, Q_MEMBER = 4, 300
POOL, ETA, RUNG = 27, 3, 1
F6_B_IN, F6_META_BUDGET, F6_META_QUANTUM = 18000, 144000, 600
FAMILIES = {
    'Ma': {'problems': 6, 'sigma': 0.02, 'types': (('dead', 0.40), ('decoy', 0.30), ('vein', 0.17), ('slow', 0.13))},
    'Ha': {'problems': 3, 'sigma': 0.015, 'types': (('dead', 0.45), ('decoy', 0.25), ('vein', 0.15), ('slow', 0.15))},
    'Hb': {'problems': 5, 'sigma': 0.025, 'types': (('dead', 0.38), ('decoy', 0.32), ('vein', 0.18), ('slow', 0.12))},
}
HELD_OUT = ('Ha', 'Hb')
WORLDS_PER_FAMILY, NULLS_PER_FAMILY = 12, 3
ARMS = ('PK', 'P1', 'D0', 'D24')
MATERIAL, ALPHA = 0.02, 0.05
SLICE_S, PAUSED = 6600, 3
OUTPUT = ROOT / 'evidence' / 'meta_repaired_b20r175'
MODULES = ('direction.py', 'curves.py', 'converge.py', 'calibrate.py', 'statefeat.py', 'allocate.py', 'engine.py',
           'manifest.py', 'world.py', 'meta.py')
PINNED = {             # `pins()` at preregistration; checked at run time
    'direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'calibrate.py': 'c3bd3d8be1975318d6d63ff189a8cd3a9393e14850c701eef2dfdf71c3f92b25',
    'statefeat.py': '5e17431bd812bdee00eaa20dd598786742271889b0067deb52459678ef53ca1d',
    'allocate.py': '5518affe5f521d20288d2f1982f2016efe9641222954e2782d6473b7be07d9e9',
    'engine.py': 'bbea0852b1ecaec56ffa4ac669a6ef5e1375f47b5fcb4f71289af62c8b0ef150',
    'manifest.py': 'c9fb74568982cb8c554311559eba29d2c7fc6c30194f99229a71b63ac54a2a46',
    'world.py': 'afec2f2f31dbca49eff5561b129c72435403725ed222b389a12742c2f6ac8579',
    'meta.py': 'cfcc669774c162a6490021804dd2aaed090a88bcdf3c4a6258c7731ae9ac77e9',
}


def h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12], 16)


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis/frontier' / m).read_bytes()).hexdigest() for m in MODULES}


def train_worlds(sealed=SEALED_SEED):
    return [(f'Ma-{i}', 'Ma', h(STUDY, sealed, 'Ma', i), False) for i in range(K_TRAIN)]


def worlds(sealed=SEALED_SEED):
    """The held-out evaluation worlds: [(world key, family, seed, null)] in a fixed order."""
    out = []
    for fam in HELD_OUT:
        for i in range(WORLDS_PER_FAMILY):
            out.append((f'{fam}-{i}', fam, h(STUDY, sealed, fam, i), False))
        for i in range(NULLS_PER_FAMILY):
            out.append((f'{fam}-null{i}', fam, h(STUDY, sealed, fam, 'null', i), True))
    return out


def make_world(fam, seed, null, horizon):
    from genesis.frontier.world import PlantedWorld
    spec = FAMILIES[fam]
    return PlantedWorld(seed, problems=spec['problems'], horizon=horizon, sigma=spec['sigma'], null=null,
                        types=spec['types'])


def on_grid(cfg):
    from genesis.frontier import meta as MT
    return set(cfg) == set(MT.GRID) and all(cfg[k] in v for k, v in MT.GRID.items())


# --------------------------------------------------------------------------------------------- the repaired search

def suite_search(train=None, b_in=B, q_member=Q_MEMBER, pool=POOL, eta=ETA, rung=RUNG):
    """One halving bracket over configurations on the training suite. Returns the survivor and the record."""
    from genesis.frontier import meta as MT
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    train = train or train_worlds()
    records, sizes = {}, {}

    def factory(run_key):
        ms = []
        for i, (key, fam, seed, null) in enumerate(train):
            w = make_world(fam, seed, null, b_in)
            rec = records.setdefault(run_key, {}).setdefault(i, {})
            sizes[i] = len(w.problems())

            def verify(p, a, w=w, rec=rec):
                v = w.verify(p, a)
                rec[p] = max(rec.get(p, 0.0), v)
                return v
            ms.append(Manifest(w, verify, b_in, quantum=QUANTUM, description={'study': STUDY, 'member': key}))
        return ms

    def meta_verify(task, art):
        rec = records.get(art.get('run'))
        if not rec:
            return 0.0
        return sum(sum(rec.get(i, {}).values()) / sizes[i] for i in range(len(train))) / len(train)
    br = MT.halving_bracket(pool, eta, rung)
    q = q_member * len(train)
    dom = MT.SuiteMetaDomain({'T0': factory}, policies=('frontier',))
    params = {'pool': pool, 'eta': eta, 'rung': rung}
    e = Frontier(Manifest(dom, meta_verify, br['quanta'] * q + q - 1, quantum=q,
                          description={'study': STUDY, 'level': 'meta'}), 'halving', seed=0, policy_params=params)
    e.run()
    branches = []
    for bid, b in sorted(e.branches.items()):
        key = MT.run_key('T0', b['direction'], b['seed'])
        engines, ks = dom._runs[key]
        branches.append({'branch': bid, 'params': dict(b['direction']['params']), 't': b['t'],
                         'value': meta_verify('T0', {'run': key}), 'member_spent': [g.spent for g in engines]})
    top = max(branches, key=lambda r: (r['t'], -r['branch']))
    cum, stages_seen = 0, []
    for n, r in br['stages']:
        cum += r
        stages_seen.append([n, sum(1 for x in branches if x['t'] >= min(cum, br['final'] - 1) * q
                                   or x is top)])
    as_scheduled = (len(branches) == pool and all(a == b for a, b in stages_seen)
                    and all(s + QUANTUM > b_in for s in top['member_spent']))
    return {'survivor': top['params'], 'survivor_value': top['value'], 'branches': branches,
            'stages': br['stages'], 'stages_seen': stages_seen, 'as_scheduled': as_scheduled,
            'c_search': dom.inner_compute(), 'outer_spent': e.spent}


def guard(survivor, train=None, budget=B):
    """The kernel's guard: the survivor and the defaults once more on every training world, fresh seeds."""
    from genesis.frontier import meta as MT
    train = train or train_worlds()
    out = {'survivor': [], 'defaults': []}
    for which, cfg in (('survivor', survivor), ('defaults', MT.DEFAULT)):
        for i, (key, fam, seed, null) in enumerate(train):
            r = run_one(fam, seed, null, 'guard-' + which, h(STUDY, 'guard', i), cfg, budget)
            out[which].append(r)
    means = {k: statistics.mean(r['value'] for r in v) for k, v in out.items()}
    return {'runs': out, 'means': means, 'promote': means['survivor'] > means['defaults'],
            'c_guard': sum(r['spent'] for v in out.values() for r in v)}


# --------------------------------------------------------------------------------------------- F6's procedure

def f6_search(world=None, b_in=F6_B_IN, budget=F6_META_BUDGET, quantum=F6_META_QUANTUM):
    """F6's meta-search (B20_R163 `meta_search`), unchanged, on the first training world."""
    from genesis.frontier import meta as MT
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    key, fam, seed, null = world or train_worlds()[0]
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
            'c_meta': dom.inner_compute(), 'opened': len(e.branches), 'outer_spent': e.spent}


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


def extra_budget(c, n_worlds):
    return int(c / n_worlds) // QUANTUM * QUANTUM


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def two_sided_label(r, better, worse):
    return (better if r['p'] < ALPHA and r['mean'] >= MATERIAL else
            worse if r['p'] < ALPHA and r['mean'] <= -MATERIAL else 'TIE')


def analyse(rows, ws=None):
    ws = ws or worlds()
    keys = [k for k, fam, s, null in ws if not null]
    val = {a: [rows[(k, a)]['value'] for k in keys] for a in ARMS}
    diff = lambda a, b: [x - y for x, y in zip(val[a], val[b])]           # noqa: E731
    p1 = wilcoxon(diff('PK', 'D0'), 'greater')
    p1['label'] = 'CONFIG_TRANSFERS' if p1['p'] < ALPHA and p1['mean'] >= MATERIAL else 'NOT_SHOWN'
    p1['ahead'] = sum(1 for x in diff('PK', 'D0') if x > 0)
    s1 = wilcoxon(diff('PK', 'D24'), 'greater')
    s1['label'] = 'PAYS' if s1['p'] < ALPHA and s1['mean'] >= MATERIAL else 'DOES_NOT_PAY'
    s2 = wilcoxon(diff('PK', 'P1'), 'two-sided')
    s2['label'] = two_sided_label(s2, 'REPAIR_BETTER', 'REPAIR_WORSE')
    s3 = wilcoxon(diff('P1', 'D0'), 'two-sided')
    s3['label'] = two_sided_label(s3, 'CONFIG_BETTER', 'CONFIG_WORSE')
    s4 = wilcoxon(diff('D24', 'D0'), 'greater')
    fams = sorted({f for k, f, s, null in ws})
    s5 = {fam: {a: statistics.mean(rows[(k, a)]['value'] for k, f, s, null in ws if f == fam and not null)
                for a in ARMS} for fam in fams}
    g, s = p1['mean'], s4['mean']
    s7 = len(keys) * s / g if g >= MATERIAL and s > 0 else None
    return {'P1': p1, 'S1': s1, 'S2': s2, 'S3': s3, 'S4': s4, 'S5': s5, 'S7_break_even_worlds': s7,
            'means': {a: statistics.mean(val[a]) for a in ARMS}}


def verdict(valid, res, nothing_promoted):
    if not valid:
        return 'INVALID'
    v = res['P1']['label']
    return v + (' (NOTHING_PROMOTED)' if nothing_promoted and v == 'NOT_SHOWN' else '')


def main(argv=None, registered=True, train=None, world_list=None, search_kw=None, f6_kw=None, budget=B):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    from genesis.frontier import meta as MT
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered and out != OUTPUT.resolve():
        raise SystemExit('the registered output is evidence/meta_repaired_b20r175')
    if registered and pins() != PINNED:
        raise SystemExit('the engine modules differ from the preregistered pins')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    train = train or train_worlds()
    spath = out / 'search.json'
    if spath.exists():
        ms = json.loads(spath.read_text())
    else:
        ms = suite_search(train, **(search_kw or {}))
        gd = guard(ms['survivor'], train, budget)
        ms['guard'] = gd
        ms['promoted'] = dict(ms['survivor']) if gd['promote'] else dict(MT.DEFAULT)
        ms['nothing_promoted'] = not gd['promote']
        ms['c_k'] = ms['c_search'] + gd['c_guard']
        spath.write_text(json.dumps(ms, indent=1, sort_keys=True) + '\n')
    fpath = out / 'f6.json'
    if fpath.exists():
        f6 = json.loads(fpath.read_text())
    else:
        f6 = f6_search(train[0], **(f6_kw or {}))
        fpath.write_text(json.dumps(f6, indent=1, sort_keys=True) + '\n')
    ws = world_list if world_list is not None else worlds()
    n_eval = sum(1 for w in ws if not w[3])
    extra = extra_budget(ms['c_k'], n_eval)
    plan = {'PK': (ms['promoted'], budget), 'P1': (f6['promoted'], budget), 'D0': (MT.DEFAULT, budget),
            'D24': (MT.DEFAULT, budget + extra)}
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
    guard_runs = [r for v in ms['guard']['runs'].values() for r in v]
    spent_ok = all(r['spent'] >= r['budget'] - QUANTUM - 1 for r in list(rows.values()) + guard_runs)
    pins_ok = (not registered) or pins() == PINNED
    grid_ok = on_grid(ms['promoted']) and on_grid(f6['promoted'])
    valid = nulls_ok and spent_ok and pins_ok and grid_ok and ms['as_scheduled']
    res = analyse(rows, ws)
    v = verdict(valid, res, ms['nothing_promoted'])
    changed = {k: [MT.DEFAULT[k], ms['promoted'][k]] for k in MT.DEFAULT if ms['promoted'].get(k) != MT.DEFAULT[k]}
    summary = {'study': STUDY, 'schema': 'genesis-b20r175-meta-repaired-v1', 'verdict': v, 'valid': valid,
               'nulls_ok': nulls_ok, 'spent_ok': spent_ok, 'pins_ok': pins_ok, 'grid_ok': grid_ok,
               'as_scheduled': ms['as_scheduled'], 'results': res,
               'S6': {'promoted': ms['promoted'], 'changed_from_defaults': changed, 'survivor': ms['survivor'],
                      'survivor_search_value': ms['survivor_value'], 'guard_means': ms['guard']['means'],
                      'nothing_promoted': ms['nothing_promoted'], 'c_search': ms['c_search'],
                      'c_guard': ms['guard']['c_guard'], 'c_k': ms['c_k'], 'extra_budget_per_world': extra,
                      'stages': ms['stages'], 'stages_seen': ms['stages_seen'],
                      'f6_promoted': f6['promoted'], 'f6_c_meta': f6['c_meta'], 'f6_opened': f6['opened']},
               'worlds': [list(x) for x in ws], 'train': [list(x) for x in train], 'budget': budget,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; a calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('worlds', 'train', 'results')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
