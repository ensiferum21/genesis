"""B20_R130: joint re-analysis (`causal.joint`): with the observational regime alone it is FCI exactly; experiments
on a tested variable are left out; added experiments recover a hidden cause the observational data alone miss."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import fci as F  # noqa: E402
from genesis.causal import joint as J  # noqa: E402
from genesis.causal import methods as PCM  # noqa: E402
from genesis.causal import sem as S  # noqa: E402


class Joint(unittest.TestCase):
    def test_observational_alone_is_fci(self):
        for seed in (1, 2, 3):
            view, truth = S.instance(seed, 8, 2, 0.3, 'gauss', 3, 3000)
            X = PCM.pooled(view)
            a, _ = J.fci({'obs': X}, 8)
            g, _ = F.run(8, PCM.fisher_z(np.corrcoef(X, rowvar=False), X.shape[0]), PCM.ALPHA)
            self.assertEqual(a, F.to_answer(g))

    def test_experiments_on_tested_variables_are_left_out(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(500, 3))
        Y = X.copy()
        Y[:, 1] = Y[:, 0]                              # a regime in which 0 and 1 are identical
        t_with = J.pooled_test({'obs': X, ('do', 1): Y})
        t_without = J.pooled_test({'obs': X})
        for S_ in ((), (2,)):
            self.assertEqual(t_with(0, 1, S_, 0.01), t_without(0, 1, S_, 0.01))
        self.assertFalse(J.pooled_test({'obs': X, ('do', 2): Y})(0, 1, (), 0.01))

    def test_more_regimes_find_a_weak_dependence(self):
        # a weak hidden cause between 0 and 1: invisible in 400 observational samples, visible with five more regimes
        t = {'p': 3, 'h': 1, 'B': [[0.0] * 3 for _ in range(3)], 'G': [[0.25, 0.25, 0.0]], 'confounded': [[0, 1]],
             'noise': 'gauss', 'scales': [[1.0] * 3]}
        rng = np.random.default_rng(4)
        found = []
        for rep in range(20):
            obs = S.sample(t, 400, rng)
            regs = {'obs': obs}
            one = J.pooled_test(regs)(0, 1, (), 0.01)
            for k in range(5):
                regs[('do', 2, k)] = S.sample(t, 400, rng, intervene=2)
            found.append((one, J.pooled_test(regs)(0, 1, (), 0.01)))
        self.assertGreater(sum(not b for a, b in found), sum(not a for a, b in found))


if __name__ == '__main__':
    unittest.main()
