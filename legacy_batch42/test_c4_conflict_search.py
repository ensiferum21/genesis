import unittest
from itertools import combinations
from c4_conflict_search import run,compare
from c4_hard_cases import sample_cases
from c4_independent_replay import replay

class CycleAware(unittest.TestCase):
    def test_empty(self):self.assertEqual(run(0,[])['size'],0)
    def test_c4(self):self.assertEqual(run(4,[(0,1),(1,2),(2,3),(0,3)],budget=40)['size'],3)
    def test_k4(self):self.assertEqual(run(4,list(combinations(range(4),2)),budget=100)['size'],4)
    def test_deterministic(self):
        c=sample_cases(count=1)[0]
        self.assertEqual(run(c['n'],c['host'],seed=4),run(c['n'],c['host'],seed=4))
    def test_bounded(self):
        for c in sample_cases(count=8):
            for budget in (1,7,60):
                r=run(c['n'],c['host'],budget=budget)
                self.assertLessEqual(r['queries'],budget)
                self.assertLessEqual(r['size'],replay(c['n'],c['host'])['optimum'])
    def test_bad_params(self):
        for kw in ({'budget':0},{'budget':True},{'seed':True}):
            with self.assertRaises(ValueError):run(4,[(0,1)],**kw)
    def test_compare(self):
        r=compare(sample_cases(count=4),budget=40)
        self.assertEqual(r['cycle_wins']+r['baseline_wins']+r['ties'],4)
        self.assertFalse(r['promotion_allowed'])
    def test_duplicate(self):
        c=sample_cases(count=1)[0]
        with self.assertRaises(ValueError):compare([c,c])
