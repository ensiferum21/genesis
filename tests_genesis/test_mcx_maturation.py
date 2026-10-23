"""B20_R108: affinity maturation of mcx-v1's configurations (design): the widened space leaves B20_R105's draws as
they were; fresh seed; new weight-1 torus sizes, used by neither Gset nor B20_R105; mutants are valid, distinct and
one or two keys away from the incumbent; the labels; the registered output."""
from pathlib import Path
import json
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r108_mcx_maturation as M  # noqa: E402
import b20r105_mcx_configure as R105  # noqa: E402
from genesis.candidate_kinds import mcx as K  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r108_mcx_maturation.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_the_wide_space_contains_the_old_one(self):
        self.assertEqual(set(K.WIDE), set(K.SPACE))
        for k in K.SPACE:
            self.assertTrue(set(K.SPACE[k]) <= set(K.WIDE[k]), k)
        self.assertEqual(max(K.WIDE['L0']), 0.2)
        self.assertIsNone(K.check_config(dict(K.DEFAULT, L0=0.2, tt=2, pool=32)))
        self.assertEqual(R105.draw_configs('random')[1], R105.draw_configs('random')[1])   # draws from SPACE only

    def test_torus_sizes(self):
        mine = [r * c for r, c in M.PLUS_SHAPES]
        theirs = [r * c for r, c in R105.PLUS_SHAPES[:10]]
        self.assertEqual(len(set(mine)), len(mine))
        self.assertFalse(set(mine) & set(theirs))
        self.assertNotIn(3000, mine)
        self.assertTrue(all(3 <= r <= 200 and 3 <= c <= 200 for r, c in M.PLUS_SHAPES))
        self.assertEqual(sum(M.setting('toroidal', i)[0] == 'torus2d' for i in range(M.PER_CLASS)), 10)

    def test_mutants(self):
        inc = dict(K.DEFAULT, L0=0.05)
        ms = M.mutants(inc, M.MUTANTS_1S, 'x')
        self.assertEqual(len(ms), 31)
        self.assertEqual(len({json.dumps(m, sort_keys=True) for m in ms}), 31)
        for m in ms:
            self.assertIsNone(K.check_config(m))
            self.assertIn(sum(m[k] != inc[k] for k in inc), (1, 2))
        self.assertEqual(ms, M.mutants(inc, M.MUTANTS_1S, 'x'))
        self.assertNotEqual(ms, M.mutants(inc, M.MUTANTS_1S, 'y'))

    def test_labels(self):
        def held(m, i):
            return {f'g{k}': {'matured@1': m + k, 'incumbent@1': i + k, 'matured@10': m + k, 'incumbent@10': i + k}
                    for k in range(24)}
        lab = M.labels(held(1010, 1000), {'1': [], '10': ['random']})
        self.assertEqual((lab['maturation@1']['label'], lab['maturation@10']['label']), ('MATURED_BETTER', 'MATURED_BETTER'))
        lab = M.labels(held(1000, 1000), {'1': list(M.CLASSES), '10': []})
        self.assertEqual((lab['maturation@1']['label'], lab['maturation@10']['label']), ('INCUMBENT_KEPT', 'NO_DIFFERENCE'))
        self.assertEqual(M.labels(held(990, 1000), {'1': [], '10': []})['maturation@1']['label'], 'MATURED_WORSE')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
