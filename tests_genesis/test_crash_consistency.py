"""B15 / W04: crash injection at CAS write, commit, export, freeze, reservation and completion.

Every crash is a real process death (os._exit at a named point, see genesis.faults):
no finally blocks or buffered writes run. After each one the test reopens the
state and checks it is all-or-nothing and that work can continue honestly.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from genesis.campaign import Campaign
from genesis.common import atomic_write, atomic_zip, bytes_hash, canonical, code_identity, digest, is_temp_name
from genesis.custodian import evaluate, recover, register, verify
from genesis.faults import FAULT_EXIT, POINTS
from genesis.kernel import receipts as R
from genesis.models import Config, Limits
from genesis.research import make_panel
from genesis.store import Store, rebuild_from_export
from tests_genesis.signed_fixtures import campaign_export

ROOT = Path(__file__).resolve().parents[1]
CFG = dict(seed=20261101, generations=2, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8)


def crash(test, code, fault, **params):
    """Run `code` in a fresh interpreter with GENESIS_FAULT=fault; require the injected death."""
    script = 'import json, sys\nP = json.loads(sys.argv[1])\n' + textwrap.dedent(code)
    env = {k: v for k, v in os.environ.items() if k != 'GENESIS_FAULT'}
    env.update(PYTHONPATH=f"{ROOT / 'src'}:{ROOT}", GENESIS_FAULT=fault, PYTHONHASHSEED='0')
    proc = subprocess.run([sys.executable, '-c', script, json.dumps(params)], env=env, capture_output=True,
                          text=True, timeout=600, cwd=ROOT)
    test.assertEqual(proc.returncode, FAULT_EXIT, f'expected an injected crash at {fault}:\n{proc.stderr[-3000:]}')


def events(store, kind=None):
    rows = [json.loads(b) for (b,) in store.db.execute('SELECT body FROM events ORDER BY seq')]
    return [r for r in rows if kind is None or r['kind'] == kind]


def export_matches(store):
    lines = (store.root / 'events.jsonl').read_bytes().split(b'\n')
    if lines[-1] != b'':
        return False
    rows = store.db.execute('SELECT hash, body FROM events ORDER BY seq').fetchall()
    return [json.loads(x) for x in lines[:-1]] == [{'hash': h, 'event': json.loads(b)} for h, b in rows]


class FaultPoints(unittest.TestCase):
    def test_every_documented_point_exists_in_source(self):
        text = ''.join(p.read_text() for p in (ROOT / 'src/genesis').rglob('*.py'))
        for name in POINTS:
            self.assertTrue(f"point('{name}')" in text or f"fault='{name}'" in text, name)

    def test_unarmed_points_are_inert(self):
        from genesis import faults
        old = os.environ.pop('GENESIS_FAULT', None)
        try:
            for name in POINTS:
                faults.point(name)
        finally:
            if old is not None:
                os.environ['GENESIS_FAULT'] = old


class StoreCrashes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'c'
        with Store(self.root) as s:
            s.save('seed', 'a', {'v': 1}); s.set_state('phase', 'X')
        with Store(self.root) as s:
            self.before = s.verify()

    def test_torn_object_never_appears_under_its_name(self):
        value = {'big': 'x' * 200000}
        crash(self, '''
            from genesis.store import Store
            with Store(P['root']) as s: s.put({'big': 'x' * P['size']})
        ''', 'cas.write', root=str(self.root), size=200000)
        h = bytes_hash(canonical(value))
        self.assertFalse((self.root / 'objects/sha256' / h).exists())
        self.assertEqual(len(list((self.root / 'objects/tmp').iterdir())), 1)
        with Store(self.root) as s:
            self.assertEqual(s.stale_temp_objects, 1)
            self.assertEqual(list((self.root / 'objects/tmp').iterdir()), [])
            self.assertEqual(s.put(value), h)
            self.assertEqual(s.get(h), value)
            self.assertEqual(s.verify()['head'], self.before['head'])

    def test_crash_before_commit_rolls_back(self):
        crash(self, '''
            from genesis.store import Store
            with Store(P['root']) as s: s.save('k', 'new', {'v': 2})
        ''', 'store.commit', root=str(self.root))
        with Store(self.root) as s:
            self.assertIsNone(s.db.execute("SELECT 1 FROM entities WHERE kind='k'").fetchone())
            self.assertEqual(s.verify(), self.before)
            self.assertTrue(export_matches(s))
            s.save('k', 'new', {'v': 2})        # the write can simply be made again
            self.assertTrue(export_matches(s))

    def test_crash_after_commit_completes_the_export(self):
        crash(self, '''
            from genesis.store import Store
            with Store(P['root']) as s: s.save('k', 'new', {'v': 2})
        ''', 'store.committed', root=str(self.root))
        exported = (self.root / 'events.jsonl').read_bytes().count(b'\n')
        with Store(self.root) as s:
            self.assertIsNotNone(s.db.execute("SELECT 1 FROM entities WHERE kind='k'").fetchone())
            self.assertEqual(s.verify()['events'], exported + 1)
            self.assertTrue(export_matches(s))

    def test_torn_export_line_is_completed_not_rewritten(self):
        crash(self, '''
            from genesis.store import Store
            with Store(P['root']) as s: s.save('k', 'new', {'v': 2})
        ''', 'store.export', root=str(self.root))
        raw = (self.root / 'events.jsonl').read_bytes()
        self.assertFalse(raw.endswith(b'\n'))           # really torn
        with Store(self.root) as s:
            self.assertTrue(export_matches(s))
            self.assertTrue((self.root / 'events.jsonl').read_bytes().startswith(raw))   # append-only

    def test_rebuild_after_database_loss_with_torn_tail(self):
        crash(self, '''
            from genesis.store import Store
            with Store(P['root']) as s: s.save('k', 'new', {'v': 2})
        ''', 'store.export', root=str(self.root))
        (self.root / 'campaign.sqlite3').unlink()       # the database is lost too
        record = rebuild_from_export(self.root)
        self.assertTrue(record['partial_tail_dropped'])
        q = Path(record['quarantine'])
        self.assertTrue((q / 'events.jsonl.partial-tail').exists() and (q / 'events.jsonl.before-rebuild').exists())
        with Store(self.root) as s:
            self.assertEqual(s.verify(), self.before)    # only the uncommitted-in-export event is lost
            self.assertTrue(export_matches(s))


class ZipCrashes(unittest.TestCase):
    def test_interrupted_zip_leaves_no_archive_and_is_not_exported(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            with Store(root) as s:
                s.save('seed', 'a', {'v': 1})
            dest = root / 'exports' / 'campaign_export.zip'
            crash(self, '''
                from genesis.cli import export_replication
                export_replication(P['root'], P['dest'])
            ''', 'zip.write', root=str(root), dest=str(dest))
            self.assertFalse(dest.exists())
            leftovers = [p for p in (root / 'exports').iterdir() if is_temp_name(p.name)]
            self.assertEqual(len(leftovers), 1)
            from genesis.cli import export_replication
            other = Path(d) / 'again.zip'
            result = export_replication(root, other)
            import zipfile
            with zipfile.ZipFile(other) as z:
                self.assertFalse(any(is_temp_name(Path(n).name) for n in z.namelist()))
            self.assertGreater(result['files'], 0)

    def test_atomic_helpers_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'f'
            atomic_write(p, b'one')
            with self.assertRaises(FileExistsError):
                atomic_write(p, b'two')
            self.assertEqual(p.read_bytes(), b'one')
            atomic_write(p, b'two', overwrite=True)
            self.assertEqual(p.read_bytes(), b'two')
            with self.assertRaises(FileExistsError):
                with atomic_zip(p) as z:
                    z.writestr('x', b'y')
            self.assertEqual([q.name for q in Path(d).iterdir()], ['f'])


class CampaignResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.reference = Path(cls.tmp.name) / 'reference'
        Campaign.initialize(cls.reference, Config(**CFG))
        with Campaign(cls.reference) as c:
            cls.ref_summary = c.run()
            cls.ref_trials = [t for (t,) in c.store.db.execute('SELECT trial_id FROM attempts')]
            cls.ref_program = c.store.state('latest_program')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def fresh(self, name):
        root = Path(self.tmp.name) / name
        Campaign.initialize(root, Config(**CFG))
        return root

    DETERMINISTIC = ('selected_policy', 'baseline', 'solver_comparison', 'better_improver_diagnostic',
                     'causal_controls', 'transfer', 'retained_in_dev')

    def same_science(self, summary, program):
        self.assertEqual(len(summary['generations']), len(self.ref_summary['generations']))
        for a, b in zip(summary['generations'], self.ref_summary['generations']):
            for k in self.DETERMINISTIC:
                self.assertEqual(a[k], b[k], k)
        self.assertEqual(program, self.ref_program)

    def test_reference_trial_ids_are_unique(self):
        self.assertEqual(len(self.ref_trials), len(set(self.ref_trials)))

    def test_crash_mid_trial_resumes_with_the_interrupted_attempt_charged(self):
        root = self.fresh('mid-trial')
        crash(self, '''
            from genesis.campaign import Campaign
            with Campaign(P['root']) as c: c.run()
        ''', 'campaign.trial:7', root=str(root))
        with Campaign(root) as c:
            with self.assertRaisesRegex(RuntimeError, 'resume'):
                c.run()                                   # never silently restarted or aborted
            self.assertEqual(c.store.state('phase'), 'DEV_RUNNING')
            summary = c.run(resume=True)
            self.assertGreater(c.reused_from_journal, 0)
            statuses = {}
            for t, st in c.store.db.execute('SELECT trial_id, status FROM attempts'):
                statuses.setdefault(t, []).append(st)
            program = c.store.state('latest_program')
        self.same_science(summary, program)
        self.assertEqual(summary['interrupted_attempts'], 1)
        self.assertEqual(summary['resumes'], 1)
        self.assertEqual(summary['total_attempts'], self.ref_summary['total_attempts'] + 1)
        # No completed attempt was executed twice; exactly one trial was re-run after its interruption.
        rerun = {t: s for t, s in statuses.items() if len(s) > 1}
        self.assertEqual(len(rerun), 1)
        self.assertEqual(sorted(next(iter(rerun.values()))), ['INTERRUPTED', 'SUCCESS'])

    def test_successor_frozen_before_the_crash_stays_frozen(self):
        root = self.fresh('frozen')
        crash(self, '''
            from genesis.campaign import Campaign
            with Campaign(P['root']) as c: c.run()
        ''', 'campaign.frozen', root=str(root))
        with Store(root) as s:
            frozen_before = [s.get(e['payload'])['version'] for e in events(s, 'DEV_SUCCESSOR_FROZEN')]
        self.assertEqual(len(frozen_before), 1)
        with Campaign(root) as c:
            summary = c.run(resume=True)
            frozen = [c.store.get(e['payload'])['version'] for e in events(c.store, 'DEV_SUCCESSOR_FROZEN')]
            program = c.store.state('latest_program')
        self.assertEqual(frozen[0], frozen_before[0])     # not re-frozen with a new identity
        self.assertEqual(len(frozen), 2)
        self.assertEqual(len(set(frozen)), 2)
        self.assertEqual(summary['generations'][0]['version'], frozen_before[0])
        self.same_science(summary, program)
        self.assertEqual(summary['interrupted_attempts'], 0)
        self.assertEqual(summary['total_attempts'], self.ref_summary['total_attempts'])

    def test_committed_generation_is_not_repeated(self):
        root = self.fresh('generation')
        crash(self, '''
            from genesis.campaign import Campaign
            with Campaign(P['root']) as c: c.run()
        ''', 'campaign.generation', root=str(root))
        with Store(root) as s:
            self.assertEqual(s.state('dev_progress')['completed'], 1)
            attempts_before = s.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
            g0 = s.state('dev_progress')
        with Campaign(root) as c:
            summary = c.run(resume=True)
            self.assertEqual(c.reused_from_journal, 0)     # generation 0 was skipped, not replayed
            program = c.store.state('latest_program')
            resumed = events(c.store, 'CAMPAIGN_RESUMED')
        self.same_science(summary, program)
        self.assertEqual(summary['total_attempts'], self.ref_summary['total_attempts'])
        self.assertGreater(summary['total_attempts'], attempts_before)
        self.assertEqual(len(resumed), 1)
        self.assertEqual(g0['completed'], 1)

    def test_crash_after_freeze_regenerates_the_report_only(self):
        root = self.fresh('complete')
        crash(self, '''
            from genesis.campaign import Campaign
            with Campaign(P['root']) as c: c.run()
        ''', 'campaign.complete', root=str(root))
        self.assertFalse((root / 'reports/report.md').exists())
        with Campaign(root) as c:
            self.assertEqual(c.store.state('phase'), 'CANDIDATE_FROZEN')
            n = c.store.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
            summary = c.run()
            self.assertEqual(c.store.db.execute('SELECT count(*) FROM attempts').fetchone()[0], n)
        self.assertTrue((root / 'reports/report.md').exists())
        self.assertEqual(summary['status'], 'DEV_EXPERIMENT_COMPLETE')

    def test_operator_interrupt_keeps_the_campaign_resumable(self):
        import genesis.campaign as campaign_module
        root = self.fresh('keyboard')
        real, calls = campaign_module.execute, {'n': 0}

        def interrupting(*a, **k):
            calls['n'] += 1
            if calls['n'] == 5:
                raise KeyboardInterrupt
            return real(*a, **k)
        campaign_module.execute = interrupting
        try:
            with Campaign(root) as c:
                with self.assertRaises(KeyboardInterrupt):
                    c.run()
                self.assertEqual(c.store.state('phase'), 'DEV_RUNNING')
        finally:
            campaign_module.execute = real
        with Campaign(root) as c:
            summary = c.run(resume=True)
        self.assertEqual(summary['interrupted_attempts'], 1)    # the HARNESS_ERROR attempt stays charged
        self.same_science(summary, c_program(root))

    def test_request_freeze_crash_then_freeze_again(self):
        from genesis.cli import request_bundle
        root = self.fresh('request')
        with Campaign(root) as c:
            c.run()
        crash(self, '''
            from genesis.campaign import Campaign
            from genesis.cli import request_bundle
            with Campaign(P['root']) as c: request_bundle(c, 5)
        ''', 'request.freeze', root=str(root))
        self.assertFalse((root / 'exports/campaign_export.zip').exists())
        with Campaign(root) as c:
            path = request_bundle(c, 5)
            request = json.loads(path.read_bytes())
            self.assertEqual(request['campaign_export_sha256'],
                             bytes_hash((root / 'exports/campaign_export.zip').read_bytes()))
            again = request_bundle(c, 5)
        self.assertEqual(again.read_bytes(), path.read_bytes())


def c_program(root):
    with Store(root) as s:
        return s.state('latest_program')


class CustodianCrashes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.root.chmod(0o700)
        k = Ed25519PrivateKey.generate(); self.key = self.root / 'fixture-key.pem'
        self.key.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                             serialization.NoEncryption()))
        self.public = base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                                   serialization.PublicFormat.Raw)).decode()
        self.tasks, _ = make_panel(781, 2, 'c4_host_v2', 'CONFIRM')
        self.pool = self.root / 'fixture-pool.json'
        self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in self.tasks]))
        source = code_identity(ROOT)['sha256']
        export, frozen = campaign_export(self.root, campaign_id='a' * 64, source_hash=source)
        manifest = self.root / 'exposure_manifest.json'
        manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []})); manifest.chmod(0o600)
        self.request = {'schema': 'genesis-evaluation-request-v3', 'campaign_id': 'a' * 64,
                        'candidate_version': frozen['candidate_version'], 'claim_id': 'utility-fixture',
                        'evidence_kind': 'sealed_evaluation', 'generation_transition': None,
                        'statement_hash': '5' * 64, 'scope': 'fixture panel', 'transfer_source_domain': None,
                        'campaign_export_sha256': bytes_hash(export.read_bytes()), 'source_hash': source,
                        'programs': frozen['programs'], 'limits': Limits().model_dump(mode='json'), 'seed': 42,
                        'task_count': 2, 'domain': 'c4_host_v2',
                        'analysis': {'primary': 'paired-edge-count', 'alpha': .05, 'family_sensitivity': True,
                                     'hypotheses': 1},
                        'exposed_graph_fingerprints': [], 'expected_evaluator_hash': source}
        register(self.root, self.request, self.key, 'TEST_FIXTURE_NOT_INDEPENDENT', exposure_manifest=manifest,
                 campaign_export=export, pool=self.pool)
        self.rid = digest(self.request)

    def run_evaluation(self, fault):
        crash(self, '''
            from genesis.custodian import evaluate
            evaluate(P['root'], P['rid'], P['pool'], P['key'], 'TEST_FIXTURE_NOT_INDEPENDENT')
        ''', fault, root=str(self.root), rid=self.rid, pool=str(self.pool), key=str(self.key))
        with self.assertRaisesRegex(FileExistsError, 'no automatic retry'):
            evaluate(self.root, self.rid, self.pool, self.key, 'fixture')

    def recovered(self):
        receipt = recover(self.root, self.rid, self.pool, self.key, 'TEST_FIXTURE_NOT_INDEPENDENT')
        payload = verify(receipt, self.public)
        self.assertEqual(R.check_receipt(payload, 'sealed_evaluation'), [])
        self.assertEqual(payload['outcome'], R.derive_outcome(payload))
        self.assertEqual(json.loads((self.root / 'evaluations' / self.rid / 'public_receipt.json').read_bytes()),
                         receipt)
        again = recover(self.root, self.rid, self.pool, self.key, 'TEST_FIXTURE_NOT_INDEPENDENT')
        self.assertEqual(again, receipt)                  # idempotent: never re-signed
        return payload

    def test_crash_after_reservation_publishes_an_invalid_receipt(self):
        self.run_evaluation('custodian.reserve')
        payload = self.recovered()
        self.assertEqual((payload['completed_rows'], payload['raw_evidence_complete'], payload['outcome']),
                         (0, False, 'INVALID'))

    def test_crash_mid_evaluation_publishes_an_invalid_receipt(self):
        self.run_evaluation('custodian.evaluate:2')
        payload = self.recovered()
        self.assertEqual((payload['completed_rows'], payload['raw_evidence_complete'], payload['outcome']),
                         (2, False, 'INVALID'))
        with Store(self.root / 'evaluations' / self.rid) as ev:
            self.assertEqual(len(events(ev, 'EVALUATION_RECOVERED')), 1)

    def test_crash_after_signing_publishes_the_complete_result(self):
        self.run_evaluation('custodian.sign')
        self.assertFalse((self.root / 'evaluations' / self.rid / 'public_receipt.json').exists())
        payload = self.recovered()
        self.assertEqual((payload['completed_rows'], payload['raw_evidence_complete']), (4, True))
        self.assertIn(payload['outcome'], ('SUPPORTED', 'NOT_SUPPORTED', 'INCONCLUSIVE'))

    def test_crash_after_publishing_keeps_the_published_receipt(self):
        self.run_evaluation('custodian.publish')
        published = json.loads((self.root / 'evaluations' / self.rid / 'public_receipt.json').read_bytes())
        payload = self.recovered()
        self.assertEqual(payload, verify(published, self.public))

    def test_recover_requires_the_committed_pool(self):
        self.run_evaluation('custodian.reserve')
        other, _ = make_panel(9182, 2, 'c4_host_v2', 'CONFIRM')
        swapped = self.root / 'swapped.json'
        swapped.write_bytes(canonical([t.model_dump(mode='json') for t in other]))
        with self.assertRaisesRegex(ValueError, 'committed at registration'):
            recover(self.root, self.rid, swapped, self.key, 'fixture')

    def test_nothing_to_recover_before_reservation(self):
        with self.assertRaisesRegex(ValueError, 'never reserved'):
            recover(self.root, self.rid, self.pool, self.key, 'fixture')


if __name__ == '__main__':
    unittest.main()
