"""OCI (runc) sandbox for arbitrary generated code (spec §16.1, §17, §30, §45).

Generated code is untrusted. Each run gets:
  * new pid, network, ipc, uts, mount and cgroup namespaces — no network at all
    (only a private loopback), no view of host processes;
  * a read-only root built from bind-mounted host /usr plus a generated /etc,
    a size-limited tmpfs /tmp, and a size-limited tmpfs /work as the only
    writable, collectable location;
  * UID/GID 65534, no capabilities, no_new_privs, a seccomp filter that
    refuses mount/namespace/kernel-module/ptrace/bpf/keyring/reboot calls;
  * cgroup memory, pids and CPU-quota limits plus rlimits (CPU, address space,
    file size, open files, core=0) and a wall-clock kill;
  * a scrubbed environment (no host variables, tokens or proxy settings).
Outputs are collected only from /work/out, without following symlinks, under a
byte cap. Every run returns a receipt, including failures.

This is the arbitrary-code backend the fixed DSL route never needed. It
requires root (to drive runc) and is reported UNAVAILABLE otherwise.
"""
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from pydantic import Field
from .common import bytes_hash, canonical, digest
from .models import StrictModel

RUNC = shutil.which('runc')
# Resolve the host interpreter to a real file under /usr (the sandbox has its own /etc,
# so alternatives symlinks such as /usr/bin/python3 -> /etc/alternatives/... do not resolve).
PYTHON = os.path.realpath(__import__('sys').executable)
SANDBOX_UID = 65534
DENIED_SYSCALLS = sorted({
    'mount', 'umount', 'umount2', 'pivot_root', 'chroot', 'unshare', 'setns',
    'init_module', 'finit_module', 'delete_module', 'kexec_load', 'kexec_file_load',
    'ptrace', 'process_vm_readv', 'process_vm_writev', 'bpf', 'perf_event_open', 'userfaultfd',
    'keyctl', 'add_key', 'request_key', 'reboot', 'swapon', 'swapoff', 'acct', 'quotactl',
    'open_by_handle_at', 'name_to_handle_at', 'lookup_dcookie', 'mknod', 'mknodat',
    'settimeofday', 'clock_settime', 'adjtimex', 'syslog', 'iopl', 'ioperm', 'vhangup',
    'fsopen', 'fsmount', 'fsconfig', 'move_mount', 'open_tree', 'mount_setattr'})
MASKED = ['/proc/acpi', '/proc/asound', '/proc/kcore', '/proc/keys', '/proc/latency_stats', '/proc/timer_list',
          '/proc/timer_stats', '/proc/sched_debug', '/sys/firmware', '/proc/scsi', '/sys/devices/virtual/powercap']
READONLY = ['/proc/bus', '/proc/fs', '/proc/irq', '/proc/sys', '/proc/sysrq-trigger']


class SandboxPolicy(StrictModel):
    schema_version: str = 'genesis-sandbox-policy-v1'
    wall_seconds: float = Field(default=120, gt=0, le=3600)
    cpu_seconds: int = Field(default=60, ge=1, le=3600)
    memory_mib: int = Field(default=2048, ge=32, le=65536)
    pids: int = Field(default=64, ge=4, le=4096)
    output_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=256 * 1024 * 1024)
    work_mib: int = Field(default=64, ge=1, le=4096)
    tmp_mib: int = Field(default=64, ge=1, le=4096)
    open_files: int = Field(default=256, ge=16, le=65536)
    max_file_mib: int = Field(default=32, ge=1, le=4096)
    # Virtual address-space cap (ulimit -v). Defaults to memory_mib; tools that mmap large
    # read-only libraries (Lean) need more address space than resident memory.
    address_space_mib: int | None = Field(default=None, ge=32, le=1 << 20)


def available():
    return RUNC is not None and os.geteuid() == 0


def policy_digest(policy):
    return digest({'policy': policy.model_dump(mode='json'), 'denied_syscalls': DENIED_SYSCALLS, 'enosys': ['clone3'],
                   'masked': MASKED, 'readonly': READONLY})


def _seccomp():
    return {'defaultAction': 'SCMP_ACT_ALLOW', 'architectures': ['SCMP_ARCH_X86_64', 'SCMP_ARCH_X86', 'SCMP_ARCH_X32'],
            'syscalls': [{'names': DENIED_SYSCALLS, 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 1},
                         # clone3 can create namespaces via its struct; answering ENOSYS makes libc fall
                         # back to clone(2), whose namespace flags are covered by no capabilities + userns off.
                         {'names': ['clone3'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 38}]}


def _config(policy, argv, cid, ro_mounts=None, extra_env=None):
    mib = 1024 * 1024
    return {
        'ociVersion': '1.0.2',
        'process': {
            'terminal': False, 'user': {'uid': SANDBOX_UID, 'gid': SANDBOX_UID, 'additionalGids': []},
            # RLIMIT_AS is applied by a shell shim after runc init: applying it to runc's
            # own Go init crashes libseccomp. The cgroup memory limit is the backstop.
            'args': ['/bin/sh', '-c', f'ulimit -v {(policy.address_space_mib or policy.memory_mib) * 1024} && exec "$@"',
                     'genesis-shim',
                     *argv],
            'cwd': '/work',
            'env': ['PATH=' + ':'.join([*(extra_env or {}).get('PATH_PREFIX', []), '/usr/bin', '/bin']),
                    'HOME=/work', 'LANG=C.UTF-8', 'PYTHONDONTWRITEBYTECODE=1', 'PYTHONHASHSEED=0', 'TMPDIR=/tmp',
                    *[f'{k}={v}' for k, v in sorted((extra_env or {}).items()) if k != 'PATH_PREFIX']],
            'capabilities': {k: [] for k in ('bounding', 'effective', 'inheritable', 'permitted', 'ambient')},
            'rlimits': [
                {'type': 'RLIMIT_CPU', 'hard': policy.cpu_seconds + 1, 'soft': policy.cpu_seconds},
                {'type': 'RLIMIT_FSIZE', 'hard': policy.max_file_mib * mib, 'soft': policy.max_file_mib * mib},
                {'type': 'RLIMIT_NOFILE', 'hard': policy.open_files, 'soft': policy.open_files},
                {'type': 'RLIMIT_NPROC', 'hard': policy.pids, 'soft': policy.pids},
                {'type': 'RLIMIT_CORE', 'hard': 0, 'soft': 0}],
            'noNewPrivileges': True, 'oomScoreAdj': 1000},
        'root': {'path': 'rootfs', 'readonly': True},
        'hostname': 'genesis-sandbox',
        'mounts': [
            {'destination': '/proc', 'type': 'proc', 'source': 'proc', 'options': ['nosuid', 'noexec', 'nodev']},
            {'destination': '/dev', 'type': 'tmpfs', 'source': 'tmpfs',
             'options': ['nosuid', 'strictatime', 'mode=755', 'size=65536k']},
            {'destination': '/dev/shm', 'type': 'tmpfs', 'source': 'shm',
             'options': ['nosuid', 'noexec', 'nodev', 'mode=1777', 'size=16m']},
            {'destination': '/tmp', 'type': 'tmpfs', 'source': 'tmpfs',
             'options': ['nosuid', 'nodev', 'mode=1777', f'size={policy.tmp_mib}m']},
            {'destination': '/usr', 'type': 'bind', 'source': '/usr', 'options': ['rbind', 'ro', 'nosuid', 'nodev']},
            {'destination': '/etc', 'type': 'bind', 'source': 'etc', 'options': ['bind', 'ro', 'nosuid', 'nodev']},
            {'destination': '/work', 'type': 'bind', 'source': 'work', 'options': ['bind', 'rw', 'nosuid', 'nodev']},
            *[{'destination': dest, 'type': 'bind', 'source': src, 'options': ['rbind', 'ro', 'nosuid', 'nodev']}
              for dest, src in sorted((ro_mounts or {}).items())],
        ],
        'linux': {
            'namespaces': [{'type': t} for t in ('pid', 'network', 'ipc', 'uts', 'mount', 'cgroup')],
            'cgroupsPath': f'/genesis-sandbox/{cid}',
            'resources': {
                'devices': [{'allow': False, 'access': 'rwm'}],
                'memory': {'limit': policy.memory_mib * mib, 'swap': policy.memory_mib * mib},
                'pids': {'limit': policy.pids},
                'cpu': {'quota': 100000, 'period': 100000},   # at most one CPU
            },
            'maskedPaths': MASKED, 'readonlyPaths': READONLY,
            'seccomp': _seccomp(),
        },
    }


def _cgroup_stat(cid):
    base = Path('/sys/fs/cgroup')
    out = {}
    for name, rel in (('cpu_ns', f'cpuacct/genesis-sandbox/{cid}/cpuacct.usage'),
                      ('peak_memory_bytes', f'memory/genesis-sandbox/{cid}/memory.max_usage_in_bytes'),
                      ('memory_failcnt', f'memory/genesis-sandbox/{cid}/memory.failcnt')):
        try:
            out[name] = int((base / rel).read_text().strip())
        except (OSError, ValueError):
            out[name] = None
    try:
        out['oom_killed'] = 'oom_kill 1' in (base / f'memory/genesis-sandbox/{cid}/memory.oom_control').read_text() \
            or (out['memory_failcnt'] or 0) > 0
    except OSError:
        out['oom_killed'] = None
    return out


def _collect(outdir, cap):
    files, total, problems = {}, 0, []
    if not outdir.is_dir() or outdir.is_symlink():
        return files, problems
    for path in sorted(outdir.rglob('*')):
        rel = str(path.relative_to(outdir))
        if path.is_symlink():
            problems.append(f'symlink refused: {rel}'); continue
        if not path.is_file():
            continue
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as f:
            data = f.read(cap - total + 1)
        if total + len(data) > cap:
            problems.append('output cap exceeded'); break
        files[rel] = data; total += len(data)
    return files, problems


def run(files, argv, policy=None, *, grant=None, ledger=None, ro_mounts=None, env=None):
    """Execute untrusted code. `files` (name -> bytes) are placed read-only under /work/src.

    Returns a receipt dict with status in SUCCESS, EXIT_NONZERO, TIMEOUT, CPU_LIMIT,
    OOM, OUTPUT_LIMIT, SANDBOX_UNAVAILABLE or SANDBOX_ERROR, plus collected outputs.
    """
    policy = policy or SandboxPolicy()
    if ledger is not None:
        ledger.require(grant, 'execute_sandboxed_code', cpu_seconds=policy.cpu_seconds, attempts=1)
    base_receipt = {'policy': policy.model_dump(mode='json'), 'policy_sha256': policy_digest(policy),
                    'argv': list(argv), 'inputs': {k: bytes_hash(v) for k, v in sorted(files.items())},
                    'runtime': 'runc', 'sandbox': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'}
    if not available():
        return dict(base_receipt, status='SANDBOX_UNAVAILABLE', reason='runc missing or not running as root')
    cid = 'g' + uuid.uuid4().hex[:24]
    bundle = Path(tempfile.mkdtemp(prefix='genesis-sbx-'))
    work = bundle / 'work'
    mounted = False
    try:
        ro_mounts = dict(ro_mounts or {})
        for dest, src in ro_mounts.items():
            if not dest.startswith('/opt/') or '..' in dest or not Path(src).is_dir():
                raise ValueError('extra read-only mounts must target /opt/<name> and be existing directories')
        for d in ('rootfs/usr', 'rootfs/etc', 'rootfs/proc', 'rootfs/dev', 'rootfs/tmp', 'rootfs/work', 'etc',
                  *[f'rootfs{dest}' for dest in ro_mounts]):
            (bundle / d).mkdir(parents=True, exist_ok=True)
        for link, target in (('bin', 'usr/bin'), ('lib', 'usr/lib'), ('lib64', 'usr/lib64'), ('sbin', 'usr/sbin')):
            os.symlink(target, bundle / 'rootfs' / link)
        (bundle / 'etc/passwd').write_text('nobody:x:65534:65534:nobody:/work:/usr/sbin/nologin\n')
        (bundle / 'etc/group').write_text('nogroup:x:65534:\n')
        (bundle / 'etc/hosts').write_text('127.0.0.1 localhost\n')
        work.mkdir()
        subprocess.run(['mount', '-t', 'tmpfs', '-o', f'size={policy.work_mib}m,mode=0755,nosuid,nodev', 'tmpfs',
                        str(work)], check=True, capture_output=True)
        mounted = True
        (work / 'src').mkdir(); (work / 'out').mkdir()
        for name, data in files.items():
            if '/' in name or name.startswith('.'):
                raise ValueError('flat, non-hidden input names only')
            (work / 'src' / name).write_bytes(data)
            (work / 'src' / name).chmod(0o444)
        os.chown(work / 'out', SANDBOX_UID, SANDBOX_UID)
        (work / 'src').chmod(0o555)
        config = _config(policy, argv, cid, ro_mounts, env)
        base_receipt['ro_mounts'] = sorted(ro_mounts)
        (bundle / 'config.json').write_bytes(canonical(config))
        start = time.monotonic_ns(); deadline = time.monotonic() + policy.wall_seconds
        proc = subprocess.Popen([RUNC, 'run', '--keep', '--bundle', str(bundle), cid], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={'PATH': '/usr/bin:/bin:/usr/sbin'},
                                start_new_session=True)
        status = None; buffers = {'stdout': bytearray(), 'stderr': bytearray()}; sizes = {'stdout': 0, 'stderr': 0}
        sel = selectors.DefaultSelector()
        for name, pipe in (('stdout', proc.stdout), ('stderr', proc.stderr)):
            os.set_blocking(pipe.fileno(), False); sel.register(pipe, selectors.EVENT_READ, name)
        while sel.get_map():
            if time.monotonic() >= deadline:
                status = 'TIMEOUT'; break
            for key, _ in sel.select(0.05):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    sel.unregister(key.fileobj); continue
                sizes[key.data] += len(chunk)
                room = policy.output_bytes - len(buffers[key.data])
                buffers[key.data].extend(chunk[:max(0, room)])
                if sizes[key.data] > policy.output_bytes:
                    status = 'OUTPUT_LIMIT'
            if status:
                break
        if status:
            killed = subprocess.run([RUNC, 'kill', cid, 'KILL'], capture_output=True)
            # Keep draining (and discarding) so neither runc nor the container blocks on a full pipe.
            drain_until = time.monotonic() + 10
            while sel.get_map() and time.monotonic() < drain_until:
                for key, _ in sel.select(0.05):
                    if not os.read(key.fd, 1 << 20):
                        sel.unregister(key.fileobj)
        try:
            proc.wait(timeout=max(1, deadline - time.monotonic()) + 5)
        except subprocess.TimeoutExpired:
            subprocess.run([RUNC, 'kill', cid, 'KILL'], capture_output=True)
            proc.wait(timeout=10); status = status or 'TIMEOUT'
        sel.close()
        wall = time.monotonic_ns() - start
        stats = _cgroup_stat(cid)
        code = proc.returncode
        if status is None:
            if code == 0:
                status = 'SUCCESS'
            elif stats.get('oom_killed') or code == 137 and (stats.get('peak_memory_bytes') or 0) >= \
                    policy.memory_mib * 1024 * 1024 * 0.9:
                status = 'OOM'
            elif code in (128 + signal.SIGXCPU, 128 + signal.SIGKILL) and (stats.get('cpu_ns') or 0) >= \
                    policy.cpu_seconds * 1e9 * 0.9:
                status = 'CPU_LIMIT'
            else:
                status = 'EXIT_NONZERO'
        outputs, problems = _collect(work / 'out', policy.output_bytes)
        receipt = dict(base_receipt, status=status, exit_code=code, wall_ns=wall, **stats,
                       stdout=bytes(buffers['stdout']).decode(errors='replace'),
                       stderr=bytes(buffers['stderr']).decode(errors='replace'),
                       output_bytes_observed=sizes, truncated=status == 'OUTPUT_LIMIT',
                       outputs={k: bytes_hash(v) for k, v in outputs.items()}, output_problems=problems,
                       config_sha256=bytes_hash(canonical(config)))
        receipt['_output_bytes'] = outputs
        return receipt
    except Exception as exc:
        return dict(base_receipt, status='SANDBOX_ERROR', reason=f'{type(exc).__name__}: {exc}')
    finally:
        subprocess.run([RUNC, 'delete', '-f', cid], capture_output=True) if RUNC else None
        if mounted:
            subprocess.run(['umount', '-l', str(work)], capture_output=True)
        shutil.rmtree(bundle, ignore_errors=True)
        if ledger is not None:
            pass  # charging happens in the caller once the receipt is stored


def run_python(source, policy=None, *, args=(), **kw):
    """Convenience: run one untrusted Python file with an isolated interpreter."""
    return run({'main.py': source.encode() if isinstance(source, str) else source},
               [PYTHON, '-I', '-B', '/work/src/main.py', *args], policy, **kw)
