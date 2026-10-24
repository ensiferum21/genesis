"""B20_R130: global interpretation of every regime (`causal.global_ml`): the established full-experiment estimator
recovers the planted model from population covariances; the multi-regime likelihood's gradient matches finite
differences; the fit recovers the model with every experiment; the answer's marks."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import admg as A  # noqa: E402
from genesis.causal import global_ml as GM  # noqa: E402
from genesis.causal import sem as S  # noqa: E402


def population(truth, done):
    """Exact regime covariances of environment 0 (n = 10**6 nominal)."""
    p, h = truth['p'], truth['h']
    B, G = np.array(truth['B']), np.array(truth['G']).reshape(h, p)
    Om = G.T @ G + np.eye(p)
    out = []
    for t in [None] + list(done):
        Br, Omr = B.copy(), Om.copy()
        if t is not None:
            Br[:, t] = 0.0
            Omr[t, :] = 0.0
            Omr[:, t] = 0.0
            Omr[t, t] = 1.0
        Mi = np.linalg.inv(np.eye(p) - Br)
        out.append((Mi.T @ Omr @ Mi, 10 ** 6, t))
    return out, B, Om


class Estimators(unittest.TestCase):
    def test_llc_recovers_the_population_model(self):
        truth = S.planted(5, 6, 2, 0.4, 'gauss')
        reg, B, Om = population(truth, range(6))
        Bh, Oh = GM.llc(reg, 6)
        self.assertTrue(np.allclose(Bh, B, atol=1e-9))
        self.assertTrue(np.allclose(Oh, Om, atol=1e-9))
        with self.assertRaises(ValueError):
            GM.llc(reg[:3], 6)

    def test_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(1)
        truth = S.planted(9, 4, 1, 0.5, 'gauss')
        reg, _, _ = population(truth, [1, 3])
        theta = rng.normal(0, 0.3, 4 * 4 - 4 + 10)
        theta[12:] += np.array([1.5, 0, 1.5, 0, 0, 1.5, 0, 0, 0, 1.5])     # a positive-definite L
        F, g = GM.objective(theta, reg, 4)
        num = np.zeros_like(theta)
        for k in range(len(theta)):
            e = np.zeros_like(theta)
            e[k] = 1e-6
            num[k] = (GM.objective(theta + e, reg, 4)[0] - GM.objective(theta - e, reg, 4)[0]) / 2e-6
        self.assertTrue(np.allclose(g, num, atol=1e-5, rtol=1e-4), np.max(np.abs(g - num)))

    def test_fit_recovers_with_every_experiment(self):
        truth = S.planted(5, 6, 2, 0.4, 'gauss')
        reg, B, Om = population(truth, range(6))
        Bh, Oh, ok = GM.fit(reg, 6, lam_b=1e-4, lam_o=1e-4, maxiter=3000)
        self.assertTrue(np.allclose(Bh, B, atol=0.02), np.max(np.abs(Bh - B)))
        self.assertTrue(np.allclose(Oh, Om, atol=0.05), np.max(np.abs(Oh - Om)))
        ans = GM.answer(Bh, Oh, 0.25, 0.15)
        sc = A.score(truth, ans)
        self.assertEqual(sc['directed']['f1'], 1.0)

    def test_answer(self):
        B = np.zeros((3, 3))
        B[0, 1] = 0.8
        Om = np.eye(3)
        Om[1, 2] = Om[2, 1] = 0.5
        Om[0, 1] = Om[1, 0] = 0.6                      # a bow: the edge wins the pair's one mark
        self.assertEqual(GM.answer(B, Om, 0.25, 0.15),
                         {'directed': [[0, 1]], 'undirected': [], 'bidirected': [[1, 2]]})

    def test_covariances(self):
        X0 = np.random.default_rng(0).normal(size=(50, 3))
        reg = GM.covariances(X0, {2: X0[:20], 0: X0[:30]})
        self.assertEqual([(n, t) for _, n, t in reg], [(50, None), (30, 0), (20, 2)])


if __name__ == '__main__':
    unittest.main()
