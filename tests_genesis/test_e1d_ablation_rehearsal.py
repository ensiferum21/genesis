"""B20_R45: a same-operator rehearsal of the E1d ablation evaluation through the v5 path.

The design:
  * the ablation's plan uses the hypothesis family the custodian assigns (`ablation:<domain>`);
  * a frozen copy of the ablation's DRAFT decision record has no structural problems;
  * the arms are the frozen candidate and its registered ablation.

The record:
  * the rehearsal ran a v5 request of kind `ablation` with the reference route;
  * the judge agrees;
  * the hosts are fresh and in the addenda."""
import json
from pathlib import Path
import sys
import unittest

from genesis import custody_records as CRec
from genesis import decision_record as DR
from genesis.common import digest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'e1d_ablation_rehearsal_b20r45'
sys.path.insert(0, str(ROOT / 'scripts'))


class Design(unittest.TestCase):
    def test_plan_family_and_decision_record(self):
        import b20r45_e1d_ablation_rehearsal as M
        p = M.ablation_plan()
        self.assertEqual(p['multiplicity']['family_id'], 'ablation:triangle_free_host_v1')
        self.assertEqual(CRec.custodian_family({'evidence_kind': 'ablation', 'domain': M.TF}),
                         p['multiplicity']['family_id'])
        A = M.R44.arms()
        record = json.loads(M.R44.RECORD.read_text())
        power = M.ablation_power()
        self.assertEqual(power['status'], 'CHOSEN')
        d = M.ablation_draft(A['candidate'], A['ablation'], power, record)
        frozen, h = DR.freeze(d)
        self.assertEqual(DR.problems(frozen), [])
        self.assertEqual(DR.problems(frozen, dict(d['analysis_plan_core'], decision_record_sha256=h),
                                     task_count=power['chosen']['total_tasks'], require_frozen=True), [])
        self.assertIn('registered ablation', d['exact_claim'])


class Record(unittest.TestCase):
    """The rehearsal ran an ablation request through v5, and the judge agrees."""
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'rehearsal_summary.json').read_text())

    def test_the_path(self):
        import b20r45_e1d_ablation_rehearsal as M
        p = self.s['receipt_payload']
        self.assertEqual((self.s['request_schema'], self.s['evidence_kind'], p['evidence_kind']),
                         ('genesis-evaluation-request-v5', 'ablation', 'ablation'))
        A = M.R44.arms()
        self.assertEqual(self.s['arms'], {'candidate': A['candidate']['descriptor_id'], 'baseline': A['ablation']['descriptor_id']})
        self.assertEqual(self.s['reference'], M.R43.reference_spec())
        self.assertEqual(p['completed_rows'], p['expected_rows'])
        self.assertTrue(self.s['judge']['agrees'], self.s['judge']['problems'])
        self.assertEqual(self.s['log_problems'], [])
        self.assertEqual(p['outcome'], self.s['judge']['recomputed_outcome'])
        refs = self.s['reference_methods']
        self.assertEqual(sum(refs['methods'].values()) + refs['unsupported'], p['task_count'])

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        mine = [GraphTask.model_validate_json(canonical(t)) for t in self.s['confirm_hosts']]
        self.assertEqual(len(RD.identities(mine)), len(mine))
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r45.json').read_text())
            self.assertTrue(RD.identities(mine) <= RD.identities([GraphTask.model_validate_json(canonical(t)) for t in add]))


if __name__ == '__main__':
    unittest.main()
