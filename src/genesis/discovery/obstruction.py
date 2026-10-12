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
# The trusted exact checker lives in verification/lp_dual.py (B20_R1, Repair D); re-exported here.
from ..verification.lp_dual import SCHEMA, check_certificate, is_motif as _is_motif  # noqa: F401


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


def certify(task, witness, *, seconds=60, sat_fallback=True):
    """Joint certification: domain-checked witness (lower) against an LP dual certificate
    (upper), then SAT/DRAT on the remaining gap within the budget. Optimum only on a match.

    Custody (B20_R1, Repair D; finding B20-REVIEW-04): the record carries a
    ``genesis-certificate-bundle-v2`` (``record['bundle']``) and the raw objects it names
    (``record['objects']``: sha256 -> bytes): the final lower witness, the exact rational
    LP certificate, and for a SAT/DRAT upper bound the original CNF and DRAT proof. Callers
    must persist the objects before publishing any result (``certificates.persist_dir``,
    ``certificates.persist`` or ``record_evidence``); ``certificates.replay`` re-checks the
    bundle with the producers disabled. Every LP and SAT attempt is listed with its cost.
    """
    from ..verification.certificates import build_v2
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
    upper_custody = {'method': 'HOST_EDGE_COUNT'}
    if v['verdict'] == 'VALID' and v['bound'] < upper:
        upper, evidence = v['bound'], {'method': 'LP_DUAL_EXACT', 'certificate': cert}
        upper_custody = {'method': 'LP_DUAL_EXACT', 'certificate': cert, 'lp_value_float': lp_value}
    if lower < upper and sat_fallback:
        # SAT/DRAT on the remaining gap only: each call asks for lower+1 edges. A model
        # raises the lower bound, re-checked by the domain. An UNSAT proof, verified by
        # drat-trim, closes the gap. The search stops as soon as lower meets the LP bound.
        # The CNF and DRAT bytes of a closing call are kept (they were discarded before B20_R1).
        from ..verification.sat import certify_upper, witness_from_model
        calls = []
        while lower < upper:
            remaining = int(seconds - (time.monotonic() - start))
            if remaining < 1:
                break
            scert, rec, cnf, proof = certify_upper(task, lower, seconds=remaining)
            calls.append({'k': lower + 1, 'status': rec['status'], 'seconds': rec.get('seconds'),
                          'checker_verdict': scert.get('verdict') if scert else None})
            if scert is not None:
                if scert['verdict'] == 'VALID':
                    upper, evidence = lower, {'method': 'SAT_DRAT', 'certificate': scert}
                    upper_custody = {'method': 'SAT_DRAT', 'certificate': scert, 'cnf': cnf, 'proof': proof}
                break
            if rec['status'] != 'SAT':
                break
            checked2 = check_witness(task, witness_from_model(task, rec['model']))
            if checked2['value'] <= lower:
                break
            lower, best = checked2['value'], checked2['selected']
            record['witness'] = [list(e) for e in best]
        record['steps'].append({'step': 'sat-drat', 'calls': calls})
    bundle, objects = build_v2(task, witness=record['witness'], lower=lower, upper=upper_custody,
                               attempts=record['steps'])
    record.update(lower=lower, upper=upper, gap=upper - lower, upper_evidence=evidence,
                  status=bundle['status'], wall_s=round(time.monotonic() - start, 3), bundle=bundle,
                  objects=objects)
    return record


def record_evidence(store, kernel, task, record, *, source_hash, promote=True):
    """Put a ``certify`` result through the shared evidence kernel (Repair D).

    Mirrors the world loop (``worldstep.ResearchLoop._update_evidence``): the problem, the
    certificate objects and the bundle go into the store's CAS first; then a replayable
    witness check (lower) and a bound state referencing the custody-held bundle (upper).
    An optimum claim is promoted only through ``kernel.promote``, which re-checks the
    witness and replays the bundle with the producers disabled; a revoked checker, a
    missing object or a changed coefficient blocks it. Returns the node ids and outcome.
    """
    from ..kernel.evidence import PromotionRejected
    from ..verification.certificates import persist
    from ..verification.lp_dual import checker_identity
    task_sha = store.put(task.model_dump(mode='json'))
    bundle_ref = persist(store, record['bundle'], record['objects'])
    run = kernel.record('execution_receipt', {'task': task.task_id, 'macro': 'joint-certification',
                                              'ir_program': None},
                        route='genesis.discovery.obstruction', source_hash=source_hash, verdict='VALID',
                        effects=['UNCHECKED_PROPOSAL', 'USES_DEV_DATA'])
    check = kernel.record('witness_check', {'schema': 'genesis-witness-check-v2', 'task': task.task_id,
                                            'task_sha256': task_sha, 'witness': record['witness'],
                                            'value': record['lower']},
                          parents=[run], route='genesis.discovery.obstruction', source_hash=source_hash,
                          verdict='VALID', verifier='dual-predicates')
    method = record['bundle']['upper']['method']
    verifier = {'SAT_DRAT': 'drat-trim', 'HOST_EDGE_COUNT': 'host-edge-count'}.get(method) or checker_identity()
    bound = kernel.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': task.task_id,
                                          'task_sha256': task_sha, 'lower': record['lower'],
                                          'upper': record['upper'], 'gap': record['gap'], 'lower_evidence': check,
                                          'certificate_bundle': bundle_ref},
                          parents=[check], route='genesis.discovery.obstruction', source_hash=source_hash,
                          verdict='VALID', verifier=verifier)
    out = {'task_sha256': task_sha, 'bundle': bundle_ref, 'witness_check': check, 'bound_state': bound,
           'claim': None, 'promoted': False, 'rejection': None}
    if record['gap'] == 0:
        claim = f'optimum:{task.task_id}:{record["upper"]}'
        problem = {'task_sha256': task_sha, 'value': record['upper'], 'claim': 'optimum'}
        kernel.create_claim(claim, kernel.math_statement(problem), 'this finite host only', [bound], problem=problem)
        out['claim'] = claim
        if promote:
            try:
                kernel.promote(claim, 'math', 'OPTIMALITY_CHECKED')
                out['promoted'] = True
            except PromotionRejected as exc:
                out['rejection'] = exc.args[0]
    return out


__all__ = ['lp_dual', 'check_certificate', 'certify', 'record_evidence', 'triangles', 'four_cycles', 'SCHEMA']
