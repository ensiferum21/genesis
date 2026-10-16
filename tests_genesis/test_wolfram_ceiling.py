"""B20_R54: the Wolfram ceiling pilot. Design: B20_R53's rules and keep rule; fresh seeds; POOL5 is exactly B20_R53's
pool construction; the evaluation targets avoid both pools and the development targets and have no declared
relation to any of them; the verdict follows the preregistered rule. Record tests are added with the result."""
from pathlib import Path
import sys
import unittest

from genesis.learning import equational as Q
from genesis.learning.partitions import EquationalAdapter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r53_wolfram_headroom as R53  # noqa: E402
import b20r54_wolfram_ceiling as M  # noqa: E402


class Design(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pools, cls.dev, cls.ev, cls.dropped = M.material(M.SEEDS[0])

    def test_rules_seeds_and_pools(self):
        self.assertIs(M.RULES, R53.RULES)
        self.assertIs(M.R53.run_gap, R53.run_gap)
        self.assertFalse(set(M.SEEDS) & set(M.PRIOR_SEEDS))
        self.assertTrue(set(R53.SEEDS) <= set(M.PRIOR_SEEDS))
        self.assertEqual(M.POOLS, {'5': 5, '6': 6})
        self.assertEqual(M.CAP, 1800)

    def test_pool5_is_b20r53s_construction(self):
        self.assertEqual(self.pools['5'], R53.material(M.SEEDS[0])[0])
        sizes = [Q.size(l) + Q.size(r) for l, r in self.pools['6'][:-R53.RULES['false_conjectures']]]
        self.assertEqual(max(sizes), 6)
        self.assertEqual(len(self.pools['6']) - R53.RULES['false_conjectures'], 233)

    def test_targets_are_unrelated_to_all_research_material(self):
        self.assertEqual((len(self.dev), len(self.ev)), (10, 15))
        ad = EquationalAdapter()
        visible = self.pools['5'] + self.pools['6'] + self.dev
        for t in self.ev:
            self.assertTrue(Q.holds(t, 'nand'))
            self.assertFalse(any(ad.relation(t, v) for v in visible))
        self.assertTrue(all(r in ('EXACT', 'ALPHA', 'INSTANCE', 'GENERALIZES') for _, r in self.dropped))


def synthetic(o5, o6):
    return [{'seed': i, 'libraries': {'oracle5': {'proved': a}, 'oracle6': {'proved': b}, 'exhaust5': {'proved': a},
                                      'exhaust6': {'proved': b}, 'gap5': {'proved': a}, 'gap6': {'proved': b},
                                      'repeat5': {'proved': a}, 'empty': {'proved': 0}}}
            for i, (a, b) in enumerate(zip(o5, o6))]


class Verdict(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(M.verdict(synthetic([10] * 4, [12, 13, 12, 11]))['verdict'], 'CEILING_HEADROOM')
        self.assertEqual(M.verdict(synthetic([10] * 4, [11, 10, 11, 9]))['verdict'], 'NO_CEILING_HEADROOM')
        self.assertEqual(M.verdict(synthetic([10] * 4, [12, 12, 11, 10]))['verdict'], 'WEAK_CEILING_HEADROOM')
        self.assertEqual(M.verdict(synthetic([10] * 4, [16, 10, 10, 10]))['verdict'], 'WEAK_CEILING_HEADROOM')
        v = M.verdict(synthetic([10] * 4, [12, 13, 12, 11]))
        self.assertEqual(v['ceiling_headroom'], [2, 3, 2, 1])
        self.assertEqual(v['descriptive']['exhaust6-exhaust5'], [2, 3, 2, 1])
        self.assertEqual(v['noise'], [0] * 4)


if __name__ == '__main__':
    unittest.main()
