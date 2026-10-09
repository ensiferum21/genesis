"""Small, exact, independently checkable C4-free host optimization.

DEV research wedge, not a theorem prover or a claim of novelty. Simple graphs,
non-induced four-cycles; exhaustive optimization limited to 20 host edges.
"""
from itertools import combinations

MAX_EDGES = 20


def normalize(n, edges):
    if type(n) is not int or not 0 <= n <= 63:
        raise ValueError('vertex count must be 0..63')
    if not isinstance(edges, (list, tuple, set)):
        raise ValueError('edges must be a collection')
    result = set()
    for e in edges:
        if not isinstance(e, (list, tuple)) or len(e) != 2:
            raise ValueError('invalid edge')
        u, v = e
        if type(u) is not int or type(v) is not int or not 0 <= u < n or not 0 <= v < n or u == v:
            raise ValueError('invalid endpoint or loop')
        edge = (min(u, v), max(u, v))
        if edge in result:
            raise ValueError('duplicate edge')
        result.add(edge)
    return tuple(sorted(result))


def c4_by_cycles(n, edges):
    """Checker A: explicitly enumerate four distinct vertices and cyclic orders."""
    es = set(normalize(n, edges))
    for a, b, c, d in combinations(range(n), 4):
        for x, y, z, w in ((a,b,c,d), (a,b,d,c), (a,c,b,d)):
            if all((min(u,v), max(u,v)) in es for u,v in ((x,y),(y,z),(z,w),(w,x))):
                return True
    return False


def c4_by_common_neighbors(n, edges):
    """Checker B: a C4 exists iff two vertices have >=2 common neighbors."""
    es = normalize(n, edges)
    neighbors = [0] * n
    for u, v in es:
        neighbors[u] |= 1 << v
        neighbors[v] |= 1 << u
    return any((neighbors[u] & neighbors[v]).bit_count() >= 2
               for u in range(n) for v in range(u + 1, n))


def verify(n, host, selected):
    host = set(normalize(n, host))
    selected = set(normalize(n, selected))
    if not selected.issubset(host):
        raise ValueError('selected edge is not in host')
    a = c4_by_cycles(n, selected)
    b = c4_by_common_neighbors(n, selected)
    if a != b:
        raise RuntimeError('independent C4 checkers disagree')
    return not a


def greedy(n, host):
    """Deterministic, non-optimal baseline; every inclusion rechecked."""
    host = normalize(n, host)
    chosen = []
    for edge in host:
        if verify(n, host, chosen + [edge]):
            chosen.append(edge)
    return tuple(chosen)


def exact(n, host):
    """Exhaustive branch-and-bound, with two independent witness checkers.

    A complete search over all subgraphs certifies the optimum for the
    explicitly bounded instance, not a universal extremal theorem.
    """
    host = normalize(n, host)
    if len(host) > MAX_EDGES:
        raise ValueError('exact search cap: 20 host edges')
    best = greedy(n, host)
    visited = 0
    def search(i, chosen):
        nonlocal best, visited
        visited += 1
        if len(chosen) + len(host) - i <= len(best):
            return
        if i == len(host):
            if len(chosen) > len(best):
                best = tuple(chosen)
            return
        e = host[i]
        if verify(n, host, chosen + [e]):
            search(i + 1, chosen + [e])
        search(i + 1, chosen)
    search(0, [])
    assert verify(n, host, best)
    return {'schema':'genesis-c4-exact-dev-v1', 'n':n, 'host':host,
            'selected':best, 'optimum':len(best), 'greedy':len(greedy(n,host)),
            'search_nodes':visited, 'complete_enumeration':True,
            'independent_c4_checkers_agree':True, 'formal_proof':False,
            'novel_discovery_claim':False}


def verify_optimum_by_independent_enumeration(result):
    """Separate exhaustive certificate checker, not reusing branch-and-bound."""
    n = result['n']
    host = normalize(n, result['host'])
    if len(host) > MAX_EDGES or not verify(n, host, result['selected']):
        return False
    target = result['optimum']
    if type(target) is not int or target != len(result['selected']):
        return False
    for size in range(target + 1, len(host) + 1):
        for subset in combinations(host, size):
            if verify(n, host, subset):
                return False
    return True
