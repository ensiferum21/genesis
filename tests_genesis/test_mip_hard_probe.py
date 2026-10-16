"""B20_R34: the MIP-hard probe keeps its contract. The settings and arms are the preregistered
ones, each setting's classification and the verdict follow from the rows, no arm exceeds a
certified optimum, and the hosts are in the exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'mip_hard_probe_b20r34'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.hosts = json.loads((EVIDENCE / 'hosts.json').read_text())

    def test_settings_and_arms_are_preregistered(self):
        import b20r34_mip_hard_probe as R34
        self.assertEqual([(s['family'], s['params']) for s in self.hosts['settings']],
                         [(f, p) for f, p in R34.SETTINGS])
        self.assertEqual(len(self.rows), R34.PER * len(R34.SETTINGS))
        d = ROOT / 'handoff' / 'e1b'
        self.assertEqual(self.s['descriptors']['candidate'],
                         json.loads((d / 'candidate_descriptor.json').read_text())['descriptor_id'])

    def test_classification_and_verdict_follow_from_the_rows(self):
        import b20r34_mip_hard_probe as R34
        base = [k for k in self.s['descriptors'] if k != 'candidate']
        by = {}
        for r in self.rows:
            by.setdefault(r['setting'], []).append(r)
        for s, rs in by.items():
            want = R34.classify(rs, base)
            got = {k: v for k, v in self.s['settings'][s].items() if k != 'params'}
            self.assertEqual(got, want)
        found = sorted(s for s, v in self.s['settings'].items() if v['class'] == 'MIP_HARD_CERTIFIABLE')
        self.assertEqual(self.s['found'], found)
        self.assertEqual(self.s['verdict'],
                         'MIP_HARD_CERTIFIABLE_SETTINGS_FOUND' if found else 'NO_MIP_HARD_CERTIFIABLE_SETTING')

    def test_no_arm_exceeds_a_certified_optimum(self):
        for r in self.rows:
            if r['optimum'] is not None:
                self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))
            if r['edges'] > 200:
                self.assertIsNone(r['optimum'])

    def test_record_repair_matches_the_rows(self):
        repair = json.loads((EVIDENCE / 'record_repair.json').read_text())
        self.assertEqual(repair['rows_checked'], len(self.rows))
        tasks = {t['task_id']: t for t in self.hosts['tasks']}
        for r in self.rows:
            self.assertEqual((tasks[r['task_id']]['n'], len(tasks[r['task_id']]['edges'])), (r['n'], r['edges']))
        regen = json.loads((EVIDENCE / 'hosts_regenerated_on_resume.json').read_text())['tasks']
        self.assertEqual(len(regen), 56)

    def test_hosts_are_in_the_exposure_addenda(self):
        ids = {t['task_id'] for t in self.hosts['tasks']}
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
