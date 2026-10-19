"""B20_R69: physics-inspired domain-baseline kinds, `ising-dsb-v1` (discrete simulated bifurcation) and
`maxcut-eo-v1` (tau-extremal optimization). Closed parameters, the identity binding, known optima, the dynamics'
own invariants, and a metered runc run with a re-checked witness."""
from itertools import combinations
import random
import unittest

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import ising_dsb as SB
from genesis.candidate_kinds import kinds as K
from genesis.candidate_kinds import maxcut_eo as EO
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}
NEW = {'ising-dsb-v1': SB, 'maxcut-eo-v1': EO}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class Registration(unittest.TestCase):
    def test_kinds_are_registered_and_bound_to_their_modules(self):
        for kind, mod in NEW.items():
            self.assertIn(kind, C2.KINDS)
            ident = C2.implementation_identity(kind)
            self.assertEqual(list(ident)[3], f'candidate_kinds/{K.KINDS[kind]}.py')
            self.assertEqual(mod.FILES, (f'candidate_kinds/{K.KINDS[kind]}.py',))
            self.assertNotIn('candidate_kinds/kinds.py', ident)

    def test_parameters_are_closed(self):
        for kind, mod in NEW.items():
            for bad in ({}, {'cpu_seconds': 0}, {'cpu_seconds': 61}, {'cpu_seconds': True},
                        {'cpu_seconds': 1, 'seed': 2}, {'cpu_seconds': '1'}):
                self.assertIsNotNone(mod.check_parameters(TF, bad), (kind, bad))
            self.assertIsNone(mod.check_parameters(TF, {'cpu_seconds': 0.5}))
            self.assertIsNotNone(mod.check_parameters('c4_host_v2', {'cpu_seconds': 1}))
            with self.assertRaises(C2.CandidateError):
                C2.build_descriptor(kind, 'c4_host_v2', {'cpu_seconds': 1}, **PROFILE)


class KnownOptima(unittest.TestCase):
    def test_turan_and_triangle_free_hosts(self):
        k10 = list(combinations(range(10), 2))                  # Turan: the largest triangle-free subgraph has 25
        c5 = [(0, 1), (0, 4), (1, 2), (2, 3), (3, 4)]            # triangle-free: kept whole although its max cut is 4
        for kind, mod in NEW.items():
            out = mod.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'cpu_seconds': 0.2}, 2, 7)
            self.assertEqual(out['value'], 25, kind)
            self.assertEqual(check_witness(task(10, k10), [tuple(e) for e in out['selected']])['value'], 25)
            out = mod.solve(CandidateGraph(domain=TF, n=5, edges=tuple(c5)), {'cpu_seconds': 0.05}, 2, 1)
            self.assertEqual(out['value'], 5, kind)

    def test_a_planted_bipartition_is_found(self):
        rng = random.Random(5)                                   # complete bipartite K_{12,12} plus a few in-part edges
        edges = sorted([(u, v) for u in range(12) for v in range(12, 24)] +
                       list({tuple(sorted(rng.sample(range(12), 2))) for _ in range(6)}))
        for kind, mod in NEW.items():
            out = mod.solve(CandidateGraph(domain=TF, n=24, edges=tuple(edges)), {'cpu_seconds': 0.3}, 2, 3)
            self.assertGreaterEqual(out['value'], 144, kind)    # at least the planted cut survives completion
            check_witness(task(24, edges), [tuple(e) for e in out['selected']])


class Dynamics(unittest.TestCase):
    def test_dense_hosts_are_solved_as_well_as_by_tabu_search(self):
        """Guards the dynamics, not just the plumbing: an unstable step (dt = 1) left dSB near a random cut."""
        import sys
        from pathlib import Path
        from unittest import mock
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        import b20r64_e1d_scaling as R64
        from genesis.candidate_kinds import maxcut_tabu as MT
        t = R64.generate_beyond_space(20266903, 1, 'DEV', {'n': 60, 'p_in': 0.8, 'p_out': 0.06}, set())[0][0]
        v = CandidateGraph(domain=TF, n=t.n, edges=t.edges)                       # 415 edges, degree about 14
        ref = MT.solve(v, {'cpu_seconds': 0.3}, 2, 1)['value']
        for kind, mod in NEW.items():
            self.assertGreaterEqual(mod.solve(v, {'cpu_seconds': 0.3}, 2, 1)['value'], 0.97 * ref, kind)
        with mock.patch.object(SB, 'DT', 1.0):                                   # the guard detects the unstable step
            self.assertLess(SB.solve(v, {'cpu_seconds': 0.3}, 2, 1)['value'], 0.97 * ref)

    def test_eo_rank_law_and_tau(self):
        self.assertAlmostEqual(EO.tau_for(60), 1 + 1 / 4.0943445622, places=6)
        self.assertGreater(EO.tau_for(10), EO.tau_for(1000))     # tau -> 1+ as n grows

    def test_sb_constants(self):
        self.assertEqual((SB.A0, SB.DT), (1.0, 0.5))                 # dt = 1 is unstable on dense hosts (docstring)
        self.assertEqual((SB.REPLICAS, SB.STEPS), (32, 400))

    def test_the_budget_bounds_the_run(self):
        import time
        h = [(u, v) for u, v in combinations(range(40), 2) if (u * 7 + v * 3) % 5 < 3]
        for kind, mod in NEW.items():
            t0 = time.process_time()
            mod.solve(CandidateGraph(domain=TF, n=40, edges=tuple(h)), {'cpu_seconds': 0.3}, 2, 11)
            self.assertLess(time.process_time() - t0, 0.3 + 0.35, kind)   # one batch or restart of slack at most


class Sandbox(unittest.TestCase):
    def test_runs_in_the_sandbox_with_checked_witnesses(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20266901, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        for kind in NEW:
            d = C2.build_descriptor(kind, TF, {'cpu_seconds': 0.5}, **PROFILE)
            r = C2.run(t, d, seed=3, expected_id=d['descriptor_id'], isolation='runc')
            self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), (kind, r))
            self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])
            self.assertGreaterEqual(r['cpu_ns'], int(0.5e9), kind)


if __name__ == '__main__':
    unittest.main()
