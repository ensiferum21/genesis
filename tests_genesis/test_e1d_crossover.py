"""B20_R63: the E1d crossover study. Design: fresh seeds, the arms (the 2 s arm is the E1d package's HiGHS
baseline, the candidate is the package's), the budget profiles, and the verdict rule."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r63_e1d_crossover as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r63_e1d_crossover.py':
                continue
            text = path.read_text()
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_arms(self):
        A = M.arms()
        self.assertEqual(list(A), ['candidate'] + [M.arm_name(b) for b in M.BUDGETS])
        self.assertEqual(M.BUDGETS, (2.0, 4.0, 8.0, 16.0, 32.0))
        for b in M.BUDGETS:
            reg, d = A[M.arm_name(b)]
            self.assertEqual((reg, d['kind'], d['parameters']), ('v2', 'milp-highs-v1', {'cpu_seconds': b}))
            self.assertEqual(d['resource_profile']['cpu_seconds'], int(b))
            self.assertGreaterEqual(d['resource_profile']['wall_seconds'], 5 * b)
        import b20r11_e1_readiness as R11
        self.assertEqual(M.mip_profile(2.0), R11.PROFILE)

    def test_rule(self):
        V = M.budget_verdict
        self.assertEqual(V([0.6, 3.0], 0), 'ADVANTAGE')
        self.assertEqual(V([0.5, 3.0], 0), 'UNRESOLVED')
        self.assertEqual(V([-0.4, 0.4], 0), 'NO_MATERIAL_DIFFERENCE')
        self.assertEqual(V([-3.0, -0.6], 0), 'MIP_AHEAD')
        self.assertEqual(V([5.0, 9.0], 1), 'UNRESOLVED_FAILURES')
        adv = {M.arm_name(b): {'verdict': 'ADVANTAGE'} for b in M.BUDGETS}
        self.assertEqual(M.overall(adv), ('ADVANTAGE_THROUGH_64X', None))
        adv['highs_16s'] = {'verdict': 'UNRESOLVED'}
        self.assertEqual(M.overall(adv), ('CROSSOVER_AT_16S', 16.0))

    def test_bootstrap_is_stratified_and_seeded(self):
        by = {'a': [1, 2, 3], 'b': [10, 10, 10]}
        est, ci = M.boot(by)
        self.assertAlmostEqual(est, 6.0)
        self.assertEqual(M.boot(by), (est, ci))
        self.assertTrue(ci[0] <= est <= ci[1])


if __name__ == '__main__':
    unittest.main()
