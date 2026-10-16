"""B20_R52: the E1b-C4 DRAFT package and rehearsal. Design: the calibration record is B20_R50's Part A under the
registered DRAFT rule and checks clean, selecting what B20_R50 selected; no study in the repository adopts it; the
arms are B20_R50's candidate and the three DSL baselines under one profile; the reference route is the C4 tree route
over B20_R46's package at 600 s and passes the custodian's checks; the DRAFT decision record, frozen, has no
problems. Record: the record on disk is the derived one, the rehearsal went through the v5 C4 tree route, the
package files match the index, and the rehearsal hosts are in the package exposure and the addenda."""
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

EVIDENCE = ROOT / 'evidence' / 'e1b_c4_package_b20r52'


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


class Record(unittest.TestCase):
    """The run's evidence and the package."""
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'rehearsal_summary.json').read_text())
        cls.index = json.loads((ROOT / 'handoff' / 'e1b_c4' / 'package_index.json').read_text())

    def test_the_record_on_disk_is_the_derived_record(self):
        on_disk = json.loads((EVIDENCE / M.RECORD_NAME).read_text())
        self.assertEqual(on_disk, M.calibration_record())
        self.assertEqual(digest(on_disk), self.s['adoption_in_the_copy']['record_sha256'])
        self.assertEqual(self.index['calibration']['sha256'], digest(on_disk))
        self.assertFalse(self.index['calibration']['adopted'])

    def test_the_rehearsal_went_through_the_v5_c4_tree_route(self):
        p = self.s['receipt_payload']
        self.assertEqual(self.s['request_schema'], 'genesis-evaluation-request-v5')
        self.assertEqual(self.s['reference'], M.reference_spec())
        self.assertIn(self.s['comparator_selection']['selected'], self.s['comparator_selection']['baselines'])
        self.assertEqual(self.s['comparator_selection']['calibration']['rule'], 'e1-hard-v2-c4tree-draft')
        self.assertEqual(p['completed_rows'], p['expected_rows'])
        self.assertTrue(self.s['judge']['agrees'], self.s['judge']['problems'])
        self.assertEqual(self.s['log_problems'], [])
        refs = self.s['reference_methods']
        self.assertEqual(sum(refs['methods'].values()) + refs['unsupported'], p['task_count'])
        self.assertTrue(all(m.startswith('GENERATED_ROWS_LP_DUAL_') and 'C4' in m for m in refs['methods']))
        self.assertIn('REHEARSAL', self.s['label'])
        self.assertEqual(self.index['rehearsal']['outcome'], p['outcome'])

    def test_package_files_match_the_index(self):
        d = ROOT / 'handoff' / 'e1b_c4'
        self.assertEqual(json.loads((d / 'candidate_descriptor.json').read_text())['descriptor_id'],
                         self.index['candidate_descriptor_id'])
        base = json.loads((d / 'baselines.json').read_text())
        self.assertEqual({n: b['descriptor_id'] for n, b in base.items()}, self.index['baselines'])
        draft = json.loads((d / 'decision_record_DRAFT.json').read_text())
        self.assertEqual(digest(draft), self.index['decision_record_draft_sha256'])
        frozen, _ = DR.freeze(draft)
        self.assertEqual(DR.problems(frozen), [])
        self.assertEqual(json.loads((d / 'reference_route.json').read_text()), M.reference_spec())
        hosts = 0
        for name in self.index['exposure_hosts_all']['files']:
            part = json.loads((d / name).read_text())
            self.assertLessEqual(len(part), M.CHUNK)
            hosts += len(part)
        self.assertEqual(hosts, self.index['exposure_hosts_all']['hosts'])

    def test_rehearsal_hosts_are_in_the_package_exposure_and_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        d = ROOT / 'handoff' / 'e1b_c4'
        listed = set()
        for name in self.index['exposure_hosts_all']['files']:
            listed |= RD.identities([GraphTask.model_validate_json(canonical(t)) for t in json.loads((d / name).read_text())])
        mine = [GraphTask.model_validate_json(canonical(t)) for t in self.s['select_hosts'] + self.s['confirm_hosts']]
        dev = json.loads((EVIDENCE / 'development_look_hosts.json').read_text())
        mine += [GraphTask.model_validate_json(canonical(t)) for t in dev['select_hosts'] + dev['confirm_hosts']]
        self.assertEqual(len(mine), 59)
        self.assertTrue(RD.identities(mine) <= listed)
        for pkg in ('e1', 'e1b'):
            addenda = set()
            for p in sorted((ROOT / 'handoff' / pkg).glob('exposure_hosts_addendum_*.json')):
                addenda |= RD.identities([GraphTask.model_validate_json(canonical(t)) for t in json.loads(p.read_text())])
            self.assertTrue(RD.identities(mine) <= addenda, pkg)


if __name__ == '__main__':
    unittest.main()
