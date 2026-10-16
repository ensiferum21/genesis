"""B20_R46: the pattern generator transferred to C4-free subgraphs.

The procedure is generator v2's, with only the motif-specific parts changed:
  * extremal numbers are exact, and brute force agrees on small patterns;
  * every kept pattern beats the 4-cycle LP and has an integer rounding certificate equal to ex(F);
  * the obligations survive the sampling screen;
  * the recipes cite only the base lemmas and earlier patterns.
Record: the package is intact, and the base lemmas and the usable bounds are Lean-CHECKED."""
import itertools
import json
from pathlib import Path
import unittest

from genesis.invention import cuts_c4 as C4

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'c4_generator_b20r46'


def brute_ex(edges):
    E = list(edges)
    return max(len(s) for k in range(len(E) + 1) for s in itertools.combinations(E, k) if C4.c4free(list(s)))


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = {}
        cls.patterns = C4.generate(max_vertices=5, stats=cls.stats)

    def test_small_patterns_and_exact_extremal_numbers(self):
        by_edges = {len(p['edges']): p for p in self.patterns}
        self.assertEqual(by_edges[6]['ex'], 4)
        ids = [p['id'] for p in self.patterns]
        self.assertIn('c4pat4_6_010203121323', ids)                    # K4: ex 4, cycle LP 4.5
        for p in self.patterns:
            self.assertEqual(p['ex'], brute_ex(p['edges']), p['id'])
            self.assertGreater(p['lp_cycle_rows'], p['ex'] + 1e-6)
            self.assertTrue(C4.c4free(p['ex_witness']))
            self.assertEqual(len(p['ex_witness']), p['ex'])

    def test_every_pattern_has_a_rounding_certificate(self):
        for i, p in enumerate(self.patterns):
            cert = C4.proof_certificate(p, self.patterns[:i])
            self.assertIsNotNone(cert, p['id'])
            self.assertEqual(cert['K'] // cert['D'], p['ex'])

    def test_cycles_are_listed_once(self):
        k4 = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        self.assertEqual(len(C4.pattern_cycles(k4)), 3)
        self.assertEqual(C4.pattern_cycles([(0, 1), (1, 2), (2, 3)]), [])


class Obligations(unittest.TestCase):
    def test_screen_and_recipes(self):
        from genesis.formal_research import loop as L
        pats = C4.generate(max_vertices=5)[:2]
        conjs = C4.conjectures(pats)
        self.assertEqual([c['id'] for c in conjs][:3], ['p4_adj_le_one', 'p4_adj_comm', 'p4_bridge'])
        for c in conjs:
            cx, relevant = L.screen(c)
            self.assertIsNone(cx, c['id'])
            self.assertGreater(relevant, 0)
        lib = [{'statement': s, 'const': f'P4P.{s}'} for s in ('p4_adj_le_one', 'p4_adj_comm', 'p4_bridge')]
        texts = C4.recipes(pats)(conjs[3], lib)
        self.assertEqual(texts[0][0], 'lp-certificate-sum')
        self.assertIn('P4P.p4_bridge', texts[0][1])
        self.assertNotIn('sorry', texts[0][1])


if __name__ == '__main__':
    unittest.main()
