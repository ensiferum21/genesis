"""B20_R27 (s15.3, W10): decompositions. These tests cover the balanced partition, induced part
tasks, the Python composition model against exhaustive checks, witness validity, the obligation
and the bounds."""
import random
import unittest

from genesis.domains import ADAPTERS
from genesis.formal_research import triangle_theory as T
from genesis.graphs import check_witness
from genesis.invention import decompositions as D
from genesis.invention import representations as RP


class Partition(unittest.TestCase):
    def test_balanced_and_no_worse_than_its_start(self):
        rng = random.Random(1)
        n = 30
        E = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < 0.3]
        for m in (2, 3, 4):
            part = D.balanced_partition(n, E, m, random.Random(5))
            sizes = sorted(sum(part[v] == p for v in range(n)) for p in range(m))
            self.assertLessEqual(sizes[-1] - sizes[0], 1)
            start = random.Random(5)
            order = list(range(n)); start.shuffle(order)
            first = {v: i % m for i, v in enumerate(order)}
            self.assertLessEqual(D.cut_size(E, part), D.cut_size(E, first))

    def test_part_task_relabels_the_induced_subgraph(self):
        tasks, _, _ = ADAPTERS['triangle_free_host_v1'].generate(77, 1, 'DEV', 'erdos', {'n': 12, 'p': 0.4})
        t = tasks[0]
        vs = [1, 4, 5, 9]
        sub, back = D.part_task(t, vs, 'p')
        self.assertEqual(sub.n, 4)
        self.assertEqual({(back[u], back[v]) for u, v in sub.edges},
                         {(u, v) for u, v in t.edges if u in vs and v in vs})


class Composition(unittest.TestCase):
    def test_vertex_disjoint_triangle_free_sets_have_a_triangle_free_union(self):
        rng = random.Random(2)
        for _ in range(400):
            vs = list(range(7)); rng.shuffle(vs)
            cut = rng.randrange(1, 7)
            A, B = vs[:cut], vs[cut:]
            S = frozenset((u, v) for u in A for v in A if u != v and rng.random() < 0.4)
            Tt = frozenset((u, v) for u in B for v in B if u != v and rng.random() < 0.4)
            self.assertTrue(D.vertex_disjoint(S, Tt))
            if T.tf(S) and T.tf(Tt):
                self.assertTrue(T.tf(S | Tt))

    def test_overlap_breaks_it(self):
        S, Tt = frozenset({(0, 1), (1, 2)}), frozenset({(0, 2)})
        self.assertFalse(D.vertex_disjoint(S, Tt))
        self.assertFalse(T.tf(S | Tt))

    def test_obligation(self):
        (c,) = D.conjectures()
        self.assertEqual(c['concl'], 'GT.TriangleFree (S ∪ T)')
        self.assertEqual([b['lean'] for b in c['binders'] if b.get('hyp')],
                         ['GT.TriangleFree S', 'GT.TriangleFree T', D.DISJOINT])


class Method(unittest.TestCase):
    def test_valid_witnesses_and_bounds(self):
        tasks, _, _ = ADAPTERS['triangle_free_host_v1'].generate(78, 1, 'DEV', 'erdos', {'n': 24, 'p': 0.3})
        t = tasks[0]
        for m in (2, 3):
            o = D.decompose_and_repair(t, m, cpu_seconds=0.4, seed=1)
            self.assertEqual(check_witness(t, [tuple(e) for e in o['witness']])['value'], o['value'])
            self.assertGreaterEqual(o['value'], o['composed'])
        w = D.whole(t, cpu_seconds=0.4, seed=1)
        self.assertEqual(check_witness(t, [tuple(e) for e in w['witness']])['value'], w['value'])
        with self.assertRaises(RP.ProposalError):
            D.decompose_and_repair(t, D.MAX_PARTS + 1, cpu_seconds=0.1)
        self.assertEqual(D.proposal(3)['id'], 'decomp_3')


if __name__ == '__main__':
    unittest.main()
