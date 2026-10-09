import unittest
from c4_budgeted_search import budgeted_exchange,budgeted_multistart,compare
from c4_math_wedge import normalize,verify
from c4_hard_cases import sample_cases

class BudgetTests(unittest.TestCase):
    def test_empty(self):
        for f in (budgeted_exchange,budgeted_multistart):
            r=f(4,[],seed=1,budget=2)
            self.assertEqual(r['size'],0)
            self.assertEqual(r['checks'],0)
    def test_k4(self):
        host=normalize(4,[(i,j) for i in range(4) for j in range(i+1,4)])
        for f in (budgeted_exchange,budgeted_multistart):
            r=f(4,host,seed=2,budget=30)
            self.assertEqual(r['size'],4)
            self.assertTrue(verify(4,host,r['selected']))
            self.assertLessEqual(r['checks'],30)
    def test_invalid_budget(self):
        with self.assertRaises(ValueError):budgeted_exchange(4,[(0,1)],seed=1,budget=0)
        with self.assertRaises(ValueError):budgeted_multistart(4,[(0,1)],seed=1,budget=True)
    def test_repeatability(self):
        host=sample_cases(count=1)[0]['host']
        for f in (budgeted_exchange,budgeted_multistart):
            self.assertEqual(f(6,host,seed=11,budget=120),f(6,host,seed=11,budget=120))
    def test_comparison(self):
        result=compare(sample_cases(count=3),budget=80)
        self.assertEqual(len(result['records']),3)
        self.assertEqual(result['exchange_wins']+result['multistart_wins']+result['ties'],3)
        self.assertTrue(all(x['exchange_checks']<=80 and x['multistart_checks']<=80 for x in result['records']))
    def test_no_false_promotion(self):
        self.assertFalse(compare(sample_cases(count=1),budget=40)['promotion_allowed'])
if __name__=='__main__':unittest.main()
