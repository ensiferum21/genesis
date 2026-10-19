"""Candidate kind `cpsat-v1` (registry v2, B20_R74): Google OR-Tools CP-SAT, a state-of-the-art exact solver, as a
strong baseline.

Why. A speed or quality claim needs the best *known* methods, not a chosen one (Rønnow et al. 2014;
docs/PHYSICS_INSPIRED_PLAN.md idea 1). CP-SAT won gold in the fixed, free and parallel categories of the MiniZinc
Challenge 2025, the main competition for constraint solvers. HiGHS, E1d's exact comparator, is a good open MILP
solver but not the strongest available.

Model (fixed): one Boolean per host edge; for every host triangle {a, b, c}, x_ab + x_bc + x_ac <= 2; maximize
the number of chosen edges. The solver runs with one search worker, the child pinned to one CPU, and a time limit
equal to the remaining budget, so it is comparable with the single-threaded arms; it returns its best solution at
the limit (proved optimal or not). The domain checker re-checks the witness; the claimed value is never trusted.

The library. CP-SAT is not in the locked environment (requirements.lock) and is not added to it. It is installed,
with its own dependencies, as a pinned tree under SOTA_DIR inside /usr (so the runc sandbox, which bind-mounts the
host's /usr read-only, sees it) and outside every site directory (so the lock check and every other code path never
import it). SOTA_TREE_SHA256 pins that tree: `check_parameters` refuses to build or accept a descriptor unless the
installed tree hashes to it, and this file, which holds the pin, is in the kind's identity. So a changed library
changes nothing silently: the kind is refused until the pin is updated, which changes its identity.

Parameters (data only): {cpu_seconds}. Domain: triangle_free_host_v1.
"""
import hashlib
import os
from pathlib import Path
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/cpsat.py',)
SOTA_DIR = '/usr/local/genesis-sota/py313'
SOTA_PACKAGES = {'ortools': '9.12.4544'}       # the versions installed and pinned (B20_R74)
SOTA_TREE_SHA256 = 'PENDING'                   # set when the tree is installed; see tree_digest()
_DIGEST = {}


def tree_digest(root=SOTA_DIR):
    """SHA-256 over the sorted (relative path, file SHA-256) pairs of the installed tree, ignoring bytecode caches."""
    if root in _DIGEST:
        return _DIGEST[root]
    base = Path(root)
    if not base.is_dir():
        _DIGEST[root] = None
        return None
    h = hashlib.sha256()
    for p in sorted(base.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            h.update(str(p.relative_to(base)).encode() + b'\0' + hashlib.sha256(p.read_bytes()).digest())
    _DIGEST[root] = h.hexdigest()
    return _DIGEST[root]


def check_parameters(domain, params):
    """None, or the reason the parameters are refused (including an unpinned or changed library)."""
    if domain not in DOMAINS:
        return f'cpsat-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'cpsat-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    got = tree_digest()
    if got is None or got != SOTA_TREE_SHA256:
        return f'the CP-SAT tree at {SOTA_DIR} is missing or not the pinned one ({got} != {SOTA_TREE_SHA256})'
    return None


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    import sys
    if SOTA_DIR not in sys.path:
        sys.path.insert(0, SOTA_DIR)
    from ortools.sat.python import cp_model
    E = [tuple(e) for e in view.edges]
    if not E:
        return {'selected': [], 'value': 0}
    adj = {}
    for u, v in E:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    m = cp_model.CpModel()
    x = {e: m.NewBoolVar(f'x{e[0]}_{e[1]}') for e in E}
    for u, v in E:
        for w in sorted(adj[u] & adj[v]):
            if w > v:
                m.Add(x[(u, v)] + x[(v, w)] + x[(u, w)] <= 2)
    m.Maximize(sum(x.values()))
    s = cp_model.CpSolver()
    budget = min(params['cpu_seconds'], cpu_seconds)
    s.parameters.max_time_in_seconds = max(0.01, budget - (time.process_time() - start))
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed % (1 << 31)
    status = s.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {'selected': [], 'value': 0}
    sel = [list(e) for e in E if s.Value(x[e])]
    return {'selected': sel, 'value': len(sel)}
