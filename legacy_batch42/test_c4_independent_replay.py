import random
import unittest
from itertools import combinations
from c4_math_wedge import exact
from c4_independent_replay import cycle_masks, replay, cross_check

class IndependentReplayTests(unittest.TestCase):
    def test_complete_k4(self):
        h=list(combinations(range(4),2))
        self.assertEqual(replay(4,h)['optimum'],4)
        self.assertEqual(len(cycle_masks(4,h)),3)
    def test_complete_k5(self):
        h=list(combinations(range(5),2))
        self.assertEqual(replay(5,h)['optimum'],6)
    def test_no_cycles(self):
        self.assertEqual(replay(5,[(0,1),(1,2),(2,3)])['optimum'],3)
    def test_full_cycle(self):
        self.assertEqual(replay(4,[(0,1),(1,2),(2,3),(0,3)])['optimum'],3)
    def test_empty(self):
        self.assertEqual(replay(0,[])['optimum'],0)
    def test_tampered_optimum(self):
        r=exact(4,list(combinations(range(4),2)))
        r['optimum']+=1
        self.assertFalse(cross_check(r))
    def test_tampered_witness(self):
        r=exact(4,list(combinations(range(4),2)))
        r['selected']=r['host']
        r['optimum']=len(r['host'])
        self.assertFalse(cross_check(r))
    def test_invalid_subset(self):
        r=exact(3,[(0,1)])
        r['selected']=((0,2),)
        self.assertFalse(cross_check(r))
    def test_cap(self):
        with self.assertRaises(ValueError):replay(7,list(combinations(range(7),2)))
    def test_exhaustive_all_hosts_n4(self):
        universe=list(combinations(range(4),2))
        for mask in range(1<<len(universe)):
            h=[e for i,e in enumerate(universe) if mask>>i&1]
            self.assertTrue(cross_check(exact(4,h)))
    def test_seeded_graph_families(self):
        rng=random.Random(3709)
        universe=list(combinations(range(7),2))
        for _ in range(20):
            h=[e for e in universe if rng.random()<0.52]
            self.assertTrue(cross_check(exact(7,h)))
    def test_order_independence(self):
        h=list(combinations(range(5),2))
        self.assertEqual(replay(5,h)['optimum'],replay(5,list(reversed(h)))['optimum'])

if __name__=='__main__':unittest.main()
