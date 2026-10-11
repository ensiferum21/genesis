"""B16 / W05: DEV-only difficulty calibration against ceiling effects."""
import copy
import json
from pathlib import Path
import unittest

from genesis import calibration as C
from genesis.common import digest
from genesis.domains import ADAPTERS

ROOT = Path(__file__).resolve().parents[1]


class Guards(unittest.TestCase):
    def test_only_dev_material_is_measured(self):
        a = ADAPTERS['c4_host_v2']
        for split in ('SELECT', 'CONFIRM', 'FUTURE'):
            tasks, _, _ = a.generate(1, 1, split, 'erdos', {'n': 6, 'p': 0.5})
            with self.assertRaises(C.ConfirmationMaterialRefused):
                C.measure(tasks)

    def test_rule_is_frozen_and_selection_follows_from_the_rows(self):
        rec = C.calibrate('c4_host_v2', [('erdos', {'n': 7, 'p': 0.5}), ('erdos', {'n': 10, 'p': 0.45})],
                          tasks_per_setting=2, reference_seconds=10)
        self.assertEqual(C.record_problems(rec), [])
        self.assertEqual(rec['splits_used'], ['DEV'])
        changed_rule = dict(rec, rule=dict(rec['rule'], ceiling_rate_max=1.0))
        self.assertIn('selection rule differs from the frozen SELECTION_RULE', C.record_problems(changed_rule))
        cherry = copy.deepcopy(rec); cherry['selected'] = [{'family': 'erdos', 'params': {'n': 7, 'p': 0.5}, 'index': 0}]
        if cherry['selected'] != rec['selected']:
            self.assertIn('selected settings do not follow from the recorded measurements and rule',
                          C.record_problems(cherry))
        doctored = copy.deepcopy(rec); doctored['settings'][0]['summary']['ceiling_rate'] = 0.35
        self.assertTrue(C.record_problems(doctored))
        smuggled = dict(rec, splits_used=['DEV', 'CONFIRM'])
        self.assertIn('calibration used material other than DEV', C.record_problems(smuggled))

    def test_eligibility_and_order(self):
        good = {'certified_fraction': 1.0, 'ceiling_rate': 0.3, 'mean_headroom': 0.05, 'reference_seconds_median': 1.0}
        self.assertEqual(C.eligible(good), [])
        self.assertEqual(C.eligible(dict(good, ceiling_rate=0.9)), ['ceiling rate outside the band'])
        self.assertEqual(C.eligible(dict(good, certified_fraction=0.5)), ['too few certified optima'])
        settings = [{'index': i, 'family': 'erdos', 'params': {'n': i}, 'ineligible_because': [],
                     'summary': dict(good, ceiling_rate=c)} for i, c in enumerate((0.55, 0.36, 0.2))]
        self.assertEqual([s['index'] for s in C.select(settings)], [1, 2, 0])


class AdoptedCalibration(unittest.TestCase):
    def test_v1_panels_had_no_headroom(self):
        v1 = json.loads((ROOT / 'evidence/dev_calibration_b16/v1_panel_c4_measurement.json').read_text())
        self.assertEqual(v1['summary']['ceiling_rate'], 1.0)
        self.assertEqual(v1['summary']['mean_headroom'], 0.0)

    def test_adopted_c4_calibration_is_valid_and_leaves_headroom(self):
        rec = C.load('c4_host_v2', ROOT)
        self.assertTrue(rec['selected'])
        chosen = {s['index'] for s in rec['selected']}
        for s in rec['settings']:
            if s['index'] in chosen:
                self.assertLessEqual(s['summary']['ceiling_rate'], C.SELECTION_RULE['ceiling_rate_max'])
                self.assertGreater(s['summary']['mean_headroom'], 0)

    def test_calibrated_panels_draw_only_selected_settings(self):
        rec = C.load('c4_host_v2', ROOT)
        tasks, seen = C.calibrated_panel(rec, 777, 7, 'CONFIRM')
        self.assertEqual(len(tasks), 7)
        self.assertEqual(len(seen), 7)
        fams = {t.family.split(':')[0] for t in tasks}
        self.assertTrue(fams <= {s['family'] for s in rec['selected']})
        self.assertTrue(all(t.split == 'CONFIRM' for t in tasks))
        sizes = {t.n for t in tasks}
        self.assertTrue(sizes <= {s['params']['n'] for s in rec['selected']})

    def test_adoption_pins_the_record(self):
        cfg = json.loads((ROOT / C.CONFIG).read_text())
        for domain, entry in cfg['domains'].items():
            rec = json.loads((ROOT / entry['record']).read_text())
            self.assertEqual(digest(rec), entry['sha256'], domain)


if __name__ == '__main__':
    unittest.main()
