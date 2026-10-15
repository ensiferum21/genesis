"""B20_R31 (s15.3, W10; GV4): the generated pattern inequalities. The generator keeps exactly the
patterns the triangle rows and earlier patterns do not imply. Every kept bound holds on
triangle-free edge sets, and copies are found as host edge sets. The component returns
checker-valid witnesses within its budget. The Lean side is in tests_formal."""
import itertools
import random
import unittest

from genesis.discovery.construct import Budget
from genesis.graphs import check_witness
from genesis.invention import cuts as C
from genesis.models import GraphTask

K5 = [(a, b) for a, b in itertools.combinations(range(5), 2)]
W5 = [(0, 1), (0, 4), (0, 5), (1, 2), (1, 5), (2, 3), (2, 5), (3, 4), (3, 5), (4, 5)]


def host(n, edges, tid='t-cuts'):
    return GraphTask(task_id=tid, domain='triangle_free_host_v1', family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = {}
        cls.pats = C.generate(stats=cls.stats)

    def test_keeps_k5_and_the_5_wheel(self):
        self.assertEqual([(p['vertices'], p['edges'], p['ex']) for p in self.pats], [(5, K5, 6), (6, W5, 7)])
        self.assertAlmostEqual(self.pats[0]['lp_triangle_rows'], 20 / 3, places=5)
        self.assertAlmostEqual(self.pats[1]['lp_triangle_rows'], 7.5, places=5)

    def test_k6_and_k6_minus_an_edge_are_implied_by_k5(self):
        implied = {d['id'].split('_')[1] for d in self.stats['implied_by_earlier_patterns']}
        self.assertEqual(implied, {'14', '15'})
        k6 = [(a, b) for a, b in itertools.combinations(range(6), 2)]
        self.assertAlmostEqual(C.relaxation_lp(6, k6), 10.0, places=5)
        self.assertAlmostEqual(C.relaxation_lp(6, k6, self.pats[:1]), 9.0, places=5)
        self.assertEqual(C.extremal(k6), 9)

    def test_extremal_matches_known_values(self):
        c5 = [(i, (i + 1) % 5) for i in range(5)]
        k4 = list(itertools.combinations(range(4), 2))
        self.assertEqual((C.extremal(c5), C.extremal(k4), C.extremal(K5), C.extremal(W5)), (5, 4, 6, 7))

    def test_every_kept_bound_holds_on_triangle_free_edge_sets(self):
        rng = random.Random(3101)
        for p in self.pats:
            for _ in range(400):
                S = []
                for e in sorted(itertools.combinations(range(7), 2), key=lambda _: rng.random()):
                    if rng.random() < 0.7 and C._tf(S + [e]):
                        S.append(e)
                phi = [rng.randrange(7) for _ in range(p['vertices'])]
                self.assertLessEqual(sum(C.adj_model(set(S), phi[a], phi[b]) for a, b in p['edges']), p['ex'])

    def test_conjectures_and_recipes_cover_every_pattern(self):
        conjs = C.conjectures(self.pats)
        self.assertEqual([c['id'] for c in conjs],
                         ['pc_adj_le_one', 'pc_bridge'] + [f'pc_{p["id"]}' for p in self.pats])
        lib = [{'const': 'X1.proof', 'statement': 'pc_adj_le_one'}, {'const': 'X2.proof', 'statement': 'pc_bridge'}]
        extra = C.recipes(self.pats)
        for c, p in zip(conjs[2:], self.pats):
            (_, tactic), = extra(c, lib)
            self.assertEqual(tactic.count('X2.proof'), len(p['triangles']))
            self.assertEqual(tactic.count('X1.proof'), len(p['edges']))
            self.assertEqual(extra(c, []), [])           # needs the bridge and the bound in the library


class Copies(unittest.TestCase):
    def test_copies_are_distinct_host_edge_sets(self):
        k6 = host(6, itertools.combinations(range(6), 2))
        k5 = {'vertices': 5, 'edges': K5}
        found, cut = C.copies(k6, k5)
        self.assertFalse(cut)
        self.assertEqual(len(found), 6)
        self.assertTrue(all(set(c) <= set(k6.edges) and len(c) == 10 for c in found))
        w = host(6, W5)
        self.assertEqual(len(C.copies(w, {'vertices': 6, 'edges': W5})[0]), 1)
        self.assertEqual(len(C.copies(w, k5)[0]), 0)

    def test_enumeration_stops_on_request(self):
        k6 = host(6, itertools.combinations(range(6), 2))
        found, cut = C.copies(k6, {'vertices': 5, 'edges': K5}, limit=2)
        self.assertEqual((len(found), cut), (2, True))
        self.assertEqual(C.copies(k6, {'vertices': 5, 'edges': K5}, stop=lambda: True), ([], True))


class Component(unittest.TestCase):
    def test_strengthened_lp_and_valid_witness_within_budget(self):
        rng = random.Random(31)
        edges = [e for e in itertools.combinations(range(14), 2) if rng.random() < 0.55]
        t = host(14, edges)
        pats = C.generate()
        _, _, tri = C.cut_lp_values(t, [])
        _, added, cut = C.cut_lp_values(t, pats)
        self.assertLessEqual(cut, tri + 1e-6)
        self.assertTrue(all(complete for _, complete in added.values()))
        b = Budget(0.3)
        o = C.cut_lp_greedy(t, pats, b, seed=5)
        self.assertLess(b.used(), 0.3 + 0.25)
        self.assertEqual(check_witness(t, [tuple(e) for e in o['witness']])['value'], len(o['witness']))
        self.assertGreaterEqual(o['lp_value'] + 1e-6, len(o['witness']))


if __name__ == '__main__':
    unittest.main()
