"""B20_R122: the repaired procedure on fresh instances (design): fresh seed, B20_R120's settings, the arms and their
specification, the three tests and the verdict, the validity checks, and the registered output; the record."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r122_hidden_causes_v2 as M  # noqa: E402


def row(seed, arm, bf1, df1=0.5, targets=None):
    m = M.arm_spec(arm)[1]
    return {'seed': seed, 'arm': arm, 'valid_problems': [], 'targets': list(range(m)) if targets is None else targets,
            'scores': {'bidirected': {'f1': bf1, 'precision': bf1, 'recall': bf1}, 'directed': {'f1': df1}, 'shd': 3,
                       'spurious_rate': 0.5}}


class Design(unittest.TestCase):
    def test_seed_is_fresh_and_settings_are_b20r120s(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r122_hidden_causes_v2.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r120_propose_interventions as R120
        self.assertNotEqual(M.SEED, R120.SEED)
        self.assertGreaterEqual(abs(M.SEED - R120.SEED), R120.N_SEEDS)
        self.assertEqual((M.P, M.H, M.K, M.N_TOTAL, M.N_INT), (R120.P, R120.H, R120.K, R120.N_TOTAL, R120.N_INT))

    def test_arms(self):
        self.assertEqual(len(M.ARMS), 10)
        self.assertEqual(M.arm_spec('fci'), ('suspicion', 0, False))
        self.assertEqual(M.arm_spec('flag'), ('suspicion', 0, True))
        self.assertEqual(M.arm_spec('random@4'), ('random', 4, True))

    def test_tests_and_verdict(self):
        def rows_with(f):
            return [row(i, arm, f(i, arm), df1=0.7 if '@4' in arm else 0.3) for i in range(12) for arm in M.ARMS]
        a = M.analyse(rows_with(lambda i, arm: {'fci': 0.2}.get(arm, 0.5 + 0.01 * i)))
        self.assertEqual((a['test1']['label'], a['verdict']), ('GENESIS_BEATS_FCI', 'HIDDEN_CAUSES_MARKED'))
        self.assertEqual(a['test2']['directed']['label'], 'EXPERIMENTS_ADD')
        self.assertEqual(a['test2']['bidirected']['label'], 'NO_DIFFERENCE')
        self.assertEqual({k: v['label'] for k, v in a['test3'].items()}, {'m2': 'NO_DIFFERENCE', 'm4': 'NO_DIFFERENCE'})
        a = M.analyse(rows_with(lambda i, arm: 0.3))
        self.assertEqual(a['verdict'], 'NOT_SHOWN')

    def test_checks(self):
        self.assertTrue(M.checks([row(1, 'fci', 0.1), row(1, 'suspicion@2', 0.1)]))
        self.assertFalse(M.checks([row(1, 'suspicion@4', 0.1, targets=[1, 2])]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R122(unittest.TestCase):
    """B20_R122's record: every answer re-scores against the regenerated truth; the tests and the verdict recompute."""

    def test_recomputes(self):
        from genesis.causal import admg as A
        from genesis.causal import sem as S
        ev = ROOT / 'evidence' / 'hidden_causes_v2_b20r122'
        s = json.loads((ev / 'summary.json').read_text())
        rows = [json.loads(l) for l in (ev / 'runs.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), M.N_SEEDS * len(M.ARMS))
        truths = {}
        for r in rows:
            if r['seed'] not in truths:
                truths[r['seed']] = S.planted(r['seed'], M.P, M.H, M.DENSITY, M.NOISE, M.K)
            self.assertEqual(json.loads(json.dumps(A.score(truths[r['seed']], r['answer']))), r['scores'])
        self.assertTrue(M.checks(rows) and s['valid'])
        a = json.loads(json.dumps(M.analyse(rows)))
        for k in ('means', 'test1', 'test2', 'test3', 'verdict'):
            self.assertEqual(a[k], s[k], k)
        self.assertEqual((a['verdict'], a['test2']['bidirected']['label'], a['test2']['directed']['label'],
                          a['test3']['m2']['label'], a['test3']['m4']['label']),
                         ('HIDDEN_CAUSES_MARKED', 'NO_DIFFERENCE', 'EXPERIMENTS_ADD', 'NO_DIFFERENCE', 'NO_DIFFERENCE'))


if __name__ == '__main__':
    unittest.main()
