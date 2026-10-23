"""B20_R119: FCI (the established method with hidden variables) and Genesis's active procedure that proposes the
interventions resolving hidden causes. FCI's oracle output must be sound (every <-> a pair with no ancestral
relation, every -> an ancestral one) and recover a textbook hidden cause; the procedure's interventions must turn a
pure hidden cause into <-> and a direct cause into ->."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import active as AC  # noqa: E402
from genesis.causal import admg as A  # noqa: E402
from genesis.causal import fci as F  # noqa: E402
from genesis.causal import sem as S  # noqa: E402


def hand(p, edges, hidden_pairs):
    B = [[0.0] * p for _ in range(p)]
    for i, j, w in edges:
        B[i][j] = w
    G = [[0.0] * p for _ in hidden_pairs]
    for k, (i, j) in enumerate(hidden_pairs):
        G[k][i], G[k][j] = 1.0, -1.0
    return {'p': p, 'h': len(hidden_pairs), 'B': B, 'G': G, 'confounded': [list(c) for c in hidden_pairs],
            'noise': 'laplace', 'scales': [[1.0] * p]}


def ancestors(parents, v):
    out, stack = set(), list(parents[v])
    while stack:
        u = stack.pop()
        if u not in out:
            out.add(u)
            stack.extend(parents[u])
    return out


class FCI(unittest.TestCase):
    def test_textbook_hidden_cause(self):
        """A -> B <- L -> C <- D with L hidden: FCI marks B <-> C, which no method without hidden variables can."""
        t = hand(4, [(0, 1, 1.0), (3, 2, 1.0)], [(1, 2)])
        a = F.fci_oracle({'p': 4}, truth=t)
        self.assertEqual(a['bidirected'], [[1, 2]])
        self.assertEqual(sorted(a['undirected']), [[0, 1], [2, 3]])        # A o-> B and D o-> C

    def test_no_hidden_variable_no_bidirected_edge(self):
        for seed in range(6):
            t = S.planted(seed, 8, 0, 0.3)
            a = F.fci_oracle({'p': 8}, truth=t)
            self.assertEqual(a['bidirected'], [], seed)
            self.assertEqual(A.score(t, a)['adjacency']['f1'], 1.0, seed)

    def test_oracle_output_is_sound(self):
        for seed in range(12):
            t = S.planted(100 + seed, 8, 3, 0.3)
            par = A.full_dag(t)
            a = F.fci_oracle({'p': 8}, truth=t)
            for i, j in a['bidirected']:
                self.assertNotIn(i, ancestors(par, j), (seed, i, j))
                self.assertNotIn(j, ancestors(par, i), (seed, i, j))
            for i, j in a['directed']:
                self.assertIn(i, ancestors(par, j), (seed, i, j))
                self.assertNotIn(j, ancestors(par, i), (seed, i, j))

    def test_every_adjacency_is_inseparable(self):
        """With the oracle, an FCI adjacency is a pair that no set of observed variables separates (checked up to
        size 3), which needs the Possible-D-SEP stage when separating sets lie outside both adjacency sets."""
        t = S.planted(7, 9, 4, 0.35)
        par = A.full_dag(t)
        a = F.fci_oracle({'p': 9}, truth=t)
        adj = {tuple(sorted(e)) for k in ('directed', 'undirected', 'bidirected') for e in a[k]}
        for i, j in adj:          # every FCI adjacency is a pair no observed set separates
            others = [v for v in range(9) if v not in (i, j)]
            self.assertFalse(any(A.d_separated(par, i, j, set(S_)) for r in range(0, 4)
                                 for S_ in __import__('itertools').combinations(others, r)), (i, j))

    def test_data_answers_are_valid(self):
        v, t = S.instance(3, 8, 2, 0.3, 'laplace', 3, 3000)
        self.assertEqual(A.validate(F.fci(v), 8), [])


class Active(unittest.TestCase):
    def test_slope_heterogeneity(self):
        rng = np.random.default_rng(0)
        x = rng.standard_normal(4000)
        envs_same = [np.column_stack([x[:2000], 2 * x[:2000] + rng.standard_normal(2000)]),
                     np.column_stack([x[2000:], 2 * x[2000:] + rng.standard_normal(2000)])]
        self.assertGreater(AC.slope_heterogeneity(envs_same, 0, 1), 0.01)
        L = rng.standard_normal(4000)
        a = np.r_[L[:2000] + rng.standard_normal(2000), L[2000:] + 3 * rng.standard_normal(2000)]
        b = L + rng.standard_normal(4000)
        envs_conf = [np.column_stack([a[:2000], b[:2000]]), np.column_stack([a[2000:], b[2000:]])]
        self.assertLess(AC.slope_heterogeneity(envs_conf, 0, 1), 0.01)     # var(a) changed: slope of b on a moves
        self.assertEqual(AC.slope_heterogeneity(envs_same[:1], 0, 1), 1.0)

    def test_interventions_resolve_a_pure_hidden_cause_and_a_direct_one(self):
        t = hand(4, [(0, 1, 1.0), (3, 2, 1.0)], [(1, 2)])
        view = {'p': 4, 'environments': [S.sample(t, 4000, np.random.default_rng(5))]}
        ans, rec = AC.resolve(view, t, 'degree', 4, 2000, seed=1)
        self.assertEqual(sorted(rec['targets']), [0, 1, 2, 3])
        self.assertIn([1, 2], ans['bidirected'])
        self.assertIn([0, 1], ans['directed'])
        self.assertIn([3, 2], ans['directed'])

    def test_strategies_respect_the_budget_and_never_repeat(self):
        v, t = S.instance(11, 8, 3, 0.3, 'laplace', 3, 3000)
        for strat in AC.STRATEGIES:
            for m in (0, 2, 4):
                ans, rec = AC.resolve(v, t, strat, m, 500, seed=2)
                self.assertEqual(len(rec['targets']), m)
                self.assertEqual(len(set(rec['targets'])), m)
                self.assertEqual(A.validate(ans, 8), [])

    def test_budget_zero_is_fci(self):
        v, t = S.instance(12, 8, 3, 0.3, 'laplace', 3, 3000)
        ans, rec = AC.resolve(v, t, 'suspicion', 0, 500, seed=3)
        self.assertEqual(ans, F.fci(v))

    def test_suspicion_prefers_the_suspected_pair(self):
        adj = {0: {1}, 1: {0, 2}, 2: {1}, 3: set()}
        susp = {(0, 1): 0.0, (1, 2): 1.0}
        self.assertEqual(AC.choose('suspicion', 4, adj, susp, [], None), 1)
        self.assertEqual(AC.choose('suspicion', 4, adj, susp, [1], None), 2)
        self.assertEqual(AC.choose('degree', 4, adj, susp, [], None), 1)

    def test_unknown_strategy(self):
        with self.assertRaises(ValueError):
            AC.resolve({'p': 2, 'environments': []}, None, 'clairvoyant', 1, 10, 0)

    def test_oracle_reference_goes_to_the_hidden_causes_first(self):
        t = hand(4, [(0, 1, 1.0), (3, 2, 1.0)], [(1, 2)])
        adj = {0: {1}, 1: {0, 2}, 2: {1, 3}, 3: {2}}
        self.assertEqual(AC.choose('oracle', 4, adj, {}, [], None, t), 1)
        self.assertEqual(AC.choose('oracle', 4, adj, {}, [1], None, t), 2)
        self.assertEqual(AC.choose('oracle', 4, adj, {}, [1, 2], None, t), 0)


if __name__ == '__main__':
    unittest.main()
