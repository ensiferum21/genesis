"""Statements about graph invariants, posed as text and evaluated exactly (research plane; the proving test's
transfer family, `docs/OMEGA_FRONTIER.md` §7b).

A statement is `[condition ->] condition`. A condition is `expr REL expr` (REL one of <=, <, >=, >, ==), a
boolean invariant, or several of these joined by `&`. It is meant for connected graphs. It is violated when the hypothesis holds (or there is none)
and the conclusion fails.

Expressions:
  * numbers; + - * /, where `/` is real division with x / 0 = 0, as in Lean; unary minus; parentheses;
  * `ceil`, `floor`, `sqrt`, `ln` (Lean's Real.log), `max(a, b)`, `min(a, b)`, `idiv(a, b)` (natural floor division, x idiv 0 = 0),
    `mod(a, b)` (natural remainder, x mod 0 = x), `nat_sub(a, b)` (truncated at 0), `ind(condition)` (1 or 0),
    `cond(condition, a, b)`;
  * the invariants of `VOCABULARY` by name, set functions such as `dist_min(max_degree_vertices)`, and any of these
    on a derived graph: `name@complement`, `name@square`.
Values are exact: integers, fractions, booleans, or numbers p + q sqrt(s) with rational p, q and one square-free
s per expression (`Surd`), so that ceilings, floors and comparisons of square roots are decided exactly. A
logarithm of a rational other than 1 is irrational, so it is held as a 70-digit `Bracket`, which decides its
floors, ceilings and signs or raises.

`Statement(text).check(graph)` gives the exact verdict and a float score for search: the score is positive exactly
when the statement is violated. `Statement.score(A)` is the attack interface (`attack.Runner(objective=...)`); it
scores -inf for a disconnected graph and for a graph above `max_n` vertices (where the exhaustive invariants stop
being practical).
"""
from fractions import Fraction
import math
import re

from . import invariants as I


# ------------------------------------------------------------------------------------------- exact numbers

def _square_free(s):
    """(k, t) with s = k^2 t and t square-free."""
    k, t, f = 1, s, 2
    while f * f <= t:
        while t % (f * f) == 0:
            t //= f * f
            k *= f
        f += 1
    return k, t


class Surd:
    """p + q sqrt(s), with p, q rational, s > 1 square-free, q != 0 (otherwise a plain Fraction is used)."""
    __slots__ = ('p', 'q', 's')

    def __init__(self, p, q, s):
        self.p, self.q, self.s = Fraction(p), Fraction(q), s

    @staticmethod
    def make(p, q, s):
        if q == 0 or s == 0:
            return Fraction(p)
        if s == 1:
            return Fraction(p) + Fraction(q)
        return Surd(p, q, s)

    def __float__(self):
        return float(self.p) + float(self.q) * math.sqrt(self.s)

    def __eq__(self, other):                       # normalised (s square-free, q != 0), so equal values match
        return isinstance(other, Surd) and (self.p, self.q, self.s) == (other.p, other.q, other.s)

    def __hash__(self):
        return hash((self.p, self.q, self.s))

    def __repr__(self):
        return f'Surd({self.p}, {self.q}, {self.s})'


class Bracket:
    """An irrational number known to lie strictly between two rationals (from `ln` of a rational other than 1, at
    70 digits). Sums with rationals, products with rationals, signs, floors and ceilings are decided from the bracket;
    if an integer or zero falls inside it, the evaluation raises rather than guess."""
    __slots__ = ('lo', 'hi')

    def __init__(self, lo, hi):
        self.lo, self.hi = Fraction(lo), Fraction(hi)

    def __float__(self):
        return float((self.lo + self.hi) / 2)

    def __repr__(self):
        return f'Bracket({float(self.lo)}, {float(self.hi)})'


def ln(x):
    """Lean's Real.log of a rational: log |x|, and 0 at 0; exact 0 at 1, otherwise a 70-digit `Bracket`."""
    if isinstance(x, (Surd, Bracket)):
        raise ValueError('ln of an irrational number')
    x = abs(Fraction(x))
    if x == 0 or x == 1:
        return Fraction(0)
    from decimal import Decimal, localcontext
    with localcontext() as c:
        c.prec = 80
        v = Fraction((Decimal(x.numerator) / Decimal(x.denominator)).ln())
    eps = Fraction(1, 10 ** 70)
    return Bracket(v - eps, v + eps)


def _parts(x, s=None):
    if isinstance(x, Surd):
        if s is not None and s != x.s:
            raise ValueError('two different square roots in one expression')
        return x.p, x.q, x.s
    return Fraction(x), Fraction(0), s


def _common(x, y):
    s = x.s if isinstance(x, Surd) else (y.s if isinstance(y, Surd) else None)
    a, b, _ = _parts(x, s)
    c, d, _ = _parts(y, s)
    return a, b, c, d, s


def add(x, y):
    if isinstance(x, Bracket) or isinstance(y, Bracket):
        if isinstance(x, Surd) or isinstance(y, Surd):
            raise ValueError('a logarithm and a square root in one expression')
        a = x if isinstance(x, Bracket) else Bracket(x, x)
        b = y if isinstance(y, Bracket) else Bracket(y, y)
        return Bracket(a.lo + b.lo, a.hi + b.hi)
    a, b, c, d, s = _common(x, y)
    return Surd.make(a + c, b + d, s) if s else a + c


def neg(x):
    if isinstance(x, Bracket):
        return Bracket(-x.hi, -x.lo)
    return Surd.make(-x.p, -x.q, x.s) if isinstance(x, Surd) else -Fraction(x)


def sub(x, y):
    return add(x, neg(y))


def mul(x, y):
    if isinstance(y, Bracket):
        x, y = y, x
    if isinstance(x, Bracket):
        if isinstance(y, (Surd, Bracket)):
            raise ValueError('a product of irrational numbers')
        f = Fraction(y)
        if f == 0:
            return Fraction(0)
        return Bracket(x.lo * f, x.hi * f) if f > 0 else Bracket(x.hi * f, x.lo * f)
    a, b, c, d, s = _common(x, y)
    if not s:
        return a * c
    return Surd.make(a * c + b * d * s, a * d + b * c, s)


def sign(x):
    """The exact sign of a number."""
    if isinstance(x, Bracket):
        if x.lo >= 0 or x.hi <= 0:
            return 1 if x.lo >= 0 else -1                      # the value is strictly inside the bracket
        raise ValueError('a sign the bracket does not decide')
    if not isinstance(x, Surd):
        x = Fraction(x)
        return (x > 0) - (x < 0)
    sp, sq = (x.p > 0) - (x.p < 0), (x.q > 0) - (x.q < 0)
    if sp == 0 or sp == sq:
        return sq
    # p and q sqrt(s) have opposite signs: compare p^2 with q^2 s
    c = x.p * x.p - x.q * x.q * x.s
    return sp if c > 0 else (sq if c < 0 else 0)


def inv(x):
    if sign(x) == 0:
        return Fraction(0)                                     # Lean: x / 0 = 0
    if isinstance(x, Bracket):
        return Bracket(1 / x.hi, 1 / x.lo)
    if not isinstance(x, Surd):
        return 1 / Fraction(x)
    den = x.p * x.p - x.q * x.q * x.s                          # nonzero: s is not a square
    return Surd.make(x.p / den, -x.q / den, x.s)


def div(x, y):
    return mul(x, inv(y))


def floor(x):
    if isinstance(x, Bracket):
        k = math.floor(x.lo)
        if x.hi <= k + 1:
            return k
        raise ValueError('a floor the bracket does not decide')
    if not isinstance(x, Surd):
        return math.floor(Fraction(x))
    k = math.floor(float(x))
    while sign(sub(x, k)) < 0:
        k -= 1
    while sign(sub(x, k + 1)) >= 0:
        k += 1
    return k


def ceil(x):
    return -floor(neg(x))


def sqrt(x):
    if isinstance(x, (Surd, Bracket)):
        raise ValueError('a square root of a square root')
    x = Fraction(x)
    if x < 0:
        return Fraction(0)                                     # Lean: Real.sqrt of a negative is 0
    p, q = x.numerator, x.denominator
    k, t = _square_free(p * q)                                 # sqrt(p/q) = sqrt(pq)/q = k sqrt(t) / q
    return Surd.make(0, Fraction(k, q), t)


def compare(x, y):
    return sign(sub(x, y))


# ------------------------------------------------------------------------------------------- the vocabulary

def _avg(vals):
    vals = list(vals)
    return Fraction(sum(vals), len(vals)) if vals else Fraction(0)


def _sq_degrees(G):
    D = G.dist()
    return [sum(1 for w in range(G.n) if w != v and D[v][w] <= 2) for v in range(G.n)]


def _sphere_max(G):
    D, r = G.dist(), I.radius(G)
    return max(sum(1 for w in range(G.n) if D[v][w] == r) for v in I.center(G))


def _has_c4(G):
    return any(bin(G.adj[a] & G.adj[c]).count('1') >= 2 for a in range(G.n) for c in range(a + 1, G.n))


def _center_neigh_alpha(G):
    mask = 0
    for u in I.center(G):
        mask |= G.adj[u]
    return I.indep_num_within(G, mask)


def _dist_evens(G):
    return [sum(1 for d in G.dist()[v] if d % 2 == 0) for v in range(G.n)]


SCALARS = {
    'n': lambda G: G.n,
    'size': lambda G: len(G.edges),
    'min_degree': I.min_degree, 'max_degree': I.max_degree, 'avg_degree': I.average_degree,
    'second_degree': I.second_smallest_degree,
    'alpha': I.indep_num, 'b': I.b, 'forest': I.largest_induced_forest, 'tree': I.largest_induced_tree,
    'path': I.path_number, 'ls': I.ls, 'indep_dom': I.indep_domination_number, 'matching': I.matching_number,
    'residue': I.residue, 'radius': I.radius, 'diameter': I.diameter, 'avg_ecc': I.average_eccentricity,
    'girth': I.girth, 'max_temp': I.max_temp, 'ng': I.ng, 'deg_sq_sum': I.degree_l2_norm_squared,
    'spanning_paths': I.min_spanning_paths, 'kappa': I.vertex_connectivity, 'alpha_core': I.alpha_core_size,
    'dp': I.dp,
    'avg_l': lambda G: _avg(I.indep_neighbours(G, v) for v in range(G.n)),
    'max_l': lambda G: max(I.indep_neighbours(G, v) for v in range(G.n)),
    'min_l': lambda G: min(I.indep_neighbours(G, v) for v in range(G.n)),
    'min_dist_even': lambda G: min(_dist_evens(G)),
    'max_dist_even': lambda G: max(_dist_evens(G)),
    'sphere_max': _sphere_max,
    'caro_wei': lambda G: sum(Fraction(1, d + 1) for d in G.degrees()),
    'center_neigh_alpha': _center_neigh_alpha,
    'ham_path': I.hamiltonian_path,
    'has_c4': _has_c4,
    'domination': I.domination_number,
    'total_dom': I.total_domination_number,
    'max_triangles': I.max_triangles,
    'freq_min_triangles': I.freq_min_triangles,
    'hh_zero_step': I.hh_zero_step,
    'max_even_correction': I.max_even_correction,
    'has_comp_edge': lambda G: I.min_complement_edge_neighbourhood(G) is not None,
    'min_comp_edge_nbhd': lambda G: I.min_complement_edge_neighbourhood(G) or 0,
    'wtd': I.well_totally_dominated,
    'pendants': I.pendants,
    'triangle_free': I.triangle_free,
    'alpha_two': I.alpha_two,
}

SETS = {
    'min_degree_vertices': I.min_degree_vertices,
    'max_degree_vertices': I.max_degree_vertices,
    'center': I.center,
    'periphery': I.periphery,
    'square_max_degree_vertices': lambda G: (lambda sq: [v for v in range(G.n) if sq[v] == max(sq)])(_sq_degrees(G)),
    'low_degree_vertices': I.low_degree_vertices,
    'high_degree_vertices': lambda G: [v for v in range(G.n) if G.degree(v) > 2],
}


def _dist_avg_all(G, S):
    D = G.dist()
    return _avg(D[v][w] for v in S for w in range(G.n) if D[v][w] != 0)


def _ecc_to(G, S):
    out = [min(G.dist()[v][s] for s in S) for v in range(G.n) if v not in S]
    return max(out) if out else 0


SET_FUNCTIONS = {
    'dist_min': I.dist_min,                     # min over distinct members (0 if fewer than two)
    'dist_max': I.dist_max_set,                 # max over all pairs of members
    'dist_avg': I.dist_avg_set,                 # mean over ordered distinct members (0 if none)
    'dist_avg_all': _dist_avg_all,              # mean of the nonzero distances from members to all vertices
    'ecc_set': I.ecc_set,                       # max over all vertices of the distance to the set
    'ecc_to': _ecc_to,                          # the same over the vertices outside the set (0 if none)
    'ecc_avg': lambda G, S: _avg(I.eccentricities(G)[v] for v in S),
    'max_degree_on': lambda G, S: max((G.degree(v) for v in S), default=0),
    'avg_degree_on': lambda G, S: _avg(G.degree(v) for v in S),
    'indep_on': I.indep_on,                     # the independence number of the induced subgraph
    'internal_edges': I.internal_edges,         # the edges with both ends in the set
}

TRANSFORMS = {'complement': lambda G: G.complement(), 'square': I.square}
FUNCTIONS = ('ceil', 'floor', 'sqrt', 'ln', 'max', 'min', 'idiv', 'mod', 'nat_sub', 'ind', 'cond')
SEEN_MAX = 200000          # the score memo's bound; at the bound it is cleared before a new entry
VOCABULARY = tuple(SCALARS) + tuple(SETS) + tuple(SET_FUNCTIONS)


# ------------------------------------------------------------------------------------------- parsing

_TOKEN = re.compile(r'\s*(?:(\d+)|([A-Za-z_][A-Za-z_0-9]*)|(->|<=|>=|==|[-+*/(),<>@&]))')


def tokens(text):
    out, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f'cannot read {text[pos:pos + 12]!r}')
        num, name, op = m.groups()
        out.append(('num', int(num)) if num else (('name', name) if name else ('op', op)))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, kind=None, value=None):
        k, v = self.peek()
        if k is None or (kind and k != kind) or (value is not None and v != value):
            raise ValueError(f'expected {value or kind}, found {v!r}')
        self.i += 1
        return v

    def statement(self):
        first = self.condition()
        if self.peek() == ('op', '->'):
            self.take()
            out = ('stmt', first, self.condition())
        else:
            out = ('stmt', None, first)
        if self.i != len(self.t):
            raise ValueError(f'unexpected {self.peek()[1]!r}')
        return out

    def condition(self):
        parts = [self.simple_condition()]
        while self.peek() == ('op', '&'):
            self.take()
            parts.append(self.simple_condition())
        return parts[0] if len(parts) == 1 else ('and', parts)

    def simple_condition(self):
        left = self.expr()
        k, v = self.peek()
        if k == 'op' and v in ('<=', '<', '>=', '>', '=='):
            self.take()
            return ('rel', v, left, self.expr())
        return ('truth', left)

    def expr(self):
        node = self.term()
        while self.peek() in (('op', '+'), ('op', '-')):
            node = (self.take(), node, self.term())
        return node

    def term(self):
        node = self.unary()
        while self.peek() in (('op', '*'), ('op', '/')):
            node = (self.take(), node, self.unary())
        return node

    def unary(self):
        if self.peek() == ('op', '-'):
            self.take()
            return ('neg', self.unary())
        return self.atom()

    def atom(self):
        k, v = self.peek()
        if k == 'num':
            self.take()
            return ('num', v)
        if (k, v) == ('op', '('):
            self.take()
            node = self.expr()
            self.take('op', ')')
            return node
        name = self.take('name')
        if name in FUNCTIONS:
            self.take('op', '(')
            args = [self.condition() if name in ('ind', 'cond') else self.expr()]
            while self.peek() == ('op', ','):
                self.take()
                args.append(self.expr())
            self.take('op', ')')
            want = {'ceil': 1, 'floor': 1, 'sqrt': 1, 'ln': 1, 'ind': 1, 'cond': 3}.get(name, 2)
            if len(args) != want:
                raise ValueError(f'{name} takes {want} arguments')
            return ('fn', name, args)
        if name in SET_FUNCTIONS:
            self.take('op', '(')
            arg = self.take('name')
            if arg not in SETS:
                raise ValueError(f'{arg!r} is not a vertex set')
            self.take('op', ')')
            node = ('setfn', name, arg)
        elif name in SCALARS:
            node = ('inv', name)
        else:
            raise ValueError(f'unknown name {name!r}')
        if self.peek() == ('op', '@'):
            self.take()
            tr = self.take('name')
            if tr not in TRANSFORMS:
                raise ValueError(f'unknown graph {tr!r}')
            node = ('on', tr, node)
        return node


def parse(text):
    return _Parser(tokens(text)).statement()


# ------------------------------------------------------------------------------------------- evaluation

class _Context:
    def __init__(self, G):
        self.graphs = {None: G}
        self.cache = {}

    def graph(self, tr):
        if tr not in self.graphs:
            self.graphs[tr] = TRANSFORMS[tr](self.graphs[None])
        return self.graphs[tr]


def _num(x):
    return Fraction(int(x)) if isinstance(x, bool) else (x if isinstance(x, (Surd, Bracket)) else Fraction(x))


def value(node, ctx, tr=None):
    op = node[0]
    if op == 'num':
        return Fraction(node[1])
    if op == 'inv' or op == 'setfn':
        key = (tr, node)
        if key not in ctx.cache:
            G = ctx.graph(tr)
            if op == 'inv':
                v = SCALARS[node[1]](G)
            else:
                v = SET_FUNCTIONS[node[1]](G, SETS[node[2]](G))
            ctx.cache[key] = v if isinstance(v, bool) else Fraction(v)
        return ctx.cache[key]
    if op == 'on':
        return value(node[2], ctx, node[1])
    if op == 'neg':
        return neg(_num(value(node[1], ctx)))
    if op in ('+', '-', '*', '/'):
        a, b = _num(value(node[1], ctx)), _num(value(node[2], ctx))
        return {'+': add, '-': sub, '*': mul, '/': div}[op](a, b)
    if op == 'fn':
        name, args = node[1], node[2]
        if name == 'ind':
            return Fraction(1 if holds(args[0], ctx) else 0)
        if name == 'cond':
            return value(args[1], ctx) if holds(args[0], ctx) else value(args[2], ctx)
        vals = [_num(value(a, ctx)) for a in args]
        if name == 'ceil':
            return Fraction(ceil(vals[0]))
        if name == 'floor':
            return Fraction(floor(vals[0]))
        if name == 'sqrt':
            return sqrt(vals[0])
        if name == 'ln':
            return ln(vals[0])
        a, b = vals
        if name == 'max':
            return a if compare(a, b) >= 0 else b
        if name == 'min':
            return a if compare(a, b) <= 0 else b
        if isinstance(a, (Surd, Bracket)) or isinstance(b, (Surd, Bracket)):
            raise ValueError(f'{name} of an irrational number')
        if name == 'nat_sub':
            return max(Fraction(0), a - b)
        if a.denominator != 1 or b.denominator != 1 or a < 0 or b < 0:
            raise ValueError(f'{name} needs natural numbers')
        a, b = int(a), int(b)
        if name == 'idiv':
            return Fraction(0 if b == 0 else a // b)
        return Fraction(a if b == 0 else a % b)            # mod
    raise ValueError(f'cannot evaluate {op!r}')


def holds(cond, ctx):
    if cond[0] == 'and':
        return all(holds(c, ctx) for c in cond[1])
    if cond[0] == 'truth':
        v = value(cond[1], ctx)
        if not isinstance(v, bool):
            raise ValueError('a number used as a condition')
        return v
    _, rel, a, b = cond
    c = compare(_num(value(a, ctx)), _num(value(b, ctx)))
    return {'<=': c <= 0, '<': c < 0, '>=': c >= 0, '>': c > 0, '==': c == 0}[rel]


def slack(cond, ctx):
    """A float that is >= 0 when the condition holds and < 0 when it fails, except that a strict relation at
    equality has slack 0 and fails; `check` uses `holds` for the verdict."""
    if cond[0] == 'and':
        return min(slack(c, ctx) for c in cond[1])
    if cond[0] == 'truth':
        return 1.0 if value(cond[1], ctx) else -1.0
    _, rel, a, b = cond
    d = float(sub(_num(value(b, ctx)), _num(value(a, ctx))))      # b - a
    return {'<=': d, '<': d, '>=': -d, '>': -d, '==': -abs(d)}[rel]


class Statement:
    def __init__(self, text, max_n=18):
        self.text, self.tree, self.max_n = text, parse(text), max_n
        self._seen = {}

    def check(self, G):
        """{'violated': bool, 'score': float} for a connected graph; the score is positive exactly when violated."""
        ctx = _Context(G)
        _, hyp, concl = self.tree
        h_ok = True if hyp is None else holds(hyp, ctx)
        c_ok = holds(concl, ctx) if h_ok else None
        violated = h_ok and not c_ok
        c_slack = slack(concl, ctx)
        raw = -c_slack if hyp is None else min(slack(hyp, ctx), -c_slack)
        raw = min(raw, 0.0) if not violated else max(raw, 0.0)
        return {'violated': bool(violated), 'score': raw + (1.0 if violated else 0.0)}

    def score(self, A):
        """The attack interface: A is a 0/1 adjacency matrix (numpy)."""
        n = A.shape[0]
        if n < 2 or n > self.max_n:
            return -math.inf
        edges = tuple((i, j) for i in range(n) for j in range(i + 1, n) if A[i, j])
        key = (n, edges)
        if key not in self._seen:
            G = I.Graph(n, edges)
            v = self.check(G)['score'] if G.connected() else -math.inf
            if len(self._seen) >= SEEN_MAX:          # bounded memo: cleared before the new entry (B20R177-SEEN)
                self._seen.clear()
            self._seen[key] = v
        return self._seen[key]
