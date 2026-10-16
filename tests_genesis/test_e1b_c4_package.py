"""B20_R52: the E1b-C4 DRAFT package and rehearsal. Design: the calibration record is B20_R50's Part A under the
registered DRAFT rule and checks clean, selecting what B20_R50 selected; no study in the repository adopts it; the
arms are B20_R50's candidate and the three DSL baselines under one profile; the reference route is the C4 tree route
over B20_R46's package at 600 s and passes the custodian's checks; the DRAFT decision record, frozen, has no
problems. Record tests are added with the result."""
import json
from pathlib import Path
import sys
import unittest

from genesis import calibration as CAL
from genesis import custodian as CU
from genesis import decision_record as DR
from genesis.common import digest
from genesis.discovery import generated_certify_c4 as GC4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r50_e1b_c4_readiness as R50  # noqa: E402
import b20r52_e1b_c4_package as M  # noqa: E402


class Design(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = M.calibration_record()
        cls.cand, cls.base = M.arms()

    def test_the_calibration_record_is_b20r50s_and_not_adopted(self):
        self.assertEqual(CAL.record_problems(self.record), [])
        self.assertEqual(self.record['rule'], CAL.SELECTION_RULE_E1_HARD_V2_C4TREE_DRAFT)
        r50 = json.loads((M.R50 / 'calibration_record.json').read_text())
        self.assertEqual([(s['family'], s['params']) for s in self.record['selected']],
                         [(s['family'], s['params']) for s in r50['selected']])
        cfg = json.loads((ROOT / CAL.CONFIG).read_text())
        self.assertNotIn(M.STUDY, cfg.get('studies', {}))

    def test_arms_and_reference(self):
        self.assertEqual(self.cand['descriptor_id'], R50.arms()['candidate']['descriptor_id'])
        self.assertEqual(sorted(self.base), sorted(R50.DSL))
        self.assertTrue(all(b['resource_profile'] == self.cand['resource_profile'] for b in self.base.values()))
        ref = M.reference_spec()
        self.assertEqual((ref['route'], ref['seconds'], ref['enumerator']), ('generated-rows-tree-c4-v1', 600, 'fast'))
        self.assertEqual(ref['package_sha256'], digest(json.loads(GC4.PACKAGE.read_text())))
        self.assertEqual(CU.reference_problems(ref), [])

    def test_the_draft_decision_record_freezes_clean(self):
        power = json.loads((M.R50 / 'power_analysis_centred_readiness.json').read_text())
        d = M.draft(self.cand, power, self.record, self.base)
        self.assertEqual(d['status'], 'DRAFT')
        frozen, _ = DR.freeze(d)
        self.assertEqual(DR.problems(frozen), [])
        self.assertIn(self.cand['descriptor_id'][:16], d['exact_claim'])
        self.assertIn('generated-rows-tree-c4-v1', d['exact_claim'])


if __name__ == '__main__':
    unittest.main()
