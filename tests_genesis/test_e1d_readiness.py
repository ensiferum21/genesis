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


class Record(unittest.TestCase):
    """The run's evidence: the selection and the verdict follow from the rows by the preregistered rule."""
    @classmethod
    def setUpClass(cls):
        import b20r41_e1d_readiness as M
        cls.M = M
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.cal = json.loads((EVIDENCE / 'calibration_record.json').read_text())
        cls.crows = [json.loads(l) for l in (EVIDENCE / 'calibration_rows.jsonl').read_text().splitlines() if l.strip()]
        cls.prows = [json.loads(l) for l in (EVIDENCE / 'pilot_rows.jsonl').read_text().splitlines() if l.strip()]

    def test_calibration_hosts_match_rows_and_selection_follows_the_rule(self):
        from genesis.common import canonical, digest
        hosts = json.loads((EVIDENCE / 'calibration_hosts.json').read_text())
        tasks = [GraphTask.model_validate_json(canonical(t)) for s in hosts['settings'] for t in s['tasks']]
        self.assertEqual([digest(t.model_dump(mode='json')) for t in tasks], self.cal['task_sha256s'])
        self.assertEqual(len(self.crows), 64)
        settings = []
        for s in self.cal['settings']:
            summary = CAL.summarize([r for r in self.crows if r['setting'] == s['index']], self.M.RULE)
            self.assertEqual(summary, s['summary'])
            self.assertEqual(CAL.eligible(summary, self.M.RULE), s['ineligible_because'])
            settings.append(dict(s, summary=summary))
        self.assertEqual(CAL.select(settings, self.M.RULE), self.cal['selected'])
        self.assertEqual([s['index'] for s in self.cal['selected']], [1, 2, 3])

    def test_calibration_was_candidate_blind(self):
        for r in self.crows:
            self.assertEqual(set(r['baselines']), set(self.M.BASELINES))
            self.assertNotEqual(r['ref']['seeded_from'], 'candidate')

    def test_pilot_verdict_follows_from_the_rows(self):
        self.assertEqual(len(self.prows), 30)
        analysis, _ = self.M.analyse(self.prows, ['candidate', *self.M.BASELINES], list(self.M.BASELINES))
        stored = json.loads((EVIDENCE / 'pilot_summary.json').read_text())
        for k in ('comparator', 'totals', 'certified_by_stratum', 'mean_difference', 'wins_ties_losses', 'optimum_hits',
                  'candidate_minus_each_baseline', 'cpu_ratio_candidate_to_comparator', 'verdict'):
            self.assertEqual(analysis[k], stored[k], k)
        self.assertEqual((stored['verdict'], stored['comparator']), ('READY_FOR_REVIEW', 'milp_highs_4x'))
        self.assertEqual(self.s['verdict'], stored['verdict'])

    def test_no_arm_exceeds_a_certified_optimum_and_arms_are_as_registered(self):
        for r in self.crows:
            if r['reference']['status'] == 'FINITE_CERTIFIED':
                self.assertTrue(all(v is None or v <= r['reference']['value'] for v in r['baselines'].values()))
        for r in self.prows:
            self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))
            self.assertTrue(all(a['isolation'] == 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP' for a in r['arms'].values()))
        import b20r67_refresh_v2_ids as R67
        self.assertEqual(self.s['descriptors'], R67.pre_r67_ids(self.M.arms()))    # recorded before B20_R67

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        hosts = json.loads((EVIDENCE / 'calibration_hosts.json').read_text())
        tasks = [GraphTask.model_validate_json(canonical(t)) for s in hosts['settings'] for t in s['tasks']]
        tasks += [GraphTask.model_validate_json(canonical(t))
                  for t in json.loads((EVIDENCE / 'pilot_hosts.json').read_text())['tasks']]
        tasks += [GraphTask.model_validate_json(canonical(t))
                  for t in json.loads((EVIDENCE / 'development_look_hosts.json').read_text())['tasks']]
        self.assertEqual(len(RD.identities(tasks)), 64 + 30 + 8)
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r41.json').read_text())
            listed = RD.identities([GraphTask.model_validate_json(canonical(t)) for t in add])
            self.assertTrue(RD.identities(tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
