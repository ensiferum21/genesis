"""Candidate kind `milp-highs-v1` (registry v2, B20_R40): an exact MILP solver as a time-matched
baseline.

It solves the largest triangle-free subgraph problem exactly: max Σ x_e s.t. x(T) ≤ 2 for every
host triangle T, x ∈ {0,1}. The solver is HiGHS through `scipy.optimize.milp`, with scipy pinned
in requirements.lock, and it returns the best incumbent at the time limit. This is the
"strong baseline" of B20_R33, B20_R34 and B20_R38, packaged so that a custodian's runner could run
it like any other comparator. The domain checker re-checks the witness, and the claimed value is
never trusted.

Fairness. The child pins itself to one CPU before importing scipy, so HiGHS's worker threads
share that core and the cgroup CPU meter stays comparable with single-threaded arms. The time
limit is `cpu_seconds` minus the time already used. The runner's cgroup accounting still meters
the whole child.

Parameters (data only): {cpu_seconds}. Domains: triangle_free_host_v1.
"""
import os
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/milp_highs.py',)


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    if domain not in DOMAINS:
        return f'milp-highs-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'milp-highs-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    return None


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    E = [tuple(e) for e in view.edges]
    idx = {e: i for i, e in enumerate(E)}
    adj = {}
    for u, v in E:
        adj.setdefault(u, set()).add(v); adj.setdefault(v, set()).add(u)
    T = [((u, v), (v, w), (u, w)) for u, v in sorted(E) for w in sorted(adj[u] & adj[v]) if w > v]
    if not E:
        return {'selected': [], 'value': 0}
    if not T:
        return {'selected': [list(e) for e in E], 'value': len(E)}
    A = lil_matrix((len(T), len(E)))
    for j, t in enumerate(T):
        for e in t:
            A[j, idx[e]] = 1
    budget = min(params['cpu_seconds'], cpu_seconds)
    left = max(0.05, budget - (time.process_time() - start))
    res = milp(-np.ones(len(E)), constraints=LinearConstraint(A.tocsr(), -np.inf, 2), integrality=np.ones(len(E)),
               bounds=Bounds(0, 1), options={'time_limit': left})
    if res.x is None:
        return {'selected': [], 'value': 0}
    sel = [list(E[i]) for i in range(len(E)) if res.x[i] > 0.5]
    return {'selected': sel, 'value': len(sel)}
