"""B20_R76: E1d's candidate and the system's best engine against CP-SAT and BURER2002. Design: fresh seeds, the arms
and their shared profile (with the fixed MQLib kind and CP-SAT), the verdict and overall rules, validity, and the
analysis on synthetic rows."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r76_sota as M  # noqa: E402


def synth(n, target, succ, cpu=0.6e9):
    runs = {}
    for a in M.ARMS:
        runs[a] = {}
        for t in M.LADDER:
            k = succ.get(a, {}).get(t, 0)
            runs[a][str(t)] = [{'value': target if i < k else target - 1, 'run': 'SUCCESS', 'cpu_ns': int(cpu),
                                'isolation': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'} for i in range(M.REPS)]
    ex = {s: {'status': 'SUCCESS', 'value': target, 'claims_optimal': s == 'cpsat', 'cpu_s': 1.0, 'wall_s': 1.0}
          for s in M.EXACT}
    return {'n': n, 'edges': 400, 'target': target, 'target_certified': True, 'runs': runs, 'exact': ex,
            'reference': {'wall_s': 30.0}, 'cpu_ns': {a: {str(t): int(cpu) for t in M.LADDER} for a in M.ARMS}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r76_sota.py':
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
        self.assertEqual((D[('cpsat', 2.0)][1]['kind'], D[('cpsat', 2.0)][1]['parameters']), ('cpsat-v1', {'cpu_seconds': 2.0}))
        self.assertEqual(D[('burer', 0.5)][1]['kind'], 'mqlib-v1')
        self.assertEqual({str(sorted(d['resource_profile'].items())) for _, d in D.values()},
                         {str(sorted(M.PROFILE.items()))})
        self.assertEqual((M.SOTAS, M.EXACT, M.NS), (('burer', 'cpsat'), ('cpsat', 'highs'), (60, 63)))

    def test_overall_rule(self):
        def by(vb, vc):
            return {'63': {'versus_sota': {'burer': {'system': {'verdict': vb}}, 'cpsat': {'system': {'verdict': vc}}}}}
        self.assertEqual(M.overall(by('X_FASTER', 'X_FASTER'), None), 'SYSTEM_BEATS_SOTA')
        self.assertEqual(M.overall(by('X_FASTER', 'SOTA_FASTER'), None), 'SOTA_BEATS_SYSTEM')
        self.assertEqual(M.overall(by('COMPARABLE', 'COMPARABLE'), None), 'SYSTEM_MATCHES_SOTA')
        self.assertEqual(M.overall(by('X_FASTER', 'COMPARABLE'), None), 'UNRESOLVED')
        self.assertEqual(M.overall(by('X_FASTER', 'X_FASTER'), 'INVALID_FAILURES'), 'INVALID_FAILURES')

    def test_analysis_on_synthetic_rows(self):
        rows = [synth(n, 300, {'cpsat': {2.0: 3}, 'burer': {0.5: 3}, 'system': {0.05: 3}, 'candidate': {0.5: 3},
                               'dsb': {0.05: 3}, 'tabu': {0.05: 3}})
                for n in M.NS for _ in range(M.PER_N)]
        by_n = M.analyse(rows)
        v = by_n['63']['versus_sota']
        self.assertEqual((v['burer']['system']['verdict'], v['cpsat']['system']['verdict']), ('X_FASTER', 'X_FASTER'))
        self.assertEqual(v['burer']['candidate']['verdict'], 'COMPARABLE')
        self.assertEqual(M.overall(by_n, None), 'SYSTEM_BEATS_SOTA')
        self.assertEqual(by_n['60']['exact']['cpsat']['claims_optimal'], M.PER_N)
        self.assertIsNone(M.validity(rows)[0])
        failed = [dict(r, runs=dict(r['runs'], burer={str(t): [dict(x, run='FAILED') for x in r['runs']['burer'][str(t)]]
                                                       for t in M.LADDER})) for r in rows]
        self.assertEqual(M.validity(failed)[0], 'INVALID_FAILURES')

    def test_the_study_is_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r76_sota.py').read_text())


if __name__ == '__main__':
    unittest.main()
