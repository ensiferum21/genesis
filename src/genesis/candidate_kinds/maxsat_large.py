"""Candidate kind `maxsat-anytime-large-v1` (registry v2, B20_R94): the 2024 and 2026 MaxSAT anytime champions
(`maxsat-anytime-v1`, `maxsat-anytime-2026-v1`) on hosts of the DEV-only large domain `triangle_free_large_v1`.

Why a separate kind. The two existing kinds hash their own files into every descriptor's identity; declaring the new
domain in them would have changed the identity of every frozen descriptor of B20_R87-R92. This kind adds the domain
without touching them: it dispatches to their unchanged `solve` (same encoding, same seeded isomorphic copies, same
pipe input, SIGTERM at the budget, hard-clause re-check) and checks parameters and pinned binaries the same way.

Parameters (data only): {solver, cpu_seconds}; solver is any key of either kind's SOLVERS (they are disjoint).
"""
from . import maxsat as MS, maxsat2026 as M26

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
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    era, s = SOLVERS[params['solver']]
    pins = [(s['binary'], s['sha256'])] + (list(s.get('data', {}).items()) if era == '2026' else [])
    for path, want in pins:
        got = MS.binary_digest(path) if era == '2024' else M26.digest(path)
        if got is None or got != want:
            return f'{path} is missing or not the pinned build ({got} != {want})'
    return None


def solve(view, params, cpu_seconds, seed):
    era, _ = SOLVERS[params['solver']]
    return (MS if era == '2024' else M26).solve(view, params, cpu_seconds, seed)
