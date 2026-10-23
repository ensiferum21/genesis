"""B20_R116: the five-minute attempt (design): the remaining instances computed from the recorded runs, the
configuration rule, the analysis with record candidates flagged never claimed, and the registered output."""
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r116_gset_attempt as M  # noqa: E402


class Design(unittest.TestCase):
    def test_best_earlier_covers_the_recorded_runs(self):
        from genesis import gset as GS
        best = GS.best_known()
        e = M.best_earlier()
        self.assertEqual(set(e), {f'G{k}' for k in range(1, 55)})
        self.assertTrue(all(e[g] <= best[g] for g in e))             # no recorded value above a best known value
        self.assertGreaterEqual(sum(e[g] >= best[g] for g in e), 27)  # at least B20_R110's 27

    def test_configuration_rule(self):
        with mock.patch.object(M, 'R113', ROOT / 'evidence' / 'does_not_exist'):
            cfgs, classifier = M.configurations()
        self.assertEqual(set(cfgs), {'random', 'toroidal', 'planar'})
        self.assertEqual(cfgs['planar']['rs'], 1)                     # without B20_R113: B20_R105's planar choice
        self.assertIn('centroids', classifier)

    def test_analysis(self):
        best = {'G1': 100, 'G2': 50}
        rows = [{'instance': 'G1', 'value': 100, 'earlier': 99}, {'instance': 'G2', 'value': 51, 'earlier': 49}]
        a = M.analyse(rows, best)
        self.assertEqual((a['reach_best_known'], a['gains_over_earlier'], a['gaps']), (2, 2, {'G1': 0, 'G2': -1}))
        self.assertEqual(a['record_candidates'], [{'instance': 'G2', 'value': 51, 'best_known': 50}])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
