"""Objects and decoders: encodings of finite-domain variables in binary variables, searched, not chosen from a list
(directive item 6).

An encoding of a domain {0, ..., D-1} in b bits is a code table: D distinct bit patterns, value v -> code[v]. Its
**decoder** maps a pattern back to its value (None for a pattern outside the table). Its **validity relation** (on b
bits) is the set of used patterns; when every pattern is used, there is no validity constraint at all. A relation on
values of r variables **lifts** to a relation on r x b bits: every block is a valid code and the decoded values satisfy
the relation. One-hot (b = D, the codes with a single 1), binary (b = ceil(log2 D)) and unary codes are points of
this space; so is every other injective table.

`search(D, value_relations, counts, b_range)` enumerates code tables up to the symmetries that cannot change their
cost (renaming and negating bits), synthesises the gadgets each table needs (validity, and every lifted relation),
and scores a table by what the problem would pay: sum over relations of count x (ancillas, non-zero coefficients),
plus validity per variable. The cheapest table is the invented representation; its gadgets go into the library with
their lineage. `compile_fd(problem, encoding, lib)` turns a finite-domain constraint problem into a binary one (and
then, through `compile`, into one BQP); `decode_fd` reads values back; `verify_fd` checks the values against the
problem directly.
"""
from itertools import combinations, permutations, product

from .relations import Partial, Relation, from_predicate
from . import gadgets as GD
from . import library as LB


class Encoding:
    __slots__ = ('D', 'b', 'code')

    def __init__(self, D, b, code):
        code = [tuple(int(v) for v in c) for c in code]
        if len(code) != D or len(set(code)) != D or any(len(c) != b for c in code):
            raise ValueError('a code table is D distinct patterns of b bits')
        self.D, self.b, self.code = D, b, code

    def decode(self, bits):
        bits = tuple(int(v) for v in bits)
        return self.code.index(bits) if bits in self.code else None

    def validity(self):
        """The relation of used patterns, or None when every pattern is used."""
        if self.D == 1 << self.b:
            return None
        return from_predicate(self.b, lambda z: tuple(z) in self.code)

    def lift(self, rel_values, r):
        """The relation on r * b bits that the decoded values satisfy rel_values (a predicate on an r-tuple of
        values). When some patterns are unused it is a Partial relation that cares only where every block is a valid
        code: invalid codes are the validity constraint's business, so the lifted constraint need not police them."""
        b = self.b

        def vals(z):
            return [self.decode(z[i * b:(i + 1) * b]) for i in range(r)]
        rel = from_predicate(r * b, lambda z: all(v is not None for v in vals(z)) and bool(rel_values(tuple(vals(z)))))
        if self.validity() is None:
            return rel
        care = from_predicate(r * b, lambda z: all(v is not None for v in vals(z)))
        return Partial(r * b, rel.table, care.table)

    def to_json(self):
        return {'D': self.D, 'b': self.b, 'code': [list(c) for c in self.code]}

    @staticmethod
    def from_json(d):
        return Encoding(d['D'], d['b'], d['code'])

    def __repr__(self):
        return f"Encoding({self.D}, {self.b}, {[''.join(map(str, c)) for c in self.code]})"


def one_hot(D):
    return Encoding(D, D, [tuple(int(i == v) for i in range(D)) for v in range(D)])


def binary(D):
    b = max(1, (D - 1).bit_length())
    return Encoding(D, b, [tuple(v >> i & 1 for i in range(b)) for v in range(D)])


def tables(D, b, symmetric=True):
    """Code tables of D values in b bits, one per class under renaming and negating bits (if `symmetric`), with the
    values' order free only up to what the relations distinguish (all orders kept: relations may not be symmetric)."""
    pats = list(product((0, 1), repeat=b))
    seen = set()
    for chosen in combinations(pats, D):
        if symmetric:
            key = None
            for perm in permutations(range(b)):
                for flips in range(1 << b):
                    t = tuple(sorted(tuple(p[perm[j]] ^ (flips >> j & 1) for j in range(b)) for p in chosen))
                    key = t if key is None or t < key else key
            if key in seen:
                continue
            seen.add(key)
        for order in permutations(chosen):
            yield Encoding(D, b, order)


def factorize(enc, pred, r, max_size=3):
    """Discover a conjunction of small relations equal to the lifted relation on valid codes (an operator: relation
    factorisation). Projections of the members onto bit subsets of size 1..max_size that exclude some valid
    non-member are candidate factors; a greedy cover keeps few of them. Returns (pieces, uniform) with pieces =
    [(bit positions, Partial relation on them)] and uniform True when every valid non-member violates exactly one
    piece (a sum of uniform piece gadgets then counts violated constraints); None if no exact factorisation."""
    b, n = enc.b, r * enc.b

    def vals(z):
        return [enc.decode(z[i * b:(i + 1) * b]) for i in range(r)]
    care = [z for z in product((0, 1), repeat=n) if all(v is not None for v in vals(z))]
    mem = [z for z in care if pred(tuple(vals(z)))]
    non = [z for z in care if not pred(tuple(vals(z)))]
    if not non:
        return [], True
    cands = []
    for size in range(1, max_size + 1):
        for S in combinations(range(n), size):
            allowed = {tuple(z[i] for i in S) for z in mem}
            seen = {tuple(z[i] for i in S) for z in care}
            excl = frozenset(k for k, z in enumerate(non) if tuple(z[i] for i in S) not in allowed)
            if excl:
                cands.append((S, allowed, seen, excl))
    left, cover = set(range(len(non))), []
    while left:
        best = max(cands, key=lambda c: (len(c[3] & left), -len(c[0])), default=None)
        if best is None or not best[3] & left:
            return None
        cover.append(best)
        left -= best[3]
    pieces = []
    for S, allowed, seen, _ in cover:
        k = len(S)
        from .relations import index as _ix
        table = sum(1 << _ix(p) for p in allowed)
        care_t = sum(1 << _ix(p) for p in seen)
        pieces.append((list(S), Partial(k, table, care_t) if care_t != (1 << (1 << k)) - 1 else Relation(k, table)))
    uniform = all(sum(not p[1].contains([z[i] for i in p[0]]) for p in pieces) == 1 for z in non)
    return pieces, uniform


def _gadget_for(rel, uniform, lib, synth, why):
    g = LB.lookup(lib, rel, uniform)
    if g is None:
        g, rep = synth(rel, uniform)
        if g is None:
            return None, lib
        lib = LB.register(lib, rel, g, {'synthesizer': rep['synthesizer'], 'tried': rep.get('tried'), 'for': why})
    return g, lib


def cost(enc, value_relations, counts, n_vars, lib, synth):
    """What the problem pays with this encoding: (total ancillas, total non-zero coefficients, the library with every
    needed gadget, the plan); None if some needed relation has no gadget within the synthesiser's limits. For each
    value relation the plan takes the cheaper of the whole lifted relation (when its arity allows) and an exact
    factorisation into small relations (`factorize`), by (ancillas, non-zero coefficients)."""
    total_anc, total_nz, plan = 0, 0, {}
    v = enc.validity()
    if v is not None:
        g, lib = _gadget_for(v, False, lib, synth, f'encoding {enc.to_json()} validity')
        if g is None:
            return None
        nz, _ = g.size()
        total_anc += n_vars * g.m
        total_nz += n_vars * nz
        plan['validity'] = {'form': 'whole', 'pieces': [{'bits': list(range(enc.b)), 'relation': v.to_json()}],
                            'ancillas': g.m, 'nonzero': nz, 'count': n_vars}
    for name, (pred, r) in value_relations.items():
        options = []
        if r * enc.b <= GD.MAX_VARS and r * enc.b <= 6:
            rel = enc.lift(pred, r)
            g, lib = _gadget_for(rel, True, lib, synth, f'encoding {enc.to_json()} relation {name}')
            if g is not None:
                options.append((g.m, g.size()[0], 'whole', [{'bits': list(range(r * enc.b)), 'relation': rel.to_json()}]))
        fac = factorize(enc, pred, r) if r * enc.b <= 12 else None
        if fac is not None and fac[1]:
            pieces, anc, nz, ok = [], 0, 0, True
            for bits, prel in fac[0]:
                g, lib = _gadget_for(prel, True, lib, synth, f'encoding {enc.to_json()} relation {name} factor')
                if g is None:
                    ok = False
                    break
                anc += g.m
                nz += g.size()[0]
                pieces.append({'bits': bits, 'relation': prel.to_json()})
            if ok:
                options.append((anc, nz, 'factors', pieces))
        if not options:
            return None
        anc, nz, form, pieces = min(options, key=lambda o: (o[0], o[1], o[2]))
        total_anc += counts[name] * anc
        total_nz += counts[name] * nz
        plan[name] = {'form': form, 'pieces': pieces, 'ancillas': anc, 'nonzero': nz, 'count': counts[name]}
    return total_anc, total_nz, lib, plan


def search(D, value_relations, counts, n_vars, b_range, lib=None, synth=None, limit=None):
    """The cheapest encoding by (variables = n_vars * b + ancillas, then non-zero coefficients) over every table with
    b in b_range; returns (best, library, table of every evaluated encoding)."""
    lib = LB.EMPTY if lib is None else lib
    synth = synth or (lambda rel, uniform: GD.synthesize_milp(rel, max_ancillas=2, bound=8, uniform=uniform,
                                                              time_limit=20))
    scored, best = [], None
    k = 0
    for b in b_range:
        if b < max(1, (D - 1).bit_length()) or b > GD.MAX_VARS:
            continue
        for enc in tables(D, b):
            k += 1
            if limit is not None and k > limit:
                break
            c = cost(enc, value_relations, counts, n_vars, lib, synth)
            if c is None:
                scored.append({'encoding': enc.to_json(), 'feasible': False})
                continue
            anc, nz, lib, det = c
            row = {'encoding': enc.to_json(), 'feasible': True, 'variables': n_vars * b + anc, 'nonzero': nz,
                   'details': det}
            scored.append(row)
            if best is None or (row['variables'], row['nonzero']) < (best['variables'], best['nonzero']):
                best = row
    return best, lib, scored


# ------------------------------------------------------------------ finite-domain problems through an encoding

def compile_fd(problem, enc, value_relations, plan=None, validity_weight=None):
    """A finite-domain problem {'n', 'D', 'constraints': [{'name', 'vars': [...], 'weight'}]} (the names index
    value_relations: name -> (predicate on a tuple of values, arity)) as a binary constraint problem for `compile`:
    variable v's bits are v * b .. v * b + b - 1. Each constraint becomes its plan's pieces (the whole lifted relation,
    or its factors), each with the constraint's weight. A validity constraint per variable when the code leaves
    patterns unused, marked hard, of weight `validity_weight` (default 1 + the total constraint weight, so no
    assignment buys constraints with an invalid code: exact)."""
    b = enc.b
    cons = []
    total = sum(c.get('weight', 1) for c in problem['constraints'])
    W = 1 + total if validity_weight is None else validity_weight
    v = enc.validity()
    if v is not None:
        for x in range(problem['n']):
            cons.append({'relation': v.to_json(), 'vars': list(range(x * b, x * b + b)), 'weight': W, 'hard': True})
    for c in problem['constraints']:
        pred, r = value_relations[c['name']]
        bits = [x * b + j for x in c['vars'] for j in range(b)]
        if plan is None or c['name'] not in plan:
            cons.append({'relation': enc.lift(pred, r).to_json(), 'vars': bits, 'weight': c.get('weight', 1)})
            continue
        for piece in plan[c['name']]['pieces']:
            cons.append({'relation': piece['relation'], 'vars': [bits[i] for i in piece['bits']],
                         'weight': c.get('weight', 1)})
    return {'n': problem['n'] * b, 'constraints': cons, 'objective': None}


def decode_fd(bits, enc, n):
    return [enc.decode(bits[x * enc.b:(x + 1) * enc.b]) for x in range(n)]


def verify_fd(problem, values, value_relations):
    """Total weight of violated constraints, from the values alone (an invalid value violates everything it is in)."""
    viol = 0
    for c in problem['constraints']:
        pred, _ = value_relations[c['name']]
        vals = tuple(values[x] for x in c['vars'])
        if any(v is None for v in vals) or not pred(vals):
            viol += c.get('weight', 1)
    return viol


__all__ = ['Encoding', 'one_hot', 'binary', 'tables', 'factorize', 'cost', 'search', 'compile_fd', 'decode_fd', 'verify_fd',
           'Relation']
