"""Small simple graphs for the conjecture domain (research plane; F2, `docs/OMEGA_FRONTIER.md` §5.2).

A graph is (n, edges) with edges a sorted tuple of (u, v), u < v, on vertices 0..n-1. `local(n, edges)` gives each
vertex's degree d_v and the average degree of its neighbours m_v as exact fractions (m_v undefined for an isolated
vertex, so the domain's graphs have none). Bound values follow the convention of Brankov, Hansen and Stevanovic
(2006): a vertex bound is the maximum over vertices of f(d_v, m_v); an edge bound the maximum over edges ij of
f(d_i, m_i, d_j, m_j). `laplacian_top` is floating point (numpy), for search only.
"""
from fractions import Fraction

from . import expr as E


def normalise(n, edges):
    es = sorted({(min(u, v), max(u, v)) for u, v in edges if u != v})
    if any(not (0 <= u < n and 0 <= v < n) for u, v in es):
        raise ValueError('edge outside the vertex range')
    return n, tuple(es)


def adjacency(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def local(n, edges):
    """[(d_v, m_v)] with m_v a Fraction; raises on an isolated vertex."""
    adj = adjacency(n, edges)
    deg = [len(a) for a in adj]
    if min(deg, default=0) == 0:
        raise ValueError('isolated vertex: m_v is undefined')
    return [(deg[v], Fraction(sum(deg[u] for u in adj[v]), deg[v])) for v in range(n)]


def envs(n, edges, kind):
    """The variable assignments over which a bound of this kind is maximised."""
    loc = local(n, edges)
    if kind == 'vertex':
        return [{'d': d, 'm': m} for d, m in loc]
    out = []
    for i, j in edges:
        for a, b in ((i, j), (j, i)):                  # both orientations (the bounds need not be symmetric)
            out.append({'di': loc[a][0], 'mi': loc[a][1], 'dj': loc[b][0], 'mj': loc[b][1]})
    return out


def bound_value(ast, kind, n, edges):
    """Float value of the bound at the graph, or None if undefined anywhere."""
    vals = [E.evaluate(ast, e) for e in envs(n, edges, kind)]
    if any(v is None for v in vals) or not vals:
        return None
    return max(vals)


def laplacian(n, edges):
    import numpy as np
    L = np.zeros((n, n))
    for u, v in edges:
        L[u, u] += 1
        L[v, v] += 1
        L[u, v] -= 1
        L[v, u] -= 1
    return L


def laplacian_top(n, edges):
    """(mu, eigenvector) in floating point."""
    import numpy as np
    w, V = np.linalg.eigh(laplacian(n, edges))
    return float(w[-1]), V[:, -1]


def rational_vector(vec, bits=30):
    """A float vector rounded to rationals with denominator 2^bits (a certificate candidate)."""
    scale = 1 << bits
    return [Fraction(round(float(v) * scale), scale) for v in vec]


def graph6(n, edges):
    """The graph6 string (n < 63)."""
    if n >= 63:
        raise ValueError('graph6 here is for n < 63')
    bits = []
    es = set(edges)
    for j in range(1, n):
        for i in range(j):
            bits.append(1 if (i, j) in es else 0)
    while len(bits) % 6:
        bits.append(0)
    out = chr(n + 63)
    for k in range(0, len(bits), 6):
        out += chr(63 + int(''.join(map(str, bits[k:k + 6])), 2))
    return out


def from_graph6(s):
    n = ord(s[0]) - 63
    bits = []
    for ch in s[1:]:
        v = ord(ch) - 63
        bits += [(v >> (5 - b)) & 1 for b in range(6)]
    edges, k = [], 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                edges.append((i, j))
            k += 1
    return normalise(n, edges)
