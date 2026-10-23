"""The DEV-only max-cut domain (B20_R101): reading benchmark files, checking cuts, and an exposure identity.

Witness. A cut is a string of n characters '0'/'1' (the side of each vertex). Its value is checked by two independent
computations that must agree (a disagreement is a checker error, never a verdict):
  (a) edge-driven: the sum of w over edges whose endpoints' sides differ;
  (b) vertex-driven: half the sum over vertices of the weight from each vertex to the other side, computed from
      adjacency lists built separately.

Benchmark files. Gset's `.rud` format (rudy generator; Helmberg and Rendl 2000): a header "n m", then m lines
"i j w" with 1-based endpoints. `parse_rud` reads it strictly (sizes, ranges, no self-loops or duplicate pairs).

Exposure identity: colour refinement (1-dimensional Weisfeiler-Leman) with edge weights as colours, as in
`graphs_large`. Isomorphic weighted graphs get the same identity.
"""
import hashlib
import json


class CheckerDisagreement(RuntimeError):
    def __init__(self, message, *, question, inputs, results):
        super().__init__(message)
        self.question, self.inputs, self.results = question, inputs, results


def parse_rud(text):
    """(n, edges) from a .rud file: edges as sorted (u, v, w), 0-based, u < v."""
    lines = [l.split() for l in text.replace('\r', '').split('\n') if l.strip()]
    if not lines or len(lines[0]) != 2:
        raise ValueError('header must be "n m"')
    n, m = int(lines[0][0]), int(lines[0][1])
    if n < 1 or m < 0 or len(lines) - 1 != m:
        raise ValueError(f'header says {m} edges, file has {len(lines) - 1}')
    out = {}
    for row in lines[1:]:
        if len(row) != 3:
            raise ValueError('edge lines are "i j w"')
        i, j, w = int(row[0]), int(row[1]), int(row[2])
        if not (1 <= i <= n and 1 <= j <= n) or i == j or w == 0:
            raise ValueError(f'bad edge {row}')
        key = (min(i, j) - 1, max(i, j) - 1)
        if key in out:
            raise ValueError(f'duplicate edge {key}')
        out[key] = w
    return n, tuple(sorted((u, v, w) for (u, v), w in out.items()))


def side_of(n, witness):
    if not isinstance(witness, str) or len(witness) != n or set(witness) - {'0', '1'}:
        raise ValueError('a cut is a string of n characters 0/1')
    return witness


def cut_edge_driven(edges, side):
    return sum(w for u, v, w in edges if side[u] != side[v])


def cut_vertex_driven(n, edges, side):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    total = 0
    for x in range(n):
        sx = side[x]
        total += sum(w for y, w in adj[x] if side[y] != sx)
    if total % 2:
        raise ArithmeticError('every cut edge is counted from both ends')
    return total // 2


def check_cut(task, witness):
    """{'value', 'checkers'} for a cut of the task; raises ValueError (malformed) or CheckerDisagreement."""
    side = side_of(task.n, witness)
    a = cut_edge_driven(task.edges, side)
    b = cut_vertex_driven(task.n, task.edges, side)
    if a != b:
        raise CheckerDisagreement('the two cut computations disagree', question='cut value',
                                  inputs={'task': task.task_id}, results={'edge-driven': a, 'vertex-driven': b})
    return {'value': a, 'checkers': ['edge-driven-sum-v1', 'vertex-driven-half-sum-v1']}


def wl_identity(n, edges, rounds=4):
    """A colour-refinement invariant of the weighted graph (isomorphism-invariant)."""
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    colour = [0] * n
    for _ in range(rounds):
        sig = [(colour[x], tuple(sorted((colour[y], w) for y, w in adj[x]))) for x in range(n)]
        names = {s: i for i, s in enumerate(sorted(set(sig)))}
        colour = [names[s] for s in sig]
    hist = sorted((s for s in [(colour[x], tuple(sorted((colour[y], w) for y, w in adj[x]))) for x in range(n)]))
    return hashlib.sha256(json.dumps([n, len(edges), hist]).encode()).hexdigest()
