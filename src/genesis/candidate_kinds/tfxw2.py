"""Candidate kind `tfxw-v2` (registry v2 and the large runner, B20_R96): `tfxw-v1` with an operator grammar (see
`candidate_kinds/native/tfxw2.c`): late acceptance, great deluge and record-to-record travel besides probability and
Metropolis acceptance; population annealing; heavy-tailed (Levy) kick counts; and a choice of which edge a kick
removes. With the new keys at their first values it runs tfxw-v1's search, so tfxw-v1's frozen configurations stay
expressible and comparable. tfxw-v1 itself is unchanged (B20_R95's evidence pins it).

Binary built by `scripts/b20r96_build_tfxw2.py` (gcc 13.3, `-O3 -std=gnu11 -static`, deterministic), installed as
/usr/local/genesis-sota/bin/tfxw2, pinned by SHA-256. Parameters (data only): {cpu_seconds, config}, config giving
every key of SPACE a value from its list. The best edge set is decoded and re-checked here; the domain re-checks it.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import time

from . import tfx as T, tfxw as TW

DOMAINS = TW.DOMAINS
FILES = ('candidate_kinds/tfxw2.py', 'candidate_kinds/native/tfxw2.c', 'candidate_kinds/tfxw.py',
         'candidate_kinds/tfx.py')
BINARY = '/usr/local/genesis-sota/bin/tfxw2'
BINARY_SHA256 = '9e67421719ac63248b024db07fa50eb83537bee665b94444d7e14c43af2beab9'
SPACE = dict(TW.SPACE, acc=(0, 1, 2, 3, 4), lahc=(20, 5, 100, 500), pa=(0, 10, 50), levy=(0, 1.5, 2.0, 3.0),
             rem=(0, 1), rr=(1.0, 0.5, 2.0, 5.0))
DEFAULT = dict(TW.DEFAULT, lahc=20, pa=0, levy=0, rem=0, rr=1.0)
NEW_KEYS = ('lahc', 'pa', 'levy', 'rem', 'rr')
_DIGEST = {}


def from_v1(config):
    """A tfxw-v1 configuration as the tfxw-v2 configuration that runs the same search."""
    return dict(config, lahc=20, pa=0, levy=0, rem=0, rr=1.0)


def binary_digest(path=None):
    path = path or BINARY
    if path not in _DIGEST:
        p = Path(path)
        _DIGEST[path] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return _DIGEST[path]


def check_config(config):
    if not isinstance(config, dict) or set(config) != set(SPACE):
        return f'config must give exactly the keys {sorted(SPACE)}'
    for k, allowed in SPACE.items():
        v = config[k]
        if isinstance(v, bool) or type(v) not in (int, float) or v not in allowed:
            return f'config[{k!r}] must be one of {allowed}'
    return None


def check_parameters(domain, params):
    if domain not in DOMAINS:
        return f'tfxw-v2 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds', 'config'}:
        return 'tfxw-v2 takes {cpu_seconds, config}'
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


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges); as tfxw-v1's."""
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
        raise RuntimeError('tfxw2 did not stop at its budget')
    lines = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 + len(E) or set(lines[0][2:]) - {'0', '1'}:
        raise RuntimeError(f'tfxw2 failed (exit {r.returncode}): {(r.stdout + r.stderr)[-300:]}')
    chosen = [E[i] for i, b in enumerate(lines[0][2:]) if b == '1']
    nb = [0] * n
    for u, v in chosen:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    if any(nb[u] & nb[v] for u, v in chosen):
        raise RuntimeError('tfxw2 returned an edge set with a triangle')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
