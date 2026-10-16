"""B20_R31 (s15.3, W10; GV4): the relaxation family's package replays from its sources, and the
recorded evidence keeps its contract. The obligations are checked, the generated patterns are the
generator's, the control is present, the hosts are fresh, the verdict is the preregistered one,
and the Part C tallies follow from its rows. Needs the formal workspace; the formal suite accepts
no skips."""
import copy
import json
import math
from pathlib import Path
import unittest

from genesis.formal_research import theory_package as TP
from genesis.invention import cuts as C

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'relaxation_invention_b20r31'


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.a = json.loads((EVIDENCE / 'part_a.json').read_text())
        cls.b = json.loads((EVIDENCE / 'part_b.json').read_text())
        cls.rows = json.loads((EVIDENCE / 'part_b_rows.json').read_text())
        cls.c = json.loads((EVIDENCE / 'part_c.json').read_text())
        cls.crows = json.loads((EVIDENCE / 'part_c_rows.json').read_text())

    def test_obligations_checked_and_package_replays(self):
        pats = C.generate()
        self.assertEqual(self.a['patterns'], [p['id'] for p in pats])
        self.assertEqual(self.a['usable'], self.a['patterns'])
        self.assertEqual(set(self.a['obligations'].values()), {'CHECKED'})
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        self.assertEqual(TP.replay(self.pkg)['verdict'], 'REPLAYED')
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')

    def test_verdict_follows_from_the_rows(self):
        self.assertEqual(len(self.rows), 48)
        self.assertEqual(set(self.b['comparisons']), {'control', 'menu', 'conventional', 'matched'})
        for other, c in self.b['comparisons'].items():
            diffs = [r['values']['new'] - r['values'][other] for r in self.rows]
            self.assertEqual(c['wins_ties_losses'], [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs),
                                                     sum(d < 0 for d in diffs)])
            self.assertEqual(c['passes'], c['mean'] >= 0.5 and c['interval_90'][0] > 0)
        want = 'UTILITY_AFTER_COST' if all(c['passes'] for c in self.b['comparisons'].values()) else \
            'NO_UTILITY_AFTER_COST'
        self.assertEqual(self.b['verdict'], want)

    def test_part_c_tallies_follow_from_the_rows(self):
        p = self.c['pooled']
        self.assertEqual(p['certified_hosts'], len(self.crows))
        for r in self.crows:
            self.assertLessEqual(r['lp_generated'], r['lp_triangle'] + 1e-6)
            self.assertGreaterEqual(r['lp_generated'] + 1e-6, r['optimum'])          # a valid relaxation
            self.assertEqual(r['floor_meets_optimum']['generated'], math.floor(r['lp_generated'] + 1e-6) == r['optimum'])
        self.assertEqual(p['floor_meets_optimum_generated'],
                         sum(r['floor_meets_optimum']['generated'] for r in self.crows))
        self.assertEqual(p['newly_met_by_generated_rows'],
                         sum(r['floor_meets_optimum']['generated'] and not r['floor_meets_optimum']['triangle']
                             for r in self.crows))

    def test_hosts_are_fresh(self):
        ids = {r['task_id'] for r in self.rows} | set(self.b['hosts']['select'])
        r30 = json.loads((ROOT / 'evidence' / 'certification_budget_b20r30' / 'hosts.json').read_text())['tasks']
        self.assertFalse(ids & {t['task_id'] for t in r30})
        for d in ('quotient_invention_b20r26', 'decomposition_invention_b20r27'):
            prior = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())
            self.assertFalse(ids & {t['task_id'] for v in prior.values() for k in v for t in v[k]})
        look = json.loads((EVIDENCE / 'development_look_hosts.json').read_text())['tasks']
        self.assertEqual(len(look), 6)
        self.assertFalse(ids & {t['task_id'] for t in look})

    def test_hosts_are_in_the_exposure_addenda(self):
        hosts = json.loads((EVIDENCE / 'hosts.json').read_text())
        look = json.loads((EVIDENCE / 'development_look_hosts.json').read_text())['tasks']
        ids = {t['task_id'] for v in hosts.values() for t in v} | {t['task_id'] for t in look}
        self.assertEqual(len(ids), 78)
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
