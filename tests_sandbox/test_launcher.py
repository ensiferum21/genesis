"""B15 / W04: privileged launcher, unprivileged research worker (spec §38: blocks release).

The launcher runs as root in this test process; every worker is a real child
process dropped to UID 65534 that can reach runc only through the launcher.
"""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest

from genesis import sandbox
from genesis.launcher import Launcher, LauncherConfig, role_separation_report, can_access

ROOT = Path(__file__).resolve().parents[1]
NOBODY = 65534
# A deployment ceiling large enough for the pinned Lean checker's policy, and no larger.
CEILING = {'wall_seconds': 300, 'cpu_seconds': 240, 'memory_mib': 6144, 'pids': 64, 'output_bytes': 8 << 20,
           'work_mib': 256, 'tmp_mib': 64, 'max_file_mib': 128, 'open_files': 16384, 'address_space_mib': 262144}
SMALL = dict(wall_seconds=30, cpu_seconds=10, memory_mib=256, pids=32, output_bytes=256 * 1024, work_mib=16,
             tmp_mib=16)


def as_worker(code, *, socket_path=None, uid=NOBODY, timeout=300):
    env = {'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin',
           'GENESIS_TOOLCHAIN': str(Path(os.environ.get('GENESIS_TOOLCHAIN', ROOT.parent / 'toolchain')))}
    if socket_path:
        env['GENESIS_LAUNCHER_SOCKET'] = str(socket_path)
    proc = subprocess.run([sys.executable, '-c', textwrap.dedent(code)], capture_output=True, text=True, env=env,
                          user=uid, group=uid, extra_groups=[], cwd='/', timeout=timeout)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr[-3000:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


RUN = '''
import json
from genesis.sandbox import run, run_python, SandboxPolicy
small = SandboxPolicy(**%s)
'''


@unittest.skipUnless(os.geteuid() == 0 and sandbox.local_available(),
                     'needs root and runc to start the launcher: release blocked until this suite runs')
class LauncherSeparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp(prefix='genesis-launcher-', dir='/tmp'))
        cls.base.chmod(0o755)
        for d in ('run', 'log', 'custody', 'trust'):
            (cls.base / d).mkdir()
        (cls.base / 'custody').chmod(0o700)
        (cls.base / 'custody' / 'key.pem').write_text('not a real key'); (cls.base / 'custody' / 'key.pem').chmod(0o600)
        (cls.base / 'trust' / 'roles.json').write_text('{}'); (cls.base / 'trust' / 'roles.json').chmod(0o444)
        cls.lean_root = str(Path(os.environ.get('GENESIS_TOOLCHAIN', ROOT.parent / 'toolchain')) / 'lean-4.34.1-linux')
        cls.config = LauncherConfig(socket_path=str(cls.base / 'run' / 'launcher.sock'),
                                    log_path=str(cls.base / 'log' / 'launcher.jsonl'), worker_uid=NOBODY,
                                    policy_ceiling=CEILING, programs=(sandbox.PYTHON, '/bin/sh'),
                                    mounts={'/opt/lean': cls.lean_root}, budget_runs=50)
        cls.launcher = Launcher(cls.config)
        cls.thread = threading.Thread(target=cls.launcher.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.launcher.stop()
        cls.thread.join(5)
        import shutil
        shutil.rmtree(cls.base, ignore_errors=True)

    def worker(self, body):
        return as_worker(RUN % json.dumps(SMALL) + textwrap.dedent(body), socket_path=self.config.socket_path)

    def log(self):
        return [json.loads(l) for l in Path(self.config.log_path).read_text().splitlines()]

    def test_unprivileged_worker_runs_code_only_through_the_launcher(self):
        out = self.worker('''
            import os
            r = run_python("import os, json\\nopen('/work/out/r.json','w').write(json.dumps({'uid': os.getuid()}))", small)
            print(json.dumps({'status': r['status'], 'launcher': r.get('launcher'), 'worker_uid': os.getuid(),
                              'inner': json.loads(r['_output_bytes']['r.json'])}))
        ''')
        self.assertEqual(out['status'], 'SUCCESS')
        self.assertEqual(out['worker_uid'], NOBODY)
        self.assertEqual(out['inner'], {'uid': NOBODY})
        self.assertEqual(out['launcher']['peer_uid'], NOBODY)
        self.assertEqual(out['launcher']['separation'], 'ROOT_LAUNCHER_UNPRIVILEGED_WORKER')
        entry = next(e for e in self.log() if e['seq'] == out['launcher']['log_seq'])
        self.assertEqual((entry['decision'], entry['status'], entry['peer']['uid']), ('RUN', 'SUCCESS', NOBODY))

    def test_without_the_launcher_the_worker_cannot_sandbox_or_run_runc(self):
        out = as_worker('''
            import json, subprocess
            from genesis.sandbox import run_python, available
            r = run_python('print(1)')
            p = subprocess.run(['runc', 'list'], capture_output=True)
            print(json.dumps({'available': available(), 'status': r['status'], 'runc_rc': p.returncode}))
        ''')
        self.assertEqual(out['status'], 'SANDBOX_UNAVAILABLE')
        self.assertFalse(out['available'])
        self.assertNotEqual(out['runc_rc'], 0)

    def refused(self, body):
        out = self.worker(body + '\nprint(json.dumps({"status": r["status"], "reason": r.get("reason")}))\n')
        self.assertEqual(out['status'], 'LAUNCHER_REFUSED', out)
        return out['reason']

    def test_policy_above_the_ceiling_is_refused(self):
        reason = self.refused('r = run_python("print(1)", SandboxPolicy(**dict(%s, memory_mib=16384)))' % json.dumps(SMALL))
        self.assertIn('ceiling', reason)
        self.assertIn('memory_mib', reason)

    def test_program_mount_and_environment_allowlists(self):
        self.assertIn('program not allowed', self.refused('r = run({}, ["/usr/bin/perl", "-e", "1"], small)'))
        self.assertIn('mount not in the launcher allowlist',
                      self.refused('r = run({}, ["/bin/sh", "-c", "true"], small, ro_mounts={"/opt/x": "/etc"})'))
        self.assertIn('mount not in the launcher allowlist',
                      self.refused('r = run({}, ["/bin/sh", "-c", "true"], small, ro_mounts={"/opt/lean": "/root"})'))
        self.assertIn('environment key not allowed',
                      self.refused('r = run({}, ["/bin/sh", "-c", "true"], small, env={"LD_PRELOAD": "/x.so"})'))
        self.assertIn('PATH_PREFIX',
                      self.refused('r = run({}, ["/bin/sh", "-c", "true"], small, env={"PATH_PREFIX": ["/usr/sbin"]})'))

    def test_only_the_configured_worker_uid_is_served(self):
        out = as_worker('''
            import json, socket, struct
            s = socket.socket(socket.AF_UNIX); s.connect(%r)
            body = json.dumps({"schema": "genesis-launch-request-v1", "argv": ["/bin/sh"]}).encode()
            s.sendall(struct.pack(">I", len(body)) + body)
            n = struct.unpack(">I", s.recv(4))[0]; data = b""
            while len(data) < n: data += s.recv(n - len(data))
            print(data.decode())
        ''' % self.config.socket_path, uid=1234)
        self.assertFalse(out['ok'])
        self.assertIn('peer uid 1234', out['refused'])

    def test_oversized_and_malformed_requests_are_refused_and_logged(self):
        for payload in (struct.pack('>I', 1 << 31), struct.pack('>I', 5) + b'nope!'):
            out = as_worker('''
                import json, socket
                s = socket.socket(socket.AF_UNIX); s.connect(%r); s.sendall(bytes.fromhex(%r))
                n = int.from_bytes(s.recv(4), "big"); data = b""
                while len(data) < n: data += s.recv(n - len(data))
                print(data.decode())
            ''' % (self.config.socket_path, payload.hex()), socket_path=None)
            self.assertFalse(out['ok'])
        reasons = [e.get('reason', '') for e in self.log() if e['decision'] == 'REFUSED']
        self.assertTrue(any('too large' in r for r in reasons))

    def test_the_worker_cannot_alter_the_launcher_log(self):
        out = as_worker('''
            import json
            try:
                open(%r, "a").write("forged\\n"); result = "WROTE"
            except OSError as e:
                result = type(e).__name__
            print(json.dumps({"result": result}))
        ''' % self.config.log_path)
        self.assertEqual(out['result'], 'PermissionError')
        prev = None
        import hashlib
        for i, line in enumerate(Path(self.config.log_path).read_bytes().splitlines(), 1):
            entry = json.loads(line)
            self.assertEqual((entry['seq'], entry['prev']), (i, prev))
            prev = hashlib.sha256(line).hexdigest()

    def test_lean_check_runs_from_the_unprivileged_worker(self):
        out = self.worker('''
            from genesis.models import GraphTask
            from genesis.verification.lean import check_witness_formally
            task = GraphTask(task_id="t", family="f", domain="c4_host_v2", n=4,
                             edges=((0, 1), (0, 3), (1, 2), (2, 3)), split="DEV")
            r = check_witness_formally(task, [[0, 1], [1, 2], [2, 3]])
            print(json.dumps({"status": r["status"], "axioms": r.get("axioms")}))
        ''')
        self.assertEqual(out['status'], 'CHECKED', out)

    def test_role_layout_report(self):
        evidence = self.base / 'evidence'; evidence.mkdir(exist_ok=True); os.chown(evidence, NOBODY, NOBODY)
        report = role_separation_report(worker_uid=NOBODY, socket_path=self.config.socket_path,
                                        log_path=self.config.log_path,
                                        secret_paths=[self.base / 'custody' / 'key.pem', self.base / 'custody'],
                                        trust_root=self.base / 'trust', evidence_roots=[evidence])
        self.assertTrue(report['ok'], report['failed'])
        (self.base / 'custody').chmod(0o755); (self.base / 'custody' / 'key.pem').chmod(0o644)
        try:
            bad = role_separation_report(worker_uid=NOBODY, secret_paths=[self.base / 'custody' / 'key.pem'])
            self.assertFalse(bad['ok'])
            self.assertFalse(role_separation_report(worker_uid=0)['ok'])
        finally:
            (self.base / 'custody').chmod(0o700); (self.base / 'custody' / 'key.pem').chmod(0o600)


@unittest.skipUnless(os.geteuid() == 0 and sandbox.local_available(), 'needs root and runc')
class LauncherLifecycle(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='genesis-launcher-', dir='/tmp')); self.base.chmod(0o755)
        (self.base / 'run').mkdir(); (self.base / 'log').mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)

    def config(self, **kw):
        return LauncherConfig(socket_path=str(self.base / 'run' / 's'), log_path=str(self.base / 'log' / 'l.jsonl'),
                              worker_uid=NOBODY, policy_ceiling=CEILING, programs=(sandbox.PYTHON,), mounts={}, **kw)

    def serve(self, config):
        launcher = Launcher(config)
        t = threading.Thread(target=launcher.serve_forever, daemon=True); t.start()
        self.addCleanup(lambda: (launcher.stop(), t.join(5)))
        return launcher

    def test_budget_is_enforced_by_the_launcher(self):
        cfg = self.config(budget_runs=1)
        self.serve(cfg)
        code = RUN % json.dumps(SMALL) + '''
statuses = [run_python("print(1)", small)["status"] for _ in range(2)]
print(json.dumps(statuses))
'''
        self.assertEqual(as_worker(code, socket_path=cfg.socket_path), ['SUCCESS', 'LAUNCHER_REFUSED'])

    def test_tampered_log_is_detected_by_the_chain_or_by_worker_anchors(self):
        from genesis.launcher import verify_log
        cfg = self.config()
        launcher = self.serve(cfg)
        code = RUN % json.dumps(SMALL) + '''
anchors = [[r["launcher"]["log_seq"], r["launcher"]["log_head"]] for r in
           (run_python("print(1)", small), run_python("print(2)", small))]
print(json.dumps(anchors))
'''
        anchors = as_worker(code, socket_path=cfg.socket_path)
        launcher.stop()
        log = Path(cfg.log_path)
        original = log.read_bytes()
        verify_log(log, anchors=anchors)
        lines = original.splitlines()
        # Rewriting the newest entry keeps the chain intact: only the worker-held head exposes it.
        log.write_bytes(b'\n'.join(lines[:-1] + [lines[-1].replace(b'"RUN"', b'"RAN"')]) + b'\n')
        verify_log(log)
        with self.assertRaisesRegex(RuntimeError, 'worker recorded'):
            verify_log(log, anchors=anchors)
        # Rewriting an older entry breaks the chain, and the launcher will not start on it.
        log.write_bytes(b'\n'.join([lines[0].replace(b'"RUN"', b'"RAN"')] + lines[1:]) + b'\n')
        with self.assertRaisesRegex(RuntimeError, 'hash chain'):
            Launcher(cfg)

    def test_socket_group_keeps_other_accounts_from_connecting(self):
        cfg = self.config(socket_gid=NOBODY)
        self.serve(cfg)
        code = RUN % json.dumps(SMALL) + 'print(json.dumps(run_python("print(1)", small)["status"]))'
        self.assertEqual(as_worker(code, socket_path=cfg.socket_path), 'SUCCESS')
        out = as_worker('''
            import json, socket
            s = socket.socket(socket.AF_UNIX)
            try:
                s.connect(%r); r = "CONNECTED"
            except OSError as e:
                r = type(e).__name__
            print(json.dumps(r))
        ''' % cfg.socket_path, uid=1234)
        self.assertEqual(out, 'PermissionError')
        refusals = [json.loads(l) for l in Path(cfg.log_path).read_text().splitlines()]
        self.assertFalse(any(e['peer']['uid'] == 1234 for e in refusals))

    def test_socket_directory_must_be_root_controlled(self):
        (self.base / 'run').chmod(0o777)
        with self.assertRaisesRegex(PermissionError, 'root-owned'):
            Launcher(self.config())

    def test_launcher_refuses_to_run_unprivileged(self):
        out = as_worker('''
            import json
            from genesis.launcher import Launcher, LauncherConfig
            try:
                Launcher(LauncherConfig(socket_path="/tmp/x.sock", log_path="/tmp/x.log", worker_uid=65534,
                                        policy_ceiling={}, programs=(), mounts={})); r = "STARTED"
            except PermissionError as e:
                r = str(e)
            print(json.dumps(r))
        ''')
        self.assertIn('must run as root', out)


class AccessModel(unittest.TestCase):
    def test_traversal_and_mode_bits(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            base = Path(d); base.chmod(0o755)
            f = base / 'f'; f.write_text('x'); f.chmod(0o644)
            self.assertTrue(can_access(f, NOBODY, set(), 'r'))
            self.assertFalse(can_access(f, NOBODY, set(), 'w'))
            base.chmod(0o700)
            self.assertFalse(can_access(f, NOBODY, set(), 'r'))     # cannot traverse the parent


if __name__ == '__main__':
    unittest.main()
