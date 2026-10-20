"""Candidate kind `tfx-v1` (registry v2, B20_R88): a native population search on the triangle-free problem itself,
with operators from physics (simulated bifurcation, mean-field annealing, parallel tempering), biology (crossover,
ant-colony memory) and the independent-set literature ((1,2)-swaps, path relinking, restarts), chosen by data.

Why. B20_R87 built the strongest anytime MaxSAT solvers. In B20_R88's development looks on B20_R76's hosts the best of
them at short budgets was DeepDist, a clause-weighting local search, and B20_R77's engine (Python) was already
faster than it at 0.05-0.25 s but slower than it needed to be: most of its time went to the interpreter. This kind is
that engine's idea (cut warm starts, then (1,2)-swap iterated local search on edge sets) rewritten in C over 64-bit
vertex bitsets, with further operators that a configuration search may switch on (B20_R89). The algorithm and every
operator are described in the source, `candidate_kinds/native/tfx.c`.

Binary. Built from that source by `scripts/b20r88_build_tfx.py` (gcc 13.3, `-O3 -std=gnu11 -static`, deterministic:
the same source gives the same bytes), installed as /usr/local/genesis-sota/bin/tfx (inside /usr, which the runc
sandbox sees read-only), pinned here by SHA-256, refused if missing or different. Both the source and this module are
the kind's files, so either changing changes the kind's identity.

Parameters (data only): {cpu_seconds, config}; config must give every key of SPACE a value from its list. DEFAULT
is the builder's first design. Run: the host goes to the binary on stdin with the seed and the remaining budget in
ms; the binary stops itself at that CPU time (a 5 s wall-clock guard kills it otherwise). The best edge set is
decoded and re-checked here (triangle-free, a subset of the host); the domain checker re-checks it again.
Domain: triangle_free_host_v1 (n <= 64, the task model's maximum is 63).
"""
import hashlib
import os
from pathlib import Path
import subprocess
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/tfx.py', 'candidate_kinds/native/tfx.c')
BINARY = '/usr/local/genesis-sota/bin/tfx'
BINARY_SHA256 = '1b0f7733b631b4b7d49fdb162911e04eb64c29d0c23d93e58ee4a2a0a640f386'
SPACE = {
    'ws': (1, 2, 3, 4, 5, 6, 7),
    'frac': (0.05, 0.1, 0.2, 0.3, 0.5),
    'K': (2, 4, 6, 8, 12, 16),
    'kicks': (1, 2, 3),
    'acc': (0, 1),
    'pw': (0.0, 0.05, 0.1, 0.2, 0.3),
    'tmin': (0.2, 0.3, 0.5),
    'tmax': (1.0, 2.0, 4.0),
    'xchg': (20, 50, 200),
    'cross': (0, 5, 20, 50),
    'rho': (0.0, 0.1, 0.3),
    'pherw': (0.0, 2.0, 4.0),
    'restart': (0, 50, 200, 1000),
    'relink': (0, 10, 20, 50),
    'repl': (8, 16, 32),
    'steps': (100, 200, 400),
    'dshare': (0.25, 0.5, 0.75),
    'femlr': (0.0, 0.1, 0.3),
    'femsteps': (100, 300),
    'femlam': (1.2, 1.5, 2.0),
}
DEFAULT = {'ws': 3, 'frac': 0.3, 'K': 4, 'kicks': 1, 'acc': 0, 'pw': 0.1, 'tmin': 0.3, 'tmax': 2.0, 'xchg': 50,
           'cross': 0, 'rho': 0.0, 'pherw': 0.0, 'restart': 0, 'relink': 0, 'repl': 32, 'steps': 400,
           'dshare': 0.5, 'femlr': 0.0, 'femsteps': 300, 'femlam': 1.5}
_DIGEST = {}


def binary_digest(path=None):
    path = path or BINARY
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _DIGEST[path]


def check_config(config):
    """None, or the reason a configuration is refused."""
    if not isinstance(config, dict) or set(config) != set(SPACE):
        return f'config must give exactly the keys {sorted(SPACE)}'
    for k, allowed in SPACE.items():
        v = config[k]
        if isinstance(v, bool) or type(v) not in (int, float) or v not in allowed:
            return f'config[{k!r}] must be one of {allowed}'
    return None


def check_parameters(domain, params):
    """None, or the reason the parameters are refused (including a missing or unpinned binary)."""
    if domain not in DOMAINS:
        return f'tfx-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds', 'config'}:
        return 'tfx-v1 takes {cpu_seconds, config}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    why = check_config(params['config'])
    if why:
        return why
    got = binary_digest()
    if got != BINARY_SHA256:
        return f'{BINARY} is missing or not the pinned build ({got} != {BINARY_SHA256})'
    return None


def arguments(config):
    return [f'{k}={config[k]}' for k in sorted(config)]


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    n = view.n
    E = [tuple(e) for e in view.edges]
    if not E or n < 2:
        return {'selected': [list(e) for e in E], 'value': len(E)}
    budget = max(0.001, min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start))
    text = f'{n} {len(E)} {int(seed) % (1 << 62)} {budget * 1000:.3f}\n' + ''.join(f'{u} {v}\n' for u, v in E)
    try:
        r = subprocess.run([BINARY, *arguments(params['config'])], input=text, capture_output=True, text=True,
                           timeout=budget + 5)
    except subprocess.TimeoutExpired:
        raise RuntimeError('tfx did not stop at its budget')
    lines = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 + len(E) or set(lines[0][2:]) - {'0', '1'}:
        raise RuntimeError(f'tfx failed (exit {r.returncode}): {(r.stdout + r.stderr)[-300:]}')
    chosen = [E[i] for i, b in enumerate(lines[0][2:]) if b == '1']
    nb = [0] * n
    for u, v in chosen:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    for u, v in chosen:
        if nb[u] & nb[v]:
            raise RuntimeError('tfx returned an edge set with a triangle')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
