"""B20_R151's design (`scripts/b20r151_expressiveness.py`), checked before it runs.

A fresh seed; three candidate classes of 2,000-vertex graphs, fresh, pairwise disjoint and disjoint from Gset; the
searches matched within each level (the ceiling four times the inventor's graph-seconds) and the same code in both
languages; a Λ0 search evaluates Λ0 programs only and a Λ1 search reaches Λ1's constructs; the half-budget ceiling is
the full ceiling's own trajectory; the ablations; the gate, Holm, the labels and the verdict on synthetic gains; and,
end to end with a stub engine, a planted expressiveness gain (a target, which Λ0 cannot write) is found EXPRESSIVE,
and a null one is not."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r151_expressiveness as S  # noqa: E402
from genesis.autonomy import selfimprove as SI  # noqa: E402
from genesis.candidate_kinds import mcx2 as K2  # noqa: E402
from genesis.candidate_kinds import mcx3 as K3  # noqa: E402


def stub_runner(planted=0.01, headroom=None):
    """A stand-in for the engine: a value per graph, noise from the seed, (1 + planted) for programs with a target,
    and REX at 10 s (1 + headroom[class]) better."""
    headroom = headroom or {'planar': 0.006, 'toroidal': 0.004, 'random': 0.0005}

    def run(cfg, task, seed, budget):
        base = 1000 + int(hashlib.sha256(task.task_id.encode()).hexdigest()[:4], 16) % 500
        noise = 1 + 0.0004 * (random.Random(seed).random() - 0.5)
        v = base * noise
        if '@' in cfg['prog']:
            v *= 1 + planted
        if budget > S.BUDGET:
            cls = 'planar' if task.family.startswith('planar') else 'toroidal' if task.family.startswith('torus')                 else 'random'
            v *= 1 + headroom[cls]
        return v, budget
    return run


class Design(unittest.TestCase):
    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('b20r*.py') if p.name != 'b20r151_expressiveness.py']
        self.assertFalse(any(re.search(rf'\b{S.SEED}\b', p.read_text()) for p in others))
        self.assertEqual(S.CEIL_EVALS * S.CEIL_SIZE, 4 * S.INV_EVALS * S.INV_SIZE)
        self.assertEqual((S.INV_EVALS, S.INV_SIZE, S.BUDGET), (240, 4, 1.0))          # B20_R132's inventor
        self.assertEqual(S.CEIL_HALF * 2, S.CEIL_EVALS)
        self.assertEqual(S.BOUND, K3.LAMBDA0_MAX)
        self.assertIsNone(SI.check_process(S.ceiling_process()))
        self.assertEqual(S.file_digest(ROOT / 'src/genesis/autonomy/feedback.py'), S.PROTECTED_FEEDBACK_SHA256)
        self.assertEqual((K3.BINARY_SHA256, K2.BINARY_SHA256), (S.MCX3_SHA256, S.MCX2_SHA256))
        self.assertEqual(set(S.CANDIDATES), {'planar2000', 'toroidal2000', 'random2000'})

    def test_graphs_are_fresh_and_disjoint(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        gset = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
        G = S.graphs(gset)
        ids = []
        for c, g in G.items():
            self.assertEqual((len(g['H']), len(g['T']), len(g['A'])), (S.H_GRAPHS, S.T_GRAPHS, S.INV_REPS))
            for t in g['H'] + g['T'] + sum(g['A'], []):
                self.assertEqual(t.n, 2000)
                ids.append(A.exposure_identity(t)['canonical'])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & gset)


class Searches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from genesis.models_maxcut import MaxCutTask
        rng = random.Random(5)
        cls.tasks = [MaxCutTask(task_id=f'planar-x{i}', n=30, family='planar2',
                                edges=tuple((u, v, 1) for u in range(30) for v in range(u + 1, 30) if rng.random() < 0.2))
                     for i in range(8)]

    def test_languages_and_budgets(self):
        lab = S.Lab(runner=stub_runner())
        for lang in S.LANGS:
            cfg, rep, calls = S.search(lab, lang, 'inventor', self.tasks, 7)
            self.assertGreaterEqual(rep['evaluations'], S.INV_EVALS)
            progs = [lab.programs[c['engine']]['prog'] for c in calls]
            l0 = [K3.is_lambda0(K3.parse(p)) for p in progs]
            if lang == 'L0':
                self.assertTrue(all(l0))
            else:
                self.assertFalse(all(l0))
            self.assertTrue(all(c['length'] <= S.BOUND for c in calls))
            self.assertEqual(progs[0], K3.DEFAULT['prog'])                         # REX first
        with self.assertRaises(AssertionError):
            S.evaluator(lab, self.tasks, 'L0')(dict(K3.DEFAULT, prog='b1 X@h'), 'A')

    def test_the_half_ceiling_is_the_full_ceilings_trajectory(self):
        lab = S.Lab(runner=stub_runner())
        _, rh, half = S.search(lab, 'L1', 'ceiling', self.tasks, 11, S.CEIL_HALF)
        _, rf, full = S.search(lab, 'L1', 'ceiling', self.tasks, 11)
        self.assertGreaterEqual(rf['evaluations'], S.CEIL_EVALS)
        n = S.CEIL_HALF
        self.assertEqual([(c['engine'], c['occ']) for c in half[:n]], [(c['engine'], c['occ']) for c in full[:n]])

    def test_ablations(self):
        p = K3.parse('b3 ?f<500 [ X@h I ] *3 [ D L ] S9 M@a')
        got = {w: K3.render(S.ablate(p, w)) for w in S.ABLATIONS}
        self.assertEqual(got, {'targets': 'b3 ?f<500 [ X I ] *3 [ D L ] S9 M@a'.replace('M@a', 'M'),
                               'guards': 'b3 X@h I *3 [ D L ] S9 M@a',
                               'repeats': 'b3 ?f<500 [ X@h I ] D L S9 M@a',
                               'blocks': 'b3 ?f<500 X@h I *3 [ D L ] S9 M@a'})
        self.assertEqual(S.constructs(p), {'targets': True, 'guards': ['f'], 'repeats': True, 'blocks': True})


class Analysis(unittest.TestCase):
    def arms(self):
        return {f'{a}_{r}': f'{a}_{r}' for a, n in (('I0', S.INV_REPS), ('I1', S.INV_REPS), ('C0', S.CEIL_REPS),
                                                   ('C1', S.CEIL_REPS), ('C0h', S.CEIL_REPS), ('C1h', S.CEIL_REPS))
                for r in range(n)}

    def gains(self, lift):
        rng = random.Random(3)
        return {k: [rng.gauss(0, 0.0002) + lift.get(k[:2], 0.0) for _ in range(S.T_GRAPHS)] for k in self.arms()}

    def test_gate(self):
        base = {f't{i}': 1000.0 for i in range(12)}
        self.assertTrue(S.gate(base, {t: 1003.0 + i * 0.01 for i, t in enumerate(base)})['pass'])
        self.assertFalse(S.gate(base, {t: 1001.0 + i * 0.01 for i, t in enumerate(base)})['pass'])     # 0.1%
        g = {'a': {'mean': 0.004, 'pass': True}, 'b': {'mean': 0.009, 'pass': True}, 'c': {'mean': 0.02, 'pass': False},
             'd': {'mean': 0.003, 'pass': True}}
        self.assertEqual(S.select(g), ['b', 'a'])

    def test_the_replicate_test(self):
        self.assertAlmostEqual(S.replicate_test([3, 4, 5], [0, 1, 2])['p'], 1 / 20)
        self.assertAlmostEqual(S.replicate_test([0, 1, 2], [3, 4, 5], 'less')['p'], 1 / 20)
        self.assertGreater(S.replicate_test([9, 0, 0], [0.1, 0.2, 0.3])['p'], S.ALPHA)
        self.assertEqual(S.replicate_test([1, 1, 1], [1, 1, 1])['p'], 1.0)

    def test_a_lucky_replicate_is_not_a_language(self):
        lucky = self.gains({})
        lucky['C1_0'] = [x + 0.005 for x in lucky['C1_0']]          # one Λ1 ceiling search found a much better engine
        r = S.analyse_class(self.arms(), lucky)
        self.assertLess(r['P1']['p'], 0.001)                          # the per-graph test alone would say yes
        self.assertGreater(r['P1']['replicates']['p'], S.ALPHA)
        v, _ = S.verdict(['x'], {'x': r}, True)
        self.assertEqual((v, r['P1']['label']), ('NOT_SHOWN', 'NOT_SHOWN'))

    def test_a_stuck_lambda0_replicate_is_not_expressiveness(self):
        stuck = self.gains({})
        for r in range(S.CEIL_REPS):
            stuck[f'C1_{r}'] = [x + 0.0001 for x in stuck[f'C1_{r}']]    # noise-level better than Λ0's good searches
        stuck['C0_2'] = [x - 0.004 for x in stuck['C0_2']]               # one Λ0 ceiling search stuck
        r = S.analyse_class(self.arms(), stuck)
        self.assertLess(r['P1']['p'], 0.001)
        self.assertGreaterEqual(r['P1']['mean'], S.MATERIAL)
        self.assertLessEqual(r['P1']['replicates']['p'], S.ALPHA)                # dominance holds, by noise
        self.assertLess(r['P1']['replicates']['margin'], S.MATERIAL)
        self.assertEqual(S.verdict(['x'], {'x': r}, True)[0], 'NOT_SHOWN')

    def test_labels_and_verdict(self):
        planted = S.analyse_class(self.arms(), self.gains({'C1': 0.002, 'I1': 0.001}))
        null = S.analyse_class(self.arms(), self.gains({}))
        hurts = S.analyse_class(self.arms(), self.gains({'I1': -0.003}))
        pc = {'x': planted, 'y': null, 'z': hurts}
        v, ph = S.verdict(['x', 'y', 'z'], pc, True)
        self.assertEqual(v, 'EXPRESSIVENESS_GAIN')
        self.assertEqual((pc['x']['reading'], pc['y']['reading'], pc['z']['reading']),
                         ('EXPRESSIVE', 'NO_LANGUAGE_EFFECT', 'LANGUAGE_HARDER_TO_SEARCH'))
        self.assertEqual(set(ph), {'x', 'y', 'z'})
        self.assertEqual(S.verdict(['y'], {'y': null}, True)[0], 'NOT_SHOWN')
        self.assertEqual(S.verdict([], {}, True)[0], 'NO_HEADROOM')
        self.assertEqual(S.verdict(['x'], {'x': planted}, False)[0], 'INVALID')
        self.assertEqual(S.holm({'a': 0.01, 'b': 0.04}), {'a': 0.02, 'b': 0.04})


class EndToEnd(unittest.TestCase):
    """The whole study with a stub engine: a planted gain only Λ1 can express is found; none is not."""

    def run_study(self, planted):
        import json
        with tempfile.TemporaryDirectory() as d:
            code = S.main([d], runner=stub_runner(planted), registered=False)
            self.assertEqual(code, 0)
            return json.loads((Path(d) / 'summary.json').read_text())

    def test_planted_and_null(self):
        s = self.run_study(0.01)
        self.assertEqual(s['studied'], ['planar2000', 'toroidal2000'])
        self.assertTrue(s['valid'], s['pins'])
        self.assertEqual(s['verdict'], 'EXPRESSIVENESS_GAIN')
        for c in s['studied']:
            self.assertEqual(s['per_class'][c]['P1']['label'], 'EXPRESSIVE')
            self.assertEqual(s['per_class'][c]['ablations'].get('C1_0|targets', -1) < 0, True)
        n = self.run_study(0.0)
        self.assertEqual(n['verdict'], 'NOT_SHOWN')


R151 = ROOT / 'evidence' / 'expressiveness_b20r151'


@unittest.skipUnless((R151 / 'summary.json').exists(), 'B20_R151 has not been recorded')
class RecordB20R151(unittest.TestCase):
    """The record of B20_R151 on its evidence: the amended script that ran its later slices; validity; the gate and the
    truth tables from the saved runs; the analysis (every class's P1, S1-S5, labels, Holm and the verdict) recomputed
    from the saved inputs; the graphs regenerate with the recorded identities."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R151 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R151 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r
        cls.rex = S.Lab.ekey(dict(K3.DEFAULT))

    def run_value(self, ek, task, occ, budget='1'):
        return self.runs[f'{ek}|{task}|{occ}|{budget}']['value']

    def test_the_script(self):
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r151_expressiveness.py').read_bytes()).hexdigest(),
                         '8742dd8de359f6596367bdde49d73bfaa8a8f4d602a48dd4a7d9e735d998035c')

    def test_validity(self):
        import statistics
        s = self.s
        self.assertTrue(s['valid'] and s['spent'] and s['disjoint'] and all(s['pins'].values()))
        cpus = {}
        for r in self.runs.values():
            b = r['key'].rsplit('|', 1)[1]
            cpus.setdefault(b, []).append(r['cpu'] / float(b))
        self.assertTrue(all(statistics.median(v) >= 0.9 for v in cpus.values()))
        self.assertEqual({b: statistics.median(v) for b, v in cpus.items()}, s['cpu_median'])

    def test_the_gate_from_the_runs(self):
        for c, ids in self.s['graphs'].items():
            base = {t: (self.run_value(self.rex, t, 0) + self.run_value(self.rex, t, 1)) / 2 for t in ids['H']}
            long = {t: self.run_value(self.rex, t, 0, '10') for t in ids['H']}
            g = S.gate(base, long)
            self.assertAlmostEqual(g['mean'], self.s['gates'][c]['mean'])
            self.assertAlmostEqual(g['p'], self.s['gates'][c]['p'])
            self.assertEqual(g['pass'], self.s['gates'][c]['pass'])
        self.assertEqual(S.select(self.s['gates']), self.s['studied'])

    def test_the_truth_tables_from_the_runs(self):
        import statistics
        for c in self.s['studied']:
            f = self.s['finals'][c]
            for t, b in f['base'].items():
                self.assertAlmostEqual(b, statistics.mean(self.run_value(self.rex, t, o) for o in range(S.T_RUNS)))
            for ek, vals in f['values'].items():
                for t, v in vals.items():
                    self.assertAlmostEqual(v, statistics.mean(self.run_value(ek, t, o) for o in range(S.T_RUNS)))

    def test_the_analysis_recomputes(self):
        import statistics
        per = {}
        for c in self.s['studied']:
            f = self.s['finals'][c]
            g = S.gains(f['values'], f['base'])
            per[c] = S.analyse_class(self.s['arms'][c], g)
        v, ph = S.verdict(self.s['studied'], per, self.s['valid'])
        self.assertEqual(v, self.s['verdict'])
        for c in self.s['studied']:
            got, rec = per[c], self.s['per_class'][c]
            for k in ('P1', 'S1'):
                self.assertEqual(got[k]['label'], rec[k]['label'])
                self.assertAlmostEqual(got[k]['p'], rec[k]['p'])
                self.assertAlmostEqual(got[k]['mean'], rec[k]['mean'])
                self.assertAlmostEqual(got[k]['replicates']['p'], rec[k]['replicates']['p'])
            self.assertAlmostEqual(got['P1']['replicates']['margin'], rec['P1']['replicates']['margin'])
            self.assertEqual(got['reading'], rec['reading'])
            for lang in ('L0', 'L1'):
                self.assertEqual(got['S4'][lang]['label'], rec['S4'][lang]['label'])
            for k, x in got['lanes'].items():
                self.assertAlmostEqual(x, rec['lanes'][k])

    def test_the_lambda0_arms_wrote_lambda0_only(self):
        calls = json.loads((R151 / 'calls.json').read_text())
        progs = json.loads((R151 / 'programs.json').read_text())
        for key, cs in calls.items():
            if key.split('|')[1][1] == '0':
                for c in cs:
                    self.assertTrue(K3.is_lambda0(K3.parse(progs[c['engine']]['prog'])), key)

    def test_the_graphs_regenerate(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        G = S.graphs({A.exposure_identity(t)['canonical'] for t in GS.tasks()})
        for c, ids in self.s['graphs'].items():
            self.assertEqual([t.task_id for t in G[c]['H']], ids['H'])
            self.assertEqual([t.task_id for t in G[c]['T']], ids['T'])
            self.assertEqual([[t.task_id for t in a] for a in G[c]['A']], ids['A'])


if __name__ == '__main__':
    unittest.main()
