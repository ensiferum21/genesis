import unittest
from itertools import combinations
from c4_math_wedge import normalize, c4_by_cycles, c4_by_common_neighbors, verify, greedy, exact, verify_optimum_by_independent_enumeration

class C4WedgeTests(unittest.TestCase):
    def test_k4(self):
        h=list(combinations(range(4),2))
        r=exact(4,h)
        self.assertEqual(r['optimum'],4)
        self.assertTrue(verify_optimum_by_independent_enumeration(r))
    def test_k5(self):
        r=exact(5,list(combinations(range(5),2)))
        self.assertEqual(r['optimum'],6)
        self.assertTrue(verify_optimum_by_independent_enumeration(r))
    def test_cycle4(self):
        h=[(0,1),(1,2),(2,3),(0,3)]
        self.assertEqual(exact(4,h)['optimum'],3)
    def test_triangle(self):
        self.assertEqual(exact(3,[(0,1),(1,2),(0,2)])['optimum'],3)
    def test_empty(self):
        self.assertEqual(exact(0,[])['optimum'],0)
    def test_disjoint(self):
        self.assertEqual(exact(6,[(0,1),(2,3),(4,5)])['optimum'],3)
    def test_induced_not_required(self):
        self.assertTrue(c4_by_cycles(4,list(combinations(range(4),2))))
    def test_host_subset(self):
        with self.assertRaises(ValueError): verify(3,[(0,1)],[(1,2)])
    def test_duplicates(self):
        with self.assertRaises(ValueError): normalize(3,[(0,1),(1,0)])
    def test_invalid_vertices(self):
        with self.assertRaises(ValueError): normalize(3,[(0,3)])
    def test_cap(self):
        with self.assertRaises(ValueError): exact(7,list(combinations(range(7),2)))
    def test_tamper(self):
        r=exact(4,list(combinations(range(4),2)))
        r['optimum']-=1
        self.assertFalse(verify_optimum_by_independent_enumeration(r))
    def test_checker_agreement_exhaustive_n4(self):
        h=list(combinations(range(4),2))
        for mask in range(1<<len(h)):
            edges=[e for i,e in enumerate(h) if mask>>i&1]
            self.assertEqual(c4_by_cycles(4,edges),c4_by_common_neighbors(4,edges))
    def test_greedy_valid(self):
        h=list(combinations(range(5),2))
        self.assertTrue(verify(5,h,greedy(5,h)))

if __name__=='__main__':unittest.main()
