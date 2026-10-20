"""B20_R94: the DEV-only large triangle-free domain, its checker and bound, and the kinds that declare it (tfxw-v1,
maxsat-anytime-large-v1). Large tasks are a separate model, so no n <= 63 code can receive one."""
from itertools import combinations
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import domains as DM, graphs_large as GL                                     # noqa: E402
from genesis.models import GraphTask                                                     # noqa: E402
from genesis.models_large import LargeCandidateGraph, LargeGraphTask                      # noqa: E402
from genesis.candidate_kinds import maxsat_large as ML, tfx as T, tfxw as TW              # noqa: E402

LARGE = 'triangle_free_large_v1'


def rand_task(n, p, seed, tid='t'):
    rng = random.Random(seed)
    E = tuple((u, v) for u, v in combinations(range(n), 2) if rng.random() < p)
    return LargeGraphTask(task_id=tid, n=n, edges=E, family='test')


def brute_optimum(task):
    best = 0
    E = task.edges
    for mask in range(1 << len(E)):
        es = [E[i] for i in range(len(E)) if mask >> i & 1]
        if len(es) > best and not GL.has_triangle_bitsets(task.n, es):
            best = len(es)
    return best


class Models(unittest.TestCase):
    def test_a_separate_model_with_its_own_cap(self):
        t = rand_task(200, 0.05, 1)
        self.assertEqual(t.domain, LARGE)
        with self.assertRaises(Exception):
            LargeGraphTask(task_id='x', n=1024, edges=(), family='f')
        with self.assertRaises(Exception):
            LargeGraphTask(task_id='x', n=5, edges=((1, 2), (0, 1)), family='f')
        with self.assertRaises(Exception):
            LargeGraphTask(task_id='x', n=5, edges=(), family='f', split='CONFIRM')
        with self.assertRaises(Exception):                                     # the small model is unchanged
            GraphTask(task_id='x', domain='triangle_free_host_v1', n=64, edges=(), family='f')
        with self.assertRaises(Exception):
            GraphTask(task_id='x', domain=LARGE, n=10, edges=(), family='f')
        small = DM.ADAPTERS['triangle_free_host_v1']
        self.assertEqual(small.parse(t.model_dump(mode='json')).status, 'UNSUPPORTED')

    def test_the_sealed_registry_is_unchanged(self):
        self.assertEqual(sorted(DM.ADAPTERS), ['c4_host_v2', 'triangle_free_host_v1'])
        self.assertIs(DM.adapter(LARGE), DM.DEV_ADAPTERS[LARGE])
        self.assertFalse(DM.adapter(LARGE).contract()['sealed'])


class Checker(unittest.TestCase):
    def test_both_predicates_agree_with_brute_force(self):
        for seed in range(40):
            t = rand_task(9, 0.5, seed)
            rng = random.Random(seed)
            es = [e for e in t.edges if rng.random() < 0.6]
            brute = any({(a, b), (a, c), (b, c)} <= set(es) for a, b, c in combinations(range(9), 3))
            self.assertEqual(GL.has_triangle_merge(9, es), brute)
            self.assertEqual(GL.has_triangle_bitsets(9, es), brute)

    def test_witness_checks(self):
        t = LargeGraphTask(task_id='k4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='f')
        self.assertEqual(GL.check_witness(t, [(0, 1), (1, 2), (2, 3), (0, 3)])['value'], 4)
        for bad in ([(0, 1), (1, 2), (0, 2)], [(0, 1), (0, 1)], [(0, 9)], [(1, 1)]):
            with self.assertRaises(ValueError):
                GL.check_witness(t, bad)
        a = DM.adapter(LARGE)
        self.assertEqual(a.validate(t, [(0, 1), (1, 2), (0, 2)])['status'], 'INVALID')
        self.assertEqual(a.validate(t, [[0, 1], [2, 3]])['status'], 'VALID')
        big = rand_task(600, 0.02, 3)
        self.assertEqual(a.validate(big, [])['value'], 0)


class Bound(unittest.TestCase):
    def test_the_packing_bound_is_valid_and_rechecked(self):
        for seed in range(12):
            t = rand_task(7, 0.6, seed)
            b = GL.triangle_packing_bound(t)
            self.assertEqual(GL.check_packing(t, b['packing']), b['upper'])
            self.assertGreaterEqual(b['upper'], brute_optimum(t))
        t = LargeGraphTask(task_id='k4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='f')
        for bad in ([[0, 1, 2], [0, 1, 3]], [[0, 1, 1]], [[0, 1]]):
            with self.assertRaises(ValueError):
                GL.check_packing(t, bad)
        t2 = LargeGraphTask(task_id='p', n=4, edges=((0, 1), (1, 2), (2, 3)), family='f')
        with self.assertRaises(ValueError):
            GL.check_packing(t2, [[0, 1, 2]])
        self.assertEqual(DM.adapter(LARGE).upper_bound(t)['upper'], 5)


class Identity(unittest.TestCase):
    def test_colour_refinement_is_an_invariant(self):
        t = rand_task(80, 0.1, 5)
        perm = list(range(80))
        random.Random(9).shuffle(perm)
        relabelled = sorted(tuple(sorted((perm[u], perm[v]))) for u, v in t.edges)
        self.assertEqual(GL.wl_identity(80, t.edges), GL.wl_identity(80, relabelled))
        other = rand_task(80, 0.1, 6)
        self.assertNotEqual(GL.wl_identity(80, t.edges), GL.wl_identity(80, other.edges))


class Adapter(unittest.TestCase):
    def test_generation_is_dev_only_distinct_and_seeded(self):
        a = DM.adapter(LARGE)
        out, seen, _ = a.generate(7, 3, 'DEV', 'planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06})
        self.assertEqual(len({x.task_id for x in out}), 3)
        self.assertEqual(len(seen), 3)
        again, _, _ = a.generate(7, 3, 'DEV', 'planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06})
        self.assertEqual([x.edges for x in out], [x.edges for x in again])
        fresh, _, _ = a.generate(7, 3, 'DEV', 'planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06},
                                 excluded=seen)
        self.assertFalse({a.exposure_identity(x)['canonical'] for x in fresh} & seen)   # earlier hosts excluded
        with self.assertRaises(ValueError):
            a.generate(7, 1, 'CONFIRM', 'erdos', {'n': 100, 'p': 0.1})
        with self.assertRaises(ValueError):
            a.generate(7, 1, 'DEV', 'erdos', {'n': 40, 'p': 0.1})

    def test_view_and_purposes(self):
        a = DM.adapter(LARGE)
        t = rand_task(100, 0.05, 2, tid='SECRET-id')
        v = a.candidate_view(t)
        self.assertIsInstance(v, LargeCandidateGraph)
        self.assertNotIn('SECRET', v.model_dump_json())
        self.assertIsNone(a.supports(t, 'execute'))
        self.assertEqual(a.supports(t, 'exact_reference').status, 'UNSUPPORTED')
        self.assertEqual(a.reference(t).status, 'UNSUPPORTED')


class Kinds(unittest.TestCase):
    def test_tfxw_parameters(self):
        p = {'cpu_seconds': 1.0, 'config': dict(TW.DEFAULT)}
        self.assertEqual(set(TW.SPACE), set(T.SPACE) | {'kpick'})
        self.assertIn('config', TW.check_parameters(LARGE, dict(p, config=dict(T.DEFAULT))))
        self.assertIn('supports', TW.check_parameters('c4_host_v2', p))
        bad = dict(p, config=dict(TW.DEFAULT, K=99))
        self.assertIn('config', TW.check_parameters(LARGE, bad))
        self.assertIn('cpu_seconds', TW.check_parameters(LARGE, dict(p, cpu_seconds=601)))
        self.assertEqual(TW.FILES[0], 'candidate_kinds/tfxw.py')

    def test_maxsat_large_parameters(self):
        self.assertEqual(len(ML.SOLVERS), 13)
        self.assertIn('supports', ML.check_parameters('triangle_free_host_v1', {'solver': 'deepdist',
                                                                                'cpu_seconds': 1}))
        self.assertIn('solver must be', ML.check_parameters(LARGE, {'solver': 'x', 'cpu_seconds': 1}))
        self.assertEqual(ML.FILES[0], 'candidate_kinds/maxsat_large.py')


if __name__ == '__main__':
    unittest.main()
