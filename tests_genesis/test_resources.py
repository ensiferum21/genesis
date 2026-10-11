"""B16 / W07: resource accounting and arm fairness."""
import ast
from pathlib import Path
import tempfile
import unittest

from genesis import resources as RS
from genesis.campaign import Campaign
from genesis.models import Config
from genesis.store import Store

SRC = Path(__file__).resolve().parents[1] / 'src' / 'genesis'
MODEL_CLIENTS = {'anthropic', 'openai', 'cohere', 'mistralai', 'google', 'transformers', 'torch', 'vllm',
                 'llama_cpp', 'ollama', 'litellm', 'langchain'}

TASK = {'task_id': 't-1', 'domain': 'c4_host_v2', 'n': 5, 'edges': [[0, 1]], 'family': 'f', 'split': 'CONFIRM'}
LIMITS = {'queries': 100, 'cpu_seconds': 1}


def solver(arm, task=TASK, limits=LIMITS, seed=7):
    return {'kind': 'solver', 'arm': arm, 'task': task, 'limits': limits, 'seed': seed, 'program': {}}


class Account(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def store(self, name='s'):
        s = Store(Path(self.tmp.name) / name)
        self.addCleanup(s.close)
        return s

    def test_every_attempt_is_charged_and_classified(self):
        s = self.store()
        s.finish(s.start('a', solver('candidate')), {'status': 'SUCCESS', 'cpu_ns': 10, 'wall_ns': 20,
                                                     'peak_rss_bytes': 1000, 'result': {'value': 3, 'queries': 4}})
        s.finish(s.start('b', solver('baseline')), {'status': 'TIMEOUT', 'cpu_ns': 30, 'wall_ns': 40})
        s.finish(s.start('c', {'kind': 'exact-check', 'task': TASK}), {'status': 'SUCCESS', 'wall_ns': 500})
        s.start('d', {'kind': 'solver', 'task': TASK, 'limits': LIMITS, 'seed': 1})     # discovery, interrupted
        s.interrupt_running()
        s.finish(s.start('e', {'kind': 'something-new'}), {'status': 'SUCCESS'})
        a = RS.account(s)
        self.assertEqual(a['inference']['attempts'], 2)
        self.assertEqual(a['inference']['failures'], 1)
        self.assertEqual((a['inference']['cpu_ns'], a['inference']['queries']), (40, 4))
        self.assertEqual(a['inference']['by_arm']['baseline']['by_status'], {'TIMEOUT': 1})
        self.assertEqual(a['ground_truth']['wall_ns'], 500)
        self.assertFalse(a['ground_truth']['charged_to_arm'])
        self.assertEqual(a['ground_truth']['cpu_unknown'], 1)
        self.assertEqual(a['discovery']['by_status'], {'INTERRUPTED': 1})
        self.assertEqual(a['unclassified']['attempts'], 1)                  # never dropped
        self.assertEqual(a['memory']['peak_bytes_by_category'], {'inference': 1000})
        total = sum(a[c]['attempts'] for c in ('discovery', 'inference', 'verification', 'ground_truth',
                                               'retrieval', 'model_calls', 'unclassified'))
        self.assertEqual(total, s.db.execute('SELECT count(*) FROM attempts').fetchone()[0])
        for c in ('retrieval', 'model_calls', 'verification'):
            self.assertEqual(a[c]['status'], 'NONE_RECORDED')
        self.assertEqual(a['human_time']['status'], 'NOT_MEASURED')
        self.assertEqual(RS.account(s), a)                                   # deterministic

    def test_human_time_is_declared_not_measured(self):
        s = self.store()
        a = RS.account(s, declared_human_seconds=5400, declared_by='research operator')
        self.assertEqual(a['human_time'], {'status': 'DECLARED', 'seconds': 5400, 'declared_by': 'research operator'})
        for bad in ((-1, 'x'), (10, None), ('ten', 'x')):
            with self.assertRaises(ValueError):
                RS.account(s, declared_human_seconds=bad[0], declared_by=bad[1])


class Fairness(unittest.TestCase):
    def run_arms(self, cand, base):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with Store(Path(tmp.name) / 's') as s:
            for i, req in enumerate(cand + base):
                s.finish(s.start(f'x{i}', req), {'status': 'SUCCESS', 'cpu_ns': 10 if req['arm'] == 'candidate' else 5,
                                                 'wall_ns': 1})
            return RS.arm_fairness(s)

    def test_paired_equal_runs_pass(self):
        out = self.run_arms([solver('candidate')], [solver('baseline')])
        self.assertEqual(out['problems'], [])
        self.assertEqual((out['paired_tasks'], out['cpu_ratio']), (1, 2.0))
        self.assertFalse(out['ground_truth_charged_to_arm'])

    def test_unequal_treatment_is_reported(self):
        cases = (([solver('candidate')], [solver('baseline', limits={'queries': 10, 'cpu_seconds': 1})], 'same limits'),
                 ([solver('candidate')], [solver('baseline', seed=8)], 'different seeds'),
                 ([solver('candidate')], [solver('baseline', task=dict(TASK, edges=[[0, 2]]))], 'presented differently'),
                 ([solver('candidate'), solver('candidate')], [solver('baseline')], 'exactly one attempt'),
                 ([solver('candidate')], [], 'exactly one attempt'))
        for cand, base, frag in cases:
            out = self.run_arms(cand, base)
            self.assertTrue(any(frag in p for p in out['problems']), (frag, out['problems']))


class CampaignAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name) / 'campaign'
        Campaign.initialize(root, Config(seed=20261103, generations=1, tasks_per_panel=3, proposals_per_epoch=2,
                                         research_trials=8))
        with Campaign(root) as c:
            c.run()
        with Store(root) as s:
            cls.account = RS.account(s)
            cls.attempts = s.db.execute('SELECT count(*) FROM attempts').fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dev_campaign_separates_discovery_from_ground_truth(self):
        a = self.account
        self.assertEqual(a['discovery']['status'], 'MEASURED')
        self.assertGreater(a['discovery']['cpu_ns'], 0)
        self.assertEqual(a['ground_truth']['status'], 'MEASURED')
        self.assertFalse(a['ground_truth']['charged_to_arm'])
        self.assertEqual(a['unclassified']['attempts'], 0)
        self.assertEqual(a['model_calls']['status'], 'NONE_RECORDED')
        total = sum(a[c]['attempts'] for c in ('discovery', 'inference', 'verification', 'ground_truth',
                                               'retrieval', 'model_calls', 'unclassified'))
        self.assertEqual(total, self.attempts)


class NoModelClient(unittest.TestCase):
    def test_no_module_imports_a_model_client(self):
        found = []
        for path in sorted(SRC.rglob('*.py')):
            for node in ast.walk(ast.parse(path.read_text(), str(path))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else []
                found += [(path.name, n) for n in names if n.split('.')[0] in MODEL_CLIENTS]
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
