"""Candidate kind `maxsat-anytime-2026-v1` (registry v2, B20_R91): the MaxSAT Evaluation 2026 unweighted anytime
entrants, built from their submitted sources by `scripts/b20r91_mse2026_tools.py`, on the problem's exact MaxSAT
encoding, as baselines.

Why. The 2026 Evaluation ranked PASMaxSAT-c first in the unweighted anytime track at 60 s and 1707 s and
Aperture-KBG first at 300 s; then SGAT-NuWLS-c, Aperture-GBG, NuWLS-c-2026-UB, Aperture-IBI, DeepDist-c and
NuWLS-c-2026. All eight are here. B20_R90's opponents
(`maxsat-anytime-v1`) were the 2024 podium, DeepDist and Aperture from hermax.

Solvers (fixed; binaries under /usr/local/genesis-sota/bin pinned by SHA-256, data files pinned too; refused if
missing or different). Each runs with the configuration of its Evaluation run script (`bin/run_ANYTIME-UW`):
  * `pasmaxsat-c`: `PASMaxSAT-c INSTANCE SECONDS`;
  * `sgat-nuwls-c`: `NuWLS-c_static -nuwls-sgat-model=WEIGHTS INSTANCE SECONDS` (the learned weight file shipped
    with the submission, installed read-only);
  * `nuwls-c-2026`: `NuWLS-c_static INSTANCE` (the Evaluation ran it under runsolver with the time limit);
  * `deepdist-c`: `DeepDist-c_static INSTANCE SECONDS`;
  * `nuwls-c-2026-ub`: `NuWLS-c_static INSTANCE` (the UB variant's own build; under runsolver in the Evaluation);
  * `aperture-kbg`, `aperture-gbg`, `aperture-ibi`: Aperture 2026 (one binary) with `-v 0 opti -i`, `-v 0` and
    `-s topor -v 0`, its three unweighted configurations (`run_ANYTIME-UW_K_B_G`, `_G_B_G`, `_I_B_I`).
SECONDS is the 2026 rules' timeout hint. The solvers accept only whole seconds, so it is the budget rounded up
(1 s for every budget up to 1 s); as in the Evaluation, the run is ended at the budget by SIGTERM, on which each
prints its best assignment.

Input. The 2026 Evaluation's instances are in the post-2022 WCNF format (hard clauses marked `h`, no `p` line) with
the standardised comment header; this kind writes exactly that, from `maxsat.wcnf` (same variables, same seeded
isomorphic copy, so a seed means the same copy as in `maxsat-anytime-v1`). Everything else (pipe input, decoding,
hard-clause re-check, loud failure) is `maxsat-anytime-v1`'s.

Parameters (data only): {solver, cpu_seconds}. Domain: triangle_free_host_v1.
"""
import hashlib
import math
import os
from pathlib import Path
import signal
import subprocess
import time

from . import maxsat as MS

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/maxsat2026.py', 'candidate_kinds/maxsat.py')
_BIN = '/usr/local/genesis-sota/bin/'
_SHARE = '/usr/local/genesis-sota/share/'
SOLVERS = {
    'pasmaxsat-c': {'binary': _BIN + 'PASMaxSAT-c',
                    'sha256': '825594bde1a7298dfccbaeca0ba184d2c52a07e821cb0840f62327bbac1094f5',
                    'args': ('{instance}', '{seconds}'), 'data': {}},
    'sgat-nuwls-c': {'binary': _BIN + 'SGAT-NuWLS-c',
                     'sha256': '1d1b9bdcedcf388eca83243ad39bc39a4f54a8f39bf571d3ad4c8503d86506cd',
                     'args': ('-nuwls-sgat-model=' + _SHARE + 'SGAT-NuWLS-c/nuwls_sgat_weights.artifact',
                              '{instance}', '{seconds}'),
                     'data': {_SHARE + 'SGAT-NuWLS-c/nuwls_sgat_weights.artifact':
                              '25e621158d81e5c82ffc5e79de4c2998a21d94b61408da32ed1f05bb17ffd800'}},
    'nuwls-c-2026': {'binary': _BIN + 'NuWLS-c-2026',
                     'sha256': 'ddfc30ea87db3d3697cb36831b70afab3f3fec33a85f275edabdf43f530da359', 'args': ('{instance}',),
                     'data': {}},
    'nuwls-c-2026-ub': {'binary': _BIN + 'NuWLS-c-2026-UB',
                        'sha256': '7a9bebe4c5a88b28b3955da00cbce91fb64545cf0728a7026020e2d0a364f239',
                        'args': ('{instance}',), 'data': {}},
    'aperture-kbg': {'binary': _BIN + 'Aperture-2026',
                     'sha256': '0fb72956e3c9c41c31626910b6b0ef26fc47f01d361d0e421b3f1100dec4b511',
                     'args': ('{instance}', '-v', '0', 'opti', '-i'), 'data': {}},
    'aperture-gbg': {'binary': _BIN + 'Aperture-2026',
                     'sha256': '0fb72956e3c9c41c31626910b6b0ef26fc47f01d361d0e421b3f1100dec4b511',
                     'args': ('{instance}', '-v', '0'), 'data': {}},
    'aperture-ibi': {'binary': _BIN + 'Aperture-2026',
                     'sha256': '0fb72956e3c9c41c31626910b6b0ef26fc47f01d361d0e421b3f1100dec4b511',
                     'args': ('{instance}', '-s', 'topor', '-v', '0'), 'data': {}},
    'deepdist-c': {'binary': _BIN + 'DeepDist-c',
                   'sha256': '7ee4555ccbdccfddb4effa5136cac9ed1be16d6797971553da7dd43da3e4a9ad',
                   'args': ('{instance}', '{seconds}'), 'data': {}},
}
_DIGEST = {}


def digest(path):
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _DIGEST[path]


def check_parameters(domain, params):
    """None, or the reason the parameters are refused (including a missing or unpinned binary or data file)."""
    if domain not in DOMAINS:
        return f'maxsat-anytime-2026-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'solver', 'cpu_seconds'}:
        return 'maxsat-anytime-2026-v1 takes {solver, cpu_seconds}'
    if params['solver'] not in SOLVERS:
        return f'solver must be one of {sorted(SOLVERS)}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    s = SOLVERS[params['solver']]
    for path, want in [(s['binary'], s['sha256']), *s['data'].items()]:
        got = digest(path)
        if got is None or got != want:
            return f'{path} is missing or not the pinned build ({got} != {want})'
    return None


def wcnf2022(E, seed=None):
    """The post-2022 WCNF text (with the standardised header) of `maxsat.wcnf`'s instance: hard clauses as `h ...`,
    soft units as `1 x 0`, no `p` line. Returns the text, or (text, order) with a seed."""
    out = MS.wcnf(E, seed)
    text, order = out if seed is not None else (out, None)
    lines = text.splitlines()
    head = [l for l in lines if l.startswith('p ')]
    top = head[0].split()[4]
    new = []
    for l in lines:
        if l.startswith('p '):
            continue
        if l.startswith('c'):
            new.append(l)
            continue
        w, rest = l.split(' ', 1)
        new.append(('h ' + rest) if w == top else l)
    text = '\n'.join(new) + '\n'
    return text if seed is None else (text, order)


def hint(budget):
    """The timeout hint in whole seconds (the solvers refuse fractions): the budget rounded up."""
    return max(1, math.ceil(budget - 1e-9))


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
    text, order = wcnf2022(E, seed)
    budget = max(0.01, min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start))
    args = [a.format(instance='/proc/self/fd/0', seconds=hint(budget)) for a in s['args']]
    p = subprocess.Popen([s['binary'], *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(input=text, timeout=budget)
    except subprocess.TimeoutExpired:
        p.send_signal(signal.SIGTERM)
        try:
            out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
    true = MS.parse_model(out, len(E))
    if true is None:
        raise RuntimeError(f'{params["solver"]} printed no assignment (exit {p.returncode}): {(out + err)[-300:]}')
    chosen = sorted(E[order[k - 1]] for k in true if 1 <= k <= len(E))
    picked = set(chosen)
    for u, v, w in MS.triangles(E):
        if (u, v) in picked and (v, w) in picked and (u, w) in picked:
            raise RuntimeError(f'{params["solver"]} returned an assignment that violates a hard clause')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
