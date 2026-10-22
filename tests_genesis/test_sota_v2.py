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


EV = ROOT / 'evidence' / 'sota_b20r76'


class Record(unittest.TestCase):
    """B20_R76's saved rows: valid, the analysis and the verdict (UNRESOLVED) recompute, the tools are the pinned ones,
    every value is a checked one below the target, and the hosts are fresh and in the exposure addenda."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_valid_and_the_verdict_recomputes(self):
        import json
        self.assertEqual(len(self.rows), M.PER_N * len(M.NS))
        invalid, cpu, fail = M.validity(self.rows)
        self.assertIsNone(invalid)
        self.assertTrue(all(cpu[a] >= M.MIN_CPU_AT_HALF for a in M.ARMS))
        self.assertEqual(set(fail.values()), {0.0})                    # BURER2002 now runs: no failures at all
        by_n = M.analyse(self.rows)
        self.assertEqual(json.loads(json.dumps(by_n)), self.s['by_n'])
        self.assertEqual(M.overall(by_n, invalid), self.s['verdict'])
        self.assertEqual(self.s['verdict'], 'UNRESOLVED')
        self.assertEqual(self.s['largest_n_versus_sota'],
                         {'burer': dict.fromkeys(('candidate', 'system', 'dsb', 'tabu', 'highs'), 'UNRESOLVED'),
                          'cpsat': {'candidate': 'UNRESOLVED', 'system': 'UNRESOLVED', 'dsb': 'X_FASTER',
                                    'tabu': 'UNRESOLVED', 'highs': 'COMPARABLE'}})

    def test_who_reached_the_target_within_2_s(self):
        # hosts (of 12) where some rung reached the target: the point the record makes, recomputed from the rows
        solved = {a: sum(not __import__('math').isinf(M.host_tts(r, a)[0]) for r in self.rows) for a in M.ARMS}
        self.assertEqual(solved, {'dsb': 11, 'system': 10, 'candidate': 9, 'tabu': 7, 'burer': 5, 'cpsat': 0,
                                  'highs': 0})
        last = next(r for r in self.rows if r['n'] == 63 and r['edges'] == 490)
        self.assertEqual((last['target'], last['target_certified'], last['exact']['cpsat']['value']), (315, True, 315))
        self.assertTrue(all(x['value'] < 315 for a in M.ARMS for t in M.LADDER for x in last['runs'][a][str(t)]))
        self.assertEqual(sum(r['exact'][s]['claims_optimal'] for r in self.rows for s in M.EXACT), 0)
        self.assertEqual(sum(r['target_certified'] for r in self.rows), 10)

    def test_values_are_bounded_and_isolated(self):
        for r in self.rows:
            self.assertLessEqual(r['target'], r['reference']['upper'])
            self.assertEqual(r['target'], max(r['best_witness_value'], r['reference']['lower']))
            for a in M.ARMS:
                for t in M.LADDER:
                    for x in r['runs'][a][str(t)]:
                        self.assertLessEqual(x['value'], r['target'])
                        self.assertEqual(x['isolation'], 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP')
            for s in M.EXACT:
                self.assertEqual(r['exact'][s]['status'], 'SUCCESS')
                self.assertLessEqual(r['exact'][s]['value'], r['target'])

    def test_the_tools_are_the_pinned_ones(self):
        import json
        from genesis.candidate_kinds import cpsat as K, mqlib as MQ
        self.assertEqual((self.s['mqlib']['sha256'], self.s['mqlib']['source']), (MQ.BINARY_SHA256, MQ.SOURCE))
        import b20r98_repin as R98                 # recorded before B20_R98's repin
        self.assertEqual((self.s['ortools']['sha256'], self.s['ortools']['workers']), (R98.PRE_R98_TREE_SHA256, K.WORKERS))
        self.assertEqual(self.s['ortools']['wheels'], K.WHEELS)
        self.assertEqual(self.s['descriptors'], json.loads(json.dumps(
            {f'{a}@{t}': R98.pre_r98_id(d) for (a, t), (_, d) in M.arm_descriptors().items()})))

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import json
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EV / 'hosts.json').read_text())['tasks']]
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        self.assertEqual(len(RD.identities(tasks)), len(tasks))
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r76.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
