"""B20_R63: the E1d crossover study. Design: fresh seeds, the arms (the 2 s arm is the E1d package's HiGHS
baseline, the candidate is the package's), the budget profiles, and the verdict rule.

Record (B20_R63): CROSSOVER_AT_8S. The verdict recomputes from the rows (4x +10.30 and 8x +6.37 ADVANTAGE; 16x
+0.43 UNRESOLVED; 32x and 64x NO_MATERIAL_DIFFERENCE); no arm exceeds a certified optimum; the arms are the
registered descriptors; the 30 hosts are distinct and in the e1/e1b exposure addenda."""
from pathlib import Path
import json
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r63_e1d_crossover as M  # noqa: E402
import b20r67_refresh_v2_ids as R67  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r63_e1d_crossover.py':
                continue
            text = path.read_text()
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_arms(self):
        A = M.arms()
        self.assertEqual(list(A), ['candidate'] + [M.arm_name(b) for b in M.BUDGETS])
        self.assertEqual(M.BUDGETS, (2.0, 4.0, 8.0, 16.0, 32.0))
        for b in M.BUDGETS:
            reg, d = A[M.arm_name(b)]
            self.assertEqual((reg, d['kind'], d['parameters']), ('v2', 'milp-highs-v1', {'cpu_seconds': b}))
            self.assertEqual(d['resource_profile']['cpu_seconds'], int(b))
            self.assertGreaterEqual(d['resource_profile']['wall_seconds'], 5 * b)
        import b20r11_e1_readiness as R11
        self.assertEqual(M.mip_profile(2.0), R11.PROFILE)

    def test_rule(self):
        V = M.budget_verdict
        self.assertEqual(V([0.6, 3.0], 0), 'ADVANTAGE')
        self.assertEqual(V([0.5, 3.0], 0), 'UNRESOLVED')
        self.assertEqual(V([-0.4, 0.4], 0), 'NO_MATERIAL_DIFFERENCE')
        self.assertEqual(V([-3.0, -0.6], 0), 'MIP_AHEAD')
        self.assertEqual(V([5.0, 9.0], 1), 'UNRESOLVED_FAILURES')
        adv = {M.arm_name(b): {'verdict': 'ADVANTAGE'} for b in M.BUDGETS}
        self.assertEqual(M.overall(adv), ('ADVANTAGE_THROUGH_64X', None))
        adv['highs_16s'] = {'verdict': 'UNRESOLVED'}
        self.assertEqual(M.overall(adv), ('CROSSOVER_AT_16S', 16.0))

    def test_bootstrap_is_stratified_and_seeded(self):
        by = {'a': [1, 2, 3], 'b': [10, 10, 10]}
        est, ci = M.boot(by)
        self.assertAlmostEqual(est, 6.0)
        self.assertEqual(M.boot(by), (est, ci))
        self.assertTrue(ci[0] <= est <= ci[1])



EV = ROOT / 'evidence' / 'e1d_crossover_b20r63'


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_verdict_recomputes_from_the_rows(self):
        self.assertEqual(len(self.rows), 30)
        v = M.verdict(self.rows)
        for k in ('verdict', 'crossover_budget_s', 'per_budget', 'descriptive', 'certified', 'candidate_failures'):
            self.assertEqual(v[k], self.s[k], k)
        self.assertEqual((v['verdict'], v['crossover_budget_s']), ('CROSSOVER_AT_8S', 8.0))
        got = {a: p['verdict'] for a, p in v['per_budget'].items()}
        self.assertEqual(got, {'highs_2s': 'ADVANTAGE', 'highs_4s': 'ADVANTAGE', 'highs_8s': 'UNRESOLVED',
                               'highs_16s': 'NO_MATERIAL_DIFFERENCE', 'highs_32s': 'NO_MATERIAL_DIFFERENCE'})

    def test_arms_and_optima(self):
        self.assertEqual(self.s['descriptors'], R67.pre_r67_ids(M.arms()))     # recorded before B20_R67
        for r in self.rows:
            self.assertIsNotNone(r['optimum'])
            self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))

    def test_hosts_are_distinct_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EV / 'hosts.json').read_text())['tasks']]
        self.assertEqual(len(RD.identities(tasks)), 30)
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r63.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
