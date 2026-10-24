"""B20_R127: the self-invented engine (design): fresh seed; the graph splits (sizes, classes, no shared or Gset
identity); the comparators; the sign test, the primary test and the verdict; the templates; the registered output."""
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
        self.assertEqual({s: len(v) for s, v in G.items()}, {'A': 6, 'B': 6, 'C': 6, 'D': 15})
        ids = [A.exposure_identity(t)['canonical'] for v in G.values() for _, t in v]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertFalse(set(ids) & ex)
        self.assertEqual({c for c, _ in G['D']}, {'random', 'planar', 'toroidal'})

    def test_templates_are_valid_programs(self):
        from genesis.candidate_kinds import mcx2 as K
        for prog in M.TEMPLATES.values():
            self.assertEqual(K.render(K.statements(prog)), prog)
        self.assertEqual(M.template_of(dict(K.DEFAULT)), ['REX'])

    def test_analysis(self):
        best = {f'G{k}': 100 for k in range(1, 13)}
        rows = [{'instance': f'G{k}', 'values': {'SYSTEM': 100, 'MCX': 99, 'REX': 98, 'BLS': 100}} for k in range(1, 13)]
        held = {'1': {f'g{k}': {'SYSTEM': 5, 'MCX': 4, 'REX': 5, 'BLS': 6} for k in range(8)}}
        a = M.analyse(held, rows, best)
        self.assertEqual((a['test1']['label'], a['verdict']), ('SYSTEM_BETTER', 'INVENTED_BETTER_THAN_HUMAN_DESIGN'))
        self.assertEqual(a['gset']['BLS']['label'], 'NOT_DISTINGUISHABLE')
        self.assertEqual(a['held_out']['1']['BLS']['label'], 'SYSTEM_WORSE')
        self.assertEqual(a['gset_reach_best_known'], {'SYSTEM': 12, 'MCX': 0, 'REX': 0, 'BLS': 12})
        self.assertEqual(a['record_candidates'], [])
        rows[0]['values']['SYSTEM'] = 101
        self.assertEqual(len(M.analyse(held, rows, best)['record_candidates']), 1)

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
