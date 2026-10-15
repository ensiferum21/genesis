"""B15 / R-04: the second-machine reproduction driver verifies before it runs anything."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'deployment'))
import reproduce  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FakeCheckpoint:
    """A miniature checkpoint in the make_checkpoint.py format."""

    def __init__(self, base):
        self.base = base
        repo = base / 'repo'; repo.mkdir()
        files = {'README.md': b'fake\n', 'scripts/tool.py': b'print(1)\n', 'src/pkg/__init__.py': b''}
        for rel, data in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True); (repo / rel).write_bytes(data)
        git = lambda *a: subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True,
                                        text=True).stdout.strip()
        git('init', '-q'); git('add', '-A')
        git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '-m', 'fake')
        self.commit, self.tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
        git('bundle', 'create', str(base / 'h.bundle'), '--all')
        self.members = {f'genesis/{k}': v for k, v in files.items()}
        self.members['genesis/source-history.bundle'] = (base / 'h.bundle').read_bytes()
        self.members['genesis/CHECKPOINT_RECORD.json'] = json.dumps({'commit': self.commit, 'tree': self.tree}).encode()

    def write(self, name, members=None, manifest=None, extra=()):
        members = dict(self.members if members is None else members)
        man = manifest or {k: {'sha256': sha(v), 'bytes': len(v)} for k, v in sorted(members.items())}
        path = self.base / name
        with zipfile.ZipFile(path, 'w') as z:
            for k, v in sorted(members.items()):
                z.writestr(k, v)
            z.writestr('genesis/CHECKPOINT_MANIFEST.json', json.dumps(man))
            for k, v in extra:
                z.writestr(k, v)
        return path


class Reproduce(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/tmp'); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.base.chmod(0o755)
        self.fake = FakeCheckpoint(self.base)

    def drive(self, zip_path, expected=None, name='work'):
        report = self.base / f'{name}.json'
        code = reproduce.main(['--checkpoint', str(zip_path), '--expected-sha256',
                               expected or sha(zip_path.read_bytes()), '--work', str(self.base / name),
                               '--toolchain', str(self.base / 'no-toolchain'), '--report', str(report)])
        return code, json.loads(report.read_text())

    def failed_step(self, report):
        bad = [s for s in report['steps'] if not s['ok']]
        return bad[0]['step'] if bad else None

    def test_verified_checkpoint_reaches_the_toolchain_step(self):
        code, report = self.drive(self.fake.write('good.zip'))
        self.assertEqual(code, 1)
        self.assertEqual(report['verdict'], 'NOT_REPRODUCED')
        self.assertEqual([s['ok'] for s in report['steps']], [True, True, True, False])
        self.assertEqual(self.failed_step(report), '4 toolchain')
        self.assertEqual(report['commit'], self.fake.commit)
        self.assertIsNone(report['operator_attestation'])

    def test_wrong_out_of_band_hash_stops_before_extraction(self):
        code, report = self.drive(self.fake.write('good.zip'), expected='0' * 64)
        self.assertEqual(self.failed_step(report), '1 checkpoint hash')
        self.assertFalse((self.base / 'work' / 'genesis').exists())

    def test_member_not_matching_the_manifest(self):
        members = dict(self.fake.members)
        manifest = {k: {'sha256': sha(v), 'bytes': len(v)} for k, v in members.items()}
        members['genesis/README.md'] = b'changed\n'
        _, report = self.drive(self.fake.write('m.zip', members, manifest))
        self.assertEqual(self.failed_step(report), '2 extraction and manifest')

    def test_consistent_rewrite_is_caught_by_the_git_history(self):
        members = dict(self.fake.members); members['genesis/scripts/tool.py'] = b'import os; os.system("x")\n'
        _, report = self.drive(self.fake.write('r.zip', members))
        self.assertEqual(self.failed_step(report), '3 source history')
        self.assertIn('differs from the committed tree', report['steps'][-1]['detail'])

    def test_extra_file_is_caught_by_the_git_history(self):
        members = dict(self.fake.members); members['genesis/src/pkg/backdoor.py'] = b'x = 1\n'
        _, report = self.drive(self.fake.write('x.zip', members))
        self.assertEqual(self.failed_step(report), '3 source history')

    def test_unsafe_member_names(self):
        for i, evil in enumerate(('genesis/../escape', '/abs', 'outside/file')):
            _, report = self.drive(self.fake.write(f'u{i}.zip', extra=[(evil, b'x')]), name=f'w{i}')
            self.assertEqual(self.failed_step(report), '2 extraction and manifest', evil)
        self.assertFalse((self.base / 'escape').exists())

    def test_work_directory_must_be_new_and_traversable(self):
        (self.base / 'exists').mkdir()
        with self.assertRaisesRegex(SystemExit, 'must not exist'):
            reproduce.main(['--checkpoint', 'x', '--expected-sha256', '0', '--work', str(self.base / 'exists'),
                            '--toolchain', 'y', '--report', str(self.base / 'r.json')])
        private = self.base / 'private'; private.mkdir(mode=0o700)
        with self.assertRaisesRegex(SystemExit, 'cannot traverse'):
            reproduce.main(['--checkpoint', 'x', '--expected-sha256', '0', '--work', str(private / 'w'),
                            '--toolchain', 'y', '--report', str(self.base / 'r.json')])

    def test_expected_results_cover_every_reference_section(self):
        expected = json.loads((ROOT / 'deployment/EXPECTED_RESULTS.json').read_text())
        self.assertEqual(set(expected), {'schema', 'campaign', 'certificate', 'lean', 'known_answers'})
        self.assertEqual(expected['certificate']['replay'], 'OPTIMALITY_CHECKED')
        self.assertEqual(expected['lean'], {'status': 'CHECKED', 'axioms': []})
        self.assertTrue(expected['known_answers']['ok'])

    def test_reference_campaign_matches_the_expected_results(self):
        """B20_R29: B20_R16 added six store events to the reference campaign (the active-version
        pointer) without updating EXPECTED_RESULTS.json, so every second-machine rehearsal from
        B20_R16 on failed at step 7. This keeps the campaign section of the reference in step with
        the code."""
        import sys
        import tempfile
        sys.path.insert(0, str(ROOT / 'deployment'))
        import reference_run
        expected = json.loads((ROOT / 'deployment/EXPECTED_RESULTS.json').read_text())['campaign']
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(reference_run.campaign(Path(d)), expected)


if __name__ == '__main__':
    unittest.main()
