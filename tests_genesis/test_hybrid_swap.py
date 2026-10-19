"""B20_R77: the `hybrid-swap-v1` kind (a cut portfolio, then (1,2)-swap iterated local search on the triangle-free
problem). Registration and the identity binding, closed parameters, the dSB constants, known optima against brute
force, the (1,2)-swap and the kick on their own, the budget, and a metered runc run with a re-checked witness."""
from itertools import combinations
import random
import unittest

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import hybrid_swap as HS
from genesis.candidate_kinds import ising_dsb as SB
from genesis.candidate_kinds import kinds as K
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
KIND = 'hybrid-swap-v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


def brute_force(n, E):
    """The largest triangle-free edge subset, by enumeration (small hosts only)."""
    tri = [(e, f, g) for e, f, g in combinations(range(len(E)), 3)
           if len(set(E[e]) | set(E[f]) | set(E[g])) == 3]
    best = 0
    for mask in range(1 << len(E)):
        if bin(mask).count('1') > best and not any(mask >> e & mask >> f & mask >> g & 1 for e, f, g in tri):
            best = bin(mask).count('1')
    return best


def state(n, E, chosen, seed=0):
    eid = {e: i for i, e in enumerate(E)}
    inc = [[] for _ in range(n)]
    for i, (u, v) in enumerate(E):
        inc[u].append(i)
        inc[v].append(i)
    s = HS.Solution(n, E, inc, eid, random.Random(seed))
    for i in range(len(E)):                      # start from exactly `chosen` (the constructor's fill is undone)
        if s.inS[i]:
            s.remove(i)
    for e in chosen:
        s.add(eid[e])
    return s


class Registration(unittest.TestCase):
    def test_registered_and_bound_to_its_module(self):
        self.assertIn(KIND, C2.KINDS)
        ident = C2.implementation_identity(KIND)
        self.assertEqual(list(ident)[3], 'candidate_kinds/hybrid_swap.py')
        self.assertEqual(HS.FILES, ('candidate_kinds/hybrid_swap.py',))
        self.assertNotIn('candidate_kinds/kinds.py', ident)
        for other in K.KINDS:                    # adding the kind changes no other kind's identity
            if other != KIND:
                self.assertNotIn('candidate_kinds/hybrid_swap.py', C2.implementation_identity(other), other)

    def test_parameters_are_closed(self):
        for bad in ({}, {'cpu_seconds': 0}, {'cpu_seconds': 61}, {'cpu_seconds': True},
                    {'cpu_seconds': 1, 'seed': 2}, {'cpu_seconds': '1'}):
            self.assertIsNotNone(HS.check_parameters(TF, bad), bad)
        self.assertIsNone(HS.check_parameters(TF, {'cpu_seconds': 0.5}))
        self.assertIsNotNone(HS.check_parameters('c4_host_v2', {'cpu_seconds': 1}))
        with self.assertRaises(C2.CandidateError):
            C2.build_descriptor(KIND, 'c4_host_v2', {'cpu_seconds': 1}, **PROFILE)

    def test_the_dynamics_are_dsb_s(self):
        self.assertEqual((HS.REPLICAS, HS.STEPS, HS.A0, HS.DT), (SB.REPLICAS, SB.STEPS, SB.A0, SB.DT))
        self.assertEqual((HS.FRAC, HS.DESC_SHARE, HS.K, HS.P_WORSE), (0.8, 0.5, 4, 0.1))


class Moves(unittest.TestCase):
    def test_a_one_two_swap(self):
        # K4 minus {x, y}: a = 0, b = 1, x = 2, y = 3. {ab, bx, ay} is maximal (ax is blocked only by b, by only by
        # a); removing ab frees both, and {bx, ay, ax, by} (a 4-cycle) is optimal.
        E = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3)]
        s = state(4, E, [(0, 1), (1, 2), (0, 3)])
        self.assertEqual(s.size, 3)
        self.assertEqual(s.swaps(float('inf')), 1)
        self.assertEqual(sorted(s.edges()), [(0, 2), (0, 3), (1, 2), (1, 3)])
        self.assertEqual(check_witness(task(4, E), s.edges())['value'], 4)

    def test_kicks_and_swaps_keep_the_set_triangle_free(self):
        rng = random.Random(4)
        E = sorted({tuple(sorted(rng.sample(range(16), 2))) for _ in range(70)})
        t = task(16, E)
        s = state(16, E, [], seed=9)
        s.fill(range(16))
        for _ in range(300):
            s.kick()
            s.swaps(float('inf'))
            self.assertEqual(check_witness(t, s.edges())['value'], s.size)
            snap = s.snapshot()
            s.kick()
            s.restore(snap)
            self.assertEqual(check_witness(t, s.edges())['value'], s.size)


class KnownOptima(unittest.TestCase):
    def test_against_brute_force(self):
        rng = random.Random(77)
        hosts = [(5, [(0, 1), (0, 4), (1, 2), (2, 3), (3, 4)]),                          # C5: kept whole
                 (6, [(i, 5) for i in range(5)] + [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]),   # the wheel W5
                 (5, list(combinations(range(5), 2)))]                                     # K5: Turan, 6
        for _ in range(4):
            hosts.append((7, sorted({tuple(sorted(rng.sample(range(7), 2))) for _ in range(14)})))
        for n, E in hosts:
            out = HS.solve(CandidateGraph(domain=TF, n=n, edges=tuple(sorted(E))), {'cpu_seconds': 0.2}, 2, 5)
            self.assertEqual(out['value'], brute_force(n, sorted(E)), E)
            self.assertEqual(check_witness(task(n, E), [tuple(e) for e in out['selected']])['value'], out['value'])

    def test_turan(self):
        k10 = list(combinations(range(10), 2))
        out = HS.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'cpu_seconds': 0.2}, 2, 7)
        self.assertEqual(out['value'], 25)

    def test_the_budget_bounds_the_run(self):
        import time
        h = [(u, v) for u, v in combinations(range(40), 2) if (u * 7 + v * 3) % 5 < 3]
        t0 = time.process_time()
        HS.solve(CandidateGraph(domain=TF, n=40, edges=tuple(h)), {'cpu_seconds': 0.3}, 2, 11)
        self.assertLess(time.process_time() - t0, 0.3 + 0.35)


class Sandbox(unittest.TestCase):
    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20267701, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = C2.build_descriptor(KIND, TF, {'cpu_seconds': 0.5}, **PROFILE)
        r = C2.run(t, d, seed=3, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])
        self.assertGreaterEqual(r['cpu_ns'], int(0.5e9))


if __name__ == '__main__':
    unittest.main()
