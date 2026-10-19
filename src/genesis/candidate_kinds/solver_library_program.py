"""Candidate kind `solver-library-v1` (registry v2, B20_R82): runs a solver program that may call a library of earlier
generations' programs (`invention/solver_library.py`), so that each generation of the system's program search can be
frozen and evaluated like any other kind.

Program and library are data, checked against the grammar (B20_R78's statements plus `macro`, library entries
calling only earlier entries) with a representation licensed by B18's checked package. Parameters (data only):
{program, cpu_seconds}, where program is {rep, body, library}. Domain: triangle_free_host_v1. The domain checker
re-checks the witness.
"""
DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/solver_library_program.py', 'invention/solver_library.py', 'invention/solver_programs.py',
         'candidate_kinds/solver_program.py', 'invention/representations.py', 'invention/soundness.py',
         'formal_research/triangle_theory.py')


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    from ..invention import solver_library as SL
    from . import solver_program as KP
    if domain not in DOMAINS:
        return f'solver-library-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'program', 'cpu_seconds'}:
        return 'solver-library-v1 takes {program, cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    try:
        reps = KP.licensed_reps(domain)
    except (OSError, ValueError, KeyError):
        return 'the representation package cannot be read'
    bad = SL.problems(params['program'], reps)
    return f'the program is not in the language: {bad[:3]}' if bad else None


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    import time
    start = time.process_time()
    from ..invention import representations as R
    from ..invention import solver_library as SL
    rep = next(r for r in R.proposals() if r['id'] == params['program']['rep'])
    budget = min(params['cpu_seconds'], cpu_seconds) - (time.process_time() - start)
    best = SL.run(params['program'], rep, view.n, view.edges, max(0.01, budget), seed)
    return {'selected': [list(e) for e in best], 'value': len(best)}
