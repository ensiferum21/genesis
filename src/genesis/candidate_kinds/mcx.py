"""Candidate kind `mcx-v1` (max-cut runner, B20_R104): Genesis's own weighted max-cut engine.

Why. `docs/OPEN_RECORDS_PLAN.md`: on the public Gset benchmark Genesis needs a solver of its own that can stand
against the published methods (B20_R102 measures where those stand); the triangle-free engines (`tfx`, `tfxw`) search
edge sets, not cuts.

Algorithm (`native/mcx.c`; fixed, the configuration is data). An iterated tabu search in the spirit of breakout local
search (Benlic and Hao 2013):
  * incremental flip gains in bucket lists; steepest ascent to a local optimum;
  * a perturbation whose strength adapts (it grows on returning to the same local optimum, resets after a new one);
    directed (best non-tabu moves, random tenure up to n / tt) with a probability falling from 1 to P as the search
    stalls; otherwise random flips (pert 0) or, half the time, recency-based flips (pert 1); pert 2 follows
    breakout local search's own rules as read from the authors' paper (Benlic and Hao 2013, Algorithms 1-3 and
    formula (2), Daniel's PDF of 23 Oct 2026): P = max(exp(-w / 1000), P), directed single flips or directed pairs
    (the best non-tabu vertex of each side) in equal shares, else random flips, one strong random perturbation after
    1000 local optima without a new best, and descent moves made tabu;
  * an elite pool of `pool` distinct local optima and, after `restart` attractors without a new best, a restart (rs):
    0 none; 1 a cluster exchange of two elites (Houdayer's move from spin-glass physics: whole domains of
    disagreement are swapped at once); 2 renormalisation: every edge whose relative orientation all elites agree on
    is contracted, the contracted weighted max-cut problem on the clusters is searched by the same method, and the
    result is projected back and polished (a coarse-graining step: keep what the elites agree on, search the rest);
    3 the multi-parent grouping crossover of the memetic algorithm MACUT (Wu and Hao, PPSN 2012, read from the
    authors' paper, Daniel's PDF of 23 Oct 2026): 2-4 elites, vertices grouped by their pattern of sides, the two
    largest groups kept whole on opposite sides, the rest random.
Not new ideas: tabu search, breakout perturbation, elite pools, cluster moves and multilevel coarsening are published;
the builder combined them. Invention by the system is not claimed for this kind.

DEFAULT is breakout local search's published setting in this engine (L0 = 0.01 n, P0 = 0.8, tenure 3 + up to n / 10,
pert 2, no restarts: rs 0; T = 1000 and Q = 0.5 are fixed in the source): the published method as adapted here, our
implementation, not the authors' code. Every other configuration adds or changes something.

Binary. Built from the in-repository source by `scripts/b20r104_build_mcx.py` (gcc 13.3, `-O3 -std=gnu11 -static`,
deterministic), installed as BINARY, pinned by SHA-256, refused if missing or different. Instances with a weighted
degree above 2^24 are refused by the binary (exit 3; the run fails, it is not hidden). The cut it prints is recomputed
here, and the domain's two checkers re-check it.

Parameters (data only): {cpu_seconds, config}; config gives every key of SPACE a value from its list.
Domain: maxcut_v1.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import time

DOMAINS = ('maxcut_v1',)
FILES = ('candidate_kinds/mcx.py', 'candidate_kinds/native/mcx.c')
BINARY = '/usr/local/genesis-sota/bin/mcx'
BINARY_SHA256 = '10825596bdb7a0a531ea45f147f956fafee4646ed656b13ba1e38d508c930978'
SPACE = {'L0': (0.005, 0.01, 0.02, 0.05), 'P': (0.5, 0.75, 0.8, 0.9), 'tt': (5, 10, 20), 'pool': (4, 8, 16),
         'restart': (2000, 20000, 200000), 'rs': (0, 1, 2, 3), 'pert': (0, 1, 2)}
DEFAULT = {'L0': 0.01, 'P': 0.8, 'tt': 10, 'pool': 8, 'restart': 2000, 'rs': 0, 'pert': 2}
_DIGEST = {}


def check_config(config):
    if not isinstance(config, dict) or set(config) != set(SPACE):
        return f'config must give exactly the keys {sorted(SPACE)}'
    for k, allowed in SPACE.items():
        v = config[k]
        if isinstance(v, bool) or type(v) not in (int, float) or v not in allowed:
            return f'config[{k!r}] must be one of {allowed}'
    return None


def binary_digest(path=None):
    path = path or BINARY
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _DIGEST[path]


def check_parameters(domain, params):
    if domain not in DOMAINS:
        return f'mcx-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds', 'config'}:
        return 'mcx-v1 takes {cpu_seconds, config}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 600:
        return 'cpu_seconds must be in (0, 600]'
    why = check_config(params['config'])
    if why:
        return why
    got = binary_digest()
    if got != BINARY_SHA256:
        return f'{BINARY} is missing or not the pinned build ({got} != {BINARY_SHA256})'
    return None


def arguments(config):
    return ['-L0', repr(float(config['L0'])), '-P', repr(float(config['P'])), '-tt', str(int(config['tt'])),
            '-pool', str(int(config['pool'])), '-restart', str(int(config['restart'])), '-rs', str(int(config['rs'])),
            '-pert', str(int(config['pert']))]


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
    budget = max(0.001, min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start))
    text = f'{n} {len(E)} {int(seed) % (1 << 62)} {budget * 1000:.3f}\n' + ''.join(f'{u} {v} {w}\n' for u, v, w in E)
    try:
        r = subprocess.run([BINARY, *arguments(params['config'])], input=text, capture_output=True, text=True,
                           timeout=budget + 10)
    except subprocess.TimeoutExpired:
        raise RuntimeError('mcx did not stop at its budget')
    lines = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 + n or set(lines[0][2:]) - {'0', '1'}:
        raise RuntimeError(f'mcx failed (exit {r.returncode}): {(r.stdout + r.stderr)[-300:]}')
    side = lines[0][2:]
    return {'side': side, 'value': sum(w for u, v, w in E if side[u] != side[v])}
