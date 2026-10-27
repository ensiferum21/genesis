"""Attacks on upper bounds of the Laplacian spectral radius: searches for counterexamples (research plane; F2,
`docs/OMEGA_FRONTIER.md` §5.4).

**The objective.** For a bound mu <= max f, a graph's score is (mu - max f) / max f in floating point; a positive
score is a candidate counterexample, which only the kernel's exact certificate (`verify.py`) can confirm. A graph
with an isolated vertex, or where the bound is undefined anywhere, scores -inf (the domain's conservative reading).

**Representations** (Genesis's starting set; none carries a quotient, partition, blow-up or symmetry concept, by
the proving test's rule, §7b):
  * `edges`    an upper-triangle bit vector on n vertices;
  * `tree`     a Pruefer sequence (trees on n vertices);
  * `bounded`  an edge bit vector repaired to maximum degree 4 (the subquartic class of Ghebleh et al. 2024);
  * `gamma`    a program of the construction language Gamma (`docs/OMEGA_FRONTIER.md` §5.3): base graphs P, C, K, S,
               E, K_{a,b}; union, join, cartesian product, corona, complement, a pendant path; at most `MAX_N`
               vertices.
**Methods** (pausable generators, one evaluation per step; all prior art, re-implemented LLM-free): `hill` ((1+1)
with restarts), `anneal` (simulated annealing), `evolution` (steady-state, as `autonomy.portfolio`), `gbfs` (greedy
best-first over mutation neighbourhoods; Roucairol and Cazenave 2025 found it strong here), `cem` (the
cross-entropy method of Rubinstein over independent per-position distributions; Wagner 2021 used a network policy
instead), `nrpa` (nested rollout policy adaptation, level 1, Rosin 2011, over edge additions; `edges` only).
"""
import heapq
import itertools
import math

import numpy as np

from . import expr as E

MAX_N = 64


# ----------------------------------------------------------------------------------------------- the objective

class Bound:
    def __init__(self, formula, kind):
        self.formula, self.kind = formula, kind
        self.fn = E.compile_numpy(E.parse(formula, kind))

    def value(self, A):
        """max f over the graph (float), or None if undefined, or if a vertex is isolated."""
        deg = A.sum(axis=1).astype(float)
        if len(deg) == 0 or deg.min() == 0:
            return None
        m = (A @ deg) / deg
        if self.kind == 'vertex':
            vals = self.fn({'d': deg, 'm': m})
        else:
            iu, ju = np.nonzero(np.triu(A, 1))
            if len(iu) == 0:
                return None
            i = np.concatenate([iu, ju])
            j = np.concatenate([ju, iu])
            vals = self.fn({'di': deg[i], 'mi': m[i], 'dj': deg[j], 'mj': m[j]})
        vals = np.broadcast_to(np.asarray(vals, float), deg.shape if self.kind == 'vertex' else (len(i),))
        if np.isnan(vals).any():
            return None
        return float(vals.max())

    def score(self, A):
        b = self.value(A)
        if b is None or b <= 0:
            return -math.inf
        L = np.diag(A.sum(axis=1)) - A
        mu = float(np.linalg.eigvalsh(L.astype(float))[-1])
        return (mu - b) / b


def edges_of(A):
    iu, ju = np.nonzero(np.triu(A, 1))
    return [(int(a), int(b)) for a, b in zip(iu, ju)]


def certificate(A):
    """(n, edges, x): the candidate certificate (x from the float top eigenvector)."""
    from fractions import Fraction
    L = (np.diag(A.sum(axis=1)) - A).astype(float)
    w, V = np.linalg.eigh(L)
    x = [Fraction(round(float(v) * (1 << 30)), 1 << 30) for v in V[:, -1]]
    return A.shape[0], edges_of(A), x


# ----------------------------------------------------------------------------------------------- representations

class EdgesRep:
    name = 'edges'

    def __init__(self, n):
        self.n = n
        self.iu, self.ju = np.triu_indices(n, 1)
        self.size = len(self.iu)

    def random(self, rng):
        p = rng.uniform(0.1, 0.5)
        return rng.random(self.size) < p

    def mutate(self, g, rng):
        h = g.copy()
        for _ in range(1 + (rng.random() < 0.3)):
            k = rng.integers(self.size)
            h[k] = not h[k]
        return h

    def crossover(self, a, b, rng):
        mask = rng.random(self.size) < 0.5
        return np.where(mask, a, b)

    def graph(self, g):
        A = np.zeros((self.n, self.n), dtype=np.int64)
        A[self.iu[g], self.ju[g]] = 1
        return A + A.T

    def positions(self):
        return [(2, self.size)]                        # (values, count) for the CEM

    def from_samples(self, s):
        return s[0].astype(bool)


class BoundedRep(EdgesRep):
    name = 'bounded'
    DMAX = 4

    def _repair(self, g, rng):
        A = EdgesRep.graph(self, g)
        h = g.copy()
        order = rng.permutation(self.size)
        idx = {(int(a), int(b)): k for k, (a, b) in enumerate(zip(self.iu, self.ju))}
        deg = A.sum(axis=1)
        for k in order:
            if not h[k]:
                continue
            a, b = int(self.iu[k]), int(self.ju[k])
            if deg[a] > self.DMAX or deg[b] > self.DMAX:
                h[k] = False
                deg[a] -= 1
                deg[b] -= 1
        del idx
        return h

    def random(self, rng):
        return self._repair(rng.random(self.size) < min(0.5, 4.0 / self.n), rng)

    def mutate(self, g, rng):
        return self._repair(EdgesRep.mutate(self, g, rng), rng)

    def crossover(self, a, b, rng):
        return self._repair(EdgesRep.crossover(self, a, b, rng), rng)

    def from_samples(self, s):
        return self._repair(s[0].astype(bool), np.random.default_rng(int(s[0].sum())))


class TreeRep:
    name = 'tree'

    def __init__(self, n):
        self.n = max(3, n)

    def random(self, rng):
        return rng.integers(0, self.n, size=self.n - 2)

    def mutate(self, g, rng):
        h = g.copy()
        h[rng.integers(len(h))] = rng.integers(self.n)
        return h

    def crossover(self, a, b, rng):
        c = rng.integers(1, len(a))
        return np.concatenate([a[:c], b[c:]])

    def graph(self, g):
        n = self.n
        deg = np.ones(n, dtype=np.int64)
        for v in g:
            deg[v] += 1
        A = np.zeros((n, n), dtype=np.int64)
        heap = [v for v in range(n) if deg[v] == 1]
        heapq.heapify(heap)
        for v in g:
            leaf = heapq.heappop(heap)
            A[leaf, v] = A[v, leaf] = 1
            deg[leaf] -= 1
            deg[v] -= 1
            if deg[v] == 1:
                heapq.heappush(heap, int(v))
        u, w = [v for v in range(n) if deg[v] == 1][:2]
        A[u, w] = A[w, u] = 1
        return A

    def positions(self):
        return [(self.n, self.n - 2)]

    def from_samples(self, s):
        return s[0].astype(np.int64)


class GammaRep:
    """Programs of the construction language Gamma as nested tuples:
    ('P'|'C'|'K'|'S'|'E', k), ('Kab', a, b), ('union'|'join'|'prod'|'corona', x, y), ('compl', x), ('pend', x, v, k)."""
    name = 'gamma'
    BASES = ('P', 'C', 'K', 'S', 'E')
    BINARY = ('union', 'join', 'prod', 'corona')

    def __init__(self, n):
        self.n = n                                     # a soft target size: programs are capped at MAX_N vertices

    def _base(self, rng):
        if rng.random() < 0.2:
            return ('Kab', int(rng.integers(1, 6)), int(rng.integers(1, 8)))
        kind = self.BASES[rng.integers(len(self.BASES))]
        lo = 3 if kind == 'C' else 1
        return (kind, int(rng.integers(lo, max(lo + 1, min(12, self.n)))))

    def random(self, rng, depth=3):
        if depth == 0 or rng.random() < 0.3:
            return self._base(rng)
        r = rng.random()
        if r < 0.75:
            op = self.BINARY[rng.integers(len(self.BINARY))]
            return (op, self.random(rng, depth - 1), self.random(rng, depth - 1))
        if r < 0.85:
            return ('compl', self.random(rng, depth - 1))
        return ('pend', self.random(rng, depth - 1), int(rng.integers(0, 8)), int(rng.integers(1, 6)))

    def mutate(self, g, rng):
        paths = list(self._paths(g))
        path = paths[rng.integers(len(paths))]
        node = self._get(g, path)
        r = rng.random()
        if node[0] in self.BASES or node[0] == 'Kab':
            if r < 0.6:
                vals = list(node)
                i = int(rng.integers(1, len(vals)))
                vals[i] = max(1 if node[0] != 'C' or i != 1 else 3, vals[i] + int(rng.choice([-2, -1, 1, 2])))
                new = tuple(vals)
            else:
                new = self.random(rng, 2)
        elif node[0] in self.BINARY and r < 0.4:
            new = (self.BINARY[rng.integers(len(self.BINARY))],) + node[1:]
        else:
            new = self.random(rng, 2)
        return self._set(g, path, new)

    def crossover(self, a, b, rng):
        pa = list(self._paths(a))
        pb = list(self._paths(b))
        return self._set(a, pa[rng.integers(len(pa))], self._get(b, pb[rng.integers(len(pb))]))

    def _paths(self, g, path=()):
        yield path
        if g[0] in self.BINARY:
            yield from self._paths(g[1], path + (1,))
            yield from self._paths(g[2], path + (2,))
        elif g[0] in ('compl', 'pend'):
            yield from self._paths(g[1], path + (1,))

    def _get(self, g, path):
        for i in path:
            g = g[i]
        return g

    def _set(self, g, path, new):
        if not path:
            return new
        lst = list(g)
        lst[path[0]] = self._set(g[path[0]], path[1:], new)
        return tuple(lst)

    def size(self, g):
        k = g[0]
        if k in self.BASES:
            return g[1]
        if k == 'Kab':
            return g[1] + g[2]
        if k in ('union', 'join'):
            return self.size(g[1]) + self.size(g[2])
        if k == 'prod':
            return self.size(g[1]) * self.size(g[2])
        if k == 'corona':
            return self.size(g[1]) * (1 + self.size(g[2]))
        if k == 'compl':
            return self.size(g[1])
        return self.size(g[1]) + g[3]

    def graph(self, g):
        if self.size(g) > MAX_N or self.size(g) < 2:
            return None
        return self._build(g)

    def _build(self, g):
        k = g[0]
        if k == 'P':
            n = g[1]
            A = np.zeros((n, n), dtype=np.int64)
            for i in range(n - 1):
                A[i, i + 1] = A[i + 1, i] = 1
            return A
        if k == 'C':
            A = self._build(('P', g[1]))
            n = g[1]
            if n >= 3:
                A[0, n - 1] = A[n - 1, 0] = 1
            return A
        if k == 'K':
            return np.ones((g[1], g[1]), dtype=np.int64) - np.eye(g[1], dtype=np.int64)
        if k == 'S':
            n = g[1] + 1
            A = np.zeros((n, n), dtype=np.int64)
            A[0, 1:] = A[1:, 0] = 1
            return A
        if k == 'E':
            return np.zeros((g[1], g[1]), dtype=np.int64)
        if k == 'Kab':
            return self._build(('join', ('E', g[1]), ('E', g[2])))
        if k in ('union', 'join'):
            X, Y = self._build(g[1]), self._build(g[2])
            a, b = len(X), len(Y)
            A = np.zeros((a + b, a + b), dtype=np.int64)
            A[:a, :a], A[a:, a:] = X, Y
            if k == 'join':
                A[:a, a:] = 1
                A[a:, :a] = 1
            return A
        if k == 'prod':
            X, Y = self._build(g[1]), self._build(g[2])
            return np.kron(X, np.eye(len(Y), dtype=np.int64)) + np.kron(np.eye(len(X), dtype=np.int64), Y)
        if k == 'corona':
            X, Y = self._build(g[1]), self._build(g[2])
            a, b = len(X), len(Y)
            n = a * (1 + b)
            A = np.zeros((n, n), dtype=np.int64)
            A[:a, :a] = X
            for i in range(a):
                s = a + i * b
                A[s:s + b, s:s + b] = Y
                A[i, s:s + b] = 1
                A[s:s + b, i] = 1
            return A
        if k == 'compl':
            X = self._build(g[1])
            return np.ones_like(X) - np.eye(len(X), dtype=np.int64) - X
        X = self._build(g[1])                              # pend: a path of length g[3] at vertex g[2] mod |X|
        a, L = len(X), g[3]
        A = np.zeros((a + L, a + L), dtype=np.int64)
        A[:a, :a] = X
        prev = g[2] % a
        for i in range(L):
            A[prev, a + i] = A[a + i, prev] = 1
            prev = a + i
        return A

    def positions(self):
        return None                                        # the CEM does not apply to programs


REPRESENTATIONS = {'edges': EdgesRep, 'tree': TreeRep, 'bounded': BoundedRep, 'gamma': GammaRep}


# ----------------------------------------------------------------------------------------------- methods

def _evaluate(rep, bound, g):
    A = rep.graph(g)
    if A is None:
        return -math.inf, None
    return bound.score(A), A


def hill(rep, bound, rng, stall=60):
    cur = rep.random(rng)
    s, A = _evaluate(rep, bound, cur)
    yield s, cur, A
    since = 0
    while True:
        if since >= stall:
            cur = rep.random(rng)
            s, A = _evaluate(rep, bound, cur)
            since = 0
            yield s, cur, A
            continue
        cand = rep.mutate(cur, rng)
        cs, cA = _evaluate(rep, bound, cand)
        yield cs, cand, cA
        if cs >= s:
            if cs > s:
                since = 0
            cur, s = cand, cs
        since += 1


def anneal(rep, bound, rng, horizon=4000, t0=0.05, t1=0.0005):
    cur = rep.random(rng)
    s, A = _evaluate(rep, bound, cur)
    yield s, cur, A
    for i in itertools.count(1):
        T = t0 * (t1 / t0) ** min(1.0, (i % horizon) / horizon)
        cand = rep.mutate(cur, rng)
        cs, cA = _evaluate(rep, bound, cand)
        yield cs, cand, cA
        if cs >= s or (math.isfinite(cs) and math.isfinite(s) and rng.random() < math.exp((cs - s) / T)):
            cur, s = cand, cs
        if i % horizon == 0:
            cur = rep.random(rng)
            s, _ = _evaluate(rep, bound, cur)


def evolution(rep, bound, rng, pop=16, tour=3, p_cross=0.25):
    P = []
    for _ in range(pop):
        g = rep.random(rng)
        s, A = _evaluate(rep, bound, g)
        P.append((s, g))
        yield s, g, A

    def pick():
        idx = rng.choice(len(P), size=min(tour, len(P)), replace=False)
        return max((P[i] for i in idx), key=lambda x: x[0])[1]
    while True:
        child = rep.crossover(pick(), pick(), rng) if rng.random() < p_cross else rep.mutate(pick(), rng)
        s, A = _evaluate(rep, bound, child)
        yield s, child, A
        worst = min(range(len(P)), key=lambda i: P[i][0])
        if s >= P[worst][0]:
            P[worst] = (s, child)


def gbfs(rep, bound, rng, children=8, cap=2000):
    start = rep.random(rng)
    s, A = _evaluate(rep, bound, start)
    yield s, start, A
    tie = itertools.count()
    heap = [(-s, next(tie), start)]
    while True:
        if not heap:
            g = rep.random(rng)
            s, A = _evaluate(rep, bound, g)
            yield s, g, A
            heap = [(-s, next(tie), g)]
            continue
        _, _, g = heapq.heappop(heap)
        for _ in range(children):
            c = rep.mutate(g, rng)
            cs, cA = _evaluate(rep, bound, c)
            yield cs, c, cA
            if math.isfinite(cs):
                heapq.heappush(heap, (-cs, next(tie), c))
        if len(heap) > cap:
            heap = heapq.nsmallest(cap // 2, heap)
            heapq.heapify(heap)


def cem(rep, bound, rng, batch=50, elite=5, alpha=0.7):
    pos = rep.positions()
    if pos is None:                                        # programs: fall back to evolution (disclosed)
        yield from evolution(rep, bound, rng)
        return
    values, count = pos[0]
    probs = np.full((count, values), 1.0 / values)
    while True:
        batch_res = []
        for _ in range(batch):
            draws = np.array([rng.choice(values, p=probs[k]) for k in range(count)]) if values > 2 else \
                (rng.random(count) < probs[:, 1]).astype(np.int64)
            g = rep.from_samples([draws])
            s, A = _evaluate(rep, bound, g)
            batch_res.append((s, draws))
            yield s, g, A
        batch_res.sort(key=lambda x: -x[0] if math.isfinite(x[0]) else math.inf)
        top = [d for _, d in batch_res[:elite]]
        freq = np.zeros_like(probs)
        for d in top:
            freq[np.arange(count), d] += 1
        freq /= len(top)
        probs = alpha * freq + (1 - alpha) * probs
        probs = np.clip(probs, 0.01, 1.0)
        probs /= probs.sum(axis=1, keepdims=True)


def nrpa(rep, bound, rng, iterations=50, alpha=1.0):
    """Level-1 NRPA over sequences of edge additions to a random spanning tree (`edges` representation only)."""
    if not isinstance(rep, EdgesRep) or isinstance(rep, BoundedRep):
        yield from evolution(rep, bound, rng)
        return
    n, size = rep.n, rep.size
    L = max(1, n // 2)
    while True:
        w = np.zeros(size)
        best_s, best_seq, best_base = -math.inf, None, None
        base = np.zeros(size, dtype=bool)                  # a random spanning tree keeps every vertex connected
        perm = rng.permutation(n)
        for i in range(1, n):
            a, b = sorted((int(perm[i]), int(perm[rng.integers(i)])))
            base[np.nonzero((rep.iu == a) & (rep.ju == b))[0][0]] = True
        for _ in range(iterations):
            g = base.copy()
            seq = []
            for _ in range(L):
                legal = np.nonzero(~g)[0]
                if len(legal) == 0:
                    break
                p = np.exp(w[legal] - w[legal].max())
                mv = int(legal[rng.choice(len(legal), p=p / p.sum())])
                g[mv] = True
                seq.append(mv)
            s, A = _evaluate(rep, bound, g)
            yield s, g, A
            if s >= best_s:
                best_s, best_seq = s, seq
            if best_seq:                                   # adapt toward the best sequence
                g2 = base.copy()
                for mv in best_seq:
                    legal = np.nonzero(~g2)[0]
                    p = np.exp(w[legal] - w[legal].max())
                    p /= p.sum()
                    w[legal] -= alpha * p
                    w[mv] += alpha
                    g2[mv] = True


METHODS = {'hill': hill, 'anneal': anneal, 'evolution': evolution, 'gbfs': gbfs, 'cem': cem, 'nrpa': nrpa}


class Runner:
    """One attack (bound, representation, method, n, seed), advanced `k` evaluations at a time; deterministic, so it
    can be rebuilt by replay."""

    def __init__(self, formula, kind, representation, method, n, seed, rep=None, objective=None):
        self.bound = objective if objective is not None else Bound(formula, kind)   # any object with score(A)
        self.rep = rep if rep is not None else REPRESENTATIONS[representation](n)
        self.rng = np.random.default_rng(seed)
        self.gen = METHODS[method](self.rep, self.bound, self.rng)
        self.evals, self.best, self.best_A = 0, -math.inf, None

    def advance(self, k):
        improved = False
        for _ in range(k):
            s, g, A = next(self.gen)
            self.evals += 1
            if A is not None and s > self.best:
                self.best, self.best_A, improved = s, A, True
        return improved
