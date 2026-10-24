"""The graph sense language: computational senses Genesis can synthesise over weighted graphs
(`docs/OMEGA_RECURSIVE_INVENTION.md` §4.1; Batch R2).

A sense is a typed expression tree whose value is a number (a scalar sense) computed from a graph
{'n', 'edges': [[u, v, w], ...]}. Its effect is **accessibility**: a deterministic function of the graph, which makes
structure usable and adds no information the graph did not contain.

**Types:** `N` (an array over vertices), `E` (an array over edges), `S` (a scalar).

**Primitives** (the human-provided seed vocabulary):
  * vertex arrays: `deg` (degree), `wdeg` (sum of incident weights), `absdeg` (sum of |weights|), `negdeg` (incident
    negative edges), `tri` (triangles through the vertex), `clust` (local clustering coefficient), `core` (core
    number), `one` (ones);
  * edge arrays: `w` (weights), `wabs` (|w|), `common` (common neighbours of the endpoints);
  * scalars: `n`, `m`, constants.
**Operators:**
  * N -> N: `nbr_mean`, `nbr_max`, `nbr_min` (over neighbours), `log1p`, `abs`, `rank` (normalised rank);
  * N x N -> N and E x E -> E: `+`, `-`, `*`, `/` (0 where the divisor is 0); N x N -> N: `max2`, `min2`;
  * N x S -> N: `gt` (indicator above a scalar), `scale` (times a scalar);
  * E -> N: `edge_sum`, `edge_max` (onto the endpoints);
  * N -> E: `ends_min`, `ends_max`, `ends_diff` (from the endpoints);
  * N -> S, E -> S: `mean`, `sd`, `cv`, `max`, `min`, `q10`, `q50`, `q90`, `frac_pos`;
  * S x S -> S: `+`, `-`, `*`, `/`, `log1p` (S -> S).
Every tree is checked (`check`): known operators, correct types, at most MAX_SIZE nodes and depth MAX_DEPTH. It is
evaluated by `evaluate` with numpy, never `eval`; primitives are computed once per graph and cached (`Context`).
`random_sense`, `mutate` and `crossover` are the search operators: they keep types and bounds.
"""
import math
import random

import numpy as np

MAX_SIZE, MAX_DEPTH = 15, 5
N_PRIM = ('deg', 'wdeg', 'absdeg', 'negdeg', 'tri', 'clust', 'core', 'one')
E_PRIM = ('w', 'wabs', 'common')
S_PRIM = ('n', 'm')
CONSTANTS = (0.0, 0.5, 1.0, 2.0, 3.0, 10.0)
OPS = {
    'nbr_mean': ('N', ('N',)), 'nbr_max': ('N', ('N',)), 'nbr_min': ('N', ('N',)), 'log1p_n': ('N', ('N',)),
    'abs_n': ('N', ('N',)), 'rank': ('N', ('N',)),
    'add_n': ('N', ('N', 'N')), 'sub_n': ('N', ('N', 'N')), 'mul_n': ('N', ('N', 'N')), 'div_n': ('N', ('N', 'N')),
    'max2_n': ('N', ('N', 'N')), 'min2_n': ('N', ('N', 'N')),
    'add_e': ('E', ('E', 'E')), 'sub_e': ('E', ('E', 'E')), 'mul_e': ('E', ('E', 'E')), 'div_e': ('E', ('E', 'E')),
    'gt': ('N', ('N', 'S')), 'scale': ('N', ('N', 'S')),
    'edge_sum': ('N', ('E',)), 'edge_max': ('N', ('E',)),
    'ends_min': ('E', ('N',)), 'ends_max': ('E', ('N',)), 'ends_diff': ('E', ('N',)),
    'add_s': ('S', ('S', 'S')), 'sub_s': ('S', ('S', 'S')), 'mul_s': ('S', ('S', 'S')), 'div_s': ('S', ('S', 'S')),
    'log1p_s': ('S', ('S',)),
}
AGGS = ('mean', 'sd', 'cv', 'max', 'min', 'q10', 'q50', 'q90', 'frac_pos')
_AGG_OPS = {f'{a}_{t}': ('S', (t.upper(),)) for a in AGGS for t in ('n', 'e')}
if set(_AGG_OPS) & set(OPS):                       # a name collision would silently retype an operator
    raise RuntimeError(f'operator names collide: {sorted(set(_AGG_OPS) & set(OPS))}')
OPS.update(_AGG_OPS)


class Context:
    """One graph's primitives, computed on demand and cached."""

    def __init__(self, graph):
        self.n = int(graph['n'])
        E = np.array([[e[0], e[1], (e[2] if len(e) == 3 else 1)] for e in graph['edges']], dtype=np.float64)
        if len(E) == 0:
            E = np.zeros((0, 3))
        self.u, self.v, self.wt = E[:, 0].astype(np.int64), E[:, 1].astype(np.int64), E[:, 2]
        self.m = len(self.u)
        self._cache = {}
        self._adj = None

    def adj(self):
        if self._adj is None:
            nb = [[] for _ in range(self.n)]
            for a, b in zip(self.u.tolist(), self.v.tolist()):
                if a != b:
                    nb[a].append(b)
                    nb[b].append(a)
            self._adj = [np.array(sorted(set(x)), dtype=np.int64) for x in nb]
        return self._adj

    def prim(self, name):
        if name in self._cache:
            return self._cache[name]
        n, u, v, w = self.n, self.u, self.v, self.wt
        if name == 'one':
            x = np.ones(n)
        elif name == 'deg':
            x = np.bincount(u, minlength=n) + np.bincount(v, minlength=n)
        elif name == 'wdeg':
            x = np.bincount(u, weights=w, minlength=n) + np.bincount(v, weights=w, minlength=n)
        elif name == 'absdeg':
            x = np.bincount(u, weights=np.abs(w), minlength=n) + np.bincount(v, weights=np.abs(w), minlength=n)
        elif name == 'negdeg':
            neg = (w < 0).astype(np.float64)
            x = np.bincount(u, weights=neg, minlength=n) + np.bincount(v, weights=neg, minlength=n)
        elif name in ('tri', 'clust', 'common'):
            adj = self.adj()
            sets = [set(a.tolist()) for a in adj]
            common = np.array([len(sets[a] & sets[b]) for a, b in zip(u.tolist(), v.tolist())], dtype=np.float64)
            self._cache['common'] = common
            tri = (np.bincount(u, weights=common, minlength=n) + np.bincount(v, weights=common, minlength=n)) / 2
            self._cache['tri'] = tri
            d = np.array([len(a) for a in adj], dtype=np.float64)
            pairs = d * (d - 1) / 2
            self._cache['clust'] = np.divide(tri, pairs, out=np.zeros(n), where=pairs > 0)
            return self._cache[name]
        elif name == 'core':
            x = core_numbers(self.adj())
        elif name == 'w':
            x = w.copy()
        elif name == 'wabs':
            x = np.abs(w)
        else:
            raise ValueError(f'unknown primitive {name!r}')
        x = np.asarray(x, dtype=np.float64)
        self._cache[name] = x
        return x


def core_numbers(adj):
    """Core number of every vertex (peeling by current degree)."""
    import heapq
    n = len(adj)
    deg = [len(a) for a in adj]
    core = [0] * n
    heap = [(d, i) for i, d in enumerate(deg)]
    heapq.heapify(heap)
    done = [False] * n
    k = 0
    while heap:
        d, i = heapq.heappop(heap)
        if done[i] or d != deg[i]:
            continue
        k = max(k, d)
        core[i] = k
        done[i] = True
        for j in adj[i].tolist():
            if not done[j]:
                deg[j] -= 1
                heapq.heappush(heap, (deg[j], j))
    return np.array(core, dtype=np.float64)


# ------------------------------------------------------------------------------------------- checking

def type_of(t):
    if isinstance(t, str):
        if t in N_PRIM:
            return 'N'
        if t in E_PRIM:
            return 'E'
        if t in S_PRIM:
            return 'S'
        raise ValueError(f'unknown primitive {t!r}')
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        return 'S'
    if isinstance(t, list) and t and t[0] in OPS:
        out, args = OPS[t[0]]
        if len(t) != 1 + len(args):
            raise ValueError(f'{t[0]} takes {len(args)} arguments')
        for a, want in zip(t[1:], args):
            if type_of(a) != want:
                raise ValueError(f'{t[0]} expects {want}')
        return out
    raise ValueError(f'not a sense expression: {t!r}')


def size(t):
    return 1 + sum(size(a) for a in t[1:]) if isinstance(t, list) else 1


def depth(t):
    return 1 + max((depth(a) for a in t[1:]), default=0) if isinstance(t, list) else 1


def check(t):
    """None, or why the tree is not a scalar sense within the bounds."""
    try:
        ty = type_of(t)
    except ValueError as e:
        return str(e)
    if ty != 'S':
        return 'a sense is scalar-valued'
    if size(t) > MAX_SIZE or depth(t) > MAX_DEPTH:
        return f'at most {MAX_SIZE} nodes and depth {MAX_DEPTH}'
    return None


# ------------------------------------------------------------------------------------------- evaluation

def _agg(name, x):
    if x.size == 0:
        return 0.0
    if name == 'mean':
        return float(x.mean())
    if name == 'sd':
        return float(x.std())
    if name == 'cv':
        m = x.mean()
        return float(x.std() / abs(m)) if m else 0.0
    if name == 'max':
        return float(x.max())
    if name == 'min':
        return float(x.min())
    if name == 'q10':
        return float(np.quantile(x, 0.1))
    if name == 'q50':
        return float(np.quantile(x, 0.5))
    if name == 'q90':
        return float(np.quantile(x, 0.9))
    if name == 'frac_pos':
        return float((x > 0).mean())
    raise ValueError(name)


def _div(a, b):
    return np.divide(a, b, out=np.zeros_like(np.asarray(a, dtype=np.float64)), where=np.asarray(b) != 0)


def _ev(t, ctx):
    if isinstance(t, str):
        if t == 'n':
            return float(ctx.n)
        if t == 'm':
            return float(ctx.m)
        return ctx.prim(t)
    if isinstance(t, (int, float)):
        return float(t)
    op, args = t[0], [_ev(a, ctx) for a in t[1:]]
    if op in ('nbr_mean', 'nbr_max', 'nbr_min'):
        x = args[0]
        out = np.zeros(ctx.n)
        for i, nb in enumerate(ctx.adj()):
            if nb.size:
                out[i] = {'nbr_mean': np.mean, 'nbr_max': np.max, 'nbr_min': np.min}[op](x[nb])
        return out
    if op in ('log1p_n', 'log1p_s'):
        return np.log1p(np.abs(args[0])) * np.sign(args[0]) if op == 'log1p_n' else \
            math.copysign(math.log1p(abs(args[0])), args[0])
    if op == 'abs_n':
        return np.abs(args[0])
    if op == 'rank':
        x = args[0]
        return (np.argsort(np.argsort(x, kind='stable'), kind='stable') / max(1, x.size - 1)).astype(np.float64)
    if op in ('add_n', 'add_e', 'add_s'):
        return args[0] + args[1]
    if op in ('sub_n', 'sub_e', 'sub_s'):
        return args[0] - args[1]
    if op in ('mul_n', 'mul_e', 'mul_s'):
        return args[0] * args[1]
    if op in ('div_n', 'div_e'):
        return _div(args[0], args[1])
    if op == 'div_s':
        return args[0] / args[1] if args[1] else 0.0
    if op == 'max2_n':
        return np.maximum(args[0], args[1])
    if op == 'min2_n':
        return np.minimum(args[0], args[1])
    if op == 'gt':
        return (args[0] > args[1]).astype(np.float64)
    if op == 'scale':
        return args[0] * args[1]
    if op == 'edge_sum':
        return np.bincount(ctx.u, weights=args[0], minlength=ctx.n) + \
            np.bincount(ctx.v, weights=args[0], minlength=ctx.n)
    if op == 'edge_max':
        out = np.full(ctx.n, -np.inf)
        np.maximum.at(out, ctx.u, args[0])
        np.maximum.at(out, ctx.v, args[0])
        out[np.isinf(out)] = 0.0
        return out
    if op in ('ends_min', 'ends_max', 'ends_diff'):
        x = args[0]
        a, b = x[ctx.u], x[ctx.v]
        return {'ends_min': np.minimum(a, b), 'ends_max': np.maximum(a, b), 'ends_diff': np.abs(a - b)}[op]
    for agg in AGGS:
        if op in (f'{agg}_n', f'{agg}_e'):
            return _agg(agg, args[0])
    raise ValueError(f'unknown operator {op!r}')


def evaluate(t, graph_or_ctx):
    """The sense's value on a graph (a finite float; non-finite values become 0)."""
    why = check(t)
    if why:
        raise ValueError(why)
    ctx = graph_or_ctx if isinstance(graph_or_ctx, Context) else Context(graph_or_ctx)
    with np.errstate(all='ignore'):
        v = float(_ev(t, ctx))
    return v if math.isfinite(v) else 0.0


# ------------------------------------------------------------------------------------------- search operators

def random_tree(want, rng, d=0, max_depth=3):
    leaves = {'N': list(N_PRIM), 'E': list(E_PRIM), 'S': list(S_PRIM) + list(CONSTANTS)}
    ops = [k for k, (out, _) in OPS.items() if out == want]
    if d >= max_depth or (d > 0 and rng.random() < 0.3):
        return rng.choice(leaves[want])
    op = rng.choice(ops)
    return [op] + [random_tree(a, rng, d + 1, max_depth) for a in OPS[op][1]]


def random_sense(rng):
    while True:
        agg = rng.choice(AGGS)
        src = rng.choice(('N', 'E'))
        t = [f'{agg}_{src.lower()}', random_tree(src, rng, 1)]
        if rng.random() < 0.2:
            t = [rng.choice(('div_s', 'sub_s', 'mul_s')), t, random_sense_scalar(rng)]
        if check(t) is None:
            return t


def random_sense_scalar(rng):
    return [f'{rng.choice(AGGS)}_n', random_tree('N', rng, 2)]


def _paths(t, path=()):
    yield path, t
    if isinstance(t, list):
        for i, a in enumerate(t[1:], start=1):
            yield from _paths(a, path + (i,))


def _replace(t, path, new):
    if not path:
        return new
    t = list(t)
    t[path[0]] = _replace(t[path[0]], path[1:], new)
    return t


def mutate(t, rng):
    for _ in range(50):
        paths = list(_paths(t))
        path, sub = rng.choice(paths)
        ty = type_of(sub)
        c = _replace(t, path, random_tree(ty, rng, len(path), max_depth=min(MAX_DEPTH - 1, len(path) + 2)))
        if check(c) is None and c != t:
            return c
    return random_sense(rng)


def crossover(a, b, rng):
    for _ in range(50):
        pa, sa = rng.choice(list(_paths(a)))
        cands = [(p, s) for p, s in _paths(b) if type_of(s) == type_of(sa)]
        if not cands:
            continue
        _, sb = rng.choice(cands)
        c = _replace(a, pa, sb)
        if check(c) is None:
            return c
    return a


def ops():
    """Search operators in the form `autonomy.feedback` and `selfimprove` use."""
    return {'random': random_sense, 'mutate': mutate, 'crossover': crossover, 'size': size}


__all__ = ['MAX_SIZE', 'MAX_DEPTH', 'N_PRIM', 'E_PRIM', 'S_PRIM', 'OPS', 'AGGS', 'Context', 'core_numbers',
           'type_of', 'size', 'depth', 'check', 'evaluate', 'random_tree', 'random_sense', 'mutate', 'crossover',
           'ops']
