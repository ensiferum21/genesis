"""B20_R124: Gaussian noise (design): fresh seed, B20_R122's settings but Gaussian noise, the arms, the primary test
and verdict, the secondary tests, the validity checks, and the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r124_gaussian_hidden_causes as M  # noqa: E402


def row(seed, arm, bf1, targets=None):
    import b20r122_hidden_causes_v2 as R122
    m = R122.arm_spec(arm)[1]
    return {'seed': seed, 'arm': arm, 'valid_problems': [], 'targets': list(range(m)) if targets is None else targets,
            'scores': {'bidirected': {'f1': bf1, 'precision': bf1, 'recall': bf1}, 'directed': {'f1': 0.5}, 'shd': 3,
                       'spurious_rate': 0.5}}


class Design(unittest.TestCase):
    def test_seed_is_fresh_and_noise_is_gaussian(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r124_gaussian_hidden_causes.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r122_hidden_causes_v2 as R122
        self.assertGreaterEqual(abs(M.SEED - R122.SEED), R122.N_SEEDS)
        self.assertEqual((M.NOISE, M.P, M.H, M.K), ('gauss', R122.P, R122.H, R122.K))
        from genesis.causal import sem as S
        v, t = S.instance(M.SEED, M.P, M.H, M.DENSITY, M.NOISE, M.K, 300)
        self.assertEqual(t['noise'], 'gauss')

    def test_tests_and_verdict(self):
        def rows_with(f):
            return [row(i, arm, f(i, arm)) for i in range(12) for arm in M.ARMS]
        a = M.analyse(rows_with(lambda i, arm: {'fci': 0.1, 'flag': 0.1}.get(arm, 0.4 + 0.01 * i)))
        self.assertEqual((a['test1']['label'], a['verdict']), ('EXPERIMENTS_ADD', 'EXPERIMENTS_NEEDED'))
        self.assertEqual(a['secondary']['flag_vs_fci']['label'], 'NO_DIFFERENCE')
        a = M.analyse(rows_with(lambda i, arm: 0.2))
        self.assertEqual(a['verdict'], 'NOT_SHOWN')
        self.assertEqual(set(a['secondary']), {'flag_vs_fci', 'oracle_vs_random@4', 'suspicion_vs_random@4',
                                               'random@8_vs_random@4'})

    def test_checks(self):
        self.assertTrue(M.checks([row(1, 'random@8', 0.1)]))
        self.assertFalse(M.checks([row(1, 'random@8', 0.1, targets=[0, 1, 2, 3])]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
