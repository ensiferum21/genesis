"""Candidate kind `maxsat-anytime-v1` (registry v2, B20_R87): the strongest anytime MaxSAT solvers, run on the
problem's exact MaxSAT encoding, as baselines.

Why. The largest triangle-free subgraph of a host is an unweighted partial MaxSAT problem: one Boolean per host edge,
one soft unit clause (x_e) per edge, one hard clause (not x_ab or not x_bc or not x_ac) per host triangle. That is
the problem class of the MaxSAT Evaluation's anytime track, where solvers have been tuned against each other every
year since 2018, so its best solvers are the most tuned general tools for this problem (see
`scripts/b20r87_maxsat_tools.py` for the choice and the sources).

Solvers (fixed; each a binary built from a pinned source by `scripts/b20r87_maxsat_tools.py`, under
/usr/local/genesis-sota/bin, pinned here by SHA-256, refused if missing or different):
  * `deepdist`: DeepDist (ECAI 2025; local search with deep differentiation clause weighting, built on SPB-MaxSAT).

Run. The instance, in the classic WCNF format ("p wcnf V C TOP"), is piped to the solver as /proc/self/fd/0 (the
sandbox child may not write files). The solver runs for the remaining budget (wall clock; the child is alone on a
pinned core), then receives SIGTERM, on which MaxSAT Evaluation solvers print their best assignment ("v" line). The
assignment is decoded to the chosen edges; a violated hard clause or a missing "v" line fails the run. The domain
checker re-checks the witness; the solver's reported cost is never trusted.

Parameters (data only): {solver, cpu_seconds}. Domain: triangle_free_host_v1.
"""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/maxsat.py',)
SOLVERS = {
    'deepdist': {'binary': '/usr/local/genesis-sota/bin/DeepDist',
                 'sha256': 'PIN_AFTER_BUILD', 'args': ()},
}
_DIGEST = {}


def binary_digest(path):
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _DIGEST[path]


def check_parameters(domain, params):
    """None, or the reason the parameters are refused (including a missing or unpinned binary)."""
    if domain not in DOMAINS:
        return f'maxsat-anytime-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'solver', 'cpu_seconds'}:
        return 'maxsat-anytime-v1 takes {solver, cpu_seconds}'
    if params['solver'] not in SOLVERS:
        return f'solver must be one of {sorted(SOLVERS)}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    s = SOLVERS[params['solver']]
    got = binary_digest(s['binary'])
    if got is None or got != s['sha256']:
        return f'{s["binary"]} is missing or not the pinned build ({got} != {s["sha256"]})'
    return None


def triangles(E):
    adj = {}
    for u, v in E:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    return [(u, v, w) for u, v in E for w in sorted(adj[u] & adj[v]) if w > v]


def wcnf(E):
    """The classic WCNF text: variable i+1 is edge i; hard clauses (weight TOP) forbid each triangle."""
    eid = {e: i + 1 for i, e in enumerate(E)}
    T = triangles(E)
    top = len(E) + 1
    lines = [f'p wcnf {len(E)} {len(T) + len(E)} {top}']
    lines += [f'{top} -{eid[(u, v)]} -{eid[(v, w)]} -{eid[(u, w)]} 0' for u, v, w in T]
    lines += [f'1 {i + 1} 0' for i in range(len(E))]
    return '\n'.join(lines) + '\n'


def parse_model(out, m):
    """The last "v" line as a set of true variables (1..m): a 0/1 string or a list of literals; None if absent."""
    vs = [l[2:].strip() for l in out.splitlines() if l.startswith('v ')]
    if not vs:
        return None
    body = vs[-1]
    if body and set(body) <= {'0', '1'} and ' ' not in body:
        if len(body) < m:
            return None
        return {i + 1 for i in range(m) if body[i] == '1'}
    true = set()
    for tok in ' '.join(vs).split():
        k = int(tok)
        if k > 0:
            true.add(k)
    return true


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    E = [tuple(e) for e in view.edges]
    if not E:
        return {'selected': [], 'value': 0}
    s = SOLVERS[params['solver']]
    text = wcnf(E)
    budget = max(0.01, min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start))
    p = subprocess.Popen([s['binary'], '/proc/self/fd/0', *s['args']], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(input=text, timeout=budget)
    except subprocess.TimeoutExpired:
        p.send_signal(signal.SIGTERM)
        try:
            out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
    true = parse_model(out, len(E))
    if true is None:
        raise RuntimeError(f'{params["solver"]} printed no assignment (exit {p.returncode}): {(out + err)[-300:]}')
    chosen = [E[i - 1] for i in sorted(true) if 1 <= i <= len(E)]
    picked = set(chosen)
    for u, v, w in triangles(E):
        if (u, v) in picked and (v, w) in picked and (u, w) in picked:
            raise RuntimeError(f'{params["solver"]} returned an assignment that violates a hard clause')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
