import unittest
from c4_budget_search import run, compare
from c4_hard_cases import sample_cases

class QueryBudget(unittest.TestCase):
    def test_deterministic(self):
        c=sample_cases(count=1)[0]
        for method in ('swap','multistart'):
            self.assertEqual(run(c['n'],c['host'],seed=3,budget=100,method=method),run(c['n'],c['host'],seed=3,budget=100,method=method))
    def test_budget(self):
        c=sample_cases(count=2)[1]
        for method in ('swap','multistart'):
            for budget in (1,2,17,50):
                r=run(c['n'],c['host'],budget=budget,method=method)
                self.assertLessEqual(r['queries'],budget)
    def test_empty(self):
        for method in ('swap','multistart'):
            self.assertEqual(run(0,[],method=method)['size'],0)
    def test_invalid(self):
        for kwargs in ({'budget':0},{'budget':True},{'seed':True},{'method':'unknown'}):
            with self.assertRaises(ValueError):run(4,[(0,1)],**kwargs)
    def test_comparison(self):
        r=compare(sample_cases(count=3),budget=100)
        self.assertEqual(r['swap_wins']+r['multistart_wins']+r['ties'],3)
        self.assertFalse(r['promotion_allowed'])
    def test_duplicate(self):
        c=sample_cases(count=1)[0]
        with self.assertRaises(ValueError):compare([c,c])
    def test_no_cases(self):
        with self.assertRaises(ValueError):compare([])
    def test_tiny_complete(self):
        from itertools import combinations
        edges=list(combinations(range(4),2))
        for method in ('swap','multistart'):
            r=run(4,edges,budget=100,method=method)
            self.assertLessEqual(r['size'],5)
