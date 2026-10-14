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
        renamed = under(rec, dict(CAL.SELECTION_RULE_E1_HARD, name='e1-hard-v9'))
        self.assertIn("selection rule 'e1-hard-v9' is not a registered rule", CAL.record_problems(renamed))
        posing = under(rec, dict(CAL.SELECTION_RULE_E1_HARD, name='e1-hard-v2'))     # v1's limits under v2's name
        self.assertIn("selection rule differs from the frozen, registered rule 'e1-hard-v2'", CAL.record_problems(posing))
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



def _row(opt, best, certified=True, seconds=1.0):
    ref = ({'status': 'FINITE_CERTIFIED', 'value': opt, 'method': 'LP_DUAL_EXACT'} if certified else
           {'status': 'UNSUPPORTED', 'reason': 'optimum not certified within 60s'})
    return {'task_sha256': digest([opt, best, certified, seconds]), 'edges': 2 * opt, 'reference': ref,
            'reference_seconds': seconds, 'baselines': {'exchange_tm': best - 1, 'low_cycle_tm': best, 'multistart_tm': None},
            'baseline_cpu_ns': {}}


def v2_record(settings_rows):
    rule = CAL.SELECTION_RULE_E1_HARD_V2
    settings = []
    for i, rows in enumerate(settings_rows):
        summary = CAL.summarize(rows, rule)
        settings.append({'index': i, 'family': 'erdos', 'params': {'n': 30 + i, 'p': 0.3}, 'generator': {},
                         'summary': summary, 'ineligible_because': CAL.eligible(summary, rule), 'rows': rows})
    return {'schema': CAL.SCHEMA, 'domain': 'triangle_free_host_v1', 'splits_used': ['DEV'], 'rule': rule,
            'settings': settings, 'selected': CAL.select(settings, rule)}


class RuleV2(unittest.TestCase):
    """B20_R24 (the user's decision of 14 Oct 2026): e1-hard-v2, for E1 and E1b; it never reads a candidate."""

    def test_v2_keeps_v1_limits_and_adds_a_headroom_bound_and_a_certification_limit(self):
        v1, v2 = CAL.SELECTION_RULE_E1_HARD, CAL.SELECTION_RULE_E1_HARD_V2
        for k in ('certified_fraction_min', 'ceiling_rate_min', 'ceiling_rate_max', 'ceiling_rate_target',
                  'mean_headroom_min', 'reference_seconds_median_max', 'select_at_most', 'order'):
            self.assertEqual(v2[k], v1[k], k)                                 # nothing relaxed
        plan = json.loads((ROOT / 'evidence/readiness_b19/e1/decision_record_DRAFT.json').read_text())['analysis_plan_core']
        self.assertEqual(v2['mean_gap_edges_min'], plan['design_effect'])     # the effect a powered study must carry
        m = v2['measurement']
        self.assertEqual((m['baselines'], m['reference'], m['isolation'], m['search_cpu_seconds'], m['reference_seconds']),
                         ('dsl-time-matched-v1', 'obstruction.certify', 'runc', 2.0, 60))
        self.assertFalse(any('candidate' in k for k in (*v2, *m)))
        self.assertIs(CAL.RULES_BY_NAME['e1-hard-v2'], v2)

    def test_v2_selection_follows_from_rows_and_older_summaries_are_unchanged(self):
        good = [_row(40, 38), _row(35, 34), _row(30, 29), _row(25, 25)]          # gap 1.0, ceiling 0.25
        shallow = [_row(40, 39), _row(35, 34), _row(30, 29), _row(25, 25)]       # gap 0.75, all else as good
        uncertified = [_row(40, 37), _row(35, 32), _row(30, 27, certified=False), _row(25, 22)]
        rec = v2_record([good, shallow, uncertified])
        self.assertEqual(CAL.record_problems(rec), [])
        self.assertEqual([s['index'] for s in rec['selected']], [0])
        self.assertEqual(rec['settings'][0]['summary']['mean_gap_edges'], 1.0)
        self.assertEqual(rec['settings'][1]['ineligible_because'], ['too little headroom in edges for the design effect'])
        self.assertIn('too few certified optima', rec['settings'][2]['ineligible_because'])
        self.assertNotIn('mean_gap_edges', CAL.summarize(good))                    # v1 and domain records unchanged
        self.assertNotIn('mean_gap_edges', CAL.summarize(good, CAL.SELECTION_RULE_E1_HARD))
        bad = copy.deepcopy(rec)
        bad['settings'][1]['summary']['mean_gap_edges'] = 1.5
        self.assertTrue(CAL.record_problems(bad))
        bad = copy.deepcopy(rec)
        bad['settings'][1]['rows'][0]['reference']['value'] += 1
        self.assertTrue(CAL.record_problems(bad))
        self.assertEqual(CAL.record_problems(CAL.load('triangle_free_host_v1', ROOT, study='e1')), [])

    def test_time_matched_measurement_runs_the_baselines_and_certifies(self):
        from genesis.domains import ADAPTERS
        tasks, _, _ = ADAPTERS['triangle_free_host_v1'].generate(77, 2, 'DEV', 'erdos', {'n': 12, 'p': 0.4})
        m = dict(CAL.SELECTION_RULE_E1_HARD_V2['measurement'], search_cpu_seconds=0.2, isolation='process',
                 reference_seconds=20)
        rows = CAL.measure_time_matched(tasks, m, seed=3)
        for r in rows:
            self.assertEqual(sorted(r['baselines']), ['exchange_tm', 'low_cycle_tm', 'multistart_tm'])
            self.assertEqual(r['reference']['status'], 'FINITE_CERTIFIED', r)
            self.assertGreaterEqual(r['reference']['value'], max(r['baselines'].values()))
            self.assertTrue(all(c and c >= int(0.2e9) for c in r['baseline_cpu_ns'].values()))
        confirm, _, _ = ADAPTERS['triangle_free_host_v1'].generate(78, 1, 'CONFIRM', 'erdos', {'n': 12, 'p': 0.4})
        with self.assertRaises(CAL.ConfirmationMaterialRefused):
            CAL.measure_time_matched(confirm, m)
        with self.assertRaisesRegex(ValueError, 'unknown calibration measurement'):
            CAL.measure_time_matched(tasks, dict(m, reference='adapter'))


if __name__ == '__main__':
    unittest.main()
