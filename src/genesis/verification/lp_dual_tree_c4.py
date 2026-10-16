"""Exact checker for branch-and-bound certificates over generated C4 rows (B20_R48; trusted side, DEV only).

A certificate bounds the largest C4-free subgraph of a c4_host_v2 host by U. It is a binary tree. Each
internal node branches on one host edge e that is not yet fixed: the `zero` child fixes e out, the `one`
child fixes e in. Each leaf carries one of two kinds of evidence for its fixings (F0 fixed out, F1 fixed in):

  * **dual**: rows with positive rational weights and nonnegative slacks on the free edges (host edges in
    neither F0 nor F1). A row is a 4-cycle of the host (rhs 3) or a copy of a registry pattern (rhs
    ex(F)), given exactly as in `verification.lp_dual_rows_c4`. At the leaf its free edges are its edges
    outside F0 ∪ F1, and its effective rhs is rhs − |row ∩ F1|, which must be ≥ 0. Every free edge must
    be covered at least once by the weights of the rows that contain it plus its slack. The leaf bound is
    |F1| + ⌊Σ weight × effective rhs + Σ slack⌋, and it must be ≤ U.
  * **infeasible**: one row with |row ∩ F1| > rhs.

**Soundness.** Take any C4-free S ⊆ E(H). Follow the tree from the root, going to `one` at an edge of S and
to `zero` otherwise. The leaf reached has F1 ⊆ S and F0 ∩ S = ∅. Every row holds for S (4-cycle rows by the
definition of C4-free; pattern rows by their Lean-checked statements, as in `lp_dual_rows_c4`), and so
holds for S's free edges with the effective rhs. No S reaches an infeasible leaf. At a dual leaf, weak LP
duality gives |S ∩ free| ≤ the dual objective, so |S| ≤ the leaf bound ≤ U. Every S reaches exactly one leaf,
so the optimum is ≤ U.

The checker verifies all of this in exact arithmetic, with no optimisation library:
  * the task identity, the registry digest and the schema;
  * every branch edge (a host edge, not already fixed);
  * every row and its right-hand side;
  * leaf coverage and leaf bounds.

The registry is `lp_dual_rows_c4.registry_from_package`'s: patterns only from CHECKED statements of an
intact package with the trusted definitions. Nothing in the evaluator or the custodian uses this module.
"""
from fractions import Fraction
import hashlib
import math
from pathlib import Path

from ..common import digest
from .lp_dual_rows_c4 import DOMAIN, REGISTRY_SCHEMA

SCHEMA = 'genesis-lp-dual-tree-c4-certificate-v1'
MAX_NODES = 2_000_000


def checker_identity():
    return 'genesis.verification.lp_dual_tree_c4@' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class Bad(Exception):
    pass


def row_edges(q, registry, Eset):
    """(sorted edge list, rhs) of a row given as in lp_dual_rows_c4, or Bad."""
    if q.get('kind') == 'cycle':
        cyc = list(q.get('cycle', ()))
        if len(cyc) != 4 or len(set(cyc)) != 4 or any(type(v) is not int for v in cyc):
            raise Bad('a cycle row names four distinct vertices')
        edges = [tuple(sorted((cyc[i], cyc[(i + 1) % 4]))) for i in range(4)]
        if not set(edges) <= Eset:
            raise Bad(f'row on {cyc} is not a 4-cycle of this host')
        rhs = 3
    elif q.get('kind') == 'pattern':
        pat = registry['patterns'].get(q.get('pattern'))
        if pat is None:
            raise Bad(f'unknown pattern {q.get("pattern")!r}')
        phi = list(q.get('map', ()))
        if len(phi) != pat['vertices'] or len(set(phi)) != len(phi) or any(type(v) is not int for v in phi):
            raise Bad('pattern map is not an injective vertex map of the right size')
        edges = [tuple(sorted((phi[a], phi[b]))) for a, b in pat['edges']]
        if not set(edges) <= Eset:
            raise Bad('pattern map sends an edge outside this host')
        rhs = pat['ex']
    else:
        raise Bad(f'unknown row kind {q.get("kind")!r}')
    if q.get('rhs') != rhs:
        raise Bad('wrong right-hand side')
    return edges, rhs


def _leaf(leaf, registry, E, Eset, F0, F1, upper):
    if not isinstance(leaf, dict):
        raise Bad('a leaf is an object')
    if leaf.get('kind') == 'infeasible':
        edges, rhs = row_edges(leaf.get('row') or {}, registry, Eset)
        if sum(1 for e in edges if e in F1) <= rhs:
            raise Bad('an infeasible leaf names a row its fixed-in edges do not overfill')
        return
    if leaf.get('kind') != 'dual':
        raise Bad(f'unknown leaf kind {leaf.get("kind")!r}')
    free = [e for e in E if e not in F0 and e not in F1]
    cover = {e: Fraction(0) for e in free}
    total = Fraction(0)
    for q in leaf.get('inequalities', ()):
        weight = Fraction(q['weight'])
        if weight <= 0:
            raise Bad('non-positive inequality weight')
        edges, rhs = row_edges(q, registry, Eset)
        eff = rhs - sum(1 for e in edges if e in F1)
        if eff < 0:
            raise Bad('a dual leaf uses a row its fixed-in edges overfill')
        for e in edges:
            if e in cover:
                cover[e] += weight
        total += weight * eff
    for e, s in leaf.get('slack', ()):
        e, s = tuple(e), Fraction(s)
        if e not in cover or s < 0:
            raise Bad('slack on a fixed or non-host edge, or negative slack')
        cover[e] += s
        total += s
    if any(v < 1 for v in cover.values()):
        raise Bad('dual infeasible at a leaf: a free edge is covered less than once')
    bound = len(F1) + math.floor(total)
    if bound > upper:
        raise Bad(f'a leaf bound {bound} exceeds the claimed upper bound {upper}')


def check_certificate(task, cert, registry):
    """Independent exact check. Returns {'verdict': VALID | REJECTED, 'bound', 'reason', 'leaves'}."""
    def bad(reason):
        return {'verdict': 'REJECTED', 'bound': None, 'reason': reason, 'leaves': None}
    if not isinstance(cert, dict) or cert.get('schema') != SCHEMA:
        return bad('not a C4 branch-and-bound certificate')
    if task.domain != DOMAIN:
        return bad('generated C4 rows are defined for c4_host_v2 hosts only')
    if cert.get('task_sha256') != digest(task.model_dump(mode='json')) or cert.get('domain') != task.domain:
        return bad('certificate names another task')
    if registry.get('schema') != REGISTRY_SCHEMA or cert.get('registry_sha256') != digest(registry):
        return bad('certificate names another registry')
    upper = cert.get('upper')
    if type(upper) is not int or upper < 0:
        return bad('the claimed upper bound is not a nonnegative integer')
    E = [tuple(e) for e in task.edges]
    Eset = set(E)
    stack = [(cert.get('tree'), frozenset(), frozenset())]
    nodes = leaves = 0
    try:
        while stack:
            node, F0, F1 = stack.pop()
            nodes += 1
            if nodes > MAX_NODES:
                return bad('tree too large')
            if not isinstance(node, dict):
                return bad('a tree node is an object')
            if 'leaf' in node:
                _leaf(node['leaf'], registry, E, Eset, F0, F1, upper)
                leaves += 1
                continue
            e = tuple(node.get('branch') or ())
            if len(e) != 2 or e not in Eset or e in F0 or e in F1:
                return bad('a branch names a fixed or non-host edge')
            if 'zero' not in node or 'one' not in node:
                return bad('a branch node lacks a child')
            stack.append((node['zero'], F0 | {e}, F1))
            stack.append((node['one'], F0, F1 | {e}))
    except Bad as exc:
        return bad(str(exc))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return bad(f'malformed certificate ({type(exc).__name__})')
    return {'verdict': 'VALID', 'bound': upper, 'reason': None, 'leaves': leaves}


__all__ = ['SCHEMA', 'check_certificate', 'checker_identity', 'row_edges']
