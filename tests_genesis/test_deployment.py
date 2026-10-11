"""B15 / W04 / R-04: supported platform definition, dependency lock and host checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import deployment as D  # noqa: E402
from genesis import sandbox  # noqa: E402


class Lock(unittest.TestCase):
    def setUp(self):
        if not sys.pycache_prefix:      # the supported runtime (and the matrix) sets PYTHONPYCACHEPREFIX
            saved = sys.pycache_prefix
            sys.pycache_prefix = tempfile.mkdtemp(prefix='genesis-test-pycache-')
            self.addCleanup(setattr, sys, 'pycache_prefix', saved)
        self.text = D.LOCK_PATH.read_text()
        self.fps = json.loads(D.FINGERPRINTS_PATH.read_text())

    def test_running_environment_matches_lock(self):
        result = D.check_lock()
        self.assertTrue(result['ok'], result['problems'])

    def test_one_python_version_everywhere(self):
        lock = D.parse_lock(self.text)
        self.assertEqual(lock['python'], self.fps['python'])
        _, requires = D.project_dependencies()
        self.assertEqual(requires, f">={lock['python']},<3.{int(lock['python'].split('.')[1]) + 1}")
        spec = json.loads(D.SPEC_PATH.read_text())
        self.assertEqual(spec['requirements']['python'], lock['python'])
        self.assertIn(f"python:{lock['python']}-", (ROOT / 'containers/Containerfile').read_text())

    def test_lock_covers_every_pyproject_dependency(self):
        from packaging.requirements import Requirement
        pins = D.parse_lock(self.text)['pins']
        for dep in D.project_dependencies()[0]:
            req = Requirement(dep)
            self.assertIn(D._norm(req.name), pins)
            self.assertTrue(req.specifier.contains(pins[D._norm(req.name)]))

    def test_header_and_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            D.parse_lock('numpy==1\n')
        head = self.text.splitlines()[0]
        with self.assertRaises(ValueError):
            D.parse_lock(f'{head}\nnumpy==1\nnumpy==2\n')

    def test_version_drift_detected(self):
        text = self.text.replace('numpy==', 'numpy==0.0.1+', 1)
        problems = D.check_lock(text, self.fps)['problems']
        self.assertTrue(any(p.startswith('numpy: installed') for p in problems), problems)

    def test_python_drift_detected(self):
        head = self.text.splitlines()[0]
        text = self.text.replace(head, head.replace('python=3.13', 'python=3.12'))
        problems = D.check_lock(text, self.fps)['problems']
        self.assertTrue(any('python 3.13 != locked 3.12' in p for p in problems), problems)

    def test_content_drift_detected(self):
        fps = json.loads(json.dumps(self.fps))
        fps['distributions']['networkx']['content_sha256'] = '0' * 64
        problems = D.check_lock(self.text, fps)['problems']
        self.assertIn('networkx: installed bytes differ from the locked content', problems)

    def test_shadowed_import_detected(self):
        fps = json.loads(json.dumps(self.fps))
        fps['distributions']['packaging']['top_level'] = ['json']   # stdlib module, not from this wheel
        problems = D.check_lock(self.text, fps)['problems']
        self.assertTrue(any('json is imported from' in p for p in problems), problems)

    def test_pin_outside_pyproject_range_detected(self):
        text = self.text.replace('cryptography==', 'cryptography==51.0.0\n#', 1)
        problems = D.check_lock(text, self.fps)['problems']
        self.assertTrue(any('cryptography: locked 51.0.0 outside pyproject range' in p for p in problems), problems)

    # Fingerprint exclusions are exercised on a real temporary distribution in
    # tests_genesis/test_external_review_b15.py (B15-REV-01).


class Host(unittest.TestCase):
    MOUNTS_V1 = [('/', 'ext4', ['rw']), ('/sys/fs/cgroup/cpu', 'cgroup', ['rw', 'cpu']),
                 ('/sys/fs/cgroup/cpuacct', 'cgroup', ['rw', 'cpuacct']),
                 ('/sys/fs/cgroup/memory', 'cgroup', ['rw', 'memory']),
                 ('/sys/fs/cgroup/pids', 'cgroup', ['rw', 'pids']), ('/tmp', 'tmpfs', ['rw'])]

    def test_cgroup_layouts(self):
        self.assertEqual(D.cgroup_layout(self.MOUNTS_V1), ('v1', ['cpu', 'cpuacct', 'memory', 'pids']))
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'cgroup.controllers').write_text('cpuset cpu io memory pids\n')
            self.assertEqual(D.cgroup_layout([('/', 'ext4', []), (d, 'cgroup2', [])], root=d),
                             ('v2', ['cpu', 'cpuset', 'io', 'memory', 'pids']))
        self.assertEqual(D.cgroup_layout([('/', 'ext4', [])]), (None, []))

    def test_filesystem_type_longest_prefix(self):
        self.assertEqual(D.filesystem_type('/tmp/x/y', self.MOUNTS_V1), 'tmpfs')
        self.assertEqual(D.filesystem_type('/home/x', self.MOUNTS_V1), 'ext4')

    def test_store_on_tmpfs_is_unsupported(self):
        report = D.platform_report(store_root='/tmp/campaign', mounts=self.MOUNTS_V1)
        check = next(c for c in report['checks'] if c['check'] == 'store_filesystem')
        self.assertEqual(check['status'], 'FAIL')
        self.assertIn('store_filesystem', report['failed'])
        self.assertEqual(report['verdict'], 'UNSUPPORTED')

    def test_wrong_machine_is_unsupported(self):
        spec = json.loads(D.SPEC_PATH.read_text())
        spec['requirements']['machine'] = 'aarch64'
        report = D.platform_report(spec, mounts=self.MOUNTS_V1)
        self.assertIn('machine', report['failed'])
        self.assertEqual(report['verdict'], 'UNSUPPORTED')

    def test_unknown_cgroup_layout_is_unverified_not_supported(self):
        report = D.platform_report(mounts=[('/', 'ext4', [])])
        self.assertIn('cgroup', report['unverified'])
        self.assertNotEqual(report['verdict'], 'SUPPORTED')

    def test_this_host_report_is_reproducible_data(self):
        report = D.platform_report(store_root=ROOT)
        names = [c['check'] for c in report['checks']]
        for required in ('os', 'machine', 'python', 'kernel', 'glibc', 'dependency_lock', 'runc', 'cgroup',
                         'seccomp', 'store_filesystem', 'toolchain_pins', 'fault_injection_disabled'):
            self.assertIn(required, names)
        json.dumps(report)

    def test_armed_fault_injection_is_unsupported(self):
        import os
        os.environ['GENESIS_FAULT'] = 'store.commit'
        try:
            report = D.platform_report(mounts=self.MOUNTS_V1)
        finally:
            del os.environ['GENESIS_FAULT']
        self.assertIn('fault_injection_disabled', report['failed'])

    def test_container_digest_status_is_consistent(self):
        spec = json.loads(D.SPEC_PATH.read_text())
        containerfile = (ROOT / 'containers/Containerfile').read_text()
        if spec['container']['digest'] is None:
            self.assertIn('PIN_REQUIRED', containerfile)
            self.assertTrue(spec['container']['status'].startswith('BLOCKED'))
        else:
            self.assertIn(spec['container']['digest'], containerfile)


class CgroupV2Stats(unittest.TestCase):
    def test_v2_reader(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'cgroup.controllers').write_text('cpu memory pids\n')
            g = base / 'genesis-sandbox' / 'gabc'
            g.mkdir(parents=True)
            (g / 'cpu.stat').write_text('usage_usec 1500\nuser_usec 1000\nsystem_usec 500\n')
            (g / 'memory.peak').write_text('4096\n')
            (g / 'memory.events').write_text('low 0\nhigh 0\nmax 2\noom 1\noom_kill 1\n')
            stats = sandbox._cgroup_stat('gabc', base)
            self.assertEqual(stats, {'cpu_ns': 1_500_000, 'peak_memory_bytes': 4096, 'memory_failcnt': 2,
                                     'oom_killed': True})
            (g / 'memory.events').write_text('max 0\noom_kill 0\n')
            self.assertFalse(sandbox._cgroup_stat('gabc', base)['oom_killed'])

    def test_v2_missing_group_reports_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'cgroup.controllers').write_text('cpu\n')
            self.assertEqual(sandbox._cgroup_stat('none', d), {'cpu_ns': None, 'peak_memory_bytes': None,
                                                               'memory_failcnt': None, 'oom_killed': None})


if __name__ == '__main__':
    unittest.main()
