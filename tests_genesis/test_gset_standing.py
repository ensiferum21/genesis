"""B20_R102: where the pinned tools stand on Gset (design): the arms and budgets, the analysis on synthetic rows
(fractions, families, the virtual best, record candidates are flagged never claimed) and the validity rule."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r102_gset_standing as M  # noqa: E402


def row(inst, fam, runs):
    return {'instance': inst, 'family': fam, 'runs': {a: {b: {'value': v, 'status': 'SUCCESS', 'cpu_ns': int(float(b) * 1e9)}
                                                        for b, v in byb.items()} for a, byb in runs.items()}}


class Design(unittest.TestCase):
    def test_arms(self):
        D = M.arms()
        self.assertEqual(len(D), 4 + 10)
        self.assertEqual({k for k in D if k[0] in ('burer', 'dsb')},
                         {('burer', 1.0), ('burer', 10.0), ('dsb', 1.0), ('dsb', 10.0)})
        self.assertEqual(D[('burer', 10.0)]['parameters'], {'heuristic': 'BURER2002', 'cpu_seconds': 10.0})
        from genesis.candidate_kinds import mqlib_maxcut as MQ
        self.assertEqual(set(M.OTHERS) | {'BURER2002'}, set(MQ.HEURISTICS))

    def test_analysis(self):
        best = {'G1': 100, 'G2': 50}
        rows = [row('G1', 'random', {'burer': {'1': 90, '10': 100}, 'dsb': {'1': 95, '10': 99}, 'x': {'10': 101}}),
                row('G2', 'toroidal', {'burer': {'1': 40, '10': 45}, 'dsb': {'1': 45, '10': 48}, 'x': {'10': 47}})]
        a = M.analyse(rows, best)
        self.assertAlmostEqual(a['per_arm']['burer@10']['mean_fraction'], (1.0 + 0.9) / 2)
        self.assertEqual(a['per_arm']['burer@10']['reach_best_known'], 1)
        self.assertEqual(a['per_arm']['dsb@10']['by_family'], {'random': 0.99, 'toroidal': 0.96})
        self.assertEqual(a['vbs10']['reach_best_known'], 1)
        self.assertAlmostEqual(a['vbs10']['mean_fraction'], (1.01 + 0.96) / 2)
        self.assertEqual(a['record_candidates'], [{'instance': 'G1', 'arm': 'x', 'budget': '10', 'value': 101,
                                                   'best_known': 100}])

    def test_validity(self):
        rows = [row('G1', 'random', {'burer': {'1': 90, '10': 100}})]
        self.assertTrue(M.validity(rows)[0])
        rows[0]['runs']['burer']['10']['cpu_ns'] = int(8e9)
        self.assertFalse(M.validity(rows)[0])
        rows = [row('G1', 'random', {'burer': {'1': 90, '10': 100}})]
        rows[0]['runs']['burer']['1']['status'] = 'TIMEOUT'
        self.assertFalse(M.validity(rows)[0])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])

    def test_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r102_gset_standing.py').read_text())


class RecordB20R102(unittest.TestCase):
    """B20_R102's record: the analysis and validity recompute from the rows; the table and the archive are the
    recorded ones; every instance has every arm."""

    @classmethod
    def setUpClass(cls):
        import json
        ev = ROOT / 'evidence' / 'gset_standing_b20r102'
        cls.s = json.loads((ev / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (ev / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_analysis_recomputes(self):
        import json
        from genesis import gset as GS
        from genesis.common import digest
        self.assertEqual([r['instance'] for r in self.rows], [f'G{k}' for k in range(1, 55)])
        best = GS.best_known()
        a = json.loads(json.dumps(M.analyse(self.rows, best)))
        for k in ('per_arm', 'record_candidates', 'vbs10'):
            self.assertEqual(a[k], self.s[k], k)
        ok, med, fails = M.validity(self.rows)
        self.assertEqual((ok, fails), (self.s['valid'], self.s['failed_runs']))
        self.assertEqual(self.s['best_known_sha256'], digest(json.loads((GS.DATA / 'best_known.json').read_text())))
        self.assertEqual(self.s['gset_archive_sha256'], GS.manifest()['archive_sha256'])
        self.assertTrue(all(len(r['runs']) == 12 for r in self.rows))

if __name__ == '__main__':
    unittest.main()
