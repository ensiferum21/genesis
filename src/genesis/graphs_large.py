"""The DEV-only large triangle-free domain (B20_R94): witness checking, a certified upper bound and an exposure
identity that scale to hosts with up to 1023 vertices.

The n <= 63 domain checks witnesses with two predicates (all vertex triples, and neighbour bitsets). Enumerating all
triples is too slow beyond a few hundred vertices, so this domain's two predicates are both edge-driven but
algorithmically independent: (a) a merge of the endpoints' sorted neighbour lists, (b) an AND of neighbour bitsets
(Python integers). A disagreement is a checker error, never a verdict.

Upper bound: any set of edge-disjoint host triangles needs one edge removed from each, so a triangle-free subgraph
has at most `edges - |packing|` edges. `triangle_packing_bound` finds a packing greedily (lowest-degree edges first,
deterministic) and `check_packing` re-checks one from its data alone (host triangles, pairwise edge-disjoint).

Exposure identity: the colour-refinement (1-dimensional Weisfeiler-Leman) invariant. Isomorphic hosts always get the
same identity, so a host already seen is never admitted as fresh; two non-isomorphic hosts may collide, which only
excludes a host that was in fact new.
"""
import hashlib
import json

from .common import digest

MAX_N = 1023


class CheckerDisagreement(RuntimeError):
    def __init__(self, message, *, question, inputs, results):
        super().__init__(message)
        self.question, self.inputs, self.results = question, inputs, results


def normalize(n, edges, max_n=MAX_N):
    if type(n) is not int or not 0 <= n <= max_n:
        raise ValueError('vertex bound')
    if not isinstance(edges, (list, tuple)):
        raise ValueError('edge collection')
    out = []
    for e in edges:
        if not isinstance(e, (tuple, list)) or len(e) != 2:
            raise ValueError('edge shape')
        u, v = e
        if type(u) is not int or type(v) is not int or not 0 <= u < n or not 0 <= v < n or u == v:
            raise ValueError('edge endpoint')
        out.append((min(u, v), max(u, v)))
    if len(set(out)) != len(out):
        raise ValueError('duplicate edge')
    return tuple(sorted(out))


def has_triangle_merge(n, edges):
    """(a) Sorted neighbour lists, merged per edge."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for a in adj:
        a.sort()
    for u, v in edges:
        a, b = adj[u], adj[v]
        i = j = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                return True
            if a[i] < b[j]:
                i += 1
            else:
                j += 1
    return False


def has_triangle_bitsets(n, edges):
    """(b) Neighbour bitsets as integers."""
    nb = [0] * n
    for u, v in edges:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    return any(nb[u] & nb[v] for u, v in edges)


def check_witness(task, edges):
    es = normalize(task.n, edges)
    if not set(es) <= set(task.edges):
        raise ValueError('witness edge outside host')
    a, b = has_triangle_merge(task.n, es), has_triangle_bitsets(task.n, es)
    if a != b:
        raise CheckerDisagreement('CHECKER_ERROR: predicate disagreement', question='triangle_free',
                                  inputs={'task': task.model_dump(mode='json'), 'edges': [list(e) for e in es]},
                                  results={'adjacency-merge-v1': not a, 'neighbor-bitsets-v1': not b})
    if a:
        raise ValueError('triangle in witness')
    return {'status': 'WITNESS_VALID', 'selected': es, 'value': len(es),
            'task_sha256': digest(task.model_dump(mode='json')),
            'checkers': ['adjacency-merge-v1', 'neighbor-bitsets-v1']}


def triangle_packing_bound(task):
    """{'upper': edges - |packing|, 'packing': [[a, b, c], ...]}: a greedy edge-disjoint triangle packing, edges taken
    in increasing order of (codegree, edge), each closing with its lowest free common neighbour."""
    n, E = task.n, task.edges
    nb = [0] * n
    for u, v in E:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    used = set()
    order = sorted(E, key=lambda e: ((nb[e[0]] & nb[e[1]]).bit_count(), e))
    packing = []
    for u, v in order:
        if (u, v) in used:
            continue
        c = nb[u] & nb[v]
        while c:
            w = (c & -c).bit_length() - 1
            c &= c - 1
            e1, e2 = (min(u, w), max(u, w)), (min(v, w), max(v, w))
            if e1 not in used and e2 not in used:
                used.update(((u, v), e1, e2))
                packing.append(sorted((u, v, w)))
                break
    return {'upper': len(E) - len(packing), 'packing': packing, 'method': 'edge-disjoint-triangle-packing-greedy'}


def check_packing(task, packing):
    """The certified upper bound a packing gives, re-checked from its data: every triple is a host triangle and no two
    share an edge. Raises ValueError otherwise."""
    host = set(task.edges)
    used = set()
    for t in packing:
        if not isinstance(t, (list, tuple)) or len(t) != 3 or len(set(t)) != 3:
            raise ValueError('not a vertex triple')
        a, b, c = sorted(t)
        es = ((a, b), (a, c), (b, c))
        if not all(e in host for e in es):
            raise ValueError('not a host triangle')
        if any(e in used for e in es):
            raise ValueError('triangles share an edge')
        used.update(es)
    return len(task.edges) - len(packing)


def wl_identity(n, edges, rounds=None):
    """The colour-refinement invariant: starting from one colour, refine each vertex's colour by its own colour and the
    sorted colours of its neighbours (new colours numbered by the sorted signatures, so the numbering is itself
    invariant) until the partition stops splitting (at most n rounds); hash n, the edge count and the sorted final
    signatures."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    col, sig = [0] * n, []
    for _ in range(n if rounds is None else rounds):
        sig = [(col[v], tuple(sorted(col[w] for w in adj[v]))) for v in range(n)]
        palette = {x: i for i, x in enumerate(sorted(set(sig)))}
        new = [palette[x] for x in sig]
        stable = len(set(new)) == len(set(col))
        col = new
        if stable:
            break
    blob = json.dumps({'n': n, 'm': len(edges), 'signatures': sorted(sig)}, sort_keys=True, default=list)
    return hashlib.sha256(blob.encode()).hexdigest()
