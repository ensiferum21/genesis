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


class Record(unittest.TestCase):
    """The run's evidence and the package."""
    @classmethod
    def setUpClass(cls):
        import b20r43_e1d_package as M
        cls.M = M
        cls.s = json.loads((EVIDENCE / 'rehearsal_summary.json').read_text())
        cls.index = json.loads((ROOT / 'handoff' / 'e1d' / 'package_index.json').read_text())

    def test_the_record_on_disk_is_the_derived_record(self):
        on_disk = json.loads((EVIDENCE / self.M.RECORD_NAME).read_text())
        self.assertEqual(on_disk, self.M.calibration_record())
        self.assertEqual(digest(on_disk), self.s['adoption_in_the_copy']['record_sha256'])
        self.assertEqual(self.index['calibration']['sha256'], digest(on_disk))
        self.assertFalse(self.index['calibration']['adopted'])

    def test_the_rehearsal_went_through_the_v5_path(self):
        p = self.s['receipt_payload']
        self.assertEqual(self.s['request_schema'], 'genesis-evaluation-request-v5')
        self.assertEqual(self.s['reference'], self.M.reference_spec())
        self.assertIn(self.s['comparator_selection']['selected'], self.s['comparator_selection']['baselines'])
        self.assertEqual(self.s['comparator_selection']['calibration']['rule'], 'e1-hard-v3-draft')
        self.assertEqual(p['completed_rows'], p['expected_rows'])
        self.assertTrue(self.s['judge']['agrees'], self.s['judge']['problems'])
        self.assertEqual(self.s['log_problems'], [])
        refs = self.s['reference_methods']
        self.assertEqual(sum(refs['methods'].values()) + refs['unsupported'], p['task_count'])
        self.assertTrue(all(m.startswith('GENERATED_ROWS_') for m in refs['methods']))
        self.assertIn('REHEARSAL', self.s['label'])
        self.assertEqual(self.index['rehearsal']['outcome'], p['outcome'])

    def test_package_files_match_the_index(self):
        d = ROOT / 'handoff' / 'e1d'
        self.assertEqual(json.loads((d / 'candidate_descriptor.json').read_text())['descriptor_id'],
                         self.index['candidate_descriptor_id'])
        base = json.loads((d / 'baselines.json').read_text())
        self.assertEqual({n: b['descriptor_id'] for n, b in base.items()}, self.index['baselines'])
        draft = json.loads((d / 'decision_record_DRAFT.json').read_text())
        self.assertEqual(digest(draft), self.index['decision_record_draft_sha256'])
        frozen, _ = DR.freeze(draft)
        self.assertEqual(DR.problems(frozen), [])
        hosts = 0
        for name in self.index['exposure_hosts_all']['files']:
            part = json.loads((d / name).read_text())
            self.assertLessEqual(len(part), self.M.CHUNK)
            hosts += len(part)
        self.assertEqual(hosts, self.index['exposure_hosts_all']['hosts'])

    def test_rehearsal_hosts_are_in_the_package_exposure_and_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        d = ROOT / 'handoff' / 'e1d'
        listed = set()
        for name in self.index['exposure_hosts_all']['files']:
            listed |= RD.identities([GraphTask.model_validate_json(canonical(t)) for t in json.loads((d / name).read_text())])
        mine = [GraphTask.model_validate_json(canonical(t)) for t in self.s['select_hosts'] + self.s['confirm_hosts']]
        dev = json.loads((EVIDENCE / 'development_look_hosts.json').read_text())['tasks']
        mine += [GraphTask.model_validate_json(canonical(t)) for t in dev]
        self.assertTrue(RD.identities(mine) <= listed)
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r43.json').read_text())
            got = RD.identities([GraphTask.model_validate_json(canonical(t)) for t in add])
            self.assertTrue(RD.identities(mine) <= got)


def canonical_profile(desc):
    return json.dumps(desc['resource_profile'], sort_keys=True)


if __name__ == '__main__':
    unittest.main()
