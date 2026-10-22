"""Candidate kind `cpsat-v1` (registry v2, B20_R76): Google OR-Tools CP-SAT, a state-of-the-art exact solver, as a
strong baseline.

Why. A speed or quality claim needs the best *known* methods, not a chosen one (Rønnow et al. 2014;
docs/PHYSICS_INSPIRED_PLAN.md idea 1). CP-SAT won gold in the fixed, free and parallel categories of the MiniZinc
Challenge 2025, the main competition for constraint solvers. HiGHS, E1d's exact comparator, is a good open MILP
solver but not the strongest available.

Model (fixed): one Boolean per host edge; for every host triangle {a, b, c}, x_ab + x_bc + x_ac <= 2; maximize
the number of chosen edges. CP-SAT is built as a portfolio of search workers (large neighbourhood search, feasibility
jump, core-based search and others) that normally run in parallel. The child pins itself to one CPU and runs
WORKERS = 8 workers on it, so the portfolio shares that one core and the CPU it uses equals the budget, as for the single-threaded arms. (A
disclosed look on two B20_R66 hosts, B20_R76 record: one worker reached 223 and 227 edges in 2 s, eight workers on
one core 245 and 266.) The time limit is the remaining budget, starting after the library import; it returns its
best solution at the limit (proved optimal or not). The domain checker re-checks the witness; the claimed value is never trusted.

The library. CP-SAT is not in the locked environment (requirements.lock) and is not added to it. PyPI is not
reachable from this workspace (B20R74-OPEN-1), so Daniel supplied the official wheel (19 Oct 2026); it is installed
without dependencies (`scripts/b20r74_sota_tools.py --ortools-wheel`, which checks the wheel's SHA-256 first) as a
pinned tree under SOTA_DIR inside /usr (so the runc sandbox, which bind-mounts the
host's /usr read-only, sees it) and outside every site directory (so the lock check and every other code path never
import it). SOTA_TREE_SHA256 pins that tree's library files (B20_R98: not pip's install-time metadata, which records
the folder the wheel was installed from): `check_parameters` refuses to build or accept a descriptor unless the
installed tree hashes to it, and this file, which holds the pin, is in the kind's identity. So a changed library
changes nothing silently: the kind is refused until the pin is updated, which changes its identity.

Dependencies. OR-Tools 9.15 declares protobuf >= 6.33.1, < 6.34; the system has protobuf 7.36.1, which the tree
uses (CP-SAT's solver is C++ with its own protobuf; the Python side only builds the model). Model building and
solving were tested with it (`tests_genesis/test_cpsat_kind.py`); the mismatch is recorded, not hidden.

Parameters (data only): {cpu_seconds}. Domain: triangle_free_host_v1.
"""
import hashlib
import os
from pathlib import Path
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/cpsat.py',)
SOTA_DIR = '/usr/local/genesis-sota/py313'
SOTA_PACKAGES = {'ortools': '9.15.6755'}       # installed with --no-deps from the wheel below (B20_R76)
WHEELS = {'ortools-9.15.6755-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl':
          'ebd5aea00374e3aad7a78de59058aca5e871a26a3c385cd0860ef1d685d03c9a'}   # supplied by Daniel from pypi.org
# The library files of the installed tree (B20_R98). B20_R76's pin (fb5ef9ac...67f9) also covered pip's install-time
# metadata, which records the folder the wheel was installed from, so it held only for that folder.
SOTA_TREE_SHA256 = '2010e03a3a3561dcfa4f0f15f4de1ca16b6321e6136fca94bdf192a9f087e47a'
WORKERS = 8
# Written by pip into *.dist-info at install time: direct_url.json holds the wheel's absolute path and RECORD lists
# it, so they differ between two installs of the same wheel. The pin leaves them out (and is then a function of the
# wheel alone: `wheel_digest`).
INSTALL_METADATA = ('INSTALLER', 'RECORD', 'REQUESTED', 'direct_url.json')
_DIGEST = {}


def _pinned(parts):
    """Whether a file of the tree (its relative path's parts) counts in the pin: not bytecode, not pip's metadata."""
    return ('__pycache__' not in parts and not parts[-1].endswith('.pyc')
            and not (len(parts) == 2 and parts[0].endswith('.dist-info') and parts[1] in INSTALL_METADATA))


def _digest(pairs):
    h = hashlib.sha256()
    for parts, file_sha in sorted(pairs):
        h.update('/'.join(parts).encode() + b'\0' + file_sha)
    return h.hexdigest()


def wheel_digest(wheel):
    """The pin computed from the wheel's own members: the digest a --no-deps install of this wheel must give."""
    import zipfile
    with zipfile.ZipFile(wheel) as z:
        return _digest([(tuple(i.filename.split('/')), hashlib.sha256(z.read(i)).digest()) for i in z.infolist()
                        if not i.is_dir() and _pinned(tuple(i.filename.split('/')))])


def tree_digest(root=SOTA_DIR):
    """SHA-256 over the sorted (relative path, file SHA-256) pairs of the installed tree's library files (bytecode
    caches and pip's install-time metadata left out)."""
    if root in _DIGEST:
        return _DIGEST[root]
    base = Path(root)
    if not base.is_dir():
        _DIGEST[root] = None
        return None
    _DIGEST[root] = _digest([(p.relative_to(base).parts, hashlib.sha256(p.read_bytes()).digest())
                             for p in base.rglob('*') if p.is_file() and _pinned(p.relative_to(base).parts)])
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
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    import sys
    if SOTA_DIR not in sys.path:
        sys.path.insert(0, SOTA_DIR)
    from ortools.sat.python import cp_model
    start = time.process_time()                 # the budget starts after the library import, as for the other arms
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
    s.parameters.num_workers = WORKERS
    s.parameters.random_seed = seed % (1 << 31)
    status = s.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {'selected': [], 'value': 0}
    sel = [list(e) for e in E if s.Value(x[e])]
    return {'selected': sel, 'value': len(sel)}
