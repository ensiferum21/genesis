"""B20_R130: per-pair instruments as programs (`causal.instruments`): the language (checks, its 45 members), the tests
on clear cases (a direct cause, a reverse one, a hidden cause), outcomes, the lab, calibration and the domain."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.causal import active3 as A3  # noqa: E402
from genesis.causal import instruments as INS  # noqa: E402
from genesis.causal import sem as S  # noqa: E402
from genesis.science import design as D  # noqa: E402


def hand(p, edges, hidden_pairs):
    B = [[0.0] * p for _ in range(p)]
    for i, j, w in edges:
        B[i][j] = w
    G = [[0.0] * p for _ in hidden_pairs]
    for k, (i, j) in enumerate(hidden_pairs):
        G[k][i], G[k][j] = 1.0, 1.0
    return {'p': p, 'h': len(hidden_pairs), 'B': B, 'G': G, 'confounded': [sorted(c) for c in hidden_pairs],
            'noise': 'gauss', 'scales': [[1.0] * p]}


class Language(unittest.TestCase):
    def test_space_and_checks(self):
        sp = INS.space()
        self.assertEqual(len(sp), 45)
        self.assertTrue(all(INS.check(x) is None for x in sp))
        self.assertIn(INS.R129, sp)
        for bad in ({'tests': [], 'alpha': 0.01}, {'tests': ['direct', 'dep'], 'alpha': 0.01},
                    {'tests': ['dep'], 'alpha': 0.02}, {'tests': ['dep', 'dep'], 'alpha': 0.01}, {'tests': ['dep']}):
            self.assertIsNotNone(INS.check(bad), bad)
        self.assertEqual(INS.alphabet({'tests': ['dep', 'gap'], 'alpha': 0.01}), ('00', '01', '10', '11'))
        self.assertEqual(INS.outcome({'tests': ['dep', 'gap'], 'alpha': 0.01}, {'dep': 0.001, 'gap': 0.5}), '10')

    def test_tests_on_clear_cases(self):
        rng = np.random.default_rng(2)
        # 0 -> 1 directly; 1 and 2 share a hidden cause, no edge
        t = hand(3, [(0, 1, 1.0)], [(1, 2)])
        X0 = S.sample(t, 3000, rng)
        adj = {0: [1], 1: [0, 2], 2: [1]}
        pv0 = INS.pvalues(X0, S.sample(t, 3000, rng, intervene=0), 0, adj)
        self.assertLess(pv0[1]['dep'], 1e-6)                     # 0 causes 1
        self.assertLess(pv0[1]['direct'], 1e-6)
        self.assertGreater(pv0[1]['gap'], 1e-3)                  # no back-door between 0 and 1: slopes agree
        pv1 = INS.pvalues(X0, S.sample(t, 3000, rng, intervene=1), 1, adj)
        self.assertGreater(pv1[0]['dep'], 1e-3)                  # 1 does not cause 0
        self.assertLess(pv1[0]['gap'], 1e-6)                     # but they are associated observationally
        self.assertGreater(pv1[2]['dep'], 1e-3)                  # 1 does not cause 2 ...
        self.assertLess(pv1[2]['gap'], 1e-6)                     # ... yet they are associated: the hidden cause

    def test_lab_calibrate_domain(self):
        view, truth = S.instance(3, 6, 1, 0.4, 'gauss', 3, 1500)
        prep = A3.prepare(view, truth, 500, 3)
        X0 = view['environments'][0]
        adj = {int(i): v for i, v in prep['adj'].items()}
        table = {str(t): {str(j): d for j, d in INS.pvalues(
            X0, S.sample(truth, 500, np.random.default_rng([3, 11, t]), env=0, intervene=t), t, adj).items()}
            for t in range(6)}
        prog = {'tests': ['dep', 'direct', 'gap'], 'alpha': 0.01}
        lab = INS.lab(prog, table, 6)
        self.assertEqual(set(lab), {str(t) for t in range(6)})
        self.assertTrue(all(len(o) == 3 for d in lab.values() for o in d.values()))
        m = INS.calibrate([(prep, truth, lab)], prog)
        self.assertEqual(len(m['alphabet']), 8)
        for d in m['predict'].values():
            self.assertAlmostEqual(sum(d.values()), 1.0)
        dom = INS.Domain(prep, m, lab)
        r, trail = D.run(dom, {'kind': 'eig'}, 6)
        self.assertEqual(sorted(r.done), list(range(6)))


if __name__ == '__main__':
    unittest.main()
