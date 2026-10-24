"""B20_R129: causal discovery as a domain of the experimental scientist (`causal.active3`): hypotheses seen from the
intervened variable, the truth's hypothesis per pair, the lab drawn once, the theory and calibrated models, the
answer, and the comparators' orders."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import active3 as A3  # noqa: E402
from genesis.causal import admg as A  # noqa: E402
from genesis.causal import sem as S  # noqa: E402
from genesis.science import design as D  # noqa: E402


def hand(p, edges, hidden_pairs, noise='gauss'):
    B = [[0.0] * p for _ in range(p)]
    for i, j, w in edges:
        B[i][j] = w
    G = [[0.0] * p for _ in hidden_pairs]
    for k, (i, j) in enumerate(hidden_pairs):
        G[k][i], G[k][j] = 1.0, 1.0
    return {'p': p, 'h': len(hidden_pairs), 'B': B, 'G': G, 'confounded': [sorted(c) for c in hidden_pairs],
            'noise': noise, 'scales': [[1.0] * p]}


class Hypotheses(unittest.TestCase):
    def test_relation_seen_from_t(self):
        self.assertEqual(A3.relation('ij', 2, '2-5'), 'cause')
        self.assertEqual(A3.relation('ij', 5, '2-5'), 'effect')
        self.assertEqual(A3.relation('ji', 2, '2-5'), 'effect')
        self.assertEqual(A3.relation('ji', 5, '2-5'), 'cause')
        self.assertEqual(A3.relation('conf', 5, '2-5'), 'conf')
        self.assertEqual(A3.relation('none', 2, '2-5'), 'none')

    def test_true_hypothesis(self):
        t = hand(4, [(0, 1, 1.0), (3, 2, 1.0)], [(1, 2), (0, 1)])
        self.assertEqual(A3.true_hypothesis(t, '0-1'), 'ij')       # a bow is marked by its edge
        self.assertEqual(A3.true_hypothesis(t, '2-3'), 'ji')
        self.assertEqual(A3.true_hypothesis(t, '1-2'), 'conf')
        self.assertEqual(A3.true_hypothesis(t, '0-3'), 'none')
        self.assertEqual((A3.key(3, 1), A3.ends('1-3')), ('1-3', (1, 3)))


class Lab(unittest.TestCase):
    def test_prepare_is_deterministic_and_serialisable(self):
        v, t = S.instance(7, 8, 2, 0.3, 'gauss', 3, 1500)
        a, b = A3.prepare(v, t, 500, 7), A3.prepare(v, t, 500, 7)
        self.assertEqual(json.loads(json.dumps(a)), json.loads(json.dumps(b)))
        self.assertEqual(set(a['lab']), {str(i) for i in range(8)})
        for tt, outs in a['lab'].items():
            self.assertEqual(sorted(int(j) for j in outs), a['adj'][tt])
            self.assertTrue(set(outs.values()) <= set(A3.OUTCOMES))
        self.assertTrue(set(a['marks'].values()) <= set(A3.MARKS))

    def test_the_instrument_on_a_clear_case(self):
        # 0 -> 1 strongly; 1 and 2 share a hidden cause, no edge; strong enough to be found at these sizes
        t = hand(3, [(0, 1, 1.5)], [(1, 2)])
        rng = np.random.default_rng(3)
        view = {'p': 3, 'environments': [S.sample(t, 3000, rng)]}
        prep = A3.prepare(view, t, 2000, 3)
        self.assertIn('0-1', prep['marks'])
        self.assertEqual(prep['lab']['0']['1'], 'direct')
        self.assertEqual(prep['lab']['1']['0'], 'none')
        if '1-2' in prep['marks']:
            self.assertEqual((prep['lab']['1']['2'], prep['lab']['2']['1']), ('none', 'none'))


class Models(unittest.TestCase):
    def test_theory_prior_and_flag(self):
        p = A3.model_prior(A3.THEORY, 'fwd', False)
        self.assertAlmostEqual(sum(p), 1.0)
        self.assertEqual(A3.HYPS[int(np.argmax(p))], 'ij')
        q = A3.model_prior(A3.THEORY, 'fwd', True)
        self.assertGreater(q[A3.HYPS.index('conf')], p[A3.HYPS.index('conf')])
        for r, d in A3.THEORY['predict'].items():
            self.assertAlmostEqual(sum(d.values()), 1.0)

    def test_calibrate_counts_with_laplace(self):
        t = hand(3, [(0, 1, 1.0)], [(1, 2)])
        prep = {'p': 3, 'marks': {'0-1': 'fwd', '1-2': 'b'}, 'flagged': [], 'adj': {'0': [1], '1': [0, 2], '2': [1]},
                'lab': {'0': {'1': 'direct'}, '1': {'0': 'none', '2': 'none'}, '2': {'1': 'indirect'}}}
        m = A3.calibrate([(prep, t)])
        self.assertAlmostEqual(m['prior']['fwd|0']['ij'], 2 / 5)
        self.assertAlmostEqual(m['prior']['b|0']['conf'], 2 / 5)
        self.assertAlmostEqual(m['prior']['u|1']['ij'], 1 / 4)
        self.assertAlmostEqual(m['predict']['cause']['direct'], 2 / 4)
        self.assertAlmostEqual(m['predict']['effect']['none'], 2 / 4)
        self.assertAlmostEqual(m['predict']['conf']['none'], 2 / 5)
        self.assertAlmostEqual(m['predict']['conf']['indirect'], 2 / 5)
        self.assertAlmostEqual(A3.model_prior(m, 'b', False)[A3.HYPS.index('conf')], 2 / 5)

    def test_domain_contract(self):
        v, t = S.instance(11, 8, 2, 0.3, 'gauss', 3, 1500)
        prep = A3.prepare(v, t, 500, 11)
        d = A3.CausalDomain(prep, A3.THEORY)
        for tt in d.experiments():
            obs = d.execute(tt)
            self.assertEqual(set(obs), set(d.touches(tt)))
            for q in d.touches(tt):
                L = np.array(d.predict(q, tt))
                self.assertEqual(L.shape, (4, 3))
                self.assertTrue(np.allclose(L.sum(axis=1), 1.0))
        r, trail = D.run(d, {'kind': 'eig'}, 8)
        self.assertEqual(sorted(r.done), list(range(8)))
        for dec in trail:
            self.assertEqual(A.validate(A3.answer(8, dec), 8), [])


class Answer(unittest.TestCase):
    def test_answer_marks_and_acyclic(self):
        ans = A3.answer(3, {'0-1': 'ij', '1-2': 'ji', '0-2': 'conf'})
        self.assertEqual(ans, {'directed': [[0, 1], [2, 1]], 'undirected': [], 'bidirected': [[0, 2]]})
        ans = A3.answer(3, {'0-1': 'ij', '1-2': 'ij', '0-2': 'ji'})          # a cycle: one edge becomes undirected
        self.assertEqual(A.validate(ans, 3), [])
        self.assertEqual(len(ans['directed']) + len(ans['undirected']), 3)
        self.assertEqual(A3.answer(3, {'0-1': 'none'}), {'directed': [], 'undirected': [], 'bidirected': []})

    def test_orders(self):
        prep = {'p': 4, 'adj': {'0': [1], '1': [0, 2, 3], '2': [1], '3': [1]}}
        self.assertEqual(A3.degree_order(prep), [1, 0, 2, 3])
        self.assertEqual(A3.oracle_order(prep, {'confounded': [[2, 3]]}), [2, 3, 1, 0])


if __name__ == '__main__':
    unittest.main()
