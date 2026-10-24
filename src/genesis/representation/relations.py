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
        """(least table over the orbit, the (perm, flips) that reach it); ties to the first transform in the order
        of `canonical_slow`, which computes the same thing directly (the tests compare them)."""
        tv, _ = _orbit_values(self.k, self.table)
        t = int(tv.argmin())
        return Relation(self.k, int(tv[t])), _ops(self.k)[t]

    def canonical_slow(self):
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


class Partial(Relation):
    """A relation that cares only about some assignments: `care` (a table) marks them; outside it any value is allowed
    (a gadget need only be non-negative there). Encodings use it: a constraint on codes need not police invalid codes
    when a separate validity constraint does."""
    __slots__ = ('care',)

    def __init__(self, k, table, care):
        super().__init__(k, table & care)
        if not 0 <= care < (1 << (1 << k)):
            raise ValueError('care table out of range')
        self.care = int(care)

    def __eq__(self, other):
        return isinstance(other, Partial) and (self.k, self.table, self.care) == (other.k, other.table, other.care)

    def __hash__(self):
        return hash((self.k, self.table, self.care))

    def __repr__(self):
        return f'Partial({self.k}, {self.table:#x}, care {self.care:#x})'

    def cares(self, x):
        return bool(self.care >> index(x) & 1)

    def contains(self, x):
        """True when the assignment satisfies the constraint: a member, or outside the care set."""
        return (not self.cares(x)) or bool(self.table >> index(x) & 1)

    def to_json(self):
        return {'k': self.k, 'table': self.table, 'care': self.care}

    def transform(self, perm, flips):
        r = Relation(self.k, self.table).transform(perm, flips)
        c = Relation(self.k, self.care).transform(perm, flips)
        return Partial(self.k, r.table, c.table)

    def canonical(self):
        import numpy as np
        tv, _ = _orbit_values(self.k, self.table)
        cv, _ = _orbit_values(self.k, self.care)
        t = int(np.lexsort((tv, cv))[0])
        return Partial(self.k, int(tv[t]), int(cv[t])), _ops(self.k)[t]

    def canonical_slow(self):
        best = None
        for perm in permutations(range(self.k)):
            for flips in range(1 << self.k):
                t = self.transform(perm, flips)
                key = (t.care, t.table)
                if best is None or key < best[0]:
                    best = (key, t, (list(perm), flips))
        return best[1], best[2]

    def id(self):
        c, _ = self.canonical()
        return digest({'relation': 'genesis-partial-relation-v1', 'k': c.k, 'table': c.table, 'care': c.care})[:16]


_POW, _OPS = {}, {}


def _ops(k):
    if k not in _OPS:
        _OPS[k] = [(list(perm), flips) for perm in permutations(range(k)) for flips in range(1 << k)]
    return _OPS[k]


def _pow(k):
    """P[t, i] = 2 ** (the index that assignment i moves to under transform t), as uint64 (k <= 6: 64 bits)."""
    if k not in _POW:
        import numpy as np
        ops = _ops(k)
        M = np.empty((len(ops), 1 << k), dtype=np.uint64)
        for t, (perm, flips) in enumerate(ops):
            for i in range(1 << k):
                y = 0
                for j in range(k):
                    if i >> j & 1:
                        y |= 1 << perm[j]
                M[t, i] = y ^ flips
        _POW[k] = np.left_shift(np.uint64(1), M)
    return _POW[k]


def _orbit_values(k, table):
    """The table after every transform (uint64 array in `_ops(k)` order)."""
    import numpy as np
    bits = np.array([table >> i & 1 for i in range(1 << k)], dtype=bool)
    return _pow(k)[:, bits].sum(axis=1, dtype=np.uint64), bits


def relation_from_json(d):
    return Partial(d['k'], d['table'], d['care']) if 'care' in d else Relation(d['k'], d['table'])


def care_of(rel):
    return getattr(rel, 'care', (1 << (1 << rel.k)) - 1)


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


__all__ = ['MAX_ARITY', 'Relation', 'Partial', 'relation_from_json', 'care_of', 'index', 'assignment', 'from_predicate', 'clause', 'exactly', 'at_most',
           'at_least', 'parity', 'nae', 'and_gate', 'or_gate', 'random_relation', 'all_relations',
           'orbit_representatives', 'product']
