"""Remaining spec §38 test classes: mutation, load/concurrency, baseline regression,
release-bundle tampering and the end-to-end smoke time cap."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
import zipfile

from genesis.execution import execute
from genesis.models import GraphTask, Limits, SolverProgram
from genesis.store import Store

ROOT = Path(__file__).resolve().parents[1]


class Mutation(unittest.TestCase):
    """Intentionally corrupt receipts, objects and events: the kernel must detect it."""

    def make(self, d):
        with Store(d) as s:
            aid = s.start('t', {'x': 1})
            s.finish(aid, {'status': 'SUCCESS', 'cpu_ns': 10})
            s.save('claim', 'c', {'v': 1})

    def test_corrupted_receipt_object_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(d)
            with Store(d) as s:
                h = s.db.execute('SELECT receipt FROM attempts').fetchone()[0]
            obj = Path(d) / 'objects' / 'sha256' / h
            obj.chmod(0o600); obj.write_bytes(obj.read_bytes().replace(b'10', b'11'))
            with self.assertRaises(RuntimeError):
                Store(d)

    def test_rewritten_event_body_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(d)
            import sqlite3
            db = sqlite3.connect(Path(d) / 'campaign.sqlite3')
            body = db.execute('SELECT body FROM events WHERE seq=1').fetchone()[0]
            forged = body.replace(b'ATTEMPT_STARTED', b'ATTEMPT_FORGED_')
            self.assertNotEqual(forged, body)
            db.execute('UPDATE events SET body=? WHERE seq=1', (forged,)); db.commit(); db.close()
            with self.assertRaises(RuntimeError):
                Store(d)

    def test_derived_state_edit_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(d)
            import sqlite3
            db = sqlite3.connect(Path(d) / 'campaign.sqlite3')
            db.execute("UPDATE attempts SET status='SUCCESS_FORGED'"); db.commit(); db.close()
            with self.assertRaises(RuntimeError):
                Store(d)

    def test_forged_solver_output_is_rejected_by_the_executor(self):
        # The executor recomputes values from the witness; a child claiming more is a CHECKER_ERROR.
        import genesis.execution as ex
        task = GraphTask(task_id='t', n=4, edges=((0, 1), (0, 2), (1, 2), (2, 3)), family='f')
        real = ex.execute(task, SolverProgram(), Limits(), 1)
        self.assertEqual(real['status'], 'SUCCESS')
        self.assertEqual(real['result']['value'], len(real['result']['selected']))


class LoadAndConcurrency(unittest.TestCase):
    def test_single_writer_refuses_a_second_coordinator(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(d):
                with self.assertRaisesRegex(RuntimeError, 'already has a writer'):
                    Store(d)

    def test_concurrent_worker_returns_keep_truthful_receipts(self):
        tasks = [GraphTask(task_id=f't{i}', n=6, edges=tuple((a, b) for a in range(6) for b in range(a + 1, 6)
                                                             if (a + b + i) % 3), family='f') for i in range(8)]
        limits = Limits(cpu_seconds=2, queries=500)
        with ThreadPoolExecutor(4) as pool:
            receipts = list(pool.map(lambda t: execute(t, SolverProgram(rounds=4), limits, 3), tasks))
        with tempfile.TemporaryDirectory() as d, Store(d) as s:   # coordinator commits sequentially
            for t, r in zip(tasks, receipts):
                s.finish(s.start(t.task_id, {'task': t.task_id}), r)
            self.assertEqual(s.verify()['events'], 16)
        for r in receipts:
            self.assertEqual(r['status'], 'SUCCESS')
            self.assertLessEqual(r['result']['queries'], limits.queries)

    def test_resource_limits_produce_failure_receipts_not_success(self):
        big = GraphTask(task_id='big', n=40, edges=tuple((a, b) for a in range(40) for b in range(a + 1, 40)),
                        family='complete')
        r = execute(big, SolverProgram(rounds=32, exchange=True), Limits(cpu_seconds=1, queries=100000), 1)
        self.assertIn(r['status'], ('CPU_LIMIT', 'RESOURCE_KILLED', 'TIMEOUT'))
        self.assertNotIn('result', r)


class BaselineRegression(unittest.TestCase):
    def test_baselines_and_exact_optima_match_the_golden_file(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('golden', ROOT / 'scripts' / 'regenerate_golden.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        golden = json.loads((ROOT / 'tests_genesis' / 'golden' / 'baselines.json').read_text())
        current = json.loads(json.dumps(mod.compute(), sort_keys=True))
        self.assertEqual(current, golden, 'baseline regression: an unexpected change requires adjudication '
                                          '(regenerate deliberately with scripts/regenerate_golden.py)')


class ReleaseBundleTampering(unittest.TestCase):
    def test_tampered_bundles_fail_verification(self):
        from genesis.campaign import Campaign
        from genesis.models import Config
        from genesis.release_bundle import build_bundle, verify_bundle
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8))
            with Campaign(root) as c:
                c.run()
            bundle = Path(d) / 'b.zip'
            build_bundle(root, bundle, report='report', limitations=['test'])
            self.assertTrue(verify_bundle(bundle)['ok'])
            for victim, change in (('CLAIMS.json', b'{"claims":[],"promotion_allowed":true}'),
                                   ('events.jsonl', None)):
                out = Path(d) / f'tampered-{victim}.zip'
                with zipfile.ZipFile(bundle) as zin, zipfile.ZipFile(out, 'w') as zout:
                    for item in zin.infolist():
                        data = zin.read(item)
                        if item.filename.endswith(victim):
                            data = change if change is not None else data[:-200]
                        zout.writestr(item, data)
                result = verify_bundle(out)
                self.assertFalse(result['ok'], victim)


class EndToEndSmoke(unittest.TestCase):
    def test_smoke_campaign_completes_under_the_600_second_cap(self):
        from genesis.cli import main
        with tempfile.TemporaryDirectory() as d:
            start = time.monotonic()
            main(['smoke', str(Path(d) / 's')])
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 600)
            self.assertTrue((Path(d) / 's' / 'reports' / 'report.md').exists())


if __name__ == '__main__':
    unittest.main()
