"""B20_R117: the hidden-confounder benchmark: the generator, the truth and its scoring, d-separation, and the
baselines on cases with known answers."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import admg as A  # noqa: E402
from genesis.causal import methods as M  # noqa: E402
from genesis.causal import sem as S  # noqa: E402


def chain_truth(h_pairs=()):
    """0 -> 1 -> 2, 3 isolated; hidden variables over the given pairs."""
    p = 4
    B = [[0.0] * p for _ in range(p)]
    B[0][1], B[1][2] = 1.0, -0.8
    G = [[0.0] * p for _ in h_pairs]
    for k, (i, j) in enumerate(h_pairs):
        G[k][i], G[k][j] = 1.0, 1.0
    return {'p': p, 'h': len(h_pairs), 'B': B, 'G': G, 'confounded': [list(c) for c in h_pairs], 'noise': 'laplace',
            'scales': [[1.0] * p]}


class Generator(unittest.TestCase):
    def test_reproducible_and_shaped(self):
        v1, t1 = S.instance(7, 6, 2, 0.4, 'laplace', 3, 900)
        v2, t2 = S.instance(7, 6, 2, 0.4, 'laplace', 3, 900)
        self.assertEqual(t1, t2)
        self.assertEqual(len(v1['environments']), 3)
        for a, b in zip(v1['environments'], v2['environments']):
            self.assertEqual(a.shape, (300, 6))
            self.assertTrue(np.array_equal(a, b))
        self.assertNotIn('B', v1)

    def test_truth(self):
        t = S.planted(11, 8, 3, 0.3)
        B = np.array(t['B'])
        pos = {v: k for k, v in enumerate(t['order'])}
        self.assertTrue(all(pos[i] < pos[j] for i, j in zip(*np.nonzero(B))))       # acyclic by the order
        self.assertTrue(all(S.W_LOW <= abs(w) <= S.W_HIGH for w in B[B != 0]))
        G = np.array(t['G'])
        self.assertTrue(all(np.count_nonzero(G[k]) == 2 for k in range(3)))           # two children each
        self.assertEqual(len({tuple(c) for c in t['confounded']}), 3)
        self.assertEqual(t['scales'], [[1.0] * 8])

    def test_environments_scale_a_third(self):
        t = S.planted(5, 9, 0, 0.3, k_env=3)
        self.assertEqual(t['scales'][0], [1.0] * 9)
        for s in t['scales'][1:]:
            changed = [x for x in s if x != 1.0]
            self.assertEqual(len(changed), 3)
            self.assertTrue(all(1.5 <= x <= 3.0 for x in changed))

    def test_the_model_holds(self):
        """Large samples: the covariance matches (I - B)^-T (G'G + D) (I - B)^-1."""
        t = S.planted(3, 5, 1, 0.5, 'uniform')
        X = S.sample(t, 200000, np.random.default_rng(0))
        B, G = np.array(t['B']), np.array(t['G'])
        Minv = np.linalg.inv(np.eye(5) - B)
        expected = Minv.T @ (G.T @ G + np.eye(5)) @ Minv
        self.assertLess(np.max(np.abs(np.cov(X, rowvar=False) - expected)), 0.08 * np.max(np.abs(expected)))

    def test_intervention_cuts_incoming_edges(self):
        t = chain_truth([(1, 3)])
        X = S.sample(t, 100000, np.random.default_rng(1), intervene=1)
        c = np.corrcoef(X, rowvar=False)
        self.assertLess(abs(c[0, 1]), 0.02)        # 0 -> 1 cut
        self.assertLess(abs(c[1, 3]), 0.02)        # hidden 1 <-> 3 cut at 1
        self.assertGreater(abs(c[1, 2]), 0.4)      # 1 -> 2 kept

    def test_refuses_bad_parameters(self):
        for args in ((1, 0, 0.1), (5, 0, 1.5), (5, 11, 0.1)):
            with self.assertRaises(ValueError):
                S.planted(0, *args)
        with self.assertRaises(ValueError):
            S.planted(0, 5, 0, 0.2, noise='cauchy')


class Scoring(unittest.TestCase):
    def test_validate(self):
        self.assertEqual(A.validate({'directed': [[0, 1]]}, 3), [])
        self.assertTrue(A.validate({'directed': [[0, 0]]}, 3))
        self.assertTrue(A.validate({'directed': [[0, 3]]}, 3))
        self.assertTrue(A.validate({'directed': [[0, 1]], 'bidirected': [[1, 0]]}, 3))
        self.assertTrue(A.validate({'directed': [[0, 1], [1, 2], [2, 0]]}, 3))
        self.assertTrue(A.validate({'order': []}, 3))
        self.assertTrue(A.validate({'directed': [[0, 1.0]]}, 3))

    def test_perfect_and_empty(self):
        t = chain_truth([(0, 3)])
        s = A.score(t, {'directed': [[0, 1], [1, 2]], 'bidirected': [[0, 3]]})
        self.assertEqual((s['directed']['f1'], s['bidirected']['f1'], s['shd'], s['spurious_rate']), (1.0, 1.0, 0, 0.0))
        e = A.score(t, M.empty({'p': 4}))
        self.assertEqual((e['directed']['recall'], e['shd'], e['latent_flagged'], e['latent_present']),
                         (0.0, 3, False, True))

    def test_spurious_and_undirected(self):
        t = chain_truth([(0, 3)])
        s = A.score(t, {'directed': [[0, 1]], 'undirected': [[1, 2], [0, 3]]})
        self.assertEqual(s['spurious_rate'], 1.0)          # 0 - 3 has no direct edge
        self.assertEqual(s['adjacency']['precision'], 2 / 3)
        self.assertEqual(s['shd'], 2)                      # 1 - 2 undirected, 0 - 3 not <->

    def test_d_separation(self):
        t = chain_truth([(1, 3)])
        par = A.full_dag(t)
        self.assertTrue(A.d_separated(par, 0, 2, {1}))
        self.assertFalse(A.d_separated(par, 0, 2, set()))
        self.assertFalse(A.d_separated(par, 1, 3, set()))        # hidden common cause
        self.assertFalse(A.d_separated(par, 0, 3, {1}))          # collider at 1: 0 -> 1 <- L -> 3
        self.assertTrue(A.d_separated(par, 0, 3, set()))


class Baselines(unittest.TestCase):
    def test_oracle_pc_without_hidden_variables_is_exact_up_to_equivalence(self):
        for seed in range(5):
            t = S.planted(seed, 7, 0, 0.35)
            a = M.pc_oracle({'p': 7}, truth=t)
            s = A.score(t, a)
            self.assertEqual(s['adjacency']['f1'], 1.0, seed)
            self.assertEqual(s['directed']['precision'], 1.0, seed)     # every oriented edge is right

    def test_oracle_pc_is_fooled_by_a_hidden_cause(self):
        t = chain_truth([(0, 3)])
        s = A.score(t, M.pc_oracle({'p': 4}, truth=t))
        self.assertEqual(s['spurious_rate'], 1.0)

    def test_pc_on_data_without_hidden_variables(self):
        f1 = []
        for seed in range(4):
            v, t = S.instance(100 + seed, 6, 0, 0.4, 'gauss', 1, 5000)
            f1.append(A.score(t, M.pc(v))['adjacency']['f1'])
        self.assertGreater(np.mean(f1), 0.85)

    def test_lingam_orients_non_gaussian_data(self):
        good = 0
        for seed in range(4):
            v, t = S.instance(200 + seed, 5, 0, 0.5, 'laplace', 1, 5000)
            good += A.score(t, M.lingam(v))['directed']['f1'] > 0.8
        self.assertGreaterEqual(good, 3)

    def test_lingam_finds_the_order_of_a_chain(self):
        t = chain_truth()
        X = S.sample(t, 20000, np.random.default_rng(3))
        order = M.causal_order(X)
        self.assertLess(order.index(0), order.index(1))
        self.assertLess(order.index(1), order.index(2))

    def test_answers_are_valid(self):
        v, t = S.instance(9, 6, 2, 0.4, 'laplace', 3, 1500)
        for name, f in M.METHODS.items():
            self.assertEqual(A.validate(f(v, truth=t), 6), [], name)


if __name__ == '__main__':
    unittest.main()
