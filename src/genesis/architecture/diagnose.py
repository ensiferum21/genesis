"""The limitation scientist: the loss ladder by oracle substitution (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §4; ARA-1).

For a workflow AG on a view, everything fitted on dev_a and measured on dev_b:

| Term | Stand-in |
|---|---|
| O | each dev_b instance's best option, chosen on half of the exact repeats and valued on the other half |
| C_rich_flex | a flexible policy (threshold with one or two cuts, oblique, tree or knn) over a rich observation battery (every primitive aggregate of the sense language, the current senses and seeded random senses), chosen by 2-fold cross-validation on dev_a |
| C_cur_flex | the same flexible stand-in over the current features only |
| C_cur | the best member of the current policy family over the current features, by exhaustive search with exact evaluation |
| S_exact | the incumbent's own search procedure and parameters, rerun with exact evaluation |
| A | the incumbent as it is |

"Exact evaluation" is paired evaluation with EXACT_REPEATS repeats, drawn once per split and shared by every
stand-in (the draws are charged once, through the view). Every policy is valued on dev_b's second half of the
repeats, the same draws for every term, so an instance's shared noise cancels in every difference. The ladder:

    information    = C_rich_flex - C_cur_flex   -> Sense and Features nodes
    expressiveness = C_cur_flex - C_cur         -> the Policy node
    search         = C_cur - S_exact            -> the Search node
    evaluation     = S_exact - A                -> the Evaluator node
    residual       = O - C_rich_flex            -> not reachable with this sense language

Each term has a bootstrap interval over dev_b's instances. The diagnosis lists the terms whose lower bound exceeds
MATERIAL (a fraction of the attainable range, O minus the best single option), largest first; NONE when there are
none; AMBIGUOUS when the top two are not separated (their difference's interval contains zero). The stand-ins are
generic and declared per role; none is indexed by a defect.
"""
import math
import random

from ..common import digest
from ..senses import graph as SG
from . import graph as G
from . import policies as PO

EXACT_REPEATS = 6
MATERIAL = 0.05
BOOT = 1000
BATTERY_RANDOM = 12
TERMS = ('information', 'expressiveness', 'search', 'evaluation', 'residual')
LOCATE = {'information': ('Sense', 'Features'), 'expressiveness': ('Policy',), 'search': ('Search',),
          'evaluation': ('Evaluator',), 'residual': ()}


def battery(seed, n_random=None, edge_aggs=('mean', 'sd')):
    """The rich observation battery: every primitive aggregate (vertex primitives by mean, sd, cv, max, q90; edge
    primitives by `edge_aggs`, mean and sd by default; n and m) and `n_random` (BATTERY_RANDOM) seeded random senses.
    The defaults give ARA-1's battery exactly."""
    n_random = BATTERY_RANDOM if n_random is None else n_random
    out = [[f'{a}_n', p] for p in SG.N_PRIM if p != 'one' for a in ('mean', 'sd', 'cv', 'max', 'q90')]
    out += [[f'{a}_e', p] for p in SG.E_PRIM for a in edge_aggs]
    out += ['n', 'm']
    rng = random.Random(f'battery|{seed}')
    target = 36 + 2 + n_random + 6 + 3 * (len(edge_aggs) - 2)    # ARA-1's count with the defaults
    while len(out) < target:
        s = SG.random_sense(rng)
        if s not in out:
            out.append(s)
    return out


class Lab:
    """The exact tables of a view's dev splits, drawn once (charged through the view), and the current features."""

    def __init__(self, view, seed, draws=None, exact_repeats=None):
        self.view, self.K, self.seed = view, view.K, seed
        reps = EXACT_REPEATS if exact_repeats is None else int(exact_repeats)
        self.draws = {} if draws is None else draws
        self.meter = PO.Meter()
        self.cells = {}
        scheme = {'op': 'paired', 'repeats': reps}
        for split in ('dev_a', 'dev_b'):
            ev = PO.Evaluation(view, split, scheme, self.meter, 'diagnosis', self.draws)
            n = view.size(split)
            self.cells[split] = [[[ev.draw_cell(i, c, r) for r in range(reps)] for c in range(self.K)]
                                 for i in range(n)]
        h = reps // 2
        self.table_a = [[sum(x) / len(x) for x in row] for row in self.cells['dev_a']]
        self.choose_b = [[sum(x[:h]) / h for x in row] for row in self.cells['dev_b']]
        self.value_b = [[sum(x[h:]) / (reps - h) for x in row] for row in self.cells['dev_b']]
        self.sense_cache = {}
        self.sense_units = 0.0

    def columns(self, exprs, split):
        gs = self.view.graphs(split)
        out = []
        for e in exprs:
            self.sense_units += SG.size(e) * len(gs) * G.SENSE_UNIT
            out.append(G.column(e, gs, self.sense_cache))
        return [[c[i] for c in out] for i in range(len(gs))]

    def per_instance(self, choices):
        return [self.value_b[i][c] for i, c in enumerate(choices)]


class _Table:
    """An Evaluation-like scorer over the exact table of dev_a (no further draws)."""

    def __init__(self, table, idx=None):
        self.t, self.n = table, len(table)

    def value(self, assign, idx=None):
        idx = range(self.n) if idx is None else list(idx)
        idx = list(idx)
        return sum(self.t[i][assign[i]] for i in idx) / max(1, len(idx))

    def table(self, K):
        return self.t


def fit_exact(family, fixed, X, table, K, seed):
    return PO.fit(family, fixed, X, K, _Table(table), 'exhaustive', {}, seed)


def flexible(X, table, K, seed, force=0):
    """The flexible stand-in: among threshold (1 and 2 cuts), tree and knn, the one with the best 2-fold
    cross-validated value on dev_a, refitted on all of dev_a. Returns (family, fixed, params)."""
    n = len(X)
    cols = preselect(X, table, K, seed, force=force)
    X = [[r[j] for j in cols] for r in X]
    folds = [list(range(0, n, 2)), list(range(1, n, 2))]
    cands = [('threshold', {'n_cuts': 1}), ('threshold', {'n_cuts': 2}), ('oblique', {}), ('tree', {}), ('knn', {})]
    best = None
    for fam, fixed in cands:
        cv = 0.0
        for k in (0, 1):
            tr, te = folds[k], folds[1 - k]
            p = fit_exact(fam, fixed, [X[i] for i in tr], [table[i] for i in tr], K, seed)
            ch = PO.apply(fam, p, [X[i] for i in te]) if p is not None else [0] * len(te)
            cv += sum(table[i][c] for i, c in zip(te, ch))
        if best is None or cv > best[0] + 1e-12:
            best = (cv, fam, fixed)
    _, fam, fixed = best
    return fam, fixed, fit_exact(fam, fixed, X, table, K, seed), cols


def preselect(X, table, K, seed, keep=6, force=0):
    """The first `force` features (the current ones), plus, when more remain, the `keep` others whose best
    single-cut stump is most valuable on dev_a (ties by index): the flexible families stay tractable over a rich
    battery, and the rich stand-in always contains the current features."""
    d = len(X[0]) if X else 0
    if d <= keep + force:
        return list(range(d))
    score = []
    for j in range(force, d):
        col = [[r[j]] for r in X]
        p = fit_exact('threshold', {'n_cuts': 1}, col, table, K, seed)
        ch = PO.apply('threshold', p, col)
        score.append((-sum(table[i][c] for i, c in enumerate(ch)), j))
    return list(range(force)) + sorted(j for _, j in sorted(score)[:keep])


def _boot(diffs, seed):
    n = len(diffs)
    rng = random.Random(f'boot|{seed}')
    ms = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOT))
    return ms[int(0.025 * BOOT)], ms[int(0.975 * BOOT) - 1]


def current_senses(ag):
    feat = [n for n, nd in ag['nodes'].items() if nd['role'] == 'Features'][0]
    memo = {}
    return [G.sense_expr(ag, s, memo) for s in G.inputs_of(ag, feat)['senses']]


def ladder(view, ag, seed=0, lab=None, draws=None, config=None):
    """The loss ladder of `ag` on the view: {terms: {term: {mean, lo, hi}}, values, range, material, diagnosis,
    located: [role, ...], units}. `config` (ARA's own settings, `ara.DEFAULT_CONFIG` keys) may change the exact
    repeats, the battery and the material fraction; without it the ladder is ARA-1's."""
    config = config or {}
    lab = lab or Lab(view, seed, draws, config.get('exact_repeats'))
    K = lab.K
    pol = [nd for nd in ag['nodes'].values() if nd['role'] == 'Policy'][0]
    srch = [nd for nd in ag['nodes'].values() if nd['role'] == 'Search'][0]
    cur = current_senses(ag)
    Xa, Xb = lab.columns(cur, 'dev_a'), lab.columns(cur, 'dev_b')
    bat = battery(seed, config.get('battery_random'), tuple(config.get('edge_aggs', ('mean', 'sd'))))
    rich = cur + [b for b in bat if b not in cur]
    Ra, Rb = lab.columns(rich, 'dev_a'), lab.columns(rich, 'dev_b')
    nb = len(Xb)
    vals = {}
    # O: chosen on the first half of the repeats, valued on the second
    vals['O'] = [lab.value_b[i][max(range(K), key=lambda c: (lab.choose_b[i][c], -c))] for i in range(nb)]
    fam, fixed, p, cols = flexible(Ra, lab.table_a, K, seed, force=len(cur))
    sub = [[r[j] for j in cols] for r in Rb]
    vals['C_rich_flex'] = lab.per_instance(PO.apply(fam, p, sub) if p is not None else [0] * nb)
    fam2, fixed2, p2, cols2 = flexible(Xa, lab.table_a, K, seed)
    sub2 = [[r[j] for j in cols2] for r in Xb]
    vals['C_cur_flex'] = lab.per_instance(PO.apply(fam2, p2, sub2) if p2 is not None else [0] * nb)
    rich_used = [rich[j] for j in cols]
    cfixed = dict(pol['params'])
    if pol['op'] == 'knn':
        cfixed.setdefault('k', 5)
    pc = fit_exact(pol['op'], cfixed, Xa, lab.table_a, K, seed)
    vals['C_cur'] = lab.per_instance(PO.apply(pol['op'], pc, Xb) if pc is not None else [0] * nb)
    # S_exact: the incumbent's search procedure, scored by the exact table of dev_a
    ps = PO.fit(pol['op'], cfixed, Xa, K, _Table(lab.table_a), srch['op'], srch['params'],
                int(digest({'ag': G.ag_id(ag), 'seed': seed})[:12], 16))
    vals['S_exact'] = lab.per_instance(PO.apply(pol['op'], ps, Xb) if ps is not None else [0] * nb)
    # A: the incumbent as it is (its draws shared with the lab's, so a cell is never paid twice)
    run = G.execute(ag, view, 'dev_a', seed=seed, sense_cache=lab.sense_cache, draws=lab.draws)
    vals['A'] = lab.per_instance(G.choose(run['policy'], view.graphs('dev_b'), lab.sense_cache))
    single = max(range(K), key=lambda c: (sum(lab.value_b[i][c] for i in range(nb)), -c))
    rdiff = [vals['O'][i] - lab.value_b[i][single] for i in range(nb)]
    rng_ = sum(rdiff) / nb
    rlo, _ = _boot(rdiff, f'{seed}|range')
    material = config.get('material', MATERIAL) * rng_ if rlo > 0 else math.inf     # no range shown: nothing is
    pairs = {'information': ('C_rich_flex', 'C_cur_flex'), 'expressiveness': ('C_cur_flex', 'C_cur'),
             'search': ('C_cur', 'S_exact'), 'evaluation': ('S_exact', 'A'), 'residual': ('O', 'C_rich_flex')}
    terms, diffs = {}, {}
    for t, (a, b) in pairs.items():
        d = [x - y for x, y in zip(vals[a], vals[b])]
        lo, hi = _boot(d, f'{seed}|{t}')
        terms[t] = {'mean': sum(d) / nb, 'lo': lo, 'hi': hi}
        diffs[t] = d
    sig = sorted((t for t in TERMS if t != 'residual' and terms[t]['lo'] > material),
                 key=lambda t: -terms[t]['mean'])
    if not sig:
        diagnosis = 'NONE'
    elif len(sig) > 1:
        d = [x - y for x, y in zip(diffs[sig[0]], diffs[sig[1]])]
        lo, _ = _boot(d, f'{seed}|amb')
        diagnosis = 'AMBIGUOUS' if lo <= 0 else sig[0]
    else:
        diagnosis = sig[0]
    return {'terms': terms, 'values': {k: sum(v) / nb for k, v in vals.items()}, 'range': rng_, 'range_lo': rlo,
            'material': material, 'significant': sig, 'diagnosis': diagnosis,
            'located': list(LOCATE[sig[0]]) if sig else [], 'incumbent_run': run, 'rich_used': rich_used,
            'units_view': view.units, 'sense_units': lab.sense_units}


__all__ = ['EXACT_REPEATS', 'MATERIAL', 'TERMS', 'LOCATE', 'battery', 'Lab', 'fit_exact', 'flexible', 'ladder',
           'current_senses']
