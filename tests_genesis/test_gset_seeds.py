"""B20_R123: three more five-minute seeds (design): the remaining instances from every recorded run, B20_R116's
configurations read as recorded, seeds distinct from B20_R116's, the analysis with record candidates flagged never
claimed, and the registered output; the record."""
import json
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


class RecordB20R123(unittest.TestCase):
    """B20_R123's record: the plan is the preregistered rule; the analysis recomputes from the rows against the table
    it ran with; its two record candidates (G38, 7688) are the value of the max-bisection literature (2013)."""

    def test_recomputes(self):
        from genesis import gset as GS
        ev = ROOT / 'evidence' / 'gset_seeds_b20r123'
        s = json.loads((ev / 'summary.json').read_text())
        plan = json.loads((ev / 'plan.json').read_text())
        rows = [json.loads(l) for l in (ev / 'rows.jsonl').read_text().splitlines() if l.strip()]
        then = GS.best_known(as_of='2026-10-24T12:00:00+08:00')
        e = M.best_earlier()
        self.assertEqual(plan['instances'], [g for g in (f'G{k}' for k in range(1, 55)) if e[g] < then[g]])
        self.assertEqual(plan['configurations'], M.configurations())
        self.assertEqual(sorted((r['instance'], r['k']) for r in rows),
                         sorted((g, k) for g in plan['instances'] for k in range(M.SEEDS)))
        r116 = {r['instance']: r['value'] for r in M.R116._rows(M.R116_DIR / 'rows.jsonl')}
        a = json.loads(json.dumps(M.analyse(rows, then, r116)))
        for k in ('per_instance', 'instances', 'reach_best_known', 'reached', 'record_candidates'):
            self.assertEqual(a[k], s[k], k)
        self.assertTrue(s['valid'])
        self.assertEqual(s['reached'], ['G15', 'G22', 'G31', 'G38', 'G41'])
        self.assertEqual({(c['instance'], c['value']) for c in s['record_candidates']}, {('G38', 7688)})
        now = GS.best_known()
        self.assertEqual(now['G38'], 7688)                                   # already known: no record
        self.assertEqual(M.analyse(rows, now, r116)['record_candidates'], [])


if __name__ == '__main__':
    unittest.main()
