"""B20_R76: `cpsat-v1`, OR-Tools CP-SAT in a pinned tree outside the locked environment. The pin is enforced, the
parameters are closed, known optima are found, and a metered runc run returns a checked witness."""
from itertools import combinations
import unittest
from unittest import mock

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import cpsat as K
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class Pin(unittest.TestCase):
    def test_the_installed_tree_is_the_pinned_one(self):
        self.assertIsNotNone(K.tree_digest())
        self.assertEqual(K.tree_digest(), K.SOTA_TREE_SHA256)
        self.assertIsNone(K.check_parameters(TF, {'cpu_seconds': 1}))

    def test_a_changed_or_missing_tree_is_refused(self):
        with mock.patch.object(K, 'SOTA_TREE_SHA256', '0' * 64):
            self.assertIn('not the pinned one', K.check_parameters(TF, {'cpu_seconds': 1}))
            with self.assertRaises(C2.CandidateError):
                C2.build_descriptor('cpsat-v1', TF, {'cpu_seconds': 1}, **PROFILE)
        self.assertIsNone(K.tree_digest('/nonexistent/genesis-sota'))

    def test_the_locked_environment_does_not_see_it(self):
        import sys
        self.assertNotIn(K.SOTA_DIR, sys.path[:-1] if sys.path and sys.path[-1] == K.SOTA_DIR else sys.path)
        from importlib import util
        if util.find_spec('ortools') is not None:          # only through the pinned tree, never site-packages
            self.assertTrue(util.find_spec('ortools').origin.startswith(K.SOTA_DIR))


class Solving(unittest.TestCase):
    def test_parameters_are_closed(self):
        for bad in ({}, {'cpu_seconds': 0}, {'cpu_seconds': 61}, {'cpu_seconds': True}, {'cpu_seconds': 1, 'x': 1}):
            self.assertIsNotNone(K.check_parameters(TF, bad), bad)
        self.assertIsNotNone(K.check_parameters('c4_host_v2', {'cpu_seconds': 1}))

    def test_known_optima(self):
        k10 = list(combinations(range(10), 2))
        out = K.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'cpu_seconds': 1.0}, 2, 7)
        self.assertEqual(out['value'], 25)
        self.assertEqual(check_witness(task(10, k10), [tuple(e) for e in out['selected']])['value'], 25)
        c5 = [(0, 1), (0, 4), (1, 2), (2, 3), (3, 4)]
        self.assertEqual(K.solve(CandidateGraph(domain=TF, n=5, edges=tuple(c5)), {'cpu_seconds': 0.5}, 2, 1)['value'], 5)

    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20267401, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = C2.build_descriptor('cpsat-v1', TF, {'cpu_seconds': 1.0}, **PROFILE)
        r = C2.run(t, d, seed=987654321987, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])


if __name__ == '__main__':
    unittest.main()
