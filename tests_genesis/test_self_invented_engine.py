"""B20_R127: the self-invented engines (design, as amended before any run, and the record): fresh seed; per-class graph splits (sizes,
classes, no shared or Gset identity); the comparators; the sign test, the primary test and the verdict; compounding
over generations; the 60 s arm and record candidates flagged never claimed; the templates; the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r127_self_invented_engine as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r127_self_invented_engine.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_graphs(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        ex = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
        G = M.graphs(ex)
        self.assertEqual(set(G), set(M.CLASSES))
        for cls in M.CLASSES:
            self.assertEqual({s: len(v) for s, v in G[cls].items()}, {'A': 4, 'B': 4, 'C': 4, 'D': 5})
        ids = [A.exposure_identity(t)['canonical'] for c in G.values() for v in c.values() for t in v]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertFalse(set(ids) & ex)
        self.assertTrue(all(t.family.startswith('dev-planar2') or 'planar2' in t.family for t in G['planar']['D']))

    def test_templates_are_valid_programs(self):
        from genesis.candidate_kinds import mcx2 as K
        for prog in M.TEMPLATES.values():
            self.assertEqual(K.render(K.statements(prog)), prog)
        self.assertEqual(M.template_of(dict(K.DEFAULT)), ['REX'])

    def test_analysis(self):
        best = {f'G{k}': 100 for k in range(1, 13)}
        rows = [{'instance': f'G{k}', 'values': {'SYSTEM': 100, 'MCX': 99, 'REX': 98, 'BLS': 100}, 'long': 100}
                for k in range(1, 13)]
        held = {'1': {f'g{k}': {'SYSTEM': 5, 'MCX': 4, 'REX': 5, 'BLS': 6} for k in range(8)}}
        gens = {f'g{k}': {'G1': 4, 'G2': 5, 'G3': 6} for k in range(8)}
        r110 = {f'G{k}': 99 for k in range(1, 13)}
        a = M.analyse(held, gens, rows, best, r110)
        self.assertEqual((a['test1']['label'], a['verdict']), ('SYSTEM_BETTER', 'INVENTED_BETTER_THAN_HUMAN_DESIGN'))
        self.assertEqual(a['gset']['BLS']['label'], 'NOT_DISTINGUISHABLE')
        self.assertEqual(a['held_out']['1']['BLS']['label'], 'SYSTEM_WORSE')
        self.assertEqual(a['compounding']['label'], 'COMPOUNDS')
        self.assertEqual((a['long']['vs_r110']['label'], a['long']['reach_best_known']), ('SYSTEM_BETTER', 12))
        self.assertEqual(a['gset_reach_best_known'], {'SYSTEM': 12, 'MCX': 0, 'REX': 0, 'BLS': 12})
        self.assertEqual(a['record_candidates'], [])
        rows[0]['long'] = 101
        rc = M.analyse(held, gens, rows, best, r110)['record_candidates']
        self.assertEqual(rc, [{'instance': 'G1', 'engine': 'SYSTEM', 'budget': 60.0, 'value': 101, 'best_known': 100}])
        gens = {f'g{k}': {'G1': 6, 'G2': 5, 'G3': 4} for k in range(8)}
        self.assertEqual(M.analyse(held, gens, rows, best, r110)['compounding']['label'], 'REGRESSES')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R127(unittest.TestCase):
    """B20_R127's record: every judged run's witness cut re-checked on its regenerated graph; the run set complete; the
    summary's tables are the runs'; the analysis, the tests and the verdict recompute against the best-known table as
    it stood when the run ended; the engines are valid programs; the judge released nothing in any search; valid; the
    code identity is the tree the study was preregistered with (8d7e402)."""
    IDENTITY = 'badf60cbbc8d6af7c5ac48b75fe3a8ab342dc6c7cf2b86be3c3e7df133606e6f'
    AS_OF = '2026-10-24T16:20:17+08:00'     # the run's end (chain.log)

    @classmethod
    def setUpClass(cls):
        import json
        cls.ev = ROOT / 'evidence' / 'self_invented_engine_b20r127'
        cls.s = json.loads((cls.ev / 'summary.json').read_text())
        cls.rows = [json.loads(line) for line in (cls.ev / 'runs.jsonl').read_text().splitlines() if line.strip()]
        cls.search = json.loads((cls.ev / 'search.json').read_text())

    def test_run_set(self):
        keys = [r['key'] for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))
        parts = {p: sum(k.startswith(p + '|') for k in keys) for p in 'DGL'}
        self.assertEqual(parts, {'D': 15 * 4 * 2 + 15 * 2, 'G': 54 * 4, 'L': 54})
        self.assertEqual(self.s['failed_runs'], sum(r['status'] != 'SUCCESS' for r in self.rows))

    def test_witnesses(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        ex = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
        tasks = {t.task_id: t for c in M.graphs(ex).values() for v in c.values() for t in v}
        tasks.update({t.task_id: t for t in GS.tasks()})
        for r in self.rows:
            if r['status'] != 'SUCCESS':
                continue
            t, side = tasks[r['task']], r['side']
            self.assertEqual(len(side), t.n, r['key'])
            self.assertEqual(sum(w for u, v, w in t.edges if side[u] != side[v]), r['value'], r['key'])

    def test_tables_and_analysis_recompute(self):
        import json
        from genesis import gset as GS
        import b20r116_gset_attempt as R116
        val = {r['key']: r['value'] for r in self.rows}
        for b, rows in self.s['held_out_values'].items():
            for task, d in rows.items():
                for e, v in d.items():
                    self.assertEqual(val[f'D|{task}|{e}|{float(b):g}'], v)
        for task, d in self.s['generation_values'].items():
            self.assertEqual(val[f'D|{task}|G1|1'], d['G1'])
            self.assertEqual(val[f'D|{task}|G2|1'], d['G2'])
            self.assertEqual(val[f'D|{task}|SYSTEM|1'], d['G3'])
        ids = {t.task_id.split('-')[1]: t.task_id for t in GS.tasks()}
        self.assertEqual([g['instance'] for g in self.s['gset_rows']], list(ids))
        for g in self.s['gset_rows']:
            for e, v in g['values'].items():
                self.assertEqual(val[f"G|{ids[g['instance']]}|{e}|10"], v)
            self.assertEqual(val[f"L|{ids[g['instance']]}|SYSTEM|60"], g['long'])
        r110 = {r['instance']: r['value'] for r in R116._rows(R116.R110 / 'rows.jsonl')}
        a = json.loads(json.dumps(M.analyse(self.s['held_out_values'], self.s['generation_values'],
                                            self.s['gset_rows'], GS.best_known(as_of=self.AS_OF), r110)))
        for k in ('gset', 'held_out', 'compounding', 'gset_reach_best_known', 'gset_mean_fraction', 'long',
                  'record_candidates', 'test1', 'verdict'):
            self.assertEqual(a[k], self.s[k], k)

    def test_engines_judge_validity_identity(self):
        from genesis.candidate_kinds import mcx2 as K
        for cls in M.CLASSES:
            e = self.s['engines'][cls]
            self.assertEqual(e, self.search['generations'][f'{cls}|{M.GENERATIONS}']['engine'])
            self.assertIsNone(K.check_config(e), cls)
        self.assertEqual(len(self.search['generations']), 9)
        for k, g in self.search['generations'].items():
            self.assertEqual(g['report']['judge']['releases'], 0, k)
        self.assertTrue(self.s['valid'])
        self.assertTrue(all(m >= 0.9 for m in self.s['cpu_median'].values()))
        self.assertEqual(self.s['code_identity'], self.IDENTITY)


if __name__ == '__main__':
    unittest.main()
