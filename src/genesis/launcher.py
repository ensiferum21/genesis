"""Privileged sandbox launcher and unprivileged research worker (roadmap W04).

Before B15 the research process itself had to run as root to drive runc. Now the
roles are separate:

  * the LAUNCHER runs as root, owns the runc sandbox, and listens on a Unix
    socket in a root-owned directory. It serves exactly one configured worker
    UID (checked with SO_PEERCRED, not trusted from the request), enforces its
    own policy ceiling, program and mount allowlists and a total budget, and
    appends every decision to a hash-chained log the worker cannot write;
  * the WORKER (research code) runs unprivileged, holds no keys and calls
    `sandbox.run`, which delegates to the launcher when GENESIS_LAUNCHER_SOCKET
    is set and the process is not root.

The launcher adds containment and accounting; it confers no evidence status.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import threading

from .common import canonical, utcnow
from .models import StrictModel

SOCKET_ENV = 'GENESIS_LAUNCHER_SOCKET'
REQUEST_SCHEMA = 'genesis-launch-request-v1'
MAX_REQUEST = 64 << 20
MAX_ARGS = 64
MAX_ARG = 4096
ENV_KEY = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')
ENV_DENY = {'LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONHOME',
            'BASH_ENV', 'ENV', 'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'NO_PROXY'}


class LauncherRefused(RuntimeError):
    pass


class LauncherConfig(StrictModel):
    schema_version: str = 'genesis-launcher-config-v1'
    socket_path: str
    log_path: str
    worker_uid: int
    policy_ceiling: dict          # SandboxPolicy fields: requests may not exceed any of them
    programs: tuple[str, ...]     # allowed argv[0] values inside the sandbox
    mounts: dict[str, str]        # allowed read-only mounts: sandbox destination -> host source
    env_keys: tuple[str, ...] = ('PATH_PREFIX', 'LEAN_PATH', 'LEAN_SYSROOT', 'GENESIS_STAGE')
    budget_runs: int = 1000
    budget_cpu_seconds: int = 36000


def _send(sock, obj):
    data = canonical(obj)
    sock.sendall(struct.pack('>I', len(data)) + data)


def _recv(sock, limit=MAX_REQUEST):
    head = _exact(sock, 4)
    (n,) = struct.unpack('>I', head)
    if n > limit:
        raise LauncherRefused('request too large')
    return json.loads(_exact(sock, n))


def _exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(1 << 20, n - len(buf)))
        if not chunk:
            raise LauncherRefused('connection closed mid-message')
        buf.extend(chunk)
    return bytes(buf)


def peer_credentials(conn):
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    pid, uid, gid = struct.unpack('3i', raw)
    return {'pid': pid, 'uid': uid, 'gid': gid}


class Launcher:
    """Root-side service. `serve_forever` handles one request at a time (concurrency 1)."""

    def __init__(self, config):
        from . import sandbox
        if os.geteuid() != 0:
            raise PermissionError('the sandbox launcher must run as root')
        self.config = config
        self.sandbox = sandbox
        self.ceiling = sandbox.SandboxPolicy(**config.policy_ceiling)
        self.used = {'runs': 0, 'cpu_seconds': 0}
        sock_path = Path(config.socket_path)
        parent = sock_path.parent
        st = parent.stat()
        if st.st_uid != 0 or st.st_mode & 0o022:
            raise PermissionError('launcher socket directory must be root-owned and not group/world writable')
        if sock_path.exists() or sock_path.is_symlink():
            sock_path.unlink()
        self.log_path = Path(config.log_path)
        if self.log_path.exists():
            self._log_head, self._log_seq = self._verify_log()
        else:
            self._log_head, self._log_seq = None, 0
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(sock_path))
        # The worker must be able to connect; the peer UID check decides who is served.
        os.chmod(sock_path, 0o666)
        self.server.listen(8)
        self._stop = threading.Event()

    # ------------------------------------------------------------------ log
    def _verify_log(self):
        return verify_log(self.log_path)

    def _log(self, record):
        self._log_seq += 1
        entry = dict(record, seq=self._log_seq, prev=self._log_head, time=utcnow())
        line = canonical(entry)
        fd = os.open(self.log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line + b'\n'); os.fsync(fd)
        finally:
            os.close(fd)
        self._log_head = hashlib.sha256(line).hexdigest()
        return self._log_seq

    # ------------------------------------------------------------------ policy
    def _check(self, req):
        if not isinstance(req, dict) or req.get('schema') != REQUEST_SCHEMA:
            raise LauncherRefused('unknown request schema')
        if set(req) - {'schema', 'files', 'argv', 'policy', 'ro_mounts', 'env'}:
            raise LauncherRefused('unexpected request fields')
        argv = req.get('argv')
        if (not isinstance(argv, list) or not argv or len(argv) > MAX_ARGS
                or not all(isinstance(a, str) and len(a) <= MAX_ARG and '\0' not in a for a in argv)):
            raise LauncherRefused('malformed argv')
        if argv[0] not in self.config.programs:
            raise LauncherRefused(f'program not allowed: {argv[0]}')
        files = req.get('files') or {}
        if not isinstance(files, dict):
            raise LauncherRefused('malformed files')
        decoded = {}
        for name, data in files.items():
            if not isinstance(name, str) or not isinstance(data, str):
                raise LauncherRefused('malformed files')
            decoded[name] = base64.b64decode(data, validate=True)
        policy = self.sandbox.SandboxPolicy(**(req.get('policy') or {}))
        over = [k for k, cap in self.ceiling.model_dump().items()
                if k != 'schema_version' and cap is not None and getattr(policy, k) is not None
                and getattr(policy, k) > cap]
        if over:
            raise LauncherRefused(f'policy exceeds the launcher ceiling: {sorted(over)}')
        mounts = req.get('ro_mounts') or {}
        if not isinstance(mounts, dict) or any(self.config.mounts.get(d) != s for d, s in mounts.items()):
            raise LauncherRefused('mount not in the launcher allowlist')
        env = req.get('env') or {}
        if not isinstance(env, dict):
            raise LauncherRefused('malformed env')
        for k, v in env.items():
            if k not in self.config.env_keys or k in ENV_DENY or not ENV_KEY.match(k):
                raise LauncherRefused(f'environment key not allowed: {k}')
            values = v if k == 'PATH_PREFIX' else [v]
            if not isinstance(values, list) or not all(isinstance(x, str) and '\0' not in x and '\n' not in x
                                                       for x in values):
                raise LauncherRefused('malformed environment value')
            if k == 'PATH_PREFIX' and not all(x.startswith('/opt/') and '..' not in x for x in values):
                raise LauncherRefused('PATH_PREFIX entries must be under /opt/')
        if self.used['runs'] + 1 > self.config.budget_runs or \
                self.used['cpu_seconds'] + policy.cpu_seconds > self.config.budget_cpu_seconds:
            raise LauncherRefused('launcher budget exhausted')
        return decoded, argv, policy, mounts, env

    # ------------------------------------------------------------------ serving
    def handle(self, conn):
        peer = peer_credentials(conn)
        request_sha = None
        try:
            if peer['uid'] != self.config.worker_uid:
                raise LauncherRefused(f'peer uid {peer["uid"]} is not the configured worker')
            raw = _recv(conn)
            request_sha = hashlib.sha256(canonical(raw)).hexdigest()
            files, argv, policy, mounts, env = self._check(raw)
            self.used['runs'] += 1; self.used['cpu_seconds'] += policy.cpu_seconds
            receipt = self.sandbox._run_local(files, argv, policy, ro_mounts=mounts, env=env)
            outputs = receipt.pop('_output_bytes', {})
            seq = self._log({'peer': peer, 'request_sha256': request_sha, 'decision': 'RUN',
                             'status': receipt.get('status'),
                             'receipt_sha256': hashlib.sha256(canonical(receipt)).hexdigest()})
            # The log head travels with the receipt, so the worker's own evidence anchors the
            # launcher log: a later rewrite of any entry up to here no longer matches it.
            receipt['launcher'] = {'log_seq': seq, 'log_head': self._log_head, 'request_sha256': request_sha,
                                   'peer_uid': peer['uid'], 'separation': 'ROOT_LAUNCHER_UNPRIVILEGED_WORKER'}
            _send(conn, {'ok': True, 'receipt': receipt,
                         'outputs': {k: base64.b64encode(v).decode() for k, v in outputs.items()}})
        except (LauncherRefused, ValueError, TypeError) as exc:
            reason = f'{type(exc).__name__}: {exc}'
            seq = self._log({'peer': peer, 'request_sha256': request_sha, 'decision': 'REFUSED', 'reason': reason})
            try:
                _send(conn, {'ok': False, 'refused': reason, 'log_seq': seq})
            except OSError:
                pass

    def serve_forever(self):
        self.server.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._stop.is_set():
                    break
                raise
            with conn:
                conn.settimeout(60)
                try:
                    self.handle(conn)
                except OSError:
                    pass

    def stop(self):
        self._stop.set()
        self.server.close()
        try:
            Path(self.config.socket_path).unlink()
        except FileNotFoundError:
            pass


def verify_log(path, *, anchors=()):
    """Check the launcher log's hash chain; `anchors` are (log_seq, log_head) pairs
    recorded in worker receipts. Returns (head, entries). The chain alone cannot
    detect a rewrite of its newest entries; the anchors held by workers can."""
    prev, seq, heads = None, 0, {}
    for line in Path(path).read_bytes().splitlines():
        entry = json.loads(line)
        seq += 1
        if entry.get('seq') != seq or entry.get('prev') != prev or canonical(entry) != line:
            raise RuntimeError('launcher log is not an intact hash chain')
        prev = hashlib.sha256(line).hexdigest(); heads[seq] = prev
    for s, head in anchors:
        if heads.get(s) != head:
            raise RuntimeError(f'launcher log entry {s} differs from the head a worker recorded')
    return prev, seq


def request(socket_path, files, argv, policy, *, ro_mounts=None, env=None, timeout=None):
    """Worker side: ask the launcher to run `argv` in the sandbox. Returns a receipt
    shaped like sandbox.run's (with `_output_bytes`), or a LAUNCHER_REFUSED receipt."""
    payload = {'schema': REQUEST_SCHEMA, 'argv': list(argv),
               'files': {k: base64.b64encode(v).decode() for k, v in files.items()},
               'policy': policy.model_dump(mode='json', exclude={'schema_version'}),
               'ro_mounts': dict(ro_mounts or {}), 'env': dict(env or {})}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout or policy.wall_seconds + 120)
        s.connect(str(socket_path))
        _send(s, payload)
        reply = _recv(s, limit=MAX_REQUEST + policy.output_bytes * 2)
    if not reply.get('ok'):
        return {'status': 'LAUNCHER_REFUSED', 'reason': reply.get('refused'), 'launcher_log_seq': reply.get('log_seq'),
                'argv': list(argv), 'runtime': 'runc-via-launcher'}
    receipt = reply['receipt']
    receipt['_output_bytes'] = {k: base64.b64decode(v) for k, v in reply['outputs'].items()}
    return receipt


# ---------------------------------------------------------------------- role separation check

def _allowed(st, uid, gids, bits):
    """POSIX permission bits only (ACLs and capabilities are not modelled)."""
    if uid == 0:
        return True
    shift = 6 if st.st_uid == uid else (3 if st.st_gid in gids else 0)
    return (st.st_mode >> shift) & bits == bits     # every requested bit, e.g. w+x to create in a directory


def can_access(path, uid, gids, want):
    """Could `uid` (with groups `gids`) read ('r') or write ('w') `path`, including traversal?"""
    path = Path(path).resolve()
    for ancestor in reversed(path.parents):
        if not _allowed(ancestor.stat(), uid, gids, 1):
            return False
    if not path.exists():
        return _allowed(path.parent.stat(), uid, gids, 3) if want == 'w' else False
    st = path.stat()
    if want == 'w' and stat.S_ISDIR(st.st_mode):
        return _allowed(st, uid, gids, 3)
    return _allowed(st, uid, gids, 4 if want == 'r' else 2)


def role_separation_report(*, worker_uid, worker_gids=(), socket_path=None, log_path=None, secret_paths=(),
                           trust_root=None, evidence_roots=()):
    """Check a deployment's role layout from the filesystem: the worker is not root,
    cannot read secrets (custodian keys, private roots), cannot write the trust root
    or the launcher's log, and the launcher socket lives in a root-owned directory."""
    gids = set(worker_gids)
    checks = []

    def add(name, ok, detail):
        checks.append({'check': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    add('worker_not_root', worker_uid != 0, f'worker uid {worker_uid}')
    for p in secret_paths:
        add(f'secret_unreadable:{p}', not can_access(p, worker_uid, gids, 'r'), 'custodian keys and private roots')
    if trust_root is not None:
        tr = Path(trust_root)
        writable = [str(q) for q in [tr, *tr.rglob('*')] if can_access(q, worker_uid, gids, 'w')]
        add('trust_root_not_writable', not writable, writable or 'no worker-writable path')
    if log_path is not None:
        add('launcher_log_not_writable', not can_access(log_path, worker_uid, gids, 'w'), str(log_path))
    if socket_path is not None:
        st = Path(socket_path).parent.stat()
        add('socket_directory_root_owned', st.st_uid == 0 and not st.st_mode & 0o022, str(Path(socket_path).parent))
    for p in evidence_roots:
        add(f'evidence_writable_by_worker:{p}', can_access(p, worker_uid, gids, 'w'), 'research store must be writable')
    failed = [c['check'] for c in checks if c['status'] == 'FAIL']
    return {'schema': 'genesis-role-separation-v1', 'ok': not failed, 'failed': failed, 'checks': checks,
            'model': 'POSIX mode bits; ACLs, capabilities and LSM policy are not modelled'}
