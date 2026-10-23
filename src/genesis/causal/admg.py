"""The planted truth as an acyclic directed mixed graph, answer validation, d-separation and scoring (B20_R117).

Truth. Over the observed variables: a directed edge i -> j for every non-zero B[i, j], and a bidirected edge i <-> j
for every pair with a hidden common parent (the latent projection of the planted model; each hidden variable has
exactly two observed children, so the projection is exact).

Answer. {'directed': [[i, j], ...], 'undirected': [[i, j], ...], 'bidirected': [[i, j], ...]}. Each unordered pair
carries at most one mark; the directed part must be acyclic. Methods that cannot express a mark simply never use it.

Scores (per instance; studies aggregate them):
  * `directed`: precision, recall and F1 of the directed edges, orientation included;
  * `adjacency`: precision, recall and F1 of causal adjacency (a directed or undirected mark, against the true
    directed edges, direction ignored);
  * `bidirected`: precision, recall and F1 of hidden-cause marks;
  * `spurious_rate`: among confounded pairs with no direct edge, the fraction given a causal adjacency, the error a
    hidden variable induces in methods that assume none;
  * `latent_flagged`: whether the answer marks any hidden cause;
  * `shd`: pairs whose mark differs from the truth's (truth: the directed edge if any, else <-> if confounded, else
    none), an undirected mark on a true directed edge counting one.
"""
from itertools import combinations


def truth_marks(truth):
    p = truth['p']
    directed = {(i, j) for i in range(p) for j in range(p) if truth['B'][i][j] != 0.0}
    bidirected = {tuple(sorted(c)) for c in truth['confounded']}
    return directed, bidirected


def validate(answer, p):
    """[] or the reasons the answer is malformed."""
    if not isinstance(answer, dict) or not set(answer) <= {'directed', 'undirected', 'bidirected'}:
        return ['an answer is {directed, undirected, bidirected}']
    out, seen = [], set()
    for kind in ('directed', 'undirected', 'bidirected'):
        for e in answer.get(kind, []):
            if (not isinstance(e, (list, tuple)) or len(e) != 2 or any(type(v) is not int for v in e)
                    or not all(0 <= v < p for v in e) or e[0] == e[1]):
                out.append(f'bad {kind} edge {e!r}')
                continue
            key = tuple(sorted(e))
            if key in seen:
                out.append(f'pair {key} marked twice')
            seen.add(key)
    if not out and _cyclic(p, [tuple(e) for e in answer.get('directed', [])]):
        out.append('the directed edges form a cycle')
    return out


def _cyclic(p, edges):
    succ = {i: [] for i in range(p)}
    indeg = [0] * p
    for i, j in edges:
        succ[i].append(j)
        indeg[j] += 1
    stack, seen = [i for i in range(p) if indeg[i] == 0], 0
    while stack:
        i = stack.pop()
        seen += 1
        for j in succ[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                stack.append(j)
    return seen != p


def _prf(pred, true):
    tp = len(pred & true)
    prec = tp / len(pred) if pred else (1.0 if not true else 0.0)
    rec = tp / len(true) if true else 1.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {'precision': prec, 'recall': rec, 'f1': f1, 'tp': tp, 'predicted': len(pred), 'true': len(true)}


def score(truth, answer):
    p = truth['p']
    problems = validate(answer, p)
    if problems:
        raise ValueError('; '.join(problems))
    directed, bidirected = truth_marks(truth)
    pd = {tuple(e) for e in answer.get('directed', [])}
    pu = {tuple(sorted(e)) for e in answer.get('undirected', [])}
    pb = {tuple(sorted(e)) for e in answer.get('bidirected', [])}
    true_adj = {tuple(sorted(e)) for e in directed}
    pred_adj = {tuple(sorted(e)) for e in pd} | pu
    only_conf = bidirected - true_adj
    spurious = len(only_conf & pred_adj) / len(only_conf) if only_conf else None
    shd = 0
    for i, j in combinations(range(p), 2):
        t = '>' if (i, j) in directed else '<' if (j, i) in directed else 'b' if (i, j) in bidirected else ''
        a = '>' if (i, j) in pd else '<' if (j, i) in pd else '-' if (i, j) in pu else 'b' if (i, j) in pb else ''
        shd += t != a
    return {'directed': _prf(pd, directed), 'adjacency': _prf(pred_adj, true_adj), 'bidirected': _prf(pb, bidirected),
            'spurious_rate': spurious, 'latent_flagged': bool(pb), 'latent_present': bool(bidirected), 'shd': shd}


# ------------------------------------------------------------------------------------------------- d-separation

def full_dag(truth):
    """Parents in the planted DAG over observed (0..p-1) and hidden (p..p+h-1) variables."""
    p, h = truth['p'], truth['h']
    parents = {v: set() for v in range(p + h)}
    for i in range(p):
        for j in range(p):
            if truth['B'][i][j] != 0.0:
                parents[j].add(i)
    for k in range(h):
        for j in range(p):
            if truth['G'][k][j] != 0.0:
                parents[j].add(p + k)
    return parents


def d_separated(parents, x, y, given):
    """x and y d-separated by `given` in the DAG (moral graph of the ancestral set; Lauritzen et al. 1990)."""
    given = set(given)
    anc, stack = set(), [x, y, *given]
    while stack:
        v = stack.pop()
        if v not in anc:
            anc.add(v)
            stack.extend(parents[v])
    nbr = {v: set() for v in anc}
    for v in anc:
        ps = [u for u in parents[v] if u in anc]
        for u in ps:
            nbr[u].add(v)
            nbr[v].add(u)
        for a, b in combinations(ps, 2):
            nbr[a].add(b)
            nbr[b].add(a)
    seen, stack = {x}, [x]
    while stack:
        v = stack.pop()
        if v == y:
            return False
        for u in nbr[v]:
            if u not in seen and u not in given:
                seen.add(u)
                stack.append(u)
    return True
