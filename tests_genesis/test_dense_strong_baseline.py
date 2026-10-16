"""B20_R38: the dense strong-baseline audit keeps its contract. The arms are the frozen package
descriptors, the verdicts follow from the rows by the preregistered rule, no arm exceeds a
certified optimum, and the hosts are fresh and in the exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'dense_strong_baseline_b20r38'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.h = json.loads((EVIDENCE / 'hosts.json').read_text())

    def test_arms_are_the_frozen_descriptors(self):
        for s in ('e1', 'e1b'):
            d = ROOT / 'handoff' / s
            self.assertEqual(self.s['descriptors'][f'{s}:candidate'],
                             json.loads((d / 'candidate_descriptor.json').read_text())['descriptor_id'])

    def test_verdicts_follow_from_the_rows(self):
        import b20r38_dense_strong_baseline as R38
        self.assertEqual(len(self.rows), 40)
        for key, res in self.s['results'].items():
            s, stratum = key.split('|')
            rs = [r for r in self.rows if r['stratum'] == stratum]
            d = R38.contrast(rs, lambda r: r['arms'][f'{s}:candidate']['value'] - r['arms'][f'{s}:mip']['value'])
            self.assertEqual(res['candidate_minus_mip'], d)
            self.assertEqual(res['verdict'], R38.verdict(d))

    def test_no_arm_exceeds_a_certified_optimum(self):
        for r in self.rows:
            if r['optimum'] is not None:
                self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        ids = {t['task_id'] for t in self.h['tasks']}
        r37 = json.loads((ROOT / 'evidence' / 'generator_v2_b20r37' / 'hosts.json').read_text())['tasks']
        self.assertFalse(ids & {t['task_id'] for t in r37})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
