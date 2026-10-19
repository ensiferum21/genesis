"""B20_R74: `mqlib-v1`, MQLib's BURER2002 built from a pinned commit outside the locked environment. The pin is
enforced, the build is reproducible, parameters are closed, known optima are found, and a metered runc run returns a
checked witness."""
from itertools import combinations
import unittest
from unittest import mock

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import mqlib as MQ
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class Pin(unittest.TestCase):
    def test_the_installed_binary_is_the_pinned_one(self):
        self.assertEqual(MQ.binary_digest(), MQ.BINARY_SHA256)
        self.assertIsNone(MQ.check_parameters(TF, {'heuristic': 'BURER2002', 'cpu_seconds': 1}))
        self.assertIn('C2.implementation_identity' if False else 'candidate_kinds/mqlib.py',
                      C2.implementation_identity('mqlib-v1'))

    def test_a_changed_or_missing_binary_is_refused(self):
        with mock.patch.object(MQ, 'BINARY_SHA256', '0' * 64):
            self.assertIn('not the pinned one', MQ.check_parameters(TF, {'heuristic': 'BURER2002', 'cpu_seconds': 1}))
            with self.assertRaises(C2.CandidateError):
                C2.build_descriptor('mqlib-v1', TF, {'heuristic': 'BURER2002', 'cpu_seconds': 1}, **PROFILE)
        self.assertIsNone(MQ.binary_digest('/nonexistent/MQLib'))


class Solving(unittest.TestCase):
    def test_parameters_are_closed(self):
        for bad in ({}, {'heuristic': 'BURER2002'}, {'heuristic': 'X', 'cpu_seconds': 1},
                    {'heuristic': 'BURER2002', 'cpu_seconds': 0}, {'heuristic': 'BURER2002', 'cpu_seconds': True},
                    {'heuristic': 'BURER2002', 'cpu_seconds': 1, 'seed': 1}):
            self.assertIsNotNone(MQ.check_parameters(TF, bad), bad)
        self.assertIsNotNone(MQ.check_parameters('c4_host_v2', {'heuristic': 'BURER2002', 'cpu_seconds': 1}))

    def test_parse_cut(self):
        self.assertEqual(MQ.parse_cut('x\n\nSolution:\n-1 1 1\n', 3), [0, 1, 1])
        self.assertIsNone(MQ.parse_cut('Solution:\n1 1\n', 3))
        self.assertIsNone(MQ.parse_cut('no solution\n', 3))

    def test_known_optima(self):
        k10 = list(combinations(range(10), 2))
        out = MQ.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'heuristic': 'BURER2002', 'cpu_seconds': 0.2},
                       2, 7)
        self.assertEqual(out['value'], 25)
        self.assertEqual(check_witness(task(10, k10), [tuple(e) for e in out['selected']])['value'], 25)

    def test_study_sized_seeds_work_and_failures_are_loud(self):
        # B20_R75: seeds above 65535 made MQLib exit, and the kind returned an empty answer
        k10 = tuple(combinations(range(10), 2))
        out = MQ.solve(CandidateGraph(domain=TF, n=10, edges=k10), {'heuristic': 'BURER2002', 'cpu_seconds': 0.1},
                       2, 123456789012345)
        self.assertEqual(out['value'], 25)
        with mock.patch.object(MQ, 'BINARY', '/bin/false'):
            with self.assertRaises(RuntimeError):
                MQ.solve(CandidateGraph(domain=TF, n=10, edges=k10), {'heuristic': 'BURER2002', 'cpu_seconds': 0.1}, 2, 1)

    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20267401, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = C2.build_descriptor('mqlib-v1', TF, {'heuristic': 'BURER2002', 'cpu_seconds': 0.5}, **PROFILE)
        r = C2.run(t, d, seed=987654321987, expected_id=d['descriptor_id'], isolation='runc')       # a study-sized seed
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertGreater(r['result']['value'], 0)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])


if __name__ == '__main__':
    unittest.main()
