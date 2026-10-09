import unittest
from c4_resource_benchmark import compare,measure
from c4_budget_search import run as baseline
from c4_conflict_search import run as candidate

CASES=[{'id':'a','family':'complete','n':4,'host':[(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]},
       {'id':'b','family':'path','n':5,'host':[(0,1),(1,2),(2,3),(3,4)]}]

class ResourceTests(unittest.TestCase):
    def test_measures_baseline(self):
        r=measure(baseline,4,CASES[0]['host'],seed=1,budget=60)
        self.assertTrue(0<=r['queries']<=60)
        self.assertEqual(len(r['witness_sha256']),64)
        self.assertGreaterEqual(r['cpu_ns'],0)
        self.assertGreaterEqual(r['peak_traced_bytes'],0)
    def test_measures_candidate(self):
        self.assertLessEqual(measure(candidate,4,CASES[0]['host'],seed=1,budget=60)['size'],5)
    def test_compare(self):
        r=compare(CASES)
        self.assertEqual(r['cycle_wins']+r['baseline_wins']+r['ties'],2)
        self.assertEqual(r['records'][0]['arm_order'],['multistart','cycle_aware'])
        self.assertEqual(r['records'][1]['arm_order'],['cycle_aware','multistart'])
        self.assertFalse(r['promotion_allowed'])
        self.assertFalse(r['cpu_budget_matched'])
    def test_duplicate(self):
        with self.assertRaises(ValueError):compare(CASES+CASES[:1])
    def test_empty(self):
        with self.assertRaises(ValueError):compare([])
    def test_invalid_budget(self):
        with self.assertRaises(ValueError):compare(CASES,budget=0)
    def test_exact_cap(self):
        from itertools import combinations
        with self.assertRaises(ValueError):compare([{'id':'big','family':'complete','n':7,'host':list(combinations(range(7),2))}])
    def test_invalid_witness(self):
        def fake(*args,**kwargs):return {'selected':((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)),'size':6,'queries':1}
        with self.assertRaises(RuntimeError):measure(fake,4,CASES[0]['host'],seed=1,budget=60)
    def test_budget_violation(self):
        def fake(*args,**kwargs):return {'selected':(),'size':0,'queries':61}
        with self.assertRaises(RuntimeError):measure(fake,4,CASES[0]['host'],seed=1,budget=60)

if __name__=='__main__':unittest.main()
