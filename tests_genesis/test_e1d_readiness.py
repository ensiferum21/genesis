"""B20_R41: E1d readiness under the DRAFT rule e1-hard-v3-draft (DEV).

The design is as preregistered:
  * the rule changes only what its docstring says, and it is not adopted;
  * the arms are E1's frozen descriptors plus two registry-v2 MIP descriptors;
  * the comparator is chosen from an explicit set that includes the MIP at four times the budget.

The route's LP rounding:
  * is off by default, so earlier results are unchanged;
  * uses only the host and the route's own LP;
  * keeps only a checked witness."""
import itertools
import json
from pathlib import Path
import sys
import unittest

from genesis import calibration as CAL
from genesis.discovery import generated_certify as GC
from genesis.graphs import check_witness
from genesis.models import GraphTask

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'e1d_readiness_b20r41'
sys.path.insert(0, str(ROOT / 'scripts'))


def host(n, edges, tid='t-r41'):
    return GraphTask(task_id=tid, domain='triangle_free_host_v1', family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


K6 = host(6, itertools.combinations(range(6), 2))


class Design(unittest.TestCase):
    def test_rule_is_a_draft_with_only_the_stated_changes(self):
        import b20r41_e1d_readiness as M
        v2 = CAL.SELECTION_RULE_E1_HARD_V2
        changed = {k for k in set(v2) | set(M.RULE) if v2.get(k) != M.RULE.get(k)}
        self.assertEqual(changed, {'name', 'reference_seconds_median_max', 'measurement', 'status'})
        self.assertEqual((M.RULE['name'], M.RULE['reference_seconds_median_max']), ('e1-hard-v3-draft', 30.0))
        self.assertNotIn('e1-hard-v3-draft', CAL.RULES_BY_NAME)

    def test_arms_are_frozen_e1_plus_two_mip_budgets(self):
        import b20r41_e1d_readiness as M
        arms = M.arms()
        self.assertEqual(set(arms), {'candidate', *M.BASELINES})
        frozen = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
        self.assertEqual(arms['candidate'][1]['descriptor_id'], frozen['descriptor_id'])
        self.assertEqual([arms[n][1]['parameters']['cpu_seconds'] for n in ('milp_highs_tm', 'milp_highs_4x')], [0.5, 2.0])
        self.assertEqual({arms[n][0] for n in ('milp_highs_tm', 'milp_highs_4x')}, {'v2'})

    def test_comparator_is_the_strongest_of_the_explicit_set(self):
        import b20r41_e1d_readiness as M
        names = ['candidate', *M.BASELINES]
        rows = []
        for i in range(4):
            vals = {'candidate': 12 - i % 2, 'exchange_tm': 8, 'low_cycle_tm': 7, 'multistart_tm': 8,
                    'milp_highs_tm': 2, 'milp_highs_4x': 9 + i % 3}
            rows.append({'task_id': f't{i}', 'stratum': 's', 'split': 'DEV', 'optimum': 12,
                         'arms': {n: {'value': v, 'run': 'SUCCESS', 'cpu_ns': 10 ** 9 * (4 if n == 'milp_highs_4x' else 1)}
                                  for n, v in vals.items()}})
        out, _ = M.analyse(rows, names, list(M.BASELINES))
        self.assertEqual(out['comparator'], 'milp_highs_4x')
        self.assertEqual(out['cpu_ratio_candidate_to_comparator'], 0.25)
        self.assertEqual(out['optimum_hits']['candidate'], 2)
        self.assertEqual(out['candidate_minus_each_baseline']['milp_highs_4x']['wins_ties_losses'], [4, 0, 0])
        rows[0]['optimum'] = None
        rows[1]['optimum'] = None
        self.assertEqual(M.analyse(rows, names, list(M.BASELINES))[0]['verdict'], 'UNSETTLED_REFERENCE')


class Rounding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = GC.load_registry()

    def test_off_by_default(self):
        rec = GC.certify_with_rows(K6, [], self.reg, seconds=5, sat_fallback=False)
        self.assertNotIn('lp-rounding', [s['step'] for s in rec['steps']])
        self.assertEqual(rec['lower'], 0)
        self.assertEqual(len(GC.lp_dual_rows(K6, self.reg)), 3)

    def test_rounding_keeps_only_a_checked_larger_witness(self):
        rec = GC.certify_with_rows(K6, [], self.reg, seconds=5, sat_fallback=False, lp_rounding_seconds=0.2)
        step = next(s for s in rec['steps'] if s['step'] == 'lp-rounding')
        self.assertGreater(step['value'], 0)
        self.assertEqual(rec['lower'], step['value'])
        self.assertEqual(check_witness(K6, [tuple(e) for e in rec['witness']])['value'], rec['lower'])
        self.assertEqual(rec['upper'], 9)                                    # the K5 rows give Turán's bound
        better = GC.certify_with_rows(K6, [(0, 3), (0, 4), (0, 5), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5)],
                                      self.reg, seconds=5, sat_fallback=False, lp_rounding_seconds=0.2)
        self.assertEqual((better['lower'], better['upper']), (9, 9))       # a better seed is never replaced

    def test_edge_values_are_the_lp_primal(self):
        _, value, _, x = GC.lp_dual_rows_x(K6, self.reg)
        self.assertEqual(len(x), len(K6.edges))
        self.assertAlmostEqual(sum(x), value, places=6)                      # strong duality
        self.assertTrue(all(-1e-9 <= v <= 1 + 1e-9 for v in x))


if __name__ == '__main__':
    unittest.main()
