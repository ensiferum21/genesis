"""B20_R87: `maxsat-anytime-v1` (the strongest anytime MaxSAT solvers, built from pinned sources) and
`mqlib-heuristic-v1` (any MaxSAT/QUBO heuristic of MQLib). Pins are enforced, the encoding is exact (also as a seeded
isomorphic copy), models are decoded back to the right edges, parameters are closed, every solver finds known optima,
and a metered runc run returns a checked witness."""
from itertools import combinations
import random
import unittest
from unittest import mock

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import maxsat as MS, mqlib_heuristic as MH
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


def random_edges(n, p, seed):
    rng = random.Random(seed)
    return [(u, v) for u, v in combinations(range(n), 2) if rng.random() < p]


def clauses(text):
    lines = [l.split() for l in text.splitlines() if not l.startswith('c')]
    head = lines[0]
    assert head[:2] == ['p', 'wcnf']
    body = [list(map(int, l)) for l in lines[1:]]
    comments = text.splitlines()[:4]
    assert comments == ['c {', f'c "nvars": {head[2]},', f'c "ncls": {head[3]},', 'c }'], comments
    assert len(body) == int(head[3])
    return int(head[2]), int(head[3]), int(head[4]), body


class Encoding(unittest.TestCase):
    def test_the_encoding_is_one_soft_unit_per_edge_and_one_hard_clause_per_triangle(self):
        E = random_edges(12, 0.6, 1)
        T = MS.triangles(E)
        self.assertEqual(sorted(T), sorted(t for t in combinations(range(12), 3)
                                           if all(e in set(E) for e in combinations(t, 2))))
        V, C, top, cl = clauses(MS.wcnf(E))
        self.assertEqual((V, C, top, len(cl)), (len(E), len(E) + len(T), len(E) + 1, len(E) + len(T)))
        hard = sorted(sorted(-x for x in c[1:-1]) for c in cl if c[0] == top)
        self.assertEqual(hard, sorted(sorted(E.index(e) + 1 for e in combinations(t, 2)) for t in T))
        self.assertEqual(sorted(c[1] for c in cl if c[0] == 1), list(range(1, len(E) + 1)))

    def test_a_seeded_copy_is_isomorphic_and_decodes_to_the_same_edges(self):
        E = random_edges(14, 0.5, 2)
        plain = clauses(MS.wcnf(E))
        text, order = MS.wcnf(E, 99)
        V, C, top, cl = clauses(text)
        self.assertEqual((V, C, top), plain[:3])
        self.assertEqual(sorted(order), list(range(len(E))))
        self.assertNotEqual(order, list(range(len(E))))
        self.assertEqual(MS.wcnf(E, 99), (text, order))                       # deterministic in the seed
        self.assertNotEqual(MS.wcnf(E, 100)[1], order)
        # every hard clause of the copy is a host triangle under the map variable k -> edge order[k-1]
        tri = {frozenset(combinations(t, 2)) for t in MS.triangles(E)}
        got = {frozenset(E[order[-x - 1]] for x in c[1:-1]) for c in cl if c[0] == top}
        self.assertEqual(got, tri)

    def test_parse_model(self):
        self.assertEqual(MS.parse_model('c x\no 3\nv 1011\n', 4), {1, 3, 4})
        self.assertEqual(MS.parse_model('v 1 -2\nv 3 -4 0\n', 4), {1, 3})
        self.assertEqual(MS.parse_model('v 0000\nv 0110\n', 4), {2, 3})            # the last line counts
        self.assertIsNone(MS.parse_model('v 01\n', 4))
        self.assertIsNone(MS.parse_model('o 3\ns SATISFIABLE\n', 4))


class Pins(unittest.TestCase):
    def test_every_installed_solver_is_the_pinned_build(self):
        for name, s in MS.SOLVERS.items():
            self.assertEqual(MS.binary_digest(s['binary']), s['sha256'], name)
            self.assertIsNone(MS.check_parameters(TF, {'solver': name, 'cpu_seconds': 1}), name)
        self.assertIn('candidate_kinds/maxsat.py', C2.implementation_identity('maxsat-anytime-v1'))

    def test_the_pin_ignores_a_build_stamp_only(self):
        # B20_R98: a rebuild differs only in the `date; uname` stamp; anything else still changes the digest
        import hashlib
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            a, b, c, plain = (Path(d) / x for x in 'abcp')
            a.write_bytes(b'\x7fELF..Thu Oct 22 22:07:48 +08 2026 Linux vm 6.18.44-fc-v140 x86_64\x00tail')
            b.write_bytes(b'\x7fELF..Tue Oct 20 05:31:02 UTC 2026 Linux vm 6.18.44-fc-v140 x86_64\x00tail')
            c.write_bytes(b'\x7fELF..Tue Oct 20 05:31:02 UTC 2026 Linux vm 6.18.44-fc-v140 x86_64\x00tAil')
            plain.write_bytes(b'\x7fELF no stamp here')
            self.assertEqual(MS.binary_digest(str(a)), MS.binary_digest(str(b)))
            self.assertNotEqual(MS.binary_digest(str(b)), MS.binary_digest(str(c)))
            self.assertEqual(MS.binary_digest(str(plain)), hashlib.sha256(plain.read_bytes()).hexdigest())

    def test_a_changed_binary_and_bad_parameters_are_refused(self):
        with mock.patch.dict(MS.SOLVERS, {'deepdist': dict(MS.SOLVERS['deepdist'], sha256='0' * 64)}):
            self.assertIn('not the pinned build', MS.check_parameters(TF, {'solver': 'deepdist', 'cpu_seconds': 1}))
            with self.assertRaises(C2.CandidateError):
                C2.build_descriptor('maxsat-anytime-v1', TF, {'solver': 'deepdist', 'cpu_seconds': 1}, **PROFILE)
        for bad in ({}, {'solver': 'deepdist'}, {'solver': 'x', 'cpu_seconds': 1},
                    {'solver': 'deepdist', 'cpu_seconds': 0}, {'solver': 'deepdist', 'cpu_seconds': True},
                    {'solver': 'deepdist', 'cpu_seconds': 61}, {'solver': 'deepdist', 'cpu_seconds': 1, 'seed': 1}):
            self.assertIsNotNone(MS.check_parameters(TF, bad), bad)
        self.assertIsNotNone(MS.check_parameters('c4_host_v2', {'solver': 'deepdist', 'cpu_seconds': 1}))


class Solving(unittest.TestCase):
    def test_every_solver_finds_known_optima_and_returns_checked_witnesses(self):
        k10 = list(combinations(range(10), 2))                        # K10: the optimum is the balanced cut, 25
        E = random_edges(24, 0.5, 3)
        for name in MS.SOLVERS:
            out = MS.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)), {'solver': name, 'cpu_seconds': 0.5},
                           2, 7)
            self.assertEqual(out['value'], 25, name)
            self.assertEqual(check_witness(task(10, k10), [tuple(e) for e in out['selected']])['value'], 25, name)
            for seed in (1, 123456789012345):
                out = MS.solve(CandidateGraph(domain=TF, n=24, edges=tuple(E)), {'solver': name, 'cpu_seconds': 0.3},
                               2, seed)
                self.assertEqual(check_witness(task(24, E), [tuple(e) for e in out['selected']])['value'],
                                 out['value'], name)
                self.assertGreater(out['value'], len(E) // 2, name)        # at least a random cut's share

    def test_failures_are_loud(self):
        k6 = tuple(combinations(range(6), 2))
        with mock.patch.dict(MS.SOLVERS, {'deepdist': dict(MS.SOLVERS['deepdist'], binary='/bin/true')}):
            with self.assertRaises(RuntimeError):
                MS.solve(CandidateGraph(domain=TF, n=6, edges=k6), {'solver': 'deepdist', 'cpu_seconds': 0.1}, 2, 1)
        # a model choosing every edge violates the hard clauses: refused, not returned
        with mock.patch.dict(MS.SOLVERS, {'deepdist': dict(MS.SOLVERS['deepdist'], binary='/bin/echo')}):
            with mock.patch.object(MS, 'parse_model', return_value=set(range(1, len(k6) + 1))):
                with self.assertRaises(RuntimeError) as cm:
                    MS.solve(CandidateGraph(domain=TF, n=6, edges=k6), {'solver': 'deepdist', 'cpu_seconds': 0.1},
                             2, 1)
        self.assertIn('violates a hard clause', str(cm.exception))

    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20268701, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        for name in MS.SOLVERS:
            d = C2.build_descriptor('maxsat-anytime-v1', TF, {'solver': name, 'cpu_seconds': 0.5}, **PROFILE)
            r = C2.run(t, d, seed=987654321987, expected_id=d['descriptor_id'], isolation='runc')
            self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), (name, r))
            self.assertGreater(r['result']['value'], 0, name)
            self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'],
                             r['result']['value'], name)


class MQLibHeuristics(unittest.TestCase):
    def test_the_codes_match_the_binary_and_parameters_are_closed(self):
        import subprocess
        from genesis.candidate_kinds import mqlib as MQ
        listed = subprocess.run([MQ.BINARY, '-l'], capture_output=True, text=True).stdout
        for h in MH.HEURISTICS:
            self.assertIn(h, listed)
        self.assertEqual(len(MH.HEURISTICS), 38)
        self.assertIsNone(MH.check_parameters(TF, {'heuristic': 'PALUBECKIS2004bMST2', 'cpu_seconds': 1}))
        for bad in ({'heuristic': 'X', 'cpu_seconds': 1}, {'heuristic': 'BURER2002'},
                    {'heuristic': 'BURER2002', 'cpu_seconds': 0}):
            self.assertIsNotNone(MH.check_parameters(TF, bad), bad)

    def test_a_non_default_heuristic_runs_and_finds_k10_s_optimum(self):
        k10 = tuple(combinations(range(10), 2))
        for h in ('PALUBECKIS2004bMST2', 'MERZ1999GLS'):
            out = MH.solve(CandidateGraph(domain=TF, n=10, edges=k10), {'heuristic': h, 'cpu_seconds': 0.2}, 2, 5)
            self.assertEqual(out['value'], 25, h)


if __name__ == '__main__':
    unittest.main()
