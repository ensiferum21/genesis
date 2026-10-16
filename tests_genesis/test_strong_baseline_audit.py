"""B20_R33: the strong-baseline audit keeps its contract. The arms are the frozen package
descriptors, the contrasts and verdicts follow from the rows by the preregistered rule, the MIP
witnesses never exceed a certified optimum, and the hosts are fresh and in the exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'strong_baseline_audit_b20r33'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.hosts = json.loads((EVIDENCE / 'hosts.json').read_text())['tasks']

    def test_arms_are_the_frozen_descriptors(self):
        for s in ('e1', 'e1b'):
            d = ROOT / 'handoff' / s
            self.assertEqual(self.s['descriptors'][f'{s}:candidate'],
                             json.loads((d / 'candidate_descriptor.json').read_text())['descriptor_id'])
            for name, desc in json.loads((d / 'time_matched_baselines.json').read_text()).items():
                self.assertEqual(self.s['descriptors'][f'{s}:{name}'], desc['descriptor_id'])

    def test_contrasts_and_verdicts_follow_from_the_rows(self):
        import b20r33_strong_baseline_audit as R33
        self.assertEqual(len(self.rows), 60)
        arms = self.s['descriptors']
        for s, st in self.s['studies'].items():
            cand = lambda r: r['arms'][f'{s}:candidate']['value']
            mp = lambda r: r['arms'][f'{s}:mip']['value']
            base = [k for k in arms if k.startswith(f'{s}:') and k != f'{s}:candidate']
            bb = lambda r: max(r['arms'][k]['value'] for k in base)
            self.assertEqual(st['mip_minus_candidate'], R33.contrast(self.rows, lambda r: mp(r) - cand(r)))
            self.assertEqual(st['candidate_minus_best_baseline'], R33.contrast(self.rows, lambda r: cand(r) - bb(r)))
            d = st['mip_minus_candidate']
            want = ('MIP_DOMINATES' if d['mean'] >= 0.5 and d['interval_90'][0] > 0 else
                    'MIP_WORSE' if d['mean'] <= -0.5 and d['interval_90'][1] < 0 else 'NO_MATERIAL_DIFFERENCE')
            self.assertEqual(st['verdict'], want)

    def test_no_arm_exceeds_a_certified_optimum(self):
        for r in self.rows:
            if r['optimum'] is not None:
                self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))
            for s in ('e1', 'e1b'):
                m = r['arms'][f'{s}:mip']
                self.assertEqual(m['overrun'], m['cpu_s'] > 1.25 * {'e1': 0.5, 'e1b': 2.0}[s])

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        ids = {t['task_id'] for t in self.hosts}
        prior = set()
        for d in ('certification_budget_b20r30', 'generated_certification_b20r32'):
            prior |= {t['task_id'] for t in json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())['tasks']}
        self.assertFalse(ids & prior)
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
