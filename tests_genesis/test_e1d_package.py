"""B20_R43: the E1d DRAFT package and its same-operator rehearsal through the v5 path.

Design checks:
  * the calibration record is B20_R41's Part A rows under the registered DRAFT rule;
  * the record passes calibration.record_problems and selects what B20_R41 selected;
  * the arms are E1's frozen candidate and five baselines under E1's profile;
  * the reference route is one the custodian accepts;
  * a frozen copy of the DRAFT decision record has no structural problems;
  * no study in the repository adopts the record."""
import json
from pathlib import Path
import sys
import unittest

from genesis import calibration as CAL
from genesis import decision_record as DR
from genesis.common import digest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'e1d_package_b20r43'
sys.path.insert(0, str(ROOT / 'scripts'))


class Design(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import b20r43_e1d_package as M
        cls.M = M
        cls.record = M.calibration_record()

    def test_record_is_b20r41_part_a_under_the_draft_rule(self):
        r41 = json.loads((ROOT / 'evidence' / 'e1d_readiness_b20r41' / 'calibration_record.json').read_text())
        self.assertEqual(CAL.record_problems(self.record), [])
        self.assertEqual(self.record['rule'], CAL.SELECTION_RULE_E1_HARD_V3_DRAFT)
        self.assertEqual(self.record['selected'], r41['selected'])
        self.assertEqual([r['task_sha256'] for s in self.record['settings'] for r in s['rows']], r41['task_sha256s'])
        for s, t in zip(self.record['settings'], r41['settings']):
            self.assertEqual((s['summary'], s['ineligible_because']), (t['summary'], t['ineligible_because']))

    def test_no_study_in_the_repository_adopts_it(self):
        cfg = json.loads((ROOT / CAL.CONFIG).read_text())
        self.assertNotIn(self.M.STUDY, cfg.get('studies', {}))
        with self.assertRaises(ValueError):
            CAL.load(self.M.TF, ROOT, study=self.M.STUDY)

    def test_arms_and_reference(self):
        from genesis import custodian as CU
        cand, base = self.M.arms()
        frozen = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
        self.assertEqual(cand, frozen)
        self.assertEqual(set(base), {'exchange_tm', 'low_cycle_tm', 'multistart_tm', 'milp_highs_tm', 'milp_highs_4x'})
        self.assertEqual({canonical_profile(b) for b in base.values()}, {canonical_profile(cand)})
        self.assertEqual([base[n]['parameters']['cpu_seconds'] for n in ('milp_highs_tm', 'milp_highs_4x')], [0.5, 2.0])
        self.assertEqual(CU.reference_problems(self.M.reference_spec()), [])

    def test_draft_decision_record_has_no_structural_problems(self):
        cand, base = self.M.arms()
        power = json.loads((ROOT / 'evidence' / 'e1d_readiness_b20r41' / 'power_analysis_centred.json').read_text())
        d = self.M.draft(cand, power, self.record, base)
        frozen, _ = DR.freeze(d)
        self.assertEqual(DR.problems(frozen), [])
        self.assertIn('generated-rows-v1', d['exact_claim'])
        self.assertIn('about 20 s', d['baselines']['not_a_competitor'])


def canonical_profile(desc):
    return json.dumps(desc['resource_profile'], sort_keys=True)


if __name__ == '__main__':
    unittest.main()
