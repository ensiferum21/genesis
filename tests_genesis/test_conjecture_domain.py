"""F2 (`docs/OMEGA_FRONTIER.md` §5-§6): the conjecture domain's expression language, exact certificates, the sealed
Brankov-Hansen-Stevanovic set and the boundary between the research plane and the kernel side."""
import ast as pyast
from fractions import Fraction
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.conjecture import expr as E  # noqa: E402
from genesis.conjecture import graphs as Gr  # noqa: E402
from genesis.conjecture import sealed as SD  # noqa: E402
from genesis.conjecture import verify as V  # noqa: E402

PKG = ROOT / 'src' / 'genesis' / 'conjecture'
RESEARCH_PLANE = ('__init__.py', 'expr.py', 'graphs.py')
KERNEL_SIDE = ('sealed.py', 'verify.py')
P3 = (3, ((0, 1), (1, 2)))
MERRIS = 'd + m'                                 # proved (Merris 1998), tight on P3 and on regular bipartite graphs
ANDERSON_MORLEY = 'di + dj'                      # proved (Anderson and Morley 1985)


def random_graph(rng, n, p):
    while True:
        es = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p]
        deg = [0] * n
        for u, v in es:
            deg[u] += 1
            deg[v] += 1
        if min(deg) > 0:
            return Gr.normalise(n, es)


class Expressions(unittest.TestCase):
    def test_parse_render_and_refusals(self):
        a = E.parse('2 + sqrt(2*(di - 1)^2 + 2*(dj - 1)^2)', 'edge')
        self.assertEqual(E.parse(E.render(a), 'edge'), a)
        self.assertEqual(E.variables_of(a), {'di', 'dj'})
        for bad, kind in (('d + x', 'vertex'), ('d^(1/2)', 'vertex'), ('di + d', 'edge'), ('__import__(1)', 'vertex'),
                          ('d +', 'vertex'), ('d m', 'vertex')):
            with self.assertRaises(ValueError):
                E.parse(bad, kind)

    def test_enclosures_contain_the_value(self):
        rng = random.Random(1)
        for k, (f, *_rest) in SD.BOUNDS.items():
            kind = SD.kind(k)
            node = E.parse(f, kind)
            names = E.VERTEX_VARS if kind == 'vertex' else E.EDGE_VARS
            for _ in range(25):
                env = {v: Fraction(rng.randint(1, 40), rng.randint(1, 6)) for v in names}
                x = E.evaluate(node, env)
                iv = E.enclose(node, env, 64)
                if x is None:
                    continue
                self.assertIsNotNone(iv, (k, env))
                self.assertLessEqual(float(iv[0]) - 1e-9, x, (k, env))
                self.assertGreaterEqual(float(iv[1]) + 1e-9, x, (k, env))
                self.assertLess(float(iv[1] - iv[0]), 1e-12 * max(1.0, abs(x)) + 1e-12, (k, env))

    def test_undefined(self):
        node = E.parse('sqrt(d - 5*m)', 'vertex')
        self.assertIsNone(E.evaluate(node, {'d': 1, 'm': 1}))
        self.assertIsNone(E.enclose(node, {'d': 1, 'm': 1}))
        self.assertIsNone(E.evaluate(E.parse('d/(m - m)', 'vertex'), {'d': 1, 'm': 2}))


class Certificates(unittest.TestCase):
    def test_p3_refutes_57_exactly_and_never_a_tight_bound(self):
        mu, vec = Gr.laplacian_top(*P3)
        self.assertAlmostEqual(mu, 3.0)
        x = Gr.rational_vector(vec)
        self.assertEqual(V.check(SD.BOUNDS[57][0], 'edge', *P3, x)['verdict'], 'REFUTED')
        self.assertEqual(V.check(MERRIS, 'vertex', *P3, x)['verdict'], 'NOT_CERTIFIED')      # equality: 3 = 3
        self.assertEqual(V.check(MERRIS, 'vertex', *P3, [1, -2, 1])['verdict'], 'NOT_CERTIFIED')  # q = 3 exactly

    def test_malformed_certificates(self):
        with self.assertRaises(ValueError):
            V.check(MERRIS, 'vertex', *P3, [1, 2])
        with self.assertRaises(ValueError):
            V.check(MERRIS, 'vertex', *P3, [0, 0, 0])
        with self.assertRaises(ValueError):
            Gr.local(3, ((0, 1),))                 # an isolated vertex

    def test_proved_bounds_are_never_certified_on_random_graphs(self):
        rng = random.Random(7)
        for _ in range(150):
            g = random_graph(rng, rng.randint(3, 16), rng.uniform(0.15, 0.7))
            mu, vec = Gr.laplacian_top(*g)
            x = Gr.rational_vector(vec)
            for f, kind in ((MERRIS, 'vertex'), (ANDERSON_MORLEY, 'edge'), (SD.BOUNDS[12][0], 'vertex'),
                            (SD.BOUNDS[42][0], 'edge')):
                self.assertNotEqual(V.check(f, kind, *g, x)['verdict'], 'REFUTED', (f, Gr.graph6(*g)))

    def test_graph6_round_trip(self):
        import networkx as nx
        rng = random.Random(3)
        for _ in range(30):
            g = random_graph(rng, rng.randint(2, 20), 0.4)
            self.assertEqual(Gr.from_graph6(Gr.graph6(*g)), g)
            h = nx.Graph()
            h.add_nodes_from(range(g[0]))
            h.add_edges_from(g[1])
            self.assertEqual(Gr.graph6(*g), nx.to_graph6_bytes(h, header=False).decode().strip())
        self.assertEqual(Gr.graph6(*P3), 'Bg')
        self.assertEqual(Gr.from_graph6('Bo'), (3, ((0, 1), (0, 2))))     # P3 centred at 0 (the report's labelling)


class Sealed(unittest.TestCase):
    def test_statuses_partition_the_68(self):
        groups = (SD.PROVED, SD.REFUTED_2024, SD.REFUTED_2025, SD.REFUTED_2026, SD.OPEN)
        self.assertEqual([len(g) for g in groups], [22, 30, 2, 12, 2])
        self.assertEqual(sorted(x for g in groups for x in g), list(range(1, 69)))
        self.assertEqual(sorted(SD.BOUNDS), list(range(1, 69)))
        for k, (f, tier, sources, note) in SD.BOUNDS.items():
            node = E.parse(f, SD.kind(k))
            allowed = set(E.VERTEX_VARS if k <= 32 else E.EDGE_VARS)
            self.assertLessEqual(E.variables_of(node), allowed)
            self.assertIn(tier, ('A1', 'A2', 'B', 'X'))
            if tier in ('A1', 'A2'):
                self.assertGreaterEqual(len(sources), 2, k)

    def test_the_primary_set(self):
        s = SD.sealed()
        self.assertFalse(set(s) & set(SD.PROVING_TEST_HOLDOUT))
        self.assertNotIn(23, s)
        self.assertFalse({28, 41, 45, 48, 50, 51} & set(s))
        self.assertEqual(len(s), 68 - 2 - 4 - 1 - 5)

    def test_the_transcription_report(self):
        r = json.loads((ROOT / 'evidence/bhs_transcription_f2/report.json').read_text())
        self.assertEqual(r['alarms_proved_or_open_violated'], [])
        self.assertEqual(r['lenient_reading_proved_or_open_violated'], [])
        self.assertEqual(r['refuted_with_small_counterexample'], [48, 57, 61])          # Taieb et al.: P3
        self.assertEqual(r['not_tight_regular'], [28])
        for k, row in r['rows'].items():
            self.assertEqual(row['text'], SD.BOUNDS[int(k)][0])                        # the report is current


class Boundary(unittest.TestCase):
    def test_the_split_covers_the_package(self):
        self.assertEqual({p.name for p in PKG.glob('*.py')}, set(RESEARCH_PLANE) | set(KERNEL_SIDE))

    def test_the_research_plane_imports_no_kernel_side(self):
        bad = []
        for name in RESEARCH_PLANE:
            for node in pyast.walk(pyast.parse((PKG / name).read_text())):
                if isinstance(node, (pyast.Import, pyast.ImportFrom)):
                    names = [a.name for a in node.names] + [getattr(node, 'module', None) or '']
                    if any(x.split('.')[-1] in ('sealed', 'verify') for x in names):
                        bad.append(name)
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
