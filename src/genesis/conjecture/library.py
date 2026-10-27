"""Library learning over Γ: named pieces abstracted from Genesis's own constructions (research plane; the proving
test's part 1, mechanism 1, decided by Daniel on 28 Oct 2026; `docs/OMEGA_FRONTIER.md` §7b).

The builder's machinery here hands over no construction. It compresses Genesis's own best Γ programs. A piece that
recurs in the best programs of at least two independent branches becomes a named operation. Its base sizes become
parameters, and it is offered in a new representation alongside Γ's own operations. The pieces are whatever
Genesis's searches produced.

  * `skeleton(t)`: a subtree with its integer parameters blanked, the shape a piece is compared by;
  * `pieces(prog)`: every subtree rooted at an operation, of 2 to `MAX_NODES` nodes;
  * `learn(sources, known)`: the best new piece. It must recur in at least `MIN_SOURCES` sources; among those, it
    has the most sources x (nodes - 1), the description length it saves. Ties go to the smaller repr. None if no
    piece recurs;
  * `GammaLib(n, ops, macros)`: Γ (with any derived operations) plus macros, leaves ('m<k>', p1, ..., pj) that
    expand to their skeleton filled with the parameters.

Macros may contain earlier macros (a library grows hierarchically).
"""
from . import attack as AT
from . import operations as OP

MAX_NODES = 7
MIN_SOURCES = 2
LIBRARY_SHARE = 0.3                   # the share of new leaves drawn from the library


def _is_leaf(t, rep_binary):
    return t[0] not in rep_binary and t[0] not in ('compl', 'pend')


def skeleton(t, binary):
    k = t[0]
    if k in binary:
        return (k, skeleton(t[1], binary), skeleton(t[2], binary))
    if k == 'compl':
        return ('compl', skeleton(t[1], binary))
    if k == 'pend':
        return ('pend', skeleton(t[1], binary), None, None)
    return (k,) + (None,) * (len(t) - 1)


def params_of(t, binary):
    k = t[0]
    if k in binary:
        return params_of(t[1], binary) + params_of(t[2], binary)
    if k == 'compl':
        return params_of(t[1], binary)
    if k == 'pend':
        return params_of(t[1], binary) + [t[2], t[3]]
    return list(t[1:])


def fill(skel, params, binary):
    it = iter(params)

    def go(s):
        k = s[0]
        if k in binary:
            return (k, go(s[1]), go(s[2]))
        if k == 'compl':
            return ('compl', go(s[1]))
        if k == 'pend':
            inner = go(s[1])
            return ('pend', inner, next(it), next(it))
        return (k,) + tuple(next(it) for _ in s[1:])
    return go(skel)


def nodes(t, binary):
    k = t[0]
    if k in binary:
        return 1 + nodes(t[1], binary) + nodes(t[2], binary)
    if k in ('compl', 'pend'):
        return 1 + nodes(t[1], binary)
    return 1


def pieces(prog, binary):
    out = []

    def walk(t):
        if not _is_leaf(t, binary):
            if 2 <= nodes(t, binary) <= MAX_NODES:
                out.append(skeleton(t, binary))
            walk(t[1])
            if t[0] in binary:
                walk(t[2])
    walk(prog)
    return out


def learn(sources, binary, known=()):
    """The best new piece among `sources` (a list of programs, one per independent source), or None."""
    count = {}
    for prog in sources:
        for s in set(pieces(prog, binary)):
            count[s] = count.get(s, 0) + 1
    known = set(known)
    best, best_key = None, None
    for s, c in count.items():
        if c < MIN_SOURCES or s in known:
            continue
        key = (-c * (nodes(s, binary) - 1), repr(s))
        if best_key is None or key < best_key:
            best, best_key = s, key
    return best


def slots(skel, binary):
    return sum(1 for x in params_of(skel, binary) if x is None)


class GammaLib(OP.GammaPlus):
    def __init__(self, n, ops, macros):
        super().__init__(n, ops)
        self.macros = dict(macros)                    # name -> skeleton

    def _base(self, rng):
        if self.macros and rng.random() < LIBRARY_SHARE:
            names = sorted(self.macros)
            name = names[int(rng.integers(len(names)))]
            k = slots(self.macros[name], self.BINARY)
            return (name,) + tuple(int(rng.integers(1, max(2, min(9, self.n)))) for _ in range(k))
        return super()._base(rng)

    def expand(self, g):
        params = [max(1, int(x)) for x in g[1:]]
        return fill(self.macros[g[0]], params, self.BINARY)

    def mutate(self, g, rng):
        paths = list(self._paths(g))
        path = paths[int(rng.integers(len(paths)))]
        node = self._get(g, path)
        if node[0] in self.macros and len(node) > 1 and rng.random() < 0.6:
            vals = list(node)
            i = int(rng.integers(1, len(vals)))
            vals[i] = max(1, vals[i] + int(rng.choice([-2, -1, 1, 2])))
            return self._set(g, path, tuple(vals))
        return super().mutate(g, rng)

    def size(self, g):
        if g[0] in self.macros:
            return self.size(self.expand(g))
        return super().size(g)

    def _build(self, g):
        if g[0] in self.macros:
            return self._build(self.expand(g))
        if g[0] == 'C' and g[1] < 3:                   # a macro's slot may hand a cycle fewer than 3 vertices
            return super()._build(('P', g[1]))
        return super()._build(g)
