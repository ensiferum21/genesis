"""Certification of maximum sum-free subsets by branch and bound over generated sum-free rows (B20_R56; untrusted
producer, DEV only).

The sum-free counterpart of `discovery.generated_bnb_c4` (B20_R48), which is unchanged. Rows: every Schur triple and
double of the host (`verification.lp_dual_tree_sf`), and every Freiman-type copy in the host of every registry
pattern (B20_R55's Lean-checked bounds). With an empty registry the route is the conventional Schur-row LP branch
and bound (the registered ablation).
  * Depth-first search. Each node fixes some host elements out (F0) and some in (F1). Its LP is the rows LP on the
    free elements, with each row's right side reduced by its fixed-in elements.
  * A node is closed when its exact dual bound |F1| + ⌊dual objective⌋ is at most the incumbent, or when a row's
    fixed-in elements overfill it.
  * Otherwise it branches on its most fractional free element, fixed-in child first.
  * An integral LP solution at a node is checked as sum-free and becomes the incumbent if larger.
The LP is solved by scipy/HiGHS, an untrusted float producer. Every leaf's dual is rationalised and its slacks
repaired exactly, and the whole tree is checked by `verification.lp_dual_tree_sf`. When the search does not finish
in time, the route falls back to the root's dual (a one-leaf tree).
"""
from fractions import Fraction
import json
import math
from pathlib import Path
import time

from ..common import digest
from ..verification import lp_dual_tree_sf as VT

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / 'evidence' / 'sf_generator_b20r55' / 'package.json'
METHOD_TREE, METHOD_ROOT, METHOD_NONE = 'LP_DUAL_TREE_SUMFREE_EXACT', 'LP_DUAL_ROOT_SUMFREE_EXACT', 'HOST_SIZE'


def load_registry(path=PACKAGE):
    """The generated sum-free row registry of a theory package, after its hash checks."""
    from ..formal_research import theory_package as TP
    from ..invention.cuts_sf import SOURCE
    pkg = json.loads(Path(path).read_text())
    problems = TP.integrity_problems(pkg)
    if problems:
        raise ValueError(f'theory package fails its integrity checks: {problems}')
    return VT.registry_from_package(pkg, sf_source=SOURCE)


def empty_registry(registry):
    """The registered ablation: the same registry with no patterns (Schur rows only)."""
    return dict(registry, patterns={})


def copies(k, relations, host, *, cap=None):
    """Injective maps [y0..yk-1] into `host` with y_a + y_b = y_c for every relation; one per image set."""
    S = set(host)
    hs = sorted(S)
    by_last = {}
    for r in relations:
        by_last.setdefault(max(r), []).append(tuple(r))
    out, seen = [], set()

    def rec(i, phi, used):
        if cap is not None and len(out) >= cap:
            return
        if i == k:
            key = frozenset(phi)
            if key not in seen:
                seen.add(key)
                out.append(list(phi))
            return
        forced = None
        for a, b, c in by_last.get(i, ()):
            if c == i and a < i and b < i:
                forced = phi[a] + phi[b]
                break
        for y in ([forced] if forced is not None else hs):
            if y not in S or y in used:
                continue
            phi.append(y)
            if all(phi[a] + phi[b] == phi[c] for a, b, c in by_last.get(i, ())):
                rec(i + 1, phi, used | {y})
            phi.pop()
    rec(0, [], frozenset())
    return out


def rows(task, registry, *, max_rows=None):
    """[(spec, element list, rhs)] for the host: Schur triples, doubles, then pattern copies in registry order."""
    E = task['elements']
    S = set(E)
    out = []
    for i, a in enumerate(E):
        if a + a in S:
            out.append(({'kind': 'double', 'pair': [a, a + a], 'rhs': 1}, [a, a + a], 1))
        for b in E[i + 1:]:
            if a + b in S:
                out.append(({'kind': 'schur', 'triple': [a, b, a + b], 'rhs': 2}, [a, b, a + b], 2))
    for pid in sorted(registry['patterns']):
        pat = registry['patterns'][pid]
        for phi in copies(pat['k'], pat['relations'], E):
            if max_rows is not None and len(out) >= max_rows:
                return out
            out.append(({'kind': 'pattern', 'pattern': pid, 'map': phi, 'rhs': pat['ex']}, phi, pat['ex']))
    return out


def separate(task, R, *, rounds=30, per_round=400, stop=None):
    """Root cutting planes (as B20_R47's separation for C4): start from the Schur and double rows, then repeatedly
    add the pattern rows the current LP solution violates most (at most `per_round` a round) until none is violated,
    `rounds` rounds have run, or `stop()` says so. Returns (working rows, rounds run, violated left)."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix
    E = task['elements']
    idx = {x: i for i, x in enumerate(E)}
    W = [r for r in R if r[0]['kind'] != 'pattern']
    pool = [r for r in R if r[0]['kind'] == 'pattern']
    cols = [[idx[x] for x in r[1]] for r in pool]
    used = set()
    k = 0
    for k in range(1, rounds + 1):
        data, ri, ci = [], [], []
        for j, r in enumerate(W):
            for x in r[1]:
                data.append(1.0); ri.append(j); ci.append(idx[x])
        A = csr_matrix((data, (ri, ci)), shape=(len(W), len(E)))
        res = linprog(-np.ones(len(E)), A_ub=A, b_ub=np.array([r[2] for r in W], float), bounds=(0, 1),
                      method='highs')
        x = res.x
        viol = sorted(((sum(x[i] for i in cols[j]) - pool[j][2], j) for j in range(len(pool)) if j not in used),
                      reverse=True)
        viol = [(v, j) for v, j in viol if v > 1e-6][:per_round]
        if not viol:
            return W, k, 0
        for _, j in viol:
            used.add(j)
            W.append(pool[j])
        if stop is not None and stop():
            break
    left = 0
    return W, k, left


def node_lp(R, idx_rows, n, F0, F1, *, max_denominator=10 ** 6):
    """As generated_bnb_c4.node_lp, over host elements: ('infeasible', row) or ('dual', objective, leaf, x)."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix
    free = [i for i in range(n) if i not in F0 and i not in F1]
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
    ineq, obj = [], Fraction(0)
    for k, j in enumerate(keep):
        if y[k]:
            for i in idx_rows[j]:
                if i in pos:
                    cover[pos[i]] += y[k]
            obj += y[k] * rhs[k]
            ineq.append(dict(R[j][0], weight=str(y[k])))
    slack = []
    for k, i in enumerate(free):
        if cover[k] < 1:
            s = 1 - cover[k]
            obj += s
            slack.append((i, s))
    return ('dual', obj, {'kind': 'dual', 'inequalities': ineq, 'slack': slack},
            {free[k]: float(v) for k, v in enumerate(xs)})


def certify_with_tree(task, witness, registry, *, seconds=60, max_rows=None, max_denominator=10 ** 6,
                      separation=None):
    """{'lower', 'upper', 'method', 'steps', 'wall_s', 'certificate', 'witness', 'nodes', 'leaves', 'rows'}; the
    optimum is certified iff lower == upper. Time includes row generation. With `separation` (a dict of
    `separate` options) the tree uses the root cutting-plane working set instead of every row."""
    start = time.monotonic()
    E = list(task['elements'])
    idx = {x: i for i, x in enumerate(E)}
    lower = VT.check_witness(task, list(witness))
    best = sorted(witness)
    steps = []
    R = rows(task, registry, max_rows=max_rows)
    if separation is not None and registry['patterns']:
        R, k, _ = separate(task, R, **separation)
        steps.append({'step': 'separation', 'rounds': k, 'rows': len(R), 'wall_s': round(time.monotonic() - start, 3)})
    idx_rows = [[idx[x] for x in els] for _, els, _ in R]
    steps.append({'step': 'rows', 'rows': len(R), 'pattern_rows': sum(r[0]['kind'] == 'pattern' for r in R),
                  'wall_s': round(time.monotonic() - start, 3)})

    def leaf_json(leaf):
        return {'kind': 'dual', 'inequalities': leaf['inequalities'],
                'slack': [[E[i], str(s)] for i, s in leaf['slack']]}

    base = {'schema': VT.SCHEMA, 'task_sha256': digest(task), 'domain': VT.DOMAIN, 'registry_sha256': digest(registry)}
    root = node_lp(R, idx_rows, len(E), frozenset(), frozenset(), max_denominator=max_denominator)
    root_bound = math.floor(root[1])
    root_leaf = leaf_json(root[2])
    steps.append({'step': 'root-lp', 'bound': root_bound, 'wall_s': round(time.monotonic() - start, 3)})

    def finish(upper, method, tree, nodes, leaves, timed_out):
        cert = dict(base, upper=upper, tree=tree) if tree is not None else None
        steps.append({'step': 'branch-and-bound', 'nodes': nodes, 'leaves': leaves, 'timed_out': timed_out,
                      'wall_s': round(time.monotonic() - start, 3)})
        return {'lower': lower, 'upper': upper, 'method': method, 'steps': steps, 'witness': best,
                'wall_s': round(time.monotonic() - start, 3), 'certificate': cert, 'nodes': nodes, 'leaves': leaves,
                'rows': len(R)}

    if root_bound <= lower:
        return finish(max(root_bound, lower), METHOD_ROOT, {'leaf': root_leaf}, 1, 1, False)
    tree = {}
    stack = [(tree, frozenset(), frozenset(), root)]
    nodes = leaves = 0
    while stack:
        if time.monotonic() - start > seconds:
            return finish(max(root_bound, lower), METHOD_ROOT if root_bound < len(E) else METHOD_NONE,
                          {'leaf': root_leaf}, nodes, leaves, True)
        node, F0, F1, res = stack.pop()
        if res is None:
            res = node_lp(R, idx_rows, len(E), F0, F1, max_denominator=max_denominator)
        nodes += 1
        if res[0] == 'infeasible':
            node['leaf'] = {'kind': 'infeasible', 'row': R[res[1]][0]}
            leaves += 1
            continue
        _, obj, leaf, x = res
        if len(F1) + math.floor(obj) <= lower:
            node['leaf'] = leaf_json(leaf)
            leaves += 1
            continue
        frac = {i: v for i, v in x.items() if 1e-6 < v < 1 - 1e-6}
        if not frac:
            sel = sorted([E[i] for i in F1] + [E[i] for i, v in x.items() if v > 0.5])
            try:
                val = VT.check_witness(task, sel)
            except ValueError:                        # cannot happen with every Schur row present; never trusted
                val = -1
            if val > lower:
                lower, best = val, sel
                stack.append((node, F0, F1, res))
                nodes -= 1
                continue
            frac = x
            if not frac:
                raise RuntimeError('a node with no free elements was neither closed nor improving')
        b = max(frac, key=lambda i: (-abs(frac[i] - 0.5), -i))
        node['branch'] = E[b]
        node['zero'], node['one'] = {}, {}
        stack.append((node['zero'], F0 | {b}, F1, None))
        stack.append((node['one'], F0, F1 | {b}, None))
    return finish(lower, METHOD_TREE, tree, nodes, leaves, False)


def mip(task, *, seconds=60):
    """Descriptive only: HiGHS MILP over the Schur rows (untrusted; its incumbent is re-checked). Returns
    {'value', 'optimal', 'wall_s'}."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import csr_matrix
    t0 = time.monotonic()
    E = task['elements']
    idx = {x: i for i, x in enumerate(E)}
    R = rows(task, {'patterns': {}})
    if not R:
        return {'value': len(E), 'optimal': True, 'wall_s': 0.0, 'witness': list(E)}
    data, ri, ci = [], [], []
    for j, (_, els, _) in enumerate(R):
        for x in els:
            data.append(1.0); ri.append(j); ci.append(idx[x])
    A = csr_matrix((data, (ri, ci)), shape=(len(R), len(E)))
    r = milp(-np.ones(len(E)), constraints=LinearConstraint(A, -np.inf, [rr[2] for rr in R]),
             integrality=np.ones(len(E)), bounds=Bounds(0, 1), options={'time_limit': seconds})
    wit = [E[i] for i in range(len(E)) if r.x is not None and r.x[i] > 0.5]
    val = VT.check_witness(task, wit) if r.x is not None else 0
    return {'value': val, 'optimal': r.status == 0, 'wall_s': round(time.monotonic() - t0, 3), 'witness': wit}


__all__ = ['certify_with_tree', 'node_lp', 'rows', 'copies', 'load_registry', 'empty_registry', 'mip', 'PACKAGE',
           'METHOD_TREE', 'METHOD_ROOT']
