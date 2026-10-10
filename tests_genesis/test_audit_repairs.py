import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from tests.test_custody_reference import ReferenceCustodyTests
from custody_reference.evaluator import canonical,file_sha
from custody_reference.private_evidence import replay_private,raw_commitment


class SemanticRepairTests(ReferenceCustodyTests):
    def rewrite(self,pool):
        self.pool.write_bytes(canonical(pool));p=json.loads(self.prereg.read_bytes())
        p['pool_sha256']=file_sha(self.pool);p['campaign_id']='changed-campaign'
        self.prereg.write_bytes(canonical(p))

    def test_unused_feature_cannot_replay(self):
        self.evaluate();pool=json.loads(self.pool.read_bytes())
        for t in pool:t['features']['unused']=0
        self.rewrite(pool)
        with self.assertRaises(FileExistsError):self.evaluate()

    def test_changed_answer_cannot_replay(self):
        self.evaluate();pool=json.loads(self.pool.read_bytes())
        for t in pool:t['answer']+=1
        self.rewrite(pool)
        with self.assertRaises(FileExistsError):self.evaluate()

    def test_unknown_field_quarantined(self):
        pool=json.loads(self.pool.read_bytes());pool[0]['features']['unregistered']=0;self.rewrite(pool)
        with self.assertRaisesRegex(ValueError,'semantic contract'):self.evaluate()

    def test_contract_cannot_reset_exposure(self):
        self.evaluate();p=self.reservation_dir/'semantic_contract.json';body=json.loads(p.read_bytes())
        body['domain']='rebranded';p.write_bytes(canonical(body))
        self.rewrite(json.loads(self.pool.read_bytes()))
        with self.assertRaisesRegex(ValueError,'contract changed'):self.evaluate()

    def test_raw_replay_reconstructs_aggregate(self):
        out,result=self.evaluate();attempt=file_sha(self.prereg)
        self.assertEqual(replay_private(self.reservation_dir,attempt),result['aggregate']['arms'])
        self.assertEqual(raw_commitment(self.reservation_dir,attempt),result['manifest']['private_evidence_sha256'])
        with sqlite3.connect(self.reservation_dir/'sealed_attempts.sqlite3') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM raw_results').fetchone()[0],8)
            self.assertEqual(db.execute('SELECT state FROM attempts').fetchone()[0],'COMPLETE')
        self.assertNotIn('secret-A',(out/'manifest.json').read_text())


class ScoreRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=str(Path(__file__).resolve().parents[1]/'legacy_batch42');sys.path.insert(0,cls.path)
        import c4_resource_benchmark
        cls.measure=staticmethod(c4_resource_benchmark.measure)
    @classmethod
    def tearDownClass(cls):sys.path.remove(cls.path)

    def test_empty_witness_claimed_nine_rejected(self):
        def fake(*args,**kwargs):return {'selected':(),'size':9,'queries':0}
        with self.assertRaises(RuntimeError):self.measure(fake,4,[(0,1)],seed=1,budget=60)

    def test_negative_boolean_fractional_costs_rejected(self):
        for charge in (-999,True,1.5):
            def fake(*args,**kwargs):return {'selected':(),'size':0,'queries':charge}
            with self.assertRaises(RuntimeError):self.measure(fake,4,[(0,1)],seed=1,budget=60)

    def test_full_witness_retained(self):
        from c4_budget_search import run
        result=self.measure(run,3,[(0,1),(0,2),(1,2)],seed=1,budget=60)
        self.assertEqual(result['size'],len(result['selected']))
        self.assertEqual(result['query_accounting'],'LEGACY_SELF_REPORTED_NOT_PROMOTABLE')
