"""A second, independent implementation of the transfer family's invariants (KERNEL SIDE; the proving test,
`docs/OMEGA_FRONTIER.md` §7b).

The kernel checks a claimed counterexample of family B (`wowii.verifier`) twice: with the research plane's
`invariants.py`, and with this module, which shares no code with it. It is written from the Lean definitions
(FormalConjecturesForMathlib, Combinatorics/SimpleGraph, read at commit c0c5380) by different means:
  * `networkx` for distances, eccentricities, girth, bipartiteness, forests, trees and domination tests;
  * plain enumeration of vertex subsets with `itertools.combinations` where `invariants.py` uses bitmask searches;
  * a maximum clique of the complement for independence (`invariants.py` branches on masks);
  * backtracking for Hamiltonian paths (`invariants.py` uses dynamic programming over subsets);
  * recursion over edges for the matching number (`invariants.py` calls networkx's blossom algorithm);
  * the Lean definition, by enumeration, for vertex connectivity (`invariants.py` calls networkx);
  * the standard Havel-Hakimi process for the residue.
It is slow and meant for checking certificates of up to about 14 vertices. `Graph` offers what the kernel's
transcription (`wowii.py`) uses: n, edges, adj (bitmasks), degree, degrees, dist, complement, connected. Results
are cached per graph.
"""
from fractions import Fraction
from itertools import combinations

import networkx as nx


class Graph:
    def __init__(self, n, edges):
        self.n = n
        self.H = nx.Graph()
        self.H.add_nodes_from(range(n))
        self.H.add_edges_from((u, v) for u, v in edges if u != v)
        self.edges = sorted((min(u, v), max(u, v)) for u, v in self.H.edges())
        self.adj = [sum(1 << w for w in self.H[v]) for v in range(n)]
        self._memo = {}

    def degree(self, v):
        return self.H.degree(v)

    def degrees(self):
        return [self.H.degree(v) for v in range(self.n)]

    def dist(self):
        if 'dist' not in self._memo:
            sp = dict(nx.all_pairs_shortest_path_length(self.H))
            self._memo['dist'] = [[sp[u][v] for v in range(self.n)] for u in range(self.n)]
        return self._memo['dist']

    def complement(self):
        return Graph(self.n, list(nx.complement(self.H).edges()))

    def connected(self):
        return self.n > 0 and nx.is_connected(self.H)

    def sub(self, S):
        return self.H.subgraph(S)


def _memo(fn):
    def wrapped(G, *args):
        key = (fn.__name__, args)
        if key not in G._memo:
            G._memo[key] = fn(G, *args)
        return G._memo[key]
    wrapped.__name__ = fn.__name__
    return wrapped


def _largest(G, ok):
    for k in range(G.n, 0, -1):
        for S in combinations(range(G.n), k):
            if ok(S):
                return k
    return 0


def _smallest(G, ok):
    for k in range(0, G.n + 1):
        for S in combinations(range(G.n), k):
            if ok(S):
                return k
    return G.n


# ------------------------------------------------------------------------------------------- degrees

def min_degree(G):
    return min(G.degrees())


def max_degree(G):
    return max(G.degrees())


def average_degree(G):
    return Fraction(sum(G.degrees()), G.n)


def second_smallest_degree(G):
    return sorted(G.degrees())[1]


def max_degree_vertices(G):
    m = max_degree(G)
    return [v for v in range(G.n) if G.degree(v) == m]


def min_degree_vertices(G):
    m = min_degree(G)
    return [v for v in range(G.n) if G.degree(v) == m]


def degree_l2_norm_squared(G):
    return sum(d * d for d in G.degrees())


def max_temp(G):
    return max((Fraction(d, G.n - d) if d < G.n else Fraction(0)) for d in G.degrees())


def ng(G):
    vals = [len(set(G.H[u]) | set(G.H[v])) for u, v in combinations(range(G.n), 2) if not G.H.has_edge(u, v)]
    return min(vals) if vals else G.n


# ------------------------------------------------------------------------------------------- independence

def _alpha_of(H):
    if H.number_of_nodes() == 0:
        return 0
    return max(len(c) for c in nx.find_cliques(nx.complement(H)))


@_memo
def indep_num(G):
    return _alpha_of(G.H)


def indep_num_within(G, mask):
    return _alpha_of(G.sub([v for v in range(G.n) if mask >> v & 1]))


@_memo
def _local(G):
    return [_alpha_of(G.sub(list(G.H[v]))) for v in range(G.n)]


def average_indep_neighbours(G):
    return Fraction(sum(_local(G)), G.n)


def max_indep_neighbours(G):
    return max(_local(G))


def min_indep_neighbours(G):
    return min(_local(G))


@_memo
def alpha_core_size(G):
    a = indep_num(G)
    return sum(1 for v in range(G.n) if _alpha_of(G.sub([w for w in range(G.n) if w != v])) < a)


# ------------------------------------------------------------------------------------------- induced subgraphs

@_memo
def b(G):
    return _largest(G, lambda S: nx.is_bipartite(G.sub(S)))


@_memo
def largest_induced_forest(G):
    return _largest(G, lambda S: nx.is_forest(G.sub(S)))


@_memo
def largest_induced_tree(G):
    return _largest(G, lambda S: nx.is_tree(G.sub(S)))


@_memo
def path_number(G):
    def is_path(S):
        H = G.sub(S)
        return nx.is_tree(H) and max(d for _, d in H.degree()) <= 2
    return _largest(G, is_path)


# ------------------------------------------------------------------------------------------- domination

@_memo
def ls(G):
    """The most leaves of a spanning tree: 2 when n = 2; otherwise n minus the smallest connected dominating set."""
    if G.n == 2:
        return 2
    gc = _smallest(G, lambda S: len(S) > 0 and nx.is_dominating_set(G.H, S) and nx.is_connected(G.sub(S)))
    return G.n - gc


@_memo
def indep_domination_number(G):
    return _smallest(G, lambda S: len(S) > 0 and nx.is_dominating_set(G.H, S)
                     and G.sub(S).number_of_edges() == 0)


# ------------------------------------------------------------------------------------------- matchings, paths

@_memo
def matching_number(G):
    edges = list(G.edges)

    def best(i, used):
        if i == len(edges):
            return 0
        u, v = edges[i]
        out = best(i + 1, used)
        if not (used >> u & 1) and not (used >> v & 1):
            out = max(out, 1 + best(i + 1, used | 1 << u | 1 << v))
        return out
    return best(0, 0)


def _ham_path(H):
    nodes = list(H.nodes())
    if len(nodes) <= 1:
        return True
    if not nx.is_connected(H):
        return False
    target = len(nodes)

    def extend(path, seen):
        if len(path) == target:
            return True
        for w in H[path[-1]]:
            if w not in seen:
                seen.add(w)
                path.append(w)
                if extend(path, seen):
                    return True
                path.pop()
                seen.discard(w)
        return False
    return any(extend([s], {s}) for s in nodes)


@_memo
def hamiltonian_path(G):
    return _ham_path(G.H)


@_memo
def min_spanning_paths(G):
    """The fewest vertex-disjoint paths of G that together contain every vertex (Lean's `pathCoverNumber`)."""
    memo = {}

    def fewest(rest):
        if not rest:
            return 0
        if rest in memo:
            return memo[rest]
        first, others = rest[0], rest[1:]
        best = None
        for k in range(len(others), -1, -1):
            for extra in combinations(others, k):
                piece = (first,) + extra
                if _ham_path(G.sub(piece)):
                    left = tuple(v for v in others if v not in extra)
                    c = 1 + fewest(left)
                    best = c if best is None else min(best, c)
        memo[rest] = best
        return best
    return fewest(tuple(range(G.n)))


@_memo
def vertex_connectivity(G):
    """Lean's `vertexConnectivity`: the least |S| with G - S disconnected or |S| = n - 1 (0 for n <= 1)."""
    if G.n <= 1:
        return 0
    for k in range(G.n):
        for S in combinations(range(G.n), k):
            rest = [v for v in range(G.n) if v not in S]
            if k == G.n - 1 or not rest or not nx.is_connected(G.sub(rest)):
                return k
    return G.n - 1


@_memo
def residue(G):
    """Havel-Hakimi: repeatedly remove a largest degree d and lower the next d largest by one; count the zeros."""
    seq = sorted(G.degrees(), reverse=True)
    while seq and seq[0] > 0:
        d = seq.pop(0)
        for i in range(d):
            seq[i] -= 1
        seq.sort(reverse=True)
    return len(seq)


# ------------------------------------------------------------------------------------------- distances

@_memo
def eccentricities(G):
    e = nx.eccentricity(G.H)
    return [e[v] for v in range(G.n)]


def radius(G):
    return min(eccentricities(G))


def diameter(G):
    return max(eccentricities(G))


def average_eccentricity(G):
    return Fraction(sum(eccentricities(G)), G.n)


def center(G):
    return sorted(nx.center(G.H))


def periphery(G):
    return sorted(nx.periphery(G.H))


@_memo
def girth(G):
    g = nx.girth(G.H)
    return 0 if g == float('inf') else int(g)


def dist_even(G, v):
    return sum(1 for d in G.dist()[v] if d % 2 == 0)


def dist_to_set(G, v, S):
    return min(G.dist()[v][s] for s in S) if S else 0


def dist_min(G, S):
    ds = [G.dist()[u][v] for u in S for v in S if u != v]
    return min(ds) if ds else 0


def ecc_set(G, S):
    return max(dist_to_set(G, v, S) for v in range(G.n)) if S else 0


def dist_max_set(G, S):
    return max((G.dist()[u][v] for u in S for v in S), default=0)


def dist_avg_set(G, S):
    ds = [G.dist()[u][v] for u in S for v in S if u != v]
    return Fraction(sum(ds), len(ds)) if ds else Fraction(0)


def dp(G):
    d = diameter(G)
    return sum(1 for u, v in combinations(range(G.n), 2) if G.dist()[u][v] == d)


def square(G):
    return Graph(G.n, list(nx.power(G.H, 2).edges()))


# ------------------------------------------------------------------------------------------- added 28 Oct 2026

def domination_number(G):
    return _smallest(G, lambda S: len(S) > 0 and nx.is_dominating_set(G.H, S))


def total_domination_number(G):
    return _smallest(G, lambda S: len(S) > 0 and all(any(w in S for w in G.H[v]) for v in range(G.n)))


def triangles_at(G, v):
    return nx.triangles(G.H, v)


def max_triangles(G):
    return max(nx.triangles(G.H).values())


def freq_min_triangles(G):
    t = nx.triangles(G.H)
    m = min(t.values())
    return sum(1 for v in t if t[v] == m)


def hh_zero_step(G):
    """Lean's havelHakimiZeroStep, by its definition: iterate the step and stop at a zero or the empty list."""
    def step(s):
        if not s:
            return []
        d, rest = s[0], s[1:]
        head, tail = rest[:d], rest[d:]
        return sorted([x - 1 if x > 0 else 0 for x in head] + tail, reverse=True)
    s = sorted(G.degrees(), reverse=True)
    for i in range(G.n + 2):
        if not s or 0 in s:
            return i
        s = step(s)
    return G.n + 2


def even_horizontal(G, v):
    D = G.dist()[v]
    return sum(1 for a, c in G.H.edges() if D[a] == D[c] and D[a] % 2 == 0)


def max_even_correction(G):
    return max(dist_even(G, v) - even_horizontal(G, v) for v in range(G.n))


def min_complement_edge_neighbourhood(G):
    C = nx.complement(G.H)
    vals = [len(set(C[u]) | set(C[w])) for u, w in C.edges()]
    return min(vals) if vals else None


@_memo
def well_totally_dominated(G):
    """All minimal total dominating sets have one size, by enumerating vertex subsets."""
    def total(S):
        return all(any(w in S for w in G.H[v]) for v in range(G.n))
    sizes = set()
    for k in range(1, G.n + 1):
        for S in combinations(range(G.n), k):
            Sset = set(S)
            if total(Sset) and all(not total(Sset - {v}) for v in S):
                sizes.add(k)
    return len(sizes) <= 1


def pendants(G):
    return sum(1 for v in range(G.n) if G.H.degree(v) == 1)


def triangle_free(G):
    return sum(nx.triangles(G.H).values()) == 0


@_memo
def alpha_two(G):
    return _largest(G, lambda S: max((d for _, d in G.sub(S).degree()), default=0) <= 1)


def low_degree_vertices(G):
    return [v for v in range(G.n) if G.H.degree(v) <= 2]


def indep_on(G, S):
    return _alpha_of(G.sub(list(S)))


def internal_edges(G, S):
    return G.sub(list(S)).number_of_edges()
