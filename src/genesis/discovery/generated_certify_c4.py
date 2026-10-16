"""Certification of C4-free optima with generated C4 rows (B20_R47; untrusted producer, DEV only).

The C4 counterpart of `discovery.generated_certify`. The evaluator's joint certification for
c4_host_v2 hosts (`obstruction.certify`) runs LP over the host's 4-cycles, then SAT/DRAT on the
remaining gap. This route makes one change: the LP also has a row for every copy of every generated C4
pattern in a registry (`verification.lp_dual_rows_c4.registry_from_package`; the patterns are
B20_R46's Lean-checked bounds). The LP is solved by scipy/HiGHS, an untrusted float producer. Its dual
is rationalised, the slacks are repaired exactly, and `verification.lp_dual_rows_c4.check_certificate`
checks the result. The SAT/DRAT step is the evaluator's own (`verification.sat.certify_upper`). This
route is not wired into the evaluator.
"""
from fractions import Fraction
import json
import math
from pathlib import Path
import time

from ..common import digest
from ..graphs import check_witness
from ..verification import lp_dual_rows_c4 as V4
from . import generated_certify as GC
from .obstruction import four_cycles

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / 'evidence' / 'c4_generator_b20r46' / 'package.json'


def load_registry(path=PACKAGE):
    """The generated C4 row registry of a theory package, after its hash checks."""
    from ..formal_research import theory_package as TP
    from ..formal_research.triangle_theory import DEFS_SOURCE
    from ..invention.representations import C4_SOURCE
    pkg = json.loads(Path(path).read_text())
    problems = TP.integrity_problems(pkg)
    if problems:
        raise ValueError(f'theory package fails its integrity checks: {problems}')
    return V4.registry_from_package(pkg, defs_source=DEFS_SOURCE, c4_source=C4_SOURCE)


def vertex_cycle(edges):
    """[a, b, c, d] for the 4-cycle with these four edges (a the least vertex, b < d)."""
    adj = {}
    for u, v in edges:
        adj.setdefault(u, []).append(v); adj.setdefault(v, []).append(u)
    a = min(adj)
    b, d = sorted(adj[a])
    c = next(x for x in adj[b] if x != a)
    return [a, b, c, d]


def search_order(vertices, edges):
    """Pattern vertices in the order maps_fast should place them: the highest-degree vertex first, then
    always the unplaced vertex with the most edges to placed ones (then higher degree, then lower id).
    maps_fast places vertices in label order and only intersects neighbourhoods of placed neighbours, so a
    label order that starts with an independent set (K_{2,4} as generated) enumerates every tuple of host
    vertices first. The order changes the search only: the copies found are the same."""
    adj = {v: set() for v in range(vertices)}
    for u, v in edges:
        adj[u].add(v); adj[v].add(u)
    order = [max(range(vertices), key=lambda v: (len(adj[v]), -v))]
    while len(order) < vertices:
        placed = set(order)
        order.append(max((v for v in range(vertices) if v not in placed),
                         key=lambda v: (len(adj[v] & placed), len(adj[v]), -v)))
    return order


def rows(task, registry, *, stop=None, max_rows=None, order='dense-first', max_total=None):
    """[(kind, edges, rhs, extra)]: the host's 4-cycles (rhs 3) and the copies of the registry's patterns,
    densest first, one map per copy (invention.cuts_v2.maps_fast on the pattern relabelled by
    search_order; maps are returned in the registry's labels), within the caps."""
    from ..invention.cuts_v2 import maps_fast
    out = []
    for es in four_cycles(task):
        out.append(('cycle', [tuple(e) for e in es], 3, {'cycle': vertex_cycle(es)}))
    total = 0
    for pid in GC.pattern_order(registry, order):
        if stop is not None and stop():
            break
        if max_total is not None and total >= max_total:
            break
        p = registry['patterns'][pid]
        k, pedges = p['vertices'], [tuple(e) for e in p['edges']]
        seq = search_order(k, pedges)
        pos = {v: i for i, v in enumerate(seq)}
        relabelled = {'vertices': k, 'edges': [tuple(sorted((pos[a], pos[b]))) for a, b in pedges]}
        cap = max_rows if max_total is None else min(x for x in (max_rows, max_total - total) if x is not None)
        found = maps_fast(task, relabelled, stop=stop, limit=cap)[0]
        total += len(found)
        for psi in found:
            phi = [psi[pos[v]] for v in range(k)]
            es = sorted(tuple(sorted((phi[a], phi[b]))) for a, b in pedges)
            out.append(('pattern', es, p['ex'], {'pattern': pid, 'map': phi}))
    return out


def lp_dual_rows_x(task, registry, *, max_denominator=10 ** 6, **kw):
    """(certificate, float LP value, number of rows, edge values x) from the untrusted LP producer."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    R = rows(task, registry, **kw)
    base = {'schema': V4.SCHEMA, 'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
            'registry_sha256': digest(registry)}
    if not R:
        return dict(base, inequalities=[], slack=[[list(e), '1'] for e in E], objective=str(len(E)),
                    bound=len(E)), float(len(E)), 0, [1.0] * len(E)
    nR, nE = len(R), len(E)
    A = lil_matrix((nE, nR + nE))
    for j, (_, es, _, _) in enumerate(R):
        for e in es:
            A[idx[e], j] = 1
    for i in range(nE):
        A[i, nR + i] = 1
    c = np.array([r[2] for r in R] + [1] * nE, dtype=float)
    res = linprog(c, A_ub=-A.tocsr(), b_ub=-np.ones(nE), bounds=(0, None), method='highs')
    if res.status != 0:
        raise RuntimeError(f'LP producer failed: {res.message}')
    y = [Fraction(float(v)).limit_denominator(max_denominator) if v > 1e-12 else Fraction(0) for v in res.x[:nR]]
    cover = [Fraction(0)] * nE
    for j, (_, es, _, _) in enumerate(R):
        if y[j]:
            for e in es:
                cover[idx[e]] += y[j]
    w = [max(Fraction(0), 1 - cover[i]) for i in range(nE)]
    objective = sum(y[j] * R[j][2] for j in range(nR)) + sum(w)
    ineq = []
    for j, (kind, es, rhs, extra) in enumerate(R):
        if y[j]:
            ineq.append(dict({'kind': kind, 'rhs': rhs, 'weight': str(y[j])}, **extra))
    cert = dict(base, inequalities=ineq, slack=[[list(E[i]), str(w[i])] for i in range(nE) if w[i]],
                objective=str(objective), bound=math.floor(objective))
    x = [max(0.0, -float(m)) for m in res.ineqlin.marginals]
    return cert, float(res.fun), nR, x


def certify_with_rows(task, witness, registry, *, seconds=600, sat_fallback=True, separation_seconds=None,
                      max_rows=None, order='dense-first', max_total=None, lp_rounding_seconds=None):
    """As generated_certify.certify_with_rows, for c4_host_v2 hosts. Returns {'lower', 'upper', 'method',
    'steps', 'wall_s', 'certificate', 'witness'}; the optimum is certified iff lower == upper."""
    from ..verification.sat import certify_upper, witness_from_model
    start = time.monotonic()
    checked = check_witness(task, [tuple(e) for e in witness])
    lower, best = checked['value'], checked['selected']
    steps = []
    t0, w0 = time.process_time(), time.monotonic()
    stop = (lambda: time.monotonic() - w0 >= separation_seconds) if separation_seconds is not None else None
    cert, lp_value, n_rows, x = lp_dual_rows_x(task, registry, stop=stop, max_rows=max_rows, order=order,
                                               max_total=max_total)
    v = V4.check_certificate(task, cert, registry)
    steps.append({'step': 'lp-dual-rows-c4', 'rows': n_rows, 'lp_value': lp_value, 'verdict': v['verdict'],
                  'bound': v['bound'], 'reason': v['reason'], 'cpu_s': round(time.process_time() - t0, 3),
                  'wall_s': round(time.monotonic() - w0, 3)})
    if lp_rounding_seconds:
        from .construct import Budget, lp_greedy
        t1, w1 = time.process_time(), time.monotonic()
        rounded = check_witness(task, [tuple(e) for e in lp_greedy(task, Budget(lp_rounding_seconds), 0, x=x)['witness']])
        steps.append({'step': 'lp-rounding', 'value': rounded['value'], 'improved': rounded['value'] > lower,
                      'cpu_s': round(time.process_time() - t1, 3), 'wall_s': round(time.monotonic() - w1, 3)})
        if rounded['value'] > lower:
            lower, best = rounded['value'], rounded['selected']
    upper, method, certificate = len(task.edges), 'HOST_EDGE_COUNT', None
    if v['verdict'] == 'VALID' and v['bound'] < upper:
        upper, method, certificate = v['bound'], 'LP_DUAL_GENERATED_C4_EXACT', cert
    if lower < upper and sat_fallback:
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
                    upper, method, certificate = lower, 'SAT_DRAT', None
                break
            if rec['status'] != 'SAT':
                break
            checked2 = check_witness(task, witness_from_model(task, rec['model']))
            if checked2['value'] <= lower:
                break
            lower, best = checked2['value'], checked2['selected']
        steps.append({'step': 'sat-drat', 'calls': calls})
    return {'lower': lower, 'upper': upper, 'method': method, 'steps': steps, 'witness': [list(e) for e in best],
            'wall_s': round(time.monotonic() - start, 3), 'certificate': certificate}


__all__ = ['search_order', 'rows', 'lp_dual_rows_x', 'certify_with_rows', 'vertex_cycle', 'load_registry', 'PACKAGE']
