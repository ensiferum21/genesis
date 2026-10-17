"""B20_R64: does E1d's advantage over HiGHS grow with host size? Design: fresh seeds, the arms (B20_R63's, a
subset), the settings, and the verdict rule."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r63_e1d_crossover as R63  # noqa: E402
import b20r64_e1d_scaling as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r64_e1d_scaling.py':
                continue
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', path.read_text()), (path.name, s))

    def test_arms_are_r63s(self):
        A, B = M.arms(), R63.arms()
        self.assertEqual(list(A), ['candidate', 'highs_2s', 'highs_8s', 'highs_32s'])
        for n, (reg, d) in A.items():
            self.assertEqual(d['descriptor_id'], B[n][1]['descriptor_id'])

    def test_settings(self):
        self.assertEqual(M.NS, (40, 50, 60))
        self.assertEqual(M.PARAMS, {'p_in': 0.8, 'p_out': 0.06})
        self.assertLessEqual(max(M.NS), 63)

    def test_beyond_space_generator_matches_the_adapter_inside_the_space(self):
        from genesis.domains import ADAPTERS
        params = dict(M.PARAMS, n=40)
        a, _, _ = ADAPTERS[M.TF].generate(7, 3, 'DEV', 'planted_cluster', params, excluded=set())
        b, _ = M.generate_beyond_space(7, 3, 'DEV', params, set())
        self.assertEqual([t.model_dump() for t in a], [t.model_dump() for t in b])
        c, _ = M.generate_beyond_space(7, 2, 'DEV', dict(M.PARAMS, n=60), set())
        self.assertEqual([t.n for t in c], [60, 60])

    def test_rule(self):
        adv = lambda *vs: {R63.arm_name(b): {'verdict': v} for b, v in zip(M.BUDGETS, vs)}
        self.assertEqual(M.crossover(adv('ADVANTAGE', 'ADVANTAGE', 'ADVANTAGE')), (None, False))
        self.assertEqual(M.crossover(adv('ADVANTAGE', 'UNRESOLVED', 'ADVANTAGE')), (8.0, False))
        self.assertEqual(M.crossover(adv('UNRESOLVED_FAILURES', 'ADVANTAGE', 'ADVANTAGE')), (2.0, True))
        o = lambda c40, c60: M.overall({40: (c40, False), 50: (None, False), 60: (c60, False)})
        self.assertEqual(o(8.0, None), 'ADVANTAGE_GROWS')
        self.assertEqual(o(8.0, 32.0), 'ADVANTAGE_GROWS')
        self.assertEqual(o(8.0, 8.0), 'UNCHANGED')
        self.assertEqual(o(None, None), 'UNCHANGED')
        self.assertEqual(o(8.0, 2.0), 'ADVANTAGE_SHRINKS')
        self.assertEqual(o(None, 32.0), 'ADVANTAGE_SHRINKS')
        self.assertEqual(M.overall({40: (8.0, True), 60: (None, False)}), 'UNRESOLVED_FAILURES')


if __name__ == '__main__':
    unittest.main()
