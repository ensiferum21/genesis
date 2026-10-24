"""Per-pair instruments as programs (B20_R130; Genesis Ω, Ω1): what one experiment measures about a pair.

An INSTRUMENT reads the data of one experiment do(t) (and the observational reference regime) and reports, for a
neighbour j, one outcome from a finite alphabet. B20_R129's instrument is `active2.classify` (direct / indirect /
none). Here an instrument is a program: a set of binary TESTS and a significance level; its outcome is the string of
the tests' results, so its alphabet has 2^k letters. What the outcomes predict under each explanation of the pair is
calibrated by simulation, as in `active3` (`calibrate`).

Tests for the pair (t, j) under do(t) (p-values, two-sided):
  * `dep`: X_j depends on X_t (Pearson);
  * `direct`: X_t's coefficient for X_j, with t's descendants adjacent to j held fixed (`active2.classify`'s test);
  * `gap`: the slope of X_j on X_t under do(t) differs from the observational slope (a back-door path or a hidden
    cause makes them differ);
  * `pgap`: the same, adjusting both slopes for j's other neighbours that t does not cause.
`classify` is the program ('dep', 'direct') at 0.01 read as none (0x), indirect (10) or direct (11); `R129` maps it.
"""
import itertools
import math

import numpy as np
from scipy import stats

from . import active as V1
from . import active3 as A3

TESTS = ('dep', 'direct', 'gap', 'pgap')
ALPHAS = (0.001, 0.01, 0.05)
R129 = {'tests': ['dep', 'direct'], 'alpha': 0.01}


def _slope(x, y):
    x = x - x.mean()
    y = y - y.mean()
    b = float(x @ y / (x @ x))
    r = y - b * x
    return b, math.sqrt(max(r @ r / max(1, len(x) - 2), 1e-300) / (x @ x))


def _coef(X, j, cols):
    A_ = X[:, cols] - X[:, cols].mean(axis=0)
    y = X[:, j] - X[:, j].mean()
    c, *_ = np.linalg.lstsq(A_, y, rcond=None)
    r = y - A_ @ c
    cov = (r @ r / max(1, len(y) - len(cols))) * np.linalg.pinv(A_.T @ A_)
    return float(c[0]), math.sqrt(max(cov[0, 0], 1e-300))


def pvalues(X0, Xt, t, adj, alpha_desc=0.01):
    """{j: {test: p}} for every j != t, from the reference regime X0 and the experiment's data Xt."""
    p = Xt.shape[1]
    desc = {k for k in range(p) if k != t and V1.dependent(Xt[:, t], Xt[:, k], alpha_desc)}
    out = {}
    for j in range(p):
        if j == t:
            continue
        d = {'dep': float(stats.pearsonr(Xt[:, t], Xt[:, j])[1])}
        med = sorted((desc & set(adj[j])) - {j})
        b, se = _coef(Xt, j, [t] + med)
        d['direct'] = float(2 * stats.norm.sf(abs(b / se)))
        bo, so = _slope(X0[:, t], X0[:, j])
        bi, si = _slope(Xt[:, t], Xt[:, j])
        d['gap'] = float(2 * stats.norm.sf(abs(bo - bi) / math.sqrt(so * so + si * si)))
        Z = sorted(set(adj[j]) - {t} - desc)
        bo, so = _coef(X0, j, [t] + Z)
        bi, si = _coef(Xt, j, [t] + Z)
        d['pgap'] = float(2 * stats.norm.sf(abs(bo - bi) / math.sqrt(so * so + si * si)))
        out[j] = d
    return out


def check(prog):
    if not isinstance(prog, dict) or set(prog) != {'tests', 'alpha'}:
        return "an instrument is {'tests': [...], 'alpha': a}"
    if (not prog['tests'] or list(prog['tests']) != [x for x in TESTS if x in prog['tests']]
            or len(set(prog['tests'])) != len(prog['tests'])):
        return f'tests: a non-empty subset of {TESTS}, in that order'
    if prog['alpha'] not in ALPHAS:
        return f'alpha: one of {ALPHAS}'
    return None


def space():
    """Every instrument of the language (15 test sets x 3 levels)."""
    out = []
    for k in range(1, len(TESTS) + 1):
        for ts in itertools.combinations(TESTS, k):
            for a in ALPHAS:
                out.append({'tests': list(ts), 'alpha': a})
    return out


def alphabet(prog):
    return tuple(''.join(x) for x in itertools.product('01', repeat=len(prog['tests'])))


def outcome(prog, pv):
    return ''.join('1' if pv[x] < prog['alpha'] else '0' for x in prog['tests'])


def lab(prog, table, p):
    """{t: {j: outcome}} for every pair, from {t: {j: {test: p}}}."""
    return {str(t): {str(j): outcome(prog, table[str(t)][str(j)]) for j in range(p) if j != t} for t in range(p)}


def calibrate(rows, prog):
    """The calibrated model for an instrument: rows [(prepared, truth, lab)], prepared as `active3.prepare`."""
    alpha_ = alphabet(prog)
    prior = {f'{m}|{f}': {h: 1.0 for h in A3.HYPS} for m in A3.MARKS for f in (0, 1)}
    pred = {r: {o: 1.0 for o in alpha_} for r in A3.RELATIONS}
    for prep, truth, lb in rows:
        for q, m in prep['marks'].items():
            h = A3.true_hypothesis(truth, q)
            prior[f"{m}|{int(q in prep['flagged'])}"][h] += 1
            i, j = A3.ends(q)
            for t, u in ((i, j), (j, i)):
                pred[A3.relation(h, t, q)][lb[str(t)][str(u)]] += 1
    norm = lambda d: {k: v / sum(d.values()) for k, v in d.items()}     # noqa: E731
    return {'prior': {k: norm(v) for k, v in prior.items()}, 'predict': {k: norm(v) for k, v in pred.items()},
            'alphabet': list(alpha_)}


class Domain(A3.CausalDomain):
    """`active3.CausalDomain` with an instrument's lab and alphabet."""

    def __init__(self, prepared, model, lab_):
        super().__init__(dict(prepared, lab=lab_), model)
        self._alpha = tuple(model['alphabet'])

    def outcomes(self):
        return self._alpha

    def predict(self, q, t):
        return [[self.model['predict'][A3.relation(h, t, q)][o] for o in self._alpha] for h in A3.HYPS]

    def execute(self, t):
        return {A3.key(t, int(j)): self.prep['lab'][str(t)][str(j)] for j in self.prep['adj'][str(t)]}
