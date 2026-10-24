"""B20_R127: the self-invented engines (design, as amended before any run): fresh seed; per-class graph splits (sizes,
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


if __name__ == '__main__':
    unittest.main()
