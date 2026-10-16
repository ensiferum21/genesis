"""B20_R49: the preregistered ablation of the transferred rows in the tree route. Design: fresh seeds, B20_R48's
settings, budget and limits; the ablation is the same route with an empty registry (4-cycle rows only) and
its certificates are checked against that registry; soundness needs both arms sound and agreeing; the tally.
Record tests are added with the result."""
from pathlib import Path
import sys
import unittest

from genesis.common import digest
from genesis.discovery import generated_bnb_c4 as GB
from genesis.discovery import generated_certify_c4 as GC4
from genesis.models import GraphTask
from genesis.verification import lp_dual_tree_c4 as VT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r47_c4_certification as R47  # noqa: E402
import b20r48_c4_tree_certification as R48  # noqa: E402
import b20r49_c4_rows_ablation as R49  # noqa: E402


def side(lu, verdict='VALID', wvalid=True):
    return {'lower': lu[0], 'upper': lu[1], 'method': 'LP_DUAL_TREE_C4_EXACT', 'wall_s': 5.0, 'nodes': 9,
            'check': {'verdict': verdict, 'bound': lu[1]}, 'witness_valid': wvalid, 'witness_value': lu[0]}


class Design(unittest.TestCase):
    def test_preregistered_constants(self):
        self.assertEqual(R49.SEEDS, (20264901, 20264911))
        self.assertFalse(set(R49.SEEDS) & (set(R48.SEEDS) | set(R47.SEEDS)))
        self.assertEqual((R48.SETTINGS, R48.SECONDS, R48.ROUTE), (R47.SETTINGS, 60, R47.ROUTE))

    def test_the_ablation_is_the_empty_registry_and_is_checked_against_it(self):
        reg = GC4.load_registry()
        empty = R49.empty_registry(reg)
        self.assertEqual(empty['patterns'], {})
        self.assertNotEqual(digest(empty), digest(reg))
        t = GraphTask(task_id='k5', domain='c4_host_v2', family='test', split='DEV', n=5,
                      edges=tuple((u, v) for u in range(5) for v in range(u + 1, 5)))
        rec = GB.certify_with_tree(t, [], empty, seconds=30, lp_rounding_seconds=None)
        self.assertEqual(rec['upper'], 6)                                      # ex(K5, C4) = 6
        self.assertEqual(VT.check_certificate(t, rec['certificate'], empty)['verdict'], 'VALID')
        self.assertEqual(VT.check_certificate(t, rec['certificate'], reg)['verdict'], 'REJECTED')

    def test_soundness_and_tally(self):
        ok = {'task_id': 't', 'stratum': 's', 'c': side((60, 60)), 'c0': side((60, 64))}
        self.assertTrue(R49.sound_row(ok))
        self.assertFalse(R49.sound_row(dict(ok, c0=side((61, 61)))))
        self.assertFalse(R49.sound_row(dict(ok, c0=side((60, 64), verdict='REJECTED'))))
        self.assertFalse(R49.sound_row(dict(ok, c=side((60, 60), wvalid=False))))
        t = R49.tally([ok, dict(ok, task_id='u', c0=side((60, 60))), dict(ok, task_id='v', c=side((59, 62)))])
        self.assertEqual((t['certified_c'], t['certified_c0'], t['certified_c_not_c0'], t['certified_c0_not_c']),
                         (2, 1, 1, 0))


if __name__ == '__main__':
    unittest.main()
