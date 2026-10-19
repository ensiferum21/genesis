"""B20_R70: time-to-solution scaling of E1d's candidate against three domain heuristics. Design: fresh seeds, the
arms and their shared profile, TTS99 and the optimal-run-time rule, the log-ratio and verdict rules, validity, and
the analysis on synthetic rows."""
import math
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r70_tts_scaling as M  # noqa: E402


def synth_row(n, target, succ, cpu=0.6e9):
    """succ: {arm: {t: successes out of REPS}}; arms missing from succ never succeed."""
    runs = {}
    for a in M.ARMS:
        runs[a] = {}
        for t in M.LADDER:
            k = succ.get(a, {}).get(t, 0)
            runs[a][str(t)] = [{'value': target if i < k else target - 1, 'run': 'SUCCESS', 'cpu_ns': int(cpu),
                                'isolation': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'} for i in range(M.REPS)]
    return {'n': n, 'edges': 100, 'target': target, 'target_certified': True, 'runs': runs,
            'cpu_ns': {a: {str(t): int(cpu) for t in M.LADDER} for a in M.ARMS}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r70_tts_scaling.py':
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
        for t in M.LADDER:
            reg, d = D[('candidate', t)]
            self.assertEqual((reg, d['kind'], d['parameters']),
                             ('v1', 'represent-and-repair-v1', {'cpu_seconds': t, 'representation': 'cross_2', 'seed': 0}))
            for a, kind in M.V2_KIND.items():
                reg, d = D[(a, t)]
                self.assertEqual((reg, d['kind'], d['parameters']), ('v2', kind, {'cpu_seconds': t}))
        self.assertEqual({str(sorted(d['resource_profile'].items())) for _, d in D.values()},
                         {str(sorted(M.PROFILE.items()))})
        self.assertEqual(M.LADDER, (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0))
        self.assertEqual((M.REPS, M.PER_N, M.NS), (4, 8, (40, 50, 60)))

    def test_tts99(self):
        self.assertEqual(M.tts99(0.5, 1.0), 0.5)
        self.assertTrue(math.isinf(M.tts99(0.5, 0.0)))
        self.assertEqual(M.tts99(0.1, 0.5), 0.1 * 7)                      # ceil(ln 0.01 / ln 0.5) = 7
        self.assertEqual(M.tts99(0.1, 0.25), 0.1 * 17)                    # ceil(ln 0.01 / ln 0.75) = 17

    def test_optimal_run_time_and_floor(self):
        r = synth_row(60, 100, {'candidate': {0.5: 2, 2.0: 4}, 'tabu': {0.02: 4}})
        tts, t, floor = M.host_tts(r, 'candidate')
        self.assertEqual((tts, t, floor), (2.0, 2.0, False))             # 0.5 * 7 = 3.5 > 2.0 * 1
        self.assertEqual(M.host_tts(r, 'tabu'), (0.02, 0.02, True))       # solved at the first rung: a floor
        self.assertTrue(math.isinf(M.host_tts(r, 'eo')[0]))

    def test_log_ratio_and_verdicts(self):
        self.assertEqual(M.log_ratio(math.inf, math.inf), 0.0)
        self.assertEqual(M.log_ratio(math.inf, 1.0), M.CAP)
        self.assertEqual(M.log_ratio(1.0, math.inf), -M.CAP)
        self.assertEqual(M.log_ratio(4.0, 1.0), 2.0)
        self.assertEqual(M.pair_verdict([1.2, 3]), 'CANDIDATE_FASTER')
        self.assertEqual(M.pair_verdict([-3, -1.5]), 'HEURISTIC_FASTER')
        self.assertEqual(M.pair_verdict([-0.5, 0.5]), 'COMPARABLE')
        self.assertEqual(M.pair_verdict([-2, 0.5]), 'UNRESOLVED')

    def test_analysis_and_overall_on_synthetic_rows(self):
        rows = []
        for n in M.NS:
            for _ in range(M.PER_N):
                if n < 60:
                    rows.append(synth_row(n, 100, {a: {0.02: 4} for a in M.ARMS}))
                else:   # the candidate needs 2 s, tabu 0.1 s, dsb 0.05 s, eo 2 s
                    rows.append(synth_row(n, 100, {'candidate': {2.0: 4}, 'tabu': {0.1: 4}, 'dsb': {0.05: 4},
                                                   'eo': {2.0: 4}}))
        by_n, slopes = M.analyse(rows)
        self.assertEqual({h: by_n['40']['per_heuristic'][h]['verdict'] for h in M.HEURISTICS},
                         {h: 'COMPARABLE' for h in M.HEURISTICS})
        self.assertEqual(by_n['40']['arms']['candidate']['floors'], M.PER_N)
        v60 = {h: by_n['60']['per_heuristic'][h]['verdict'] for h in M.HEURISTICS}
        self.assertEqual(v60, {'tabu': 'HEURISTIC_FASTER', 'dsb': 'HEURISTIC_FASTER', 'eo': 'COMPARABLE'})
        self.assertEqual(M.overall(by_n, None), 'E1D_SLOWER_THAN_SOME')
        self.assertGreater(slopes['candidate'], slopes['dsb'])
        self.assertEqual(M.validity(rows)[0], None)
        self.assertEqual(M.overall(by_n, 'INVALID_CPU_DELIVERY'), 'INVALID_CPU_DELIVERY')
        slow = [synth_row(40, 100, {a: {0.02: 4} for a in M.ARMS}, cpu=0.3e9)]
        self.assertEqual(M.validity(slow)[0], 'INVALID_CPU_DELIVERY')

    def test_the_study_is_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r70_tts_scaling.py').read_text())


if __name__ == '__main__':
    unittest.main()
