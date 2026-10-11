"""B16 / W07: preregistered analysis v2 and power analysis."""
import copy
import unittest

from genesis.kernel import analysis as A
from genesis import power as P


def plan(**over):
    p = {'schema': A.PLAN_SCHEMA, 'primary': 'paired-edge-difference', 'estimand': 'mean-of-stratum-means',
         'strata': 'family', 'minimum_useful_effect': 0.5, 'design_effect': 1.0, 'alpha': 0.05,
         'power_target': 0.8, 'test': 'stratified-sign-flip',
         'interval': {'method': 'stratified-bootstrap-percentile', 'level': 0.9, 'resamples': 2000},
         'multiplicity': {'method': 'holm', 'family_id': 'fam-1', 'family_size': 1},
         'stopping': {'rule': 'single-analysis'}, 'failures': 'score-zero', 'unsupported': 'exclude-and-report',
         'max_unsupported_fraction': 0.1, 'cost': {'measure': 'cpu_ns', 'max_ratio': None},
         'regression': {'max_stratum_loss': None}, 'sensitivity': list(A.SENSITIVITY),
         'decision_rule': 'superiority-with-minimum-useful-effect', 'decision_record_sha256': 'a' * 64}
    p.update(over)
    return p


def rows(diffs_by_stratum, *, cand_fail=(), base_fail=(), unsupported=(), cpu=(1, 1), split=None, headroom=2):
    out = []
    for s, diffs in diffs_by_stratum.items():
        for i, d in enumerate(diffs):
            tid = f'{s}-{i}'
            if tid in unsupported:
                out.append({'task_id': tid, 'stratum': s, 'status': 'UNSUPPORTED'})
                continue
            base = 20
            r = {'task_id': tid, 'stratum': s, 'status': 'SCORED',
                 'candidate': {'value': 0 if tid in cand_fail else base + d,
                               'run': 'FAILED' if tid in cand_fail else 'SUCCESS', 'cpu_ns': cpu[0]},
                 'baseline': {'value': 0 if tid in base_fail else base,
                              'run': 'FAILED' if tid in base_fail else 'SUCCESS', 'cpu_ns': cpu[1]}}
            if split:
                r['split'] = split
                r['optimum'] = r['candidate']['value'] + headroom
            out.append(r)
    return out


STRONG = {'erdos:a': [2, 1, 3, 1, 2, 2], 'erdos:b': [1, 2, 1, 2, 3, 1], 'bip:c': [2, 2, 1, 1, 2, 3]}


class Plan(unittest.TestCase):
    def test_valid_plan(self):
        self.assertEqual(A.check_plan(plan()), [])

    def test_frozen_choices_and_coherence(self):
        for over, frag in (({'test': 't-test'}, 'test'), ({'stopping': {'rule': 'peek-weekly'}}, 'stopping'),
                           ({'failures': 'drop'}, 'failures'), ({'design_effect': 0.5}, 'design_effect'),
                           ({'alpha': 0.2}, 'alpha'), ({'minimum_useful_effect': 0}, 'minimum_useful_effect'),
                           ({'interval': {'method': 'stratified-bootstrap-percentile', 'level': 0.95,
                                          'resamples': 2000}}, '1 - 2*alpha'),
                           ({'multiplicity': {'method': 'none'}}, 'multiplicity'),
                           ({'sensitivity': ['task-sign-test']}, 'sensitivity'),
                           ({'decision_record_sha256': 'x'}, 'decision_record')):
            self.assertTrue(any(frag in p for p in A.check_plan(plan(**over))), (over, A.check_plan(plan(**over))))
        extra = plan(); extra['rescue'] = True
        self.assertTrue(A.check_plan(extra))


class Analyze(unittest.TestCase):
    def test_deterministic_and_strong_effect_supported(self):
        r1, r2 = A.analyze(rows(STRONG), plan()), A.analyze(rows(STRONG), plan())
        self.assertEqual(r1, r2)
        self.assertEqual(r1['decision'], 'SUPPORTED', r1['reasons'])
        self.assertEqual(r1['p_method'], 'exact')
        self.assertAlmostEqual(r1['estimate'], (11 / 6 + 10 / 6 + 11 / 6) / 3)
        self.assertLessEqual(r1['interval'][0], r1['estimate'])
        self.assertEqual(A.decision_from_result(r1, plan()), 'SUPPORTED')

    def test_exact_p_value_known_case(self):
        r = A.analyze(rows({'a': [1, 1, 1], 'b': [1, 1, 1]}), plan())
        self.assertAlmostEqual(r['p_value'], 1 / 64)

    def test_no_effect_or_harm_not_supported(self):
        for data in ({'a': [0, 1, -1, 0, 1, -1], 'b': [1, -1, 0, 0, -1, 1]}, {'a': [-1, -2, -1], 'b': [-2, -1, 0]}):
            r = A.analyze(rows(data), plan())
            self.assertEqual(r['decision'], 'NOT_SUPPORTED')
            self.assertIn('holm_rejects_no_superiority', r['reasons'])

    def test_minimum_useful_effect_is_separate_from_significance(self):
        tiny = {s: [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0] for s in ('a', 'b', 'c')}
        r = A.analyze(rows(tiny), plan(minimum_useful_effect=0.5, design_effect=1.0))
        self.assertTrue(r['checks']['holm_rejects_no_superiority'])
        self.assertFalse(r['checks']['estimate_reaches_minimum_useful_effect'])
        self.assertEqual(r['decision'], 'NOT_SUPPORTED')

    def test_holm_uses_the_registered_family(self):
        data = {'a': [1, 1, 1], 'b': [1, 1, 1]}           # p = 1/64 ~ 0.0156
        self.assertEqual(A.analyze(rows(data), plan())['decision'], 'SUPPORTED')
        big_family = plan(multiplicity={'method': 'holm', 'family_id': 'f', 'family_size': 5})
        r = A.analyze(rows(data), big_family)               # unknown members count as p = 1: alpha / 5
        self.assertFalse(r['checks']['holm_rejects_no_superiority'])
        r = A.analyze(rows(data), plan(multiplicity={'method': 'holm', 'family_id': 'f', 'family_size': 2}),
                      family_p_values=[0.001])
        self.assertTrue(r['checks']['holm_rejects_no_superiority'])   # rank 2 threshold alpha/1

    def test_failures_score_zero_and_stay_visible(self):
        data = rows(STRONG, cand_fail={'erdos:a-0', 'erdos:a-1'})
        r = A.analyze(data, plan())
        self.assertEqual(r['failures'], {'candidate': 2, 'baseline': 0})
        self.assertLess(r['estimate'], A.analyze(rows(STRONG), plan())['estimate'])
        self.assertGreater(r['sensitivity']['failures-excluded'], r['estimate'])

    def test_unsupported_policies(self):
        few = rows(STRONG, unsupported={'erdos:a-5'})
        r = A.analyze(few, plan(max_unsupported_fraction=0.1))
        self.assertEqual(r['unsupported'], ['erdos:a-5'])
        self.assertEqual(r['decision'], 'SUPPORTED')
        many = rows(STRONG, unsupported={'erdos:a-0', 'erdos:a-1', 'erdos:b-0'})
        self.assertEqual(A.analyze(many, plan(max_unsupported_fraction=0.1))['decision'], 'INVALID')
        self.assertEqual(A.analyze(few, plan(unsupported='invalidate-if-any'))['decision'], 'INVALID')

    def test_single_analysis_rule(self):
        self.assertEqual(A.analyze(rows(STRONG), plan(), analysis_count=2)['decision'], 'INVALID')

    def test_cost_and_regression_criteria(self):
        r = A.analyze(rows(STRONG, cpu=(10, 1)), plan(cost={'measure': 'cpu_ns', 'max_ratio': 2.0}))
        self.assertEqual(r['decision'], 'NOT_SUPPORTED')
        self.assertEqual(r['reasons'], ['cost_within_bound'])
        mixed = dict(STRONG, **{'bad:d': [-3, -2, -3, -2, -3, -2]})
        r = A.analyze(rows(mixed), plan(regression={'max_stratum_loss': 1.0}))
        self.assertIn('no_stratum_regression', r['reasons'])

    def test_malformed_rows_invalid(self):
        bad = rows(STRONG)
        bad[0]['candidate']['value'] = -1
        self.assertEqual(A.analyze(bad, plan())['decision'], 'INVALID')
        dup = rows(STRONG) + rows({'erdos:a': [1]})
        self.assertEqual(A.analyze(dup, plan())['decision'], 'INVALID')

    def test_recorded_result_cannot_be_edited_into_support(self):
        r = A.analyze(rows({'a': [0, 1, -1, 0], 'b': [0, 0, 1, -1]}), plan())
        self.assertEqual(A.decision_from_result(r, plan()), 'NOT_SUPPORTED')
        forged = copy.deepcopy(r)
        forged['checks'] = {k: True for k in forged['checks']}
        self.assertEqual(A.decision_from_result(forged, plan()), 'INVALID')
        forged = copy.deepcopy(r); forged['estimate'] = 5.0; forged['interval'] = [1.0, 6.0]
        self.assertEqual(A.decision_from_result(forged, plan()), 'INVALID')
        self.assertEqual(A.decision_from_result(r, plan(minimum_useful_effect=0.25)), 'INVALID')   # other plan

    def test_monte_carlo_path_is_deterministic(self):
        big = {s: [1, 2, 0, 1, -1, 2, 1, 0, 1, 2] for s in ('a', 'b', 'c')}
        r1, r2 = A.analyze(rows(big), plan()), A.analyze(rows(big), plan())
        self.assertEqual(r1['p_method'], 'monte-carlo-20000')
        self.assertEqual(r1, r2)
        self.assertLess(r1['p_value'], 0.01)


class Power(unittest.TestCase):
    def pilot(self, headroom=2):
        return rows({'a': [0, 1, -1, 2, 0, 1, 0, -1], 'b': [1, 0, 0, 2, -1, 1, 1, 0]}, split='DEV',
                    headroom=headroom)

    def test_power_increases_with_sample_and_targets_are_met(self):
        result = P.required_sample(self.pilot(), plan(), sims=300)
        powers = [row['power'] for row in result['table']]
        self.assertGreaterEqual(powers[-1], powers[0])
        self.assertEqual(result['status'], 'CHOSEN')
        self.assertGreaterEqual(result['chosen']['power'], 0.8)
        self.assertGreaterEqual(result['chosen']['tasks_per_stratum'], 10)        # design floor
        self.assertLessEqual(result['power_at_minimum_useful_effect'], 0.7)    # the threshold is not the design effect
        self.assertLessEqual(result['false_positive_rate_at_zero_effect'], 0.06)

    def test_floor_is_a_parameter_and_recorded(self):
        result = P.required_sample(self.pilot(), plan(), sims=200, min_tasks_per_stratum=4)
        self.assertEqual(result['min_tasks_per_stratum'], 4)
        self.assertEqual(result['table'][0]['tasks_per_stratum'], 4)

    def test_no_headroom_makes_the_design_infeasible(self):
        result = P.required_sample(self.pilot(headroom=0), plan(), sims=50)
        self.assertEqual(result['status'], 'INFEASIBLE')
        self.assertIsNone(result['chosen'])

    def test_centred_headroom_for_a_near_ceiling_candidate(self):
        """B19: a candidate already at the optimum but well ahead of the baseline. The B16
        model reads its zero headroom as no room for any effect; the centred model measures
        the headroom of the centred candidate that the simulation actually perturbs."""
        near = rows({'a': [2, 1, 2, 2, 1, 2, 2, 1], 'b': [1, 2, 2, 1, 2, 2, 1, 2]}, split='DEV', headroom=0)
        self.assertEqual(P.required_sample(near, plan(), sims=50)['status'], 'INFEASIBLE')
        centred = P.required_sample(near, plan(), sims=200, headroom='centred')
        self.assertNotEqual(centred['status'], 'INFEASIBLE')
        self.assertEqual(centred['headroom_reference'], 'centred')
        self.assertNotIn('headroom_reference', P.required_sample(self.pilot(), plan(), sims=50))  # B16 output unchanged
        with self.assertRaises(ValueError):
            P.required_sample(near, plan(), sims=10, headroom='other')

    def test_pilot_must_be_dev_material_with_optima(self):
        bad = self.pilot()
        bad[0]['split'] = 'CONFIRM'
        with self.assertRaises(P.NonDevPilot):
            P.required_sample(bad, plan(), sims=50)
        missing = [{k: v for k, v in r.items() if k != 'split'} for r in self.pilot()]
        with self.assertRaises(P.NonDevPilot):
            P.required_sample(missing, plan(), sims=50)
        no_opt = [{k: v for k, v in r.items() if k != 'optimum'} for r in self.pilot()]
        with self.assertRaisesRegex(ValueError, 'certified optimum'):
            P.required_sample(no_opt, plan(), sims=50)

    def test_simulation_agrees_with_the_exact_analysis(self):
        self.assertGreaterEqual(P.approximation_check(self.pilot(), plan(), 12, sims=30), 0.8)


if __name__ == '__main__':
    unittest.main()
