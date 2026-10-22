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


EV = ROOT / 'evidence' / 'engine_vs_sota_b20r77'


class Record(unittest.TestCase):
    """B20_R77's saved rows: valid; the analysis and the verdict (ENGINE_BEATS_SOTA) recompute; the engine reached the
    best known value on every host; values are bounded and isolated; the tools and descriptors are the pinned and
    recorded ones; the hosts are fresh and in the exposure addenda."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_valid_and_the_verdict_recomputes(self):
        import json
        self.assertEqual(len(self.rows), M.PER_N)
        invalid, cpu, fail = M.validity(self.rows)
        self.assertIsNone(invalid)
        self.assertEqual(set(fail.values()), {0.0})
        a = json.loads(json.dumps(M.analyse(self.rows)))
        for k in ('primary', 'secondary', 'improvement', 'arms', 'exact', 'certified', 'hosts', 'edges'):
            self.assertEqual(a[k], self.s[k], k)
        self.assertEqual(M.overall(M.analyse(self.rows), invalid), self.s['verdict'])
        self.assertEqual(self.s['verdict'], 'ENGINE_BEATS_SOTA')
        self.assertEqual(self.s['primary_verdicts'], {S: {'q0.5': 'ENGINE_FASTER', 'q0.75': 'ENGINE_FASTER'}
                                                      for S in M.SOTAS})
        # the narrowest primary margin: BURER2002 on the typical host
        self.assertEqual(self.s['primary']['burer']['q0.5']['interval_90'], [1.3219, 10.0])
        # B20_R76's statistic agrees for both tools
        for S in M.SOTAS:
            self.assertEqual(self.s['primary'][S]['b20r76_per_host_median']['verdict'], 'ENGINE_FASTER', S)

    def test_who_reached_the_target_within_2_s(self):
        self.assertEqual({a: v['reached_within_2s'] for a, v in self.s['arms'].items()},
                         {'engine': 24, 'dsb': 21, 'system': 19, 'tabu': 15, 'candidate': 15, 'burer': 10, 'cpsat': 0})
        for r in self.rows:     # the engine's best equals the best known value on every host
            self.assertEqual(max(x['value'] for t in M.LADDER for x in r['runs']['engine'][str(t)]), r['target'])
        others = ('system', 'dsb', 'tabu', 'candidate', 'burer', 'cpsat')
        alone = [r for r in self.rows if r['exact']['cpsat']['value'] < r['target']
                 and all(x['value'] < r['target'] for a in others for t in M.LADDER for x in r['runs'][a][str(t)])]
        self.assertEqual(sorted((r['target'], r['target_certified']) for r in alone),
                         [(292, True), (297, False), (303, True)])
        self.assertEqual((self.s['exact']['cpsat_60s']['claims_optimal'], self.s['exact']['cpsat_60s']['reaches_target']),
                         (0, 3))
        self.assertEqual(self.s['certified'], 16)

    def test_values_are_bounded_and_isolated(self):
        for r in self.rows:
            self.assertLessEqual(r['target'], r['reference']['upper'])
            self.assertEqual(r['target'], max(r['best_witness_value'], r['reference']['lower']))
            self.assertEqual(r['target_certified'], r['reference']['upper'] == r['target'])
            self.assertEqual(r['exact']['cpsat']['status'], 'SUCCESS')
            for a in M.ARMS:
                for t in M.LADDER:
                    for x in r['runs'][a][str(t)]:
                        self.assertLessEqual(x['value'], r['target'])
                        self.assertEqual(x['isolation'], 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP')

    def test_the_tools_and_arms_are_the_pinned_ones(self):
        import json
        from genesis.candidate_kinds import cpsat as K, mqlib as MQ
        self.assertEqual((self.s['mqlib']['sha256'], self.s['mqlib']['source']), (MQ.BINARY_SHA256, MQ.SOURCE))
        import b20r98_repin as R98                 # recorded before B20_R98's repin
        self.assertEqual((self.s['ortools']['sha256'], self.s['ortools']['workers']), (R98.PRE_R98_TREE_SHA256, K.WORKERS))
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
        old = json.loads((ROOT / 'evidence' / 'sota_b20r76' / 'hosts.json').read_text())['tasks']
        self.assertFalse(RD.identities(tasks) & RD.identities([GraphTask.model_validate_json(canonical(t)) for t in old]))
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r77.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
