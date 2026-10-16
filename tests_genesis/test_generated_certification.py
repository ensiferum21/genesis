"""B20_R32: the generated-row certification study keeps its contract. The summary and the verdict
follow from the rows by the preregistered rule. Every kept certificate re-checks VALID against
the registry, at the value the evaluator's route certified. The hosts are fresh and in the
handoff exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

from genesis.common import canonical
from genesis.discovery import generated_certify as GC
from genesis.models import GraphTask
from genesis.verification import lp_dual_rows as V

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'generated_certification_b20r32'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.tasks = {t['task_id']: GraphTask.model_validate_json(canonical(t))
                     for t in json.loads((EVIDENCE / 'hosts.json').read_text())['tasks']}

    def test_every_host_measured_once(self):
        self.assertEqual(len(self.rows), 90)
        self.assertEqual({r['task_id'] for r in self.rows}, set(self.tasks))

    def test_summary_and_verdict_follow_from_the_rows(self):
        import b20r32_generated_certification as R32
        self.assertEqual(self.s['pooled'], R32.tally(self.rows))
        p = self.s['pooled']
        self.assertAlmostEqual(self.s['mcnemar_p_one_sided'],
                               round(R32.mcnemar_one_sided(p['lp_upper_b_not_a'], p['lp_upper_a_not_b']), 6))
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
        self.assertEqual(self.s['registry']['package_sha256'], reg['package_sha256'])
        kept = sorted((EVIDENCE / 'certificates').glob('*.json'))
        want = {r['task_id'] for r in self.rows if r['b']['lower'] == r['b']['upper'] and
                r['b']['method'] == 'LP_DUAL_GENERATED_EXACT' and r['a']['method'] != 'LP_DUAL_EXACT'}
        self.assertEqual({p.stem for p in kept}, want)
        by_id = {r['task_id']: r for r in self.rows}
        for path in kept:
            r = by_id[path.stem]
            v = V.check_certificate(self.tasks[path.stem], json.loads(path.read_text()), reg)
            self.assertEqual(v['verdict'], 'VALID')
            self.assertEqual(v['bound'], r['b']['upper'])
            self.assertEqual(r['a']['upper'], r['b']['upper'])
            self.assertNotEqual(r['a']['method'], 'LP_DUAL_EXACT')

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        prior = set()
        for d in ('certification_budget_b20r30', 'relaxation_invention_b20r31'):
            h = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())
            prior |= {t['task_id'] for t in (h['tasks'] if 'tasks' in h else [t for v in h.values() for t in v])}
        self.assertFalse(prior & set(self.tasks))
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(set(self.tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
