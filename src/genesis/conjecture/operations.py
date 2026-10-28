"""Operators acting on Γ's own operations (research plane; the proving test's part 1, mechanism 4, decided by Daniel
on 28 Oct 2026: "Do the hardest so it proves it can find its way"; `docs/OMEGA_FRONTIER.md` §7b).

The builder's machinery here hands over no construction. It makes one of Γ's operations, the cartesian product, a
point in a space of operations that Genesis can mutate and recombine. No point of that space is favoured, and every
operation it reaches has an exact decoder.

**The space.** A product-type operation builds a graph on pairs (u, v), u from X and v from Y. Whether (u, v) and
(u', v') are adjacent depends only on how u relates to u' and how v relates to v'. Each coordinate is in one of three
states:
  * `same`: equal;
  * `adj`: adjacent;
  * `non`: distinct and not adjacent.
A RULE is the set of state pairs that make two distinct pairs adjacent: a subset of the 8 pairs other than
(same, same), held as an 8-bit table. All 256 tables are graph operations. Γ's cartesian product is the table
{(same, adj), (adj, same)}. The decoder is exact: the adjacency matrix is the sum of Kronecker products of the
coordinates' state indicators (I, X, J - I - X), one term per pair in the table. Each pair of vertex pairs is in
exactly one state pair, so the result is 0/1.

**The operators** draw uniformly from the space:
  * `mutate_table` flips one of the 8 bits, chosen uniformly;
  * `recombine_tables` takes each bit from one parent or the other, with equal odds.

`GammaPlus(n, ops)` is Γ with extra binary operations {name: table}. They are drawn, mutated and swapped like Γ's
own. A conjecture domain's `derive` adds one such operation to a Γ representation: a mutation of one of its
product-type operations, or a recombination of two. The result is a new representation (see `domain.py`).
"""
import hashlib

import numpy as np

from . import attack as AT

STATES = ('same', 'adj', 'non')
PAIRS = tuple((a, b) for a in STATES for b in STATES if (a, b) != ('same', 'same'))     # the 8 table positions


def table_of(pairs):
    return sum(1 << PAIRS.index(tuple(p)) for p in pairs)


def pairs_of(table):
    return [PAIRS[i] for i in range(len(PAIRS)) if table >> i & 1]


CARTESIAN = table_of([('same', 'adj'), ('adj', 'same')])      # Γ's 'prod', as a point of the space


def _indicators(X):
    n = len(X)
    eye = np.eye(n, dtype=np.int64)
    return {'same': eye, 'adj': X.astype(np.int64), 'non': np.ones((n, n), dtype=np.int64) - eye - X}


def rule_product(X, Y, table):
    """The adjacency matrix of the operation `table` applied to adjacency matrices X and Y (exact)."""
    ix, iy = _indicators(X), _indicators(Y)
    A = np.zeros((len(X) * len(Y), len(X) * len(Y)), dtype=np.int64)
    for a, b in pairs_of(table):
        A += np.kron(ix[a], iy[b])
    return A


def mutate_table(table, rng):
    return table ^ (1 << int(rng.integers(len(PAIRS))))


def recombine_tables(t1, t2, rng):
    mask = int(rng.integers(0, 1 << len(PAIRS)))
    return (t1 & mask) | (t2 & ~mask & ((1 << len(PAIRS)) - 1))


class GammaPlus(AT.GammaRep):
    """Γ with extra binary operations, each a rule table of the product-type space."""

    def __init__(self, n, ops, max_n=None):
        super().__init__(n, max_n)
        self.ops = dict(ops)
        self.BINARY = AT.GammaRep.BINARY + tuple(sorted(self.ops))

    def size(self, g):
        if g[0] in self.ops:
            return self.size(g[1]) * self.size(g[2])
        return super().size(g)

    def _build(self, g):
        if g[0] in self.ops:
            return rule_product(self._build(g[1]), self._build(g[2]), self.ops[g[0]])
        return super()._build(g)


def product_tables(ops):
    """The product-type operations of a representation: Γ's cartesian product and every derived table."""
    return [CARTESIAN] + [ops[k] for k in sorted(ops)]


def derive_table(ops, seed):
    """A new table, by mutating one product-type operation or recombining two, chosen uniformly; deterministic in the
    seed. Tables already present are skipped (up to 32 tries); None if none is new."""
    rng = np.random.default_rng(int(hashlib.sha256(repr(('derive', seed)).encode()).hexdigest()[:15], 16))
    have = set(product_tables(ops))
    for _ in range(32):
        tables = product_tables(ops)
        if len(tables) >= 2 and rng.random() < 0.5:
            i, j = rng.choice(len(tables), size=2, replace=False)
            t = recombine_tables(tables[int(i)], tables[int(j)], rng)
        else:
            t = mutate_table(tables[int(rng.integers(len(tables)))], rng)
        if t not in have:
            return t
    return None
