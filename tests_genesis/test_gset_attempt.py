"""B20_R116: the five-minute attempt (design): the remaining instances computed from the recorded runs, the
configuration rule, the analysis with record candidates flagged never claimed, and the registered output; the
record."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r116_gset_attempt as M  # noqa: E402


class Design(unittest.TestCase):
    def test_best_earlier_covers_the_recorded_runs(self):
        from genesis import gset as GS
        best = GS.best_known()
        e = M.best_earlier()
        self.assertEqual(set(e), {f'G{k}' for k in range(1, 55)})
        self.assertTrue(all(e[g] <= best[g] for g in e))             # no recorded value above a best known value
        self.assertGreaterEqual(sum(e[g] >= best[g] for g in e), 27)  # at least B20_R110's 27

    def test_configuration_rule(self):
        with mock.patch.object(M, 'R113', ROOT / 'evidence' / 'does_not_exist'):
            cfgs, classifier = M.configurations()
        self.assertEqual(set(cfgs), {'random', 'toroidal', 'planar'})
        self.assertEqual(cfgs['planar']['rs'], 1)                     # without B20_R113: B20_R105's planar choice
        self.assertIn('centroids', classifier)

    def test_analysis(self):
        best = {'G1': 100, 'G2': 50}
        rows = [{'instance': 'G1', 'value': 100, 'earlier': 99}, {'instance': 'G2', 'value': 51, 'earlier': 49}]
        a = M.analyse(rows, best)
        self.assertEqual((a['reach_best_known'], a['gains_over_earlier'], a['gaps']), (2, 2, {'G1': 0, 'G2': -1}))
        self.assertEqual(a['record_candidates'], [{'instance': 'G2', 'value': 51, 'best_known': 50}])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R116(unittest.TestCase):
    """B20_R116's record: the plan is the preregistered rule applied to the recorded runs; the analysis recomputes
    from the rows."""

    def test_recomputes(self):
        from genesis import gset as GS
        ev = ROOT / 'evidence' / 'gset_attempt_b20r116'
        s = json.loads((ev / 'summary.json').read_text())
        plan = json.loads((ev / 'plan.json').read_text())
        rows = [json.loads(l) for l in (ev / 'rows.jsonl').read_text().splitlines() if l.strip()]
        best = GS.best_known(as_of='2026-10-24T12:00:00+08:00')          # the table B20_R116 ran with
        earlier = M.best_earlier()
        self.assertEqual(plan['instances'], [g for g in (f'G{k}' for k in range(1, 55)) if earlier[g] < best[g]])
        self.assertEqual(plan['configurations'], M.configurations()[0])
        self.assertEqual([r['instance'] for r in rows], plan['instances'])
        a = json.loads(json.dumps(M.analyse(rows, best)))
        for k in ('instances', 'reach_best_known', 'reached', 'gains_over_earlier', 'gaps', 'mean_fraction',
                  'record_candidates'):
            self.assertEqual(a[k], s[k], k)
        self.assertTrue(s['valid'])
        self.assertEqual((s['reach_best_known'], s['reached'], s['record_candidates']),
                         (7, ['G19', 'G25', 'G29', 'G30', 'G37', 'G39', 'G52'], []))


if __name__ == '__main__':
    unittest.main()
