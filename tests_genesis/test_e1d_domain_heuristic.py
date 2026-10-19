"""B20_R68: E1d's candidate against a standard max-cut heuristic. Design: fresh seeds, the arms, the verdict rule,
the CPU-delivery criterion and the analysis on synthetic rows."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r68_e1d_domain_heuristic as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r68_e1d_domain_heuristic.py':
                continue
            text = path.read_text()
            for s in (M.SEED_A, M.SEED_B, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_arms(self):
        import json
        A = M.arms()
        self.assertEqual(list(A), ['candidate', 'tabu_0.5s', 'tabu_2s', 'highs_2s'])
        pkg = ROOT / 'handoff' / 'e1d'
        self.assertEqual(A['candidate'], ('v1', json.loads((pkg / 'candidate_descriptor.json').read_text())))
        self.assertEqual(A['highs_2s'][1]['descriptor_id'],
                         json.loads((pkg / 'package_index.json').read_text())['baselines']['milp_highs_4x'])
        for name, sec in (('tabu_0.5s', 0.5), ('tabu_2s', 2.0)):
            reg, d = A[name]
            self.assertEqual((reg, d['kind'], d['parameters']), ('v2', 'maxcut-tabu-v1', {'cpu_seconds': sec}))
        profiles = {d['resource_profile'] == A['tabu_0.5s'][1]['resource_profile'] for _, d in list(A.values())[1:]}
        self.assertEqual(profiles, {True})                                      # one profile for every v2 arm
        self.assertEqual(A['tabu_0.5s'][1]['resource_profile'], dict(M.PROFILE))

    def test_rule(self):
        self.assertEqual(M.part_verdict([0.6, 3.0], 0), 'CANDIDATE_AHEAD')
        self.assertEqual(M.part_verdict([-0.4, 0.4], 0), 'NO_MATERIAL_DIFFERENCE')
        self.assertEqual(M.part_verdict([-3.0, -0.6], 0), 'HEURISTIC_AHEAD')
        self.assertEqual(M.part_verdict([-0.4, 1.0], 0), 'UNRESOLVED')
        self.assertEqual(M.part_verdict([0.6, 3.0], 1), 'UNRESOLVED_FAILURES')
        self.assertEqual(M.part_verdict([0.6, 3.0], 1, False), 'INVALID_CPU_DELIVERY')     # checked first
        self.assertEqual(M.OVERALL['NO_MATERIAL_DIFFERENCE'], 'E1D_MATCHES_DOMAIN_HEURISTIC')

    def test_analysis_on_synthetic_rows(self):
        def row(stratum, values, cpu=0.6, opt=None):
            return {'stratum': stratum, 'optimum': opt, 'reference': {'upper': 101, 'wall_s': 1.0},
                    'arms': {n: {'value': v, 'run': 'SUCCESS', 'cpu_ns': int(cpu * 1e9)} for n, v in values.items()}}
        names = ['candidate', 'tabu_0.5s', 'tabu_2s', 'highs_2s']
        rows = [row(s, {'candidate': 100, 'tabu_0.5s': 100, 'tabu_2s': 100, 'highs_2s': 90}, opt=100)
                for s in ('a', 'b', 'c') for _ in range(10)]
        out = M.analyse_part(rows, names)
        p = out['primary_candidate_minus_tabu_0.5s']
        self.assertEqual((p['estimate'], p['interval_90'], p['verdict']), (0.0, [0.0, 0.0], 'NO_MATERIAL_DIFFERENCE'))
        self.assertEqual(out['secondary']['tabu_0.5s_minus_highs_2s']['estimate'], 10.0)
        self.assertEqual(out['optimum_hits'], {'candidate': 30, 'tabu_0.5s': 30, 'tabu_2s': 30, 'highs_2s': 0})
        self.assertEqual(out['mean_gap_to_upper_bound']['highs_2s'], 11.0)
        slow = [row('a', {'candidate': 100, 'tabu_0.5s': 90, 'tabu_2s': 100, 'highs_2s': 90}, cpu=0.3)] * 10
        self.assertEqual(M.analyse_part(slow, names)['primary_candidate_minus_tabu_0.5s']['verdict'],
                         'INVALID_CPU_DELIVERY')
        failed = [dict(r, arms=dict(r['arms'], **{'tabu_0.5s': {'value': 0, 'run': 'FAILED', 'cpu_ns': 6 * 10**8}}))
                  for r in rows]
        self.assertEqual(M.analyse_part(failed, names)['primary_candidate_minus_tabu_0.5s']['verdict'],
                         'UNRESOLVED_FAILURES')

    def test_the_study_is_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r68_e1d_domain_heuristic.py').read_text())


if __name__ == '__main__':
    unittest.main()
