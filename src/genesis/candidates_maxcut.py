"""The runner for the DEV-only max-cut domain (B20_R101): registry v2's discipline for weighted max-cut.

As `candidates_large` for the large triangle-free domain, under its own schema and identity, so that no existing
descriptor changes:
  * descriptors with schema `genesis-candidate-descriptor-maxcut-v1`, the v2 fields, and an implementation identity of
    this file, `candidates_v2.py` (whose helpers it uses), `graphs_maxcut.py`, `models_maxcut.py` and the kind's files;
  * only the kinds of the closed kind map whose module declares the max-cut domain (`is_maxcut_kind`; since
    B20_R104 derived rather than listed here, so that adding a kind leaves every max-cut identity unchanged, as
    B20_R67 did for registry v2);
  * a bounded child (runc with the cgroup meter, or rlimits for DEV) that sees only the `MaxCutCandidateView`, the data
    parameters and the limits; strict output decoding ({side, value}); the domain's two computations re-check every
    cut, and a claimed value that differs from the checked one fails the run.
Not wired into the custodian, requests or receipts: DEV studies only.
"""
import hashlib
import json
from pathlib import Path
import sys

from .common import canonical, digest
from . import candidates_v2 as V2

SCHEMA = 'genesis-candidate-descriptor-maxcut-v1'
DOMAIN = 'maxcut_v1'
CORE_FILES = ('candidates_maxcut.py', 'candidates_v2.py', 'graphs_maxcut.py', 'models_maxcut.py')
MAX_OUTPUT = 1 << 20
CHILD_ARGV = ('-s', '-B', '-m', 'genesis.candidates_maxcut', '--trusted-candidate-child', '/work/src/request.json')


def is_maxcut_kind(kind):
    return isinstance(kind, str) and kind in V2.KINDS and DOMAIN in getattr(V2._kind(kind), 'DOMAINS', ())


def maxcut_kinds():
    return tuple(k for k in V2.KINDS if is_maxcut_kind(k))


def implementation_identity(kind):
    if not is_maxcut_kind(kind):
        raise V2.CandidateError('UNKNOWN_KIND', f'{kind} is not a max-cut kind')
    mod = V2._kind(kind)
    own = f'candidate_kinds/{V2.KINDS[kind]}.py'
    if not mod.FILES or mod.FILES[0] != own:
        raise V2.CandidateError('MALFORMED_KIND', f'{kind}: the first declared file must be its own module, {own}')
    here = V2._here()
    return {f: hashlib.sha256((here / f).read_bytes()).hexdigest() for f in list(CORE_FILES) + list(mod.FILES)}


def _check_profile(rp):
    if set(rp) != V2.PROFILE or type(rp['queries']) is not int or type(rp['memory_mib']) is not int:
        raise V2.CandidateError('MALFORMED_PROFILE')
    if not 0 < rp['cpu_seconds'] <= 600 or not 0 < rp['wall_seconds'] <= 3600 or not 256 <= rp['memory_mib'] <= 8192:
        raise V2.CandidateError('MALFORMED_PROFILE')


def build_descriptor(kind, parameters, *, cpu_seconds, memory_mib=2048, wall_seconds=None, queries=60):
    if not is_maxcut_kind(kind):
        raise V2.CandidateError('UNKNOWN_KIND', f'{kind} is not a max-cut kind')
    why = V2._kind(kind).check_parameters(DOMAIN, parameters)
    if why:
        raise V2.CandidateError('MALFORMED_PARAMETERS', why)
    rp = {'cpu_seconds': cpu_seconds, 'memory_mib': memory_mib,
          'wall_seconds': wall_seconds if wall_seconds is not None else max(30, int(cpu_seconds * 3)),
          'queries': queries}
    _check_profile(rp)
    body = {'schema': SCHEMA, 'kind': kind, 'domain': DOMAIN, 'parameters': json.loads(canonical(parameters)),
            'implementation': implementation_identity(kind), 'resource_profile': rp}
    return dict(body, descriptor_id=digest(body))


def descriptor_problems(desc, *, expected_id=None):
    if not isinstance(desc, dict) or set(desc) != V2.FIELDS or desc.get('schema') != SCHEMA:
        return ['not a max-cut candidate descriptor']
    if not is_maxcut_kind(desc['kind']):
        return [f'unknown kind {desc["kind"]!r}']
    out = []
    body = {k: desc[k] for k in V2.FIELDS - {'descriptor_id'}}
    if digest(body) != desc['descriptor_id']:
        out.append('descriptor_id does not match the descriptor')
    if desc['implementation'] != implementation_identity(desc['kind']):
        out.append('implementation identity differs from this code')
    if desc['domain'] != DOMAIN:
        out.append('descriptor domain is not the max-cut domain')
    why = V2._kind(desc['kind']).check_parameters(desc['domain'], desc['parameters'])
    if why:
        out.append(why)
    try:
        _check_profile(desc['resource_profile'])
    except V2.CandidateError as exc:
        out.append(exc.code)
    if expected_id is not None and desc['descriptor_id'] != expected_id:
        out.append('descriptor is not the expected one')
    return out


def _policy(rp):
    import math
    from .sandbox import SandboxPolicy
    return SandboxPolicy(wall_seconds=rp['wall_seconds'], cpu_seconds=int(math.ceil(rp['cpu_seconds'])) + 1,
                         memory_mib=rp['memory_mib'], address_space_mib=rp['memory_mib'], pids=16,
                         output_bytes=MAX_OUTPUT + 1, work_mib=32, tmp_mib=64, open_files=128, max_file_mib=16)


def _decode(raw, n):
    if len(raw) > MAX_OUTPUT:
        raise V2.CandidateError('OUTPUT_TOO_LARGE')
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        raise V2.CandidateError('MALFORMED_OUTPUT', 'not JSON') from None
    if not isinstance(obj, dict) or set(obj) != {'side', 'value'}:
        raise V2.CandidateError('MALFORMED_OUTPUT', 'expected exactly {side, value}')
    if not isinstance(obj['side'], str) or len(obj['side']) != n or type(obj['value']) is not int:
        raise V2.CandidateError('MALFORMED_OUTPUT', 'side must be a string of n characters, value an int')
    return obj['side'], obj['value']


def run(task, desc, *, seed, expected_id=None, isolation='runc'):
    """Execute a max-cut candidate on one task; the claimed value is never trusted."""
    from .domains import adapter
    from .models_maxcut import MaxCutTask
    if isolation not in V2.ISOLATIONS:
        raise ValueError(f'isolation must be one of {V2.ISOLATIONS}')
    base = {'descriptor_id': desc.get('descriptor_id') if isinstance(desc, dict) else None, 'registry': SCHEMA,
            'execution_mode': 'TRUSTED_REGISTERED_RUNNER', 'arbitrary_code_sandbox': False}
    if not isinstance(task, MaxCutTask):
        return dict(base, status='UNSUPPORTED', reason='not a max-cut task')
    problems = descriptor_problems(desc, expected_id=expected_id)
    if problems:
        return dict(base, status='REFUSED', problems=problems)
    domain = adapter(DOMAIN)
    gate = domain.supports(task, 'execute')
    if gate:
        return dict(base, status='UNSUPPORTED', reason=gate.reason)
    view = domain.candidate_view(task)
    rp = desc['resource_profile']
    req = {'view': view.model_dump(mode='json'), 'kind': desc['kind'], 'parameters': desc['parameters'],
           'cpu_seconds': rp['cpu_seconds'], 'queries': rp['queries'], 'seed': seed}
    runner = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if isolation == 'runc':
        from . import sandbox as S
        r = S.run({'request.json': canonical(req)}, [S.PYTHON, *CHILD_ARGV], _policy(rp),
                  ro_mounts={V2.SOURCE_MOUNT: str(V2._here().parent)},
                  env={'PYTHONPATH': V2.SOURCE_MOUNT, 'PYTHONHASHSEED': '0'})
        receipt = dict(base, cpu_ns=r.get('cpu_ns'), wall_ns=r.get('wall_ns'), peak_memory_bytes=r.get('peak_memory_bytes'),
                       meter='cgroup', isolation=r.get('sandbox'), sandbox_status=r['status'],
                       candidate_view_sha256=digest(req['view']), runner_sha256=runner, limits=rp)
        if r['status'] != 'SUCCESS':
            return dict(receipt, status=V2.SANDBOX_STATUS.get(r['status'], 'HARNESS_ERROR'),
                        stderr_tail=(r.get('stderr') or r.get('reason') or '')[-500:])
        stdout = r['stdout']
    else:
        import os
        import tempfile
        from .learning.budget import NS, run_bounded
        with tempfile.NamedTemporaryFile(prefix='genesis-maxcut-', suffix='.json', delete=False) as f:
            f.write(canonical(req))
            path = f.name
        try:
            os.chmod(path, 0o444)
            env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(V2._here().parent), 'PYTHONHASHSEED': '0',
                   'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'}
            if sys.pycache_prefix:
                env['PYTHONPYCACHEPREFIX'] = sys.pycache_prefix
            r = run_bounded([sys.executable, '-s', '-m', 'genesis.candidates_maxcut', '--trusted-candidate-child', path],
                            cpu_ns=int((rp['cpu_seconds'] + 1.0) * NS), wall_ns=int(rp['wall_seconds'] * NS),
                            memory_bytes=rp['memory_mib'] << 20, env=env, cwd='/', output_cap=MAX_OUTPUT + 1)
        finally:
            os.unlink(path)
        receipt = dict(base, cpu_ns=r['cpu_ns'], wall_ns=r['wall_ns'], meter=r['meter'], termination=r['termination'],
                       exit_code=r['exit_code'], candidate_view_sha256=digest(req['view']), runner_sha256=runner,
                       isolation='PROCESS_RLIMITS')
        if r['termination'] != 'EXITED' or r['exit_code'] != 0:
            status = {'CPU_BUDGET_KILLED': 'CPU_LIMIT', 'WALL_KILLED': 'TIMEOUT', 'RLIMIT_KILLED': 'CPU_LIMIT'}.get(
                r['termination'], 'EXECUTION_ERROR')
            return dict(receipt, status=status, stderr_tail=r['stderr'][-500:])
        stdout = r['stdout']
    try:
        side, claimed = _decode(stdout, task.n)
    except V2.CandidateError as exc:
        return dict(receipt, status='CHECKER_ERROR', reason=exc.code)
    checked = domain.validate(task, side)
    if checked['status'] != 'VALID' or checked['value'] != claimed:
        return dict(receipt, status='CHECKER_ERROR', reason='cut invalid or claimed value differs', check=checked)
    return dict(receipt, status='SUCCESS', result={'side': side, 'value': claimed}, check=checked)


def _child(path):
    import resource
    req = json.loads(Path(path).read_bytes())
    if set(req) != {'view', 'kind', 'parameters', 'cpu_seconds', 'queries', 'seed'} or \
            not is_maxcut_kind(req['kind']):
        raise SystemExit(2)
    from .models_maxcut import MaxCutCandidateView
    view = MaxCutCandidateView.model_validate_json(canonical(req['view']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    out = V2._kind(req['kind']).solve(view, req['parameters'], req['cpu_seconds'], req['seed'])
    sys.stdout.write(json.dumps(out))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--trusted-candidate-child':
        _child(sys.argv[2])
    else:
        raise SystemExit('usage: python -m genesis.candidates_maxcut --trusted-candidate-child REQUEST')
