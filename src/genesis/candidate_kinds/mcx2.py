"""Candidate kind `mcx2-v1` (max-cut runner, B20_R125): Genesis's max-cut engine as an interpreter of search programs.

Why. Daniel, 24 Oct 2026: mix several physics principles, and let the system invent and improve its own engines and
the process that improves them. `mcx-v1` (B20_R104) fixed its search loop in C; here the loop is a PROGRAM over
physics operators, so that the system can write engines, not only configure one.

Algorithm (`native/mcx2.c`; the program and the configuration are data). A population of replicas at `levels`
temperatures (two per level), sharing mcx's elite pool, runs the program as the body of a loop until the CPU budget is
spent. Statements: B<k> (k attractors of breakout local search per replica), b<k> (the coldest level only), X (replica
exchange between adjacent levels), I (isoenergetic cluster moves within each level), C (renormalisation of the coldest
replica), M (MACUT's crossover into the hottest), H (Houdayer's elite exchange into the hottest), R (random restart of
the hottest), S<k> (the next statement only after k attractors without a new best) and P<k> (the next statement only on
every k-th pass). See the C source for each operator's source in the literature. None of the operators is new.

DEFAULT is the builder's hybrid, "REX": "B100 X I S2000 C" at 4 levels (parallel tempering over breakout local search,
isoenergetic cluster moves, renormalisation on stalls). It stands for the human-designed engine against which the
system's own programs are judged.

Binary. Built from the in-repository source by `scripts/b20r125_build_mcx2.py` (gcc 13.3, `-O3 -std=gnu11 -static`,
deterministic), installed as BINARY, pinned by SHA-256, refused if missing or different.
Parameters (data only): {cpu_seconds, config}; config gives `prog` (a program string in the grammar below) and a value
from SPACE for every other key. Domain: maxcut_v1.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

DOMAINS = ('maxcut_v1',)
FILES = ('candidate_kinds/mcx2.py', 'candidate_kinds/native/mcx2.c')
BINARY = '/usr/local/genesis-sota/bin/mcx2'
BINARY_SHA256 = '892b896b256e6dac3eb64aaba0e2d1ebef5ecb10e7950025cba028d324cfeebd'
OPS = 'BbXICMHRSP'
ARG_RANGE = {'B': (1, 100000), 'b': (1, 100000), 'S': (1, 10 ** 7), 'P': (1, 1000)}
MAX_STATEMENTS = 32
SPACE = {'levels': (1, 2, 3, 4, 6, 8), 'L0': (0.005, 0.01, 0.02, 0.05, 0.1, 0.2), 'L0hot': (0.02, 0.05, 0.1, 0.2, 0.3),
         'tmax': (0.05, 0.1, 0.2, 0.5, 1.0, 2.0), 'P': (0.5, 0.75, 0.8, 0.9), 'tt': (2, 3, 5, 10, 20),
         'pool': (4, 8, 16, 32), 'pert': (0, 1, 2)}
DEFAULT = {'prog': 'B100 X I S2000 C', 'levels': 4, 'L0': 0.01, 'L0hot': 0.1, 'tmax': 0.5, 'P': 0.8, 'tt': 10,
           'pool': 8, 'pert': 2}
_DIGEST = {}
_TOKEN = re.compile(r'^([BbXICMHRSP])([1-9][0-9]{0,8})?$')


def statements(prog):
    """[(op, arg or None)] or a ValueError."""
    if not isinstance(prog, str):
        raise ValueError('a program is a string')
    toks = prog.split()
    if not 1 <= len(toks) <= MAX_STATEMENTS:
        raise ValueError(f'a program has 1 to {MAX_STATEMENTS} statements')
    out = []
    for t in toks:
        m = _TOKEN.match(t)
        if not m:
            raise ValueError(f'bad statement {t!r}')
        op, arg = m.group(1), m.group(2)
        if (op in ARG_RANGE) != (arg is not None):
            raise ValueError(f'{op} {"needs" if op in ARG_RANGE else "takes no"} argument')
        if arg is not None:
            lo, hi = ARG_RANGE[op]
            if not lo <= int(arg) <= hi:
                raise ValueError(f'{op} argument outside [{lo}, {hi}]')
        out.append((op, int(arg) if arg else None))
    if not any(op in 'Bb' for op, _ in out):
        raise ValueError('a program needs a B or b statement')
    return out


def render(stmts):
    return ' '.join(op + (str(a) if a is not None else '') for op, a in stmts)


def check_config(config):
    if not isinstance(config, dict) or set(config) != set(SPACE) | {'prog'}:
        return f'config must give exactly the keys {sorted(set(SPACE) | {"prog"})}'
    try:
        if render(statements(config['prog'])) != config['prog']:
            return 'prog must be in canonical form (statements separated by single spaces)'
    except ValueError as e:
        return f'prog: {e}'
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
        return f'mcx2-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds', 'config'}:
        return 'mcx2-v1 takes {cpu_seconds, config}'
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
    return ['-prog', config['prog'], '-levels', str(int(config['levels'])), '-L0', repr(float(config['L0'])),
            '-L0hot', repr(float(config['L0hot'])), '-tmax', repr(float(config['tmax'])), '-P', repr(float(config['P'])),
            '-tt', str(int(config['tt'])), '-pool', str(int(config['pool'])), '-pert', str(int(config['pert']))]


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
        raise RuntimeError('mcx2 did not stop at its budget')
    lines = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 + n or set(lines[0][2:]) - {'0', '1'}:
        raise RuntimeError(f'mcx2 failed (exit {r.returncode}): {(r.stdout + r.stderr)[-300:]}')
    side = lines[0][2:]
    return {'side': side, 'value': sum(w for u, v, w in E if side[u] != side[v])}
