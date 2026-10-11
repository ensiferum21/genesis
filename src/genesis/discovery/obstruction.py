"""Construction meets obstruction: LP relaxation with exact dual certificates (roadmap W13).

Source problem: the largest motif-free subgraph S of a host H (maximise |S|).
Target: the LP relaxation, max Σ x_e subject to x(M) ≤ |M| − 1 for every motif M of H
(triangles, or 4-cycles) and 0 ≤ x ≤ 1.

The relationship between source and target is checked in three parts:
  * Feasibility mapping. A motif-free S gives its indicator vector, which satisfies every
    inequality. That validity is the Lean lemma `motif_not_all` ("a triangle-free set
    does not contain all three edges of a triangle"), proved in the B19 obstruction
    package.
  * Objective direction. Both problems maximise, so the LP optimum is at least the
    integer optimum.
  * Weak duality. Any y ≥ 0 and w ≥ 0 with Σ_{M ∋ e} y_M + w_e ≥ 1 for every edge e gives
      |S| = Σ_e x_e ≤ Σ_M y_M x(M) + Σ_e w_e x_e ≤ Σ_M y_M (|M| − 1) + Σ_e w_e.
    The integer optimum is therefore at most the floor of that objective.

The LP is solved by scipy/HiGHS, an untrusted floating-point producer. Its dual is turned
into exact rationals and repaired to be feasible exactly: each slack w_e is raised to cover
its edge. `check_certificate` is a small independent checker in exact arithmetic. It
recomputes the task identity, checks that every inequality is a motif of this host with
the right right-hand side, checks dual feasibility edge by edge, and recomputes the bound.

An optimum is claimed only when a witness checked by the domain meets a verified upper
certificate: an LP dual certificate, or a SAT/DRAT certificate when the LP leaves a gap
and the remaining budget allows.
"""
from fractions import Fraction
import math
import time

from ..common import digest
from ..graphs import check_witness

SCHEMA = 'genesis-lp-dual-certificate-v1'


def triangles(task):
    E = set(map(tuple, task.edges))
    adj = {}
    for u, v in E:
        adj.setdefault(u, set()).add(v); adj.setdefault(v, set()).add(u)
    out = []
    for u, v in sorted(E):
        for w in sorted(adj[u] & adj[v]):
            if w > v:
                out.append(((u, v), (v, w), (u, w)))
    return out


def four_cycles(task):
    from ..graphs import motifs
    E = list(task.edges)
    out = []
    for m in motifs(task):
        es, r = [], m
        while r:
            b = r & -r; r ^= b
            es.append(E[b.bit_length() - 1])
        out.append(tuple(sorted(es)))
    return out


def motifs_of(task):
    return triangles(task) if task.domain == 'triangle_free_host_v1' else four_cycles(task)


def _is_motif(task, edges):
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


def lp_dual(task, *, max_denominator=10 ** 6):
    """(certificate, float LP value) from the untrusted LP producer."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    M = motifs_of(task)
    if not M:
        cert = {'schema': SCHEMA, 'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
                'inequalities': [], 'slack': [[list(e), '1'] for e in E], 'objective': str(len(E)), 'bound': len(E)}
        return cert, float(len(E))
    # dual: min Σ (|M|-1) y_M + Σ w_e  s.t.  Σ_{M ∋ e} y_M + w_e >= 1,  y, w >= 0
    nM, nE = len(M), len(E)
    A = lil_matrix((nE, nM + nE))
    for j, m in enumerate(M):
        for e in m:
            A[idx[e], j] = 1
    for i in range(nE):
        A[i, nM + i] = 1
    c = np.array([len(m) - 1 for m in M] + [1] * nE, dtype=float)
    r = linprog(c, A_ub=-A.tocsr(), b_ub=-np.ones(nE), bounds=(0, None), method='highs')
    if r.status != 0:
        raise RuntimeError(f'LP producer failed: {r.message}')
    y = [Fraction(float(v)).limit_denominator(max_denominator) if v > 1e-12 else Fraction(0) for v in r.x[:nM]]
    cover = [Fraction(0)] * nE
    for j, m in enumerate(M):
        if y[j]:
            for e in m:
                cover[idx[e]] += y[j]
    w = [max(Fraction(0), 1 - cover[i]) for i in range(nE)]        # exact repair of the slacks
    objective = sum(y[j] * (len(M[j]) - 1) for j in range(nM)) + sum(w)
    cert = {'schema': SCHEMA, 'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
            'inequalities': [{'edges': [list(e) for e in M[j]], 'rhs': len(M[j]) - 1, 'weight': str(y[j])}
                             for j in range(nM) if y[j]],
            'slack': [[list(E[i]), str(w[i])] for i in range(nE) if w[i]],
            'objective': str(objective), 'bound': math.floor(objective)}
    return cert, float(r.fun)


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
            if not _is_motif(task, edges):
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


def certify(task, witness, *, seconds=60, sat_fallback=True):
    """Joint certification: domain-checked witness (lower) against an LP dual certificate
    (upper), then SAT/DRAT on the remaining gap within the budget. Optimum only on a match."""
    start = time.monotonic()
    checked = check_witness(task, [tuple(e) for e in witness])
    lower, best = checked['value'], checked['selected']
    record = {'lower': lower, 'witness': [list(e) for e in best], 'steps': []}
    t0 = time.process_time()
    cert, lp_value = lp_dual(task)
    v = check_certificate(task, cert)
    record['steps'].append({'step': 'lp-dual', 'lp_value': lp_value, 'verdict': v['verdict'], 'bound': v['bound'],
                            'cpu_s': round(time.process_time() - t0, 3)})
    upper, evidence = len(task.edges), {'method': 'HOST_EDGE_COUNT'}
    if v['verdict'] == 'VALID' and v['bound'] < upper:
        upper, evidence = v['bound'], {'method': 'LP_DUAL_EXACT', 'certificate': cert}
    if lower < upper and sat_fallback:
        # SAT/DRAT on the remaining gap only: each call asks for lower+1 edges. A model
        # raises the lower bound, re-checked by the domain. An UNSAT proof, verified by
        # drat-trim, closes the gap. The search stops as soon as lower meets the LP bound.
        from ..verification.sat import certify_upper, witness_from_model
        calls = []
        while lower < upper:
            remaining = int(seconds - (time.monotonic() - start))
            if remaining < 1:
                break
            cert, rec, _, _ = certify_upper(task, lower, seconds=remaining)
            calls.append({'k': lower + 1, 'status': rec['status'], 'seconds': rec.get('seconds')})
            if cert is not None:
                if cert['verdict'] == 'VALID':
                    upper, evidence = lower, {'method': 'SAT_DRAT', 'certificate': cert}
                break
            if rec['status'] != 'SAT':
                break
            checked2 = check_witness(task, witness_from_model(task, rec['model']))
            if checked2['value'] <= lower:
                break
            lower, best = checked2['value'], checked2['selected']
            record['witness'] = [list(e) for e in best]
        record['steps'].append({'step': 'sat-drat', 'calls': calls})
    record.update(lower=lower, upper=upper, gap=upper - lower, upper_evidence=evidence,
                  status='OPTIMALITY_CHECKED' if lower == upper else 'BOUNDS_ONLY',
                  wall_s=round(time.monotonic() - start, 3))
    return record


__all__ = ['lp_dual', 'check_certificate', 'certify', 'triangles', 'four_cycles', 'SCHEMA']
