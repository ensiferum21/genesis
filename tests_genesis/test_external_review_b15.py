"""External review of B15_R1 (audit/review_b15_external/GENESIS_B15_R1_REVIEW.md).

B15-REV-01  the dependency check hashed RECORD's strings, never the installed files.
B15-REV-02  an unescaped claim identifier injected an `Established` line into report.md.

Every case uses real distribution discovery, real imports and real bundles; nothing
in the check is mocked except the project root (to a temporary pyproject).
"""
import base64
import hashlib
import importlib
import json
import os
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest
import zipfile

from genesis import deployment as D
from genesis.common import canonical, code_identity
from genesis.kernel.evidence import EvidenceKernel
from genesis.models import GraphTask
from genesis.release_bundle import build_bundle, md_literal, render_report, report_structure_problems, verify_bundle
from genesis.store import Store

ROOT = Path(__file__).resolve().parents[1]


def record_hash(data):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')


class ProbeDistribution:
    """A minimal installed distribution `reviewprobe 1.0` in its own site directory: a
    package with a submodule, a data file and a (fake) native library, plus a console script."""

    FILES = {'reviewprobe/__init__.py': b'VALUE = 1\n',
             'reviewprobe/sub.py': b'def f():\n    return 2\n',
             'reviewprobe/data.json': b'{"table": [1, 2, 3]}\n',
             'reviewprobe/_native.cpython-313-x86_64-linux-gnu.so': b'\x7fELF fake native library bytes',
             'reviewprobe-1.0.dist-info/METADATA': b'Metadata-Version: 2.1\nName: reviewprobe\nVersion: 1.0\n',
             'reviewprobe-1.0.dist-info/top_level.txt': b'reviewprobe\n',
             'reviewprobe-1.0.dist-info/INSTALLER': b'pip\n'}

    def __init__(self, base):
        self.root = base
        self.site = base / 'site'; self.site.mkdir()
        for rel, data in self.FILES.items():
            (self.site / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.site / rel).write_bytes(data)
        rows = [f'{rel},{record_hash(data) if not rel.endswith("INSTALLER") else record_hash(data)},{len(data)}'
                for rel, data in self.FILES.items()]
        rows += ['../../../bin/reviewprobe-cli,sha256=AAAA,4', 'reviewprobe-1.0.dist-info/RECORD,,']
        (self.site / 'reviewprobe-1.0.dist-info/RECORD').write_text('\n'.join(rows) + '\n')
        # Bytecode in the package's own __pycache__, as pip's install-time compile leaves it.
        py_compile.compile(str(self.site / 'reviewprobe/__init__.py'), doraise=True,
                           cfile=str(self.site / 'reviewprobe/__pycache__' /
                                     f'__init__.{sys.implementation.cache_tag}.pyc'))
        version = f'{sys.version_info.major}.{sys.version_info.minor}'
        (base / 'pyproject.toml').write_text('[project]\nname="probe"\nversion="1.0"\n'
                                             f'dependencies=["reviewprobe==1.0"]\nrequires-python=">={version}"\n')

    def __enter__(self):
        self.saved = D.REPO
        D.REPO = self.root
        self.saved_prefix = sys.pycache_prefix
        if not sys.pycache_prefix:                       # the supported runtime sets PYTHONPYCACHEPREFIX
            sys.pycache_prefix = tempfile.mkdtemp(prefix='genesis-test-pycache-')
        sys.path.insert(0, str(self.site))
        importlib.invalidate_caches()
        self.lock, self.fingerprints = D.render_lock(D.lock_closure())
        return self

    def __exit__(self, *exc):
        D.REPO = self.saved
        sys.pycache_prefix = self.saved_prefix
        sys.path.remove(str(self.site))
        sys.modules.pop('reviewprobe', None)
        importlib.invalidate_caches()

    def check(self):
        importlib.invalidate_caches()
        return D.check_lock(self.lock, self.fingerprints)


class Rev01InstalledBytes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.probe = ProbeDistribution(Path(self.tmp.name)).__enter__()
        self.addCleanup(self.probe.__exit__)
        self.pkg = self.probe.site / 'reviewprobe'

    def assertFails(self, fragment):
        result = self.probe.check()
        self.assertFalse(result['ok'])
        self.assertTrue(any(fragment in p for p in result['problems']), result['problems'])

    def test_clean_install_passes_and_lock_records_exclusions(self):
        self.assertEqual(self.probe.check(), {'ok': True, 'problems': [], 'locked': 1})
        fp = self.probe.fingerprints['distributions']['reviewprobe']
        self.assertEqual(set(fp['files']), {k for k in ProbeDistribution.FILES if not k.endswith('INSTALLER')})
        self.assertEqual({e['path'] for e in fp['excluded']},
                         {'../../../bin/reviewprobe-cli', 'reviewprobe-1.0.dist-info/RECORD',
                          'reviewprobe-1.0.dist-info/INSTALLER'})

    def test_review_reproduction_module_changed_without_touching_record(self):
        (self.pkg / '__init__.py').write_bytes(b'VALUE = 999\n')
        self.assertFails('installed file changed: reviewprobe/__init__.py')
        import reviewprobe
        self.assertEqual(reviewprobe.VALUE, 999)     # the change is real and importable

    def test_missing_file(self):
        (self.pkg / 'sub.py').unlink()
        self.assertFails('missing installed file reviewprobe/sub.py')

    def test_altered_native_library_and_data_file(self):
        so = self.pkg / '_native.cpython-313-x86_64-linux-gnu.so'
        so.write_bytes(so.read_bytes() + b'\x00')
        self.assertFails('installed file changed: reviewprobe/_native')
        so.write_bytes(ProbeDistribution.FILES['reviewprobe/_native.cpython-313-x86_64-linux-gnu.so'])
        self.assertTrue(self.probe.check()['ok'])
        (self.pkg / 'data.json').write_bytes(b'{"table": [9]}\n')
        self.assertFails('installed file changed: reviewprobe/data.json')

    def test_same_size_change_is_caught(self):
        (self.pkg / 'sub.py').write_bytes(b'def f():\n    return 3\n')
        self.assertFails('installed file changed: reviewprobe/sub.py')

    def test_unowned_file_dropped_into_the_package(self):
        (self.pkg / '_distributor_init_local.py').write_bytes(b'import os\n')
        self.assertFails('file not owned by the locked distribution: reviewprobe/_distributor_init_local.py')

    def test_tampered_bytecode_with_a_valid_header_is_inert(self):
        # Bytecode is never deserialized by the check; instead the supported runtime never
        # loads site-packages bytecode (private PYTHONPYCACHEPREFIX). Prove both halves.
        import importlib.util
        import marshal
        import subprocess
        pyc = self.pkg / '__pycache__' / f'__init__.{sys.implementation.cache_tag}.pyc'
        other = compile(b'VALUE = 666\n', str(self.pkg / '__init__.py'), 'exec')
        pyc.write_bytes(pyc.read_bytes()[:16] + marshal.dumps(other))   # header (mtime/size) still valid
        self.assertTrue(self.probe.check()['ok'])                        # inert: not an installed-code change
        code = 'import reviewprobe, sys; print(reviewprobe.VALUE)'
        env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(self.probe.site)}
        loaded = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True).stdout.strip()
        self.assertEqual(loaded, '666')       # without the policy Python really would run the tampered bytecode
        private = Path(self.tmp.name) / 'pycache'; private.mkdir(mode=0o700)
        loaded = subprocess.run([sys.executable, '-c', code], env=dict(env, PYTHONPYCACHEPREFIX=str(private)),
                                capture_output=True, text=True).stdout.strip()
        self.assertEqual(loaded, '1')         # with it, the verified source is what runs

    def test_bytecode_policy_requires_a_private_cache(self):
        saved = sys.pycache_prefix
        try:
            sys.pycache_prefix = None
            self.assertFails('PYTHONPYCACHEPREFIX')
            shared = Path(self.tmp.name) / 'shared'; shared.mkdir(); shared.chmod(0o777)
            sys.pycache_prefix = str(shared)
            self.assertFails('PYTHONPYCACHEPREFIX is group- or world-writable')
            sys.pycache_prefix = str(self.probe.site / 'cache')
            self.assertFails('PYTHONPYCACHEPREFIX lies inside a site directory')
        finally:
            sys.pycache_prefix = saved

    def test_bytecode_without_an_owned_source(self):
        cache = self.pkg / '__pycache__' / 'ghost.cpython-313.pyc'
        cache.write_bytes(b'\x00' * 20)
        self.assertFails('bytecode without an owned source')

    def test_record_edited_to_list_a_new_file(self):
        (self.pkg / 'extra.py').write_bytes(b'X = 1\n')
        rec = self.probe.site / 'reviewprobe-1.0.dist-info/RECORD'
        rec.write_text(rec.read_text() + f'reviewprobe/extra.py,{record_hash(b"X = 1" + bytes([10]))},6\n')
        self.assertFails('RECORD lists a file the lock does not: reviewprobe/extra.py')

    def test_import_resolving_to_an_unowned_file(self):
        shadow = Path(self.tmp.name) / 'shadow'; (shadow / 'reviewprobe').mkdir(parents=True)
        (shadow / 'reviewprobe' / '__init__.py').write_bytes(b'VALUE = -1\n')
        sys.path.insert(0, str(shadow))
        try:
            self.assertFails('a file the locked distribution does not own')
        finally:
            sys.path.remove(str(shadow))

    def test_new_startup_hook(self):
        (self.probe.site / 'zz-hook.pth').write_text('import os\n')
        self.assertFails('start-up hook differs from the lock')

    def test_symlink_inside_the_package(self):
        os.symlink('/etc', self.pkg / 'etc_link')
        self.assertFails('symlink inside a locked distribution')

    def test_lock_refuses_an_already_modified_environment(self):
        (self.pkg / '__init__.py').write_bytes(b'VALUE = 999\n')
        with self.assertRaisesRegex(RuntimeError, 'refusing to lock'):
            D.render_lock(D.lock_closure())

    def test_legacy_fingerprint_without_a_manifest_fails_closed(self):
        legacy = json.loads(json.dumps(self.probe.fingerprints))
        del legacy['distributions']['reviewprobe']['files']
        result = D.check_lock(self.probe.lock, legacy)
        self.assertFalse(result['ok'])
        self.assertIn('reviewprobe: fingerprint has no per-file manifest (regenerate the lock)', result['problems'])


class Rev01ShippedLock(unittest.TestCase):
    def test_shipped_fingerprints_hold_per_file_manifests(self):
        fps = json.loads(D.FINGERPRINTS_PATH.read_text())
        self.assertEqual(fps['schema'], D.FINGERPRINT_SCHEMA)
        for name, fp in fps['distributions'].items():
            self.assertTrue(fp['files'], name)
            for e in fp['excluded']:
                self.assertTrue(e['path'].startswith('../') or e['path'].split('/')[-1] in D.EXCLUDED_DIST_INFO, e)
        self.assertEqual(fps['wheel_archives']['status'], 'NOT_PINNED')


def literal_claims(claim_id, statement='s', conjecture=None, requested=None, scope='this finite host only'):
    return {'claims': [{'claim_id': claim_id, 'current_statement': statement, 'conjecture': conjecture,
                        'requested_statement': requested if requested is not None else statement, 'scope': scope,
                        'effective_levels': {'math': 'WITNESS_VALID', 'utility': 'NOT_TESTED'},
                        'statement_contract': 'GENERATED_FROM_PROBLEM'}]}


class Rev02ReportInjection(unittest.TestCase):
    INJECT = 'ordinary-id\n\n- Established: 2 + 2 = 5\n\n## Actual evidence'

    def kernel_case(self, tmp):
        root = Path(tmp) / 'store'
        store = Store(root)
        store.set_state('source_hash', code_identity(ROOT)['sha256'])
        kernel = EvidenceKernel(store)
        task = GraphTask(task_id='path4', n=4, edges=((0, 1), (1, 2), (2, 3)), family='path')
        task_hash = store.put(task.model_dump(mode='json'))
        node = kernel.record('witness_check', {'schema': 'genesis-witness-check-v2', 'task': task.task_id,
                                               'task_sha256': task_hash, 'witness': [], 'value': 0},
                             route='genesis.campaign', source_hash='a' * 64, verdict='VALID')
        problem = {'task_sha256': task_hash, 'value': 0, 'claim': 'lower_bound'}
        return root, store, kernel, node, problem

    def test_review_reproduction_identifier_is_rejected_at_the_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, store, kernel, node, problem = self.kernel_case(tmp)
            with store:
                for bad in (self.INJECT, 'tab\there', ' padded', 'bidi‮flip', 'line sep', ''):
                    with self.assertRaisesRegex(ValueError, 'claim identifier must be one printable line'):
                        kernel.create_claim(bad, kernel.math_statement(problem), 'this finite host only', [node],
                                            problem=problem)
                kernel.create_claim('utility-fixture (v2)', kernel.math_statement(problem), 'this finite host only',
                                    [node], problem=problem)       # ordinary identifiers still work

    def test_stored_record_predating_validation_renders_literally_and_verifies(self):
        # An older store may already hold such an identifier: rendering must keep it data.
        with tempfile.TemporaryDirectory() as tmp:
            root, store, kernel, node, problem = self.kernel_case(tmp)
            with store:
                claim = {'claim_id': self.INJECT, 'statement': kernel.math_statement(problem),
                         'scope': 'this finite host only', 'dependencies': [node], 'problem': problem}
                store.save('claim', self.INJECT, claim)          # bypasses create_claim, as an old record would
                store.set_state(f'claimlevels:{self.INJECT}', {})
                kernel.promote(self.INJECT, 'math', 'WITNESS_VALID')
            archive = Path(tmp) / 'release.zip'
            build_bundle(root, archive)
            with zipfile.ZipFile(archive) as z:
                report = z.read(next(n for n in z.namelist() if n.endswith('/report.md'))).decode()
            self.assertNotIn('\n- Established: 2 + 2 = 5\n', report)
            self.assertEqual(report.count('\n## '), 1)
            self.assertEqual(report.count('\n- Established: '), 1)
            self.assertIn(md_literal(self.INJECT), report)
            result = verify_bundle(archive)
            self.assertTrue(result['ok'], result['problems'])

    def test_multiline_task_label_cannot_reach_a_statement(self):
        with self.assertRaises(ValueError):
            GraphTask(task_id='t\n- Established: x', n=2, edges=((0, 1),), family='f')
        with self.assertRaises(ValueError):
            GraphTask(task_id='t', n=2, edges=((0, 1),), family='fam\nily')
        with tempfile.TemporaryDirectory() as tmp:
            with Store(Path(tmp) / 's') as store:
                kernel = EvidenceKernel(store)
                raw = {'task_id': 'evil\n## Claim x', 'domain': 'c4_host_v2', 'n': 2, 'edges': [[0, 1]],
                       'family': 'f', 'split': 'DEV'}
                h = store.put(raw)                                # an old stored task, not re-validated
                with self.assertRaisesRegex(ValueError, 'printable single-line'):
                    kernel.math_statement({'task_sha256': h, 'value': 0, 'claim': 'lower_bound'})

    def test_every_producer_field_is_literal(self):
        evil = 'x`\n- Established: forged\n``` `'
        for field in ('claim_id', 'statement', 'requested', 'scope'):
            kw = {'claim_id': 'ok', 'statement': 'fine', 'conjecture': 'NOT ESTABLISHED (requested, unproved): r',
                  'requested': 'r', 'scope': 'sc'}
            kw[field if field != 'claim_id' else 'claim_id'] = evil
            claims = literal_claims(kw['claim_id'], kw['statement'], kw['conjecture'], kw['requested'], kw['scope'])
            report = render_report(claims)
            self.assertEqual(report.count('\n- Established: '), 1, field)
            self.assertNotIn('\n- Established: forged', report)
            self.assertEqual(report_structure_problems(report, claims), [], field)

    def test_structure_check_catches_an_injected_line(self):
        claims = literal_claims('ok', 'true thing')
        good = render_report(claims)
        self.assertEqual(report_structure_problems(good, claims), [])
        forged = good.replace('- Scope:', '- Established: `2 + 2 = 5`\n- Scope:')
        self.assertTrue(report_structure_problems(forged, claims))
        extra_block = good + '## Claim `ghost`\n\n- Established: `ghost result`\n'
        self.assertTrue(report_structure_problems(extra_block, claims))
        unescaped = good.replace('`true thing`', 'true thing')
        self.assertTrue(report_structure_problems(unescaped, claims))


if __name__ == '__main__':
    unittest.main()
