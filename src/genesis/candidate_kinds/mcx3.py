"""Candidate kind `mcx3-v1` (max-cut runner, B20_R153): `mcx2-v1` with a construct algebra over its programs.

Why. Daniel, 27 Oct 2026, 14:33: "prioritize richer algorithm expressiveness, experimentally separated from
improvements in search. They should improve on themselves as in expressiveness wise and richness"
(`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`). mcx2's programs are flat loops of physics operators with two guards; mcx3
lets a program say WHEN and WHERE an operator acts, so that there is a richer language for Genesis to write engines
in and to grow (the named statements of `genesis.expressive`).

The constructs (`native/mcx3.c`, where they are specified): targets on operators (`@c`, `@h`, `@a`, `@<levels>`),
guards over run-time observables (`?f<v`, `?d>v`, ... : the fraction of the budget spent, the elite pool's
diversity, the spread of the replicas' cuts, the attractors since the last new best), repeats (`*k`), and blocks
(`[ ... ]`). They are control and addressing; no search operator is added, and the operators are mcx2's (the C
functions that implement them are mcx2's, unchanged). The algebra is the builder's: a human LANGUAGE change, labelled
as such. Every mcx2 program is an mcx3 program with the same meaning: under the same seed and options mcx3 makes the
same moves with the same clock readings and returns the same cut (`test_mcx3_kind`, with counting-clock builds).

The language as data. A program is a list of items: ('op', op, arg, target), ('S', k), ('P', k), ('?', obs, cmp,
v), ('*', k, item), ('[', items); with `calls=True` also ('call', name, args), a named statement, which the front end
(`genesis.expressive.lambda1`) expands before a program reaches the kind. `parse` reads the text, `render` writes the
canonical text, `canonical` normalises a program to the one form of its class under rewrites that preserve its
meaning (a target equal to the operator's default is dropped, B@c is b, a single-item block is its item, an unguarded
block not ending in a guard is spliced into its list, *1 is dropped, nested repeats multiply), and `is_lambda0` tells
whether a program is in mcx2's language. A configuration's `prog` is canonical text without calls.

Binary. Built from the in-repository source by `scripts/b20r153_build_mcx3.py` (gcc 13.3, `-O3 -std=gnu11 -static`,
deterministic), installed as BINARY, pinned by SHA-256, refused if missing or different.
Parameters (data only): {cpu_seconds, config}; config gives `prog` and a value from SPACE (mcx2's) for every other
key. Domain: maxcut_v1.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

DOMAINS = ('maxcut_v1',)
FILES = ('candidate_kinds/mcx3.py', 'candidate_kinds/native/mcx3.c')
BINARY = '/usr/local/genesis-sota/bin/mcx3'
BINARY_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
OPS = 'BbXICMHRDL'
DEFAULT_TARGET = {'B': 'a', 'b': 'c', 'X': 'a', 'I': 'a', 'D': 'a', 'L': 'c', 'C': 'c', 'M': 'h', 'H': 'h', 'R': 'h'}
GUARDS = ('S', 'P', '?')
OBSERVABLES = {'f': (0, 1000), 'd': (0, 1000), 's': (0, 10 ** 6), 't': (0, 10 ** 7)}
ARG_RANGE = {'B': (1, 100000), 'b': (1, 100000), 'S': (1, 10 ** 7), 'P': (1, 1000), '*': (1, 1000)}
MAX_ITEMS = 256                 # the kind's bound on a program's items (the binary's is 512)
MAX_DEPTH = 8                   # the kind's bound on nesting (the binary's is 16)
LAMBDA0_MAX = 32                # mcx2's MAX_STATEMENTS
LEVEL_DIGITS = '01234567'
SPACE = {'levels': (1, 2, 3, 4, 6, 8), 'L0': (0.005, 0.01, 0.02, 0.05, 0.1, 0.2), 'L0hot': (0.02, 0.05, 0.1, 0.2, 0.3),
         'tmax': (0.05, 0.1, 0.2, 0.5, 1.0, 2.0), 'P': (0.5, 0.75, 0.8, 0.9), 'tt': (2, 3, 5, 10, 20),
         'pool': (4, 8, 16, 32), 'pert': (0, 1, 2)}
DEFAULT = {'prog': 'B100 X I S2000 C', 'levels': 4, 'L0': 0.01, 'L0hot': 0.1, 'tmax': 0.5, 'P': 0.8, 'tt': 10,
           'pool': 8, 'pert': 2}
_DIGEST = {}
_NUM = r'(0|[1-9][0-9]{0,8}|\$[1-9])'
_OP = re.compile(r'^([BbXICMHRDL])' + _NUM + r'?(?:@([cha]|[0-7]{1,8}))?$')
_GUARD = re.compile(r'^([SP])' + _NUM + r'$')
_OBS = re.compile(r'^\?([fdst])([<>])' + _NUM + r'$')
_REP = re.compile(r'^\*' + _NUM + r'$')
_ONE = r'(?:0|[1-9][0-9]{0,8}|\$[1-9])'
_CALL = re.compile(r'^([a-z][a-z0-9_]{1,23})(?:\((' + _ONE + r'(?:,' + _ONE + r')*)\))?$')
NAME = re.compile(r'^[a-z][a-z0-9_]{1,23}$')


def _num(s, params):
    if s.startswith('$'):
        if not params:
            raise ValueError(f'a parameter {s} outside a definition')
        return s
    return int(s)


def parse(text, calls=False, params=False):
    """The program in `text` as a tuple of items, or a ValueError. `calls`: named statements allowed; `params`:
    parameters $1..$9 allowed in numeric places (in a definition's body). Ranges are checked by `check`."""
    if not isinstance(text, str):
        raise ValueError('a program is a string')
    toks = text.split()
    pos = [0]

    def item(depth):
        if depth > MAX_DEPTH:
            raise ValueError(f'nesting deeper than {MAX_DEPTH}')
        t = toks[pos[0]]
        pos[0] += 1
        if t == '[':
            body = lst(depth + 1, True)
            if not body:
                raise ValueError('an empty block')
            return ('[', body)
        m = _REP.match(t)
        if m:
            if pos[0] >= len(toks) or toks[pos[0]] == ']' or toks[pos[0]][0] in 'SP?':
                raise ValueError('a repeat governs an operator, a block, a call or a repeat')
            return ('*', _num(m.group(1), params), item(depth + 1))
        m = _GUARD.match(t)
        if m:
            return (m.group(1), _num(m.group(2), params))
        m = _OBS.match(t)
        if m:
            return ('?', m.group(1), m.group(2), _num(m.group(3), params))
        m = _OP.match(t)
        if m:
            op, arg, tgt = m.group(1), m.group(2), m.group(3)
            if (op in 'Bb') != (arg is not None):
                raise ValueError(f'{op} {"needs" if op in "Bb" else "takes no"} argument')
            if op == 'b' and tgt:
                raise ValueError('b takes no target (it is B@c)')
            return ('op', op, _num(arg, params) if arg else None, tgt)
        m = _CALL.match(t)
        if m and not calls:
            raise ValueError(f'a named statement {t!r} (expand it first)')
        if m:
            args = tuple(_num(a, params) for a in m.group(2).split(',')) if m.group(2) else ()
            return ('call', m.group(1), args)
        raise ValueError(f'bad item {t!r}')

    def lst(depth, closed):
        out = []
        while pos[0] < len(toks) and toks[pos[0]] != ']':
            out.append(item(depth))
        if closed:
            if pos[0] >= len(toks):
                raise ValueError('a "[" without "]"')
            pos[0] += 1
        elif pos[0] < len(toks):
            raise ValueError('a "]" without "["')
        return tuple(out)
    prog = lst(0, False)
    if not prog:
        raise ValueError('an empty program')
    return prog


def _render_item(x):
    k = x[0]
    if k == 'op':
        return x[1] + ('' if x[2] is None else str(x[2])) + ('' if x[3] is None else '@' + x[3])
    if k in ('S', 'P'):
        return k + str(x[1])
    if k == '?':
        return f'?{x[1]}{x[2]}{x[3]}'
    if k == '*':
        return f'*{x[1]} ' + _render_item(x[2])
    if k == '[':
        return '[ ' + ' '.join(_render_item(y) for y in x[1]) + ' ]'
    if k == 'call':
        return x[1] + (f'({",".join(map(str, x[2]))})' if x[2] else '')
    raise ValueError(f'not an item: {x!r}')


def render(prog):
    return ' '.join(_render_item(x) for x in prog)


def walk(prog):
    """Every item of the program, depth first, in order."""
    for x in prog:
        yield x
        if x[0] == '[':
            yield from walk(x[1])
        elif x[0] == '*':
            yield from walk((x[2],))


def size(prog):
    """The number of items (each operator, guard, repeat, block and call counts one)."""
    return sum(1 for _ in walk(prog))


def depth(prog):
    def d(x):
        return 1 + (max(d(y) for y in x[1]) if x[0] == '[' else d(x[2]) if x[0] == '*' else 0)
    return max(d(x) for x in prog)


def check(prog, calls=False):
    """None if the program is well formed for the kind (ranges, bounds, at least one B or b), else why not."""
    try:
        if size(prog) > MAX_ITEMS:
            return f'more than {MAX_ITEMS} items'
        if depth(prog) > MAX_DEPTH + 1:
            return f'nesting deeper than {MAX_DEPTH}'
        for x in walk(prog):
            k = x[0]
            if k == 'call' and not calls:
                return 'a named statement (expand it first)'
            nums = []
            if k == 'op':
                if x[1] not in OPS:
                    return f'unknown operator {x[1]}'
                if x[2] is not None:
                    nums.append((x[1], x[2]))
                if x[3] is not None and x[3] not in ('c', 'h', 'a') and not (
                        x[3] and set(x[3]) <= set(LEVEL_DIGITS)):
                    return f'bad target {x[3]}'
            elif k in ('S', 'P', '*'):
                nums.append((k, x[1]))
            elif k == '?':
                lo, hi = OBSERVABLES[x[1]]
                if isinstance(x[3], int) and not lo <= x[3] <= hi:
                    return f'?{x[1]} value outside [{lo}, {hi}]'
            for op, v in nums:
                lo, hi = ARG_RANGE[op]
                if isinstance(v, int) and not lo <= v <= hi:
                    return f'{op} argument outside [{lo}, {hi}]'
        if not calls and not any(x[0] == 'op' and x[1] in 'Bb' for x in walk(prog)):
            return 'a program needs a B or b'
    except (TypeError, IndexError, KeyError) as e:
        return f'malformed program ({e})'
    return None


def statements(text):
    """The program in `text` (no calls), checked; a ValueError if it is not one."""
    prog = parse(text)
    why = check(prog)
    if why:
        raise ValueError(why)
    return prog


def _canon_target(op, tgt):
    if tgt is None:
        return None
    if tgt not in ('c', 'h', 'a'):
        tgt = ''.join(sorted(set(tgt)))
        tgt = 'c' if tgt == '0' else 'a' if tgt == LEVEL_DIGITS else tgt
    return None if tgt == DEFAULT_TARGET[op] else tgt


def _guardlike(x, guard_calls):
    return x[0] in GUARDS or (x[0] == 'call' and (guard_calls is None or x[1] in guard_calls))


def _canon_item(x, guard_calls):
    k = x[0]
    if k == 'op':
        op, arg, tgt = x[1], x[2], _canon_target(x[1], x[3])
        if op == 'B' and tgt == 'c':
            return ('op', 'b', arg, None)
        return ('op', op, arg, tgt)
    if k == '[':
        body = canonical(x[1], guard_calls)
        return body[0] if len(body) == 1 and not _guardlike(body[0], guard_calls) else ('[', body)
    if k == '*':
        n, body = x[1], _canon_item(x[2], guard_calls)
        if isinstance(n, int) and body[0] == '*' and isinstance(body[1], int) and n * body[1] <= ARG_RANGE['*'][1]:
            n, body = n * body[1], body[2]
        return body if n == 1 else ('*', n, body)
    if k == 'call':
        return ('call', x[1], tuple(x[2]))
    return tuple(x)


def canonical(prog, guard_calls=None):
    """The canonical form: the same meaning (see the module docstring for the rewrites), one text per class.
    `guard_calls`: the named statements that are guards (a call to one governs the next item); None, as when the
    library is not known, treats every call as one, which keeps the meaning whatever the calls expand to."""
    out = []
    for x in (_canon_item(y, guard_calls) for y in prog):
        governed = bool(out) and _guardlike(out[-1], guard_calls)
        if x[0] == '[' and not governed and not _guardlike(x[1][-1], guard_calls):
            out.extend(x[1])
        else:
            out.append(x)
    return tuple(out)


def is_lambda0(prog):
    """In mcx2's language: flat, operators without targets and S and P guards only, at most 32 statements."""
    return (len(prog) <= LAMBDA0_MAX and all(x[0] in ('S', 'P') or (x[0] == 'op' and x[3] is None) for x in prog)
            and check(prog) is None)


def check_config(config):
    if not isinstance(config, dict) or set(config) != set(SPACE) | {'prog'}:
        return f'config must give exactly the keys {sorted(set(SPACE) | {"prog"})}'
    try:
        prog = statements(config['prog'])
    except ValueError as e:
        return f'prog: {e}'
    if render(canonical(prog)) != config['prog']:
        return 'prog must be in canonical form'
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
        return f'mcx3-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds', 'config'}:
        return 'mcx3-v1 takes {cpu_seconds, config}'
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


def solve(view, params, cpu_seconds, seed, binary=None):
    """{'side': '0101...', 'value': int} for the candidate view (n, weighted edges). `binary`: for tests only."""
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
        r = subprocess.run([binary or BINARY, *arguments(params['config'])], input=text, capture_output=True,
                           text=True, timeout=budget + 10)
    except subprocess.TimeoutExpired:
        raise RuntimeError('mcx3 did not stop at its budget')
    lines = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 + n or set(lines[0][2:]) - {'0', '1'}:
        raise RuntimeError(f'mcx3 failed (exit {r.returncode}): {(r.stdout + r.stderr)[-300:]}')
    side = lines[0][2:]
    return {'side': side, 'value': sum(w for u, v, w in E if side[u] != side[v])}
