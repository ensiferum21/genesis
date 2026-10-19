"""Candidate registry v2: kinds with their own implementation identity (B20_R40; built, not wired).

**The problem it solves (NEXT_ACTIONS engineering item 2).** Registry v1 (`genesis.candidates`)
is closed. A descriptor's identity includes `candidates.py` itself, so adding any kind there
changes the descriptor ids of every frozen v1 candidate, including those in the E1 and E1b
packages. New kinds were therefore blocked, among them a time-matched exact-MIP baseline that
B20_R33/R38 show a GV3 comparison needs.

**Design.** Registry v2 lives beside v1 and leaves it untouched:
  * Descriptors use schema `genesis-candidate-descriptor-v2`, with the same fields as v1.
  * A kind lives in its own module under `genesis/candidate_kinds/`. That module declares the
    kind's domains, a parameter check, the child `solve(view, params, cpu_seconds, seed)` and its
    own files.
  * A v2 descriptor's implementation identity is the digests of this core module, the kind's
    files, and the domain files the child imports (`graphs.py`, `models.py`). Adding a kind module
    leaves every other kind's identity unchanged. Changing this core changes every v2 identity,
    on purpose.
  * The runner is the v1 runner's discipline, re-implemented here so that v1's file is not part of
    v2 identities:
      - a bounded child process sees only the candidate view (no task id, family, split or
        reference), the data parameters and the limits;
      - `isolation='runc'` uses the OCI sandbox with cgroup metering, and `'process'` uses
        rlimits (DEV);
      - output is strictly decoded, and the domain checker recomputes the value from the witness.
  * The registry is closed: KINDS maps kind names to modules. No module name, path or code
    comes from data. Since B20_R67 the map lives in `candidate_kinds/kinds.py`, outside every
    identity, so adding a kind really leaves the other kinds' identities unchanged (before, the map
    was in this core file, and adding a kind changed every v2 descriptor id). A kind's identity
    hashes the module actually dispatched for it: its first declared file must be its own source.

**Not wired.** The custodian, evaluation requests v4 and receipts still use registry v1 only. A
v2 descriptor in a request would be refused today. Wiring v2 in is a reviewed change; see
`docs/CANDIDATE_REGISTRY_V2.md`.
"""
import hashlib
import importlib
import json
from pathlib import Path
import sys

from .common import canonical, digest

SCHEMA = 'genesis-candidate-descriptor-v2'
from .candidate_kinds.kinds import KINDS  # noqa: E402  (B20_R67: the kind map, outside every identity)
CORE_FILES = ('candidates_v2.py', 'graphs.py', 'models.py')
FIELDS = {'schema', 'kind', 'domain', 'parameters', 'implementation', 'resource_profile', 'descriptor_id'}
PROFILE = {'cpu_seconds', 'memory_mib', 'wall_seconds', 'queries'}
ISOLATIONS = ('runc', 'process')
MAX_OUTPUT = 1 << 20
SOURCE_MOUNT = '/opt/genesis-src'
CHILD_ARGV = ('-s', '-B', '-m', 'genesis.candidates_v2', '--trusted-candidate-child', '/work/src/request.json')
SANDBOX_STATUS = {'TIMEOUT': 'TIMEOUT', 'CPU_LIMIT': 'CPU_LIMIT', 'OOM': 'MEMORY_LIMIT', 'OUTPUT_LIMIT': 'OUTPUT_LIMIT',
                  'EXIT_NONZERO': 'EXECUTION_ERROR'}


class CandidateError(ValueError):
    def __init__(self, code, detail=''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code = code


def _here():
    return Path(__file__).resolve().parent


def _kind(kind):
    if kind not in KINDS:
        raise CandidateError('UNKNOWN_KIND', str(kind))
    return importlib.import_module(f'.candidate_kinds.{KINDS[kind]}', __package__)


def implementation_identity(kind):
    """Digests of this core, the kind's own files and the domain files its child imports. The kind's first
    declared file must be the source of the module dispatched for it (B20_R67), so a kind name pointed at
    another module gets another identity."""
    mod = _kind(kind)
    own = f'candidate_kinds/{KINDS[kind]}.py'
    if not mod.FILES or mod.FILES[0] != own or Path(mod.__file__).resolve() != (_here() / own).resolve():
        raise CandidateError('MALFORMED_KIND', f'{kind}: the first declared file must be its own module, {own}')
    files = list(CORE_FILES) + list(mod.FILES)
    return {f: hashlib.sha256((_here() / f).read_bytes()).hexdigest() for f in files}


def _check_profile(rp):
    if set(rp) != PROFILE or type(rp['queries']) is not int or type(rp['memory_mib']) is not int:
        raise CandidateError('MALFORMED_PROFILE')
    if not 0 < rp['cpu_seconds'] <= 60 or not 0 < rp['wall_seconds'] <= 600 or not 256 <= rp['memory_mib'] <= 8192:
        raise CandidateError('MALFORMED_PROFILE')


def build_descriptor(kind, domain, parameters, *, cpu_seconds, memory_mib=2048, wall_seconds=None, queries=60):
    why = _kind(kind).check_parameters(domain, parameters)
    if why:
        raise CandidateError('MALFORMED_PARAMETERS', why)
    rp = {'cpu_seconds': cpu_seconds, 'memory_mib': memory_mib,
          'wall_seconds': wall_seconds if wall_seconds is not None else max(10, int(cpu_seconds * 5)), 'queries': queries}
    _check_profile(rp)
    body = {'schema': SCHEMA, 'kind': kind, 'domain': domain, 'parameters': json.loads(canonical(parameters)),
            'implementation': implementation_identity(kind), 'resource_profile': rp}
    return dict(body, descriptor_id=digest(body))


def descriptor_problems(desc, *, expected_id=None, domain=None):
    """[] for a descriptor this code would build identically, else the reasons it is refused."""
    if not isinstance(desc, dict) or set(desc) != FIELDS or desc.get('schema') != SCHEMA:
        return ['not a v2 candidate descriptor']
    if desc['kind'] not in KINDS:
        return [f'unknown kind {desc["kind"]!r}']
    out = []
    body = {k: desc[k] for k in FIELDS - {'descriptor_id'}}
    if digest(body) != desc['descriptor_id']:
        out.append('descriptor_id does not match the descriptor')
    if desc['implementation'] != implementation_identity(desc['kind']):
        out.append('implementation identity differs from this code')
    why = _kind(desc['kind']).check_parameters(desc['domain'], desc['parameters'])
    if why:
        out.append(why)
    try:
        _check_profile(desc['resource_profile'])
    except CandidateError as exc:
        out.append(exc.code)
    if expected_id is not None and desc['descriptor_id'] != expected_id:
        out.append('descriptor is not the expected one')
    if domain is not None and desc['domain'] != domain:
        out.append('descriptor domain differs from the task domain')
    return out


def child_request(task, desc, seed):
    from .domains import adapter
    view = adapter(task.domain).candidate_view(task)
    return {'view': view.model_dump(mode='json'), 'kind': desc['kind'], 'parameters': desc['parameters'],
            'cpu_seconds': desc['resource_profile']['cpu_seconds'], 'queries': desc['resource_profile']['queries'],
            'seed': seed}


def sandbox_policy(rp):
    import math
    from .sandbox import SandboxPolicy
    return SandboxPolicy(wall_seconds=rp['wall_seconds'], cpu_seconds=int(math.ceil(rp['cpu_seconds'])) + 1,
                         memory_mib=rp['memory_mib'], address_space_mib=rp['memory_mib'], pids=16,
                         output_bytes=MAX_OUTPUT + 1, work_mib=1, tmp_mib=16, open_files=128, max_file_mib=1)


def decode_output(raw, n_edges):
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


def _decode_and_check(receipt, stdout, task, domain):
    try:
        edges, claimed = decode_output(stdout, len(task.edges))
    except CandidateError as exc:
        return dict(receipt, status='CHECKER_ERROR', reason=exc.code)
    checked = domain.validate(task, edges)
    if checked['status'] != 'VALID' or checked['value'] != claimed:
        return dict(receipt, status='CHECKER_ERROR', reason='witness invalid or claimed value differs', check=checked)
    return dict(receipt, status='SUCCESS', result={'selected': [list(e) for e in edges], 'value': claimed}, check=checked)


def run(task, desc, *, seed, expected_id=None, isolation='process'):
    """Execute a v2 candidate on one task; the claimed value is never trusted."""
    from .domains import Unsupported, adapter
    if isolation not in ISOLATIONS:
        raise ValueError(f'isolation must be one of {ISOLATIONS}')
    problems = descriptor_problems(desc, expected_id=expected_id, domain=task.domain)
    base = {'descriptor_id': desc.get('descriptor_id') if isinstance(desc, dict) else None, 'registry': SCHEMA,
            'execution_mode': 'TRUSTED_REGISTERED_RUNNER', 'arbitrary_code_sandbox': False}
    if problems:
        return dict(base, status='REFUSED', problems=problems)
    domain = adapter(task.domain)
    gate = domain if isinstance(domain, Unsupported) else domain.supports(task, 'execute')
    if gate:
        return dict(base, status='UNSUPPORTED', reason=gate.reason)
    req = child_request(task, desc, seed)
    rp = desc['resource_profile']
    runner = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if isolation == 'runc':
        from . import sandbox as S
        r = S.run({'request.json': canonical(req)}, [S.PYTHON, *CHILD_ARGV], sandbox_policy(rp),
                  ro_mounts={SOURCE_MOUNT: str(_here().parent)}, env={'PYTHONPATH': SOURCE_MOUNT, 'PYTHONHASHSEED': '0'})
        receipt = dict(base, cpu_ns=r.get('cpu_ns'), wall_ns=r.get('wall_ns'), peak_memory_bytes=r.get('peak_memory_bytes'),
                       meter='cgroup', isolation=r.get('sandbox'), sandbox_status=r['status'],
                       candidate_view_sha256=digest(req['view']), runner_sha256=runner, limits=rp)
        if r['status'] != 'SUCCESS':
            return dict(receipt, status=SANDBOX_STATUS.get(r['status'], 'HARNESS_ERROR'),
                        stderr_tail=(r.get('stderr') or r.get('reason') or '')[-500:])
        return _decode_and_check(receipt, r['stdout'], task, domain)
    import os
    import tempfile
    from .learning.budget import NS, run_bounded
    with tempfile.NamedTemporaryFile(prefix='genesis-cand2-', suffix='.json', delete=False) as f:
        f.write(canonical(req))
        path = f.name
    try:
        os.chmod(path, 0o444)
        env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(_here().parent), 'PYTHONHASHSEED': '0',
               'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'}
        if sys.pycache_prefix:
            env['PYTHONPYCACHEPREFIX'] = sys.pycache_prefix
        r = run_bounded([sys.executable, '-s', '-m', 'genesis.candidates_v2', '--trusted-candidate-child', path],
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
    return _decode_and_check(receipt, r['stdout'], task, domain)


def _child(path):
    import resource
    req = json.loads(Path(path).read_bytes())
    if set(req) != {'view', 'kind', 'parameters', 'cpu_seconds', 'queries', 'seed'} or req['kind'] not in KINDS:
        raise SystemExit(2)
    from .models import CandidateGraph
    view = CandidateGraph.model_validate_json(canonical(req['view']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    out = _kind(req['kind']).solve(view, req['parameters'], req['cpu_seconds'], req['seed'])
    sys.stdout.write(json.dumps(out))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--trusted-candidate-child':
        _child(sys.argv[2])
    else:
        raise SystemExit('usage: python -m genesis.candidates_v2 --trusted-candidate-child REQUEST')
