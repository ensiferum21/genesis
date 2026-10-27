"""The proving test's transfer family (KERNEL SIDE; `docs/OMEGA_FRONTIER.md` §7b): Graffiti.pc conjectures from
E. DeLaVina's "Written on the Wall II", as formalised in Lean in `google-deepmind/formal-conjectures`
(FormalConjectures/WrittenOnTheWallII, Apache 2.0, read at commit c0c5380). The statuses come from those files:
`research solved` with the conjecture as stated is PROVED; `research solved` stated as `¬ ∀ ...` is DISPROVED (a
counterexample exists); `research open` is OPEN.

Each statement is transcribed from its Lean text into `evaluate(G)`, exact on a connected graph (`invariants.Graph`):
  * an inequality gives (lhs, rhs) with exact rationals, and is violated when lhs > rhs (a counterexample);
  * an implication gives (hypothesis, conclusion), violated when the hypothesis holds and the conclusion fails;
  * a statement with a side condition (`0 < dp G`, ...) is vacuous where the condition fails.
Real division by zero is 0, as in Lean; natural subtraction and division truncate where Lean's do; every square root
appears under a ceiling and is computed exactly (`ceil_sqrt`, `ceil_affine_sqrt`).

Not transcribed (their definitions need more machinery): 103 (a logarithm), 160, 291, 309, 314, 315, 316, 322, 327,
438b. Kept: 53 of the 63 (23 proved, 21 disproved, 9 open); their statuses were checked against the Lean
categories and the leading negation of each statement.
"""
from fractions import Fraction
import math

from contextlib import contextmanager

from . import invariants as _research
from . import invariants_ref as _reference


class _Implementation:
    """The invariants the evaluators below call (`I.name`): the research plane's `invariants.py` by default, or the
    kernel's independent `invariants_ref.py` inside `implementation(_reference)`."""
    def __init__(self):
        self.module = _research

    def __getattr__(self, name):
        return getattr(self.module, name)


I = _Implementation()


@contextmanager
def implementation(module):
    old, I.module = I.module, module
    try:
        yield
    finally:
        I.module = old


def evaluate_both(number, n, edges):
    """The statement's verdict on a graph by both implementations: (research, reference) evaluations."""
    with implementation(_research):
        a = ALL[number][1](_research.Graph(n, edges))
    with implementation(_reference):
        b = ALL[number][1](_reference.Graph(n, edges))
    return a, b


def floor(x):
    return math.floor(Fraction(x))


def ceil(x):
    return math.ceil(Fraction(x))


def ceil_sqrt(x):
    """ceil(sqrt(x)) for a nonnegative rational x, exactly."""
    x = Fraction(x)
    p, q = x.numerator, x.denominator
    k = math.isqrt(p // q)
    while k * k * q < p:
        k += 1
    while k > 0 and (k - 1) * (k - 1) * q >= p:
        k -= 1
    return k


def ceil_affine_sqrt(a, s, c):
    """ceil((a + sqrt(s)) / c) for rationals a, c > 0 and integer s >= 0, exactly."""
    a, c = Fraction(a), Fraction(c)
    k = math.floor((a + math.isqrt(s)) / c) - 1
    while True:                                    # the smallest k with k*c - a >= sqrt(s)
        t = k * c - a
        if t >= 0 and t * t >= s:
            return k
        k += 1


def div(x, y):
    return Fraction(0) if y == 0 else Fraction(x) / Fraction(y)


def has_c4(G):
    for a in range(G.n):
        for c in range(G.n):
            if c != a and bin(G.adj[a] & G.adj[c]).count('1') >= 2:
                return True
    return False


def max_indep_neighbours(G):
    return I.max_indep_neighbours(G)


def min_dist_even(G):
    return min(I.dist_even(G, v) for v in range(G.n))


def square_max_degree_vertices(G):
    D = G.dist()
    sq = [sum(1 for w in range(G.n) if w != v and D[v][w] <= 2) for v in range(G.n)]
    m = max(sq)
    return [v for v in range(G.n) if sq[v] == m]


def periphery_max_degree(G):
    return max(G.degree(v) for v in I.periphery(G))


def square_periphery_average(G):
    S = I.square(G)
    per = I.periphery(S)
    return div(sum(S.degree(v) for v in per), len(per))


def dist_avg_pairs_nonzero(G, S):
    """The average of dist(v, w) over v in S, w any vertex, dist != 0 (Conjectures 33 and 34)."""
    D = G.dist()
    ds = [D[v][w] for v in S for w in range(G.n) if D[v][w] != 0]
    return div(sum(ds), len(ds))


def ecc_to(G, S):
    """ecc G S: the maximum over v outside S of the distance from v to S (0 if S is everything)."""
    out = [I.dist_to_set(G, v, S) for v in range(G.n) if v not in S]
    return max(out) if out else 0


def sphere_max(G):
    D, r = G.dist(), I.radius(G)
    return max(sum(1 for w in range(G.n) if D[v][w] == r) for v in I.center(G))


def caro_wei(G):
    return sum(Fraction(1, d + 1) for d in G.degrees())


def center_neighbourhood_indep(G):
    C = set(I.center(G))
    N = 0
    for v in range(G.n):
        if any(G.adj[u] >> v & 1 for u in C):
            N |= 1 << v
    return I.indep_num_within(G, N)


def ineq(lhs, rhs):
    return {'kind': 'ineq', 'lhs': Fraction(lhs), 'rhs': Fraction(rhs)}


def imp(hyp, concl):
    return {'kind': 'imp', 'hyp': bool(hyp), 'concl': bool(concl)}


def vacuous():
    return {'kind': 'vacuous'}


# number: (status, evaluate, short text)
def _s1(G): return ineq(G.n + 1 - 2 * I.matching_number(G), I.ls(G))
def _s2(G): return ineq(2 * (I.average_indep_neighbours(G) - 1), I.ls(G))
def _s3(G): return ineq(I.indep_domination_number(G) * I.max_temp(G), I.ls(G))
def _s4(G): return ineq(I.ng(G) - 1, I.ls(G))
def _s5(G): return ineq(sphere_max(G), I.ls(G))
def _s6(G): return ineq(1 + G.n - I.matching_number(G) - I.indep_num(G), I.ls(G))
def _s7(G): return ineq(max_indep_neighbours(G) - 1 + G.n - 2 * I.indep_num(G), I.ls(G))
def _s13(G): return ineq(I.diameter(G) + max_indep_neighbours(G) - 1, I.b(G))
def _s16(G): return ineq(2 * (I.radius(G) - 1) + max_indep_neighbours(G), I.b(G))
def _s17(G): return ineq(I.indep_num(G) + ceil(Fraction(I.diameter(G), 3)), I.b(G))
def _s18(G): return ineq(I.indep_num(G) + ceil_sqrt(I.dist_max_set(G, I.max_degree_vertices(G))), I.b(G))
def _s20(G): return ineq(div(G.n, floor(I.average_degree(G))), I.b(G))
def _s31(G): return ineq(2 * I.radius(G) - 1, I.path_number(G))


def _s100(G):
    rhs = ceil_affine_sqrt(2 * max_indep_neighbours(G), I.degree_l2_norm_squared(G.complement()), 4)
    return ineq(I.indep_num(G), rhs)                 # ceil((maxL + sqrt(S)/2) / 2) = ceil((2 maxL + sqrt(S)) / 4)


def _s101(G): return ineq(I.indep_num(G), (G.n + I.alpha_core_size(G)) // 2)
def _s141(G): return ineq(Fraction(I.girth(G), 2) - 1 + max_indep_neighbours(G), I.largest_induced_tree(G))
def _s142(G): return ineq(Fraction(2, 3) * I.girth(G) + I.ecc_set(G, I.periphery(G)), I.largest_induced_tree(G))


def _s143(G):
    s = I.second_smallest_degree(G)
    return vacuous() if s <= 0 else ineq(I.girth(G) + 1, I.largest_induced_tree(G) * s)


def _s144(G): return ineq(I.girth(G) - 1 + ecc_to(G, I.center(G)), I.largest_induced_tree(G))


def _s145(G):
    lm = I.min_indep_neighbours(G.complement())
    return vacuous() if lm <= 0 else ineq(2 * I.ecc_set(G, I.periphery(G)), I.largest_induced_tree(G) * lm)


def _s146(G):
    r2 = I.radius(I.square(G))
    return vacuous() if r2 <= 0 else ineq(2 * I.ecc_set(G, I.periphery(G)), I.largest_induced_tree(G) * r2)


def _s198a(G): return imp(I.b(G) <= 2 + I.average_eccentricity(G), I.hamiltonian_path(G))
def _s217(G): return imp(I.ls(G) <= 4 * (1 if I.residue(G) == 2 else 0) + 2, I.hamiltonian_path(G))
# disproved (the conjecture as it was posed; the Lean files state its negation)
def _s23(G): return ineq(floor(I.indep_num(G) + I.dist_avg_set(G, I.max_degree_vertices(G)) / 2), I.b(G))
def _s24(G): return ineq(max_indep_neighbours(G) + ceil(Fraction(min_dist_even(G), 3)), I.b(G))
def _s25(G): return ineq(2 * ceil(Fraction(1 + min_dist_even(G), 3)), I.b(G))


def _s32(G):
    A, M = I.min_degree_vertices(G), I.max_degree_vertices(G)
    D = G.dist()
    da = div(sum(D[a][c] for a in A for c in A if a != c), len(A) * (len(A) - 1))
    eccavg = div(sum(I.eccentricities(G)[v] for v in M), len(M))
    return ineq(da + Fraction(1, 2) * eccavg, I.path_number(G))


def _s33(G): return ineq(ceil(2 * dist_avg_pairs_nonzero(G, I.max_degree_vertices(G))), I.path_number(G))


def _s34(G):
    return ineq(ceil(dist_avg_pairs_nonzero(G, I.center(G)) + dist_avg_pairs_nonzero(G, I.max_degree_vertices(G))),
                I.path_number(G))


def _s36(G):
    d = I.dp(G)
    return vacuous() if d <= 0 else ineq(Fraction(2 * I.radius(G), d), I.path_number(G))


def _s58(G):
    la = I.average_indep_neighbours(G)
    return ineq(max(0, ceil(div(I.b(G), la))), I.largest_induced_forest(G))


def _s59(G): return ineq(ceil_sqrt(I.residue(G) * I.b(G)), I.largest_induced_forest(G))
def _s63(G): return ineq(ceil(Fraction(min_dist_even(G) + I.b(G) + 1, 3)), I.largest_induced_forest(G))


def _s64(G):
    return ineq(ceil_sqrt(I.indep_num(G) * (1 + G.n % I.max_degree(G))), I.largest_induced_forest(G))


def _s65(G):
    return ineq(I.dist_min(G, I.min_degree_vertices(G)) + ceil(Fraction(I.dist_min(G, I.max_degree_vertices(G)), 3)),
                I.largest_induced_forest(G))


def _s85(G): return ineq(ceil_sqrt(1 + 2 * min_dist_even(G)), I.largest_induced_tree(G))
def _s91(G): return ineq(I.b(G), 1 + Fraction(I.largest_induced_forest(G) * ceil(I.average_indep_neighbours(G)), 2))
def _s109(G): return ineq(I.indep_num(G), floor(Fraction(I.residue(G) + 2 * I.b(G), 3)))


def _s172(G):
    return ineq(-1 + periphery_max_degree(G) + I.dist_min(G, square_max_degree_vertices(G)), I.ls(G))


def _s176(G): return ineq(G.n + I.dist_min(G, square_max_degree_vertices(G)), I.ls(G) + I.b(G))
def _s181(G): return ineq(I.indep_num(G) + square_periphery_average(G), I.ls(G) + I.b(G))
def _s194(G): return imp(I.indep_num(G) <= 1 + I.average_indep_neighbours(G), I.hamiltonian_path(G))


def _s200(G):
    return imp(I.largest_induced_tree(G) == ceil(1 + I.average_indep_neighbours(G)), I.hamiltonian_path(G))


def _s430a(G):
    if G.n <= 3:
        return vacuous()
    return ineq(I.indep_domination_number(G), center_neighbourhood_indep(G) + 2 * floor(caro_wei(G) - 1))


# open
def _s19(G): return ineq(floor(I.average_eccentricity(G) + max_indep_neighbours(G)), I.b(G))


def _s40(G):
    return ineq(ceil(Fraction(I.min_spanning_paths(G) + I.b(G) + 1, 2)), I.largest_induced_forest(G))


def _s61(G): return ineq(I.residue(G) + ceil(Fraction(I.diameter(G), 3)), I.largest_induced_forest(G))


def _s72(G):
    return ineq(ceil(I.average_eccentricity(G) + Fraction(max_indep_neighbours(G), 3)), I.largest_induced_tree(G))


def _s84(G):
    d = I.min_degree(G)
    return vacuous() if d <= 0 else ineq(Fraction(2 * I.radius(G), d), I.largest_induced_tree(G))


def _s96(G):
    return ineq(I.indep_num(G), 1 + min_dist_even(G) * (max_indep_neighbours(G) - 1))


def _s133(G):
    l = I.average_indep_neighbours(G)
    return ineq(I.radius(G) + (Fraction(1) if has_c4(G) else l), I.path_number(G))


def _s189(G):
    return imp(max(I.dist_even(G, v) for v in range(G.n)) <= 1 + I.second_smallest_degree(G), I.hamiltonian_path(G))


def _s199(G):
    return imp(max(0, I.largest_induced_tree(G) - 2) <= I.vertex_connectivity(G), I.hamiltonian_path(G))


PROVED = {1: _s1, 2: _s2, 3: _s3, 4: _s4, 5: _s5, 6: _s6, 7: _s7, 13: _s13, 16: _s16, 17: _s17, 18: _s18, 20: _s20,
          31: _s31, 100: _s100, 101: _s101, 141: _s141, 142: _s142, 143: _s143, 144: _s144, 145: _s145, 146: _s146,
          '198a': _s198a, 217: _s217}
DISPROVED = {23: _s23, 24: _s24, 25: _s25, 32: _s32, 33: _s33, 34: _s34, 36: _s36, 58: _s58, 59: _s59, 63: _s63,
             64: _s64, 65: _s65, 85: _s85, 91: _s91, 109: _s109, 172: _s172, 176: _s176, 181: _s181, 194: _s194,
             200: _s200, '430a': _s430a}
OPEN = {19: _s19, 40: _s40, 61: _s61, 72: _s72, 84: _s84, 96: _s96, 133: _s133, 189: _s189, 199: _s199}
ALL = {**{k: ('proved', f) for k, f in PROVED.items()}, **{k: ('disproved', f) for k, f in DISPROVED.items()},
       **{k: ('open', f) for k, f in OPEN.items()}}


# ------------------------------------------------------------------------------- the statements as posed
# What the research plane is given: each statement as text in its statement language (`statement.py`), written a
# second time from the Lean text, not from the evaluators above. The two transcriptions are compared on every
# connected graph up to 7 vertices, on the documented counterexamples and on random graphs
# (`tests_genesis/test_wowii.py`). Both are the builder's, so this is a consistency check, not an independent source.
TEXT = {
    1: 'n + 1 - 2*matching <= ls',
    2: '2*(avg_l - 1) <= ls',
    3: 'indep_dom*max_temp <= ls',
    4: 'ng - 1 <= ls',
    5: 'sphere_max <= ls',
    6: '1 + n - matching - alpha <= ls',
    7: 'max_l - 1 + n - 2*alpha <= ls',
    13: 'diameter + max_l - 1 <= b',
    16: '2*(radius - 1) + max_l <= b',
    17: 'alpha + ceil(diameter/3) <= b',
    18: 'alpha + ceil(sqrt(dist_max(max_degree_vertices))) <= b',
    19: 'floor(avg_ecc + max_l) <= b',
    20: 'n / floor(avg_degree) <= b',
    23: 'floor(alpha + dist_avg(max_degree_vertices)/2) <= b',
    24: 'max_l + ceil(min_dist_even/3) <= b',
    25: '2*ceil((1 + min_dist_even)/3) <= b',
    31: '2*radius - 1 <= path',
    32: 'dist_avg(min_degree_vertices) + 1/2*ecc_avg(max_degree_vertices) <= path',
    33: 'ceil(2*dist_avg_all(max_degree_vertices)) <= path',
    34: 'ceil(dist_avg_all(center) + dist_avg_all(max_degree_vertices)) <= path',
    36: 'dp > 0 -> 2*radius/dp <= path',
    40: 'ceil((spanning_paths + b + 1)/2) <= forest',
    58: 'max(0, ceil(b/avg_l)) <= forest',
    59: 'ceil(sqrt(residue*b)) <= forest',
    61: 'residue + ceil(diameter/3) <= forest',
    63: 'ceil((min_dist_even + b + 1)/3) <= forest',
    64: 'ceil(sqrt(alpha*(1 + mod(n, max_degree)))) <= forest',
    65: 'dist_min(min_degree_vertices) + ceil(dist_min(max_degree_vertices)/3) <= forest',
    72: 'ceil(avg_ecc + max_l/3) <= tree',
    84: 'min_degree > 0 -> 2*radius/min_degree <= tree',
    85: 'ceil(sqrt(1 + 2*min_dist_even)) <= tree',
    91: 'b <= 1 + forest*ceil(avg_l)/2',
    96: 'alpha <= 1 + min_dist_even*(max_l - 1)',
    100: 'alpha <= ceil((max_l + 1/2*sqrt(deg_sq_sum@complement))/2)',
    101: 'alpha <= idiv(n + alpha_core, 2)',
    109: 'alpha <= floor((residue + 2*b)/3)',
    133: 'radius + cond(has_c4, 1, avg_l) <= path',
    141: 'girth/2 - 1 + max_l <= tree',
    142: '2/3*girth + ecc_set(periphery) <= tree',
    143: 'second_degree > 0 -> girth + 1 <= tree*second_degree',
    144: 'girth - 1 + ecc_to(center) <= tree',
    145: 'min_l@complement > 0 -> 2*ecc_set(periphery) <= tree*min_l@complement',
    146: 'radius@square > 0 -> 2*ecc_set(periphery) <= tree*radius@square',
    172: '-1 + max_degree_on(periphery) + dist_min(square_max_degree_vertices) <= ls',
    176: 'n + dist_min(square_max_degree_vertices) <= ls + b',
    181: 'alpha + avg_degree_on(periphery)@square <= ls + b',
    189: 'max_dist_even <= 1 + second_degree -> ham_path',
    194: 'alpha <= 1 + avg_l -> ham_path',
    '198a': 'b <= 2 + avg_ecc -> ham_path',
    199: 'nat_sub(tree, 2) <= kappa -> ham_path',
    200: 'tree == ceil(1 + avg_l) -> ham_path',
    217: 'ls <= 4*ind(residue == 2) + 2 -> ham_path',
    '430a': 'n > 3 -> indep_dom <= center_neigh_alpha + 2*floor(caro_wei - 1)',
}


# ------------------------------------------------------------------------------- documented counterexamples
# The disproved statements whose Lean files describe an explicit counterexample, rebuilt here from that text, with
# the invariant values the text states. They check the transcription: each must violate its statement, and the
# stated values must come out. Not rebuilt: 23, 24, 25, 33 (no graph given), 34 (a 39-vertex tree; partial check in
# the tests), 58 (79 vertices, beyond exhaustive search).

def _from_graph6(s):
    n = ord(s[0]) - 63
    bits = []
    for ch in s[1:]:
        bits += [((ord(ch) - 63) >> (5 - b)) & 1 for b in range(6)]
    edges, k = [], 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                edges.append((i, j))
            k += 1
    return I.Graph(n, edges)


def path_graph(n):
    return I.Graph(n, [(i, i + 1) for i in range(n - 1)])


def c5_k4():
    """The lexicographic product C5[K4]: vertex 4i + a; adjacent within a blob or between consecutive blobs."""
    return I.Graph(20, [(4 * i + a, 4 * j + c) for i in range(5) for j in range(5) for a in range(4) for c in range(4)
                        if (4 * i + a) < (4 * j + c) and (i == j or (i - j) % 5 in (1, 4))])


def two_triangles(k):
    """D_k: two triangles whose distinguished vertices are joined by a path of k edges."""
    inner = list(range(6, 6 + k - 1))
    chain = [2] + inner + [3]
    return I.Graph(6 + k - 1, [(0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5)]
                   + [(chain[i], chain[i + 1]) for i in range(k)])


def line_k7():
    pairs = [(a, c) for a in range(7) for c in range(a + 1, 7)]
    return I.Graph(21, [(i, j) for i in range(21) for j in range(i + 1, 21) if set(pairs[i]) & set(pairs[j])])


def clique_blowup_path(sizes):
    start = [sum(sizes[:i]) for i in range(len(sizes))]
    blobs = [list(range(start[i], start[i] + s)) for i, s in enumerate(sizes)]
    edges = [(u, v) for bl in blobs for u in bl for v in bl if u < v]
    edges += [(u, v) for i in range(len(blobs) - 1) for u in blobs[i] for v in blobs[i + 1]]
    return I.Graph(sum(sizes), edges)


def chain_hub_leaves():
    """Conjecture 59's 18-vertex graph: a bipartite chain graph on {0..4} | {5..9}, a hub 10 adjacent to 0..9, leaves
    11..17 at the hub. The Lean text does not fix the chain graph. Of the 252 chain graphs (nested neighbourhoods of
    sizes d_0 <= ... <= d_4), six give the values it states (residue 10, b 17, forest 13), and all six violate the
    statement; this is the first, with neighbourhood sizes (2, 3, 4, 5, 5)."""
    sizes = (2, 3, 4, 5, 5)
    return I.Graph(18, [(i, 5 + j) for i in range(5) for j in range(sizes[i])] + [(10, v) for v in range(10)]
                   + [(10, v) for v in range(11, 18)])


COUNTEREXAMPLES = {
    32: (lambda: path_graph(5), {'path_number': 5}),
    36: (lambda: I.Graph(10, [(0, 4), (0, 5), (0, 7), (0, 8), (1, 4), (1, 6), (1, 7), (1, 8), (2, 8), (3, 7), (5, 9),
                              (6, 9), (7, 9), (8, 9)]), {'radius': 3, 'dp': 1, 'path_number': 5}),
    59: (chain_hub_leaves, {'residue': 10, 'b': 17, 'largest_induced_forest': 13}),
    63: (c5_k4, {'min_dist_even': 9, 'largest_induced_forest': 4, 'b': 4}),
    64: (c5_k4, {'largest_induced_forest': 4, 'indep_num': 2}),
    65: (lambda: I.Graph(17, [(i, i + 1) for i in range(12)] + [(1, 13), (1, 14), (13, 14), (11, 15), (11, 16),
                                                                 (15, 16)]),
         {'largest_induced_forest': 15}),
    85: (c5_k4, {'min_dist_even': 9, 'largest_induced_tree': 4}),
    91: (lambda: _from_graph6('JBza_CB?wF_'), {'b': 8, 'largest_induced_forest': 6, 'average_indep_neighbours': 2}),
    109: (lambda: I.Graph(13, [(7, 8), (7, 9), (8, 9), (10, 11), (10, 12), (11, 12)]
                          + [(u, v) for u in range(7) for v in range(7, 13)]),
          {'indep_num': 7, 'residue': 2, 'b': 9}),
    172: (lambda: two_triangles(9), {'ls': 4}),
    176: (lambda: two_triangles(7), {'ls': 4, 'b': 10}),
    181: (line_k7, {'ls': 16, 'b': 6, 'indep_num': 3}),
    194: (lambda: _from_graph6('Q~~~~~~~~~~~~}~}^~??G??_??_'), {'indep_num': 4, 'hamiltonian_path': False}),
    200: (lambda: _from_graph6('J??FFBRq}N_'), {'largest_induced_tree': 4, 'hamiltonian_path': False}),
    '430a': (lambda: clique_blowup_path((1, 4, 12, 19, 12, 4, 1)), {'indep_domination_number': 3}),
}


def stated_value(G, name):
    if name == 'min_dist_even':
        return min_dist_even(G)
    return getattr(I, name)(G)


def verifier(posed, max_n=16, log=None):
    """For a study (kernel side): verify(pid, artifact) -> 1.0 if the artifact's graph is connected and violates the
    posed statement by this module's transcription, computed twice, with the research plane's invariants and with
    the kernel's independent ones (`invariants_ref.py`); else 0.0. Both must say violated. A disagreement is
    appended to `log` (a list) when one is given. `posed` is {id: statement number}; artifacts are those of
    `conjecture.invariant_domain` (n, edges)."""
    def verify(pid, art):
        try:
            n, edges = int(art['n']), [tuple(int(x) for x in e) for e in art['edges']]
            if not 2 <= n <= max_n or any(not (0 <= u < n and 0 <= v < n) for u, v in edges):
                return 0.0
            if not _reference.Graph(n, edges).connected():
                return 0.0
            a, b = evaluate_both(posed[pid], n, edges)
            va, vb = violated(a), violated(b)
            if va != vb and log is not None:
                log.append({'problem': pid, 'n': n, 'edges': edges, 'research': va, 'reference': vb})
            return 1.0 if va and vb else 0.0
        except (KeyError, ValueError, TypeError, IndexError):
            return 0.0
    return verify


def violated(result):
    if result['kind'] == 'ineq':
        return result['lhs'] > result['rhs']
    if result['kind'] == 'imp':
        return result['hyp'] and not result['concl']
    return False


def margin(result):
    """A search score: positive exactly when violated."""
    if result['kind'] == 'ineq':
        return float(result['lhs'] - result['rhs'])
    if result['kind'] == 'imp':
        return 1.0 if (result['hyp'] and not result['concl']) else (-0.5 if result['hyp'] else -1.0)
    return -2.0
