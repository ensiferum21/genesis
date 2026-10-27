"""B20_R104: `mcx-v1`, Genesis's max-cut engine, and the planar graph families (engineering).

The binary is rebuilt from the in-repository source and equals the pin; the configuration is data and is refused
outside its space; every restart mode reaches the optimum of small graphs (brute force) and the printed cut is the
checked one; malformed input and over-large weights are refused by the binary; the runner admits exactly the kinds
that declare the max-cut domain; the planar families are unions of two planar layers, deterministic per seed.
No test runs mcx on Gset (Gset is B20_R106's test set)."""
from itertools import product
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import candidates_maxcut as CM  # noqa: E402
from genesis import graphs_maxcut as GM  # noqa: E402
from genesis.candidate_kinds import mcx as K  # noqa: E402
from genesis.domains import adapter  # noqa: E402
from genesis.models_maxcut import MaxCutCandidateView, MaxCutTask  # noqa: E402
import b20r104_build_mcx as B  # noqa: E402

A = adapter('maxcut_v1')


def rand_task(n, p, seed, weights=(-1, 1)):
    rng = random.Random(seed)
    edges = tuple((u, v, rng.choice(weights)) for u in range(n) for v in range(u + 1, n) if rng.random() < p)
    return MaxCutTask(task_id=f't{seed}', n=n, edges=edges, family='test')


def brute(task):
    return max(GM.cut_edge_driven(task.edges, '0' + ''.join(bits)) for bits in product('01', repeat=task.n - 1))


def raw(text, *args):
    return subprocess.run([K.BINARY, *args], input=text, capture_output=True, text=True, timeout=30)


class Binary(unittest.TestCase):
    def test_the_build_is_deterministic_and_pinned(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            a, b = B.build(Path(d) / 'a'), B.build(Path(d) / 'b')
        self.assertEqual(a, b)
        self.assertEqual(a, K.BINARY_SHA256)
        self.assertEqual(K.binary_digest(), K.BINARY_SHA256)

    def test_refusals(self):
        self.assertEqual(raw('2 1 1 10\n0 1 1\n', '-rs', '4').returncode, 2)
        self.assertEqual(raw('2 1 1 10\n0 1 1\n', '-pert', '3').returncode, 2)
        self.assertEqual(raw('2 1 1 10\n0 1 1\n', '-pool', '1').returncode, 2)
        self.assertEqual(raw('2 1 1 10\n0 1 1\n', '-L0').returncode, 2)
        for bad in ('2 1 1 10\n0 0 1\n', '2 1 1 10\n0 2 1\n', '2 1 1 10\n0 1 0\n', '2 2 1 10\n0 1 1\n', '2 1 1 0\n0 1 1\n'):
            self.assertEqual(raw(bad).returncode, 2, bad)
        self.assertEqual(raw('3 2 1 10\n0 1 10000000\n0 2 10000000\n').returncode, 3)   # weighted degree 2e7 > 2^24

    def test_output(self):
        r = raw('4 5 7 50\n0 1 1\n1 2 1\n2 3 1\n0 3 1\n0 2 -1\n')
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.split('\n')
        self.assertEqual(lines[0], 'o 4')
        self.assertIn(lines[1], ('v 0101', 'v 1010'))


class Kind(unittest.TestCase):
    def test_configuration_is_data(self):
        self.assertIsNone(K.check_config(K.DEFAULT))
        self.assertIsNone(K.check_parameters('maxcut_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        self.assertIn('rs', K.check_config(dict(K.DEFAULT, rs=4)))
        self.assertIn('pert', K.check_config(dict(K.DEFAULT, pert=True)))
        self.assertEqual((K.DEFAULT['rs'], K.DEFAULT['pert'], K.DEFAULT['P'], K.DEFAULT['L0'], K.DEFAULT['tt']),
                         (0, 2, 0.8, 0.01, 10))                          # breakout local search's published setting
        self.assertEqual(K.arguments(K.DEFAULT), ['-L0', '0.01', '-P', '0.8', '-tt', '10', '-pool', '8', '-restart',
                                                  '2000', '-rs', '0', '-pert', '2'])
        self.assertIsNotNone(K.check_config({k: v for k, v in K.DEFAULT.items() if k != 'rs'}))
        self.assertIsNotNone(K.check_parameters('triangle_free_large_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        self.assertIsNotNone(K.check_parameters('maxcut_v1', {'cpu_seconds': 0, 'config': K.DEFAULT}))
        with mock.patch.object(K, 'BINARY_SHA256', '0' * 64):
            self.assertIn('pinned', K.check_parameters('maxcut_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))

    def test_every_restart_mode_reaches_small_optima(self):
        for seed in range(6):
            t = rand_task(11 + seed, 0.5, seed, weights=(-2, -1, 1, 3))
            opt = brute(t)
            view = MaxCutCandidateView(n=t.n, edges=t.edges)
            for rs, pert in product((0, 1, 2, 3), (0, 1, 2)):
                cfg = dict(K.DEFAULT, rs=rs, pert=pert, pool=4, restart=2000)
                out = K.solve(view, {'cpu_seconds': 0.05, 'config': cfg}, 0.05, seed)
                self.assertEqual(out['value'], opt, (seed, rs, pert))
                self.assertEqual(GM.cut_edge_driven(t.edges, out['side']), opt)

    def test_runs_in_the_sandbox(self):
        t = rand_task(16, 0.4, 11)
        d = CM.build_descriptor('mcx-v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}, cpu_seconds=1.0)
        self.assertIn('candidate_kinds/native/mcx.c', d['implementation'])
        r = CM.run(t, d, seed=987654321, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(r['result']['value'], brute(t))
        self.assertLess(r['cpu_ns'], 1.6e9)

    def test_a_large_generated_graph(self):
        t = A.generate(20271001, 1, 'DEV', 'erdos_pm1', {'n': 3000, 'p': 0.004})[0][0]
        d = CM.build_descriptor('mcx-v1', {'cpu_seconds': 1.0, 'config': dict(K.DEFAULT, rs=2)}, cpu_seconds=1.0)
        r = CM.run(t, d, seed=5, isolation='process')
        self.assertEqual(r['status'], 'SUCCESS', r)
        self.assertEqual(r['check']['status'], 'VALID')


class Runner(unittest.TestCase):
    def test_membership_is_the_declared_domain(self):
        self.assertEqual(set(CM.maxcut_kinds()), {'mqlib-maxcut-v1', 'dsb-maxcut-v1', 'mcx-v1', 'mcx2-v1', 'mcx3-v1'})
        for kind in ('tfxw-v1', 'mqlib-v1', 'nope', None, 3):
            self.assertFalse(CM.is_maxcut_kind(kind), kind)


class PlanarFamilies(unittest.TestCase):
    def test_union_of_two_planar_layers(self):
        for fam in ('planar2', 'planar2_pm1'):
            ts, _, _ = A.generate(20271002, 3, 'DEV', fam, {'n': 200, 'density': 1.0})
            for t in ts:
                m = len(t.edges)
                self.assertLessEqual(m, 2 * (3 * t.n - 6))
                self.assertGreater(m, 1.6 * (3 * t.n - 6))           # two maximal layers, little overlap
                deg = [0] * t.n
                for u, v, _ in t.edges:
                    deg[u] += 1
                    deg[v] += 1
                self.assertEqual(max(deg), max(deg[:12]))            # the hubs are early vertices, as in Gset
                self.assertEqual({w for *_, w in t.edges}, {1} if fam == 'planar2' else {-1, 1})
            again, _, _ = A.generate(20271002, 3, 'DEV', fam, {'n': 200, 'density': 1.0})
            self.assertEqual([t.edges for t in ts], [t.edges for t in again])
        sparse = A.generate(20271002, 1, 'DEV', 'planar2', {'n': 400, 'density': 0.5})[0][0]
        self.assertLess(len(sparse.edges), 1.2 * (3 * 400 - 6))
        with self.assertRaises(ValueError):
            A.generate(1, 1, 'DEV', 'planar2', {'n': 200, 'density': 0.01})

    def test_tori_are_numbered_as_gset_s(self):
        t = A.generate(20271003, 1, 'DEV', 'torus2d', {'rows': 100, 'cols': 8})[0][0]
        self.assertEqual((t.n, len(t.edges), {w for *_, w in t.edges}), (800, 1600, {1}))
        self.assertEqual(sorted({v for u, v, _ in t.edges if u == 0}), [1, 7, 8, 792])     # as G11's vertex 0
        odd = A.generate(20271003, 1, 'DEV', 'torus2d_pm1', {'rows': 25, 'cols': 120})[0][0]
        self.assertEqual((odd.n, len(odd.edges), {w for *_, w in odd.edges}), (3000, 6000, {-1, 1}))

    def test_each_layer_is_planar(self):
        import networkx as nx
        full = A._planar_layer(random.Random(3), 300, 1.0)
        self.assertEqual(len(full), 3 * 300 - 6)                      # maximal planar
        for density in (1.0, 0.5):
            layer = A._planar_layer(random.Random(3), 300, density)
            self.assertTrue(nx.check_planarity(nx.Graph(sorted(layer)))[0])
            self.assertTrue(all(0 <= u < v < 300 for u, v in layer))
            self.assertLessEqual(len(layer), density * 3 * 298)


if __name__ == '__main__':
    unittest.main()
