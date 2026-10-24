"""Back-ends of the Problem Compiler: run an engine on a compiled problem; the family's verifier judges the answer.

  * `genesis`: Genesis's own engine. The BQP's penalised QUBO is reduced to max-cut (`bqp.to_maxcut`), solved by
    `mcx2` (the builder's hybrid REX unless a configuration is given), decoded, repaired (`bqp.repair`) and returned.
  * `milp`: the exact linearised model (`bqp.to_milp`) solved by HiGHS through `scipy.optimize.milp` with a time
    limit, its best incumbent returned (a general-purpose solver, as `candidate_kinds/milp_highs.py`).
  * `maxsat`: a pinned MaxSAT Evaluation 2026 anytime solver (`candidate_kinds/maxsat2026.SOLVERS`) on the family's
    natural encoding (`families.wcnf`), or on the exact generic one (`bqp.to_wcnf`) when the family gives none.
Every back-end returns (x, info): an assignment of the BQP's variables and what happened (CPU, notes). Nothing a
back-end says about quality is trusted; the caller decodes and verifies with the family's own checker.
"""
import os
import signal
import subprocess
import time

from . import bqp as Q

BACKENDS = ('genesis', 'milp', 'maxsat')


def _pin():
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass


def genesis(problem, cpu_seconds, seed, config=None, penalty=None):
    from ..candidate_kinds import mcx2 as K
    from ..models_maxcut import MaxCutCandidateView
    start = time.process_time()
    P = penalty or Q.default_penalty(problem)
    qubo = Q.penalised(problem, P) if problem['hard'] else problem
    n1, E = Q.to_maxcut(qubo)
    n = problem['n']
    if not E:
        x = [0] * n
    else:
        cfg = config or K.DEFAULT
        budget = max(0.01, cpu_seconds - (time.process_time() - start))
        r = K.solve(MaxCutCandidateView(n=n1, edges=tuple((u, v, w) for u, v, w in E)),
                    {'cpu_seconds': budget, 'config': cfg}, budget, seed)
        x = Q.from_cut(r['side'], n)
    raw_bad = Q.evaluate(problem, x)[1]
    if problem['hard']:
        x = Q.repair(problem, x)
    return x, {'penalty': P, 'violations_before_repair': raw_bad, 'edges': len(E)}


def milp(problem, cpu_seconds, seed=None):
    _pin()
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp as solve
    from scipy.sparse import lil_matrix
    start = time.process_time()
    c, const, rows, nv = Q.to_milp(problem)
    cons = []
    if rows:
        A = lil_matrix((len(rows), nv))
        lo, hi = np.full(len(rows), -np.inf), np.full(len(rows), np.inf)
        for r, (coef, l, h) in enumerate(rows):
            for k, a in coef.items():
                A[r, k] = a
            if l is not None:
                lo[r] = l
            if h is not None:
                hi[r] = h
        cons = [LinearConstraint(A.tocsr(), lo, hi)]
    left = max(0.05, cpu_seconds - (time.process_time() - start))
    res = solve(np.array(c, dtype=float), constraints=cons, integrality=np.ones(nv), bounds=Bounds(0, 1),
                options={'time_limit': left, 'disp': False})
    n = problem['n']
    if res.x is None:
        return [0] * n, {'status': int(res.status), 'message': str(res.message), 'incumbent': False}
    x = [int(round(v)) for v in res.x[:n]]
    return x, {'status': int(res.status), 'message': str(res.message), 'incumbent': True,
               'bound': float(getattr(res, 'mip_dual_bound', float('nan')) or float('nan')) + const}


def maxsat(problem, cpu_seconds, seed=None, solver='nuwls-c-2026', native=None):
    """native: (hard, soft, n_vars) of the family's natural encoding over the BQP's variables 1..n first."""
    from ..candidate_kinds import maxsat as MS
    from ..candidate_kinds import maxsat2026 as M26
    _pin()
    s = M26.SOLVERS[solver]
    why = M26.check_parameters('triangle_free_host_v1', {'solver': solver, 'cpu_seconds': 1.0})
    if why:
        raise RuntimeError(why)
    start = time.process_time()
    if native is not None:
        hard, soft, nv = native
        offset = None
    else:
        hard, soft, nv, offset = Q.to_wcnf(problem)
    text = Q.wcnf_text(hard, soft, nv)
    budget = max(0.01, cpu_seconds - (time.process_time() - start))
    args = [a.format(instance='/proc/self/fd/0', seconds=M26.hint(budget)) for a in s['args']]
    p = subprocess.Popen([s['binary'], *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True)
    try:
        out, err = p.communicate(input=text, timeout=budget)
    except subprocess.TimeoutExpired:
        p.send_signal(signal.SIGTERM)
        try:
            out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
    true = MS.parse_model(out, nv)
    n = problem['n']
    if true is None:
        return [0] * n, {'model': False, 'exit': p.returncode, 'tail': (out + err)[-200:]}
    x = [1 if (i + 1) in true else 0 for i in range(n)]
    return x, {'model': True, 'solver': solver, 'offset': offset}


def run(backend, problem, cpu_seconds, seed, **kw):
    if backend == 'genesis':
        return genesis(problem, cpu_seconds, seed, **kw)
    if backend == 'milp':
        return milp(problem, cpu_seconds, seed)
    if backend == 'maxsat':
        return maxsat(problem, cpu_seconds, seed, **kw)
    raise ValueError(f'back-ends are {BACKENDS}')
