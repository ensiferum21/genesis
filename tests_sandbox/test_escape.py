"""Sandbox escape suite (spec §38: failure blocks release; a skip also blocks release).

Every test runs a hostile program inside the OCI sandbox and asserts that the
attempt was contained and that the receipt tells the truth about it.
"""
import json
import os
from pathlib import Path
import socket
import tempfile
import textwrap
import time
import unittest

from genesis.sandbox import SandboxPolicy, available, run, run_python

POLICY = SandboxPolicy(wall_seconds=60, cpu_seconds=20, memory_mib=256, pids=32, work_mib=16, tmp_mib=16,
                       output_bytes=256 * 1024)


def probe(source, policy=POLICY, args=()):
    receipt = run_python(textwrap.dedent(source), policy, args=args)
    out = receipt.get('_output_bytes', {}).get('result.json')
    return receipt, json.loads(out) if out else None


RESULT = '''
import json
def save(obj):
    with open('/work/out/result.json', 'w') as f:
        json.dump(obj, f)
'''


@unittest.skipUnless(available(), 'runc sandbox unavailable: release blocked until this suite runs')
class Network(unittest.TestCase):
    def test_no_outbound_network_dns_or_host_proxy(self):
        proxy_port = int(os.environ.get('HTTPS_PROXY', 'http://127.0.0.1:33453').rsplit(':', 1)[-1].strip('/') or 0)
        receipt, r = probe(RESULT + f'''
import socket
res = {{}}
for name, addr in [('cloudflare_dns', ('1.1.1.1', 53)), ('google_https', ('8.8.8.8', 443)),
                   ('host_proxy', ('127.0.0.1', {proxy_port})), ('metadata', ('169.254.169.254', 80))]:
    try:
        socket.create_connection(addr, timeout=2); res[name] = 'CONNECTED'
    except OSError as e:
        res[name] = type(e).__name__
try:
    socket.getaddrinfo('github.com', 443); res['dns'] = 'RESOLVED'
except OSError as e:
    res['dns'] = type(e).__name__
import os
res['interfaces'] = sorted(os.listdir('/sys/class/net')) if os.path.isdir('/sys/class/net') else []
save(res)
''')
        self.assertEqual(receipt['status'], 'SUCCESS', receipt.get('stderr'))
        self.assertNotIn('CONNECTED', r.values())
        self.assertNotEqual(r['dns'], 'RESOLVED')


@unittest.skipUnless(available(), 'runc sandbox unavailable: release blocked until this suite runs')
class Filesystem(unittest.TestCase):
    def test_root_usr_etc_proc_sys_are_not_writable(self):
        receipt, r = probe(RESULT + '''
res = {}
for path in ['/usr/evil', '/etc/evil', '/evil', '/proc/sys/kernel/hostname', '/work/src/evil', '/dev/evil']:
    try:
        with open(path, 'w') as f: f.write('x')
        res[path] = 'WRITTEN'
    except OSError as e:
        res[path] = type(e).__name__
for path in ['/tmp/ok', '/work/out/ok']:
    with open(path, 'w') as f: f.write('ok')
    res[path] = 'WRITTEN'
save(res)
''')
        self.assertEqual(receipt['status'], 'SUCCESS', receipt.get('stderr'))
        for path, outcome in r.items():
            self.assertEqual(outcome == 'WRITTEN', path in ('/tmp/ok', '/work/out/ok'), (path, outcome))

    def test_host_secrets_evaluator_root_and_home_are_invisible(self):
        with tempfile.TemporaryDirectory() as private:
            marker = Path(private) / 'sealed_tasks.json'
            marker.write_text('{"secret": true}')
            receipt, r = probe(RESULT + '''
import os, sys
paths = sys.argv[1:] + ['/root', '/home', '/root/.ccr/ca-bundle.crt', '/home/claude/genesis', '/var/run/docker.sock',
                        '/proc/1/root/root']
res = {p: os.path.exists(p) for p in paths}
res['env'] = sorted(os.environ)
save(res)
''', args=(str(marker), private))
        self.assertEqual(receipt['status'], 'SUCCESS', receipt.get('stderr'))
        env = r.pop('env')
        self.assertFalse(any(r.values()), r)
        self.assertEqual(set(env) - {'PATH', 'HOME', 'LANG', 'PYTHONDONTWRITEBYTECODE', 'PYTHONHASHSEED', 'TMPDIR',
                                     'LC_CTYPE', 'PWD'}, set())  # PWD is set by the in-container shell shim

    def test_symlinked_outputs_are_not_followed(self):
        receipt = run_python('import os; os.symlink("/etc/passwd", "/work/out/stolen"); '
                             'open("/work/out/real.txt","w").write("ok")', POLICY)
        self.assertEqual(receipt['status'], 'SUCCESS', receipt.get('stderr'))
        self.assertNotIn('stolen', receipt['_output_bytes'])
        self.assertIn('symlink refused: stolen', receipt['output_problems'])

    def test_disk_fill_is_bounded(self):
        receipt, r = probe(RESULT + '''
res = {}
for target in ['/work/out/fill', '/tmp/fill']:
    written = 0
    try:
        with open(target, 'wb') as f:
            for _ in range(200):
                f.write(b'x' * (1 << 20)); f.flush(); written += 1
        res[target] = ['NO_LIMIT', written]
    except OSError as e:
        res[target] = [type(e).__name__, written]
import os
for t in ['/work/out/fill', '/tmp/fill']:
    try: os.remove(t)
    except OSError: pass
save(res)
''')
        self.assertEqual(receipt['status'], 'SUCCESS', receipt.get('stderr'))
        for target, (outcome, mib) in r.items():
            self.assertNotEqual(outcome, 'NO_LIMIT', target)
            self.assertLessEqual(mib, 32, target)


@unittest.skipUnless(available(), 'runc sandbox unavailable: release blocked until this suite runs')
class Privilege(unittest.TestCase):
    def test_no_root_no_capabilities_no_namespace_or_mount_tricks(self):
        receipt, r = probe(RESULT + '''
import ctypes, os
libc = ctypes.CDLL(None, use_errno=True)
res = {'uid': os.getuid(), 'euid': os.geteuid()}
status = open('/proc/self/status').read()
res['cap_eff'] = [l.split()[1] for l in status.splitlines() if l.startswith('CapEff')][0]
res['no_new_privs'] = [l.split()[1] for l in status.splitlines() if l.startswith('NoNewPrivs')][0]
res['seccomp'] = [l.split()[1] for l in status.splitlines() if l.startswith('Seccomp:')][0]
def attempt(name, fn):
    try:
        out = fn(); res[name] = 'ALLOWED' if out in (0, None) else 'DENIED:%d' % ctypes.get_errno()
    except Exception as e:
        res[name] = 'DENIED:' + type(e).__name__
attempt('setuid0', lambda: os.setuid(0))
attempt('mount', lambda: libc.mount(b'tmpfs', b'/tmp', b'tmpfs', 0, None))
attempt('unshare_user', lambda: os.unshare(os.CLONE_NEWUSER))
attempt('chroot', lambda: os.chroot('/tmp'))
attempt('ptrace_attach_1', lambda: libc.ptrace(16, 1, None, None))
attempt('keyctl', lambda: libc.syscall(250, 0, 0, 0, 0, 0))           # keyctl
attempt('bpf', lambda: libc.syscall(321, 0, 0, 0))                    # bpf
attempt('init_module', lambda: libc.syscall(175, 0, 0, 0))            # init_module
attempt('mknod', lambda: os.mknod('/tmp/dev', 0o600 | 0o020000, os.makedev(1, 3)))
attempt('reboot', lambda: libc.syscall(169, 0xfee1dead, 672274793, 0x4321fedc, 0))
res['visible_pids'] = sorted(int(p) for p in os.listdir('/proc') if p.isdigit())
save(res)
''')
        self.assertEqual(receipt['status'], 'SUCCESS', receipt.get('stderr'))
        self.assertEqual((r['uid'], r['euid']), (65534, 65534))
        self.assertEqual(int(r['cap_eff'], 16), 0)
        self.assertEqual(r['no_new_privs'], '1')
        self.assertEqual(r['seccomp'], '2')
        for name in ('setuid0', 'mount', 'unshare_user', 'chroot', 'ptrace_attach_1', 'keyctl', 'bpf', 'init_module',
                     'mknod', 'reboot'):
            self.assertTrue(r[name].startswith('DENIED'), (name, r[name]))
        self.assertLessEqual(len(r['visible_pids']), 3, r['visible_pids'])  # own pid namespace


@unittest.skipUnless(available(), 'runc sandbox unavailable: release blocked until this suite runs')
class Resources(unittest.TestCase):
    def test_fork_bomb_is_capped_by_pids(self):
        receipt, r = probe(RESULT + '''
import os, time
children = 0; error = None
try:
    for _ in range(500):
        pid = os.fork()
        if pid == 0:
            time.sleep(5); os._exit(0)
        children += 1
except OSError as e:
    error = type(e).__name__
save({'children': children, 'error': error})
''')
        self.assertIn(receipt['status'], ('SUCCESS', 'EXIT_NONZERO'), receipt.get('stderr'))
        self.assertLess(r['children'], POLICY.pids)
        self.assertIsNotNone(r['error'])

    def test_memory_hog_is_contained(self):
        receipt, r = probe(RESULT + '''
blocks = []; got = 0; error = None
try:
    for _ in range(4096):
        blocks.append(bytearray(1 << 20)); got += 1
except MemoryError:
    error = 'MemoryError'
save({'mib': got, 'error': error})
''')
        if r is not None:
            self.assertEqual(r['error'], 'MemoryError')
            self.assertLess(r['mib'], POLICY.memory_mib)
        else:
            self.assertEqual(receipt['status'], 'OOM')
        if receipt.get('peak_memory_bytes'):
            self.assertLessEqual(receipt['peak_memory_bytes'], POLICY.memory_mib * 1024 * 1024)

    def test_cpu_spin_is_killed_at_cpu_limit(self):
        policy = POLICY.model_copy(update={'cpu_seconds': 2, 'wall_seconds': 60})
        start = time.monotonic()
        receipt = run_python('while True: pass', policy)
        self.assertEqual(receipt['status'], 'CPU_LIMIT', (receipt['exit_code'], receipt.get('cpu_ns')))
        self.assertLess(time.monotonic() - start, 30)

    def test_sleep_is_killed_at_wall_limit(self):
        policy = POLICY.model_copy(update={'wall_seconds': 2})
        start = time.monotonic()
        receipt = run_python('import time; time.sleep(120)', policy)
        self.assertEqual(receipt['status'], 'TIMEOUT')
        self.assertLess(time.monotonic() - start, 30)

    def test_output_flood_is_truncated_and_reported(self):
        receipt = run_python('import sys\nwhile True: sys.stdout.write("x" * 65536)', POLICY)
        self.assertEqual(receipt['status'], 'OUTPUT_LIMIT')
        self.assertTrue(receipt['truncated'])
        self.assertLessEqual(len(receipt['stdout']), POLICY.output_bytes)

    def test_receipts_record_failures_truthfully(self):
        receipt = run_python('raise SystemExit(3)', POLICY)
        self.assertEqual((receipt['status'], receipt['exit_code']), ('EXIT_NONZERO', 3))
        self.assertIn('policy_sha256', receipt)
        self.assertIn('config_sha256', receipt)


class Unavailable(unittest.TestCase):
    def test_reports_unavailable_rather_than_running_unconfined(self):
        import genesis.sandbox as sb
        saved = sb.RUNC
        try:
            sb.RUNC = None
            self.assertEqual(sb.run_python('print(1)')['status'], 'SANDBOX_UNAVAILABLE')
        finally:
            sb.RUNC = saved


if __name__ == '__main__':
    unittest.main()
