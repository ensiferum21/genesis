"""Candidate kind `tfxw-v1` (registry v2, B20_R94): `tfx-v1`'s search rebuilt to scale past 64 vertices (multiword
vertex sets, per-edge tightness, work-list local search, undo logs; see `candidate_kinds/native/tfxw.c`), for the
DEV-only large domain `triangle_free_large_v1` and, for comparison with `tfx-v1`, the n <= 63 domain.

Binary. Built from that source by `scripts/b20r94_build_tfxw.py` (gcc 13.3, `-O3 -std=gnu11 -static`,
deterministic), installed as /usr/local/genesis-sota/bin/tfxw, pinned here by SHA-256, refused if missing or different.

Parameters (data only): {cpu_seconds, config}; config gives every key of `tfx.SPACE` a value from its list (the same
operators with the same meaning, so B20_R89's configuration is a valid starting point). The best edge set is decoded
and re-checked here (triangle-free, a subset of the host); the domain checker re-checks it again.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import time

from . import tfx as T

DOMAINS = ('triangle_free_large_v1', 'triangle_free_host_v1')
FILES = ('candidate_kinds/tfxw.py', 'candidate_kinds/native/tfxw.c', 'candidate_kinds/tfx.py')
BINARY = '/usr/local/genesis-sota/bin/tfxw'
BINARY_SHA256 = 'UNBUILT'
SPACE, DEFAULT = T.SPACE, T.DEFAULT
check_config = T.check_config
_DIGEST = {}


def binary_digest(path=None):
    path = path or BINARY
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _DIGEST[path]


def check_parameters(domain, params):
    if domain not in DOMAINS:
        return f'tfxw-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds', 'config'}:
        return 'tfxw-v1 takes {cpu_seconds, config}'
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
        r = subprocess.run([BINARY, *T.arguments(params['config'])], input=text, capture_output=True, text=True,
                           timeout=budget + 10)
    except subprocess.TimeoutExpired:
        raise RuntimeError('tfxw did not stop at its budget')
    lines = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 + len(E) or set(lines[0][2:]) - {'0', '1'}:
        raise RuntimeError(f'tfxw failed (exit {r.returncode}): {(r.stdout + r.stderr)[-300:]}')
    chosen = [E[i] for i, b in enumerate(lines[0][2:]) if b == '1']
    nb = [0] * n
    for u, v in chosen:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    if any(nb[u] & nb[v] for u, v in chosen):
        raise RuntimeError('tfxw returned an edge set with a triangle')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
