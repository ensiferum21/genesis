"""Candidate kind `mqlib-maxcut-v1` (max-cut runner, B20_R101): MQLib's heuristics on weighted max-cut.

Why. MQLib (Dunning, Gupta and Silberholz, INFORMS J. Computing 2018) implements 37 max-cut and QUBO heuristics under
one termination rule; its best single heuristic, BURER2002 (Burer, Monteiro and Zhang 2002), is the strongest
published baseline Genesis has pinned (`mqlib-v1`, B20_R74). On the max-cut domain MQLib solves the problem it was
written for: the weighted graph goes to it in its max-cut format ("n m" then "i j w", 1-based: the same as Gset's),
through a pipe (the child may not write files), and the best cut it prints is the witness. No completion step.

The binary is `mqlib-v1`'s, pinned by the same SHA-256 (built by `scripts/b20r74_sota_tools.py`); MQLib's seeds are
taken modulo 65,536 and any failure fails the run (B20_R75/R76's lessons).

Parameters (data only): {heuristic, cpu_seconds}; heuristic in HEURISTICS. Domain: maxcut_v1.
"""
import os
import subprocess
import time

from . import mqlib as MQ

DOMAINS = ('maxcut_v1',)
FILES = ('candidate_kinds/mqlib_maxcut.py', 'candidate_kinds/mqlib.py')
HEURISTICS = ('BURER2002', 'DESOUSA2013', 'DUARTE2005', 'FESTA2002G', 'FESTA2002GPR', 'FESTA2002GVNS',
              'FESTA2002GVNSPR', 'FESTA2002VNS', 'FESTA2002VNSPR', 'LAGUNA2009CE', 'LAGUNA2009HCE')   # MQLib's max-cut ones


def check_parameters(domain, params):
    if domain not in DOMAINS:
        return f'mqlib-maxcut-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'heuristic', 'cpu_seconds'}:
        return 'mqlib-maxcut-v1 takes {heuristic, cpu_seconds}'
    if params['heuristic'] not in HEURISTICS:
        return f'heuristic must be one of {HEURISTICS}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 600:
        return 'cpu_seconds must be in (0, 600]'
    got = MQ.binary_digest()
    if got != MQ.BINARY_SHA256:
        return f'the MQLib binary at {MQ.BINARY} is missing or not the pinned one ({got} != {MQ.BINARY_SHA256})'
    return None


def cut_value(edges, side):
    return sum(w for u, v, w in edges if side[u] != side[v])


def solve(view, params, cpu_seconds, seed):
    """{'side': '0101...', 'value': int} for the candidate view (n, weighted edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    n, E = view.n, [tuple(e) for e in view.edges]
    if not E:
        return {'side': '0' * n, 'value': 0}
    instance = f'{n} {len(E)}\n' + ''.join(f'{u + 1} {v + 1} {w}\n' for u, v, w in E)
    budget = max(0.01, min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start))
    p = subprocess.run([MQ.BINARY, '-fM', '/proc/self/fd/0', '-h', params['heuristic'], '-r', f'{budget:.4f}', '-ps',
                        '-s', str(seed % MQ.MAX_SEED)], input=instance, capture_output=True, text=True,
                       timeout=budget + 30)
    side = MQ.parse_cut(p.stdout, n) if p.returncode == 0 else None
    if side is None:
        raise RuntimeError(f'MQLib failed (exit {p.returncode}): {(p.stdout + p.stderr)[-300:]}')
    s = ''.join('1' if x else '0' for x in side)
    return {'side': s, 'value': cut_value(E, s)}
