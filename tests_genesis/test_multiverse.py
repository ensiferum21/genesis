"""B20_R73: the multiverse analysis of E1d's DEV verdicts. Design: the contrasts are the studies' own, the
preregistered analysis reproduces each study's verdict, the rule, the universe and the labels."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r73_multiverse as M  # noqa: E402


class Design(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cs = M.contrasts()

    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r73_multiverse.py':
                continue
            text = path.read_text()
            for s in M.EXTRA_SEEDS:
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_the_contrasts(self):
        self.assertEqual(len(self.cs), 18)
        sizes = {c['id']: sum(len(v) for v in c['by'].values()) for c in self.cs}
        self.assertEqual(sizes['B20_R63 highs_8s'], 30)
        self.assertEqual(sizes['B20_R64 n60 highs_32s'], 10)
        self.assertEqual(sizes['B20_R66 highs_60s'], 20)
        self.assertEqual((sizes['B20_R68 Part A'], sizes['B20_R68 Part B']), (30, 20))
        self.assertEqual(len(next(c for c in self.cs if c['id'] == 'B20_R68 Part A')['by']), 3)

    def test_the_preregistered_analysis_reproduces_every_study_verdict(self):
        for c in self.cs:
            ci = M.interval(c['by'], 'boot-mean', 0.90, c['seed'])
            self.assertEqual(M.rule(ci, 0.5, c['failures']), c['prereg'], c['id'])

    def test_rule_and_labels(self):
        self.assertEqual(M.rule((0.6, 2), 0.5, 0), 'AHEAD')
        self.assertEqual(M.rule((-0.4, 0.4), 0.5, 0), 'NO_MATERIAL_DIFFERENCE')
        self.assertEqual(M.rule((-2, -0.6), 0.5, 0), 'BEHIND')
        self.assertEqual(M.rule((0.03, 0.9), 0.5, 0), 'UNRESOLVED')
        self.assertEqual(M.rule((0.6, 2), 0.5, 1), 'FAILURES')
        self.assertEqual((M.label(0.95), M.label(0.7), M.label(0.3)), ('ROBUST', 'MIXED', 'FRAGILE'))

    def test_universe_sizes(self):
        a = next(c for c in self.cs if c['id'] == 'B20_R68 Part A')       # stratified
        b = next(c for c in self.cs if c['id'] == 'B20_R68 Part B')       # one stratum
        self.assertEqual(len(M.analyses(a)), 108)
        self.assertEqual(len(M.analyses(b)), 54)

    def test_t_interval_is_the_textbook_one(self):
        lo, hi = M.interval({'all': [1.0, 2.0, 3.0, 4.0]}, 't-mean', 0.90, None)
        self.assertAlmostEqual((lo + hi) / 2, 2.5)
        self.assertAlmostEqual((hi - lo) / 2, 2.3533634 * (1.6666667 / 4) ** 0.5, places=4)   # t_{0.95,3} * se

    def test_preregistered_study_verdicts(self):
        pre = M.preregistered_study_verdicts()
        self.assertEqual(pre, {'B20_R63': 'crossover 8.0', 'B20_R64': 'ADVANTAGE_GROWS',
                               'B20_R66': 'REPLICATED_ADVANTAGE_THROUGH_120X', 'B20_R68': 'E1D_MATCHES_DOMAIN_HEURISTIC'})


if __name__ == '__main__':
    unittest.main()
