"""B20_R101: the DEV-only weighted max-cut domain, the pinned Gset benchmark and its first two kinds.

Reading `.rud` files strictly; two independent cut computations against brute force; the adapter (views, refusals,
generated families, isomorphism-invariant identity); the pinned Gset data (archive and every member, published sizes,
families, best-known values with their sources); the runner (descriptors, refusals, runs in the sandbox with checked
witnesses) and the kinds `mqlib-maxcut-v1` and `dsb-maxcut-v1` (optimal on small graphs)."""
from itertools import product
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import candidates_maxcut as CM  # noqa: E402
from genesis import gset as GS  # noqa: E402
from genesis import graphs_maxcut as GM  # noqa: E402
from genesis.domains import adapter  # noqa: E402
from genesis.models_maxcut import MaxCutTask  # noqa: E402

A = adapter('maxcut_v1')


def rand_task(n, p, seed, pm=True, tid='t'):
    rng = random.Random(seed)
    edges = tuple((u, v, rng.choice((-1, 1)) if pm else 1) for u in range(n) for v in range(u + 1, n) if rng.random() < p)
    return MaxCutTask(task_id=tid, n=n, edges=edges, family='test')


def brute(task):
    best = None
    for bits in product('01', repeat=task.n - 1):
        side = '0' + ''.join(bits)
        v = GM.cut_edge_driven(task.edges, side)
        best = v if best is None or v > best else best
    return best


class Reading(unittest.TestCase):
    def test_rud(self):
        n, e = GM.parse_rud('3 2\r\n1 2 1\r\n3 2 -1\r\n')
        self.assertEqual((n, e), (3, ((0, 1, 1), (1, 2, -1))))
        for bad in ('3 2\n1 2 1\n', '3 1\n1 1 1\n', '3 2\n1 2 1\n2 1 1\n', '3 1\n1 4 1\n', '3 1\n1 2 0\n', '3\n'):
            with self.assertRaises(ValueError, msg=bad):
                GM.parse_rud(bad)

    def test_models_refuse_malformed_graphs(self):
        for edges in (((1, 0, 1),), ((0, 1, 0),), ((0, 2, 1), (0, 1, 1)), ((0, 1, 1), (0, 1, -1))):
            with self.assertRaises(ValueError):
                MaxCutTask(task_id='x', n=3, edges=edges, family='f')


class Checking(unittest.TestCase):
    def test_two_computations_agree_and_match_brute_force(self):
        for seed in range(30):
            t = rand_task(9, 0.5, seed)
            rng = random.Random(seed)
            for _ in range(5):
                side = ''.join(rng.choice('01') for _ in range(t.n))
                self.assertEqual(GM.cut_edge_driven(t.edges, side), GM.cut_vertex_driven(t.n, t.edges, side))
            best = brute(t)
            self.assertEqual(max(A.validate(t, '0' + ''.join(b))['value'] for b in product('01', repeat=8)), best)

    def test_validate(self):
        t = rand_task(6, 0.8, 1)
        self.assertEqual(A.validate(t, '010101')['status'], 'VALID')
        for bad in ('0101', '01010x', 101010, None):
            self.assertEqual(A.validate(t, bad)['status'], 'INVALID')

    def test_identity_is_isomorphism_invariant(self):
        t = rand_task(12, 0.4, 7)
        perm = list(range(12))
        random.Random(3).shuffle(perm)
        e2 = tuple(sorted((min(perm[u], perm[v]), max(perm[u], perm[v]), w) for u, v, w in t.edges))
        t2 = MaxCutTask(task_id='y', n=12, edges=e2, family='f')
        self.assertEqual(A.exposure_identity(t), A.exposure_identity(t2))
        e3 = tuple((u, v, -w) if i == 0 else (u, v, w) for i, (u, v, w) in enumerate(t.edges))
        self.assertNotEqual(A.exposure_identity(t)['canonical'],
                            A.exposure_identity(MaxCutTask(task_id='z', n=12, edges=e3, family='f'))['canonical'])


class Adapter(unittest.TestCase):
    def test_purposes_and_views(self):
        t = rand_task(8, 0.5, 2)
        self.assertIsNone(A.supports(t, 'execute'))
        self.assertIsNotNone(A.supports(t, 'exact_reference'))
        self.assertEqual(A.candidate_view(t).edges, t.edges)
        self.assertNotIn('task_id', A.candidate_view(t).model_dump())
        self.assertFalse(A.SEALED)

    def test_generated_families(self):
        ts, seen, _ = A.generate(5, 3, 'DEV', 'torus_pm1', {'side': 6})
        self.assertEqual([t.n for t in ts], [36] * 3)
        self.assertTrue(all(len(t.edges) == 72 for t in ts))
        self.assertEqual(len({A.exposure_identity(t)['canonical'] for t in ts}), 3)
        ts2, _, _ = A.generate(5, 2, 'DEV', 'erdos_pm1', {'n': 40, 'p': 0.2}, excluded=seen)
        self.assertEqual(len(ts2), 2)
        with self.assertRaises(ValueError):
            A.generate(5, 1, 'DEV', 'torus_pm1', {'side': 2})


class Gset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = GS.tasks()

    def test_the_pinned_benchmark(self):
        self.assertEqual([t.task_id for t in self.tasks], [f'gset-G{k}' for k in range(1, 55)])
        size = {t.task_id: (t.n, len(t.edges)) for t in self.tasks}
        published = {1: (800, 19176), 11: (800, 1600), 14: (800, 4694), 15: (800, 4661), 22: (2000, 19990),
                     32: (2000, 4000), 35: (2000, 11778), 43: (1000, 9990), 48: (3000, 6000), 51: (1000, 5909),
                     54: (1000, 5916)}
        for k, s in published.items():
            self.assertEqual(size[f'gset-G{k}'], s, k)
        fam = {t.task_id: t.family for t in self.tasks}
        self.assertEqual((fam['gset-G1'], fam['gset-G11'], fam['gset-G18'], fam['gset-G48']),
                         ('gset-random-1', 'gset-toroidal-pm1', 'gset-planar-pm1', 'gset-toroidal-1'))

    def test_best_known_values_and_sources(self):
        import json
        bk = GS.best_known()
        doc = json.loads((GS.DATA / 'best_known.json').read_text())
        self.assertEqual(sorted(bk, key=lambda g: int(g[1:])), [f'G{k}' for k in range(1, 55)])
        self.assertEqual((bk['G1'], bk['G14'], bk['G22'], bk['G27'], bk['G39'], bk['G54']),
                         (11624, 3064, 13359, 3341, 2408, 3852))
        # B20_R104: the BLS paper's Table 2 (Daniel's PDF, 23 Oct 2026) raised 20 values, e.g. the tori G32-G34
        self.assertEqual((bk['G23'], bk['G30'], bk['G32'], bk['G34'], bk['G43']), (13344, 3413, 1410, 1384, 6660))
        # and MACUT's Table 1 (Daniel's PDF, 23 Oct 2026) raised three planar ones
        self.assertEqual((bk['G35'], bk['G36'], bk['G37']), (7686, 7679, 7690))
        self.assertEqual(sum('macut2012_paper' in v['sources'] for v in doc['instances'].values()), 24)
        for g, v in doc['instances'].items():
            self.assertEqual(v['best_known'], max(v['sources'].values()), g)
            self.assertEqual(v['from'], sorted(k for k, x in v['sources'].items() if x == v['best_known']), g)
            self.assertGreaterEqual(v['best_known'], v['sources']['optsicom2009'], g)
            self.assertGreaterEqual(v['sources']['bls2013_paper'], v['sources']['before_bls2013'], g)
            self.assertTrue(set(v['sources']) <= set(doc['sources']), g)
        self.assertIn('never as a record', doc['policy'])
        # 24 Oct 2026: B20_R123's 7688 on G38 was already in the max-bisection literature (Wu and Hao 2013)
        self.assertEqual((bk['G38'], doc['instances']['G38']['from']), (7688, ['wuhao2013_bisection']))
        before = GS.best_known(as_of='2026-10-24T12:00:00+08:00')
        self.assertEqual(before['G38'], 7687)
        self.assertEqual({g for g in bk if bk[g] != before[g]}, {'G38'})
        self.assertTrue(all('added' in s for s in doc['sources'].values()))

    def test_only_set_one_instances(self):
        with self.assertRaises(ValueError):
            GS.tasks([55])

    def test_a_tampered_archive_is_refused(self):
        from unittest import mock
        man = GS.manifest()
        with mock.patch.object(GS, 'manifest', return_value=dict(man, archive_sha256='0' * 64)):
            with self.assertRaises(ValueError):
                GS.tasks([1])


class Runner(unittest.TestCase):
    def test_descriptors_and_refusals(self):
        d = CM.build_descriptor('dsb-maxcut-v1', {'cpu_seconds': 1.0}, cpu_seconds=1.0)
        self.assertEqual(CM.descriptor_problems(d), [])
        m = CM.build_descriptor('mqlib-maxcut-v1', {'heuristic': 'BURER2002', 'cpu_seconds': 1.0}, cpu_seconds=1.0)
        self.assertIn('candidate_kinds/mqlib.py', m['implementation'])
        bad = dict(d, parameters={'cpu_seconds': 2.0})
        self.assertIn('descriptor_id does not match the descriptor', CM.descriptor_problems(bad))
        from genesis import candidates_v2 as V2
        with self.assertRaises(V2.CandidateError):
            CM.build_descriptor('tfxw-v1', {'cpu_seconds': 1.0}, cpu_seconds=1.0)
        with self.assertRaises(V2.CandidateError):
            CM.build_descriptor('mqlib-maxcut-v1', {'heuristic': 'NOPE', 'cpu_seconds': 1.0}, cpu_seconds=1.0)
        self.assertEqual(CM.run(rand_task(5, 0.5, 1), bad, seed=1)['status'], 'REFUSED')

    def test_both_kinds_run_in_the_sandbox_and_reach_small_optima(self):
        t = rand_task(16, 0.4, 11)
        opt = brute(t)
        for kind, params in (('dsb-maxcut-v1', {'cpu_seconds': 1.0}),
                             ('mqlib-maxcut-v1', {'heuristic': 'BURER2002', 'cpu_seconds': 1.0})):
            d = CM.build_descriptor(kind, params, cpu_seconds=1.0)
            r = CM.run(t, d, seed=987654321, expected_id=d['descriptor_id'], isolation='runc')
            self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), (kind, r))
            self.assertEqual(r['check']['status'], 'VALID')
            self.assertEqual(r['result']['value'], opt, kind)

    def test_a_gset_instance_runs(self):
        t = GS.tasks([11])[0]
        d = CM.build_descriptor('mqlib-maxcut-v1', {'heuristic': 'BURER2002', 'cpu_seconds': 2.0}, cpu_seconds=2.0)
        r = CM.run(t, d, seed=1, isolation='runc')
        self.assertEqual(r['status'], 'SUCCESS', r)
        self.assertGreater(r['result']['value'], 0.95 * GS.best_known()['G11'])
        self.assertLessEqual(r['result']['value'], 627)          # OPTSICOM's upper bound for G11


if __name__ == '__main__':
    unittest.main()
