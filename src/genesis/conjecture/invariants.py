"""Exact graph invariants for the proving test's transfer family: the Graffiti.pc conjectures of "Written on the Wall
II" as formalised in Lean by `google-deepmind/formal-conjectures` (research plane; `docs/OMEGA_FRONTIER.md` §7b).

Each function follows the Lean definition it names (FormalConjecturesForMathlib, Combinatorics/SimpleGraph, and the
WrittenOnTheWallII files, read at commit c0c5380). Every value is exact: integers, or `fractions.Fraction` for
averages. The independence number is computed by exact branching on vertex masks; the other NP-hard invariants by
exhaustive search over vertex subsets (bitmasks), which is exact and practical up to about 16 vertices. A graph is `Graph(n, edges)`; the statements are about connected graphs.

Conventions taken from the Lean definitions:
  * `dist` is the BFS distance (graphs are connected);
  * `girth` is Mathlib's `girth`, 0 for an acyclic graph;
  * `ls` is the maximum number of degree-1 vertices of a spanning tree: n - (connected domination number) for
    n >= 3, and 2 for n = 2;
  * `path_number` is the order of a largest induced path (a single vertex is one);
  * `residue` is the number of zeros left by the Havel-Hakimi process exactly as `residueAux` defines it;
  * `temp(v) = deg / (n - deg)`, 0 when deg = n;
  * `second_smallest_degree` is the degree sequence sorted ascending, at index 1;
  * set distances: `dist_min(S)` over ordered pairs of distinct members (0 if none); `ecc_set(S)` is the maximum over
    all vertices of the distance to S; `dist_max_set(S)` over all pairs of members; `dist_avg_set(S)` over ordered
    pairs of distinct members (0 if none).
"""
from fractions import Fraction
from functools import lru_cache


class Graph:
    def __init__(self, n, edges):
        self.n = n
        self.adj = [0] * n
        es = set()
        for u, v in edges:
            if u != v:
                self.adj[u] |= 1 << v
                self.adj[v] |= 1 << u
                es.add((min(u, v), max(u, v)))
        self.edges = sorted(es)
        self.full = (1 << n) - 1
        self._dist = None
        self._memo = {}                                # per-graph results of `_cached` invariants

    # ------------------------------------------------------------------------------------------- basics
    def degree(self, v):
        return bin(self.adj[v]).count('1')

    def degrees(self):
        return [self.degree(v) for v in range(self.n)]

    def neighbours(self, v):
        return [u for u in range(self.n) if self.adj[v] >> u & 1]

    def complement(self):
        return Graph(self.n, [(u, v) for u in range(self.n) for v in range(u + 1, self.n) if not self.adj[u] >> v & 1])

    def induced_edges(self, S):
        return sum(bin(self.adj[v] & S).count('1') for v in _bits(S)) // 2

    def connected_within(self, S):
        if S == 0:
            return False
        start = S & -S
        seen, frontier = start, start
        while frontier:
            nxt = 0
            for v in _bits(frontier):
                nxt |= self.adj[v] & S
            frontier = nxt & ~seen
            seen |= nxt
        return seen == S

    def components_within(self, S):
        count, rest = 0, S
        while rest:
            start = rest & -rest
            seen, frontier = start, start
            while frontier:
                nxt = 0
                for v in _bits(frontier):
                    nxt |= self.adj[v] & S
                frontier = nxt & ~seen
                seen |= nxt
            rest &= ~seen
            count += 1
        return count

    def bipartite_within(self, S):
        colour = {}
        for s in _bits(S):
            if s in colour:
                continue
            colour[s] = 0
            stack = [s]
            while stack:
                v = stack.pop()
                for u in _bits(self.adj[v] & S):
                    if u not in colour:
                        colour[u] = 1 - colour[v]
                        stack.append(u)
                    elif colour[u] == colour[v]:
                        return False
        return True

    def independent(self, S):
        return all(self.adj[v] & S == 0 for v in _bits(S))

    # ------------------------------------------------------------------------------------------- distances
    def dist(self):
        if self._dist is None:
            D = []
            for s in range(self.n):
                d = [None] * self.n
                d[s] = 0
                frontier, k, seen = 1 << s, 0, 1 << s
                while frontier:
                    k += 1
                    nxt = 0
                    for v in _bits(frontier):
                        nxt |= self.adj[v]
                    nxt &= ~seen
                    for v in _bits(nxt):
                        d[v] = k
                    seen |= nxt
                    frontier = nxt
                D.append(d)
            self._dist = D
        return self._dist

    def connected(self):
        return self.n >= 1 and self.connected_within(self.full)


def _bits(S):
    while S:
        low = S & -S
        yield low.bit_length() - 1
        S ^= low


def _subsets_by_size(n, descending=True):
    sizes = range(n, -1, -1) if descending else range(n + 1)
    for k in sizes:
        yield k, _combinations_masks(n, k)


def _combinations_masks(n, k):
    from itertools import combinations
    for c in combinations(range(n), k):
        m = 0
        for v in c:
            m |= 1 << v
        yield m


def _max_subset(G, ok, upper=None):
    """The largest k <= upper with some k-subset S satisfying ok(S); `upper` must be a valid upper bound."""
    top = G.n if upper is None else min(G.n, upper)
    for k in range(top, 0, -1):
        for S in _combinations_masks(G.n, k):
            if ok(S):
                return k
    return 0


def _cached(fn):
    """Remember fn(G) on the graph (graphs are not changed after they are built)."""
    def wrapped(G):
        if fn.__name__ not in G._memo:
            G._memo[fn.__name__] = fn(G)
        return G._memo[fn.__name__]
    wrapped.__name__, wrapped.__doc__ = fn.__name__, fn.__doc__
    return wrapped


def _min_subset(G, ok):
    for k, masks in _subsets_by_size(G.n, descending=False):
        for S in masks:
            if ok(S):
                return k
    return G.n


# ----------------------------------------------------------------------------------------------- invariants

def order(G):
    return G.n


def size(G):
    return len(G.edges)


def min_degree(G):
    return min(G.degrees())


def max_degree(G):
    return max(G.degrees())


def average_degree(G):
    return Fraction(sum(G.degrees()), G.n)


def second_smallest_degree(G):
    d = sorted(G.degrees())
    return d[1] if len(d) > 1 else 0


def _mis(adj, S, memo):
    """The independence number of the subgraph induced by the vertex mask S (exact branching on masks)."""
    if S == 0:
        return 0
    got = memo.get(S)
    if got is not None:
        return got
    low, low_d, high, high_d = -1, 1 << 30, -1, -1
    for v in _bits(S):
        d = bin(adj[v] & S).count('1')
        if d < low_d:
            low, low_d = v, d
        if d > high_d:
            high, high_d = v, d
    if low_d <= 1:                                    # a vertex of degree <= 1 is in some maximum independent set
        r = 1 + _mis(adj, S & ~(adj[low] | 1 << low), memo)
    else:
        r = max(_mis(adj, S & ~(1 << high), memo), 1 + _mis(adj, S & ~(adj[high] | 1 << high), memo))
    memo[S] = r
    return r


@_cached
def indep_num(G):
    return _mis(G.adj, G.full, {})


def indep_num_within(G, S):
    return _mis(G.adj, S, {})


def _indep_brute(G, S):
    """The same by trying every subset of S, largest first (kept to test `_mis`)."""
    from itertools import combinations
    members = list(_bits(S))
    for k in range(len(members), 0, -1):
        for c in combinations(members, k):
            m = 0
            for v in c:
                m |= 1 << v
            if G.independent(m):
                return k
    return 0


def indep_neighbours(G, v):
    """indepNeighborsCard: the independence number of the subgraph induced by N(v)."""
    return indep_num_within(G, G.adj[v])


def average_indep_neighbours(G):
    """averageIndepNeighbors = l(G) = l_avg(G)."""
    return Fraction(sum(indep_neighbours(G, v) for v in range(G.n)), G.n)


def max_indep_neighbours(G):
    return max(indep_neighbours(G, v) for v in range(G.n))


def min_indep_neighbours(G):
    return min(indep_neighbours(G, v) for v in range(G.n))


@_cached
def b(G):
    """largestInducedBipartiteSubgraphSize. Each side is independent, so b <= 2 alpha; the search starts there."""
    return _max_subset(G, G.bipartite_within, upper=2 * indep_num(G))


@_cached
def largest_induced_forest(G):
    """An induced forest is bipartite, so it has at most b vertices; the search starts there."""
    return _max_subset(G, lambda S: G.induced_edges(S) == bin(S).count('1') - G.components_within(S), upper=b(G))


@_cached
def largest_induced_tree(G):
    """An induced tree is an induced forest; the search starts at the forest number."""
    return _max_subset(G, lambda S: S != 0 and G.connected_within(S) and G.induced_edges(S) == bin(S).count('1') - 1,
                       upper=largest_induced_forest(G))


def path_number(G):
    """path(G): the order of a largest induced path."""
    def ok(S):
        if S == 0:
            return False
        k = bin(S).count('1')
        if k == 1:
            return True
        return (G.connected_within(S) and G.induced_edges(S) == k - 1
                and all(bin(G.adj[v] & S).count('1') <= 2 for v in _bits(S)))
    return _max_subset(G, ok, upper=largest_induced_tree(G))       # an induced path is an induced tree


def connected_domination_number(G):
    def ok(S):
        dom = S
        for v in _bits(S):
            dom |= G.adj[v]
        return dom == G.full and G.connected_within(S)
    return _min_subset(G, ok)


def ls(G):
    """Ls: the maximum number of leaves (degree-1 vertices) of a spanning tree."""
    if G.n == 2:
        return 2
    return G.n - connected_domination_number(G)


def domination_number(G):
    def ok(S):
        dom = S
        for v in _bits(S):
            dom |= G.adj[v]
        return dom == G.full
    return _min_subset(G, ok)


def indep_domination_number(G):
    def ok(S):
        if not G.independent(S):
            return False
        dom = S
        for v in _bits(S):
            dom |= G.adj[v]
        return dom == G.full
    return _min_subset(G, ok)


def total_domination_number(G):
    def ok(S):
        dom = 0
        for v in _bits(S):
            dom |= G.adj[v]
        return dom == G.full
    return _min_subset(G, ok)


def matching_number(G):
    import networkx as nx
    H = nx.Graph()
    H.add_nodes_from(range(G.n))
    H.add_edges_from(G.edges)
    return len(nx.max_weight_matching(H, maxcardinality=True))


def residue(G):
    """The Havel-Hakimi residue, exactly as `residueAux`."""
    s = sorted(G.degrees(), reverse=True)
    while True:
        if not s:
            return 0
        d, rest = s[0], s[1:]
        if d == 0:
            return 1 + len(rest)
        dec = [x - 1 for x in rest[:d]]
        s = sorted(dec + rest[d:], reverse=True)


def eccentricities(G):
    D = G.dist()
    return [max(row) for row in D]


def radius(G):
    return min(eccentricities(G))


def diameter(G):
    return max(eccentricities(G))


def average_eccentricity(G):
    return Fraction(sum(eccentricities(G)), G.n)


def center(G):
    e = eccentricities(G)
    r = min(e)
    return [v for v in range(G.n) if e[v] == r]


def periphery(G):
    """maxEccentricityVertices: eccentricity equal to the diameter."""
    e = eccentricities(G)
    d = max(e)
    return [v for v in range(G.n) if e[v] == d]


def girth(G):
    """Mathlib's girth: the length of a shortest cycle, 0 if there is none."""
    best = None
    for s in range(G.n):
        dist = {s: 0}
        parent = {s: -1}
        queue = [s]
        for v in queue:
            for u in G.neighbours(v):
                if u not in dist:
                    dist[u] = dist[v] + 1
                    parent[u] = v
                    queue.append(u)
                elif parent[v] != u:
                    L = dist[u] + dist[v] + 1
                    best = L if best is None else min(best, L)
    return best or 0


def dist_even(G, v):
    return sum(1 for d in G.dist()[v] if d % 2 == 0)


def dist_to_set(G, v, S):
    return min(G.dist()[v][s] for s in S) if S else 0


def dist_min(G, S):
    pairs = [(a, c) for a in S for c in S if a != c]
    return min(G.dist()[a][c] for a, c in pairs) if pairs else 0


def ecc_set(G, S):
    return max(dist_to_set(G, v, S) for v in range(G.n))


def dist_max_set(G, S):
    return max((G.dist()[a][c] for a in S for c in S), default=0)


def dist_avg_set(G, S):
    pairs = [(a, c) for a in S for c in S if a != c]
    return Fraction(sum(G.dist()[a][c] for a, c in pairs), len(pairs)) if pairs else Fraction(0)


def max_degree_vertices(G):
    d = G.degrees()
    m = max(d)
    return [v for v in range(G.n) if d[v] == m]


def min_degree_vertices(G):
    d = G.degrees()
    m = min(d)
    return [v for v in range(G.n) if d[v] == m]


def max_temp(G):
    n = G.n
    return max((Fraction(d, n - d) if d != n else Fraction(0)) for d in G.degrees())


def ng(G):
    """NG: the minimum over non-edges uv of |N(u) U N(v)|; n if G is complete."""
    vals = [bin(G.adj[u] | G.adj[v]).count('1') for u in range(G.n) for v in range(u + 1, G.n)
            if not G.adj[u] >> v & 1]
    return min(vals) if vals else G.n


def degree_l2_norm_squared(G):
    """degreeL2Norm(G)^2 = sum of squared degrees (an integer; the norm is its square root)."""
    return sum(d * d for d in G.degrees())


def _path_ends_table(G):
    """reach[mask]: the vertices at which some path through exactly the vertices of mask can end (bitmask DP)."""
    n = G.n
    reach = [0] * (1 << n)
    for v in range(n):
        reach[1 << v] = 1 << v
    for mask in range(1, 1 << n):
        ends = reach[mask]
        if not ends:
            continue
        for v in _bits(ends):
            for u in _bits(G.adj[v] & ~mask):
                reach[mask | (1 << u)] |= 1 << u
    return reach


def _path_search(G, budget):
    """True or False when a depth-first search settles whether G has a Hamiltonian path within `budget` steps;
    None when it runs out."""
    n, full = G.n, G.full
    steps = [0]

    def extend(v, mask):
        if mask == full:
            return True
        steps[0] += 1
        if steps[0] > budget:
            raise TimeoutError
        nxt = sorted(_bits(G.adj[v] & ~mask), key=lambda u: bin(G.adj[u] & ~mask).count('1'))   # fewest exits first
        return any(extend(u, mask | 1 << u) for u in nxt)
    try:
        return any(extend(v, 1 << v) for v in range(n))
    except TimeoutError:
        return None


@_cached
def hamiltonian_path(G):
    """Whether G has a Hamiltonian path. A disconnected graph, or one with more than two vertices of degree at most
    1, has none; otherwise a budgeted depth-first search, and the exact bitmask DP if the search does not settle."""
    n = G.n
    if n == 1:
        return True
    if not G.connected() or sum(1 for d in G.degrees() if d <= 1) > 2:
        return False
    found = _path_search(G, budget=20 * n * n)
    if found is not None:
        return found
    return _path_ends_table(G)[G.full] != 0


@_cached
def min_spanning_paths(G):
    """The fewest vertex-disjoint paths (not necessarily induced) whose union contains every vertex (WOWII's "path
    cover number", `pathCoverNumber` in Lean; renamed here because the proving test's audit forbids that stem in
    research-plane identifiers). It is 1 exactly when there is a Hamiltonian path; otherwise k = 2, 3, ... is tried,
    from at least half the number of degree-1 vertices (each is an end of its path), until the vertices split into
    k path-traceable parts."""
    n = G.n
    if hamiltonian_path(G):
        return 1
    reach = _path_ends_table(G)

    @lru_cache(maxsize=None)
    def splits(mask, k):
        if k == 1:
            return reach[mask] != 0
        low = mask & -mask
        rest = mask ^ low
        sub = rest
        while True:
            piece = sub | low
            if piece != mask and reach[piece] and splits(mask ^ piece, k - 1):
                return True
            if sub == 0:
                return False
            sub = (sub - 1) & rest
    leaves = sum(1 for v in range(n) if G.degree(v) <= 1)
    for k in range(max(2, (leaves + 1) // 2), n + 1):
        if splits(G.full, k):
            return k
    return n


def vertex_connectivity(G):
    import networkx as nx
    H = nx.Graph()
    H.add_nodes_from(range(G.n))
    H.add_edges_from(G.edges)
    return nx.node_connectivity(H)


def alpha_core_size(G):
    """|alphaCore|: the vertices whose deletion lowers the independence number."""
    a = indep_num(G)
    return sum(1 for v in range(G.n) if indep_num_within(G, G.full & ~(1 << v)) < a)


def dp(G):
    """The number of unordered pairs of distinct vertices at distance diam(G)."""
    D, d = G.dist(), diameter(G)
    return sum(1 for u in range(G.n) for v in range(u + 1, G.n) if D[u][v] == d)


def square(G):
    D = G.dist()
    return Graph(G.n, [(u, v) for u in range(G.n) for v in range(u + 1, G.n) if D[u][v] <= 2])
