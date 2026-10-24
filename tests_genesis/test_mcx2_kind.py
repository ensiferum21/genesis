"""B20_R125: `mcx2-v1`, the max-cut engine as an interpreter of search programs over physics operators (engineering).

The binary is rebuilt from the in-repository source and equals the pin; programs and configurations are data,
refused outside their grammar and space by both the kind and the binary; every operator, alone and mixed, reaches
the optimum of small graphs (brute force) with the printed cut the checked one, at one and at several levels; the
builder's hybrid is the default; it runs in the sandbox; the runner admits it as a max-cut kind. No test runs mcx2 on
Gset."""
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
from genesis.candidate_kinds import mcx2 as K  # noqa: E402
from genesis.models_maxcut import MaxCutCandidateView, MaxCutTask  # noqa: E402
import b20r125_build_mcx2 as B  # noqa: E402


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
        ok = '2 1 1 10\n0 1 1\n'
        for prog in ('', 'X', 'B0', 'B', 'Q1', 'B1 S', 'B1X', 'B' + '9' * 10, ' '.join(['B1'] * 33), 'B1 D2', 'L'):
            self.assertEqual(raw(ok, '-prog', prog).returncode, 2, prog)
        for opt, val in (('-levels', '0'), ('-levels', '9'), ('-tmax', '0'), ('-L0hot', '2'), ('-pert', '3')):
            self.assertEqual(raw(ok, opt, val).returncode, 2, opt)
        self.assertEqual(raw('2 1 1 10\n0 0 1\n').returncode, 2)
        self.assertEqual(raw('3 2 1 10\n0 1 10000000\n0 2 10000000\n').returncode, 3)

    def test_default_program_and_output(self):
        r = raw('4 5 7 50\n0 1 1\n1 2 1\n2 3 1\n0 3 1\n0 2 -1\n')
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.split('\n')
        self.assertEqual(lines[0], 'o 4')
        self.assertIn(lines[1], ('v 0101', 'v 1010'))


class Kind(unittest.TestCase):
    def test_grammar(self):
        self.assertEqual(K.statements('B100 X I S2000 C'), [('B', 100), ('X', None), ('I', None), ('S', 2000), ('C', None)])
        self.assertEqual(K.render(K.statements('b5 P3 M')), 'b5 P3 M')
        for bad in ('', 'X I', 'B0', 'B100000000', 'S0 B1', 'B1 X3', 'P B1', 'Z1 B1', ' '.join(['B1'] * 33), 7, 'B1 D2', 'B1 L1'):
            with self.assertRaises(ValueError, msg=bad):
                K.statements(bad)

    def test_configuration_is_data(self):
        self.assertIsNone(K.check_config(K.DEFAULT))
        self.assertIsNone(K.check_parameters('maxcut_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        self.assertEqual((K.DEFAULT['prog'], K.DEFAULT['levels']), ('B100 X I S2000 C', 4))   # the builder's hybrid
        self.assertIn('canonical', K.check_config(dict(K.DEFAULT, prog='B100  X')))
        self.assertIn('prog', K.check_config(dict(K.DEFAULT, prog='X')))
        self.assertIn('levels', K.check_config(dict(K.DEFAULT, levels=5)))
        self.assertIn('pert', K.check_config(dict(K.DEFAULT, pert=True)))
        self.assertIsNotNone(K.check_config({k: v for k, v in K.DEFAULT.items() if k != 'tmax'}))
        self.assertIsNotNone(K.check_parameters('triangle_free_large_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        with mock.patch.object(K, 'BINARY_SHA256', '0' * 64):
            self.assertIn('pinned', K.check_parameters('maxcut_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        self.assertEqual(K.arguments(K.DEFAULT)[:4], ['-prog', 'B100 X I S2000 C', '-levels', '4'])

    def test_every_operator_reaches_small_optima(self):
        progs = ('B100 X I S2000 C', 'B1', 'b5 X I', 'B10 S50 M', 'B10 P3 H S20 R', 'B3 C', 'b1 I I X S5 C P2 M',
                 'b2 D', 'B5 L', 'B3 S10 L D X I')
        for seed in range(5):
            t = rand_task(10 + seed, 0.5, seed, weights=(-2, -1, 1, 3))
            opt = brute(t)
            view = MaxCutCandidateView(n=t.n, edges=t.edges)
            for prog, levels in product(progs, (1, 3)):
                cfg = dict(K.DEFAULT, prog=prog, levels=levels, pool=4)
                out = K.solve(view, {'cpu_seconds': 0.05, 'config': cfg}, 0.05, seed)
                self.assertEqual(out['value'], opt, (seed, prog, levels))
                self.assertEqual(GM.cut_edge_driven(t.edges, out['side']), opt)

    def test_runs_in_the_sandbox(self):
        t = rand_task(16, 0.4, 11)
        d = CM.build_descriptor('mcx2-v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}, cpu_seconds=1.0)
        self.assertIn('candidate_kinds/native/mcx2.c', d['implementation'])
        r = CM.run(t, d, seed=987654321, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(r['result']['value'], brute(t))
        self.assertLess(r['cpu_ns'], 1.6e9)

    def test_membership(self):
        self.assertTrue(CM.is_maxcut_kind('mcx2-v1'))


if __name__ == '__main__':
    unittest.main()
