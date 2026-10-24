"""B20_R121: the active procedure, version 2: version 1 reproduced exactly when asked for; the LiNGAM-residual
signal; direct causation under intervention (direct, indirect, none); the decision rule; flags that experiments can
refute but not erase."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import active as V1  # noqa: E402
from genesis.causal import active2 as V2  # noqa: E402
from genesis.causal import admg as A  # noqa: E402
from genesis.causal import sem as S  # noqa: E402


def hand(p, edges, hidden_pairs, noise='laplace'):
    B = [[0.0] * p for _ in range(p)]
    for i, j, w in edges:
        B[i][j] = w
    G = [[0.0] * p for _ in hidden_pairs]
    for k, (i, j) in enumerate(hidden_pairs):
        G[k][i], G[k][j] = 1.0, 1.0
    return {'p': p, 'h': len(hidden_pairs), 'B': B, 'G': G, 'confounded': [list(c) for c in hidden_pairs],
            'noise': noise, 'scales': [[1.0] * p]}


class Version1Kept(unittest.TestCase):
    def test_v1_reproduced(self):
        for seed in (3, 4):
            v, t = S.instance(seed, 8, 3, 0.3, 'laplace', 3, 3000)
            for strat in ('random', 'suspicion'):
                self.assertEqual(V2.resolve(v, t, strat, 2, 500, seed, rule='v1', signal='v1')[0],
                                 V1.resolve(v, t, strat, 2, 500, seed)[0])


class Signal(unittest.TestCase):
    def test_residual_dependence_finds_a_hidden_cause(self):
        rng = np.random.default_rng(0)
        t_dir = hand(2, [(0, 1, 1.0)], [])
        t_conf = hand(2, [(0, 1, 1.0)], [(0, 1)])
        X = S.sample(t_dir, 3000, rng)
        self.assertGreater(V2.residual_p([X], 1, [0], 0), 0.01)          # right model: independent residual
        X = S.sample(t_conf, 3000, rng)
        self.assertLess(V2.residual_p([X], 1, [0], 0), 0.01)             # hidden cause: dependent residual

    def test_suspicion_is_scaled_and_keyed_by_adjacent_pairs(self):
        v, t = S.instance(5, 8, 3, 0.3, 'laplace', 3, 3000)
        adj = {i: {j for j in range(8) if j != i and abs(i - j) == 1} for i in range(8)}
        s = V2.suspicion(v, adj)
        self.assertEqual(set(s), {(i, i + 1) for i in range(7)})
        self.assertTrue(all(0.0 <= x <= 1.0 for x in s.values()))


class DirectCausation(unittest.TestCase):
    def setUp(self):
        # 0 -> 2 -> 1 and a hidden cause of 0 and 1; 3 -> 1 directly
        self.t = hand(4, [(0, 2, 1.0), (2, 1, 1.0), (3, 1, 1.0)], [(0, 1)])
        self.adj = {0: {1, 2}, 1: {0, 2, 3}, 2: {0, 1}, 3: {1}}

    def test_indirect_ancestor_is_not_a_direct_cause(self):
        X0 = S.sample(self.t, 4000, np.random.default_rng(1), intervene=0)
        self.assertEqual(V2.classify(X0, 0, 1, self.adj), 'indirect')
        self.assertEqual(V2.classify(X0, 0, 2, self.adj), 'direct')
        self.assertEqual(V1.dependent(X0[:, 0], X0[:, 1]), True)        # what version 1 read as 0 -> 1

    def test_direct_and_none(self):
        X3 = S.sample(self.t, 4000, np.random.default_rng(2), intervene=3)
        self.assertEqual(V2.classify(X3, 3, 1, self.adj), 'direct')
        X1 = S.sample(self.t, 4000, np.random.default_rng(3), intervene=1)
        self.assertEqual(V2.classify(X1, 1, 0, self.adj), 'none')

    def test_decide(self):
        base = {'directed': [[0, 1]], 'undirected': [[2, 3]], 'bidirected': []}
        m = V2.decide(base, {(0, 1): 'indirect'})
        self.assertEqual(m[(0, 1)], ('b', None))
        m = V2.decide(base, {(0, 1): 'none'})
        self.assertEqual(m[(0, 1)], ('u', None))
        m = V2.decide(base, {(0, 1): 'none', (1, 0): 'none'})
        self.assertEqual(m[(0, 1)], ('b', None))
        m = V2.decide(base, {(3, 2): 'direct'})
        self.assertEqual(m[(2, 3)], ('d', (3, 2)))


class Flags(unittest.TestCase):
    def test_experiments_refute_but_never_erase_a_flag(self):
        v, t = S.instance(6, 8, 3, 0.3, 'laplace', 3, 3000)
        ans0, rec0 = V2.resolve(v, t, 'suspicion', 0, 500, 6, flag=True)
        flagged = {tuple(map(int, k.split('-'))) for k, s in rec0['suspicion'].items() if s >= V2.FLAG_SCORE}
        self.assertEqual({tuple(e) for e in ans0['bidirected']} >= flagged, True)
        ans, rec = V2.resolve(v, t, 'suspicion', 4, 500, 6, flag=True)
        direct = {tuple(sorted(map(int, k.split('-')))) for k, o in rec['tests'].items() if o == 'direct'}
        self.assertTrue(flagged - direct <= {tuple(e) for e in ans['bidirected']})
        self.assertEqual(A.validate(ans, 8), [])

    def test_refusals(self):
        v, t = S.instance(7, 6, 1, 0.3, 'laplace', 1, 1000)
        with self.assertRaises(ValueError):
            V2.resolve(v, t, 'suspicion', 1, 100, 7, rule='v3')
        with self.assertRaises(ValueError):
            V2.resolve(v, t, 'suspicion', 1, 100, 7, signal='v1', flag=True)
        with self.assertRaises(ValueError):
            V2.resolve(v, t, 'clairvoyant', 1, 100, 7)


if __name__ == '__main__':
    unittest.main()
