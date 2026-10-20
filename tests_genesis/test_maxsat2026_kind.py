"""B20_R91: `maxsat-anytime-2026-v1`, the MaxSAT Evaluation 2026 anytime entrants built from their submitted sources.
Pins (binaries and the SGAT weight file) are enforced; the post-2022 encoding is the same instance (and the same
seeded copy) as `maxsat-anytime-v1`'s; the timeout hint is whole seconds; every solver finds known optima, returns
checked witnesses, fails loudly, and runs in the sandbox."""
from itertools import combinations
import random
import unittest
from unittest import mock

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import maxsat as MS, maxsat2026 as M
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}


def task(n, edges):
    return GraphTask(task_id='t', domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class Encoding(unittest.TestCase):
    def test_the_post_2022_text_is_the_same_instance_and_copy(self):
        rng = random.Random(1)
        E = [e for e in combinations(range(12), 2) if rng.random() < 0.6]
        for seed in (None, 5):
            old = MS.wcnf(E, seed) if seed is None else MS.wcnf(E, seed)[0]
            new = M.wcnf2022(E, seed) if seed is None else M.wcnf2022(E, seed)[0]
            top = [l for l in old.splitlines() if l.startswith('p ')][0].split()[4]
            want = [('h ' + l.split(' ', 1)[1]) if l.split(' ', 1)[0] == top else l
                    for l in old.splitlines() if not l.startswith('p ')]
            self.assertEqual(new.splitlines(), want)
            self.assertFalse(any(l.startswith('p ') for l in new.splitlines()))
            self.assertEqual(new.splitlines()[:4], old.splitlines()[:4])            # the standardised header
        self.assertEqual(M.wcnf2022(E, 5)[1], MS.wcnf(E, 5)[1])

    def test_the_timeout_hint_is_whole_seconds_rounded_up(self):
        self.assertEqual([M.hint(b) for b in (0.01, 0.05, 0.5, 1.0, 1.2, 2.0, 10.0)], [1, 1, 1, 1, 2, 2, 10])


class Pins(unittest.TestCase):
    def test_every_binary_and_data_file_is_pinned(self):
        for name, s in M.SOLVERS.items():
            self.assertEqual(M.digest(s['binary']), s['sha256'], name)
            for p, h in s['data'].items():
                self.assertEqual(M.digest(p), h, p)
            self.assertIsNone(M.check_parameters(TF, {'solver': name, 'cpu_seconds': 1}), name)
        ident = C2.implementation_identity('maxsat-anytime-2026-v1')
        self.assertIn('candidate_kinds/maxsat2026.py', ident)
        self.assertIn('candidate_kinds/maxsat.py', ident)

    def test_a_changed_binary_or_weight_file_and_bad_parameters_are_refused(self):
        s = M.SOLVERS['sgat-nuwls-c']
        with mock.patch.dict(M.SOLVERS, {'sgat-nuwls-c': dict(s, data={p: '0' * 64 for p in s['data']})}):
            self.assertIn('not the pinned build', M.check_parameters(TF, {'solver': 'sgat-nuwls-c', 'cpu_seconds': 1}))
        with mock.patch.dict(M.SOLVERS, {'pasmaxsat-c': dict(M.SOLVERS['pasmaxsat-c'], sha256='0' * 64)}):
            with self.assertRaises(C2.CandidateError):
                C2.build_descriptor('maxsat-anytime-2026-v1', TF, {'solver': 'pasmaxsat-c', 'cpu_seconds': 1}, **PROFILE)
        for bad in ({}, {'solver': 'pasmaxsat-c'}, {'solver': 'deepdist', 'cpu_seconds': 1},
                    {'solver': 'pasmaxsat-c', 'cpu_seconds': 0}, {'solver': 'pasmaxsat-c', 'cpu_seconds': 61},
                    {'solver': 'pasmaxsat-c', 'cpu_seconds': 1, 'seed': 2}):
            self.assertIsNotNone(M.check_parameters(TF, bad), bad)


class Solving(unittest.TestCase):
    def test_known_optima_and_checked_witnesses(self):
        k10 = list(combinations(range(10), 2))
        rng = random.Random(3)
        E = [e for e in combinations(range(24), 2) if rng.random() < 0.5]
        for name in M.SOLVERS:
            out = M.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'solver': name, 'cpu_seconds': 0.5}, 2, 7)
            self.assertEqual(out['value'], 25, name)
            for seed in (1, 123456789012345):
                out = M.solve(CandidateGraph(domain=TF, n=24, edges=tuple(E)), {'solver': name, 'cpu_seconds': 0.3},
                              2, seed)
                self.assertEqual(check_witness(task(24, E), [tuple(e) for e in out['selected']])['value'],
                                 out['value'], name)
                self.assertGreater(out['value'], len(E) // 2, name)

    def test_failures_are_loud(self):
        k6 = tuple(combinations(range(6), 2))
        with mock.patch.dict(M.SOLVERS, {'pasmaxsat-c': dict(M.SOLVERS['pasmaxsat-c'], binary='/bin/true')}):
            with self.assertRaises(RuntimeError):
                M.solve(CandidateGraph(domain=TF, n=6, edges=k6), {'solver': 'pasmaxsat-c', 'cpu_seconds': 0.1}, 2, 1)
        with mock.patch.object(MS, 'parse_model', return_value=set(range(1, len(k6) + 1))):
            with self.assertRaises(RuntimeError) as cm:
                M.solve(CandidateGraph(domain=TF, n=6, edges=k6), {'solver': 'pasmaxsat-c', 'cpu_seconds': 0.1}, 2, 1)
        self.assertIn('violates a hard clause', str(cm.exception))

    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20269101, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        for name in M.SOLVERS:
            d = C2.build_descriptor('maxsat-anytime-2026-v1', TF, {'solver': name, 'cpu_seconds': 0.5}, **PROFILE)
            r = C2.run(t, d, seed=987654321987, expected_id=d['descriptor_id'], isolation='runc')
            self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), (name, r))
            self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'],
                             r['result']['value'], name)


if __name__ == '__main__':
    unittest.main()
