"""B20_R47: the preregistered C4 certification-coverage study. Design: the settings, seeds, budgets and
route limits are the preregistered ones; the analysis applies B20_R35's four-part rule and the secondary
gap-closure diagnostic. Record tests are added with the result."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r47_c4_certification as R47  # noqa: E402


def row(tid, stratum, a, b, wa, wb, la, lb):
    side = lambda lu, w, lp, m: {'lower': lu[0], 'upper': lu[1], 'method': m, 'wall_s': w,
                                 'lp_step': {'bound': lp, 'verdict': 'VALID'}}
    return {'task_id': tid, 'stratum': stratum, 'a': side(a, wa, la, 'SAT_DRAT'), 'b': side(b, wb, lb, 'SAT_DRAT')}


class Design(unittest.TestCase):
    def test_preregistered_constants(self):
        self.assertEqual(R47.SETTINGS, [('erdos', {'n': 30, 'p': 0.2}), ('erdos', {'n': 36, 'p': 0.17})])
        self.assertEqual((R47.PER, R47.SEEDS, R47.SECONDS), (20, (20264701, 20264711), 60))
        self.assertEqual(R47.ROUTE, {'separation_seconds': 15, 'max_rows': 50000, 'max_total': 80000,
                                     'order': 'dense-first', 'lp_rounding_seconds': 1.0})
        self.assertEqual(R47.C4, 'c4_host_v2')

    def test_tally_and_gap_closure(self):
        rows = [row('t1', 's', (60, 60), (60, 60), 3.0, 4.0, 63, 61),
                row('t2', 's', (62, 66), (62, 63), 60.0, 60.0, 66, 63),
                row('t3', 's', (77, 77), (77, 77), 30.0, 31.0, 80, 77)]
        t = R47.tally(rows)
        self.assertEqual((t['certified_a'], t['certified_b'], t['certified_b_not_a']), (2, 2, 0))
        g = t['gap_closure']
        self.assertEqual((g['hosts_with_optimum'], g['hosts_with_lp_gap'], g['rows_lp_meets_optimum']), (2, 2, 1))
        self.assertAlmostEqual(g['mean_fraction_closed'], (2 / 3 + 1) / 2, places=4)


if __name__ == '__main__':
    unittest.main()
