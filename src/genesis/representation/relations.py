"""Relations over binary variables: the predicates of Genesis's representation language (directive items 6-7).

A relation of arity k is a set of assignments of k binary variables, stored as a truth table: bit `i` of `table` is 1
when the assignment whose variable j is bit j of i belongs to the relation. Relations are values: equal tables are
the same relation, and every relation has a canonical form under renaming and negating variables (the orbit's least
table), so that one content address names the whole family and a gadget found for one member serves all of them.

**Operators** build new relations from old ones, so the language extends itself: `negate` (a literal), `permute`,
`project` (there exists a value of one variable), `complement`, `conjoin` (two relations on a shared variable set,
by a map of variables), `extend` (a relation lifted to more variables, which it ignores). Named constructors give the
relations problem families use: clauses, exactly-j / at-most-j / at-least-j of k, parity, not-all-equal, gates.
"""
from itertools import permutations, product

from ..common import digest

MAX_ARITY = 6


class Relation:
    __slots__ = ('k', 'table')

    def __init__(self, k, table):
        if not 0 < k <= MAX_ARITY:
            raise ValueError(f'arity must be 1..{MAX_ARITY}')
        if not 0 <= table < (1 << (1 << k)):
            raise ValueError('table out of range')
        self.k, self.table = int(k), int(table)

    # -------------------------------------------------------------- values
    def __eq__(self, other):
        return isinstance(other, Relation) and (self.k, self.table) == (other.k, other.table)

    def __hash__(self):
        return hash((self.k, self.table))

    def __repr__(self):
        return f'Relation({self.k}, {self.table:#x})'

    def contains(self, x):
        return bool(self.table >> index(x) & 1)

    def members(self):
        return [assignment(i, self.k) for i in range(1 << self.k) if self.table >> i & 1]

    def size(self):
        return bin(self.table).count('1')

    def to_json(self):
        return {'k': self.k, 'table': self.table}

    @staticmethod
    def from_json(d):
        return Relation(d['k'], d['table'])

    # -------------------------------------------------------------- canonical form and identity
    def transform(self, perm, flips):
        """The relation after renaming variable j to perm[j] and negating the variables in `flips` (a bitmask over the
        new names)."""
        t = 0
        for i in range(1 << self.k):
            if self.table >> i & 1:
                x = assignment(i, self.k)
                y = [0] * self.k
                for j, v in enumerate(x):
                    y[perm[j]] = v
                t |= 1 << (index(y) ^ flips)
        return Relation(self.k, t)

    def canonical(self):
        """(least table over the orbit, the (perm, flips) that reach it)."""
        best = None
        for perm in permutations(range(self.k)):
            for flips in range(1 << self.k):
                t = self.transform(perm, flips).table
                if best is None or t < best[0]:
                    best = (t, (list(perm), flips))
        return Relation(self.k, best[0]), best[1]

    def id(self):
        c, _ = self.canonical()
        return digest({'relation': 'genesis-relation-v1', 'k': c.k, 'table': c.table})[:16]

    # -------------------------------------------------------------- operators
    def negate(self, j):
        return self.transform(list(range(self.k)), 1 << j)

    def permute(self, perm):
        return self.transform(list(perm), 0)

    def complement(self):
        return Relation(self.k, ((1 << (1 << self.k)) - 1) ^ self.table)

    def project(self, j):
        """There exists a value of variable j: a relation of arity k - 1 on the other variables, in order."""
        if self.k == 1:
            raise ValueError('cannot project the only variable')
        t = 0
        for x in self.members():
            t |= 1 << index(x[:j] + x[j + 1:])
        return Relation(self.k - 1, t)

    def extend(self, k, places):
        """The relation on k variables whose variables `places` (in order) satisfy self; the others are free."""
        if len(places) != self.k or len(set(places)) != self.k or max(places) >= k:
            raise ValueError('places must name distinct variables of the new arity')
        t = 0
        for i in range(1 << k):
            x = assignment(i, k)
            if self.contains([x[p] for p in places]):
                t |= 1 << i
        return Relation(k, t)

    def conjoin(self, other, places_self, places_other, k):
        """The relation on k variables where self holds on `places_self` and other on `places_other`."""
        return Relation(k, self.extend(k, places_self).table & other.extend(k, places_other).table)


def index(x):
    return sum(int(v) << j for j, v in enumerate(x))


def assignment(i, k):
    return tuple(i >> j & 1 for j in range(k))


def from_predicate(k, f):
    return Relation(k, sum(1 << i for i in range(1 << k) if f(assignment(i, k))))


# ------------------------------------------------------------------ named relations (what problem families use)

def clause(signs):
    """OR of literals: signs[j] True for x_j, False for not x_j."""
    return from_predicate(len(signs), lambda x: any(v == s for v, s in zip(x, signs)))


def exactly(k, j):
    return from_predicate(k, lambda x: sum(x) == j)


def at_most(k, j):
    return from_predicate(k, lambda x: sum(x) <= j)


def at_least(k, j):
    return from_predicate(k, lambda x: sum(x) >= j)


def parity(k, p):
    return from_predicate(k, lambda x: sum(x) % 2 == p)


def nae(k):
    return from_predicate(k, lambda x: 0 < sum(x) < k)


def and_gate(k):
    """x_{k-1} = AND of x_0 .. x_{k-2}."""
    return from_predicate(k, lambda x: x[-1] == int(all(x[:-1])))


def or_gate(k):
    return from_predicate(k, lambda x: x[-1] == int(any(x[:-1])))


def random_relation(k, rng, density=0.5):
    return Relation(k, sum(1 << i for i in range(1 << k) if rng.random() < density))


def all_relations(k):
    return [Relation(k, t) for t in range(1, (1 << (1 << k)))]


def orbit_representatives(k):
    """One relation per class under renaming and negating variables (excluding the empty relation)."""
    seen, out = set(), []
    for r in all_relations(k):
        c, _ = r.canonical()
        if c.table not in seen:
            seen.add(c.table)
            out.append(c)
    return out


__all__ = ['MAX_ARITY', 'Relation', 'index', 'assignment', 'from_predicate', 'clause', 'exactly', 'at_most',
           'at_least', 'parity', 'nae', 'and_gate', 'or_gate', 'random_relation', 'all_relations',
           'orbit_representatives', 'product']
