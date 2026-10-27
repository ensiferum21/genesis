"""Representations Genesis abstracts from its own converged counterexamples (research plane; F2/F5,
`docs/OMEGA_FRONTIER.md` §4.4, §5.3, §7b).

When independent branches converge on a structure, the Frontier asks the domain to abstract it
(`ConjectureDomain.abstract`). Here that means three steps, all in Genesis's own construction language Gamma (the
builder's base operations, no partition, quotient, blow-up or symmetry concept):
  1. **parse** a converged graph into a Gamma program, by decomposing it the way Gamma composes graphs: a
     disconnected graph is a union of its components; a graph whose complement is disconnected is a join of the
     complement's components; recognised bases (paths, cycles, complete graphs, stars, empty graphs, complete
     bipartite graphs) are leaves; a pendant path is peeled off; anything else is an opaque leaf (an explicit
     graph);
  2. **generalise**: every size in the program becomes a parameter, with the observed value as its anchor (the
     anti-unification of one example is its fully parameterised form; with several examples, positions that
     always agree stay fixed, as in X2's learner);
  3. the parameterised program is a **template**: a new representation whose genomes are parameter vectors, built
     to graphs of up to TEMPLATE_MAX_N vertices, so that a structure found at small n can be searched at large n.
A template is useful only if searching it finds what the starting representations do not; the domain records it
with its provenance, and the proving test measures that (part 1).
"""
import itertools

import numpy as np

TEMPLATE_MAX_N = 400


def _components(A):
    n = len(A)
    seen, comps = [False] * n, []
    for s in range(n):
        if seen[s]:
            continue
        stack, comp = [s], []
        seen[s] = True
        while stack:
            v = stack.pop()
            comp.append(v)
            for u in np.nonzero(A[v])[0]:
                if not seen[u]:
                    seen[u] = True
                    stack.append(int(u))
        comps.append(sorted(comp))
    return comps


def _sub(A, idx):
    return A[np.ix_(idx, idx)]


def _walk(A, start):
    """The vertices of a path or cycle in order from `start`."""
    order, prev, v = [start], -1, start
    while True:
        nb = [int(u) for u in np.nonzero(A[v])[0] if u != prev and u not in order]
        if not nb:
            return order
        prev, v = v, nb[0]
        order.append(v)


def _base(A):
    """(a Gamma base program, the vertex order its build uses) for A, or None."""
    n = len(A)
    deg = A.sum(axis=1)
    m = int(deg.sum()) // 2
    if m == 0:
        return ('E', n), list(range(n))
    if m == n * (n - 1) // 2:
        return ('K', n), list(range(n))
    if n >= 3 and m == n - 1 and int(deg.max()) == n - 1:
        c = int(np.argmax(deg))
        return ('S', n - 1), [c] + [v for v in range(n) if v != c]
    comps = _components(A)
    if len(comps) == 1 and m == n - 1 and int(deg.max()) <= 2:
        end = [v for v in range(n) if deg[v] <= 1][0]
        return ('P', n), _walk(A, end)
    if len(comps) == 1 and m == n and n >= 3 and all(d == 2 for d in deg):
        return ('C', n), _walk(A, 0)
    return None


def parse(A):
    """A Gamma program whose graph is isomorphic to A (opaque leaves where Gamma cannot decompose further)."""
    return _parse(np.asarray(A, dtype=np.int64))[0]


def _parse(A):
    """(program, order): order[i] is the vertex of A that the program's build puts at index i."""
    n = len(A)
    b = _base(A)
    if b is not None:
        return b
    comps = _components(A)
    if len(comps) > 1:
        return _fold('union', [_mapped(A, c) for c in comps])
    Ac = np.ones_like(A) - np.eye(n, dtype=np.int64) - A
    ccomps = _components(Ac)
    if len(ccomps) > 1:
        parts = [_mapped(A, c) for c in ccomps]
        if len(parts) == 2 and all(p[0][0] == 'E' for p in parts):
            (pa, oa), (pb, ob) = sorted(parts, key=lambda x: repr(x[0]))
            return ('Kab', pa[1], pb[1]), oa + ob
        return _fold('join', parts)
    deg = A.sum(axis=1)
    leaves = [v for v in range(n) if deg[v] == 1]
    if leaves and n > 3:                               # peel a pendant path ending at a leaf
        path, v, prev, anchor = [leaves[0]], leaves[0], -1, None
        while True:
            nb = [int(u) for u in np.nonzero(A[v])[0] if u != prev]
            if len(nb) != 1:
                break
            if deg[nb[0]] != 2:
                anchor = nb[0]
                break
            prev, v = v, nb[0]
            path.append(v)
        if anchor is not None:
            rest = [u for u in range(n) if u not in path]
            sub, sub_order = _parse(_sub(A, rest))
            order = [rest[i] for i in sub_order]
            return ('pend', sub, order.index(anchor), len(path)), order + list(reversed(path))
    edges = tuple(map(tuple, np.argwhere(np.triu(A, 1)).tolist()))
    return ('G', n, edges), list(range(n))                # an opaque leaf


def _mapped(A, idx):
    prog, order = _parse(_sub(A, idx))
    return prog, [idx[i] for i in order]


def _fold(op, parts):
    parts = sorted(parts, key=lambda x: repr(x[0]))
    prog, order = parts[0]
    for q, o in parts[1:]:
        prog, order = (op, prog, q), order + o
    return prog, order


def size_slots(prog, path=()):
    """[(path to an integer leaf, value)]: the sizes a template may vary."""
    k = prog[0]
    if k in ('P', 'C', 'K', 'S', 'E'):
        return [(path + (1,), prog[1])]
    if k == 'Kab':
        return [(path + (1,), prog[1]), (path + (2,), prog[2])]
    if k in ('union', 'join', 'prod', 'corona'):
        return size_slots(prog[1], path + (1,)) + size_slots(prog[2], path + (2,))
    if k == 'compl':
        return size_slots(prog[1], path + (1,))
    if k == 'pend':
        return size_slots(prog[1], path + (1,)) + [(path + (3,), prog[3])]
    return []                                            # opaque leaves are fixed


def _set(prog, path, value):
    if len(path) == 1:
        lst = list(prog)
        lst[path[0]] = value
        return tuple(lst)
    lst = list(prog)
    lst[path[0]] = _set(prog[path[0]], path[1:], value)
    return tuple(lst)


def generalise(programs):
    """A template {'program', 'slots': [(path, anchor)]} from one or more programs of the same shape: slots where
    the programs disagree (or every slot, for one program) become parameters."""
    shapes = {repr(_shape(p)) for p in programs}
    if len(shapes) != 1:
        return None
    base = programs[0]
    slots = []
    for i, (path, v) in enumerate(size_slots(base)):
        vals = {size_slots(p)[i][1] for p in programs}
        if len(programs) == 1 or len(vals) > 1:
            slots.append((path, v))
    if not slots:
        return None
    return {'program': base, 'slots': slots}


def _shape(prog):
    k = prog[0]
    if k in ('P', 'C', 'K', 'S', 'E'):
        return (k,)
    if k == 'Kab':
        return ('Kab',)
    if k in ('union', 'join', 'prod', 'corona'):
        return (k, _shape(prog[1]), _shape(prog[2]))
    if k == 'compl':
        return (k, _shape(prog[1]))
    if k == 'pend':
        return (k, _shape(prog[1]), prog[2])
    return prog


def _gamma_class():
    from .attack import GammaRep

    class Gamma(GammaRep):
        """Gamma with opaque leaves ('G', n, edges), which parsing leaves where Gamma cannot decompose."""

        def size(self, g):
            return g[1] if g[0] == 'G' else GammaRep.size(self, g)

        def _build(self, g):
            if g[0] == 'G':
                A = np.zeros((g[1], g[1]), dtype=np.int64)
                for u, v in g[2]:
                    A[u, v] = A[v, u] = 1
                return A
            return GammaRep._build(self, g)
    return Gamma


def build(prog, max_n=TEMPLATE_MAX_N):
    """The adjacency matrix of a Gamma program (opaque leaves allowed), or None beyond max_n."""
    G = _gamma_class()(max_n)
    if G.size(prog) > max_n:
        return None
    return G._build(prog)


class TemplateRep:
    """A representation whose genomes are integer parameter vectors for a template's slots."""

    def __init__(self, template, n=None, max_n=TEMPLATE_MAX_N):
        self.t, self.max_n = template, max_n
        self.gamma = _gamma_class()(max_n)
        self.name = 'template'
        self.anchor = np.array([v for _, v in template['slots']], dtype=np.int64)
        self.lo = np.array([3 if self._is_cycle(p) else 1 for p, _ in template['slots']], dtype=np.int64)

    def _is_cycle(self, path):
        node = self.t['program']
        for i in path[:-1]:
            node = node[i]
        return node[0] == 'C' and path[-1] == 1

    def program(self, g):
        prog = self.t['program']
        for (path, _), v in zip(self.t['slots'], g):
            prog = _set(prog, path, int(v))
        return prog

    def random(self, rng):
        scale = rng.choice([1, 2, 3, 4, 6, 8])
        g = np.maximum(self.lo, (self.anchor * scale + rng.integers(-2, 3, size=len(self.anchor))))
        return g

    def mutate(self, g, rng):
        h = g.copy()
        k = rng.integers(len(h))
        r = rng.random()
        if r < 0.5:
            h[k] = max(self.lo[k], h[k] + int(rng.choice([-3, -2, -1, 1, 2, 3])))
        elif r < 0.75:
            h[k] = max(self.lo[k], int(round(h[k] * rng.choice([0.5, 1.5, 2.0]))))
        else:
            f = rng.choice([0.5, 1.5, 2.0])
            h = np.maximum(self.lo, np.round(h * f).astype(np.int64))
        return h

    def crossover(self, a, b, rng):
        mask = rng.random(len(a)) < 0.5
        return np.where(mask, a, b)

    def graph(self, g):
        prog = self.program(g)
        size = self.gamma.size(prog)
        if size > self.max_n or size < 2:
            return None
        return self.gamma._build(prog)

    def positions(self):
        return None


def candidates(arrays, max_programs=4):
    """Templates from converged graphs: parse each, group by shape, generalise each group."""
    progs = [parse(A) for A in arrays]
    groups = {}
    for p in progs:
        groups.setdefault(repr(_shape(p)), []).append(p)
    out = []
    for key, ps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        t = generalise(ps[:max_programs])
        if t is not None and any(x[0] != 'G' for x in itertools.chain([t['program']])):
            out.append(t)
    return out
