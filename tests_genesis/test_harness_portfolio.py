"""B20_R148 (design): fresh seeds and disjoint instance blocks; the ten test tasks, the held-out ones and the
development tasks; the registered output and the protected judge's digest; a run spends its matched budget; the
analysis (H1's rule, the primary tests, Holm, labels and the verdict) on synthetic rows; validity."""
from pathlib import Path
import itertools
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r148_harness_portfolio as M  # noqa: E402
from genesis.autonomy import portfolio as P  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r148_harness_portfolio.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        self.assertFalse(re.search(r'\b214\d{5}\b', ''.join(p.read_text() for p in (ROOT / 'scripts').glob('*.py')
                                                            if p.name != 'b20r148_harness_portfolio.py')))

    def test_instance_seed_blocks_are_disjoint(self):
        used = []
        for phase in M.PHASES:
            for i, (d, f, _) in enumerate(M.TASKS):
                for s in 'AVT':
                    base = M.instance_seed(phase, i, s)
                    n = M.SIZES['acquire'][s] if d == 'acquire' else 1
                    used.append(range(base, base + n))
        for a, b in itertools.combinations(used, 2):
            self.assertFalse(set(a) & set(b))
        self.assertTrue(all(max(r) < M.SEED + 300000 for r in used))
        self.assertTrue(all(M.SIZES['acquire'][s] <= 100 for s in 'AVT'))

    def test_tasks_and_roles(self):
        self.assertEqual(len(M.TASKS), 10)
        held = [(d, f) for d, f, h in M.TASKS if h]
        self.assertEqual(held, [('acquire', 'large'), ('formula', 'mixed'), ('mcx2', 'torus'), ('mcx2', 'erdos_pm1')])
        dev = [(d, f) for _, d, f in M.dev_tasks_spec()]
        self.assertEqual(len(dev), 6)
        self.assertFalse(set(dev) & set(held))
        self.assertTrue(all(d != 'mcx2' for d, _ in dev))
        self.assertEqual(len(M.test_tasks_spec()), 10)
        self.assertEqual(set(M.ACQ_SETTINGS), {f for d, f, _ in M.TASKS if d == 'acquire'})
        self.assertEqual(set(M.MCX_SETTINGS), {f for d, f, _ in M.TASKS if d == 'mcx2'})

    def test_registered_output_and_protected_judge(self):
        self.assertEqual(M.protected_digest(), M.PROTECTED_FEEDBACK_SHA256)
        with self.assertRaises(SystemExit):
            M.main(['/tmp/elsewhere'])

    def test_constants_match_the_preregistration(self):
        doc = M.__doc__
        self.assertEqual((M.B, M.J, M.ROUNDS, M.EXPLORE), (1024, 5, 32, 10))
        self.assertEqual(M.RUN_SEEDS, tuple(range(6)))
        self.assertEqual((M.DEV_SEEDS, M.TUNE_SEEDS, M.CANDIDATES, M.REFERENCE_N), ((100, 101, 102), (200, 201), 4, 32))
        self.assertIn('B = 1024', doc)
        self.assertIn('Six run seeds (0-5)', doc)
        self.assertIn('A 24, V 32, T 64', doc)
        self.assertEqual(P.checkpoints(M.B, M.J), [32, 64, 128, 256, 512, 1024])

    def test_a_run_spends_its_matched_budget(self):
        from genesis.autonomy import portfolio_tasks as PT
        t = PT.formula_task('small', {s: PT.formula_items(91919700 + i, 100) for i, s in enumerate('AVT')},
                            name='formula:small')
        for arm in ('single:evolution', 'halving', 'halving_tuned'):
            row = M.run_row(t, arm, 0, None)
            self.assertTrue(M.B - 2 <= row['used'] <= M.B, (arm, row['used']))
            self.assertEqual(len(row['curve']), M.J + 1)
            self.assertIsNotNone(row['answer'])


def synthetic(better='halving', by=0.1, noise=0.0, beat_all=True, spread=0.01):
    """Rows for every task, seed and arm: each arm's curve is constant; `better` gets +by on every task."""
    rows = []
    for d, f, _ in M.TASKS:
        t = f'{d}:{f}'
        for s in M.RUN_SEEDS:
            for k, arm in enumerate(P.ARMS):
                base = 0.5 + spread * (k % 3) + noise * ((s * 7 + k) % 5 - 2) / 100
                if arm == better:
                    base += by
                if beat_all and arm == f'single:{P.HARNESSES[(len(t) + s * 0) % 6]}':
                    base += 0.2                                    # one harness wins each task, by family
                rows.append({'task': t, 'arm': arm, 'seed': s, 'curve': [base] * (M.J + 1), 'used': M.B,
                             'cpu_s': 1.0})
    norms = {f'{d}:{f}': {'low': 0.0, 'references': {}} for d, f, _ in M.TASKS}
    return rows, norms


class Analysis(unittest.TestCase):
    def test_holm_and_labels(self):
        self.assertEqual(M.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
        self.assertEqual(M.label(0.01, 0.2), 'BETTER')
        self.assertEqual(M.label(0.01, -0.2), 'WORSE')
        self.assertEqual(M.label(0.2, 0.2), 'NOT_DISTINGUISHABLE')

    def test_a_portfolio_that_dominates_is_g2_better(self):
        rows, norms = synthetic('halving', by=0.3)
        res = M.analyse(rows, norms, {'hstar': 'anneal'})
        self.assertEqual(res['primary']['T1']['label'], 'BETTER')
        self.assertEqual(res['primary']['T2']['label'], 'BETTER')
        self.assertEqual(res['verdict'], 'G2_BETTER')
        self.assertEqual(res['primary']['T3']['label'], 'WORSE')
        self.assertEqual(res['g3'], 'G3_HURTS')

    def test_equal_arms_show_nothing(self):
        rows, norms = synthetic(None, by=0.0, beat_all=False, spread=0.0)
        res = M.analyse(rows, norms, {'hstar': 'evolution'})
        self.assertEqual(res['verdict'], 'NOT_SHOWN')
        self.assertEqual(res['g3'], 'G3_NOT_SHOWN')
        self.assertEqual(res['H1']['label'], 'UNIVERSAL_HARNESS')     # nobody is beaten on every seed

    def test_h1_rule(self):
        rows, norms = synthetic(None, by=0.0, beat_all=True)
        res = M.analyse(rows, norms, {'hstar': 'evolution'})
        # each task has one winning harness: a harness is beaten wherever another one wins on all seeds
        self.assertEqual(res['H1']['label'], 'NO_UNIVERSAL_HARNESS' if not res['H1']['unbeaten'] else
                         'UNIVERSAL_HARNESS')
        for h, tasks in res['H1']['beaten_on'].items():
            for t in tasks:
                self.assertNotEqual(res['H1']['winner_by_task'][t], h)

    def test_validity(self):
        rows, _ = synthetic()
        self.assertIsNone(M.validity(rows))
        self.assertEqual(M.validity(rows[1:]), 'INVALID_MISSING_ROWS')
        bad = [dict(r) for r in rows]
        bad[0]['used'] = M.B - 10
        self.assertEqual(M.validity(bad), 'INVALID_BUDGET')


R148 = ROOT / M.OUT


@unittest.skipUnless((R148 / 'summary.json').exists(), 'B20_R148 has not run in this tree')
class RecordB20R148(unittest.TestCase):
    """The record of B20_R148 on its evidence: the preregistered script unchanged; validity; the verdict, H1 and every
    label recompute from the saved rows; development chose H* and G3's parameters from development rows only."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((R148 / 'summary.json').read_text())
        cls.rows = M.load_jsonl(R148 / 'rows.jsonl')
        cls.norms = json.loads((R148 / 'norms.json').read_text())
        cls.dev = json.loads((R148 / 'dev.json').read_text())

    def test_the_preregistered_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r148_harness_portfolio.py').read_bytes()).hexdigest(),
                         'd20a30d4728190e62ce6d24cc1f334a451a534c4a0bb875936c842035dbd3409')

    def test_validity_and_the_labels_recompute(self):
        self.assertIsNone(M.validity(self.rows))
        res = M.analyse(self.rows, self.norms, self.dev)
        self.assertEqual(res['verdict'], self.s['verdict'])
        self.assertEqual(res['g3'], self.s['g3'])
        self.assertEqual(res['H1']['label'], self.s['H1']['label'])
        for k in ('T1', 'T2', 'T3'):
            self.assertEqual(res['primary'][k]['label'], self.s['primary'][k]['label'])
            self.assertAlmostEqual(res['primary'][k]['p_holm'], self.s['primary'][k]['p_holm'])

    def test_development_used_development_rows_only(self):
        drows = M.load_jsonl(R148 / 'dev_rows.jsonl')
        dev_tasks = {f'{d}:{f}' for _, d, f in M.dev_tasks_spec()}
        self.assertEqual({r['task'] for r in drows}, dev_tasks)
        self.assertEqual(len(drows), len(dev_tasks) * 6 * len(M.DEV_SEEDS))
        self.assertEqual(set(self.dev['dev_tasks']), dev_tasks)
        self.assertEqual(f"single:{self.dev['hstar']}", self.s['hstar'])
        for h, params in self.dev['tuned'].items():
            self.assertIn(params, self.dev['tuning'][h]['settings'])


if __name__ == '__main__':
    unittest.main()
