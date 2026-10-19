"""B20_R67: registry v2's kind map outside every identity, and the `maxcut-tabu-v1` domain baseline.

The kind map moved out of `candidates_v2.py`, so adding a kind no longer changes the other kinds' descriptor ids, and
a kind's identity hashes the module actually dispatched for it. The new kind is a standard max-cut tabu search with
the same greedy triangle-free completion as E1's candidate; its witnesses are re-checked by the domain checker.
"""
from itertools import combinations
import unittest
from unittest import mock

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import kinds as K
from genesis.candidate_kinds import maxcut_tabu as MT
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class KindMap(unittest.TestCase):
    def test_the_kind_map_is_outside_every_identity_and_dispatch_is_bound(self):
        self.assertLessEqual({'milp-highs-v1', 'maxcut-tabu-v1'}, set(C2.KINDS))      # later batches add kinds
        for kind in C2.KINDS:
            ident = C2.implementation_identity(kind)
            self.assertNotIn('candidate_kinds/kinds.py', ident)
            self.assertEqual(list(ident)[3], f'candidate_kinds/{K.KINDS[kind]}.py')     # its own module is hashed
        before = C2.implementation_identity('milp-highs-v1')
        with mock.patch.dict(C2.KINDS, {'another-kind-v1': 'maxcut_tabu'}):     # adding a kind ...
            self.assertEqual(C2.implementation_identity('milp-highs-v1'), before)  # ... changes no other identity
        frozen = C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': 2.0}, **PROFILE)
        self.assertEqual(C2.descriptor_problems(frozen, domain=TF), [])
        with mock.patch.dict(C2.KINDS, {'milp-highs-v1': 'maxcut_tabu'}):      # a name pointed at another module
            self.assertIn('implementation identity differs from this code', C2.descriptor_problems(frozen))
        with mock.patch.object(MT, 'FILES', ('candidate_kinds/milp_highs.py',)), \
                mock.patch.dict(C2.KINDS, {'milp-highs-v1': 'maxcut_tabu'}):    # ... that declares another's file
            with self.assertRaises(C2.CandidateError) as ctx:
                C2.implementation_identity('milp-highs-v1')
            self.assertEqual(ctx.exception.code, 'MALFORMED_KIND')


class MaxcutTabu(unittest.TestCase):
    def desc(self, seconds=0.3, **kw):
        return C2.build_descriptor('maxcut-tabu-v1', TF, {'cpu_seconds': seconds}, **dict(PROFILE, **kw))

    def test_parameters_are_closed(self):
        for bad in ({}, {'cpu_seconds': 0}, {'cpu_seconds': 61}, {'cpu_seconds': True}, {'cpu_seconds': 1, 'seed': 2}):
            self.assertIsNotNone(MT.check_parameters(TF, bad), bad)
        self.assertIsNotNone(MT.check_parameters('c4_host_v2', {'cpu_seconds': 1}))
        with self.assertRaises(C2.CandidateError):
            C2.build_descriptor('maxcut-tabu-v1', 'c4_host_v2', {'cpu_seconds': 1}, **PROFILE)

    def test_known_optima_in_process(self):
        k10 = list(combinations(range(10), 2))                   # Turan: the largest triangle-free subgraph has 25
        out = MT.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'cpu_seconds': 0.2}, 2, 7)
        self.assertEqual(out['value'], 25)
        self.assertEqual(check_witness(task(10, k10), [tuple(e) for e in out['selected']])['value'], 25)
        bip = [(u, v) for u in range(6) for v in range(6, 13) if (u + v) % 3]
        out = MT.solve(CandidateGraph(domain=TF, n=13, edges=tuple(bip)), {'cpu_seconds': 0.1}, 2, 1)
        self.assertEqual(out['value'], len(bip))                  # a bipartite host is kept whole

    def test_runs_in_the_sandbox_with_checked_witnesses(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20266701, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = self.desc(0.5)
        r = C2.run(t, d, seed=3, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])
        self.assertGreaterEqual(r['cpu_ns'], int(0.5e9))           # the budget is spent and charged
        p = C2.run(t, d, seed=3, isolation='process')
        self.assertEqual(p['status'], 'SUCCESS', p)


if __name__ == '__main__':
    unittest.main()
