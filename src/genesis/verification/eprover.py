"""Pinned E prover wrapper. Outcomes are prover CLAIMS: a proof object is recorded but
not independently replayed, so nothing here reaches THEOREM_CHECKED (which needs Lean)."""
import resource
import subprocess
import tempfile
import time
from pathlib import Path

from ..fol import to_tptp
from .tools import tool

SZS = {'Theorem': 'THEOREM', 'Unsatisfiable': 'THEOREM', 'CounterSatisfiable': 'COUNTERSATISFIABLE',
       'Satisfiable': 'COUNTERSATISFIABLE', 'ResourceOut': 'RESOURCE_OUT', 'GaveUp': 'GAVE_UP'}


def problem_text(axioms, conjecture):
    lines = [f'fof(ax{i}, axiom, {to_tptp(a)}).' for i, a in enumerate(axioms)]
    lines.append(f'fof(goal, conjecture, {to_tptp(conjecture)}).')
    return '\n'.join(lines) + '\n'


def prove(axioms, conjecture, *, seconds=10, memory_mib=2048, mode='auto'):
    """mode: 'auto' (E's single automatic strategy, the B11 setting) or 'schedule' (E's
    strategy schedule on one core)."""
    if mode not in ('auto', 'schedule'):
        raise ValueError(mode)
    e = tool('eprover')
    text = problem_text(axioms, conjecture)
    with tempfile.TemporaryDirectory(prefix='genesis-e-') as d:
        path = Path(d) / 'p.p'; path.write_text(text)
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (int(seconds) + 2, int(seconds) + 3))
            resource.setrlimit(resource.RLIMIT_AS, (memory_mib << 20, memory_mib << 20))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        start = time.monotonic()
        try:
            proc = subprocess.run([e['path'], '--auto' if mode == 'auto' else '--auto-schedule=1', f'--cpu-limit={max(1, int(seconds))}', '-s', '--proof-object',
                                   str(path)], capture_output=True, text=True, timeout=seconds + 15, preexec_fn=limits,
                                  stdin=subprocess.DEVNULL, env={'PATH': '/usr/bin:/bin'})
            out = proc.stdout
        except subprocess.TimeoutExpired:
            out = ''
        elapsed = time.monotonic() - start
    status, proof = _parse(out)
    return {'status': status, 'prover': e['identity'], 'seconds': round(elapsed, 3), 'proof': proof,
            'proof_replayed': False, 'problem': text, 'mode': mode}


def _parse(out):
    """SZS status and proof object. E writes '%% SZS status ResourceOut' (two comment marks)
    when it stops at its own limit; before B20_R1 that line was not matched and a timeout was
    recorded as ERROR (defect B20R-NEW-01). Any run of '#'/'%' marks is accepted now."""
    status = 'ERROR'
    for line in out.splitlines():
        words = line.lstrip('#%').split()
        if line[:1] in '#%' and len(words) >= 3 and words[:2] == ['SZS', 'status']:
            status = SZS.get(words[2], 'ERROR')
            break
    else:
        if not out:
            status = 'RESOURCE_OUT'
    proof = None
    if status == 'THEOREM' and 'SZS output start' in out:
        proof = out[out.index('SZS output start'):]
    return status, proof


def prove_bounded(axioms, conjecture, *, limit_s, cpu_ns, wall_ns, memory_mib=2048, mode='auto', label=None):
    """E under an outer, metered CPU budget (Repair B). ``limit_s`` is E's own whole-second
    limit (from the reservation); ``cpu_ns``/``wall_ns`` are the reservation, enforced on
    every descendant by ``learning.budget.run_bounded``. The result carries the resource
    record; the caller's account decides whether a proof can be credited."""
    from ..learning.budget import run_bounded
    if mode not in ('auto', 'schedule'):
        raise ValueError(mode)
    if type(limit_s) is not int or limit_s < 1:
        raise ValueError('E needs a whole-second limit of at least 1')
    e = tool('eprover')
    text = problem_text(axioms, conjecture)
    with tempfile.TemporaryDirectory(prefix='genesis-e-') as d:
        path = Path(d) / 'p.p'
        path.write_text(text)
        r = run_bounded([e['path'], '--auto' if mode == 'auto' else '--auto-schedule=1', f'--cpu-limit={limit_s}',
                         '-s', '--proof-object', str(path)], cpu_ns=cpu_ns, wall_ns=wall_ns,
                        memory_bytes=memory_mib << 20, label=label)
    status, proof = _parse(r['stdout'])
    if r['termination'] != 'EXITED' and status == 'ERROR':
        status = 'RESOURCE_OUT'
    return {'status': status, 'prover': e['identity'], 'seconds': round(r['wall_ns'] / 1e9, 3), 'proof': proof,
            'proof_replayed': False, 'problem': text, 'mode': mode,
            'resource': {k: r[k] for k in ('termination', 'exit_code', 'cpu_ns', 'wall_ns', 'meter')}}
