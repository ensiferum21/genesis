"""B20_R77: the system's new engine against CP-SAT and BURER2002 (powered). Design: fresh seeds, the arms and their
shared profile, the quantile-ratio statistic and its paired bootstrap, the verdict and overall rules, validity, and
the analysis on synthetic rows."""
from pathlib import Path
import math
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r77_engine_vs_sota as M  # noqa: E402


def synth(target, succ, cpu=0.6e9):
    """One host row: arm -> {t: number of the 3 runs that reach the target}."""
    runs = {}
    for a in M.ARMS:
        runs[a] = {}
        for t in M.LADDER:
            k = succ.get(a, {}).get(t, 0)
            runs[a][str(t)] = [{'value': target if i < k else target - 1, 'run': 'SUCCESS', 'cpu_ns': int(cpu),
                                'isolation': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'} for i in range(M.REPS)]
    return {'n': 63, 'edges': 460, 'target': target, 'target_certified': True, 'runs': runs,
            'exact': {'cpsat': {'status': 'SUCCESS', 'value': target, 'claims_optimal': False, 'cpu_s': 60.0,
                                'wall_s': 60.0}},
            'reference': {'wall_s': 30.0}, 'cpu_ns': {a: {str(t): int(cpu) for t in M.LADDER} for a in M.ARMS}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r77_engine_vs_sota.py':
                continue
            text = path.read_text()
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_arms(self):
        import json
        D = M.arm_descriptors()
        self.assertEqual(len(D), len(M.ARMS) * len(M.LADDER))
        frozen = json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text())
        self.assertEqual(D[('candidate', 0.5)][1]['descriptor_id'], frozen['descriptor_id'])
        self.assertEqual((D[('engine', 2.0)][1]['kind'], D[('engine', 2.0)][1]['parameters']),
                         ('hybrid-swap-v1', {'cpu_seconds': 2.0}))
        self.assertEqual(D[('burer', 0.5)][1]['kind'], 'mqlib-v1')
        self.assertEqual(D[('cpsat', 0.5)][1]['kind'], 'cpsat-v1')
        self.assertEqual({str(sorted(d['resource_profile'].items())) for _, d in D.values()},
                         {str(sorted(M.PROFILE.items()))})
        self.assertEqual((M.SOTAS, M.QS, M.N, M.PER_N), (('burer', 'cpsat'), (0.5, 0.75), 63, 24))

    def test_quantile_ratio(self):
        inf = math.inf
        self.assertEqual(M.quantile_ratio([0.1, 0.2, inf, inf], [0.1, 0.1, 0.2, 0.2], 0.75), 10.0)   # tool's q75 never
        self.assertEqual(M.quantile_ratio([inf] * 4, [inf] * 4, 0.5), 0.0)
        self.assertAlmostEqual(M.quantile_ratio([0.4] * 4, [0.1] * 4, 0.5), 2.0)
        self.assertEqual(M.quantile_ratio([0.1] * 4, [inf] * 4, 0.5), -10.0)

    def test_the_bootstrap_is_paired(self):
        seen = []
        M.boot(lambda ix: seen.append(tuple(ix)) or 0.0, 5)
        self.assertEqual(len(seen), M.BOOT + 1)
        self.assertEqual(seen[-1], (0, 1, 2, 3, 4))            # the estimate itself is on the hosts as drawn
        self.assertTrue(all(len(s) == 5 for s in seen))

    def test_verdict_and_overall_rules(self):
        self.assertEqual(M.verdict((1.2, 10)), 'ENGINE_FASTER')
        self.assertEqual(M.verdict((-10, -1.2)), 'SOTA_FASTER')
        self.assertEqual(M.verdict((-0.5, 0.5)), 'COMPARABLE')
        self.assertEqual(M.verdict((0.0, 10)), 'UNRESOLVED')

        def a(vs):
            return {'primary': {S: {f'q{q}': {'verdict': vs[i * 2 + j]} for j, q in enumerate(M.QS)}
                                for i, S in enumerate(M.SOTAS)}}
        self.assertEqual(M.overall(a(['ENGINE_FASTER'] * 4), None), 'ENGINE_BEATS_SOTA')
        self.assertEqual(M.overall(a(['ENGINE_FASTER'] * 3 + ['SOTA_FASTER']), None), 'SOTA_BEATS_ENGINE')
        self.assertEqual(M.overall(a(['COMPARABLE'] * 4), None), 'ENGINE_MATCHES_SOTA')
        self.assertEqual(M.overall(a(['ENGINE_FASTER'] * 3 + ['UNRESOLVED']), None), 'MIXED')
        self.assertEqual(M.overall(a(['ENGINE_FASTER'] * 4), 'INVALID_FAILURES'), 'INVALID_FAILURES')

    def test_analysis_on_synthetic_rows(self):
        # the engine reaches every target at 0.25 s; BURER2002 at 0.05 s on k hosts of 24, never on the rest; CP-SAT never
        def rows_for(k):
            return [synth(300, {'engine': {0.25: 3, 0.5: 3, 2.0: 3}, 'system': {2.0: 3}, 'dsb': {0.5: 3, 2.0: 3},
                                'burer': {0.05: 3, 2.0: 3} if i < k else {}})
                    for i in range(M.PER_N)]
        # 9 of 24: BURER2002's median is 'never' on these hosts, but a resample often has it solve half of them,
        # when it is faster (0.05 s against 0.25 s): the typical-host comparison is honestly unresolved
        s9 = M.analyse(rows_for(9))
        self.assertEqual((s9['primary']['burer']['q0.5']['log2_ratio'], s9['primary']['burer']['q0.5']['verdict']),
                         (10.0, 'UNRESOLVED'))
        self.assertEqual(s9['primary']['burer']['q0.75']['verdict'], 'ENGINE_FASTER')
        self.assertEqual(M.overall(s9, None), 'MIXED')
        rows = rows_for(6)
        s = M.analyse(rows)
        self.assertEqual(s['primary']['cpsat']['q0.5']['verdict'], 'ENGINE_FASTER')
        self.assertEqual(s['primary']['burer']['q0.75']['verdict'], 'ENGINE_FASTER')
        self.assertEqual(s['primary']['burer']['q0.5']['log2_ratio'], 10.0)
        self.assertEqual(s['arms']['engine']['reached_within_2s'], 24)
        self.assertEqual(s['arms']['burer']['reached_within_2s'], 6)
        self.assertEqual(s['improvement']['system']['q0.5']['verdict'], 'ENGINE_FASTER')
        self.assertEqual(s['exact']['cpsat_60s']['reaches_target'], 24)
        self.assertIsNone(M.validity(rows)[0])
        self.assertEqual(M.overall(s, None), 'ENGINE_BEATS_SOTA')
        slow = [dict(r, cpu_ns={a: {str(t): int(0.3e9) for t in M.LADDER} for a in M.ARMS}) for r in rows]
        self.assertEqual(M.validity(slow)[0], 'INVALID_CPU_DELIVERY')
        failed = [dict(r, runs=dict(r['runs'], burer={str(t): [dict(x, run='FAILED') for x in r['runs']['burer'][str(t)]]
                                                       for t in M.LADDER})) for r in rows]
        self.assertEqual(M.validity(failed)[0], 'INVALID_FAILURES')

    def test_the_study_is_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r77_engine_vs_sota.py').read_text())


if __name__ == '__main__':
    unittest.main()
