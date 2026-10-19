"""Candidate kind `mqlib-v1` (registry v2, B20_R74): MQLib's BURER2002, the best single max-cut heuristic in the
largest independent comparison of max-cut/QUBO heuristics, as a state-of-the-art domain baseline.

Why. Dunning, Gupta and Silberholz (INFORMS J. Computing 2018) implemented 37 max-cut and QUBO heuristics in one
open-source library (MQLib), ran them under identical termination criteria on 3,296 instances, and found BURER2002
(the rank-two relaxation heuristic of Burer, Monteiro and Zhang, 2002) the best single heuristic: it matched the
best result on 22.9% of instances, more than any other. A claim against "the best known methods" needs it.

Use. On dense hosts a maximum cut is close to the largest triangle-free subgraph. The child passes the host to MQLib as
an unweighted max-cut instance (MQLib's file format, through a pipe: the child may not write files), runs MQLib's BURER2002 for the budget, reads the best cut it
prints, and completes it greedily to a triangle-free subgraph exactly as E1's candidate and the other max-cut kinds
complete theirs (the other edges in random order, each added if it closes no triangle). The domain checker
re-checks the witness; the claimed value is never trusted.

The binary. MQLib is C++ and has no wheel for this Python; it is built from source at a pinned commit by
`scripts/b20r74_sota_tools.py` (compiler, flags and source order fixed) and installed at BINARY, inside /usr (the
runc sandbox bind-mounts the host's /usr read-only) and outside every Python path. BINARY_SHA256 pins it:
`check_parameters` refuses unless the installed binary hashes to it, and this file, which holds the pin, is in the
kind's identity.

Parameters (data only): {heuristic, cpu_seconds}; heuristic in HEURISTICS. Domain: triangle_free_host_v1.
"""
import hashlib
import os
from pathlib import Path
import random
import subprocess
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/mqlib.py',)
BINARY = '/usr/local/genesis-sota/bin/MQLib'
BINARY_SHA256 = '9e760cb75ab9a989a6a714bb0a357ce591e50bbd80ac1100fac253f7913ec4e3'   # two clean builds agree
SOURCE = {'repository': 'https://github.com/MQLib/MQLib', 'commit': '585496274af5abb0849d0d47e135496b4688680b',
          'compiler': 'g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0',
          'command': 'cd <tmp>; g++ -IMQLib/include -std=c++11 -O2 -w -ffile-prefix-map=<tmp>=. -o MQLib.bin '
                     '<every MQLib/src/**/*.cpp, relative, sorted> -lm'}
HEURISTICS = ('BURER2002',)
_PIN = {}


def binary_digest(path=BINARY):
    if path not in _PIN:
        p = Path(path)
        _PIN[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _PIN[path]


def check_parameters(domain, params):
    """None, or the reason the parameters are refused (including an unpinned or changed binary)."""
    if domain not in DOMAINS:
        return f'mqlib-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'heuristic', 'cpu_seconds'}:
        return 'mqlib-v1 takes {heuristic, cpu_seconds}'
    if params['heuristic'] not in HEURISTICS:
        return f'heuristic must be one of {HEURISTICS}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    got = binary_digest()
    if got != BINARY_SHA256:
        return f'the MQLib binary at {BINARY} is missing or not the pinned one ({got} != {BINARY_SHA256})'
    return None


def parse_cut(stdout, n):
    """The ±1 vector printed after 'Solution:' as a side list, or None."""
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == 'Solution:' and i + 1 < len(lines):
            vals = lines[i + 1].split()
            if len(vals) == n and all(v in ('1', '-1') for v in vals):
                return [1 if v == '1' else 0 for v in vals]
    return None


def complete(E, n, side, rng):
    nb = [set() for _ in range(n)]
    chosen, rest = [], []
    for u, v in E:
        if side[u] != side[v]:
            chosen.append((u, v)); nb[u].add(v); nb[v].add(u)
        else:
            rest.append((u, v))
    rng.shuffle(rest)
    for u, v in rest:
        if not (nb[u] & nb[v]):
            chosen.append((u, v)); nb[u].add(v); nb[v].add(u)
    return chosen


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    n = view.n
    E = [tuple(e) for e in view.edges]
    if not E:
        return {'selected': [], 'value': 0}
    budget = max(0.01, min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start))
    # the child may not write files (RLIMIT_FSIZE 0), so the instance goes to MQLib through a pipe
    instance = f'{n} {len(E)}\n' + ''.join(f'{u + 1} {v + 1} 1\n' for u, v in E)
    p = subprocess.run([BINARY, '-fM', '/proc/self/fd/0', '-h', params['heuristic'], '-r', f'{budget:.4f}', '-ps',
                        '-s', str(seed % (1 << 31))], input=instance, capture_output=True, text=True,
                       timeout=budget + 5)
    side = parse_cut(p.stdout, n) if p.returncode == 0 else None
    if side is None:
        return {'selected': [], 'value': 0}
    best = complete(E, n, side, random.Random(seed))
    return {'selected': [list(e) for e in sorted(best)], 'value': len(best)}
