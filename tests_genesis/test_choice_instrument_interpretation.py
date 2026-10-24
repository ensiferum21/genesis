"""B20_R130: choice, instrument and interpretation, separated (design and record): fresh, disjoint seed ranges; the tests,
Holm and the verdicts; identifiability by intervened endpoints; validity; the registered output and its input."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r130_choice_instrument_interpretation as M  # noqa: E402


def synthetic(gain_interp, gain_choice, gain_inst, n=20):
    rows = []
    for s in range(n):
        for st in ('test', 'transfer'):
            def add(choice, interp, budget, f1, order=None):
                rows.append({'set': st, 'seed': s, 'choice': choice, 'order': order, 'interp': interp,
                             'budget': budget, 'targets': [0, 1], 'answer': {'bidirected': []}, 'problems': [],
                             'f1': f1, 'directed_f1': f1, 'cpu_s': 0.0})
            jit = 0.003 * s
            for b in M.BUDGETS:
                base = 0.2 + 0.02 * b + jit
                add('genesis', 'per_pair', b, base)
                add('genesis', 'global', b, base + gain_interp)
                add('genesis', 'joint', b, base + 0.01)
                for o in range(M.R_RANDOM):
                    add('random', 'global', b, base + gain_interp - gain_choice, o)
                    add('random', 'per_pair', b, base - 0.05, o)
                add('degree', 'global', b, base)
                add('oracle', 'global', b, base + 0.2)
            add('all', 'global', 'full', 0.7 + jit)
            add('all', 'llc', 'full', 0.7 + jit)
            add('all', 'per_pair', 'full', 0.5 + jit)
            add('all', 'per_pair_invented', 'full', 0.5 + gain_inst + jit)
    return rows


class Design(unittest.TestCase):
    def test_seeds_are_fresh_and_disjoint(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r130_choice_instrument_interpretation.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r129_adaptive_scientist as R129
        r129 = [(R129.SEED + off, R129.SEED + off + n) for off, n, _ in R129.SETS.values()]
        mine = sorted((M.SEED + off, M.SEED + off + n) for off, n, _ in M.SETS.values())
        for a0, a1 in mine:
            for b0, b1 in r129:
                self.assertTrue(a1 <= b0 or b1 <= a0)
        for (a0, a1), (b0, b1) in zip(mine, mine[1:]):
            self.assertLessEqual(a1, b0)
        with self.assertRaises(ValueError):
            M.world('test', 200)
        self.assertEqual((M.NOISE, M.BASE, M.SETS['test'][1]), ('gauss', R129.BASE, 200))

    def test_verdicts(self):
        a = M.analyse(synthetic(0.1, 0.1, 0.0))
        self.assertEqual((a['T_interpretation']['label'], a['T_choice']['label'], a['T_instrument']['label']),
                         ('INTERPRETATION_BETTER', 'CHOICE_BETTER', 'NO_DIFFERENCE'))
        self.assertEqual(a['verdict'], 'CHOICE+INTERPRETATION')
        a = M.analyse(synthetic(0.0, 0.0, 0.05))
        self.assertEqual(a['verdict'], 'INSTRUMENT')
        a = M.analyse(synthetic(-0.1, 0.0, 0.0))
        self.assertEqual(a['verdict'], 'NOT_SHOWN (WORSE: INTERPRETATION)')
        self.assertIn('headline_noninferiority', a['secondary'])
        self.assertIn('T_choice', M.analyse(synthetic(0.1, 0.1, 0.0), 'transfer'))

    def test_holm_and_identifiability(self):
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.02, 'c': 0.04}), {'a': True, 'b': True, 'c': True})
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.03, 'c': 0.04}), {'a': True, 'b': False, 'c': False})
        rows = [{'set': 'test', 'seed': 1, 'choice': 'genesis', 'interp': 'global', 'budget': 4, 'targets': [0, 3],
                 'answer': {'bidirected': [[0, 1]]}}]
        out = M.identifiability(rows, {1: {'confounded': [[0, 1], [2, 4], [3, 5]]}})
        self.assertEqual(out['4']['1'], {'marked': 1, 'hidden_causes': 2, 'recall': 0.5})
        self.assertEqual(out['4']['0'], {'marked': 0, 'hidden_causes': 1, 'recall': 0.0})

    def test_checks(self):
        r = {'problems': [], 'targets': [1, 2]}
        self.assertTrue(M.checks([r]))
        self.assertFalse(M.checks([dict(r, targets=[1, 1])]))
        self.assertFalse(M.checks([dict(r, problems=['x'])]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R130(unittest.TestCase):
    """B20_R130's record: the analysis, the Holm family, the verdict and identifiability recompute from the saved
    rows; every answer valid; the per-pair model and the joint priors recalibrate from the saved calibration worlds;
    a sample of worlds regenerates from its seeds and its runs replay exactly (global, per-pair, LLC and the invented
    instrument); the code identity is the run tree's."""
    IDENTITY = '48d08b3e13f77b13bb7e0495c8e888cd845e49856186d450031084b559d0043c'   # the run tree, 56e1301
    SAMPLE = {'test': 3, 'transfer': 2}

    @classmethod
    def setUpClass(cls):
        import json
        cls.ev = ROOT / 'evidence' / 'choice_instrument_interpretation_b20r130'
        cls.s = json.loads((cls.ev / 'summary.json').read_text())
        cls.rows = M.load_jsonl(cls.ev / 'runs.jsonl')
        cls.models = json.loads((cls.ev / 'models.json').read_text())
        cls.inst = json.loads((cls.ev / 'instruments.json').read_text())
        cls.worlds = {s: sorted(M.load_jsonl(cls.ev / f'worlds_{s}.jsonl'), key=lambda r: r['seed']) for s in M.SETS}

    def test_analysis_recomputes(self):
        import json
        truths = {r['seed']: r['truth'] for s in ('test', 'transfer') for r in self.worlds[s]}
        res = json.loads(json.dumps({'test': M.analyse(self.rows, 'test'), 'transfer': M.analyse(self.rows, 'transfer'),
                                     'identifiability': M.identifiability(self.rows, truths)}, default=float))
        for k in ('test', 'transfer', 'identifiability'):
            self.assertEqual(res[k], self.s[k], k)
        self.assertEqual(self.s['verdict'], res['test']['verdict'])
        self.assertTrue(M.checks(self.rows) and self.s['valid'])
        self.assertEqual(self.s['runs'], len(self.rows))
        self.assertEqual({s: len(v) for s, v in self.worlds.items()}, {s: v[1] for s, v in M.SETS.items()})
        self.assertEqual(self.s['code_identity'], self.IDENTITY)

    def test_models_recalibrate(self):
        import json
        from genesis.causal import active3 as A3
        cal = self.worlds['calibration']
        pp = json.loads(json.dumps(A3.calibrate([(r['prep'], r['truth']) for r in cal])))
        self.assertEqual(pp, self.models['per_pair'])
        best = max(self.inst['table'], key=lambda k: (round(self.inst['table'][k]['AB'], 12),
                                                      k == json.dumps(M_INS().R129, sort_keys=True), k))
        self.assertEqual(json.loads(best), self.inst['invented'])
        self.assertEqual(self.s['thresholds'], self.models['thresholds'])

    def test_thresholds_recalibrate(self):
        """The global estimator's thresholds, refitted on the 100 calibration worlds (about 9 minutes)."""
        import json
        cal = [M.Data(r) for r in self.worlds['calibration']]
        th = json.loads(json.dumps(M.calibrate_thresholds(cal)))
        self.assertEqual(th, self.models['thresholds'])

    def test_sample_regenerates_and_replays(self):
        import json
        import b20r129_adaptive_scientist as R129
        from genesis.causal import active3 as A3
        from genesis.causal import global_ml as GM
        from genesis.causal import instruments as INS
        from genesis.causal import sem as S
        from genesis.science import design as D
        import numpy as np
        R129_CHOICE = M.R129_CHOICE
        choice = json.loads(R129_CHOICE.read_text())
        g_acq = R129.acquisition(choice['genesis'], lam=json.loads((R129_CHOICE.parent / 'lambda.json').read_text())
                                 ['lambda'], invented=choice['invented'])
        tb, to = self.models['thresholds']['tb'], self.models['thresholds']['to']
        inv = self.inst['invented']
        inv_model = INS.calibrate([(r['prep'], r['truth'], INS.lab(inv, r['table'], r['settings']['p']))
                                   for r in self.worlds['calibration']], inv)
        saved = {}
        for r in self.rows:
            saved[(r['seed'], r['choice'], r['order'], r['interp'], str(r['budget']))] = r
        for set_name, k in self.SAMPLE.items():
            for row in self.worlds[set_name][:k]:
                seed, st = row['seed'], row['settings']
                view, truth = S.instance(seed, st['p'], st['h'], st['density'], M.NOISE, M.K, M.N_TOTAL)
                self.assertEqual(json.loads(json.dumps(truth)), row['truth'])
                prep = json.loads(json.dumps(A3.prepare(view, truth, M.N_INT, seed)))
                self.assertEqual(prep, row['prep'])
                d = M.Data(row)
                p = d.p
                dom = A3.CausalDomain(row['prep'], self.models['per_pair'])
                seqs = {('genesis', None): D.run(dom, g_acq, p)[0].done, ('degree', None): A3.degree_order(row['prep']),
                        ('oracle', None): A3.oracle_order(row['prep'], d.truth)}
                for o in range(M.R_RANDOM):
                    seqs[('random', o)] = [int(x) for x in R129.rng_for(seed, o).permutation(p)]
                for (c, o), seq in seqs.items():
                    for b in M.BUDGETS:
                        done = seq[:b]
                        B, Om, ok, _ = d.global_fit(done)
                        r = saved[(seed, c, o, 'global', str(b))]
                        self.assertEqual(r['targets'], list(done))
                        self.assertEqual(json.loads(json.dumps(GM.answer(B, Om, tb, to))), r['answer'])
                        key = (seed, c, o, 'per_pair', str(b))
                        if key in saved:
                            ans = A3.answer(p, M.per_pair_decisions(row['prep'], self.models['per_pair'], done))
                            self.assertEqual(json.loads(json.dumps(ans)), saved[key]['answer'])
                full = list(range(p))
                Bl, Ol = GM.llc(GM.covariances(d.X0, d.exps), p)
                self.assertEqual(json.loads(json.dumps(GM.answer(Bl, Ol, tb, to))),
                                 saved[(seed, 'all', None, 'llc', 'full')]['answer'])
                if set_name == 'test':
                    lab = INS.lab(inv, row['table'], p)
                    ans = A3.answer(p, M.per_pair_decisions(row['prep'], None, full, lab, inv_model))
                    self.assertEqual(json.loads(json.dumps(ans)), saved[(seed, 'all', None, 'per_pair_invented',
                                                                         'full')]['answer'])


def M_INS():
    from genesis.causal import instruments as INS
    return INS


if __name__ == '__main__':
    unittest.main()
