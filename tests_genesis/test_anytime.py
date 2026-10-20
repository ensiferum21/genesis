"""Quality at equal time and sequential stopping (`genesis.anytime`): the MSE 2026 anytime score, paired bootstrap
verdicts against a margin, and Bonferroni-split interim looks that stop when decided."""
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from genesis import anytime as A  # noqa: E402


def host(edges, best, **values):
    return {'edges': edges, 'best_value': best, 'values': {a: {10.0: v} for a, v in values.items()}}


class Score(unittest.TestCase):
    def test_the_evaluation_formula(self):
        self.assertEqual(A.score(4, 4), 1.0)
        self.assertEqual(A.score(4, 9), 0.5)
        self.assertEqual(A.score(0, 1), 0.5)
        self.assertEqual(A.score(4, None), 0.0)
        self.assertEqual(A.cost(100, 90), 10)
        with self.assertRaises(ValueError):
            A.score(5, 4)

    def test_host_scores_refuse_a_value_above_the_best_known(self):
        hs = [host(100, 90, a=90, b=85), host(50, 40, a=None, b=40)]
        s = A.host_scores(hs, ('a', 'b'), 10.0)
        self.assertEqual(s['a'], [1.0, 0.0])
        self.assertAlmostEqual(s['b'][0], 11 / 16)
        with self.assertRaises(ValueError):
            A.host_scores([host(100, 90, a=91)], ('a',), 10.0)
        self.assertEqual(A.ranking(s)[0][0], 'b')


class Verdicts(unittest.TestCase):
    def test_margin_verdicts(self):
        self.assertEqual(A.verdict((0.02, 0.05), 0.01), 'A_BETTER')
        self.assertEqual(A.verdict((-0.05, -0.02), 0.01), 'B_BETTER')
        self.assertEqual(A.verdict((-0.005, 0.004), 0.01), 'EQUIVALENT')
        self.assertEqual(A.verdict((-0.005, 0.03), 0.01), 'UNRESOLVED')

    def test_a_clear_difference_is_found_and_none_is_not_invented(self):
        rng = random.Random(1)
        a = [0.95 + 0.04 * rng.random() for _ in range(30)]
        b = [x - 0.05 for x in a]
        self.assertEqual(A.compare(a, b, 0.01)['verdict'], 'A_BETTER')
        self.assertEqual(A.compare(b, a, 0.01)['verdict'], 'B_BETTER')
        self.assertEqual(A.compare(a, list(a), 0.01)['verdict'], 'EQUIVALENT')
        with self.assertRaises(ValueError):
            A.compare(a, b[:-1], 0.01)


class Sequential(unittest.TestCase):
    def test_level_is_split_over_the_looks(self):
        self.assertAlmostEqual(A.look_level(0.10, 1), 0.90)
        self.assertAlmostEqual(A.look_level(0.10, 3), 1 - 0.10 / 3)
        with self.assertRaises(ValueError):
            A.look_level(0.10, 0)

    def test_stops_early_when_decided_and_runs_on_otherwise(self):
        rng = random.Random(2)
        a = [0.9 + 0.1 * rng.random() for _ in range(36)]
        b = [x - 0.08 for x in a]
        r = A.sequential(a, b, (12, 24, 36), 0.01)
        self.assertEqual((r['stopped_at'], r['verdict']), (12, 'A_BETTER'))
        noise = [rng.gauss(0, 0.02) for _ in range(36)]
        c = [x + e for x, e in zip(a, noise)]
        r = A.sequential(a, c, (12, 24, 36), 0.001)
        self.assertIsNone(r['stopped_at'])
        self.assertEqual(len(r['looks']), 3)
        with self.assertRaises(ValueError):
            A.sequential(a, b, (24, 12), 0.01)

    def test_interim_looks_do_not_inflate_false_decisions(self):
        """Under no difference, the share of studies that stop with a decision at any of 3 looks stays near or
        below alpha = 0.10 (Bonferroni is conservative)."""
        rng = random.Random(3)
        wrong = 0
        trials = 200
        for t in range(trials):
            a = [rng.random() for _ in range(36)]
            b = [rng.random() for _ in range(36)]
            r = A.sequential(a, b, (12, 24, 36), 0.0, resamples=400, seed=t)
            wrong += r['verdict'] in ('A_BETTER', 'B_BETTER') and r['stopped_at'] is not None
        self.assertLess(wrong / trials, 0.15)


if __name__ == '__main__':
    unittest.main()
