"""B20_R12: the separately versioned E1 calibration rule and study adoption (the user's decision of 13 Oct 2026).

The domain rule (SELECTION_RULE) and the domain adoption are unchanged; a study adopts a record made
under a registered rule; neither rule looks at a candidate.
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from genesis import calibration as CAL
from genesis.common import digest

ROOT = Path(__file__).resolve().parents[1]


def round2():
    cfg = json.loads((ROOT / CAL.CONFIG).read_text())['domains']['triangle_free_host_v1']
    return json.loads((ROOT / cfg['record']).read_text())


def under(record, rule):
    """The same measurements re-selected under ``rule`` (as a calibration run with that rule would record)."""
    r = copy.deepcopy(record)
    r['rule'] = rule
    for s in r['settings']:
        s['ineligible_because'] = CAL.eligible(s['summary'], rule)
    r['selected'] = CAL.select(r['settings'], rule)
    return r


class Rules(unittest.TestCase):
    def test_domain_rule_and_adoption_unchanged(self):
        self.assertEqual(CAL.SELECTION_RULE['ceiling_rate_min'], 0.1)
        self.assertNotIn('name', CAL.SELECTION_RULE)                    # existing records keep validating
        rec = CAL.load('triangle_free_host_v1', ROOT)
        self.assertEqual(rec['selected'], [{'family': 'erdos', 'index': 2, 'params': {'n': 22, 'p': 0.35}}])

    def test_e1_rule_is_candidate_independent_and_harder(self):
        r = CAL.SELECTION_RULE_E1_HARD
        self.assertLessEqual(r['ceiling_rate_max'], 0.25)
        for k in ('certified_fraction_min', 'mean_headroom_min', 'reference_seconds_median_max', 'select_at_most'):
            self.assertEqual(r[k], CAL.SELECTION_RULE[k])              # nothing else relaxed
        self.assertFalse(any('candidate' in k for k in r))

    def test_registered_rules_validate_and_tampering_does_not(self):
        rec = round2()
        self.assertEqual(CAL.record_problems(rec), [])
        e1 = under(rec, CAL.SELECTION_RULE_E1_HARD)
        self.assertEqual(CAL.record_problems(e1), [])
        # On the round-2 measurements the E1 rule would pick the settings the fixed baselines never solve,
        # fastest evaluator first; the evaluator-speed limit still excludes n22 p0.5.
        self.assertEqual([s['index'] for s in e1['selected']], [5, 1, 2])
        loose = under(rec, dict(CAL.SELECTION_RULE_E1_HARD, ceiling_rate_max=0.3))
        self.assertIn("selection rule differs from the frozen, registered rule 'e1-hard-v1'", CAL.record_problems(loose))
        renamed = under(rec, dict(CAL.SELECTION_RULE_E1_HARD, name='e1-hard-v2'))
        self.assertIn("selection rule 'e1-hard-v2' is not a registered rule", CAL.record_problems(renamed))
        unnamed = under(rec, {k: v for k, v in CAL.SELECTION_RULE_E1_HARD.items() if k != 'name'})
        self.assertIn('selection rule differs from the frozen SELECTION_RULE', CAL.record_problems(unnamed))
        wrong = copy.deepcopy(e1)
        wrong['selected'] = rec['selected']
        self.assertTrue(CAL.record_problems(wrong))

    def test_study_adoption(self):
        rec = under(round2(), CAL.SELECTION_RULE_E1_HARD)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'configs').mkdir()
            shutil.copytree(ROOT / 'evidence' / 'dev_calibration_b16', d / 'evidence' / 'dev_calibration_b16')
            (d / 'e1.json').write_text(json.dumps(rec))
            cfg = json.loads((ROOT / CAL.CONFIG).read_text())
            cfg['studies'] = {'e1': {'triangle_free_host_v1': {'record': 'e1.json', 'sha256': digest(rec),
                                                               'rule': 'e1-hard-v1'}}}
            (d / CAL.CONFIG).write_text(json.dumps(cfg))
            self.assertEqual(CAL.load('triangle_free_host_v1', d, study='e1')['selected'], rec['selected'])
            self.assertEqual(CAL.load('triangle_free_host_v1', d)['selected'], round2()['selected'])   # domain unchanged
            cfg['studies']['e1']['triangle_free_host_v1']['rule'] = 'genesis-default'
            (d / CAL.CONFIG).write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError, 'does not use the rule'):
                CAL.load('triangle_free_host_v1', d, study='e1')
            with self.assertRaisesRegex(ValueError, 'no adopted calibration'):
                CAL.load('c4_host_v2', d, study='e1')


if __name__ == '__main__':
    unittest.main()
