"""B20_R129: the adaptive experimental scientist (design): fresh, disjoint seed ranges; the worlds' settings; the
arms; experiments needed; the tests (Wilcoxon, non-inferiority, Holm) and the verdict; calibration error; the
validity check; the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r129_adaptive_scientist as M  # noqa: E402


def row(seed, arm, needed, f1, set_name='test', model='calibrated', order=None, p=10):
    r = {'set': set_name, 'model': model, 'arm': arm, 'seed': seed, 'p': p, 'targets': list(range(p)),
         'f1': f1, 'directed_f1': [0.5] * (p + 1), 'needed': needed, 'full': f1[-1],
         'entropy': [5.0 - 0.3 * b for b in range(p + 1)], 'choice_cpu_s': 0.001, 'problems': []}
    if order is not None:
        r['order'] = order
    return r


def synthetic(g_needed, g_f1_4, r_f1_8, n=20):
    rows = []
    for s in range(n):
        for st in ('test', 'transfer'):
            for arm in M.ESTABLISHED + M.BUILDER + ('oracle',):
                if arm == 'random':
                    for o in range(3):
                        f = [0.0] * 8 + [r_f1_8 + 0.001 * s] + [0.5, 0.5]
                        rows.append(row(s, 'random', 7 + (s % 3) * 0.5, f, st, order=o))
                        if st == 'test':
                            rows.append(row(s, 'random', 7, f, st, model='theory', order=o))
                    continue
                need = g_needed + (s % 4) * 0.25 if arm == 'decfall' else 5 + (s % 2)
                f = [0.0] * 4 + [g_f1_4 + 0.002 * s if arm == 'decfall' else 0.1] + [0.4] * 6
                rows.append(row(s, arm, need, f, st))
                if st == 'test' and arm in ('eig', 'decfall'):
                    rows.append(row(s, arm, need, f, st, model='theory'))
    return rows


CHOICE = {'genesis': 'decfall', 'best_invented': None, 'best_other': 'decfall'}


class Design(unittest.TestCase):
    def test_seeds_are_fresh_and_disjoint(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r129_adaptive_scientist.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r128_improve_the_improver as R128
        self.assertGreater(M.SEED, R128.SEED + 10000 * (R128.REPETITIONS + 1) + 10000)
        ranges = sorted((M.SEED + off, M.SEED + off + n) for off, n, _ in M.SETS.values())
        for (a0, a1), (b0, b1) in zip(ranges, ranges[1:]):
            self.assertLessEqual(a1, b0)
        self.assertEqual(M.world('test', 0)[0], M.SEED + 5000)
        with self.assertRaises(ValueError):
            M.world('test', 200)
        self.assertEqual(M.SETS['test'][1], 200)
        self.assertEqual((M.NOISE, M.BASE), ('gauss', {'p': 10, 'h': 3, 'density': 0.2}))
        self.assertNotEqual(M.SHIFT, M.BASE)

    def test_arms(self):
        from genesis.science import acquire as Q
        prep = {'p': 3, 'adj': {'0': [1], '1': [0, 2], '2': [1]}}
        truth = {'confounded': [[0, 2]]}
        for arm in M.ESTABLISHED + M.BUILDER + ('oracle',):
            acq = M.acquisition(arm, prep, truth, lam=1.0)
            self.assertIn(acq['kind'], ('random', 'order', 'static_eig', 'eig', 'dec', 'hybrid', 'program'))
            if acq['kind'] == 'program':
                self.assertIsNone(Q.check(acq['program']))
        self.assertEqual(M.acquisition('oracle', prep, truth)['order'][:2], [0, 2])
        self.assertEqual(M.acquisition('inv1', invented={'inv1': Q.EIG})['program'], Q.EIG)
        with self.assertRaises(ValueError):
            M.acquisition('nonsense')
        self.assertEqual(set(M.CANDIDATES) - set(M.ESTABLISHED) - set(M.BUILDER), set())

    def test_experiments_needed_on_a_world(self):
        from genesis.causal import active3 as A3
        from genesis.causal import sem as S
        view, truth = S.instance(M.SEED - 77, 6, 2, 0.4, 'gauss', 3, 1500)
        row_ = {'seed': 1, 'prep': A3.prepare(view, truth, 500, 1), 'truth': truth}
        w = M.World(row_, A3.THEORY)
        for arm in ('eig', 'decfall', 'degree', 'oracle'):
            acq = M.acquisition(arm, row_['prep'], truth, lam=1.0)
            r = M.full_row(w, 'test', 'theory', arm, acq, beliefs_at=4)
            self.assertEqual(sorted(r['targets']), list(range(6)))
            self.assertEqual(r['f1'][-1], w.full)
            self.assertEqual(r['needed'], w.experiments_needed(acq))
            self.assertLessEqual(r['needed'], 6)
            self.assertTrue(all(r['f1'][b] < w.full - M.EPS for b in range(r['needed'])))
            self.assertEqual(len(r['entropy']), 7)
            self.assertEqual(set(r['beliefs4']), set(r['true']))
        rr = M.full_row(w, 'test', 'theory', 'random', {'kind': 'random'}, M.rng_for(1, 0), order=0)
        self.assertEqual(rr['targets'], M.full_row(w, 'test', 'theory', 'random', {'kind': 'random'},
                                                   M.rng_for(1, 0), order=0)['targets'])
        self.assertTrue(M.checks([r, rr]))
        self.assertFalse(M.checks([dict(r, targets=r['targets'][:5])]))

    def test_statistics(self):
        a, b = [1.0 + 0.01 * i for i in range(20)], [0.0] * 20
        self.assertEqual(M.wilcoxon(a, b, ('B', 'W', 'N'))['label'], 'B')
        self.assertEqual(M.wilcoxon(b, a, ('B', 'W', 'N'))['label'], 'W')
        self.assertEqual(M.wilcoxon(a[:5], b[:5], ('B', 'W', 'N'))['label'], 'N')       # under 6 differences
        # non-inferiority: 0.03 worse is within the 0.05 margin, 0.10 worse is not
        x = [0.5 + 0.001 * i for i in range(30)]
        self.assertEqual(M.wilcoxon([v - 0.03 for v in x], x, ('OK', 'NO', 'NO'), 'greater', 0.05)['label'], 'OK')
        self.assertEqual(M.wilcoxon([v - 0.10 for v in x], x, ('OK', 'NO', 'NO'), 'greater', 0.05)['label'], 'NO')
        self.assertEqual(M.holm({'T1': 0.01, 'T2': 0.04}), {'T1': True, 'T2': True})
        self.assertEqual(M.holm({'T1': 0.03, 'T2': 0.04}), {'T1': False, 'T2': False})
        self.assertEqual(M.holm({'T1': 0.001, 'T2': 0.2}), {'T1': True, 'T2': False})
        self.assertAlmostEqual(M.ece([0.1, 0.1, 0.9, 0.9], [0, 0, 1, 1]), 0.1)
        self.assertIsNone(M.ece([], []))

    def test_verdicts(self):
        a = M.analyse(synthetic(3.0, 0.45, 0.40), CHOICE)
        self.assertEqual((a['test']['T1']['label'], a['test']['T2']['label']), ('FEWER_EXPERIMENTS', 'HALF_SUFFICES'))
        self.assertEqual(a['verdict'], 'ADAPTIVE_SCIENTIST_HALF_THE_EXPERIMENTS')
        a = M.analyse(synthetic(3.0, 0.20, 0.40), CHOICE)
        self.assertEqual(a['verdict'], 'ADAPTIVE_SCIENTIST')
        a = M.analyse(synthetic(9.0, 0.20, 0.40), CHOICE)
        self.assertEqual(a['verdict'], 'WORSE_THAN_RANDOM')
        self.assertEqual(set(a['secondary']) >= {'eig_vs_random', 'eig_vs_static_eig', 'genesis_vs_oracle',
                                                  'genesis@4_vs_random@8', 'regret_vs_oracle',
                                                  'theory_vs_calibrated_f1@4', 'information_vs_f1_gain_eig'}, True)
        self.assertIn('T1', a['transfer'])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
