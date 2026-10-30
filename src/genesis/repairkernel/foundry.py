"""The kernel's side of an obstacle (`docs/OMEGA_SELF_REPAIR.md` §3, §5): it runs the job, and when the job fails it
hands the obstacle to the research plane **across an isolation boundary** and decides what comes back.

Three parties, three processes:
  * the **kernel** (this module, root): runs the job and its checkpoints; serves the research plane's requests (run or
    resume the job, its repairable source, its visible tests); takes **one proposal per obstacle**, which it checks
    with the static guard, sends to the independent verifier (another process, `verify`), and hands to the
    Supervisor's predefined policy (`supervisor`), which promotes it with a backup for rollback, or not. It logs the
    full verdict; the research plane learns only accepted or not, which checks failed, and whether it was promoted;
  * the **trial executor** (`executor`): runs candidate sources on workloads (the job's failing segment, or fresh
    workloads of the research plane's choosing) against the reference models, and reports pass, crash or divergence
    and what the probe saw;
  * the **research plane** (`genesis.repair.remote`, running `genesis.repair.loop`): diagnoses, synthesises, and
    proposes; it keeps its own vault of repair knowledge.

**Isolation** (`isolated=True`), enforced by the operating system, not by convention: the executor and the research
plane each run in a private mount namespace, as their own unprivileged user (RESEARCH_ID, EXECUTOR_ID), with no
capabilities and `no_new_privs`. In each namespace /home, /tmp, /var/tmp, /dev/shm, /mnt, /opt and /srv are covered by
empty file systems, so neither sees the repository, its history, the evidence, the logs, the other's files or any
shared scratch space; each sees only, read-only, the source tree it runs from:
  * the research plane's view of `src/` lacks `genesis/repairkernel` entirely (the reference models, the hidden tests,
    the kernel's seeds, the defect catalogue, the correct sources, the policy), and it can write only to its vault;
  * the executor's view lacks the verifier, the catalogue, the policy and this module (`HIDDEN_FROM_EXECUTOR`), and it
    can write nowhere; a candidate it runs is first checked by the static guard (`guard`).
Neither can write the Judge (`autonomy/feedback.py`), the Supervisor, the verifier, the policy or the sealed tests: they
are root's, and not even visible to them. The parties talk over pipes; the kernel never unpickles what either sends.

`isolated=False` runs the same protocol in one process (unit tests; development)."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading
import time

from . import bench as BN
from . import guard as GD
from . import supervisor as SV
from . import verify as VF

RESEARCH_ID = 61001
EXECUTOR_ID = 61002
COVER = ('/home', '/tmp', '/var/tmp', '/dev/shm', '/opt', '/srv')
HIDDEN_FROM_EXECUTOR = ('verify.py', 'defects.py', 'supervisor.py', 'foundry.py')
ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}


def src_root():
    return Path(__file__).resolve().parents[2]


class Kernel:
    """The kernel's answers to the research plane, for one job and one obstacle."""

    def __init__(self, job, scope='testbed', log_path=None, repair_id='repair', separate=True):
        self.job, self.scope, self.repair_id, self.separate = job, scope, repair_id, separate
        self.log_path = Path(log_path) if log_path else job.dir.parent / 'supervisor.jsonl'
        self.original = job.file.read_text()
        self.proposals = 0
        self.verdict = None
        self.decision = None
        self.runs = []
        self.verify_s = 0.0

    def hello(self):
        return {'repairable': [str(self.job.file)], 'validation': ['Divergence']}

    def run(self, resume=False):
        r = self.job.run(resume=resume)
        self.runs.append({k: r.get(k) for k in ('status', 'op', 'started')})
        return r

    def source(self):
        return self.job.file.read_text()

    def visible_tests(self):
        from . import targets as TG
        return [list(t) for t in TG.VISIBLE_TESTS[self.job.target]]

    def propose(self, patch):
        self.proposals += 1
        if self.proposals > 1:
            return {'accepted': False, 'failed_checks': None, 'promoted': False,
                    'why': 'refused: one proposal per obstacle'}
        why = GD.check(self.original, patch)
        if why:
            self.verdict = {'accepted': False, 'checks': {'guard': {'ok': False, 'why': why}}}
        else:
            j = self.job
            run = VF.run_separately if self.separate else VF.verify
            t = time.time()
            self.verdict = run(j.dir, j.target, j.seed, j.n_ops, j.every, patch)
            self.verify_s = round(time.time() - t, 2)
        failed = [k for k, v in self.verdict.get('checks', {}).items() if not v.get('ok')]
        if not self.verdict.get('accepted'):
            return {'accepted': False, 'failed_checks': failed or None, 'promoted': False,
                    'why': 'the verifier rejected it' if failed else 'verifier error'}
        self.decision = SV.promote(self.job.file, patch, self.verdict, self.scope, self.log_path, self.repair_id)
        d = self.decision['decision']
        return {'accepted': True, 'failed_checks': [], 'promoted': d['promote'], 'why': d['why']}

    def serve(self, q):
        op = q.get('op')
        if op == 'hello':
            return self.hello()
        if op == 'run':
            return self.run(bool(q.get('resume')))
        if op == 'source':
            return self.source()
        if op == 'visible_tests':
            return self.visible_tests()
        if op == 'propose':
            return self.propose(str(q.get('patch', '')))
        return {'error': f'unknown request {op!r}'}


class LocalHandle(BN.Handle):
    """The research plane's handle in one process (`isolated=False`)."""

    def __init__(self, kernel):
        super().__init__(kernel.job)
        self._kernel = kernel

    def run(self, resume=False):
        return self._kernel.run(resume)

    def propose(self, patch):
        return self._kernel.propose(patch)


# ------------------------------------------------------------------------------------------------- isolation
def _namespace(uid, binds, covers, bootstrap, args):
    """argv: a private mount namespace in which `binds` [(source, target, writable)] are mounted under /mnt, `covers`
    (paths under /mnt) are hidden, COVER is hidden, and `bootstrap` runs as `uid` with no capabilities."""
    sh = ['set -e', 'mount -t tmpfs -o mode=0755 tmpfs /mnt', ': > /mnt/.hidden', 'chmod 0000 /mnt/.hidden']
    for source, target, writable in binds:
        sh.append(f'mkdir -p {shlex.quote(target)}')
        sh.append(f'mount --bind {shlex.quote(str(source))} {shlex.quote(target)}')
        if not writable:
            sh.append(f'mount -o remount,bind,ro {shlex.quote(target)}')
    for c in covers:
        if c.endswith('/'):
            sh.append(f'[ -d {shlex.quote(c)} ] && mount -t tmpfs -o mode=0555 tmpfs {shlex.quote(c)} || true')
        else:
            sh.append(f'[ -e {shlex.quote(c)} ] && mount --bind /mnt/.hidden {shlex.quote(c)} || true')
    for c in COVER:
        sh.append(f'mount -t tmpfs -o mode=0755 tmpfs {c}')
    sh.append('cd /')
    sh.append(' '.join(['exec', 'setpriv', f'--reuid={uid}', f'--regid={uid}', '--clear-groups', '--no-new-privs',
                        '--inh-caps=-all', '--bounding-set=-all', sys.executable, '-I', '-c',
                        shlex.quote(bootstrap)] + [shlex.quote(str(a)) for a in args]))
    return ['unshare', '-m', '--propagation', 'private', 'sh', '-c', '\n'.join(sh)]


def _send(f, obj):
    f.write((json.dumps(obj, default=str) + '\n').encode())
    f.flush()


def handle_obstacle(job, *, vault_dir, arm='loop', budget=300, seed=0, repair_id='repair', exclude_vault=(),
                    scope='testbed', log_path=None, isolated=True, timeout=900, stderr_path=None):
    """Hand the job's obstacle to the research plane; returns (the research plane's record, the kernel's record)."""
    import resource
    kernel = Kernel(job, scope, log_path, repair_id, separate=True)
    ru0, k0 = resource.getrusage(resource.RUSAGE_CHILDREN), time.process_time()
    params = {'arm': arm, 'budget': budget, 'seed': seed, 'repair_id': repair_id, 'exclude_vault': list(exclude_vault)}
    t0 = time.time()
    if not isolated:
        import importlib
        loop = importlib.import_module('genesis.repair.loop')
        vault = loop.Vault(Path(vault_dir) / 'vault.jsonl')
        rec = loop.episode(LocalHandle(kernel), vault=vault, **params)
        return rec, _kernel_record(kernel, t0, isolated, ru0, k0)
    vault_dir = Path(vault_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)
    os.chown(vault_dir, RESEARCH_ID, RESEARCH_ID)
    for f in vault_dir.iterdir():
        os.chown(f, RESEARCH_ID, RESEARCH_ID)
    src = src_root()
    # pipes: research -> kernel, kernel -> research, research -> executor, executor -> research, kernel -> executor
    r2k, k2r, r2x, x2r, k2x = os.pipe(), os.pipe(), os.pipe(), os.pipe(), os.pipe()
    ex_boot = ('import sys; sys.path.insert(0, "/mnt/src"); '
               'from genesis.repairkernel.executor import main; main()')
    ex_cmd = _namespace(EXECUTOR_ID, [(src, '/mnt/src', False)],
                        [f'/mnt/src/genesis/repairkernel/{f}' for f in HIDDEN_FROM_EXECUTOR]
                        + ['/mnt/src/genesis/repairkernel/__pycache__/', '/mnt/src/genesis/repair/'],
                        ex_boot, [k2x[0], r2x[0], x2r[1]])
    rs_boot = ('import sys; sys.path.insert(0, "/mnt/src"); '
               'from genesis.repair.remote import main; main()')
    rs_cmd = _namespace(RESEARCH_ID, [(src, '/mnt/src', False), (vault_dir, '/mnt/vault', True)],
                        ['/mnt/src/genesis/repairkernel/'],
                        rs_boot, [r2k[1], k2r[0], r2x[1], x2r[0], '/mnt/vault/vault.jsonl', json.dumps(params)])
    err = open(stderr_path, 'ab') if stderr_path else subprocess.DEVNULL
    ex = subprocess.Popen(ex_cmd, pass_fds=(k2x[0], r2x[0], x2r[1]), cwd='/', env=ENV, stdin=subprocess.DEVNULL,
                          stdout=err, stderr=err)
    rs = subprocess.Popen(rs_cmd, pass_fds=(r2k[1], k2r[0], r2x[1], x2r[0]), cwd='/', env=ENV,
                          stdin=subprocess.DEVNULL, stdout=err, stderr=err)
    for fd in (k2x[0], r2x[0], x2r[1], r2k[1], k2r[0], r2x[1], x2r[0]):
        os.close(fd)
    import pickle
    with os.fdopen(k2x[1], 'wb') as f:          # the executor's job specification (the kernel's own data)
        pickle.dump({'failing': job.trial_spec(), 'original': kernel.original, 'target': job.target,
                     'filename': str(job.file)}, f)
    killed = []

    def watchdog():
        for p in (rs, ex):
            try:
                p.wait(timeout=max(1, timeout - (time.time() - t0)))
            except subprocess.TimeoutExpired:
                killed.append(True)
                rs.kill()
                ex.kill()
                return
    threading.Thread(target=watchdog, daemon=True).start()
    rec = None
    with os.fdopen(r2k[0], 'rb') as rin, os.fdopen(k2r[1], 'wb') as rout:
        for line in rin:
            try:
                q = json.loads(line)
            except ValueError:
                break
            if q.get('op') == 'done':
                rec = q.get('record')
                _send(rout, {'ok': True})
                break
            try:
                _send(rout, kernel.serve(q))
            except BrokenPipeError:
                break
    for p in (rs, ex):
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
    if err is not subprocess.DEVNULL:
        err.close()
    krec = _kernel_record(kernel, t0, isolated, ru0, k0)
    krec['exit'] = {'research': rs.returncode, 'executor': ex.returncode, 'killed_by_timeout': bool(killed)}
    return rec, krec


def _views(party, vault_dir=None):
    src = src_root()
    if party == 'executor':
        return EXECUTOR_ID, [(src, '/mnt/src', False)], (
            [f'/mnt/src/genesis/repairkernel/{f}' for f in HIDDEN_FROM_EXECUTOR]
            + ['/mnt/src/genesis/repairkernel/__pycache__/', '/mnt/src/genesis/repair/'])
    binds = [(src, '/mnt/src', False)] + ([(vault_dir, '/mnt/vault', True)] if vault_dir else [])
    return RESEARCH_ID, binds, ['/mnt/src/genesis/repairkernel/']


def run_isolated(party, code, vault_dir=None, timeout=60):
    """Run `code` (Python) as `party` ('research' or 'executor') in the same isolation as an obstacle; its stdout.
    For the isolation tests: what each party can and cannot see or change."""
    if vault_dir:
        Path(vault_dir).mkdir(parents=True, exist_ok=True)
        os.chown(vault_dir, RESEARCH_ID, RESEARCH_ID)
    uid, binds, covers = _views(party, vault_dir)
    cmd = _namespace(uid, binds, covers, code, [])
    p = subprocess.run(cmd, cwd='/', env=ENV, capture_output=True, text=True, timeout=timeout)
    return p.stdout + (p.stderr[-2000:] if p.returncode else '')


ISOLATION_PROBE = r'''
import json, os
out = {'uid': os.getuid(), 'euid': os.geteuid()}
def attempt(name, fn):
    try:
        r = fn()
        out[name] = 'ok' if r is None else r
    except Exception as e:
        out[name] = type(e).__name__
def read(p):
    return lambda: 'read ' + str(len(open(p, 'rb').read())) + ' bytes'
def write(p):
    def w():
        with open(p, 'a') as f:
            f.write('')
    return w
REPO = __REPO__
attempt('read hidden tests (own view)', read('/mnt/src/genesis/repairkernel/verify.py'))
attempt('read defect catalogue (own view)', read('/mnt/src/genesis/repairkernel/defects.py'))
attempt('read reference models (own view)', read('/mnt/src/genesis/repairkernel/targets.py'))
attempt('read hidden tests (repository path)', read(REPO + '/src/genesis/repairkernel/verify.py'))
attempt('read repository history', lambda: str(len(os.listdir(REPO + '/.git'))))
attempt('list /home', lambda: str(os.listdir('/home')))
attempt('list /tmp', lambda: str(os.listdir('/tmp')))
attempt('list /root', lambda: str(os.listdir('/root')))
attempt('write the Judge', write('/mnt/src/genesis/autonomy/feedback.py'))
attempt('write the Judge (repository path)', write(REPO + '/src/genesis/autonomy/feedback.py'))
attempt('write the Supervisor policy', write('/mnt/src/genesis/repairkernel/supervisor.py'))
attempt('write the verifier (repository path)', write(REPO + '/src/genesis/repairkernel/verify.py'))
attempt('create a file in the source tree', write('/mnt/src/genesis/new_file.py'))
attempt('write the vault', write('/mnt/vault/probe.txt'))
attempt('write /tmp', write('/tmp/probe.txt'))
print(json.dumps(out))
'''


def isolation_report(vault_dir):
    """What each party can do, measured (not declared): a dict per party."""
    repo = str(src_root().parent)
    out = {}
    for party in ('research', 'executor'):
        raw = run_isolated(party, ISOLATION_PROBE.replace('__REPO__', repr(repo)), vault_dir if party == 'research' else None)
        try:
            out[party] = json.loads(raw.strip().splitlines()[-1])
        except (ValueError, IndexError):
            out[party] = {'error': raw[-800:]}
    return out


def _kernel_record(kernel, t0, isolated, ru0, k0):
    """With the episode's CPU time: the kernel's own, and its children's (the research plane, the trial executor and
    the verifier, each waited for), which is every party's work on the obstacle."""
    import resource
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    children = (ru.ru_utime - ru0.ru_utime) + (ru.ru_stime - ru0.ru_stime)
    kernel_cpu = time.process_time() - k0
    return {'isolated': isolated, 'wall_s': round(time.time() - t0, 2), 'verify_s': kernel.verify_s,
            'cpu_s': {'kernel': round(kernel_cpu, 3), 'children': round(children, 3),
                      'total': round(kernel_cpu + children, 3)},
            'proposals': kernel.proposals,
            'verdict': kernel.verdict, 'decision': kernel.decision, 'runs': kernel.runs}
