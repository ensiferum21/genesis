"""Candidate kind `maxsat-anytime-large-v1` (registry v2, B20_R94): the 2024 and 2026 MaxSAT anytime champions
(`maxsat-anytime-v1`, `maxsat-anytime-2026-v1`) on hosts of the DEV-only large domain `triangle_free_large_v1`.

Why a separate kind. The two existing kinds hash their own files into every descriptor's identity; declaring the new
domain in them would have changed the identity of every frozen descriptor of B20_R87-R92. This kind adds the domain
without touching them, using their encodings (`maxsat.wcnf`, `maxsat2026.wcnf2022`: the same seeded isomorphic
copies), their solvers' commands and arguments (the 2026 entrants with the whole-second timeout hint), pipe input,
SIGTERM at the budget, `maxsat.parse_model` and the hard-clause re-check.

One difference, in the champions' favour: on large hosts encoding the instance takes the harness a second or more
(B20_R94's look: 1.2 s of Python for G(256, 0.5), 350,231 triangles), and the n <= 63 kinds charge it to the solver's
budget. Here the solver's budget starts after the encoding: it gets the whole `cpu_seconds` (wall clock from its start,
as in the Evaluation), and the descriptor's resource profile must allow the encoding on top (`ENCODING_ALLOWANCE_S`).

Parameters (data only): {solver, cpu_seconds}; solver is any key of either kind's SOLVERS (they are disjoint).
"""
import signal
import subprocess
import time

from . import maxsat as MS, maxsat2026 as M26

ENCODING_ALLOWANCE_S = 5.0     # what a descriptor's profile adds to cpu_seconds for the encoding

DOMAINS = ('triangle_free_large_v1',)
FILES = ('candidate_kinds/maxsat_large.py', 'candidate_kinds/maxsat.py', 'candidate_kinds/maxsat2026.py')
assert not set(MS.SOLVERS) & set(M26.SOLVERS)
SOLVERS = {**{k: ('2024', v) for k, v in MS.SOLVERS.items()}, **{k: ('2026', v) for k, v in M26.SOLVERS.items()}}


def check_parameters(domain, params):
    if domain not in DOMAINS:
        return f'maxsat-anytime-large-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'solver', 'cpu_seconds'}:
        return 'maxsat-anytime-large-v1 takes {solver, cpu_seconds}'
    if params['solver'] not in SOLVERS:
        return f'solver must be one of {sorted(SOLVERS)}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 600:
        return 'cpu_seconds must be in (0, 600]'
    era, s = SOLVERS[params['solver']]
    pins = [(s['binary'], s['sha256'])] + (list(s.get('data', {}).items()) if era == '2026' else [])
    for path, want in pins:
        got = MS.binary_digest(path) if era == '2024' else M26.digest(path)
        if got is None or got != want:
            return f'{path} is missing or not the pinned build ({got} != {want})'
    return None


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int}: encode, then give the solver its whole budget."""
    import os
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    E = [tuple(e) for e in view.edges]
    if not E:
        return {'selected': [], 'value': 0}
    era, s = SOLVERS[params['solver']]
    text, order = (MS.wcnf if era == '2024' else M26.wcnf2022)(E, seed)
    spent = time.process_time() - start
    budget = max(0.01, min(params['cpu_seconds'], cpu_seconds - spent))
    if era == '2024':
        argv = [s['binary'], '/proc/self/fd/0', *s['args']]
    else:
        argv = [s['binary'], *[a.format(instance='/proc/self/fd/0', seconds=M26.hint(budget)) for a in s['args']]]
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    nb = {}
    for u, v in chosen:
        nb[u] = nb.get(u, 0) | 1 << v
        nb[v] = nb.get(v, 0) | 1 << u
    if any(nb[u] & nb[v] for u, v in chosen):
        raise RuntimeError(f'{params["solver"]} returned an assignment that violates a hard clause')
    return {'selected': [list(e) for e in chosen], 'value': len(chosen)}
