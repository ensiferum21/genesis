"""Certification with generated rows (B20_R32; untrusted producer, DEV only).

`obstruction.certify` is the evaluator's joint certification. It first tries an exact LP dual
certificate over the host's triangles, then SAT/DRAT on the remaining gap within the budget.
`certify_with_rows` is the same procedure, with one change: the LP also has a row for every copy
of every generated pattern in a registry (`verification.lp_dual_rows.registry_from_package`; the
patterns are B20_R31's Lean-checked K5 and W5 bounds). A tighter LP can close the gap without
SAT.

The LP is solved by scipy/HiGHS, an untrusted float producer. Its dual is turned into exact
rationals, the slacks are repaired exactly, and `verification.lp_dual_rows.check_certificate`
checks the result independently. The SAT/DRAT step is the evaluator's own
(`verification.sat.certify_upper`), unchanged. This route builds no certificate bundle and is not
wired into the evaluator: it is a component under DEV measurement.
"""
from fractions import Fraction
import json
import math
from pathlib import Path
import time

from ..common import digest
from ..graphs import check_witness
from ..verification import lp_dual_rows as V
from .obstruction import triangles

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / 'evidence' / 'relaxation_invention_b20r31' / 'package.json'


def load_registry(path=PACKAGE):
    """The generated-row registry of a theory package, after its hash checks."""
    from ..formal_research import theory_package as TP
    from ..formal_research.triangle_theory import DEFS_SOURCE
    pkg = json.loads(Path(path).read_text())
    problems = TP.integrity_problems(pkg)
    if problems:
        raise ValueError(f'theory package fails its integrity checks: {problems}')
    return V.registry_from_package(pkg, defs_source=DEFS_SOURCE)


def pattern_order(registry, order='size'):
    """Registry pattern ids in enumeration order: 'size' is smallest first (vertices, edges, id;
    B20_R35); 'dense-first' is highest edge density first, then more vertices (B20_R37)."""
    P = registry['patterns']
    if order == 'dense-first':
        dens = lambda k: len(P[k]['edges']) / (P[k]['vertices'] * (P[k]['vertices'] - 1) / 2)
        return sorted(P, key=lambda k: (-dens(k), -P[k]['vertices'], k))
    return sorted(P, key=lambda k: (P[k]['vertices'], len(P[k]['edges']), k))


def rows(task, registry, *, stop=None, max_rows=None, order=None, enumerator=None, max_total=None):
    """[(kind, edges, rhs, extra)] for the host's triangles and the copies of the registry patterns.
    By default every copy of every pattern, patterns in id order, by invention.cuts.maps. With
    `order` ('size' or 'dense-first') patterns are taken in that order; `max_rows` caps the copies
    per pattern, `max_total` all pattern copies, and `stop()` ends enumeration;
    `enumerator='fast'` uses invention.cuts_v2.maps_fast (one map per copy, by symmetry breaking).
    Any subset of copies gives valid rows, so a cap only weakens the bound."""
    from ..invention.cuts import maps as generic
    out = [('triangle', list(t), 2, None) for t in triangles(task)]
    ids = pattern_order(registry, order) if order in ('size', 'dense-first') else sorted(registry['patterns'])
    total = 0
    for pid in ids:
        if stop is not None and stop():
            break
        if max_total is not None and total >= max_total:
            break
        p = registry['patterns'][pid]
        pat = {'vertices': p['vertices'], 'edges': [tuple(e) for e in p['edges']]}
        cap = max_rows if max_total is None else min(x for x in (max_rows, max_total - total) if x is not None)
        if enumerator == 'fast':
            from ..invention.cuts_v2 import maps_fast
            found = maps_fast(task, pat, stop=stop, limit=cap)[0]
        else:
            found = generic(task, pat, stop=stop, limit=cap)
        total += len(found)
        for phi in found:
            es = sorted(tuple(sorted((phi[a], phi[b]))) for a, b in pat['edges'])
            out.append(('pattern', es, p['ex'], {'pattern': pid, 'map': list(phi)}))
    return out


def lp_dual_rows(task, registry, **kw):
    """(certificate, float LP value, number of rows) from the untrusted LP producer."""
    return lp_dual_rows_x(task, registry, **kw)[:3]


def lp_dual_rows_x(task, registry, *, max_denominator=10 ** 6, stop=None, max_rows=None, order=None, enumerator=None,
                   max_total=None):
    """As lp_dual_rows, plus the LP's edge values x (HiGHS's duals of the cover rows; untrusted
    floats, used only to guide a primal heuristic, never as evidence; B20_R41)."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    R = rows(task, registry, stop=stop, max_rows=max_rows, order=order, enumerator=enumerator, max_total=max_total)
    base = {'schema': V.SCHEMA, 'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
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
        if not y[j]:
            continue
        q = {'kind': kind, 'rhs': rhs, 'weight': str(y[j])}
        q.update({'edges': [list(e) for e in es]} if kind == 'triangle' else extra)
        ineq.append(q)
    cert = dict(base, inequalities=ineq, slack=[[list(E[i]), str(w[i])] for i in range(nE) if w[i]],
                objective=str(objective), bound=math.floor(objective))
    x = [max(0.0, -float(m)) for m in res.ineqlin.marginals]
    return cert, float(res.fun), nR, x


def certify_with_rows(task, witness, registry, *, seconds=600, sat_fallback=True, separation_seconds=None,
                      max_rows=None, order=None, enumerator=None, max_total=None, lp_rounding_seconds=None):
    """Joint certification as `obstruction.certify`, with the generated rows in the LP step.
    With `separation_seconds` (wall) and/or `max_rows` (per pattern), copies are enumerated
    smallest pattern first and enumeration stops at either limit (B20_R35); by default every copy
    of every pattern is used (B20_R32). B20_R37 adds `order`, `enumerator` and `max_total` (see rows).
    B20_R41 adds `lp_rounding_seconds`: after the LP step, construct.lp_greedy guided by the LP's own
    edge values for that many CPU seconds, kept if the checked witness is larger. It uses nothing
    but the host and the route's LP, so it stays candidate-blind; off by default (earlier results
    unchanged).
    Returns {'lower', 'upper', 'method', 'steps', 'wall_s', 'certificate'}; optimum iff lower == upper."""
    from ..verification.sat import certify_upper, witness_from_model
    start = time.monotonic()
    checked = check_witness(task, [tuple(e) for e in witness])
    lower, best = checked['value'], checked['selected']
    steps = []
    t0, w0 = time.process_time(), time.monotonic()
    limited = separation_seconds is not None or max_rows is not None
    stop = (lambda: time.monotonic() - w0 >= separation_seconds) if separation_seconds is not None else None
    cert, lp_value, n_rows, x = lp_dual_rows_x(task, registry, stop=stop, max_rows=max_rows,
                                               order=order or ('size' if limited else None), enumerator=enumerator,
                                               max_total=max_total)
    v = V.check_certificate(task, cert, registry)
    steps.append({'step': 'lp-dual-rows', 'rows': n_rows, 'lp_value': lp_value, 'verdict': v['verdict'],
                  'bound': v['bound'], 'reason': v['reason'], 'cpu_s': round(time.process_time() - t0, 3),
                  'wall_s': round(time.monotonic() - w0, 3)})
    if lp_rounding_seconds:
        from .construct import Budget, lp_greedy
        t1, w1 = time.process_time(), time.monotonic()
        rounded = check_witness(task, [tuple(e) for e in lp_greedy(task, Budget(lp_rounding_seconds), 0, x=x)['witness']])
        steps.append({'step': 'lp-rounding', 'value': rounded['value'], 'improved': rounded['value'] > lower,
                      'fractional_edges': sum(1e-6 < xi < 1 - 1e-6 for xi in x),
                      'cpu_s': round(time.process_time() - t1, 3), 'wall_s': round(time.monotonic() - w1, 3)})
        if rounded['value'] > lower:
            lower, best = rounded['value'], rounded['selected']
    upper, method, certificate, sat_custody = len(task.edges), 'HOST_EDGE_COUNT', None, None
    if v['verdict'] == 'VALID' and v['bound'] < upper:
        upper, method, certificate = v['bound'], 'LP_DUAL_GENERATED_EXACT', cert
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
                    sat_custody = {'method': 'SAT_DRAT', 'certificate': scert, 'cnf': cnf, 'proof': proof}
                break
            if rec['status'] != 'SAT':
                break
            checked2 = check_witness(task, witness_from_model(task, rec['model']))
            if checked2['value'] <= lower:
                break
            lower, best = checked2['value'], checked2['selected']
        steps.append({'step': 'sat-drat', 'calls': calls})
    return {'lower': lower, 'upper': upper, 'method': method, 'steps': steps, 'sat_custody': sat_custody,
            'witness': [list(e) for e in best],
            'wall_s': round(time.monotonic() - start, 3), 'certificate': certificate}


def reference(task, package, *, seconds=600, evidence=None, **route):
    """A joint reference over generated rows (B20_R39; built, not wired into the evaluator). It
    mirrors domains.GraphHostAdapter._joint_reference: the evaluator's seed witness, then
    certify_with_rows with the package's registry. A certified result is taken into custody:
    LP_DUAL_GENERATED_EXACT in a certificates_rows bundle, SAT_DRAT in an ordinary v2 bundle.
    With `evidence` (a directory), the objects and bundle are written there. Returns the
    reference record (FINITE_CERTIFIED with value and method, or UNSUPPORTED with a reason)."""
    from ..dsl import solve
    from ..formal_research.triangle_theory import DEFS_SOURCE
    from ..models import SolverProgram
    from ..verification import certificates as CB
    from ..verification import certificates_rows as CR
    from .construct import Budget, lp_greedy
    registry = V.registry_from_package(package, defs_source=DEFS_SOURCE)
    start = tuple(map(tuple, solve(task, SolverProgram(rounds=8), 100000, 0)['selected']))
    lp = tuple(map(tuple, lp_greedy(task, Budget(1.0), 0)['witness']))
    rec = certify_with_rows(task, max((start, lp), key=len), registry, seconds=seconds, **route)
    if rec['lower'] != rec['upper']:
        return {'status': 'UNSUPPORTED', 'reason': f'optimum not certified within {seconds}s by the generated-rows '
                                                    f'route (bounds {rec["lower"]}..{rec["upper"]})'}
    if rec['method'] == 'LP_DUAL_GENERATED_EXACT':
        bundle, blobs = CR.build(task, witness=rec['witness'], lower=rec['lower'], certificate=rec['certificate'],
                                 package=package, attempts=rec['steps'])
    elif rec['method'] == 'SAT_DRAT':
        bundle, blobs = CB.build_v2(task, witness=rec['witness'], lower=rec['lower'], upper=rec['sat_custody'],
                                    attempts=rec['steps'])
    else:
        bundle, blobs = CB.build_v2(task, witness=rec['witness'], lower=rec['lower'],
                                    upper={'method': 'HOST_EDGE_COUNT'}, attempts=rec['steps'])
    out = {'status': 'FINITE_CERTIFIED', 'value': rec['upper'], 'method': 'GENERATED_ROWS_' + rec['method'],
           'witness': rec['witness'], 'certificate_status': bundle['status'], 'bundle_schema': bundle['schema']}
    if evidence is not None:
        out['certificate_bundle'] = CB.persist_dir(evidence, bundle, blobs)
    return out


__all__ = ['load_registry', 'rows', 'pattern_order', 'lp_dual_rows', 'certify_with_rows', 'reference', 'PACKAGE']
