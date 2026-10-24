"""B20_R123: three more five-minute seeds (design): the remaining instances from every recorded run, B20_R116's
configurations read as recorded, seeds distinct from B20_R116's, the analysis with record candidates flagged never
claimed, and the registered output."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r123_gset_seeds as M  # noqa: E402


class Design(unittest.TestCase):
    def test_remaining_instances(self):
        from genesis import gset as GS
        best = GS.best_known()
        e = M.best_earlier()
        todo = [g for g in (f'G{k}' for k in range(1, 55)) if e[g] < best[g]]
        self.assertEqual(todo, ['G14', 'G15', 'G22', 'G24', 'G26', 'G31', 'G35', 'G36', 'G38', 'G41', 'G42', 'G51',
                                'G53', 'G54'])
        self.assertEqual(sum(e[g] >= best[g] for g in e), 40)

    def test_configurations_are_b20r116s(self):
        import json
        c = M.configurations()
        self.assertEqual(c, json.loads((M.R116_DIR / 'plan.json').read_text())['configurations'])
        self.assertEqual(c['planar']['rs'], 2)

    def test_seeds_are_distinct_from_b20r116s(self):
        from genesis.common import digest
        tid = 'gset-G35'
        mine = {M.run_seed(tid, k) for k in range(M.SEEDS)}
        self.assertEqual(len(mine), M.SEEDS)
        self.assertNotIn(int(digest({'study': 'b20r116', 'task': tid})[:12], 16), mine)

    def test_analysis(self):
        best = {'G1': 100, 'G2': 50}
        rows = [{'instance': 'G1', 'k': 0, 'value': 99}, {'instance': 'G1', 'k': 1, 'value': 100},
                {'instance': 'G1', 'k': 2, 'value': 97}, {'instance': 'G2', 'k': 0, 'value': 51}]
        a = M.analyse(rows, best, {'G1': 98, 'G2': None})
        self.assertEqual((a['reach_best_known'], a['reached']), (2, ['G1', 'G2']))
        self.assertEqual(a['per_instance']['G1']['spread_300s'], 3)
        self.assertEqual(a['per_instance']['G1']['reached_runs'], 1)
        self.assertEqual(a['record_candidates'], [{'instance': 'G2', 'k': 0, 'value': 51, 'best_known': 50}])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
