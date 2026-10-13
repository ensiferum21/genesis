"""Executable candidate adapters: the trusted-runner side (handoff H05; B19-OPEN-3).

The custodian validates programs as ``SolverProgram`` (the fixed data-only DSL), so B19's
represent-and-repair candidate cannot be evaluated by it. This module is the reviewed
runner that a later, separately reviewed change can wire into the custodian: a CLOSED
registry of candidate kinds, descriptors that the runner rebuilds and checks instead of
trusting, execution in a bounded child process that sees only the candidate view, and a
strict decoder whose output is re-checked by the domain checker.

Kinds (closed; nothing else is accepted):
  dsl-program-v1           the existing fixed DSL (``execution.execute``), unchanged.
  formal-research-successor-v1  (B20_R7) a frozen equational research successor: the system's
                           axioms plus the library of a custody manifest (bound by its id), proving
                           a statement with E under {premise_k, prove_seconds}. The child sees only
                           the statement and the library statements; its output is a proof CLAIM,
                           worth nothing until the evaluator replays it in Lean from custody.
                           Statement domains only (``eq_<system>_v1``); runc isolation only.
  represent-and-repair-v1  ``invention.representations.represent_and_repair`` with
                           data-only parameters {representation, cpu_seconds, seed}. The
                           representation must be a typed grammar proposal whose soundness
                           mode for the task's domain licenses lifting a decoded witness
                           (SUFF or EQ, derived from the committed B18 representation
                           package by ``invention.soundness``). Every C4 decoder is
                           REJECTED there, so C4 tasks are refused for this kind.

Trust level. No candidate source, module name, path, command or pickle is ever accepted:
only reviewed in-repository code runs, with parameters that are data. Two isolation levels:

  isolation='runc'     (required by the custodian, B20_R5) the reviewed child runs in the OCI
                       sandbox (``genesis.sandbox``): no network, read-only root, uid 65534,
                       seccomp, cgroup CPU/memory/pids limits; the reviewed source tree is mounted
                       read-only at /opt/genesis-src and the only input file is the candidate
                       view. The custodian's private root, panels, keys and references are not
                       mounted. Both arms of a v4 evaluation, DSL included, run this way, so they
                       are metered by the same cgroup accounting.
  isolation='process'  (DEV) a child process with rlimits, metered by
                       ``learning.budget.run_bounded``; for the DSL kind, the existing
                       ``execution.execute`` path, unchanged.

Status (B20_R5): wired into the custodian through evaluation request v4 and scientific
receipt v4 (``kernel.receipts``); the custodian rebuilds descriptors from the campaign's
frozen export (``custodian.check_request_against_export``).
"""
import hashlib
import json
from pathlib import Path
import sys

from .common import canonical, digest

SCHEMA = 'genesis-candidate-descriptor-v1'
KINDS = ('dsl-program-v1', 'represent-and-repair-v1', 'formal-research-successor-v1')
PACKAGE = Path(__file__).resolve().parents[2] / 'evidence' / 'invention_b18' / 'representations' / 'package.json'
MAX_OUTPUT = 1 << 20
FIELDS = {'schema', 'kind', 'domain', 'parameters', 'implementation', 'resource_profile', 'descriptor_id'}
PROFILE = {'cpu_seconds', 'memory_mib', 'wall_seconds', 'queries'}
SOURCE_MOUNT = '/opt/genesis-src'
TOOLCHAIN_MOUNT = '/opt/toolchain'      # PINS.json: verification.tools resolves REPO as /opt inside the sandbox
TOOLS_MOUNT = '/opt/tools'              # the pinned binaries (GENESIS_TOOLCHAIN inside the sandbox)
ISOLATIONS = ('runc', 'process')


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
                                         'invention/soundness.py'],
             'formal-research-successor-v1': ['candidates.py', 'learning/equational.py', 'learning/research.py',
                                              'verification/eprover.py', 'verification/tools.py', 'fol.py']}[kind]
    return {f: _sha_file(here / f) for f in files}


def _check_parameters(kind, domain, params):
    from .domains import ADAPTERS
    if not isinstance(params, dict):
        raise CandidateError('MALFORMED_PARAMETERS')
    if kind == 'formal-research-successor-v1':
        from .learning.statement_panels import system_of_domain
        if set(params) != {'system', 'manifest_id', 'premise_k', 'prove_seconds'}:
            raise CandidateError('MALFORMED_PARAMETERS',
                                 'formal-research-successor-v1 takes {system, manifest_id, premise_k, prove_seconds}')
        if system_of_domain(domain) is None:
            raise CandidateError('UNKNOWN_DOMAIN', domain)
        if params['system'] != system_of_domain(domain):
            raise CandidateError('DOMAIN_MISMATCH', 'the successor system is not the domain system')
        m = params['manifest_id']
        if not (isinstance(m, str) and len(m) == 64 and all(c in '0123456789abcdef' for c in m)) or \
                type(params['premise_k']) is not int or not 0 <= params['premise_k'] <= 32 or \
                type(params['prove_seconds']) is not int or not 1 <= params['prove_seconds'] <= 60:
            raise CandidateError('MALFORMED_PARAMETERS')
        return
    if domain not in ADAPTERS:
        raise CandidateError('UNKNOWN_DOMAIN', domain)
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


def _check_profile(rp):
    if not isinstance(rp, dict) or set(rp) != PROFILE:
        raise CandidateError('MALFORMED_RESOURCE_PROFILE', f'expected {sorted(PROFILE)}')
    if type(rp['cpu_seconds']) not in (int, float) or not 0 < rp['cpu_seconds'] <= 60 \
            or type(rp['memory_mib']) is not int or not 256 <= rp['memory_mib'] <= 8192 \
            or type(rp['wall_seconds']) not in (int, float) or not 0 < rp['wall_seconds'] <= 600 \
            or type(rp['queries']) is not int or not 1 <= rp['queries'] <= 100000:
        raise CandidateError('MALFORMED_RESOURCE_PROFILE')


def build_descriptor(kind, domain, parameters, *, cpu_seconds, memory_mib=2048, wall_seconds=None, queries=60):
    """The descriptor a trusted party builds from frozen data (never from request facts).

    ``queries`` caps the DSL interpreter's oracle queries (the represent-and-repair kind has no
    query notion; it is bounded by CPU). Arms of one evaluation must share the whole profile."""
    if kind not in KINDS:
        raise CandidateError('UNKNOWN_KIND', str(kind))
    _check_parameters(kind, domain, parameters)
    rp = {'cpu_seconds': cpu_seconds, 'memory_mib': memory_mib,
          'wall_seconds': wall_seconds or max(10, 4 * cpu_seconds), 'queries': queries}
    _check_profile(rp)
    body = {'schema': SCHEMA, 'kind': kind, 'domain': domain, 'parameters': json.loads(canonical(parameters)),
            'implementation': implementation_identity(kind), 'resource_profile': rp}
    return dict(body, descriptor_id=digest(body))


def rebuild(desc):
    """The descriptor rebuilt from its data fields by this (reviewed) code; raises CandidateError."""
    if not isinstance(desc, dict) or set(desc) != FIELDS or desc.get('schema') != SCHEMA:
        raise CandidateError('MALFORMED_DESCRIPTOR')
    rp = desc['resource_profile']
    _check_profile(rp)
    return build_descriptor(desc['kind'], desc['domain'], desc['parameters'], **rp)


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
    try:
        _check_profile(desc['resource_profile'])
    except CandidateError as exc:
        out.append(exc.code)
    return out


def child_request(task, desc, seed):
    """Exactly what the child receives: the candidate view, the parameters and limits."""
    from .domains import adapter
    view = adapter(task.domain).candidate_view(task)
    return {'view': view.model_dump(mode='json'), 'kind': desc['kind'], 'parameters': desc['parameters'],
            'cpu_seconds': desc['resource_profile']['cpu_seconds'], 'queries': desc['resource_profile']['queries'],
            'seed': seed}


def sandbox_policy(rp):
    """The OCI sandbox policy for one arm with resource profile ``rp`` (same for every arm)."""
    import math
    from .sandbox import SandboxPolicy
    return SandboxPolicy(wall_seconds=rp['wall_seconds'], cpu_seconds=int(math.ceil(rp['cpu_seconds'])) + 1,
                         memory_mib=rp['memory_mib'], address_space_mib=rp['memory_mib'], pids=16,
                         output_bytes=MAX_OUTPUT + 1, work_mib=1, tmp_mib=16, open_files=128, max_file_mib=1)


def sandbox_mounts(kind=None):
    """Read-only mounts: the reviewed source tree; for the formal kind also the pin file and the
    pinned prover (``verification.tools`` re-checks the binary hash inside the sandbox)."""
    mounts = {SOURCE_MOUNT: str(Path(__file__).resolve().parents[1])}
    if kind == 'formal-research-successor-v1':
        from .verification.tools import toolchain_root
        mounts[TOOLCHAIN_MOUNT] = str(Path(__file__).resolve().parents[2] / 'toolchain')
        mounts[TOOLS_MOUNT] = str(toolchain_root())
    return mounts


CHILD_ARGV = ('-s', '-B', '-m', 'genesis.candidates', '--trusted-candidate-child', '/work/src/request.json')
SANDBOX_STATUS = {'TIMEOUT': 'TIMEOUT', 'CPU_LIMIT': 'CPU_LIMIT', 'OOM': 'MEMORY_LIMIT', 'OUTPUT_LIMIT': 'OUTPUT_LIMIT',
                  'EXIT_NONZERO': 'EXECUTION_ERROR'}


def _run_sandboxed(req, rp):
    from . import sandbox as S
    env = {'PYTHONPATH': SOURCE_MOUNT, 'PYTHONHASHSEED': '0'}
    if req['kind'] == 'formal-research-successor-v1':
        env['GENESIS_TOOLCHAIN'] = TOOLS_MOUNT
    r = S.run({'request.json': canonical(req)}, [S.PYTHON, *CHILD_ARGV], sandbox_policy(rp),
              ro_mounts=sandbox_mounts(req['kind']), env=env)
    meter = {'cpu_ns': r.get('cpu_ns'), 'wall_ns': r.get('wall_ns'), 'peak_memory_bytes': r.get('peak_memory_bytes'),
             'meter': 'cgroup', 'isolation': r.get('sandbox'), 'policy_sha256': r.get('policy_sha256'),
             'config_sha256': r.get('config_sha256'), 'sandbox_status': r['status']}
    if r['status'] == 'SUCCESS':
        return meter, None, r['stdout']
    status = SANDBOX_STATUS.get(r['status'], 'HARNESS_ERROR')
    return meter, dict(status=status, stderr_tail=(r.get('stderr') or r.get('reason') or '')[-500:]), None


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


def run(task, desc, *, seed, expected_id=None, isolation='process', context=None):
    """Execute a frozen candidate on one task. Returns a receipt; the claimed value is never
    trusted: the domain checker recomputes it from the witness (for the formal kind the
    evaluator replays the claimed proof; see ``run_formal``)."""
    from .domains import Unsupported, adapter
    from .learning.budget import NS, run_bounded
    if isolation not in ISOLATIONS:
        raise ValueError(f'isolation must be one of {ISOLATIONS}')
    if isinstance(desc, dict) and desc.get('kind') == 'formal-research-successor-v1':
        return run_formal(task, desc, seed=seed, expected_id=expected_id, isolation=isolation, context=context)
    problems = descriptor_problems(desc, expected_id=expected_id, domain=task.domain)
    base = {'descriptor_id': desc.get('descriptor_id') if isinstance(desc, dict) else None,
            'execution_mode': 'TRUSTED_REGISTERED_RUNNER', 'arbitrary_code_sandbox': False}
    if problems:
        return dict(base, status='REFUSED', problems=problems)
    domain = adapter(task.domain)
    gate = domain if isinstance(domain, Unsupported) else domain.supports(task, 'execute')
    if gate:
        return dict(base, status='UNSUPPORTED', reason=gate.reason)
    if isolation == 'runc':
        req = child_request(task, desc, seed)
        meter, failure, stdout = _run_sandboxed(req, desc['resource_profile'])
        receipt = dict(base, **meter, candidate_view_sha256=digest(req['view']), runner_sha256=_sha_file(__file__),
                       limits=desc['resource_profile'])
        if failure:
            return dict(receipt, **failure)
        return _decode_and_check(receipt, stdout, task, domain)
    if desc['kind'] == 'dsl-program-v1':
        from .execution import execute
        from .models import Limits, SolverProgram
        rp = desc['resource_profile']
        limits = Limits(cpu_seconds=max(1, int(rp['cpu_seconds'])), memory_mib=rp['memory_mib'],
                        wall_seconds=int(rp['wall_seconds']), queries=rp['queries'])
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
    return _decode_and_check(dict(receipt, isolation='PROCESS_RLIMITS'), r['stdout'], task, domain)


FORMAL_STATUSES = ('THEOREM', 'COUNTERSATISFIABLE', 'RESOURCE_OUT', 'GAVE_UP', 'ERROR', 'UNKNOWN')   # eprover.SZS


def formal_child_request(task, desc, manifest, seed):
    """Exactly what the formal child receives: the statement, the library statements (in manifest
    order, with their custody uids), the parameters and limits. No task id, stratum or panel."""
    return {'view': {'domain': task['domain'], 'statement': task['statement']}, 'kind': desc['kind'],
            'parameters': desc['parameters'],
            'library': [{'uid': l['uid'], 'statement': l['statement']} for l in manifest['lemmas']],
            'cpu_seconds': desc['resource_profile']['cpu_seconds'], 'queries': desc['resource_profile']['queries'],
            'seed': seed}


def decode_formal_output(raw, library_uids):
    """Strict decoder for the formal child's output: {status, proof, premise_uids}."""
    if len(raw) > MAX_OUTPUT:
        raise CandidateError('OUTPUT_TOO_LARGE')
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        raise CandidateError('MALFORMED_OUTPUT', 'not JSON') from None
    if not isinstance(obj, dict) or set(obj) != {'status', 'proof', 'premise_uids'}:
        raise CandidateError('MALFORMED_OUTPUT', 'expected exactly {status, proof, premise_uids}')
    if obj['status'] not in FORMAL_STATUSES or not (obj['proof'] is None or isinstance(obj['proof'], str)) or \
            not isinstance(obj['premise_uids'], list) or not all(u in library_uids for u in obj['premise_uids']) or \
            len(set(obj['premise_uids'])) != len(obj['premise_uids']):
        raise CandidateError('MALFORMED_OUTPUT')
    if (obj['status'] == 'THEOREM') != bool(obj['proof']):
        raise CandidateError('MALFORMED_OUTPUT', 'a proof object exactly when the status is THEOREM')
    return obj


def run_formal(task, desc, *, seed, expected_id=None, isolation='runc', context=None):
    """Run a frozen formal-research successor on one statement task {task_id, statement, domain}.
    ``context['manifest']`` is the successor manifest the custodian rebuilt from the export.
    Returns a receipt whose result is a CLAIM (a proof object with its premise uids, or no proof);
    the value is decided by the evaluator's Lean replay, not here."""
    base = {'descriptor_id': desc.get('descriptor_id') if isinstance(desc, dict) else None,
            'execution_mode': 'TRUSTED_REGISTERED_RUNNER', 'arbitrary_code_sandbox': False}
    problems = descriptor_problems(desc, expected_id=expected_id, domain=task.get('domain'))
    manifest = (context or {}).get('manifest')
    if not problems and (not isinstance(manifest, dict) or manifest.get('manifest_id') != desc['parameters']['manifest_id']
                         or manifest.get('system') != desc['parameters']['system']):
        problems = ['MANIFEST_MISMATCH']
    if not problems and isolation != 'runc':
        problems = ['ISOLATION_REQUIRED']
    if problems:
        return dict(base, status='REFUSED', problems=problems)
    req = formal_child_request(task, desc, manifest, seed)
    meter, failure, stdout = _run_sandboxed(req, desc['resource_profile'])
    receipt = dict(base, **meter, candidate_view_sha256=digest(req['view']), runner_sha256=_sha_file(__file__),
                   limits=desc['resource_profile'], library_sha256=digest(req['library']))
    if failure:
        return dict(receipt, **failure)
    try:
        out = decode_formal_output(stdout, {l['uid'] for l in req['library']})
    except CandidateError as exc:
        return dict(receipt, status='CHECKER_ERROR', reason=exc.code)
    claim = 'PROOF' if out['status'] == 'THEOREM' else 'NO_PROOF'
    return dict(receipt, status='SUCCESS', result={'claim': claim, 'prover_status': out['status'], 'proof': out['proof'],
                                                   'premise_uids': out['premise_uids']})


def _decode_and_check(receipt, stdout, task, domain):
    try:
        edges, claimed = decode_output(stdout, len(task.edges))
    except CandidateError as exc:
        return dict(receipt, status='CHECKER_ERROR', reason=exc.code)
    checked = domain.validate(task, edges)
    if checked['status'] != 'VALID' or checked['value'] != claimed:
        return dict(receipt, status='CHECKER_ERROR', reason='witness invalid or claimed value differs', check=checked)
    return dict(receipt, status='SUCCESS', result={'selected': [list(e) for e in edges], 'value': claimed},
                check=checked)


def _formal_child(req):
    # The sandbox policy already caps file size (1 MiB) and processes (cgroup pids); E needs both.
    from .fol import parse
    from .learning import equational as Q
    from .learning.research import premises
    from .verification.eprover import prove

    def eq(text):                     # as written (no renaming or orientation): replay binds these texts
        f = parse(text)
        while f[0] == 'all':
            f = f[2]
        return (f[1], f[2])
    params = req['parameters']
    target = eq(req['view']['statement'])
    library = [{'id': l['uid'], 'uid': l['uid'], 'eq': eq(l['statement'])} for l in req['library']]
    prem = premises(library, target, params['premise_k'])
    r = prove(Q.axioms(params['system']) + [Q.closed(p['eq']) for p in prem], Q.closed(target),
              seconds=min(params['prove_seconds'], int(req['cpu_seconds'])), mode='auto')
    proof = r['proof'] if r['status'] == 'THEOREM' and r.get('proof') else None
    sys.stdout.write(json.dumps({'status': r['status'] if (r['status'] != 'THEOREM' or proof) else 'UNKNOWN',
                                 'proof': proof, 'premise_uids': [p['uid'] for p in prem]}))


def _child(path):
    import resource
    req = json.loads(Path(path).read_bytes())
    if req.get('kind') == 'formal-research-successor-v1':
        if set(req) != {'view', 'kind', 'parameters', 'library', 'cpu_seconds', 'queries', 'seed'}:
            raise SystemExit(2)
        return _formal_child(req)
    if set(req) != {'view', 'kind', 'parameters', 'cpu_seconds', 'queries', 'seed'} or req['kind'] not in KINDS:
        raise SystemExit(2)
    from .models import CandidateGraph
    view = CandidateGraph.model_validate_json(canonical(req['view']))      # no task id, family, split or reference
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    if hasattr(resource, 'RLIMIT_NPROC'):
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    if req['kind'] == 'dsl-program-v1':
        from .dsl import solve
        from .models import SolverProgram
        out = solve(view, SolverProgram.model_validate_json(canonical(req['parameters']['program'])),
                    req['queries'], req['seed'])
        sys.stdout.write(json.dumps({'selected': [list(e) for e in out['selected']], 'value': out['value']}))
        return
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


__all__ = ['SCHEMA', 'KINDS', 'CandidateError', 'build_descriptor', 'rebuild', 'descriptor_problems', 'child_request',
           'decode_output', 'run', 'implementation_identity', 'representation_mode', 'sandbox_policy',
           'sandbox_mounts', 'ISOLATIONS', 'run_formal', 'formal_child_request', 'decode_formal_output']
