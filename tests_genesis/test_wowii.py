"""F6 groundwork for the proving test (`docs/OMEGA_FRONTIER.md` §7b): the exact invariants of the transfer family
(research plane, `conjecture/invariants.py`) and the transcribed Graffiti.pc statements with their statuses (kernel
side, `conjecture/wowii.py`)."""
from fractions import Fraction
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.conjecture import invariants as I  # noqa: E402
from genesis.conjecture import wowii as W  # noqa: E402

try:
    import networkx as nx
except ImportError:                                # pragma: no cover
    nx = None


def petersen():
    return I.Graph(10, [(i, (i + 1) % 5) for i in range(5)] + [(5 + i, 5 + (i + 2) % 5) for i in range(5)]
                   + [(i, i + 5) for i in range(5)])


def random_graph(rng, n, p):
    return I.Graph(n, [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p])


def connected_atlas(max_n):
    out = []
    for H in nx.graph_atlas_g():
        if 2 <= H.number_of_nodes() <= max_n and nx.is_connected(H):
            out.append(I.Graph(H.number_of_nodes(), list(H.edges())))
    return out


class Invariants(unittest.TestCase):
    def test_petersen(self):
        G = petersen()
        got = {'indep_num': I.indep_num(G), 'girth': I.girth(G), 'diameter': I.diameter(G), 'radius': I.radius(G),
               'matching_number': I.matching_number(G), 'b': I.b(G), 'forest': I.largest_induced_forest(G),
               'tree': I.largest_induced_tree(G), 'path': I.path_number(G), 'ls': I.ls(G),
               'domination': I.domination_number(G), 'residue': I.residue(G), 'spanning_paths': I.min_spanning_paths(G),
               'hamiltonian_path': I.hamiltonian_path(G)}
        self.assertEqual(got, {'indep_num': 4, 'girth': 5, 'diameter': 2, 'radius': 2, 'matching_number': 5, 'b': 7,
                               'forest': 7, 'tree': 7, 'path': 5, 'ls': 6, 'domination': 3, 'residue': 3,
                               'spanning_paths': 1, 'hamiltonian_path': True})

    def test_the_independence_branching_matches_brute_force(self):
        rng = random.Random(5)
        for _ in range(250):
            n = rng.randint(1, 12)
            G = random_graph(rng, n, rng.random())
            S = rng.getrandbits(n)
            self.assertEqual(I.indep_num_within(G, S), I._indep_brute(G, S))
            self.assertEqual(I.indep_num(G), I._indep_brute(G, G.full))

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_against_networkx(self):
        rng = random.Random(11)
        done = 0
        while done < 120:
            n = rng.randint(2, 10)
            G = random_graph(rng, n, rng.uniform(0.2, 0.8))
            if not G.connected():
                continue
            H = nx.Graph()
            H.add_nodes_from(range(n))
            H.add_edges_from(G.edges)
            self.assertEqual(I.indep_num(G), len(max(nx.find_cliques(nx.complement(H)), key=len)))
            self.assertEqual(I.radius(G), nx.radius(H))
            self.assertEqual(I.diameter(G), nx.diameter(H))
            g = nx.girth(H)
            self.assertEqual(I.girth(G), 0 if g == math.inf else g)
            self.assertEqual(I.matching_number(G), len(nx.max_weight_matching(H, maxcardinality=True)))
            done += 1


class ExactArithmetic(unittest.TestCase):
    def test_ceilings_of_square_roots(self):
        rng = random.Random(3)
        for _ in range(2000):
            x = Fraction(rng.randint(0, 10 ** 6), rng.randint(1, 50))
            k = W.ceil_sqrt(x)                          # the defining property, exactly
            self.assertTrue(k >= 0 and k * k >= x and (k == 0 or (k - 1) ** 2 < x))
            a, s, c = Fraction(rng.randint(0, 200), rng.randint(1, 5)), rng.randint(0, 10 ** 5), rng.randint(1, 9)
            k = W.ceil_affine_sqrt(a, s, c)
            self.assertTrue(k * c - a >= 0 and (k * c - a) ** 2 >= s)
            t = (k - 1) * c - a
            self.assertTrue(t < 0 or t * t < s)
        self.assertEqual([W.ceil_sqrt(v) for v in (0, 1, 2, 4, 5, 9, Fraction(1, 4), Fraction(17, 4))],
                         [0, 1, 2, 2, 3, 3, 1, 3])


class Statements(unittest.TestCase):
    def test_the_family(self):
        self.assertEqual((len(W.PROVED), len(W.DISPROVED), len(W.OPEN)), (23, 21, 9))
        self.assertEqual(len(W.ALL), 53)
        self.assertFalse(set(W.PROVED) & set(W.DISPROVED) or set(W.PROVED) & set(W.OPEN)
                         or set(W.DISPROVED) & set(W.OPEN))

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_proved_and_open_statements_hold_on_every_connected_graph_up_to_7_vertices(self):
        graphs = connected_atlas(7)
        self.assertEqual(len(graphs), 1 + 2 + 6 + 21 + 112 + 853)   # OEIS A001349, n = 2..7
        bad = []
        for k, (status, f) in W.ALL.items():
            if status == 'disproved':
                continue
            for G in graphs:
                if W.violated(f(G)):
                    bad.append((k, G.n, G.edges))
                    break
        self.assertEqual(bad, [])

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_the_only_disproved_statement_with_a_counterexample_up_to_7_vertices_is_32(self):
        graphs = connected_atlas(7)
        small = sorted(str(k) for k, f in W.DISPROVED.items() if any(W.violated(f(G)) for G in graphs))
        self.assertEqual(small, ['32'])

    def test_every_documented_counterexample_violates_its_statement_with_the_stated_values(self):
        cache = {}
        for k, (build, stated) in W.COUNTEREXAMPLES.items():
            self.assertIn(k, W.DISPROVED)
            G = cache.setdefault(build.__name__ if build.__name__ != '<lambda>' else k, build())
            self.assertTrue(G.connected(), k)
            self.assertTrue(W.violated(W.DISPROVED[k](G)), k)
            for name, value in stated.items():
                self.assertEqual(W.stated_value(G, name), value, (k, name))
            self.assertGreater(W.margin(W.DISPROVED[k](G)), 0)

    def test_conjecture_34s_tree_partly(self):
        """The 39-vertex tree is beyond exhaustive search for path(G); for a tree it is the diameter plus one."""
        edges = [(i, 2 * i + 1) for i in range(15)] + [(i, 2 * i + 2) for i in range(15)]   # binary tree 0..30
        chain = [0, 31, 32, 33, 34, 35]                                                       # five edges to 35
        edges += [(chain[i], chain[i + 1]) for i in range(5)] + [(35, 36), (35, 37), (35, 38)]
        G = I.Graph(39, edges)
        self.assertTrue(G.connected())
        self.assertEqual(len(G.edges), 38)
        D = G.dist()
        C, M = I.center(G), I.max_degree_vertices(G)
        self.assertEqual((len(C), len(M)), (1, 1))
        self.assertEqual((sum(D[C[0]]), sum(D[M[0]])), (154, 266))
        bound = math.ceil(W.dist_avg_pairs_nonzero(G, C) + W.dist_avg_pairs_nonzero(G, M))
        self.assertEqual(bound, 12)
        self.assertEqual(I.diameter(G) + 1, 11)       # path(G) of a tree: its longest path
        self.assertGreater(bound, I.diameter(G) + 1)


if __name__ == '__main__':
    unittest.main()
