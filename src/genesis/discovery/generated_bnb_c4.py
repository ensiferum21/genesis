"""Certification of C4-free optima by branch and bound over generated C4 rows (B20_R48; untrusted producer, DEV).

`generated_certify_c4` (B20_R47) solves one LP over the host's 4-cycle rows and the copies of B20_R46's
Lean-checked patterns. On the hosts it left open, its bound was 1 to 5 above the optimum. A development probe
found the gap to be global: rows on up to 8 vertices that the LP violates barely moved it. This route keeps
the same rows and branches instead.
  * Depth-first search. Each node fixes some host edges out (F0) and some in (F1). Its LP is the rows LP
    on the free edges, with each row's right side reduced by its fixed-in edges.
  * A node is closed when its exact dual bound |F1| + ⌊dual objective⌋ is at most the incumbent, or when
    a row's fixed-in edges overfill it.
  * Otherwise it branches on its most fractional free edge, fixed-in child first.
  * An integral LP solution at a node is checked as C4-free and becomes the incumbent if larger.
The LP is solved by scipy/HiGHS, an untrusted float producer. Every leaf's dual is rationalised and its
slacks repaired exactly, and the whole tree is checked by `verification.lp_dual_tree_c4`. When the search
does not finish in time, the route falls back to the root's rows certificate (a one-leaf tree). There is
no SAT step. This route is not wired into the evaluator.
"""
from fractions import Fraction
import math
import time

from ..common import digest
from ..graphs import check_witness
from ..verification import lp_dual_tree_c4 as VT
from . import generated_certify_c4 as GC4

METHOD_TREE, METHOD_ROOT, METHOD_NONE = 'LP_DUAL_TREE_C4_EXACT', 'LP_DUAL_GENERATED_C4_EXACT', 'HOST_EDGE_COUNT'


def _row_spec(row):
    kind, _, rhs, extra = row
    return dict({'kind': kind, 'rhs': rhs}, **extra)


def node_lp(R, idx_rows, nE, F0, F1, *, max_denominator=10 ** 6):
    """At fixings (index sets F0, F1): ('infeasible', row index) or ('dual', exact objective, leaf, x) where
    leaf is the rationalised dual (inequalities, slack on free edges) and x the float primal on free edges."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix
    free = [i for i in range(nE) if i not in F0 and i not in F1]
    pos = {i: k for k, i in enumerate(free)}
    data, ri, ci, rhs, keep = [], [], [], [], []
    for j, es in enumerate(idx_rows):
        f1 = sum(1 for i in es if i in F1)
        if f1 > R[j][2]:
            return ('infeasible', j)
        fr = [pos[i] for i in es if i in pos]
        if not fr:
            continue
        r = len(rhs)
        data += [1.0] * len(fr); ri += [r] * len(fr); ci += fr
        rhs.append(R[j][2] - f1); keep.append(j)
    if not free:
        return ('dual', Fraction(0), {'kind': 'dual', 'inequalities': [], 'slack': []}, {})
    if rhs:
        A = csr_matrix((data, (ri, ci)), shape=(len(rhs), len(free)))
        res = linprog(-np.ones(len(free)), A_ub=A, b_ub=np.array(rhs, float), bounds=(0, 1), method='highs')
        if res.status != 0:
            raise RuntimeError(f'LP producer failed: {res.message}')
        marg, xs = res.ineqlin.marginals, res.x
    else:
        marg, xs = [], [1.0] * len(free)
    y = [Fraction(float(-m)).limit_denominator(max_denominator) if -m > 1e-12 else Fraction(0) for m in marg]
    cover = [Fraction(0)] * len(free)
    ineq = []
    obj = Fraction(0)
    for k, j in enumerate(keep):
        if y[k]:
            for i in idx_rows[j]:
                if i in pos:
                    cover[pos[i]] += y[k]
            obj += y[k] * rhs[k]
            ineq.append(dict(_row_spec(R[j]), weight=str(y[k])))
    slack = []
    for k, i in enumerate(free):
        if cover[k] < 1:
            s = 1 - cover[k]
            obj += s
            slack.append((i, s))
    x = {free[k]: float(v) for k, v in enumerate(xs)}
    return ('dual', obj, {'kind': 'dual', 'inequalities': ineq, 'slack': slack}, x)


def certify_with_tree(task, witness, registry, *, seconds=60, separation_seconds=15, max_rows=50000, max_total=80000,
                      order='dense-first', lp_rounding_seconds=1.0, max_denominator=10 ** 6):
    """Returns {'lower', 'upper', 'method', 'steps', 'wall_s', 'certificate', 'witness', 'nodes', 'leaves'}; the
    optimum is certified iff lower == upper. The certificate is a tree certificate (verification.lp_dual_tree_c4)."""
    start = time.monotonic()
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    checked = check_witness(task, [tuple(e) for e in witness])
    lower, best = checked['value'], checked['selected']
    steps = []
    w0 = time.monotonic()
    stop = (lambda: time.monotonic() - w0 >= separation_seconds) if separation_seconds is not None else None
    R = GC4.rows(task, registry, stop=stop, max_rows=max_rows, order=order, max_total=max_total)
    idx_rows = [[idx[e] for e in es] for _, es, _, _ in R]
    steps.append({'step': 'rows', 'rows': len(R), 'wall_s': round(time.monotonic() - w0, 3)})

    def leaf_json(leaf):
        return {'kind': 'dual', 'inequalities': leaf['inequalities'],
                'slack': [[list(E[i]), str(s)] for i, s in leaf['slack']]}

    base = {'schema': VT.SCHEMA, 'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
            'registry_sha256': digest(registry)}
    root = node_lp(R, idx_rows, len(E), frozenset(), frozenset(), max_denominator=max_denominator)
    root_bound = math.floor(root[1])
    root_leaf = leaf_json(root[2])
    steps.append({'step': 'root-lp', 'bound': root_bound, 'wall_s': round(time.monotonic() - start, 3)})
    if lp_rounding_seconds:
        from .construct import Budget, lp_greedy
        xfull = [root[3].get(i, 0.0) for i in range(len(E))]
        rounded = check_witness(task, [tuple(e) for e in lp_greedy(task, Budget(lp_rounding_seconds), 0, x=xfull)['witness']])
        steps.append({'step': 'lp-rounding', 'value': rounded['value'], 'improved': rounded['value'] > lower})
        if rounded['value'] > lower:
            lower, best = rounded['value'], rounded['selected']

    def finish(upper, method, tree, nodes, leaves, timed_out):
        cert = dict(base, upper=upper, tree=tree) if tree is not None else None
        steps.append({'step': 'branch-and-bound', 'nodes': nodes, 'leaves': leaves, 'timed_out': timed_out,
                      'wall_s': round(time.monotonic() - start, 3)})
        return {'lower': lower, 'upper': upper, 'method': method, 'steps': steps, 'witness': [list(e) for e in best],
                'wall_s': round(time.monotonic() - start, 3), 'certificate': cert, 'nodes': nodes, 'leaves': leaves}

    if root_bound <= lower:
        return finish(max(root_bound, lower), METHOD_ROOT, {'leaf': root_leaf}, 1, 1, False)
    tree = {}
    stack = [(tree, frozenset(), frozenset(), root)]
    nodes = leaves = 0
    while stack:
        if time.monotonic() - start > seconds:
            upper = max(root_bound, lower)
            method = METHOD_ROOT if root_bound < len(E) else METHOD_NONE
            return finish(upper, method, {'leaf': root_leaf}, nodes, leaves, True)
        node, F0, F1, res = stack.pop()
        if res is None:
            res = node_lp(R, idx_rows, len(E), F0, F1, max_denominator=max_denominator)
        nodes += 1
        if res[0] == 'infeasible':
            node['leaf'] = {'kind': 'infeasible', 'row': _row_spec(R[res[1]])}
            leaves += 1
            continue
        _, obj, leaf, x = res
        bound = len(F1) + math.floor(obj)
        if bound <= lower:
            node['leaf'] = leaf_json(leaf)
            leaves += 1
            continue
        frac = {i: v for i, v in x.items() if 1e-6 < v < 1 - 1e-6}
        if not frac:
            sel = [E[i] for i in F1] + [E[i] for i, v in x.items() if v > 0.5]
            try:
                c = check_witness(task, sel)
            except ValueError:                        # cannot happen with every 4-cycle row present; never trusted
                c = {'value': -1}
            if c['value'] > lower:
                lower, best = c['value'], c['selected']
                stack.append((node, F0, F1, res))
                nodes -= 1
                continue
            frac = x                                  # rounding noise only: branch on any free edge
            if not frac:
                raise RuntimeError('a node with no free edges was neither closed nor improving')
        b = max(frac, key=lambda i: (-abs(frac[i] - 0.5), -i))
        node['branch'] = list(E[b])
        node['zero'], node['one'] = {}, {}
        stack.append((node['zero'], F0 | {b}, F1, None))
        stack.append((node['one'], F0, F1 | {b}, None))
    return finish(lower, METHOD_TREE, tree, nodes, leaves, False)


def reference_record(task, package, *, seconds=120, **route):
    """(record, bundle, blobs): the tree route as a reference (B20_R51, opt-in through v5 requests that name
    'generated-rows-tree-c4-v1'). The seed is the evaluator's own: the better of the DSL rounds=8 solve and
    1 CPU s of LP-ordered greedy. A certified result is taken into custody in a certificates_tree_c4 bundle;
    the objects are returned unwritten (the custodian persists them). An uncertified host gives
    (UNSUPPORTED record, None, None)."""
    from ..dsl import solve
    from ..models import SolverProgram
    from ..verification import certificates_tree_c4 as CT
    from .construct import Budget, lp_greedy
    registry = CT._registry(package)
    start = tuple(map(tuple, solve(task, SolverProgram(rounds=8), 100000, 0)['selected']))
    lp = tuple(map(tuple, lp_greedy(task, Budget(1.0), 0)['witness']))
    rec = certify_with_tree(task, max((start, lp), key=len), registry, seconds=seconds, **route)
    if rec['lower'] != rec['upper'] or rec['certificate'] is None:
        return ({'status': 'UNSUPPORTED', 'reason': f'optimum not certified within {seconds}s by the C4 tree route '
                                                     f'(bounds {rec["lower"]}..{rec["upper"]})'}, None, None)
    bundle, blobs = CT.build(task, witness=rec['witness'], lower=rec['lower'], certificate=rec['certificate'],
                             package=package, attempts=rec['steps'])
    out = {'status': 'FINITE_CERTIFIED', 'value': rec['upper'], 'method': 'GENERATED_ROWS_' + rec['method'],
           'witness': rec['witness'], 'certificate_status': bundle['status'], 'bundle_schema': bundle['schema'],
           'nodes': rec['nodes']}
    return out, bundle, blobs


__all__ = ['certify_with_tree', 'node_lp', 'reference_record', 'METHOD_TREE', 'METHOD_ROOT']
