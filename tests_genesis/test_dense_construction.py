"""B20_R36: the dense construction study (relaxation family, attempt 2) keeps its contract. The
component is the Lean-checked K5 bound of B20_R31, the comparisons and the verdict follow from
the rows by the B20_R17 rule, no arm exceeds a certified optimum, and the hosts are fresh and in
the exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'dense_construction_b20r36'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'part_b_rows.jsonl').read_text().splitlines() if l.strip()]
        cls.h = json.loads((EVIDENCE / 'hosts.json').read_text())

    def test_component_is_the_checked_k5_bound(self):
        import b20r36_dense_construction as R36
        self.assertEqual(self.s['patterns'], [R36.K5_ID])
        a = json.loads((ROOT / 'evidence' / 'relaxation_invention_b20r31' / 'part_a.json').read_text())
        self.assertEqual(a['obligations'][f'pc_{R36.K5_ID}'], 'CHECKED')
        self.assertEqual(self.s['attempts_in_family'], ['B20_R31', 'B20_R36'])

    def test_comparisons_and_verdict_follow_from_the_rows(self):
        import b20r36_dense_construction as R36
        self.assertEqual(len(self.rows), 32)
        for other, c in self.s['comparisons'].items():
            self.assertEqual(c, R36.compare(self.rows, other))
        rule = all(self.s['comparisons'][o]['passes'] for o in ('control', 'menu', 'conventional', 'matched'))
        self.assertEqual(self.s['verdict'], 'UTILITY_AFTER_COST' if rule else 'NO_UTILITY_AFTER_COST')
        self.assertEqual(self.s['beyond_mip'], self.s['comparisons']['mip']['passes'])

    def test_no_arm_exceeds_a_certified_optimum(self):
        for r in self.rows:
            if r['optimum'] is not None:
                self.assertTrue(all(v <= r['optimum'] for v in r['values'].values()))

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        ids = {t['task_id'] for k in ('select', 'eval') for t in self.h[k]}
        self.assertEqual(len(ids), 48)
        r35 = json.loads((ROOT / 'evidence' / 'dense_certification_b20r35' / 'hosts.json').read_text())['tasks']
        self.assertFalse(ids & {t['task_id'] for t in r35})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
