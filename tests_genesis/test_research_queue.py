"""The persistent research queue (`autonomy/queue.py`; directive item 12): persistence and resumption, dependencies
and capabilities, stagnation (committed directions keep running; nothing deleted), diagnosis, bounded reactivation
never repeated for a tag; the repository's queue file loads and is consistent."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import queue as Q  # noqa: E402


class ResearchQueue(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.path = Path(self.d.name) / 'q.json'

    def tearDown(self):
        self.d.cleanup()

    def test_dependencies_capabilities_and_resumption(self):
        q = Q.Queue(self.path)
        q.add('a', 'first', priority=1, unlocks=['cap'])
        q.add('b', 'after a', depends_on=['a'])
        q.add('c', 'needs cap', requires=['cap'], priority=5)
        self.assertEqual([d['id'] for d in q.ready()], ['a'])
        q.start('a')
        q.save()
        q = Q.Queue(self.path)                              # resumed from disk
        self.assertEqual(q.get('a')['status'], 'running')
        with self.assertRaises(ValueError):
            q.start('b')
        q.finish('a', 'SHOWN', True, artifacts=['evidence/a'])
        self.assertEqual(q.next()['id'], 'c')
        self.assertEqual([d['id'] for d in q.ready()], ['c', 'b'])
        with self.assertRaises(ValueError):
            q.add('a', 'again')
        with self.assertRaises(ValueError):
            q.add('z', 'bad dep', depends_on=['nope'])

    def test_stagnation_keeps_commitments_and_artifacts(self):
        q = Q.Queue(self.path)
        for i in range(3):
            q.add(f's{i}', 'study', line='inv')
        q.add('later', 'more of the same', line='inv')
        q.add('registered', 'preregistered', line='inv', committed=True)
        for i in range(3):
            q.start(f's{i}')
            q.finish(f's{i}', 'NOT_SHOWN', False, artifacts=[f'evidence/s{i}'])
        self.assertTrue(q.doc['lines']['inv']['stagnant'])
        self.assertEqual(q.get('later')['status'], 'dormant')
        self.assertEqual(q.get('later')['failure'], 'stagnated')
        self.assertEqual(q.get('registered')['status'], 'queued')
        self.assertEqual(q.get('s0')['artifacts'], ['evidence/s0'])
        self.assertEqual(len(q.doc['directions']), 5)

    def test_positive_outcome_resets_the_run(self):
        q = Q.Queue(self.path)
        q.record_past('x', 'old1', 'NOT_SHOWN', False)
        q.record_past('x', 'old2', 'NOT_SHOWN', False)
        q.record_past('x', 'old3', 'SHOWN', True)
        q.record_past('x', 'old4', 'NOT_SHOWN', False)
        self.assertFalse(q.doc['lines']['x']['stagnant'])
        self.assertEqual(q.doc['lines']['x']['run'], 1)

    def test_diagnosis_and_bounded_reactivation(self):
        q = Q.Queue(self.path)
        q.add('d1', 'dormant 1', line='inv', priority=1)
        q.add('d2', 'dormant 2', line='inv', priority=3)
        q.add('d3', 'dormant 3', line='inv', priority=2)
        q.add('fix', 'the diagnosis', line='diag', unlocks=['judge-v3'])
        for i in range(3):
            q.record_past('inv', f'p{i}', 'NOT_SHOWN', False)
        self.assertEqual({q.get(x)['status'] for x in ('d1', 'd2', 'd3')}, {'dormant'})
        q.diagnose('inv', 'fix', tags=['judge-v3'])
        with self.assertRaises(ValueError):
            q.reactivate('judge-v3', 2)                     # not unlocked yet
        q.start('fix')
        q.finish('fix', 'JUDGE_WAS_THE_BOTTLENECK', True)
        self.assertEqual(q.reactivate('judge-v3', 2), ['d2', 'd3'])
        self.assertEqual(q.reactivate('judge-v3', 2), ['d1'])
        self.assertEqual(q.reactivate('judge-v3', 2), [])   # never twice for a tag
        self.assertEqual(q.summary()['next'], 'd2')

    def test_repository_queue(self):
        path = ROOT / 'research_queue.json'
        q = Q.Queue(path)
        ids = set(q.doc['directions'])
        for d in q.doc['directions'].values():
            self.assertIn(d['status'], Q.STATES)
            self.assertTrue(set(d['depends_on']) <= ids)
        self.assertEqual(json.loads(path.read_text())['schema'], 'genesis-research-queue-v1')
        self.assertIn('engine-invention', q.doc['lines'])


if __name__ == '__main__':
    unittest.main()
