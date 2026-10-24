"""The graph sense language and the perceptual workspace (Batch R2; fixtures): every primitive against networkx;
type checking and bounds; random senses, mutations and crossovers stay well typed and finite; senses run as research
objects; the workspace records producers, dependencies and missing inputs."""
from pathlib import Path
import random
import sys
import unittest

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import process as P  # noqa: E402
from genesis.objects import core as O  # noqa: E402
from genesis.senses import graph as SG  # noqa: E402
from genesis.senses.workspace import Workspace  # noqa: E402


def graph(seed, n=40, p=0.15):
    rng = random.Random(seed)
    E = [[u, v, rng.choice((1, 1, -1, 2))] for u in range(n) for v in range(u + 1, n) if rng.random() < p]
    return {'n': n, 'edges': E}


class Primitives(unittest.TestCase):
    def test_against_networkx(self):
        for s in range(3):
            g = graph(s)
            G = nx.Graph()
            G.add_nodes_from(range(g['n']))
            G.add_weighted_edges_from(g['edges'])
            ctx = SG.Context(g)
            self.assertEqual(ctx.prim('deg').tolist(), [G.degree(i) for i in range(g['n'])])
            self.assertEqual(ctx.prim('wdeg').tolist(), [G.degree(i, weight='weight') for i in range(g['n'])])
            self.assertEqual(ctx.prim('tri').tolist(), [nx.triangles(G, i) for i in range(g['n'])])
            self.assertTrue(np.allclose(ctx.prim('clust'), [nx.clustering(G, i) for i in range(g['n'])]))
            core = nx.core_number(G)
            self.assertEqual(ctx.prim('core').tolist(), [core[i] for i in range(g['n'])])
            self.assertEqual(ctx.prim('common').tolist(),
                             [len(set(G[u]) & set(G[v])) for u, v, _ in g['edges']])

    def test_evaluation(self):
        g = graph(5)
        deg = SG.Context(g).prim('deg')
        self.assertAlmostEqual(SG.evaluate(['cv_n', 'deg'], g), deg.std() / deg.mean())
        self.assertEqual(SG.evaluate(['frac_pos_e', ['sub_e', 'w', ['ends_min', 'one']]], g),
                         float(np.mean([w - 1 > 0 for _, _, w in g['edges']])))
        self.assertEqual(SG.evaluate(['max_n', 'deg'], {'n': 3, 'edges': []}), 0.0)


class Checking(unittest.TestCase):
    def test_types_and_bounds(self):
        self.assertIsNone(SG.check(['mean_n', ['nbr_mean', 'deg']]))
        self.assertIn('scalar', SG.check(['nbr_mean', 'deg']))
        self.assertIsNotNone(SG.check(['mean_n', 'w']))
        self.assertIsNotNone(SG.check(['mean_n', ['nope', 'deg']]))
        deep = 'deg'
        for _ in range(8):
            deep = ['nbr_mean', deep]
        self.assertIsNotNone(SG.check(['mean_n', deep]))

    def test_search_operators(self):
        rng = random.Random(1)
        g = graph(2)
        trees = [SG.random_sense(rng) for _ in range(60)]
        trees += [SG.mutate(t, rng) for t in trees[:30]] + [SG.crossover(a, b, rng) for a, b in zip(trees, trees[1:31])]
        for t in trees:
            self.assertIsNone(SG.check(t), t)
            self.assertTrue(np.isfinite(SG.evaluate(t, g)))
        self.assertGreater(len({str(t) for t in trees}), 60)


class Objects(unittest.TestCase):
    def test_sense_objects_and_the_workspace(self):
        g = graph(3)
        s1 = O.make('Sense', {'tree': ['cv_n', 'deg']}, 'graph-sense', {'graph': 'Graph'}, {'value': 'Real'},
                    effect='accessibility', post=['finite'], name='degree spread')
        s2 = O.make('Sense', {'tree': ['mean_n', 'clust']}, 'graph-sense', {'graph': 'Graph'}, {'value': 'Real'},
                    effect='accessibility')
        ratio = O.make('Composition', {'expr': {'op': '/', 'a': {'op': 'input', 'name': 'a'},
                                                'b': {'op': 'input', 'name': 'b'}}}, 'expr',
                       {'a': 'Real', 'b': 'Real'}, {'value': 'Real'})
        ws = Workspace(g)
        a = ws.observe('spread', s1, P.Fuel(10))
        b = ws.observe('clustering', s2, P.Fuel(10))
        r = ws.derive('ratio', ratio, {'a': 'spread', 'b': 'clustering'}, P.Fuel(10))
        self.assertAlmostEqual(r, a / b if b else 0.0)
        self.assertEqual(ws.lineage('ratio'), ['clustering', 'instance', 'spread'])
        self.assertEqual(ws.obs['spread']['producer'], O.oid(s1))
        self.assertEqual(ws.missing({'x': 'Real', 'y': 'Distribution'}), {'y': 'Distribution'})
        bad = O.make('Sense', {'tree': ['nbr_mean', 'deg']}, 'graph-sense', {'graph': 'Graph'}, {'value': 'Real'})
        with self.assertRaises(ValueError):
            ws.observe('bad', bad, P.Fuel(10))
        with self.assertRaises(ValueError):
            Workspace({'n': 2, 'edges': [[0, 5]]})


if __name__ == '__main__':
    unittest.main()
