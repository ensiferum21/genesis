"""Exact checker for LP dual upper-bound certificates (trusted side of roadmap W13).

Moved verbatim from ``discovery/obstruction.py`` in B20_R1 (Repair D) so that the trusted
checker is a small module of its own. Its identity (:func:`checker_identity`) is the
SHA-256 of this file; a certificate bundle records it, and a revoked identity blocks
replay. The untrusted producer (scipy/HiGHS in ``obstruction.lp_dual``) stays outside.

Weak duality, for the largest motif-free subgraph S of a host H: any y >= 0 over motifs
and w >= 0 over edges with sum_{M containing e} y_M + w_e >= 1 for every edge e gives
|S| <= sum_M y_M (|M| - 1) + sum_e w_e, because a motif-free S contains at most |M| - 1
edges of each motif M (the Lean lemma ``motif_not_all`` in the B19 obstruction package).
The checker recomputes the task identity, checks that every inequality is a motif of
this host with the right right-hand side, checks dual feasibility edge by edge in exact
rational arithmetic, and recomputes the bound. It imports no optimisation library.
"""
from fractions import Fraction
import hashlib
import math
from pathlib import Path

from ..common import digest

SCHEMA = 'genesis-lp-dual-certificate-v1'


def checker_identity():
    return 'genesis.verification.lp_dual@' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def is_motif(task, edges):
    """Does this edge set form a forbidden motif of the task's own host?"""
    E = set(map(tuple, task.edges))
    edges = [tuple(e) for e in edges]
    if len(set(edges)) != len(edges) or not set(edges) <= E:
        return False
    if task.domain == 'triangle_free_host_v1':
        if len(edges) != 3:
            return False
        vs = sorted({x for e in edges for x in e})
        if len(vs) != 3:
            return False
        a, b, c = vs
        return set(edges) == {(a, b), (b, c), (a, c)}
    if len(edges) != 4:
        return False
    vs = {x for e in edges for x in e}
    deg = {v: sum(v in e for e in edges) for v in vs}
    if len(vs) != 4 or any(d != 2 for d in deg.values()):
        return False
    # connected 2-regular on 4 vertices = a 4-cycle
    seen, stack = set(), [next(iter(vs))]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack += [y for e in edges for y in e if x in e and y != x]
    return seen == vs


def check_certificate(task, cert):
    """Independent exact check. Returns {'verdict': VALID | REJECTED, 'bound', 'reason'}."""
    def bad(reason):
        return {'verdict': 'REJECTED', 'bound': None, 'reason': reason}
    if not isinstance(cert, dict) or cert.get('schema') != SCHEMA:
        return bad('not an LP dual certificate')
    if cert.get('task_sha256') != digest(task.model_dump(mode='json')) or cert.get('domain') != task.domain:
        return bad('certificate names another task')
    E = [tuple(e) for e in task.edges]
    cover = {e: Fraction(0) for e in E}
    total = Fraction(0)
    try:
        for q in cert['inequalities']:
            edges = [tuple(e) for e in q['edges']]
            weight = Fraction(q['weight'])
            if weight <= 0:
                return bad('non-positive inequality weight')
            if not is_motif(task, edges):
                return bad(f'inequality on {edges} is not a motif of this host')
            if q['rhs'] != len(edges) - 1:
                return bad('wrong right-hand side for a motif inequality')
            for e in edges:
                cover[e] += weight
            total += weight * q['rhs']
        for e, s in cert['slack']:
            e, s = tuple(e), Fraction(s)
            if e not in cover or s < 0:
                return bad('slack on a non-edge or negative slack')
            cover[e] += s
            total += s
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return bad(f'malformed certificate ({type(exc).__name__})')
    short = [e for e, v in cover.items() if v < 1]
    if short:
        return bad(f'dual infeasible: {len(short)} edges are covered less than once')
    if Fraction(cert['objective']) != total or cert['bound'] != math.floor(total):
        return bad('objective or bound does not match the weights')
    return {'verdict': 'VALID', 'bound': math.floor(total), 'reason': None}


__all__ = ['SCHEMA', 'check_certificate', 'is_motif', 'checker_identity']
