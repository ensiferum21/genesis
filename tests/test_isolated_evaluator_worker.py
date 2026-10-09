import json, tempfile, unittest
from pathlib import Path
from scripts.isolated_evaluator_worker import run

class WorkerTests(unittest.TestCase):
    def test_score_and_no_custody_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'pool').write_text(json.dumps([{'id':'a','answer':3},{'id':'b','answer':4}]))
            (p/'candidate').write_text(json.dumps({'answers':{'a':3,'b':0}}))
            r=run(p/'pool',p/'candidate',p/'out')
            self.assertEqual((r['count'],r['correct']),(2,1))
            self.assertFalse(r['independent_custody_proven'])
    def test_reject_unknown_task(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'pool').write_text(json.dumps([{'id':'a','answer':3}]))
            (p/'candidate').write_text(json.dumps({'answers':{'unknown':3}}))
            with self.assertRaises(ValueError): run(p/'pool',p/'candidate',p/'out')
