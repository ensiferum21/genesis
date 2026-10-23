"""B20_R107: the feedback contract, version 2 (design): calibration on the judge's own two confirmation splits,
evaluations charged by cost, version 1 unchanged; the study's protocols, its k-host confirmation, its truth-based
labels and the registered output."""
from pathlib import Path
import random
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from genesis.autonomy import feedback as FB  # noqa: E402
import b20r107_contract_v2 as M  # noqa: E402


def toy_ops():
    return {'random': lambda rng: {'d': [rng.randrange(5) for _ in range(10)]},
            'mutate': lambda p, rng: {'d': [x if rng.random() > 0.3 else rng.randrange(5) for x in p['d']]},
            'crossover': lambda a, b, rng: {'d': [rng.choice(pair) for pair in zip(a['d'], b['d'])]},
            'size': lambda p: 1}


class Contract(unittest.TestCase):
    def test_bc_calibration_ignores_the_worker_s_quirks(self):
        rng = random.Random(3)
        quirk = {}

        def ev(p, split):                       # A carries a large per-program quirk; B and C only small noise
            q = quirk.setdefault(p['k'], rng.gauss(0, 10.0))
            return (q if split == 'A' else 0.0) + rng.gauss(0, 0.1)
        calib = [{'k': f'c{i}'} for i in range(32)]
        ab = FB.Judge(ev, calib, {'k': 's'}).tau
        bc = FB.Judge(ev, calib, {'k': 's'}, calibrate='BC').tau
        self.assertGreater(ab, 10 * bc)
        with self.assertRaises(ValueError):
            FB.Judge(ev, calib, {'k': 's'}, calibrate='AC')

    def test_costs_are_charged_and_v1_is_unchanged(self):
        rng = random.Random(4)
        ev = lambda p, s: rng.gauss(0, 1)
        _, a = FB.steady_state_search(toy_ops(), ev, 600, 1, contract=True)
        rng = random.Random(4)
        _, b = FB.steady_state_search(toy_ops(), ev, 600, 1, contract=True, calibrate='AB', cost=None)
        self.assertEqual(a, b)
        calls = []

        def counted(p, s):
            calls.append(s)
            return rng.gauss(0, 1)
        _, c = FB.steady_state_search(toy_ops(), counted, 600, 1, contract=True, calibrate='BC', cost={'B': 4, 'C': 4})
        self.assertEqual(c['evaluations'], sum(4 if s in 'BC' else 1 for s in calls))
        self.assertIn('C', calls)

    def test_v2_releases_a_real_effect_through_quirky_training_data(self):
        rng = random.Random(6)
        quirk = {}

        def ev(p, s):
            k = str(p['d'])
            q = quirk.setdefault((k, s), rng.gauss(0, 3.0)) if s == 'A' else 0.0
            return float(sum(p['d'])) + q + rng.gauss(0, 1)
        wide = {'random': lambda rng: {'d': [rng.randrange(10) for _ in range(20)]},
                'mutate': lambda p, rng: {'d': [x if rng.random() > 0.2 else rng.randrange(10) for x in p['d']]},
                'crossover': lambda a, b, rng: {'d': [rng.choice(pair) for pair in zip(a['d'], b['d'])]},
                'size': lambda p: 1}
        _, r = FB.steady_state_search(wide, ev, 1500, 2, contract=True, calibrate='BC')
        self.assertGreaterEqual(r['judge']['releases'], 1)


class Study(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r107_contract_v2.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_one_search_per_protocol(self):
        ops = M.R103.language_ops()
        for protocol in M.PROTOCOLS:
            r = M.one_search(ops, 'none', 1.0, protocol, 0, 0.15)
            self.assertEqual(r['protocol'], protocol)
            self.assertEqual(r['true_gain'], 0.0)
            self.assertLessEqual(r['evaluations'], M.MAX_EVALS + FB.FINALISTS * FB.FINAL_EVALS + 2 * M.K_HOSTS)
            self.assertEqual(r['judge'] is None, protocol == 'open')

    def test_labels(self):
        s_e = 0.15

        def tab(rel, claim, opt, gain1, gain2, open_gain=0.4):
            t = {}
            for q in M.Q_MULTIPLES:
                t[f'planted|q{q:g}|open'] = {'mean_true_gain': open_gain}
                for v, g in (('v1', gain1), ('v2', gain2)):
                    t[f'none|q{q:g}|{v}'] = {'release_share': rel, 'mean_claimed_gain': claim, 'mean_final_optimism': opt}
                    t[f'planted|q{q:g}|{v}'] = {'mean_true_gain': g}
            return t
        self.assertEqual(M.labels(tab(0.02, 0.01, 0.0, 0.1, 0.3), s_e)['headline'], 'V2_FIXES_POWER')
        self.assertEqual(M.labels(tab(0.02, 0.01, 0.0, 0.3, 0.3), s_e)['headline'], 'BOTH_WORK')
        self.assertEqual(M.labels(tab(0.02, 0.01, 0.0, 0.1, 0.1), s_e)['headline'], 'V2_TOO_STRICT')
        self.assertEqual(M.labels(tab(0.2, 0.01, 0.0, 0.3, 0.3), s_e)['headline'], 'V2_LEAKS')
        self.assertEqual(M.labels(tab(0.02, 0.01, 0.05, 0.3, 0.3), s_e)['headline'], 'V2_LEAKS')    # biased finals
        self.assertEqual(M.labels(tab(0.02, -0.5, 0.0, 0.3, 0.3), s_e)['v1']['label'], 'WORKS')      # truth, not ratio

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])



class RecordB20R107(unittest.TestCase):
    """B20_R107's record: the table and labels recompute from the 1,080 searches."""

    @classmethod
    def setUpClass(cls):
        import json
        ev = ROOT / 'evidence' / 'contract_v2_b20r107'
        cls.s = json.loads((ev / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (ev / 'searches.jsonl').read_text().splitlines() if l.strip()]

    def test_recomputes(self):
        import json
        self.assertEqual(len(self.rows), 2 * len(M.Q_MULTIPLES) * len(M.PROTOCOLS) * M.REPS)
        tab = json.loads(json.dumps(M.table(self.rows)))
        self.assertEqual(tab, self.s['table'])
        self.assertEqual(json.loads(json.dumps(M.labels(tab, self.s['sigma_e']))), self.s['labels'])
        self.assertEqual((self.s['labels']['headline'], self.s['labels']['v2']['label'], self.s['labels']['v1']['label']),
                         ('V2_FIXES_POWER', 'WORKS', 'LEAKS'))
        self.assertAlmostEqual(M.R103.sigma_e(), self.s['sigma_e'], places=12)

    def test_v1_s_leak_is_its_final_numbers_noise(self):
        """v1 fails HOLDS only on the bias tolerance (0.25 sigma_e) at quirks 0 and 2: means within 2.3 standard
        errors of zero; it released noise in 1 of 180 no-signal searches, as v2 did."""
        import statistics
        s_e = self.s['sigma_e']
        for v in ('v1', 'v2'):
            none = [r for r in self.rows if r['signal'] == 'none' and r['protocol'] == v]
            self.assertEqual(sum(r['judge']['releases'] > 0 for r in none), 1, v)
        for q in M.Q_MULTIPLES:
            xs = [r['final_optimism'] for r in self.rows if (r['signal'], r['q'], r['protocol']) == ('none', q, 'v1')]
            self.assertLess(abs(statistics.mean(xs)) / (statistics.stdev(xs) / len(xs) ** 0.5), 2.5)
            self.assertLessEqual(self.s['table'][f'none|q{q:g}|v1']['release_share'], 0.1)
        self.assertGreater(abs(self.s['table']['none|q0|v1']['mean_final_optimism']), M.MAX_BIAS * s_e)


if __name__ == '__main__':
    unittest.main()
