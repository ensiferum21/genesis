"""The libraries an Architecture Graph runs: policy families, evaluator schemes and search procedures (ARA-1).

A choice workflow maps each instance to one of K options. Its parts, each a role in `graph.LIB`:
  * **Policy families** (`FAMILIES`, ordered by flexibility): `global` (one option for every instance), `threshold`
    (one feature, `n_cuts` cut points, an option per interval), `oblique` (one cut on a + s * b over two
    standardised features, s from OBLIQUE_SCALES), `tree` (a depth-2 axis-aligned tree), `knn`
    (nearest neighbours over standardised features, labelled by the evaluator). A fitted policy is JSON:
    {family, senses, params}, so it can be applied to new graphs by anyone holding the sense language.
  * **Evaluator schemes**: every call `view.evaluate(split, i, c, r)` costs one unit. `independent` draws a fresh
    repeat index for every call, so noise shared by an instance's options does not cancel between candidates;
    `paired` evaluates every option of an instance with the same repeat indices 0..R-1 and caches them, so the
    shared noise cancels and a candidate already covered by the table costs nothing more.
  * **Search procedures**: `hill_climb` (from a start, one coordinate at a time, strict improvement), `restarts`
    (hill climbs from random starts, the steps divided between them), `exhaustive` (every candidate of a
    deterministic grid, while units last). Every search stops when its node's units run out and returns the best
    candidate found so far.
Everything is deterministic given the seed: the view's draws are a function of (split, i, c, r).
"""
import itertools
import math
import random

FAMILIES = ('global', 'threshold', 'oblique', 'tree', 'knn')
OBLIQUE_SCALES = (-3.0, -2.0, -1.5, -1.0, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
SCHEMES = ('independent', 'paired')
SEARCHES = ('hill_climb', 'restarts', 'exhaustive')
KNN_KS = (1, 3, 5, 9)
QUANTILES = tuple(i / 10 for i in range(1, 10))


class Exhausted(Exception):
    """A node's units ran out."""


class Meter:
    """Units charged per node, against per-node caps."""

    def __init__(self, caps=None):
        self.caps = dict(caps or {})
        self.charges = {}

    def charge(self, node, units):
        new = self.charges.get(node, 0.0) + units
        cap = self.caps.get(node)
        if cap is not None and new > cap + 1e-9:
            raise Exhausted(node)
        self.charges[node] = new

    def left(self, node):
        cap = self.caps.get(node)
        return math.inf if cap is None else cap - self.charges.get(node, 0.0)

    @property
    def total(self):
        return sum(self.charges.values())


# ------------------------------------------------------------------------------------------------ evaluation

class Evaluation:
    """Scores assignments (one option per instance of `split`) with the view's noisy evaluator under a scheme;
    every new call is charged to `node` on `meter`."""

    def __init__(self, view, split, scheme, meter, node, draws=None):
        self.view, self.split, self.meter, self.node = view, split, meter, node
        self.kind, self.repeats = scheme['op'], int(scheme['repeats'])
        self.n = view.size(split)
        self.cache = {}
        self.fresh = 0
        self.draws = draws

    def draw_cell(self, i, c, r):
        """Each cell is charged to the node once per Evaluation (so charges do not depend on any outside cache);
        a value already drawn from the view under the same (split, i, c, r) is reused from `draws`, which saves the
        view's units, never the node's charge."""
        key = (i, c, r)
        if key not in self.cache:
            self.meter.charge(self.node, 1)
            full = (self.split, i, c, r)
            if self.draws is not None and full in self.draws:
                self.cache[key] = self.draws[full]
            else:
                self.cache[key] = self.view.evaluate(self.split, i, c, r)
                if self.draws is not None:
                    self.draws[full] = self.cache[key]
        return self.cache[key]

    def cell(self, i, c):
        """The mean of R draws of option c on instance i: under `paired` the repeat indices are 0..R-1 (shared by
        the options); under `independent` they are fresh."""
        if self.kind == 'paired':
            return sum(self.draw_cell(i, c, r) for r in range(self.repeats)) / self.repeats
        rs = range(self.fresh, self.fresh + self.repeats)
        self.fresh += self.repeats
        return sum(self.draw_cell(i, c, r) for r in rs) / self.repeats

    def value(self, assign, idx=None):
        idx = range(self.n) if idx is None else idx
        idx = list(idx)
        return sum(self.cell(i, assign[i]) for i in idx) / max(1, len(idx))

    def table(self, K):
        """[instance][option] cell means (under `independent` each cell is drawn once and kept)."""
        rows = []
        for i in range(self.n):
            rows.append([self.cell(i, c) for c in range(K)])
        return rows


# ------------------------------------------------------------------------------------------------ policies

def standardise(X):
    if not X:
        return [], [], []
    d = len(X[0])
    mu = [sum(r[j] for r in X) / len(X) for j in range(d)]
    sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in X) / len(X)) or 1.0 for j in range(d)]
    return [[(r[j] - mu[j]) / sd[j] for j in range(d)] for r in X], mu, sd


def apply(family, params, X):
    """The option chosen for every row of X."""
    if family == 'global':
        return [params['choice']] * len(X)
    if family == 'threshold':
        f, cuts, ch = params['f'], params['cuts'], params['choices']
        return [ch[sum(r[f] > t for t in cuts)] for r in X]
    if family == 'oblique':
        a, b, sc, cut, ch = params['a'], params['b'], params['s'], params['cut'], params['choices']
        mu, sd = params['mu'], params['sd']
        return [ch[int((r[a] - mu[a]) / sd[a] + sc * (r[b] - mu[b]) / sd[b] > cut)] for r in X]
    if family == 'tree':
        f, t, lv = params['f'], params['t'], params['leaves']
        out = []
        for r in X:
            if r[f[0]] <= t[0]:
                out.append(lv[0] if r[f[1]] <= t[1] else lv[1])
            else:
                out.append(lv[2] if r[f[2]] <= t[2] else lv[3])
        return out
    if family == 'knn':
        mu, sd, k = params['mu'], params['sd'], params['k']
        Z = [[(r[j] - mu[j]) / sd[j] for j in range(len(mu))] for r in X]
        return [_knn_vote(z, params['X'], params['y'], k) for z in Z]
    raise ValueError(f'unknown family {family!r}')


def _knn_vote(z, TX, Ty, k, skip=None):
    ds = sorted((sum((a - b) ** 2 for a, b in zip(z, x)), j) for j, x in enumerate(TX) if j != skip)
    votes = {}
    for d, j in ds[:k]:
        votes[Ty[j]] = votes.get(Ty[j], 0) + 1
    return min(votes, key=lambda c: (-votes[c], c)) if votes else 0


def quantile_cuts(X, f):
    vals = sorted(r[f] for r in X)
    if not vals:
        return [0.0]
    out = []
    for q in QUANTILES:
        v = vals[min(len(vals) - 1, int(q * len(vals)))]
        if v not in out:
            out.append(v)
    return out


def default_params(family, fixed, X, K):
    """The family's default (and the incumbent's default start)."""
    d = len(X[0]) if X else 1
    if family == 'global':
        return {'choice': 0}
    if family == 'threshold':
        n = int(fixed.get('n_cuts', 1))
        qc = quantile_cuts(X, 0) if X else [0.0]
        cuts = sorted(qc[min(len(qc) - 1, (j + 1) * len(qc) // (n + 1))] for j in range(n))
        return {'f': 0, 'cuts': cuts, 'choices': [0] * (n + 1)}
    if family == 'tree':
        qc = quantile_cuts(X, 0) if X else [0.0]
        c = qc[len(qc) // 2]
        return {'f': [0, min(1, d - 1), min(1, d - 1)], 't': [c, c, c], 'leaves': [0, 0, 0, 0]}
    if family == 'oblique':
        _, mu, sd = standardise(X)
        return {'a': 0, 'b': min(1, d - 1), 's': 1.0, 'cut': 0.0, 'choices': [0, 0], 'mu': mu, 'sd': sd}
    raise ValueError(family)


def random_params(family, fixed, X, K, rng):
    d = len(X[0]) if X else 1
    if family == 'global':
        return {'choice': rng.randrange(K)}
    if family == 'threshold':
        n = int(fixed.get('n_cuts', 1))
        f = rng.randrange(d)
        cuts = sorted(rng.choice(quantile_cuts(X, f)) for _ in range(n))
        return {'f': f, 'cuts': cuts, 'choices': [rng.randrange(K) for _ in range(n + 1)]}
    if family == 'tree':
        fs = [rng.randrange(d) for _ in range(3)]
        return {'f': fs, 't': [rng.choice(quantile_cuts(X, f)) for f in fs], 'leaves': [rng.randrange(K) for _ in range(4)]}
    if family == 'oblique':
        _, mu, sd = standardise(X)
        a = rng.randrange(d)
        b = rng.randrange(d)
        p = {'a': a, 'b': b, 's': rng.choice(OBLIQUE_SCALES), 'cut': 0.0, 'choices': [rng.randrange(K) for _ in range(2)],
             'mu': mu, 'sd': sd}
        p['cut'] = rng.choice(_oblique_cuts(X, p))
        return p
    raise ValueError(family)


def _oblique_cuts(X, p):
    vals = sorted((r[p['a']] - p['mu'][p['a']]) / p['sd'][p['a']] + p['s'] * (r[p['b']] - p['mu'][p['b']]) /
                  p['sd'][p['b']] for r in X)
    if not vals:
        return [0.0]
    out = []
    for q in QUANTILES:
        v = vals[min(len(vals) - 1, int(q * len(vals)))]
        if v not in out:
            out.append(v)
    return out


def neighbour(family, params, X, K, rng, step):
    """One coordinate changed: an option, a feature, or a cut moved by `step` times the feature's range."""
    d = len(X[0]) if X else 1
    p = {k: (list(v) if isinstance(v, list) else v) for k, v in params.items()}

    def moved(f, t):
        vals = [r[f] for r in X] or [0.0]
        span = (max(vals) - min(vals)) or 1.0
        return t + rng.choice((-1, 1)) * step * span
    if family == 'global':
        p['choice'] = rng.choice([c for c in range(K) if c != p['choice']] or [p['choice']])
        return p
    if family == 'threshold':
        what = rng.choice(('choice', 'cut', 'feature') if d > 1 else ('choice', 'cut'))
        if what == 'choice':
            j = rng.randrange(len(p['choices']))
            p['choices'][j] = rng.choice([c for c in range(K) if c != p['choices'][j]] or [p['choices'][j]])
        elif what == 'cut':
            j = rng.randrange(len(p['cuts']))
            p['cuts'][j] = moved(p['f'], p['cuts'][j])
            p['cuts'] = sorted(p['cuts'])
        else:
            p['f'] = rng.choice([f for f in range(d) if f != p['f']])
        return p
    if family == 'oblique':
        what = rng.choice(('choice', 'cut', 'scale', 'feature'))
        if what == 'choice':
            j = rng.randrange(2)
            p['choices'][j] = rng.choice([c for c in range(K) if c != p['choices'][j]] or [p['choices'][j]])
        elif what == 'cut':
            p['cut'] = p['cut'] + rng.choice((-1, 1)) * step * 4.0
        elif what == 'scale':
            p['s'] = rng.choice([x for x in OBLIQUE_SCALES if x != p['s']])
        else:
            p[rng.choice(('a', 'b'))] = rng.randrange(d)
        return p
    if family == 'tree':
        what = rng.choice(('leaf', 'cut', 'feature'))
        j = rng.randrange(4 if what == 'leaf' else 3)
        if what == 'leaf':
            p['leaves'][j] = rng.choice([c for c in range(K) if c != p['leaves'][j]] or [p['leaves'][j]])
        elif what == 'cut':
            p['t'][j] = moved(p['f'][j], p['t'][j])
        else:
            p['f'][j] = rng.randrange(d)
        return p
    raise ValueError(family)


def grid(family, fixed, X, K):
    """The exhaustive candidates, in a fixed order (for `tree`, the root split; sides are fitted greedily)."""
    d = len(X[0]) if X else 1
    if family == 'global':
        return [{'choice': c} for c in range(K)]
    if family == 'threshold':
        n = int(fixed.get('n_cuts', 1))
        out = []
        for f in range(d):
            for cuts in itertools.combinations(quantile_cuts(X, f), n):
                for ch in itertools.product(range(K), repeat=n + 1):
                    out.append({'f': f, 'cuts': list(cuts), 'choices': list(ch)})
        return out
    if family == 'oblique':
        _, mu, sd = standardise(X)
        out = []
        for a, b in itertools.combinations(range(d), 2):
            for sc in OBLIQUE_SCALES:
                base = {'a': a, 'b': b, 's': sc, 'mu': mu, 'sd': sd}
                for cut in _oblique_cuts(X, dict(base, cut=0.0)):
                    for ch in itertools.product(range(K), repeat=2):
                        out.append(dict(base, cut=cut, choices=list(ch)))
        return out
    raise ValueError(family)


# ------------------------------------------------------------------------------------------------ search

REQUIRED = {'global': ('choice',), 'threshold': ('f', 'cuts', 'choices'),
            'oblique': ('a', 'b', 's', 'cut', 'choices', 'mu', 'sd'), 'tree': ('f', 't', 'leaves')}


def valid_start(family, fixed, start, d, K):
    """Whether a configured start is a member of this family (a start written for another family, or for another
    number of cuts, is not used)."""
    if not isinstance(start, dict) or family not in REQUIRED or any(k not in start for k in REQUIRED[family]):
        return False
    if family == 'threshold':
        n = int(fixed.get('n_cuts', 1))
        return (len(start['cuts']) == n and len(start['choices']) == n + 1 and 0 <= start['f'] < d and
                all(0 <= c < K for c in start['choices']))
    if family == 'global':
        return 0 <= start['choice'] < K
    return True

def fit(family, fixed, X, K, ev, search, sparams, seed):
    """The search procedure's fitted parameters for the family, scored by the Evaluation `ev` (which charges)."""
    rng = random.Random(seed)
    if family == 'knn':
        return _fit_knn(fixed, X, K, ev)
    best = {'params': None, 'value': -math.inf}

    def consider(p):
        v = ev.value(apply(family, p, X))
        if v > best['value']:
            best['params'], best['value'] = p, v
        return v
    try:
        if search == 'exhaustive':
            if family == 'tree':
                _exhaustive_tree(fixed, X, K, ev, best)
            else:
                for p in grid(family, fixed, X, K):
                    consider(p)
        else:
            k = int(sparams.get('k', 4)) if search == 'restarts' else 1
            steps = int(sparams.get('steps', 60))
            step = float(sparams.get('step', 0.1))
            for s in range(k):
                if search == 'restarts':
                    cur = random_params(family, fixed, X, K, rng)
                else:
                    cur = sparams.get('start')
                    if not valid_start(family, fixed, cur, len(X[0]) if X else 1, K):
                        cur = default_params(family, fixed, X, K)
                    cur = {kk: (list(v) if isinstance(v, list) else v) for kk, v in cur.items()}
                cv = consider(cur)
                for _ in range(max(1, steps // k)):
                    nxt = neighbour(family, cur, X, K, rng, step)
                    nv = consider(nxt)
                    if nv > cv:
                        cur, cv = nxt, nv
    except Exhausted:
        pass
    if best['params'] is None:
        best['params'] = default_params(family, fixed, X, K) if family != 'knn' else None
    return best['params']


def _exhaustive_tree(fixed, X, K, ev, best):
    """Root split over every feature and cut; each side's split and leaves chosen by its own exhaustive search."""
    d = len(X[0]) if X else 1
    for f0 in range(d):
        for t0 in quantile_cuts(X, f0):
            left = [i for i, r in enumerate(X) if r[f0] <= t0]
            right = [i for i, r in enumerate(X) if r[f0] > t0]
            sides = []
            for idx in (left, right):
                sb = (-math.inf, (0, t0, 0, 0))
                for f in range(d):
                    for t in quantile_cuts(X, f):
                        for a, b in itertools.product(range(K), repeat=2):
                            assign = [a if r[f] <= t else b for r in X]
                            v = ev.value(assign, idx) if idx else 0.0
                            if v > sb[0]:
                                sb = (v, (f, t, a, b))
                sides.append(sb[1])
            p = {'f': [f0, sides[0][0], sides[1][0]], 't': [t0, sides[0][1], sides[1][1]],
                 'leaves': [sides[0][2], sides[0][3], sides[1][2], sides[1][3]]}
            v = ev.value(apply('tree', p, X))
            if v > best['value']:
                best['params'], best['value'] = p, v


def _fit_knn(fixed, X, K, ev):
    """Labels: each training instance's best option by the evaluator's table; k chosen by leave-one-out value."""
    try:
        T = ev.table(K)
    except Exhausted:
        return None
    Z, mu, sd = standardise(X)
    y = [max(range(K), key=lambda c: (T[i][c], -c)) for i in range(len(X))]
    ks = [int(fixed['k'])] if 'k' in fixed else list(KNN_KS)
    best = None
    for k in ks:
        v = sum(T[i][_knn_vote(Z[i], Z, y, k, skip=i)] for i in range(len(X))) / max(1, len(X))
        if best is None or v > best[0]:
            best = (v, k)
    return {'X': Z, 'y': y, 'mu': mu, 'sd': sd, 'k': best[1]}


__all__ = ['FAMILIES', 'OBLIQUE_SCALES', 'SCHEMES', 'SEARCHES', 'Exhausted', 'Meter', 'Evaluation', 'apply', 'standardise',
           'quantile_cuts', 'default_params', 'random_params', 'neighbour', 'grid', 'fit']
