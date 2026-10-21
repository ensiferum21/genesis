"""Certified upper bounds for the large triangle-free domain (B20_R96): fractional Mantel clique packings.

Why. Targets in large hosts are best known values, not optima (UNCERTIFIED_TARGETS has been chronic since B20_R75,
and the n <= 63 certification route does not scale). A bound says how far any answer can still be from the best
possible one. B20_R94's edge-disjoint triangle packing is valid but weak on dense hosts: each triangle certifies one
removed edge per three, so on G(256, 0.5) it cannot certify below about two thirds of the edges, while the best
answers keep about 55%.

The bound. For any subgraph F of the host and any triangle-free H, |E(H) ∩ E(F)| <= ex(F, K3). For a clique K_k,
ex = floor(k^2 / 4) (Mantel's theorem, 1907). Given weights y_C >= 0 on cliques C with sum over the cliques containing
each edge at most 1 (a fractional packing),

    |E(H)| <= m - sum_C y_C (e(C) - ex(C)),

since every edge contributes at most 1 - sum_{C ∋ e} y_C outside the cliques and the cliques contribute at most
sum_C y_C ex(C). A triangle gives 1 per 3 edges; K5 and K6 give 0.4 per edge; K8 3/7; large cliques approach 1/2, which
is what dense random hosts need (their best triangle-free subgraphs keep about half the edges).

How. Cliques are grown greedily at random from every edge (neighbour bitsets), the packing weights are found by a
linear program (scipy's HiGHS) or, as a fallback, by proportional scaling (each clique scaled by its most loaded
edge: always feasible, monotone), and then rounded down to integers over a common denominator so the certificate
is checked exactly in integers: every set is a clique of the host, every edge's load is at most the denominator, and
the bound is floor((m D - sum_C k_C (e(C) - ex(C))) / D).
"""
import random

DENOMINATOR = 1 << 20


def mantel(k):
    return k * k // 4


def _nb(task):
    nb = [0] * task.n
    for u, v in task.edges:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    return nb


def grow_cliques(task, tries_per_edge=2, max_size=16, seed=0):
    """Distinct cliques of 3 or more vertices, grown greedily at random from every edge: start from its endpoints,
    repeatedly add a random common neighbour, preferring (with probability 1/2) one with many neighbours inside the
    candidate set."""
    rng = random.Random(seed)
    nb = _nb(task)
    out = set()
    for u, v in task.edges:
        for _ in range(tries_per_edge):
            members, cand = [u, v], nb[u] & nb[v]
            while cand and len(members) < max_size:
                bits = []
                c = cand
                while c:
                    low = c & -c
                    bits.append(low.bit_length() - 1)
                    c ^= low
                if rng.random() < 0.5 and len(bits) > 1:
                    sample = rng.sample(bits, min(len(bits), 8))
                    w = max(sample, key=lambda x: ((nb[x] & cand).bit_count(), rng.random()))
                else:
                    w = rng.choice(bits)
                members.append(w)
                cand &= nb[w]
            if len(members) >= 3:
                out.add(tuple(sorted(members)))
    return sorted(out)


def _edge_index(task):
    return {e: i for i, e in enumerate(task.edges)}


def _clique_edges(c, index):
    return [index[(c[i], c[j])] for i in range(len(c)) for j in range(i + 1, len(c))]


def _gain(c):
    k = len(c)
    return k * (k - 1) // 2 - mantel(k)


def _lp_weights(task, cliques, index, seconds):
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import csc_matrix
    rows, cols = [], []
    for j, c in enumerate(cliques):
        es = _clique_edges(c, index)
        rows.extend(es)
        cols.extend([j] * len(es))
    A = csc_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(task.edges), len(cliques)))
    gains = np.array([_gain(c) for c in cliques], dtype=float)
    res = linprog(-gains, A_ub=A, b_ub=np.ones(len(task.edges)), bounds=(0, None), method='highs',
                  options={'time_limit': float(seconds)})
    if res.x is None:
        return None
    return [max(0.0, float(x)) for x in res.x]


def _scaling_weights(task, cliques, index, rounds=60):
    m = len(task.edges)
    edges_of = [_clique_edges(c, index) for c in cliques]
    y = [1.0] * len(cliques)
    for _ in range(rounds):
        load = [0.0] * m
        for j, es in enumerate(edges_of):
            for e in es:
                load[e] += y[j]
        y = [y[j] / max(load[e] for e in es) for j, es in enumerate(edges_of)]
    return y


def clique_packing_bound(task, seconds=60, seed=0, tries_per_edge=2, max_size=16, use_lp=True):
    """{'upper', 'cliques', 'weights', 'denominator', 'method'}; the certificate re-checks with `check`."""
    index = _edge_index(task)
    cliques = grow_cliques(task, tries_per_edge, max_size, seed)
    m = len(task.edges)
    if not cliques:
        return {'upper': m, 'cliques': [], 'weights': [], 'denominator': DENOMINATOR, 'method': 'no-triangle'}
    y, method = None, None
    if use_lp:
        try:
            y = _lp_weights(task, cliques, index, seconds)
            method = 'mantel-clique-packing-lp'
        except Exception:                   # no solver or a solver failure: fall back, never guess
            y = None
    if y is None:
        y = _scaling_weights(task, cliques, index)
        method = 'mantel-clique-packing-scaling'
    # round down to integers over a common denominator, then repair any overload exactly
    k = [int(x * DENOMINATOR) for x in y]
    load = [0] * m
    edges_of = [_clique_edges(c, index) for c in cliques]
    for j, es in enumerate(edges_of):
        for e in es:
            load[e] += k[j]
    for j, es in enumerate(edges_of):
        over = max(load[e] for e in es) - DENOMINATOR
        if over > 0 and k[j] > 0:
            cut = min(k[j], over)
            k[j] -= cut
            for e in es:
                load[e] -= cut
    keep = [j for j in range(len(cliques)) if k[j] > 0]
    cert = {'cliques': [list(cliques[j]) for j in keep], 'weights': [k[j] for j in keep],
            'denominator': DENOMINATOR, 'method': method}
    cert['upper'] = check(task, cert)
    return cert


def check(task, cert):
    """The bound a certificate proves, re-checked from its data in integers: every set is a clique of the host on 3
    or more distinct vertices, every weight a non-negative integer, every edge's load at most the denominator.
    Raises ValueError otherwise."""
    D = cert['denominator']
    if type(D) is not int or D < 1:
        raise ValueError('bad denominator')
    host = set(task.edges)
    index = _edge_index(task)
    load = {}
    gain = 0
    if len(cert['cliques']) != len(cert['weights']):
        raise ValueError('cliques and weights differ in number')
    for c, k in zip(cert['cliques'], cert['weights']):
        if type(k) is not int or k < 0:
            raise ValueError('weights must be non-negative integers')
        if len(c) < 3 or len(set(c)) != len(c) or any(type(x) is not int or not 0 <= x < task.n for x in c):
            raise ValueError('not a vertex set of 3 or more')
        c = sorted(c)
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                e = (c[i], c[j])
                if e not in host:
                    raise ValueError('not a clique of the host')
                load[index[e]] = load.get(index[e], 0) + k
        gain += k * _gain(c)
    if any(v > D for v in load.values()):
        raise ValueError('an edge is overloaded')
    m = len(task.edges)
    return (m * D - gain) // D
