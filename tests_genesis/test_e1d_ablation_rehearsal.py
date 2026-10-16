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


if __name__ == '__main__':
    unittest.main()
