"""Executable candidate adapters: the trusted-runner side (handoff H05; B19-OPEN-3).

The custodian validates programs as ``SolverProgram`` (the fixed data-only DSL), so B19's
represent-and-repair candidate cannot be evaluated by it. This module is the reviewed
runner that a later, separately reviewed change can wire into the custodian: a CLOSED
registry of candidate kinds, descriptors that the runner rebuilds and checks instead of
trusting, execution in a bounded child process that sees only the candidate view, and a
strict decoder whose output is re-checked by the domain checker.

Kinds (closed; nothing else is accepted):
  dsl-program-v1           the existing fixed DSL (``execution.execute``), unchanged.
  represent-and-repair-v1  ``invention.representations.represent_and_repair`` with
                           data-only parameters {representation, cpu_seconds, seed}. The
                           representation must be a typed grammar proposal whose soundness
                           mode for the task's domain licenses lifting a decoded witness
                           (SUFF or EQ, derived from the committed B18 representation
                           package by ``invention.soundness``). Every C4 decoder is
                           REJECTED there, so C4 tasks are refused for this kind.

Trust level. Like the DSL runner this is NOT an arbitrary-code sandbox: no candidate source,
module name, path, command or pickle is ever accepted. Only reviewed in-repository code runs,
with parameters that are data. The child has rlimits (CPU, address space, no files, no
processes), a minimal environment, and the parent meters and kills it through
``learning.budget.run_bounded``. Arbitrary generated code still needs the container sandbox.

Status: engineering only. ``custodian.UNSUPPORTED_KINDS`` and request validation are
unchanged; the signed request/receipt schemas do not yet carry a candidate descriptor (a
reviewed schema extension is required, handoff s12.1).
"""
import hashlib
import json
from pathlib import Path
import sys

from .common import canonical, digest

SCHEMA = 'genesis-candidate-descriptor-v1'
KINDS = ('dsl-program-v1', 'represent-and-repair-v1')
PACKAGE = Path(__file__).resolve().parents[2] / 'evidence' / 'invention_b18' / 'representations' / 'package.json'
MAX_OUTPUT = 1 << 20
FIELDS = {'schema', 'kind', 'domain', 'parameters', 'implementation', 'resource_profile', 'descriptor_id'}


class CandidateError(ValueError):
    def __init__(self, code, detail=''):
        self.code = code
        super().__init__(f'{code}: {detail}' if detail else code)


def _sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def implementation_identity(kind):
    """Digests of the reviewed source files a kind runs (part of the descriptor identity)."""
    here = Path(__file__).resolve().parent
    files = {'dsl-program-v1': ['dsl.py', 'execution.py', 'graphs.py', 'models.py'],
             'represent-and-repair-v1': ['candidates.py', 'invention/representations.py', 'graphs.py', 'models.py',
                                         'invention/soundness.py']}[kind]
    return {f: _sha_file(here / f) for f in files}


def _check_parameters(kind, domain, params):
    from .domains import ADAPTERS
    if domain not in ADAPTERS:
        raise CandidateError('UNKNOWN_DOMAIN', domain)
    if not isinstance(params, dict):
        raise CandidateError('MALFORMED_PARAMETERS')
    if kind == 'dsl-program-v1':
        from .models import SolverProgram
        if set(params) != {'program'}:
            raise CandidateError('MALFORMED_PARAMETERS', 'dsl-program-v1 takes {program}')
        SolverProgram.model_validate_json(canonical(params['program']))
        return
    if set(params) != {'representation', 'cpu_seconds', 'seed'}:
        raise CandidateError('MALFORMED_PARAMETERS', 'represent-and-repair-v1 takes {representation, cpu_seconds, seed}')
    if type(params['representation']) is not str or type(params['seed']) is not int or \
            type(params['cpu_seconds']) not in (int, float) or not 0 < params['cpu_seconds'] <= 60:
        raise CandidateError('MALFORMED_PARAMETERS')
    mode = representation_mode(params['representation'], domain)
    if mode not in ('SUFF', 'EQ'):
        raise CandidateError('REPRESENTATION_NOT_LICENSED',
                             f'{params["representation"]} on {domain} has soundness mode {mode}')


def representation_mode(rep_id, domain):
    from .invention import soundness as S
    modes = S.representation_modes(json.loads(PACKAGE.read_text()))
    rec = modes.get((rep_id, domain))
    if rec is None:
        raise CandidateError('UNKNOWN_REPRESENTATION', rep_id)
    return rec['established'] if not S.problems(rec, 'lift_positive') else (
        'REJECTED' if rec['established'] == 'REJECTED' else rec['established'] + '_NOT_LIFTING')


def build_descriptor(kind, domain, parameters, *, cpu_seconds, memory_mib=2048, wall_seconds=None):
    """The descriptor a trusted party builds from frozen data (never from request facts)."""
    if kind not in KINDS:
        raise CandidateError('UNKNOWN_KIND', str(kind))
    _check_parameters(kind, domain, parameters)
    body = {'schema': SCHEMA, 'kind': kind, 'domain': domain, 'parameters': json.loads(canonical(parameters)),
            'implementation': implementation_identity(kind),
            'resource_profile': {'cpu_seconds': cpu_seconds, 'memory_mib': memory_mib,
                                 'wall_seconds': wall_seconds or max(10, 4 * cpu_seconds)}}
    return dict(body, descriptor_id=digest(body))


def descriptor_problems(desc, *, expected_id=None, domain=None):
    """Rebuild and compare; returns stable problem codes (empty: usable)."""
    out = []
    if not isinstance(desc, dict) or set(desc) != FIELDS or desc.get('schema') != SCHEMA:
        return ['MALFORMED_DESCRIPTOR']
    if desc['kind'] not in KINDS:
        return ['UNKNOWN_KIND']
    if digest({k: v for k, v in desc.items() if k != 'descriptor_id'}) != desc['descriptor_id']:
        out.append('DESCRIPTOR_ID_MISMATCH')
    if expected_id is not None and desc['descriptor_id'] != expected_id:
        out.append('NOT_THE_FROZEN_CANDIDATE')
    if domain is not None and desc['domain'] != domain:
        out.append('DOMAIN_MISMATCH')
    if desc['implementation'] != implementation_identity(desc['kind']):
        out.append('IMPLEMENTATION_CHANGED')
    try:
        _check_parameters(desc['kind'], desc['domain'], desc['parameters'])
    except CandidateError as exc:
        out.append(exc.code)
    except Exception:
        out.append('MALFORMED_PARAMETERS')
    return out


def child_request(task, desc, seed):
    """Exactly what the child receives: the candidate view, the parameters and limits."""
    from .domains import adapter
    view = adapter(task.domain).candidate_view(task)
    return {'view': view.model_dump(mode='json'), 'kind': desc['kind'], 'parameters': desc['parameters'],
            'cpu_seconds': desc['resource_profile']['cpu_seconds'], 'seed': seed}


def decode_output(raw, n_edges):
    """Strict decoder for candidate output. Returns the witness edge list or raises."""
    if len(raw) > MAX_OUTPUT:
        raise CandidateError('OUTPUT_TOO_LARGE')
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        raise CandidateError('MALFORMED_OUTPUT', 'not JSON') from None
    if not isinstance(obj, dict) or set(obj) != {'selected', 'value'}:
        raise CandidateError('MALFORMED_OUTPUT', 'expected exactly {selected, value}')
    sel, val = obj['selected'], obj['value']
    if not isinstance(sel, list) or len(sel) > n_edges or type(val) is not int:
        raise CandidateError('MALFORMED_OUTPUT', 'selected must be a list no longer than the host, value an int')
    edges = []
    for e in sel:
        if not isinstance(e, list) or len(e) != 2 or any(type(x) is not int for x in e):
            raise CandidateError('MALFORMED_OUTPUT', 'edges are pairs of ints')
        edges.append((e[0], e[1]))
    return edges, val


def run(task, desc, *, seed, expected_id=None):
    """Execute a frozen candidate on one task. Returns a receipt; the claimed value is never
    trusted: the domain checker recomputes it from the witness."""
    from .domains import Unsupported, adapter
    from .learning.budget import NS, run_bounded
    problems = descriptor_problems(desc, expected_id=expected_id, domain=task.domain)
    base = {'descriptor_id': desc.get('descriptor_id') if isinstance(desc, dict) else None,
            'execution_mode': 'TRUSTED_REGISTERED_RUNNER', 'arbitrary_code_sandbox': False}
    if problems:
        return dict(base, status='REFUSED', problems=problems)
    domain = adapter(task.domain)
    gate = domain if isinstance(domain, Unsupported) else domain.supports(task, 'execute')
    if gate:
        return dict(base, status='UNSUPPORTED', reason=gate.reason)
    if desc['kind'] == 'dsl-program-v1':
        from .execution import execute
        from .models import Limits, SolverProgram
        rp = desc['resource_profile']
        limits = Limits(cpu_seconds=max(1, int(rp['cpu_seconds'])), memory_mib=rp['memory_mib'],
                        wall_seconds=int(rp['wall_seconds']))
        return dict(execute(task, SolverProgram.model_validate_json(canonical(desc['parameters']['program'])),
                            limits, seed), **base)
    req = child_request(task, desc, seed)
    data = canonical(req)
    rp = desc['resource_profile']
    import os
    import tempfile
    with tempfile.NamedTemporaryFile(prefix='genesis-cand-', suffix='.json', delete=False) as f:
        f.write(data)
        path = f.name
    try:
        os.chmod(path, 0o444)
        env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(Path(__file__).resolve().parents[1]), 'PYTHONHASHSEED': '0',
               'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'}
        if sys.pycache_prefix:
            env['PYTHONPYCACHEPREFIX'] = sys.pycache_prefix
        # Like the DSL runner: minimal environment, no user site, cwd '/' (nothing importable from cwd).
        r = run_bounded([sys.executable, '-s', '-m', 'genesis.candidates', '--trusted-candidate-child', path],
                        cpu_ns=int((rp['cpu_seconds'] + 1.0) * NS), wall_ns=int(rp['wall_seconds'] * NS),
                        memory_bytes=rp['memory_mib'] << 20, env=env, cwd='/', output_cap=MAX_OUTPUT + 1)
    finally:
        os.unlink(path)
    receipt = dict(base, cpu_ns=r['cpu_ns'], wall_ns=r['wall_ns'], meter=r['meter'], termination=r['termination'],
                   exit_code=r['exit_code'], candidate_view_sha256=digest(req['view']),
                   runner_sha256=_sha_file(__file__))
    if r['termination'] != 'EXITED' or r['exit_code'] != 0:
        status = {'CPU_BUDGET_KILLED': 'CPU_LIMIT', 'WALL_KILLED': 'TIMEOUT', 'RLIMIT_KILLED': 'CPU_LIMIT'}.get(
            r['termination'], 'EXECUTION_ERROR')
        return dict(receipt, status=status, stderr_tail=r['stderr'][-500:])
    try:
        edges, claimed = decode_output(r['stdout'], len(task.edges))
    except CandidateError as exc:
        return dict(receipt, status='CHECKER_ERROR', reason=exc.code)
    checked = domain.validate(task, edges)
    if checked['status'] != 'VALID' or checked['value'] != claimed:
        return dict(receipt, status='CHECKER_ERROR', reason='witness invalid or claimed value differs', check=checked)
    return dict(receipt, status='SUCCESS', result={'selected': [list(e) for e in edges], 'value': claimed},
                check=checked)


def _child(path):
    import resource
    req = json.loads(Path(path).read_bytes())
    if set(req) != {'view', 'kind', 'parameters', 'cpu_seconds', 'seed'} or req['kind'] != 'represent-and-repair-v1':
        raise SystemExit(2)
    from .models import CandidateGraph
    view = CandidateGraph.model_validate_json(canonical(req['view']))      # no task id, family, split or reference
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    if hasattr(resource, 'RLIMIT_NPROC'):
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    from .invention import representations as R
    rep = next(r for r in R.proposals() if r['id'] == req['parameters']['representation'])
    motif_ok = {'triangle_free_host_v1': R.tf_add_ok}[view.domain]
    out = R.represent_and_repair(view.n, view.edges, rep, motif_ok, cpu_seconds=min(req['parameters']['cpu_seconds'],
                                                                                     req['cpu_seconds']),
                                 seed=req['parameters']['seed'] ^ req['seed'])
    sys.stdout.write(json.dumps({'selected': [list(e) for e in out['witness']], 'value': out['value']}))


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--trusted-candidate-child':
        raise SystemExit('internal trusted candidate runner only')
    _child(sys.argv[2])


__all__ = ['SCHEMA', 'KINDS', 'CandidateError', 'build_descriptor', 'descriptor_problems', 'child_request',
           'decode_output', 'run', 'implementation_identity', 'representation_mode']
