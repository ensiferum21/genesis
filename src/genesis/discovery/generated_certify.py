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


def pattern_order(registry):
    """Registry patterns, smallest first (vertices, edges, id): the order copies are enumerated in."""
    return sorted(registry['patterns'], key=lambda k: (registry['patterns'][k]['vertices'],
                                                        len(registry['patterns'][k]['edges']), k))


def rows(task, registry, *, stop=None, max_rows=None, order=None):
    """[(kind, edges, rhs, extra)] for the host's triangles and the copies of the registry patterns.
    By default every copy of every pattern, patterns in id order. With `order='size'` patterns are
    taken smallest first; `max_rows` caps the copies per pattern and `stop()` ends enumeration.
    Any subset of copies gives valid rows, so a cap only weakens the bound."""
    from ..invention.cuts import maps
    out = [('triangle', list(t), 2, None) for t in triangles(task)]
    ids = pattern_order(registry) if order == 'size' else sorted(registry['patterns'])
    for pid in ids:
        if stop is not None and stop():
            break
        p = registry['patterns'][pid]
        pat = {'vertices': p['vertices'], 'edges': [tuple(e) for e in p['edges']]}
        for phi in maps(task, pat, stop=stop, limit=max_rows):
            es = sorted(tuple(sorted((phi[a], phi[b]))) for a, b in pat['edges'])
            out.append(('pattern', es, p['ex'], {'pattern': pid, 'map': list(phi)}))
    return out


def lp_dual_rows(task, registry, *, max_denominator=10 ** 6, stop=None, max_rows=None, order=None):
    """(certificate, float LP value, number of rows) from the untrusted LP producer."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    R = rows(task, registry, stop=stop, max_rows=max_rows, order=order)
    base = {'schema': V.SCHEMA, 'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
            'registry_sha256': digest(registry)}
    if not R:
        return dict(base, inequalities=[], slack=[[list(e), '1'] for e in E], objective=str(len(E)),
                    bound=len(E)), float(len(E)), 0
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
    return cert, float(res.fun), nR


def certify_with_rows(task, witness, registry, *, seconds=600, sat_fallback=True, separation_seconds=None,
                      max_rows=None):
    """Joint certification as `obstruction.certify`, with the generated rows in the LP step.
    With `separation_seconds` (wall) and/or `max_rows` (per pattern), copies are enumerated
    smallest pattern first and enumeration stops at either limit (B20_R35); by default every copy
    of every pattern is used (B20_R32).
    Returns {'lower', 'upper', 'method', 'steps', 'wall_s', 'certificate'}; optimum iff lower == upper."""
    from ..verification.sat import certify_upper, witness_from_model
    start = time.monotonic()
    checked = check_witness(task, [tuple(e) for e in witness])
    lower = checked['value']
    steps = []
    t0, w0 = time.process_time(), time.monotonic()
    limited = separation_seconds is not None or max_rows is not None
    stop = (lambda: time.monotonic() - w0 >= separation_seconds) if separation_seconds is not None else None
    cert, lp_value, n_rows = lp_dual_rows(task, registry, stop=stop, max_rows=max_rows,
                                          order='size' if limited else None)
    v = V.check_certificate(task, cert, registry)
    steps.append({'step': 'lp-dual-rows', 'rows': n_rows, 'lp_value': lp_value, 'verdict': v['verdict'],
                  'bound': v['bound'], 'reason': v['reason'], 'cpu_s': round(time.process_time() - t0, 3),
                  'wall_s': round(time.monotonic() - w0, 3)})
    upper, method, certificate = len(task.edges), 'HOST_EDGE_COUNT', None
    if v['verdict'] == 'VALID' and v['bound'] < upper:
        upper, method, certificate = v['bound'], 'LP_DUAL_GENERATED_EXACT', cert
    if lower < upper and sat_fallback:
        calls = []
        while lower < upper:
            remaining = int(seconds - (time.monotonic() - start))
            if remaining < 1:
                break
            scert, rec, _, _ = certify_upper(task, lower, seconds=remaining)
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
            lower = checked2['value']
        steps.append({'step': 'sat-drat', 'calls': calls})
    return {'lower': lower, 'upper': upper, 'method': method, 'steps': steps,
            'wall_s': round(time.monotonic() - start, 3), 'certificate': certificate}


__all__ = ['load_registry', 'rows', 'pattern_order', 'lp_dual_rows', 'certify_with_rows', 'PACKAGE']
