"""B20_R118: the causal calibration (design): fresh seed, the 2 x 2 factorial within seeds, the tests' labels, the
headroom rule, the oracle's validity conditions, and the registered output; the record."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r118_causal_calibration as M  # noqa: E402


def row(seed, h, k, m, f1, conn=0, pairs=0, flagged=False, adj=1.0):
    return {'seed': seed, 'h': h, 'k': k, 'method': m,
            'scores': {'directed': {'f1': f1}, 'adjacency': {'f1': adj}, 'shd': 0, 'latent_flagged': flagged,
                       'confounded_connected': conn, 'confounded_nonadjacent': pairs}}


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r118_causal_calibration.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_factorial_within_seeds(self):
        c = M.cells()
        self.assertEqual(len(c), 160)
        self.assertEqual(len({s for s, _, _ in c}), 40)
        self.assertEqual({(h, k) for _, h, k in c}, {(0, 1), (0, 3), (3, 1), (3, 3)})

    def test_same_graph_with_and_without_hidden_variables(self):
        from genesis.causal import sem as S
        a = S.planted(M.SEED, M.P, 0, M.DENSITY, M.NOISE, 1)
        b = S.planted(M.SEED, M.P, 3, M.DENSITY, M.NOISE, 3)
        self.assertEqual((a['B'], a['order']), (b['B'], b['order']))
        c = S.planted(M.SEED, M.P, 0, M.DENSITY, M.NOISE, 3)
        self.assertEqual(b['scales'], c['scales'])
        import numpy as np
        v0, _ = S.instance(M.SEED, M.P, 0, M.DENSITY, M.NOISE, 3, M.N_TOTAL)
        v3, t3 = S.instance(M.SEED, M.P, 3, M.DENSITY, M.NOISE, 3, M.N_TOTAL)
        G = np.array(t3['G'])
        untouched = [j for j in range(M.P) if not G[:, j].any()]
        roots = [j for j in untouched if not np.array(t3['B'])[:, j].any()]
        for X0, X3 in zip(v0['environments'], v3['environments']):    # a root with no hidden parent: same values
            for j in roots:
                self.assertTrue(np.array_equal(X0[:, j], X3[:, j]))

    def test_analysis_labels(self):
        rows = []
        for i in range(10):
            s = 100 + i
            for m in M.METHODS:
                good = {'pc': 0.9, 'lingam': 0.8, 'empty': 0.0, 'pc_oracle': 1.0}[m]
                rows += [row(s, 0, 1, m, good), row(s, 0, 3, m, good),
                         row(s, 3, 1, m, good - 0.1 - 0.01 * i, conn=2 if m != 'empty' else 0, pairs=2),
                         row(s, 3, 3, m, good - 0.1 - 0.01 * i, conn=2 if m != 'empty' else 0, pairs=2)]
        a = M.analyse(rows)
        self.assertEqual({m: a['test1'][m]['label'] for m in M.DATA_METHODS}, {'pc': 'HIDDEN_HURTS', 'lingam': 'HIDDEN_HURTS'})
        self.assertEqual(a['test2']['pc']['h0']['label'], 'NO_EFFECT')
        self.assertEqual(a['better_at_h3'], 'pc')
        self.assertEqual((a['spurious']['pc']['rate'], a['headroom']), (1.0, 'CONFOUNDING_MISLEADS'))
        self.assertEqual(a['spurious']['empty']['rate'], 0.0)
        self.assertEqual(a['hidden_flagged']['pc'], 0.0)

    def test_headroom_rule(self):
        def label(conn):
            rows = []
            for i in range(10):
                for m in M.METHODS:
                    for h in M.HS:
                        for k in M.KS:
                            rows.append(row(i, h, k, m, 0.5, conn=conn if h == 3 else 0, pairs=3 if h == 3 else 0))
            return M.analyse(rows)['headroom']
        self.assertEqual(label(3), 'CONFOUNDING_MISLEADS')
        self.assertEqual(label(0), 'MOSTLY_SAFE')
        self.assertEqual(label(1), 'PARTIAL')

    def test_oracle_checks(self):
        self.assertTrue(M.checks([row(1, 3, 1, 'pc_oracle', 0.5, conn=2, pairs=2), row(1, 0, 1, 'pc_oracle', 1.0)]))
        self.assertFalse(M.checks([row(1, 3, 1, 'pc_oracle', 0.5, conn=1, pairs=2)]))
        self.assertFalse(M.checks([row(1, 0, 1, 'pc_oracle', 0.9, adj=0.9)]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R118(unittest.TestCase):
    """B20_R118's record: every answer re-scores from its saved answer and the regenerated truth; the tests, the
    headroom and the oracle checks recompute from the rows."""

    def test_recomputes(self):
        from genesis.causal import admg as A
        from genesis.causal import sem as S
        ev = ROOT / 'evidence' / 'causal_calibration_b20r118'
        s = json.loads((ev / 'summary.json').read_text())
        rows = [json.loads(l) for l in (ev / 'runs.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), 160 * len(M.METHODS))
        truths = {}
        for r in rows:
            key = (r['seed'], r['h'], r['k'])
            if key not in truths:
                truths[key] = S.planted(r['seed'], M.P, r['h'], M.DENSITY, M.NOISE, r['k'])
            sc = A.score(truths[key], r['answer'])
            for k in ('directed', 'adjacency', 'bidirected', 'shd', 'spurious_rate', 'latent_flagged'):
                self.assertEqual(json.loads(json.dumps(sc[k])), r['scores'][k], (key, r['method'], k))
        a = json.loads(json.dumps(M.analyse(rows)))
        for k in ('means', 'test1', 'test2', 'spurious', 'better_at_h3', 'headroom', 'hidden_flagged'):
            self.assertEqual(a[k], s[k], k)
        self.assertTrue(M.checks(rows) and s['valid'])
        self.assertEqual((a['test1']['lingam']['label'], a['test1']['pc']['label'], a['headroom']),
                         ('HIDDEN_HURTS', 'NO_EFFECT', 'CONFOUNDING_MISLEADS'))
        self.assertEqual((a['spurious']['lingam']['connected'], a['spurious']['pc']['connected'],
                          a['spurious']['lingam']['pairs']), (191, 130, 192))


if __name__ == '__main__':
    unittest.main()
