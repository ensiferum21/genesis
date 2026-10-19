"""Candidate kind `solver-program-v1` (registry v2, B20_R78): runs a solver program written in the closed language
of `invention/solver_programs.py`, so that a program the system's own program search finds can be frozen as a
descriptor and evaluated by the runner like any other kind.

The program is data: `check_parameters` refuses anything outside the grammar (statements, arguments, nesting,
size) and any representation that B18's checked package does not license (SUFF or EQ) on the domain, exactly as
`represent-search-v1` requires. The interpreter never executes code from data.

Parameters (data only): {program, cpu_seconds}. Domain: triangle_free_host_v1. The domain checker re-checks the
witness; the claimed value is never trusted.
"""
import json
from pathlib import Path

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/solver_program.py', 'invention/solver_programs.py', 'invention/representations.py',
         'invention/soundness.py', 'formal_research/triangle_theory.py')
PACKAGE = Path(__file__).resolve().parents[3] / 'evidence' / 'invention_b18' / 'representations' / 'package.json'


def licensed_reps(domain):
    """The B18 representations whose established soundness mode on the domain is SUFF or EQ."""
    from ..invention import representations as R
    from ..invention import soundness as S
    modes = S.representation_modes(json.loads(PACKAGE.read_text()))
    out = set()
    for r in R.proposals():
        rec = modes.get((r['id'], domain))
        if rec is not None and not S.problems(rec, 'lift_positive') and rec['established'] in ('SUFF', 'EQ'):
            out.add(r['id'])
    return out


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    from ..invention import solver_programs as SP
    if domain not in DOMAINS:
        return f'solver-program-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'program', 'cpu_seconds'}:
        return 'solver-program-v1 takes {program, cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    try:
        reps = licensed_reps(domain)
    except (OSError, ValueError, KeyError):
        return 'the representation package cannot be read'
    bad = SP.problems(params['program'], reps)
    return f'the program is not in the language: {bad[:3]}' if bad else None


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    import time
    start = time.process_time()
    from ..invention import representations as R
    from ..invention import solver_programs as SP
    rep = next(r for r in R.proposals() if r['id'] == params['program']['rep'])
    budget = min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start)
    best = SP.run(params['program'], rep, view.n, view.edges, max(0.01, budget), seed)
    return {'selected': [list(e) for e in best], 'value': len(best)}
