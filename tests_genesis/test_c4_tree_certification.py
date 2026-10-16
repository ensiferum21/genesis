"""B20_R48: the preregistered C4 tree-certification study. Design: the settings, seeds, budgets and route
limits are the preregistered ones (B20_R47's settings and limits, fresh seeds); soundness needs a VALID
certificate with the claimed bound, a C4-free witness of the reported value, and agreement when both routes
certify; the tally and the calibration-limit check. Record tests are added with the result."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r47_c4_certification as R47  # noqa: E402
import b20r48_c4_tree_certification as R48  # noqa: E402


def row(tid, a, c, *, verdict='VALID', bound=None, wvalid=True, wvalue=None, method='LP_DUAL_TREE_C4_EXACT'):
    return {'task_id': tid, 'stratum': 's',
            'a': {'lower': a[0], 'upper': a[1], 'method': 'SAT_DRAT', 'wall_s': 10.0},
            'c': {'lower': c[0], 'upper': c[1], 'method': method, 'wall_s': 5.0, 'nodes': 9, 'check_s': 0.1,
                  'certificate_bytes': 100, 'check': {'verdict': verdict, 'bound': c[1] if bound is None else bound},
                  'witness_valid': wvalid, 'witness_value': c[0] if wvalue is None else wvalue}}


class Design(unittest.TestCase):
    def test_preregistered_constants(self):
        self.assertEqual(R48.SETTINGS, R47.SETTINGS)
        self.assertEqual((R48.PER, R48.SEEDS, R48.SECONDS), (20, (20264801, 20264811), 60))
        self.assertEqual(R48.ROUTE, R47.ROUTE)
        self.assertEqual(R48.CALIBRATION_LIMIT, 0.9)
        self.assertFalse(set(R48.SEEDS) & set(R47.SEEDS))

    def test_soundness_rule(self):
        self.assertTrue(R48.sound_row(row('t', (60, 60), (60, 60))))
        self.assertTrue(R48.sound_row(row('t', (60, 64), (60, 60))))
        self.assertFalse(R48.sound_row(row('t', (60, 60), (61, 61))))                  # values disagree
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), verdict='REJECTED')))
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), bound=61)))
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), wvalid=False)))
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), wvalue=59)))

    def test_tally(self):
        rows = [row('t1', (60, 60), (60, 60)), row('t2', (60, 64), (61, 61)), row('t3', (60, 64), (60, 63))]
        t = R48.tally(rows)
        self.assertEqual((t['certified_a'], t['certified_c'], t['certified_c_not_a'], t['certified_a_not_c']), (1, 2, 1, 0))
        self.assertAlmostEqual(t['rate_c'], 2 / 3, places=4)
        self.assertEqual(t['by_method_c'], {'LP_DUAL_TREE_C4_EXACT': 2})


if __name__ == '__main__':
    unittest.main()
