"""Genesis's own acquisition language (Genesis Ω, P1 with a first piece of P3): rules for choosing experiments that
the system writes, mutates and judges itself.

A PROGRAM is {'agg': 'sum' | 'max', 'expr': TREE}. The score of an experiment is the aggregate (sum or max) of TREE
over the questions the experiment touches, TREE evaluated on that (question, experiment)'s features
(`design.FEATURES`: eig, dec, decf, ent, maxp, pf, seen, one). A TREE is
  * a feature name, or a constant from CONSTANTS;
  * [op, a, b] with op in BINARY: '+', '-', '*', 'max', 'min';
  * [op, a] with op in UNARY: 'sqrt' (of |a|), 'sq', 'inv1' (1 / (1 + |a|)).
Programs are data, checked by `check` (types, size at most MAX_SIZE nodes, depth at most MAX_DEPTH) and evaluated by
an interpreter (never by `eval`); the same program always makes the same choices.

The established acquisitions are points of this language: eig is {'agg': 'sum', 'expr': 'eig'}, decision improvement
{'agg': 'sum', 'expr': 'dec'}, the hybrid ['+', 'eig', ['*', lam, 'dec']], degree {'agg': 'sum', 'expr': 'one'}.
So an invented rule is judged against them inside the same language, and a search seeded with them starts from the
state of the art.

**Amendment (B20_R130):** the same language is used over other feature sets (`features=`), for example the pair
features of `causal.interpret`; with the default it is exactly B20_R129's.

Search operators (`ops()`, for `autonomy.feedback.steady_state_search`): `random` (a random tree of depth at most 3,
with `seeds` first when given), `mutate` (one of: replace a subtree, replace a leaf, change an operator, switch the
aggregate, wrap the tree in a new operator, hoist a subtree), `crossover` (a subtree of one parent grafted into the
other), `size` (number of nodes).
"""
import json

import numpy as np

from .design import FEATURES

CONSTANTS = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0)
BINARY = ('+', '-', '*', 'max', 'min')
UNARY = ('sqrt', 'sq', 'inv1')
AGGS = ('sum', 'max')
MAX_SIZE, MAX_DEPTH = 15, 4
MUTATIONS = ('subtree', 'leaf', 'op', 'agg', 'wrap', 'hoist')


def check(prog, features=FEATURES):
    """None, or why `prog` is not a program (over `features`; the acquisition features by default)."""
    if not isinstance(prog, dict) or set(prog) != {'agg', 'expr'} or prog['agg'] not in AGGS:
        return "a program is {'agg': 'sum' | 'max', 'expr': tree}"
    try:
        n, d = _shape(prog['expr'], features)
    except ValueError as e:
        return str(e)
    if n > MAX_SIZE or d > MAX_DEPTH:
        return f'at most {MAX_SIZE} nodes and depth {MAX_DEPTH}'
    return None


def _shape(t, features=FEATURES):
    if isinstance(t, str):
        if t not in features:
            raise ValueError(f'unknown feature {t!r}')
        return 1, 0
    if isinstance(t, float) and not isinstance(t, bool):
        if t not in CONSTANTS:
            raise ValueError(f'constants are {CONSTANTS}')
        return 1, 0
    if isinstance(t, list) and len(t) == 3 and t[0] in BINARY:
        (na, da), (nb, db) = _shape(t[1], features), _shape(t[2], features)
        return 1 + na + nb, 1 + max(da, db)
    if isinstance(t, list) and len(t) == 2 and t[0] in UNARY:
        n, d = _shape(t[1], features)
        return 1 + n, 1 + d
    raise ValueError(f'not a tree: {t!r}')


def size(prog, features=None):
    return _count(prog['expr'])


def _count(t):
    return 1 + sum(_count(x) for x in t[1:]) if isinstance(t, list) else 1


def text(prog):
    def s(t):
        if isinstance(t, (str, float)):
            return str(t)
        if len(t) == 2:
            return f'{t[0]}({s(t[1])})'
        return f'({s(t[1])} {t[0]} {s(t[2])})' if t[0] in '+-*' else f'{t[0]}({s(t[1])}, {s(t[2])})'
    return f"{prog['agg']} {s(prog['expr'])}"


def _ev(t, F):
    if isinstance(t, str):
        return F[t]
    if isinstance(t, float):
        return np.full(len(F['one']), t)
    if len(t) == 2:
        a = _ev(t[1], F)
        return {'sqrt': lambda: np.sqrt(np.abs(a)), 'sq': lambda: a * a, 'inv1': lambda: 1.0 / (1.0 + np.abs(a))}[t[0]]()
    a, b = _ev(t[1], F), _ev(t[2], F)
    if t[0] == '+':
        return a + b
    if t[0] == '-':
        return a - b
    if t[0] == '*':
        return a * b
    return np.maximum(a, b) if t[0] == 'max' else np.minimum(a, b)


def scores(prog, n_exp, pairs):
    """The score of each of n_exp experiments from pairs [(experiment index, features)]; an experiment touching no
    question scores 0."""
    out = np.zeros(n_exp)
    if not pairs:
        return out
    idx = np.array([k for k, _ in pairs])
    F = {f: np.array([x[f] for _, x in pairs], dtype=float) for f in FEATURES}
    v = np.nan_to_num(_ev(prog['expr'], F), nan=0.0, posinf=1e12, neginf=-1e12)
    if prog['agg'] == 'sum':
        np.add.at(out, idx, v)
    else:
        out[:] = -np.inf
        np.maximum.at(out, idx, v)
        out[np.isneginf(out)] = 0.0
    return out


# ------------------------------------------------------------------------------------------------- search operators

def _leaf(rng, features=FEATURES):
    return features[rng.randrange(len(features))] if rng.random() < 0.75 else CONSTANTS[rng.randrange(len(CONSTANTS))]


def random_tree(rng, depth=3, features=FEATURES):
    if depth == 0 or rng.random() < 0.3:
        return _leaf(rng, features)
    if rng.random() < 0.8:
        return [BINARY[rng.randrange(len(BINARY))], random_tree(rng, depth - 1, features),
                random_tree(rng, depth - 1, features)]
    return [UNARY[rng.randrange(len(UNARY))], random_tree(rng, depth - 1, features)]


def random_program(rng, features=FEATURES):
    while True:
        p = {'agg': AGGS[rng.randrange(2)] if rng.random() < 0.3 else 'sum', 'expr': random_tree(rng, 3, features)}
        if check(p, features) is None:
            return p


def _paths(t, path=()):
    yield path
    if isinstance(t, list):
        for k in range(1, len(t)):
            yield from _paths(t[k], path + (k,))


def _get(t, path):
    for k in path:
        t = t[k]
    return t


def _set(t, path, new):
    if not path:
        return new
    t = json.loads(json.dumps(t))
    node = t
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = new
    return t


def mutate(prog, rng, features=FEATURES):
    for _ in range(50):
        t = prog['expr']
        paths = list(_paths(t))
        path = paths[rng.randrange(len(paths))]
        node = _get(t, path)
        kind = MUTATIONS[rng.randrange(len(MUTATIONS))]
        agg = prog['agg']
        if kind == 'subtree':
            t = _set(t, path, random_tree(rng, 2, features))
        elif kind == 'leaf':
            leaves = [p for p in paths if not isinstance(_get(t, p), list)]
            t = _set(t, leaves[rng.randrange(len(leaves))], _leaf(rng, features))
        elif kind == 'op':
            if not isinstance(node, list):
                continue
            ops = BINARY if len(node) == 3 else UNARY
            t = _set(t, path, [ops[rng.randrange(len(ops))]] + node[1:])
        elif kind == 'agg':
            agg = 'max' if agg == 'sum' else 'sum'
        elif kind == 'wrap':
            if rng.random() < 0.8:
                t = _set(t, path, [BINARY[rng.randrange(len(BINARY))], node, _leaf(rng, features)])
            else:
                t = _set(t, path, [UNARY[rng.randrange(len(UNARY))], node])
        else:
            if path == ():
                sub = [p for p in paths if p]
                if not sub:
                    continue
                t = _get(t, sub[rng.randrange(len(sub))])
            else:
                t = node
        child = {'agg': agg, 'expr': t}
        if check(child, features) is None and child != prog:
            return child
    return random_program(rng, features)


def crossover(a, b, rng, features=FEATURES):
    for _ in range(50):
        pa = list(_paths(a['expr']))
        pb = list(_paths(b['expr']))
        child = {'agg': a['agg'], 'expr': _set(a['expr'], pa[rng.randrange(len(pa))],
                                               _get(b['expr'], pb[rng.randrange(len(pb))]))}
        if check(child, features) is None:
            return child
    return json.loads(json.dumps(a))


def ops(seeds=(), features=FEATURES):
    """Operators for `autonomy.feedback.steady_state_search` over programs on `features`; the first random programs
    are `seeds`, in order."""
    queue = [json.loads(json.dumps(s)) for s in seeds]
    for s in queue:
        why = check(s, features)
        if why:
            raise ValueError(f'seed {s!r}: {why}')

    def rand(rng):
        return queue.pop(0) if queue else random_program(rng, features)
    return {'random': rand, 'mutate': lambda p, rng: mutate(p, rng, features),
            'crossover': lambda a, b, rng: crossover(a, b, rng, features), 'size': size}


EIG = {'agg': 'sum', 'expr': 'eig'}
DEC = {'agg': 'sum', 'expr': 'dec'}
DEGREE = {'agg': 'sum', 'expr': 'one'}


def hybrid(lam):
    return {'agg': 'sum', 'expr': ['+', 'eig', ['*', float(lam), 'dec']]}
