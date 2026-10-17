"""B20_R66: E1d at n60, internal replication of B20_R64's n60 result with HiGHS up to 60 s. Design: fresh seeds,
the arms, the validity criterion and the verdict rule.

Record (B20_R66): REPLICATED_ADVANTAGE_THROUGH_120X, valid (CPU delivery 0.99): +18.75 at 32 s, +2.20 at 60 s."""
from pathlib import Path
import json
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r63_e1d_crossover as R63  # noqa: E402
import b20r66_e1d_n60 as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r66_e1d_n60.py':
                continue
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', path.read_text()), (path.name, s))

    def test_arms(self):
        A, B = M.arms(), R63.arms()
        self.assertEqual(list(A), ['candidate', 'highs_32s', 'highs_60s'])
        self.assertEqual(A['candidate'][1]['descriptor_id'], B['candidate'][1]['descriptor_id'])
        self.assertEqual(A['highs_32s'][1]['descriptor_id'], B['highs_32s'][1]['descriptor_id'])
        d = A['highs_60s'][1]
        self.assertEqual((d['parameters'], d['resource_profile']['cpu_seconds'], d['resource_profile']['wall_seconds']),
                         ({'cpu_seconds': 60.0}, 60, 300))

    def test_rule(self):
        per = lambda v32, v60: {'highs_32s': {'verdict': v32}, 'highs_60s': {'verdict': v60}}
        self.assertEqual(M.overall(per('ADVANTAGE', 'ADVANTAGE'), True), 'REPLICATED_ADVANTAGE_THROUGH_120X')
        self.assertEqual(M.overall(per('ADVANTAGE', 'UNRESOLVED'), True), 'REPLICATED_CROSSOVER_BY_120X')
        self.assertEqual(M.overall(per('UNRESOLVED', 'ADVANTAGE'), True), 'NOT_REPLICATED')
        self.assertEqual(M.overall(per('ADVANTAGE', 'ADVANTAGE'), False), 'INVALID_CPU_DELIVERY')

    def test_delivery(self):
        row = lambda v32, c32, v60, c60: {'optimum': None, 'reference': {'lower': 100, 'upper': 101},
                                          'arms': {'candidate': {'value': 100},
                                                   'highs_32s': {'value': v32, 'cpu_ns': int(c32 * 1e9)},
                                                   'highs_60s': {'value': v60, 'cpu_ns': int(c60 * 1e9)}}}
        d = M.delivery([row(90, 32.0, 95, 60.0), row(91, 16.0, 100, 1.0)])
        self.assertEqual(d['highs_32s'], (2, 0.75))
        self.assertEqual(d['highs_60s'], (1, 1.0))           # the 60 s arm reached the best known on the 2nd host



EV = ROOT / 'evidence' / 'e1d_n60_b20r66'


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_verdict_and_validity_recompute(self):
        self.assertEqual(len(self.rows), 20)
        v = M.verdict(self.rows)
        for k in ('verdict', 'per_budget', 'cpu_delivery', 'valid', 'descriptive', 'candidate_failures'):
            self.assertEqual(json.loads(json.dumps(v[k])), self.s[k], k)
        self.assertEqual(v['verdict'], 'REPLICATED_ADVANTAGE_THROUGH_120X')
        self.assertTrue(v['valid'])
        self.assertEqual(self.s['descriptors'], {n: d['descriptor_id'] for n, (_, d) in M.arms().items()})

    def test_no_arm_exceeds_a_proven_upper_bound(self):
        for r in self.rows:
            self.assertTrue(all(a['value'] <= r['reference']['upper'] for a in r['arms'].values()))

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        load = lambda p: [GraphTask.model_validate_json(canonical(t)) for t in json.loads(p.read_text())['tasks']]
        tasks = load(EV / 'hosts.json')
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        self.assertEqual(len(RD.identities(tasks)), 20)
        self.assertFalse(RD.identities(tasks) & RD.identities(load(ROOT / 'evidence' / 'e1d_scaling_b20r64' / 'hosts.json')))
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r66.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
