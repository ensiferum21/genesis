"""B20_R35: the dense certification study keeps its contract. The settings are the preregistered
ones, the summary and verdict follow from the rows, every kept certificate re-checks VALID at the
certified value, and the hosts are fresh and in the exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

from genesis.common import canonical
from genesis.discovery import generated_certify as GC
from genesis.models import GraphTask
from genesis.verification import lp_dual_rows as V

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'dense_certification_b20r35'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.h = json.loads((EVIDENCE / 'hosts.json').read_text())
        cls.tasks = {t['task_id']: GraphTask.model_validate_json(canonical(t)) for t in cls.h['tasks']}

    def test_settings_and_hosts(self):
        import b20r35_dense_certification as R35
        self.assertEqual([(s['family'], s['params']) for s in self.h['settings']], list(R35.SETTINGS))
        self.assertEqual(len(self.rows), R35.PER * len(R35.SETTINGS))
        self.assertEqual({r['task_id'] for r in self.rows}, set(self.tasks))
        for r in self.rows:
            self.assertEqual(len(self.tasks[r['task_id']].edges), r['edges'])

    def test_summary_and_verdict_follow_from_the_rows(self):
        import b20r32_generated_certification as R32
        import b20r35_dense_certification as R35
        self.assertEqual(self.s['pooled'], R35.tally(self.rows))
        p = self.s['pooled']
        self.assertAlmostEqual(self.s['mcnemar_p_one_sided'],
                               round(R32.mcnemar_one_sided(p['certified_b_not_a'], p['certified_a_not_b']), 8))
        passes = self.s['passes']
        self.assertEqual(passes['coverage'], p['certified_b'] >= p['certified_a'])
        self.assertEqual(passes['mcnemar'], self.s['mcnemar_p_one_sided'] < 0.05)
        self.assertEqual(passes['time'], self.s['wall_saving_a_minus_b']['interval_90'][0] > 0)
        want = ('DEFECT_FOUND' if not passes['sound'] else
                'CERTIFICATION_UTILITY' if all(passes.values()) else 'NO_CERTIFICATION_UTILITY')
        self.assertEqual(self.s['verdict'], want)
        for r in self.rows:
            if r['a']['lower'] == r['a']['upper'] and r['b']['lower'] == r['b']['upper']:
                self.assertEqual(r['a']['upper'], r['b']['upper'])

    def test_kept_certificates_recheck(self):
        reg = GC.load_registry()
        kept = sorted((EVIDENCE / 'certificates').glob('*.json'))
        want = {r['task_id'] for r in self.rows if r['b']['lower'] == r['b']['upper'] and
                r['a']['lower'] != r['a']['upper'] and r['b']['certificate_sha256']}
        self.assertEqual({p.stem for p in kept}, want)
        by_id = {r['task_id']: r for r in self.rows}
        for path in kept:
            v = V.check_certificate(self.tasks[path.stem], json.loads(path.read_text()), reg)
            self.assertEqual(v['verdict'], 'VALID')
            self.assertEqual(v['bound'], by_id[path.stem]['b']['upper'])

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        r34 = json.loads((ROOT / 'evidence' / 'mip_hard_probe_b20r34' / 'hosts.json').read_text())['tasks']
        self.assertFalse(set(self.tasks) & {t['task_id'] for t in r34})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(set(self.tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
