import unittest
from c4_hard_cases import sample_cases, compare

class HardCases(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(sample_cases(count=5),sample_cases(count=5))
    def test_reject_invalid(self):
        for opts in ({'count':0},{'count':201},{'seed':True},{'restarts':-1}):
            with self.assertRaises(ValueError): sample_cases(**opts)
    def test_small_checked(self):
        r=compare(sample_cases(count=3),restarts=3)
        self.assertEqual(r['count'],3)
        self.assertTrue(all(x['gap']>=0 for x in r['records']))
        self.assertFalse(r['promotion_allowed'])
    def test_duplicate_id(self):
        c=sample_cases(count=1)[0]
        with self.assertRaises(ValueError):compare([c,c])
    def test_tampered_host(self):
        c=sample_cases(count=1)[0].copy();c['host']=[(0,1),(1,0)]
        with self.assertRaises(ValueError):compare([c])
    def test_empty(self):
        with self.assertRaises(ValueError):compare([])
