"""Candidate kind `maxsat-anytime-v1` (registry v2, B20_R87): the strongest anytime MaxSAT solvers, run on the
problem's exact MaxSAT encoding, as baselines.

Why. The largest triangle-free subgraph of a host is an unweighted partial MaxSAT problem: one Boolean per host edge,
one soft unit clause (x_e) per edge, one hard clause (not x_ab or not x_bc or not x_ac) per host triangle. That is
the problem class of the MaxSAT Evaluation's anytime track, where solvers have been tuned against each other every
year since 2018, so its best solvers are the most tuned general tools for this problem (see
`scripts/b20r87_maxsat_tools.py` for the choice and the sources).

Solvers (fixed; each a binary built from a pinned source by `scripts/b20r87_maxsat_tools.py`, under
/usr/local/genesis-sota/bin, pinned here by SHA-256 with any build stamp zeroed (B20_R98), refused if missing or
different), each run with its published configuration for unweighted instances:
  * `deepdist`: DeepDist (ECAI 2025; local search with deep differentiation clause weighting, built on SPB-MaxSAT);
  * `spb-maxsat-c-fps`: SPB-MaxSAT-c-FPS (MaxSAT Evaluation 2024 anytime winner, with SPB-MaxSAT-c-Band);
  * `nuwls-c-ibr`: NuWLS-c-IBR (MSE 2024 anytime podium; NuWLS local search inside TT-Open-WBO-Inc);
  * `tt-open-wbo-inc`: TT-Open-WBO-Inc 2024 with IntelSAT (Nadel; SAT-based anytime search, the code base of the
    recent winners);
  * `aperture`: Aperture (Nadel, Slonimski and Strichman, SOFT 2026; `-s glucose`, its unweighted configuration).

Run. The instance, in the classic WCNF format ("p wcnf V C TOP") after the comment header of the MaxSAT
Evaluation's standardised instances (`c "nvars": V,` and `c "ncls": C,`; DeepDist sizes its arrays from these lines
alone and, without them, reads no clause and crashes; the other solvers skip comments), is piped to the solver as /proc/self/fd/0 (the
sandbox child may not write files). The solver runs for the remaining budget (wall clock; the child is alone on a
pinned core), then receives SIGTERM, on which MaxSAT Evaluation solvers print their best assignment ("v" line). The
assignment is decoded to the chosen edges; a violated hard clause or a missing "v" line fails the run. The domain
checker re-checks the witness; the solver's reported cost is never trusted.

Seeds. These solvers fix their own random seeds, so the same input gives the same run. The seed instead picks an
isomorphic copy of the instance: a seeded random order of the variables, of the clauses and of the literals within
each clause (the usual way to sample a deterministic solver's run-to-run spread; nothing about the problem
changes). The model is mapped back to the original edges.

Parameters (data only): {solver, cpu_seconds}. Domain: triangle_free_host_v1.
"""
import hashlib
import os
from pathlib import Path
import re
import signal
import subprocess
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/maxsat.py',)
_BIN = '/usr/local/genesis-sota/bin/'
SOLVERS = {
    'deepdist': {'binary': _BIN + 'DeepDist',
                         'sha256': 'b06627366a58402fa9d8ec1ebfb7206d3d9a023c0c12f944c06c4b3b571f5adc', 'args': ()},
    'spb-maxsat-c-fps': {'binary': _BIN + 'SPB-MaxSAT-c-FPS',
                         'sha256': '3f55ae480e0c0c353edf152f32f6749e1ca273537181339b708a7d4dd405b221', 'args': ()},
    'nuwls-c-ibr': {'binary': _BIN + 'NuWLS-c-IBR',
                         'sha256': 'c8567c3949753d310a4fb284d1ccde8bc3881f0b36347e2f0ac1894afc24d2f1', 'args': ()},
    'tt-open-wbo-inc': {'binary': _BIN + 'TT-Open-WBO-Inc-IntelSAT',
                         'sha256': 'f54cfaa62ff5a120aa495d93f8d2072b8ae7c9f02143f363dcc63d8f1da7ddcf', 'args': ()},
    'aperture': {'binary': _BIN + 'Aperture',
                         'sha256': '862515f4790576e8689d023c41753008e10e66ada9a47d121fa38815f4e43fe9', 'args': ('-s', 'glucose')},
}
_DIGEST = {}


# A build stamp some binaries embed (Aperture's bundled SAT solvers' configure scripts write `date; uname` output into
# the binary), and the GNU build-id note, a hash the linker computes over the binary and so over the stamp: a rebuild
# from the same source differs in these bytes only (checked by rebuilding both Apertures twice, B20_R98). The pin
# zeroes them before hashing, so it covers what the binary is, not when and where it was built. A binary without a
# stamp hashes as plain SHA-256, build-id included.
STAMP = re.compile(rb'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [ 0-9][0-9] '
                   rb'[0-9]{2}:[0-9]{2}:[0-9]{2} [A-Za-z0-9+\-]{1,6} [0-9]{4} Linux [ -~]{1,200}')
BUILD_ID = re.compile(rb'\x04\x00\x00\x00\x14\x00\x00\x00\x03\x00\x00\x00GNU\x00.{20}', re.S)


def stamp_free(data):
    """The bytes with any build stamp and, if there is one, the build-id zeroed (same length: nothing else moves)."""
    if not STAMP.search(data):
        return data
    data = STAMP.sub(lambda m: b'\0' * len(m.group(0)), data)
    return BUILD_ID.sub(lambda m: m.group(0)[:16] + b'\0' * 20, data)


def binary_digest(path):
    """SHA-256 of the binary with its build stamp zeroed (B20_R98); None if it is missing."""
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(stamp_free(p.read_bytes())).hexdigest() if p.is_file() else None
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


def wcnf(E, seed=None):
    """The classic WCNF text: one variable per edge; hard clauses (weight TOP) forbid each triangle. Without a seed,
    variable i+1 is edge i, in order. With a seed, an isomorphic copy: variable k+1 is edge order[k] for a seeded
    random permutation, and clauses and literals are shuffled. Returns the text, or (text, order) with a seed."""
    import random
    m = len(E)
    order = list(range(m))
    rng = random.Random(seed) if seed is not None else None
    if rng:
        rng.shuffle(order)
    var = {E[j]: k + 1 for k, j in enumerate(order)}
    T = triangles(E)
    top = m + 1
    hard = [[var[(u, v)], var[(v, w)], var[(u, w)]] for u, v, w in T]
    clauses = [f'{top} ' + ' '.join(f'-{x}' for x in (rng.sample(h, 3) if rng else h)) + ' 0' for h in hard]
    clauses += [f'1 {k + 1} 0' for k in range(m)]
    if rng:
        rng.shuffle(clauses)
    head = ['c {', f'c "nvars": {m},', f'c "ncls": {len(clauses)},', 'c }', f'p wcnf {m} {len(clauses)} {top}']
    text = '\n'.join(head + clauses) + '\n'
    return text if seed is None else (text, order)


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
    text, order = wcnf(E, seed)
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
    chosen = sorted(E[order[k - 1]] for k in true if 1 <= k <= len(E))
    picked = set(chosen)
    for u, v, w in triangles(E):
        if (u, v) in picked and (v, w) in picked and (u, w) in picked:
            raise RuntimeError(f'{params["solver"]} returned an assignment that violates a hard clause')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
