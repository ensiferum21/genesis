"""Transformation contracts for the Problem Compiler (Genesis Ω contract §6, §16.4).

Every transformation from a problem to an engine's form DECLARES what it preserves:
  * `exact`: the objective of every assignment is an affine function of the transformed objective (checked: on
    sampled assignments, the residual of that affine relation is zero);
  * `approximate`: it is not, and the answers it yields are only ever trusted after the original checker re-scores
    them in the original problem.
`check_maxcut(qubo, n1, E, declared, samples, rng)` tests a max-cut reduction's declaration on random assignments
(and all of them when n is small): for an exact reduction, 4 f(x) + 2 cut(side(x)) is the same constant for every
assignment, with side(x) the cut that puts the reference vertex on side 1 and x_i = 1 on its side. A reduction that
claims `exact` and fails is REJECTED; one declared `approximate` is CATEGORISED as such (its deviation reported).
"""
from itertools import product

from . import bqp as Q


def side_of(x, n1):
    return [1 if xi else 0 for xi in x] + [1]


def check_maxcut(qubo, n1, E, declared, samples=200, rng=None):
    import random
    rng = rng or random.Random(0)
    n = qubo['n']
    if n1 != n + 1:
        return {'verdict': 'REJECTED', 'reason': 'the reduction must add exactly one reference vertex'}
    xs = list(product((0, 1), repeat=n)) if n <= 12 else [[rng.randint(0, 1) for _ in range(n)] for _ in range(samples)]
    vals = set()
    worst = 0.0
    first = None
    for x in xs:
        side = side_of(x, n1)
        if Q.from_cut(side, n) != list(x):
            return {'verdict': 'REJECTED', 'reason': 'the decoder does not invert the encoding'}
        cut = sum(w for u, v, w in E if side[u] != side[v])
        k = 4 * Q.evaluate(qubo, x)[0] + 2 * cut
        first = k if first is None else first
        worst = max(worst, abs(k - first))
        vals.add(round(k, 9))
    exact = len(vals) == 1
    if declared == 'exact':
        return {'verdict': 'EXACT' if exact else 'REJECTED', 'deviation': worst,
                'reason': '' if exact else 'claimed exact; 4f + 2cut is not constant'}
    return {'verdict': 'APPROXIMATE', 'deviation': worst, 'reason': 'declared approximate: answers re-checked in the '
                                                                     'original problem'}
