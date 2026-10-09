import unittest
from c4_benchmark import ordered_greedy, multistart_greedy, fresh_suite, evaluate
from c4_math_wedge import normalize, verify

class BenchmarkTests(unittest.TestCase):
    def test_suite_determinism(self):
        self.assertEqual(fresh_suite(), fresh_suite())
    def test_suite_changes_seed(self):
        self.assertNotEqual(fresh_suite(1), fresh_suite(2))
    def test_bad_suite_parameters(self):
        for kwargs in ({'cases':0},{'cases':201},{'seed':True}):
            with self.assertRaises(ValueError): fresh_suite(**kwargs)
    def test_invalid_order(self):
        with self.assertRaises(ValueError): ordered_greedy(3, [(0,1)], [])
    def test_multistart_valid(self):
        host=normalize(5, list(__import__('itertools').combinations(range(5),2)))
        r=multistart_greedy(5,host,seed=7,restarts=12)
        self.assertTrue(verify(5,host,r['selected']))
        self.assertEqual(r['starts'],13)
    def test_multistart_repeat(self):
        h=[(0,1),(0,2),(1,2),(1,3)]
        self.assertEqual(multistart_greedy(4,h,seed=10),multistart_greedy(4,h,seed=10))
    def test_invalid_restarts(self):
        for x in (0,1025,True):
            with self.assertRaises(ValueError): multistart_greedy(3,[],seed=1,restarts=x)
    def test_empty_eval(self):
        with self.assertRaises(ValueError): evaluate([])
    def test_duplicate_ids(self):
        x=fresh_suite(cases=1)[0]
        with self.assertRaises(ValueError): evaluate([x,x])
    def test_comparison(self):
        r=evaluate(fresh_suite(cases=8),restarts=8)
        self.assertEqual(len(r['cases']),8)
        self.assertEqual(r['candidate_wins']+r['ties']+r['baseline_wins'],8)
        self.assertEqual(r['baseline_wins'],0)
        self.assertFalse(r['promotion_allowed'])
    def test_comparison_determinism(self):
        s=fresh_suite(cases=4)
        self.assertEqual(evaluate(s,restarts=4),evaluate(s,restarts=4))
    def test_oversized_rejected(self):
        from itertools import combinations
        with self.assertRaises(ValueError): evaluate([{'case':'big','n':7,'host':list(combinations(range(7),2)),'family':'x'}])

if __name__=='__main__': unittest.main()
