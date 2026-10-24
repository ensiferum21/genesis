"""B20_R120: can Genesis propose the experiments that resolve hidden causes? (design): fresh seed, the arms and
budgets, the primary test and verdict, the secondary tests, the validity checks, and the registered output; the
record."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r120_propose_interventions as M  # noqa: E402


def row(seed, arm, bf1, targets=None):
    m = 0 if arm == 'fci' else int(arm.split('@')[1])
    return {'seed': seed, 'arm': arm, 'valid_problems': [], 'targets': list(range(m)) if targets is None else targets,
            'scores': {'bidirected': {'f1': bf1, 'precision': bf1, 'recall': bf1}, 'directed': {'f1': 0.5}, 'shd': 3,
                       'spurious_rate': 0.5}}


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r120_propose_interventions.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_arms(self):
        self.assertEqual(M.ARMS[0], 'fci')
        self.assertEqual(len(M.ARMS), 9)
        self.assertIn('suspicion@2', M.ARMS)
        self.assertIn('oracle@4', M.ARMS)

    def test_primary_test_and_verdict(self):
        def rows_with(susp2, rand2):
            out = []
            for i in range(12):
                for arm in M.ARMS:
                    v = {'suspicion@2': susp2(i), 'random@2': rand2(i)}.get(arm, 0.3)
                    out.append(row(i, arm, v))
            return out
        a = M.analyse(rows_with(lambda i: 0.6 + 0.01 * i, lambda i: 0.2))
        self.assertEqual((a['test1']['label'], a['verdict']), ('SUSPICION_BETTER', 'GENESIS_PROPOSES_BETTER'))
        a = M.analyse(rows_with(lambda i: 0.2, lambda i: 0.6 + 0.01 * i))
        self.assertEqual(a['verdict'], 'GENESIS_PROPOSES_WORSE')
        a = M.analyse(rows_with(lambda i: 0.3, lambda i: 0.3))
        self.assertEqual((a['test1']['label'], a['verdict']), ('NO_DIFFERENCE', 'NOT_SHOWN'))
        self.assertEqual(set(a['secondary']), {'suspicion_vs_random@4', 'suspicion_vs_degree@2',
                                               'suspicion_vs_degree@4', 'suspicion@4_vs_fci'})

    def test_checks(self):
        self.assertTrue(M.checks([row(1, 'fci', 0.1), row(1, 'random@2', 0.1)]))
        self.assertFalse(M.checks([row(1, 'random@2', 0.1, targets=[3])]))
        self.assertFalse(M.checks([row(1, 'random@2', 0.1, targets=[3, 3])]))
        bad = row(1, 'fci', 0.1)
        bad['valid_problems'] = ['x']
        self.assertFalse(M.checks([bad]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R120(unittest.TestCase):
    """B20_R120's record: every answer re-scores against the regenerated truth; the tests and the verdict recompute
    from the rows; budgets were used exactly."""

    def test_recomputes(self):
        from genesis.causal import admg as A
        from genesis.causal import sem as S
        ev = ROOT / 'evidence' / 'propose_interventions_b20r120'
        s = json.loads((ev / 'summary.json').read_text())
        rows = [json.loads(l) for l in (ev / 'runs.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), M.N_SEEDS * len(M.ARMS))
        truths = {}
        for r in rows:
            if r['seed'] not in truths:
                truths[r['seed']] = S.planted(r['seed'], M.P, M.H, M.DENSITY, M.NOISE, M.K)
            sc = A.score(truths[r['seed']], r['answer'])
            self.assertEqual(json.loads(json.dumps(sc)), r['scores'], (r['seed'], r['arm']))
        self.assertTrue(M.checks(rows) and s['valid'])
        a = json.loads(json.dumps(M.analyse(rows)))
        for k in ('means', 'test1', 'secondary', 'verdict'):
            self.assertEqual(a[k], s[k], k)
        self.assertEqual((a['test1']['label'], a['verdict']), ('NO_DIFFERENCE', 'NOT_SHOWN'))


if __name__ == '__main__':
    unittest.main()
