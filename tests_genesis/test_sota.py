"""B20_R75: E1d's candidate and the system's best engine against state-of-the-art tools. Design: fresh seeds, the
arms and their shared profile, the verdict rules, validity and the analysis on synthetic rows."""
import math
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r75_sota as M  # noqa: E402


def synth(n, target, succ, cpu=0.6e9):
    runs = {}
    for a in M.ARMS:
        runs[a] = {}
        for t in M.LADDER:
            k = succ.get(a, {}).get(t, 0)
            runs[a][str(t)] = [{'value': target if i < k else target - 1, 'run': 'SUCCESS', 'cpu_ns': int(cpu),
                                'isolation': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'} for i in range(M.REPS)]
    ex = {s: {'status': 'SUCCESS', 'value': target, 'claims_optimal': True, 'cpu_s': 1.0, 'wall_s': 1.0}
          for s in M.EXACT}
    return {'n': n, 'edges': 400, 'target': target, 'target_certified': True, 'runs': runs, 'exact': ex,
            'reference': {'wall_s': 30.0}, 'cpu_ns': {a: {str(t): int(cpu) for t in M.LADDER} for a in M.ARMS}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r75_sota.py':
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
        self.assertEqual((D[('burer', 2.0)][1]['kind'], D[('burer', 2.0)][1]['parameters']),
                         ('mqlib-v1', {'heuristic': 'BURER2002', 'cpu_seconds': 2.0}))
        self.assertEqual(D[('system', 0.5)][1]['parameters'], {'representation': 'cross_2', 'move': 'descent',
                                                                 'cpu_seconds': 0.5})
        self.assertEqual({str(sorted(d['resource_profile'].items())) for _, d in D.values()},
                         {str(sorted(M.PROFILE.items()))})

    def test_verdicts(self):
        self.assertEqual(M.pair_verdict([1.2, 3]), 'X_FASTER')
        self.assertEqual(M.pair_verdict([-3, -1.2]), 'SOTA_FASTER')
        self.assertEqual(M.pair_verdict([-0.5, 0.5]), 'COMPARABLE')
        self.assertEqual(M.pair_verdict([-2, 0.5]), 'UNRESOLVED')

    def test_analysis_on_synthetic_rows(self):
        rows = []
        for n in M.NS:
            for _ in range(M.PER_N):     # BURER2002 at 0.05 s, the system at 0.5 s, the candidate at 2 s
                rows.append(synth(n, 300, {'burer': {0.05: 3}, 'system': {0.5: 3}, 'candidate': {2.0: 3},
                                           'dsb': {0.1: 3}, 'tabu': {0.05: 3}}))
        by_n = M.analyse(rows)
        v = by_n['63']['versus_sota']
        self.assertEqual((v['system']['verdict'], v['candidate']['verdict'], v['tabu']['verdict']),
                         ('SOTA_FASTER', 'SOTA_FASTER', 'COMPARABLE'))
        self.assertEqual(v['highs']['verdict'], 'SOTA_FASTER')        # never solves: +10 cap
        self.assertEqual(M.overall(by_n, None), 'SOTA_BEATS_SYSTEM')
        self.assertEqual(by_n['60']['exact']['highs']['claims_optimal'], M.PER_N)
        self.assertEqual(M.SOTA, 'burer')
        self.assertIsNone(M.validity(rows)[0])
        self.assertEqual(M.validity([synth(60, 300, {}, cpu=0.3e9)])[0], 'INVALID_CPU_DELIVERY')

    def test_the_study_is_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r75_sota.py').read_text())


EV = ROOT / 'evidence' / 'sota_b20r75'


class Record(unittest.TestCase):
    """B20_R75's saved rows: the validity check fails (BURER2002 never ran), and the summary recomputes."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_the_verdict_is_invalid_and_recomputes(self):
        import json
        self.assertEqual(len(self.rows), M.PER_N * len(M.NS))
        invalid, cpu, fail = M.validity(self.rows)
        self.assertEqual(invalid, 'INVALID_CPU_DELIVERY')
        self.assertLess(cpu['burer'], M.MIN_CPU_AT_HALF)
        self.assertTrue(all(cpu[a] >= M.MIN_CPU_AT_HALF for a in M.ARMS if a != 'burer'))
        self.assertEqual(M.overall(M.analyse(self.rows), invalid), self.s['verdict'])
        self.assertEqual(json.loads(json.dumps(M.analyse(self.rows))), self.s['by_n'])

    def test_the_cause_burer2002_returned_nothing(self):
        # every BURER2002 run returned an empty witness: MQLib rejects seeds above 65535 (B20_R75 record)
        vals = {x['value'] for r in self.rows for t in M.LADDER for x in r['runs']['burer'][str(t)]}
        self.assertEqual(vals, {0})
        self.assertTrue(all(x['value'] > 0 for r in self.rows for a in M.ARMS if a not in ('burer', 'highs')
                            for t in M.LADDER for x in r['runs'][a][str(t)]))

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import json
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EV / 'hosts.json').read_text())['tasks']]
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r75.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
