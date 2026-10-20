"""B20_R88: `tfx-v1`, the native population search. The binary is the pinned build of the in-repository source (and
rebuilds to the same bytes), parameters are closed, every configuration returns triangle-free subsets of the host,
optima match brute force, the budget is kept, failures are loud, and a metered runc run returns a checked witness."""
from itertools import combinations
import random
import subprocess
import sys
import time
import unittest
from unittest import mock
from pathlib import Path

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import tfx as T
from genesis.graphs import check_witness
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}
ROOT = Path(__file__).resolve().parents[1]


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


def view(n, E):
    return CandidateGraph(domain=TF, n=n, edges=tuple(E))


def brute(n, E):
    """The largest triangle-free subset by branching on edges (fine for m <= 15)."""
    best = 0

    def rec(i, chosen):
        nonlocal best
        if len(chosen) + len(E) - i <= best:
            return
        if i == len(E):
            best = len(chosen)
            return
        u, v = E[i]
        if not any((min(u, w), max(u, w)) in chosen and (min(v, w), max(v, w)) in chosen for w in range(n)):
            rec(i + 1, chosen | {E[i]})
        rec(i + 1, chosen)
    rec(0, frozenset())
    return best


def random_config(rng):
    return {k: rng.choice(v) for k, v in T.SPACE.items()}


class Pin(unittest.TestCase):
    def test_the_binary_is_the_pinned_build_of_the_source(self):
        self.assertEqual(T.binary_digest(), T.BINARY_SHA256)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/b20r88_build_tfx.py'), '--check'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ident = C2.implementation_identity('tfx-v1')
        self.assertIn('candidate_kinds/tfx.py', ident)
        self.assertIn('candidate_kinds/native/tfx.c', ident)

    def test_a_changed_binary_is_refused(self):
        p = {'cpu_seconds': 1, 'config': dict(T.DEFAULT)}
        self.assertIsNone(T.check_parameters(TF, p))
        with mock.patch.object(T, 'BINARY_SHA256', '0' * 64):
            self.assertIn('not the pinned build', T.check_parameters(TF, p))
            with self.assertRaises(C2.CandidateError):
                C2.build_descriptor('tfx-v1', TF, p, **PROFILE)


class Parameters(unittest.TestCase):
    def test_parameters_are_closed(self):
        good = dict(T.DEFAULT)
        self.assertIsNone(T.check_config(good))
        for k in T.SPACE:
            self.assertIsNotNone(T.check_config({x: y for x, y in good.items() if x != k}), k)
        self.assertIsNotNone(T.check_config(dict(good, extra=1)))
        self.assertIsNotNone(T.check_config(dict(good, K=5)))
        self.assertIsNotNone(T.check_config(dict(good, acc=True)))
        self.assertIsNotNone(T.check_config(dict(good, frac='0.3')))
        for bad in ({}, {'cpu_seconds': 1}, {'config': good}, {'cpu_seconds': 0, 'config': good},
                    {'cpu_seconds': 61, 'config': good}, {'cpu_seconds': True, 'config': good},
                    {'cpu_seconds': 1, 'config': good, 'seed': 3}):
            self.assertIsNotNone(T.check_parameters(TF, bad), bad)
        self.assertIsNotNone(T.check_parameters('c4_host_v2', {'cpu_seconds': 1, 'config': good}))

    def test_every_listed_value_reaches_the_binary(self):
        # the binary refuses unknown keys (exit 2): every key it is given must be one it parses
        rng = random.Random(1)
        for k, values in T.SPACE.items():
            for v in values:
                cfg = dict(T.DEFAULT, **{k: v})
                out = T.solve(view(8, list(combinations(range(8), 2))), {'cpu_seconds': 0.02, 'config': cfg}, 1,
                              rng.randrange(1 << 40))
                self.assertEqual(out['value'], 16, (k, v))       # K8: Turán, 16


class Solving(unittest.TestCase):
    def test_optima_match_brute_force(self):
        rng = random.Random(2)
        hosts = [(5, [(i, (i + 1) % 5) if i < 4 else (0, 4) for i in range(5)]),           # C5: 5
                 (6, [(0, i) for i in range(1, 6)] + [(i, i + 1) for i in range(1, 5)] + [(1, 5)]),  # wheel W5
                 (5, list(combinations(range(5), 2)))]                                     # K5: 6
        for _ in range(6):
            E = [e for e in combinations(range(6), 2) if rng.random() < 0.6]
            hosts.append((6, E))
        configs = [dict(T.DEFAULT)] + [random_config(rng) for _ in range(4)]
        for n, E in hosts:
            E = sorted((min(u, v), max(u, v)) for u, v in E)
            opt = brute(n, E)
            for cfg in configs:
                out = T.solve(view(n, E), {'cpu_seconds': 0.05, 'config': cfg}, 1, rng.randrange(1 << 40))
                self.assertEqual(out['value'], opt, (n, E, cfg))
                self.assertEqual(check_witness(task(n, E), [tuple(e) for e in out['selected']])['value'], opt)

    def test_turan(self):
        for n, opt in ((10, 25), (12, 36)):
            Kn = list(combinations(range(n), 2))
            out = T.solve(view(n, Kn), {'cpu_seconds': 0.1, 'config': dict(T.DEFAULT)}, 1, 7)
            self.assertEqual(out['value'], opt)

    def test_random_configurations_return_checked_witnesses(self):
        rng = random.Random(3)
        for _ in range(40):
            n = rng.randrange(20, 64)
            E = [e for e in combinations(range(n), 2) if rng.random() < rng.choice((0.2, 0.5, 0.8))]
            cfg = random_config(rng)
            out = T.solve(view(n, E), {'cpu_seconds': 0.03, 'config': cfg}, 1, rng.randrange(1 << 62))
            self.assertEqual(check_witness(task(n, E), [tuple(e) for e in out['selected']])['value'], out['value'],
                             cfg)
            self.assertGreaterEqual(out['value'], len(E) // 2, cfg)              # at least a random cut's share

    def test_the_budget_is_kept(self):
        rng = random.Random(4)
        E = [e for e in combinations(range(63), 2) if rng.random() < 0.5]
        for b in (0.05, 0.3):
            t0 = time.monotonic()
            T.solve(view(63, E), {'cpu_seconds': b, 'config': dict(T.DEFAULT, K=16)}, 5, 11)
            self.assertLess(time.monotonic() - t0, b + 0.15)

    def test_failures_are_loud(self):
        k6 = tuple(combinations(range(6), 2))
        with mock.patch.object(T, 'BINARY', '/bin/false'):
            with self.assertRaises(RuntimeError):
                T.solve(view(6, k6), {'cpu_seconds': 0.05, 'config': dict(T.DEFAULT)}, 1, 1)
        r = subprocess.run([T.BINARY, 'nosuchkey=1'], input='3 1 1 10\n0 1\n', capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run([T.BINARY], input='3 2 1 10\n0 1\n0 1\n', capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)                                         # a repeated edge

    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20268801, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = C2.build_descriptor('tfx-v1', TF, {'cpu_seconds': 0.3, 'config': dict(T.DEFAULT)}, **PROFILE)
        r = C2.run(t, d, seed=987654321987, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])
        self.assertGreater(r['result']['value'], 0)


if __name__ == '__main__':
    unittest.main()
