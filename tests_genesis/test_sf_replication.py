"""B20_R59: the internal replication of B20_R57. Design: B20_R57's protocol with fresh seeds only; the replication
rule. Record tests are added with the result."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r56_sf_tree_certification as R56  # noqa: E402
import b20r57_sf_hard_certification as R57  # noqa: E402
import b20r58_sf_pattern_selection as R58  # noqa: E402
import b20r59_sf_replication as M  # noqa: E402


class Design(unittest.TestCase):
    def test_fresh_seeds_only(self):
        used = set(R56.SEEDS) | set(R57.SEEDS) | set(R58.DEV_SEEDS) | set(R58.EVAL_SEEDS)
        self.assertFalse(set(M.SEEDS) & used)
        self.assertEqual(len(M.SEEDS), len(R57.SEEDS))
        prior = {tuple(R57.candidate(s, i, N, p)['elements']) for s, (N, p) in zip(R57.SEEDS, R57.SETTINGS)
                 for i in range(R57.MAX_CANDIDATES)}
        new = {tuple(R57.candidate(s, i, N, p)['elements']) for s, (N, p) in zip(M.SEEDS, R57.SETTINGS)
               for i in range(R57.MAX_CANDIDATES)}
        self.assertFalse(prior & new)

    def test_rule(self):
        s = lambda v, b='BOUND_UTILITY': {'verdict': v, 'bound': {'verdict': b}}
        self.assertEqual(M.replication_verdict(s('CERTIFICATION_UTILITY'))['replication'], 'REPLICATED')
        self.assertEqual(M.replication_verdict(s('NO_CERTIFICATION_UTILITY'))['replication'], 'NOT_REPLICATED')
        self.assertEqual(M.replication_verdict(s('DEFECT_FOUND'))['replication'], 'DEFECT_FOUND')


if __name__ == '__main__':
    unittest.main()
