"""B20_R131: the cascade on a real case (design): fresh, disjoint seeds; the archive step (every evaluated rule
dormant with an inferred, scored failed_due_to edge) and the trigger's selection on a toy trace; the refusals."""
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r131_cascade as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh_and_disjoint(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r131_cascade.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r129_adaptive_scientist as R129
        import b20r130_choice_instrument_interpretation as R130
        import b20r133_problem_compiler as R133
        mine = [(M.SEED + o, M.SEED + o + n) for o, n in M.SETS.values()]
        others = [(R129.SEED + o, R129.SEED + o + n) for o, n, _ in R129.SETS.values()]
        others += [(R130.SEED + o, R130.SEED + o + n) for o, n, _ in R130.SETS.values()]
        others += [(R133.SEED, R133.SEED + 4000)]
        for a0, a1 in mine:
            for b0, b1 in others:
                self.assertTrue(a1 <= b0 or b1 <= a0)
        with self.assertRaises(ValueError):
            M.world('test', 200)
        self.assertEqual(M.FUEL, 24)

    def test_archive_and_trigger_on_a_toy_trace(self):
        from genesis import vault as V
        trace = [(0, 0, {'agg': 'sum', 'expr': 'eig'}, 'A', -5.0), (0, 1, {'agg': 'sum', 'expr': 'dec'}, 'A', -4.0),
                 (0, 2, {'agg': 'sum', 'expr': 'eig'}, 'B', -5.5), (1, 3, {'agg': 'max', 'expr': 'pf'}, 'A', -6.0)]
        with tempfile.TemporaryDirectory() as d, V.Vault(Path(d) / 'v') as v:
            ids, ev = M.archive(v, trace, lambda m: None)
            self.assertEqual(len(ids), 3)
            for a in ids:
                st = v.status(a)
                self.assertEqual((st['status'], st['failure']), ('dormant', 'context_limited'))
            trig = v.put(V.Vault.record('CapabilityRecord', {'name': 't', 'unlocks': ['interpretation']},
                                        domain='causal', creator={'process': 'test'}))
            opps = v.opportunities(trig, 2)
            texts = [v.get(a)['content']['text'] for a in opps]
            self.assertEqual(texts, ['sum dec', 'sum eig'])                 # best stored training score first
            self.assertEqual(v.get(ids[0])['contracts']['scores'], {'A': -5.0, 'B': -5.5})

    def test_refusals(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R131(unittest.TestCase):
    """B20_R131's record (NO_VERIFIED_TRIGGER): the verdict follows from B20_R130's recorded summary; the means, the
    winners and the costs recompute from the saved rows and phases; the vault (packed as vault.tar.xz) restores,
    verifies, holds every archived rule dormant with its inferred edge, and the trigger was never verified; the null
    trigger has no opportunities; a sample of test worlds replays exactly; the code identity is the run tree's."""
    IDENTITY = '4ea230c6bbffb0bf60b4b97519c93372026ca8cf2af22a72953a4ac73f165cb4'   # the run tree, 68e24c0
    SAMPLE = 2

    @classmethod
    def setUpClass(cls):
        import json
        cls.ev = ROOT / 'evidence' / 'cascade_b20r131'
        cls.s = json.loads((cls.ev / 'summary.json').read_text())
        cls.ph = json.loads((cls.ev / 'phases.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.ev / 'runs.jsonl').read_text().splitlines()]

    def test_verdict_and_analysis_recompute(self):
        import json
        import statistics
        s130 = json.loads((ROOT / 'evidence' / 'choice_instrument_interpretation_b20r130' / 'summary.json').read_text())
        shown = bool(s130['test']['holm']['interpretation']) and \
            s130['test']['T_interpretation']['label'] == 'INTERPRETATION_BETTER'
        self.assertFalse(shown)
        self.assertFalse(self.ph['shown'])
        self.assertEqual(self.s['verdict'], 'NO_VERIFIED_TRIGGER')
        self.assertNotIn('reactivated', self.ph['arms'])                 # no reactivation without a verified trigger
        self.assertNotIn('primary', self.s)
        by = {(r['seed'], r['arm']): r['score'] for r in self.rows}
        seeds = sorted({r['seed'] for r in self.rows})
        self.assertEqual(len(seeds), M.SETS['test'][1])
        arms = sorted({r['arm'] for r in self.rows})
        self.assertEqual(arms, ['eig', 'fresh', 'null', 'random'])
        means = {a: statistics.mean(by[(x, a)] for x in seeds) for a in arms}
        self.assertEqual(json.loads(json.dumps(means)), self.s['means'])
        for a, d in self.ph['arms'].items():
            self.assertEqual(len(d['tested']), M.FUEL)                    # matched compute: FUEL evaluations each
            best = max(range(len(d['tested'])), key=lambda i: (round(d['tested'][i]['score'], 12), -i))
            self.assertEqual(d['tested'][best]['program'], self.s['winners'][a])
            self.assertEqual(max(x['score'] for x in d['tested']), self.s['arm_training_best'][a])
            self.assertEqual(d['cpu_s'], self.s['arm_cpu_s'][a])
        self.assertEqual(self.s['winners']['eig'], {'kind': 'eig'})
        self.assertEqual(self.s['null_opportunities'], 0)
        self.assertEqual({k: v for k, v in self.ph['archive'].items() if k != 'ids'}, self.s['archive'])
        self.assertEqual(self.s['archive']['rules'], len(self.ph['archive']['ids']))
        self.assertTrue(self.s['valid'])
        self.assertEqual(self.s['code_identity'], self.IDENTITY)

    def test_vault_restores_and_verifies(self):
        import tarfile
        from genesis import vault as V
        with tempfile.TemporaryDirectory() as d:
            with tarfile.open(self.ev / 'vault.tar.xz') as t:
                t.extractall(d, filter='data')
            with V.Vault(Path(d) / 'vault') as v:
                rep = v.verify()
                self.assertEqual(rep['integrity'], 'LOCAL_HASH_CHECKED')
                self.assertEqual({k: rep[k] for k in ('artifacts', 'events', 'head')},
                                 {k: self.s['vault'][k] for k in ('artifacts', 'events', 'head')})
                ids = self.ph['archive']['ids']
                self.assertEqual(rep['artifacts'], len(ids) + 4)          # + two evidence records, two triggers
                for a in ids[:: max(1, len(ids) // 50)]:
                    st = v.status(a)
                    self.assertEqual((st['status'], st['failure']), ('dormant', 'context_limited'))
                edges = v.edges(kind='failed_due_to')
                self.assertEqual({e['src'] for e in edges}, set(ids))
                self.assertTrue(all(e['dst'] == 'tag:interpretation' and e['confidence'] == 0.5 for e in edges))
                self.assertNotEqual(v.status(self.ph['trigger'])['status'], 'verified')
                self.assertEqual(v.opportunities(self.ph['null'], M.FUEL), [])
                self.assertEqual(v.edges(kind='reactivated_by'), [])

    def test_sample_replays(self):
        """Every arm's winner re-scored on the first test worlds under the global interpretation (about a minute)."""
        import json
        models = json.loads((self.ev / 'models.json').read_text())
        tb, to = models['thresholds']['tb'], models['thresholds']['to']
        self.assertEqual(models['thresholds'], self.s['thresholds'])
        worlds = sorted((json.loads(x) for x in (self.ev / 'worlds_test.jsonl').read_text().splitlines()),
                        key=lambda r: r['seed'])
        saved = {(r['seed'], r['arm']): r for r in self.rows}
        from genesis.science import design as D
        for row in worlds[:self.SAMPLE]:
            self.assertEqual(M.world('test', row['seed'] - M.SEED - M.SETS['test'][0])[0], row['seed'])
            w = M.GWorld(row, models['per_pair'], tb, to)
            for arm, prog in sorted(self.s['winners'].items()):
                acq = prog if 'kind' in prog else {'kind': 'program', 'program': prog}
                r, _ = D.run(w.dom, acq, max(M.BUDGETS), beliefs=w.beliefs)
                rec = saved[(row['seed'], arm)]
                self.assertEqual(r.done, rec['targets'])
                self.assertEqual({str(b): w.f1(r.done[:b]) for b in M.BUDGETS}, rec['f1'])


if __name__ == '__main__':
    unittest.main()
