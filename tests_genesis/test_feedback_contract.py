"""B20_R103: the feedback contract (`autonomy.feedback`) and the zero-signal battery (design).

The judge evaluates each program on its confirmation data at most once, releases only beyond a fixed threshold and
stops a stalled search; the search is `solver_search`'s algorithm; on pure noise the contract releases nothing and
stops, on a large real effect it releases; the study's oracle, noise estimate and labels."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from genesis.autonomy import feedback as FB  # noqa: E402
import b20r103_zero_signal as M  # noqa: E402


def toy_ops():
    """Programs are tuples of digits; quality is their sum (a real, climbable signal when used)."""
    return {'random': lambda rng: {'d': [rng.randrange(5) for _ in range(10)]},
            'mutate': lambda p, rng: {'d': [x if rng.random() > 0.3 else rng.randrange(5) for x in p['d']]},
            'crossover': lambda a, b, rng: {'d': [rng.choice(pair) for pair in zip(a['d'], b['d'])]},
            'size': lambda p: 1}


class Contract(unittest.TestCase):
    def test_the_search_is_solver_search_s(self):
        from genesis.invention import solver_search as SS
        self.assertEqual((FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS, FB.FINALISTS),
                         (SS.POP, SS.CHILDREN, SS.LEADERS, SS.TOURNAMENT, SS.P_CROSS, SS.FINALISTS))
        self.assertEqual(FB.FINAL_EVALS, len(SS.FINAL_BUDGETS) * SS.FINAL_SEEDS)

    def test_judge_rules(self):
        rng = random.Random(1)
        vals = {}

        def ev(p, split):
            vals[(p['k'], split)] = vals.get((p['k'], split), 0) + 1
            return {'A': 0.0, 'B': 0.0}[split] + (10.0 if p['k'] == 'good' and split == 'B' else rng.gauss(0, 1))
        calib = [{'k': f'c{i}'} for i in range(32)]
        J = FB.Judge(ev, calib, {'k': 'start'}, patience=3)
        self.assertGreater(J.tau, 0)
        self.assertIsNone(J.submit({'k': 'c1'}))                   # a calibration program: already judged
        self.assertIsNotNone(J.submit({'k': 'good'}))
        self.assertEqual(J.releases, 1)
        before = vals[('good', 'B')]
        self.assertIsNone(J.submit({'k': 'good'}))                # judged once; no second draw
        self.assertEqual(vals[('good', 'B')], before)
        for k in ('x1', 'x2'):
            J.submit({'k': k})
        self.assertTrue(J.stopped)                                  # three generations without a release

    def test_no_signal_releases_nothing_and_stops(self):
        rng = random.Random(5)
        releases = 0
        for seed in range(10):
            w, rep = FB.steady_state_search(toy_ops(), lambda p, s: rng.gauss(0, 1), 1500, seed, contract=True)
            releases += rep['judge']['releases']
            self.assertTrue(rep['judge']['stopped'])
            self.assertLess(rep['evaluations'], 1500)
        self.assertLessEqual(releases, 1)                            # about 5% of stalled searches by design

    def test_a_large_real_effect_is_released(self):
        rng = random.Random(6)
        ev = lambda p, s: float(sum(p['d'])) + rng.gauss(0, 1)
        w, rep = FB.steady_state_search(toy_ops(), ev, 1500, 2, contract=True)
        self.assertGreaterEqual(rep['judge']['releases'], 1)
        self.assertGreaterEqual(sum(w['d']), 32)
        w2, rep2 = FB.steady_state_search(toy_ops(), ev, 1500, 2, contract=False)
        self.assertIsNone(rep2['judge'])
        self.assertGreaterEqual(sum(w2['d']), 32)


class Study(unittest.TestCase):
    def test_seed_is_fresh(self):
        import re
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r103_zero_signal.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_noise_estimate_comes_from_the_recorded_searches(self):
        s = M.sigma_e()
        self.assertTrue(0.1 < s < 0.2, s)

    def test_oracle(self):
        o = M.Oracle(2.0, 0.0, 1.0, 9)
        p = {'rep': 'cross_2', 'body': [['descent'], ['descent'], ['loop', [['descent']]]]}
        self.assertEqual(M.descents(p), 3)
        self.assertEqual(o.truth(p), 6.0)
        self.assertEqual(o.quirk(p, 'A'), o.quirk(p, 'A'))         # persistent per program and split
        self.assertNotEqual(o.quirk(p, 'A'), o.quirk(p, 'B'))
        self.assertEqual(o(p, 'A'), 6.0 + o.quirk(p, 'A'))           # no fresh noise when sigma_e = 0

    def test_labels(self):
        def rows(signal, q, protocol, claimed, gain):
            return [{'signal': signal, 'q': q, 'protocol': protocol, 'claimed_gain': claimed, 'true_gain': gain}]
        base = []
        for q in M.Q_MULTIPLES:
            base += rows('none', q, 'open', 1.0, 0.0) + rows('none', q, 'contract', 0.0, 0.0)
            base += rows('planted', q, 'open', 1.0, 4.0) + rows('planted', q, 'contract', 1.0, 3.0)
        self.assertEqual(M.labels(base, 0.15, 0.05, 0.05),
                         {'l1_no_signal': 'CONTRACT_HOLDS', 'l1_planted_signal': 'POWER_KEPT',
                          'headline': 'CONTRACT_WORKS', 'l2': 'CALIBRATED'})
        weak = [dict(r, true_gain=1.0) if (r['signal'], r['protocol'], r['q']) == ('planted', 'contract', 2.0) else r
                for r in base]
        self.assertEqual(M.labels(weak, 0.15, 0.05, 0.2)['headline'], 'CONTRACT_TOO_STRICT')
        self.assertEqual(M.labels(weak, 0.15, 0.05, 0.2)['l2'], 'OVERCONFIDENT')
        leaky = [dict(r, claimed_gain=0.5) if (r['signal'], r['protocol']) == ('none', 'contract') else r for r in base]
        self.assertEqual(M.labels(leaky, 0.15, 0.0, 0.0)['headline'], 'CONTRACT_LEAKS')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
