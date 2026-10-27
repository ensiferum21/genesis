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
RESEARCH_PLANE = ('__init__.py', 'expr.py', 'graphs.py', 'attack.py', 'domain.py', 'abstraction.py',
                  'generate.py', 'invariants.py', 'statement.py', 'invariant_domain.py',
                  'operations.py')
KERNEL_SIDE = ('sealed.py', 'verify.py', 'audit.py', 'wowii.py', 'invariants_ref.py')
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


class Independent(unittest.TestCase):
    """The second, independent check: Berkowitz's exact characteristic polynomial and a Sturm count."""

    def test_charpoly_and_sturm_against_numpy(self):
        import numpy as np
        rng = random.Random(3)
        for _ in range(25):
            n = rng.randint(2, 13)
            g = Gr.normalise(n, [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < 0.4])
            p = V.charpoly(*g)
            L = Gr.laplacian(*g)
            ref = np.poly(L)
            self.assertTrue(np.allclose(p, ref, atol=1e-6 * max(1, abs(ref).max())))
            w = np.linalg.eigvalsh(L)
            for c in (0.5, 1.5, 2.7, 4.1):
                self.assertEqual(V.roots_above(p, c), len({round(x, 6) for x in w if x > c + 1e-9}))

    def test_both_checks_agree(self):
        C4 = (4, ((0, 1), (1, 2), (2, 3), (0, 3)))
        self.assertEqual(V.check_charpoly('d + 1', 'vertex', *C4)['verdict'], 'REFUTED')
        self.assertEqual(V.check_charpoly('d + m', 'vertex', *C4)['verdict'], 'NOT_CERTIFIED')   # tight: mu = 4
        rng = random.Random(11)
        for _ in range(40):
            g = random_graph(rng, rng.randint(3, 12), rng.uniform(0.2, 0.7))
            mu, vec = Gr.laplacian_top(*g)
            for f, kind in (('d + 1', 'vertex'), (MERRIS, 'vertex'), ('di + dj - 1', 'edge')):
                a = V.check(f, kind, *g, Gr.rational_vector(vec))['verdict']
                b = V.check_charpoly(f, kind, *g)['verdict']
                if a == 'REFUTED':
                    self.assertEqual(b, 'REFUTED', (f, Gr.graph6(*g)))
                if f == MERRIS:
                    self.assertNotEqual(b, 'REFUTED')


class UpperCertificates(unittest.TestCase):
    def test_collatz_wielandt(self):
        import numpy as np
        from fractions import Fraction
        star = V.adjacency(5, [(0, 1), (0, 2), (0, 3), (0, 4)])
        self.assertEqual(V.collatz_upper(star, [2, 1, 1, 1, 1]), 2)              # lambda_1(K_{1,4}) = 2, exactly
        rng = random.Random(5)
        for _ in range(40):
            g = random_graph(rng, rng.randint(3, 14), 0.4)
            A = V.adjacency(*g)
            w, vec = np.linalg.eigh(np.array(A, float))
            x = [Fraction(max(1e-6, abs(float(t)))).limit_denominator(10 ** 9) for t in vec[:, -1]]
            self.assertGreaterEqual(float(V.collatz_upper(A, x)), w[-1] - 1e-9)
        with self.assertRaises(ValueError):
            V.collatz_upper(star, [1, 0, 1, 1, 1])

    def test_the_wagner_rebuild(self):
        """Wagner 2021 (arXiv 2104.14516) refuted Aouchiche and Hansen's lambda_1 + mu >= sqrt(n - 1) + 1 with a
        19-vertex tree with lambda_1 = sqrt(10) and matching number 2 (read from the abstract page's text, 27 Oct
        2026; its Figure 4 was not seen). Rebuilt from those values: two stars K_{1,8} whose centres share a
        neighbour (lambda^2 = 10 solves 1 = 2 / (lambda^2 - 8)). The certificate is exact: a Collatz-Wielandt upper
        bound r on lambda_1 with r + mu < sqrt(n - 1) + 1, decided in rationals."""
        from fractions import Fraction
        from genesis.conjecture import invariants_ref as R

        def certified(n, edges, x):
            r = V.collatz_upper(V.adjacency(n, edges), x)
            mu = R.matching_number(R.Graph(n, edges))
            t = r + mu - 1                                     # refuted iff t < sqrt(n - 1)
            return t < 0 or t * t < n - 1, r, mu
        edges = [(0, 1), (0, 2)] + [(1, 3 + i) for i in range(8)] + [(2, 11 + i) for i in range(8)]
        centre = Fraction(15811388, 10 ** 7)                   # sqrt(10) / 2, rounded; the middle vertex 1, leaves 1/2
        x = [1, centre, centre] + [Fraction(1, 2)] * 16
        ok, r, mu = certified(19, edges, x)
        self.assertEqual(mu, 2)
        self.assertTrue(ok)
        self.assertLess(abs(float(r) - 10 ** 0.5), 1e-6)
        # the star K_{1,18} meets the bound with equality (sqrt(18) + 1): no certificate exists
        star = [(0, i) for i in range(1, 19)]
        self.assertFalse(certified(19, star, [Fraction(42426407, 10 ** 7)] + [1] * 18)[0])
        # one more edge between two leaves of different stars raises mu to 3: the same vector no longer certifies
        self.assertFalse(certified(19, edges + [(3, 11)], x)[0])


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


class Attacks(unittest.TestCase):
    """The attacks and the Frontier's view of the domain, on INVENTED bounds only (never the sealed set):
    'd + 1' is false (C4: mu = 4 > 3), 'di + dj - 1' is false, '2*d' and 'd + m' are proved (2 Delta; Merris)."""
    POSED = {'q1': ('d + 1', 'vertex'), 'q2': ('2*d', 'vertex'), 'q3': ('d + m', 'vertex'),
             'q5': ('di + dj - 1', 'edge')}

    def test_every_representation_and_method_runs_and_is_deterministic(self):
        from genesis.conjecture import attack as AT
        for rep in AT.REPRESENTATIONS:
            for meth in AT.METHODS:
                a = AT.Runner('d + 1', 'vertex', rep, meth, 10, seed=5)
                b = AT.Runner('d + 1', 'vertex', rep, meth, 10, seed=5)
                a.advance(300)
                b.advance(150)
                b.advance(150)
                self.assertEqual(a.best, b.best, (rep, meth))
                self.assertEqual(a.evals, 300)

    def test_the_vectorised_bound_matches_the_exact_one(self):
        from genesis.conjecture import attack as AT
        rng = random.Random(4)
        for _ in range(40):
            g = random_graph(rng, rng.randint(3, 12), 0.4)
            import numpy as np
            A = np.zeros((g[0], g[0]), dtype=np.int64)
            for u, v in g[1]:
                A[u, v] = A[v, u] = 1
            for f, kind in (('sqrt(2*d^2 + 2*d*m)', 'vertex'), ('2 + sqrt(2*(di - 1)^2 + 2*(dj - 1)^2)', 'edge')):
                val = AT.Bound(f, kind).value(A)
                exact = Gr.bound_value(E.parse(f, kind), kind, *g)
                self.assertAlmostEqual(val, exact, places=9)

    def test_the_frontier_refutes_the_false_and_never_the_proved(self):
        from genesis.conjecture.domain import ConjectureDomain
        from genesis.frontier.engine import Frontier
        from genesis.frontier.manifest import Manifest
        dom = ConjectureDomain(self.POSED)
        e = Frontier(Manifest(dom, V.verifier(self.POSED), budget=6000, quantum=100), 'frontier', seed=2)
        e.run()
        self.assertEqual(e.best_verified.get('q1'), 1.0)
        self.assertEqual(e.best_verified.get('q5'), 1.0)
        self.assertFalse(e.best_verified.get('q2'))
        self.assertFalse(e.best_verified.get('q3'))

    def test_forged_artifacts_are_refused(self):
        posed = {'q2': ('2*d', 'vertex')}
        verify = V.verifier(posed)
        self.assertEqual(verify('q2', {'n': 3, 'edges': [[0, 1], [1, 2]], 'x': ['1', '-2', '1']}), 0.0)
        self.assertEqual(verify('q2', {'n': 'x'}), 0.0)


class Abstraction(unittest.TestCase):
    """Templates: graphs parsed into Gamma programs (isomorphic when rebuilt), sizes generalised into parameters."""

    def test_parse_rebuilds_isomorphic_graphs(self):
        import networkx as nx
        import numpy as np
        from genesis.conjecture import abstraction as AB, attack as AT
        rng = np.random.default_rng(9)
        G = AT.GammaRep(30)
        checked = 0
        for _ in range(300):
            prog = G.random(rng)
            A = G.graph(prog)
            if A is None or len(A) < 2:
                continue
            B = AB.build(AB.parse(A))
            self.assertTrue(nx.is_isomorphic(nx.from_numpy_array(A), nx.from_numpy_array(B)), prog)
            checked += 1
        self.assertGreater(checked, 150)

    def test_generalise_and_search_a_template(self):
        import numpy as np
        from genesis.conjecture import abstraction as AB, attack as AT
        A = AT.GammaRep(30)._build(('join', ('E', 3), ('union', ('K', 4), ('C', 5))))
        t = AB.generalise([AB.parse(A)])
        self.assertEqual(len(t['slots']), 3)
        R = AB.TemplateRep(t)
        rng = np.random.default_rng(2)
        g = R.random(rng)
        self.assertEqual(R.graph(g).shape[0], int(sum(g)))
        two = AB.generalise([AB.parse(AT.GammaRep(30)._build(('Kab', 2, 5))),
                             AB.parse(AT.GammaRep(30)._build(('Kab', 2, 9)))])
        self.assertEqual([v for _, v in two['slots']], [5])                  # the agreeing size stays fixed

    def test_the_domain_abstracts_converged_structures(self):
        from genesis.conjecture.domain import ConjectureDomain
        from genesis.frontier.engine import Frontier
        from genesis.frontier.manifest import Manifest
        posed = {'q3': ('d + m', 'vertex'), 'q1': ('d + 1', 'vertex')}
        dom = ConjectureDomain(posed)
        e = Frontier(Manifest(dom, V.verifier(posed), budget=40000, quantum=200), 'frontier', seed=4,
                     abstraction=True, branch_out=False)
        e.run()
        self.assertTrue(dom.templates)
        shapes = [repr(__import__('genesis.conjecture.abstraction', fromlist=['x'])._shape(v['template']['program']))
                  for v in dom.templates.values()]
        self.assertEqual(len(shapes), len(set(shapes)))
        self.assertTrue(any(b['direction']['representation'].startswith('template') for b in e.branches.values()))
        self.assertFalse(e.best_verified.get('q3'))                          # a proved bound stays unrefuted


class Generation(unittest.TestCase):
    def test_conjectures_from_genesis_own_data(self):
        import numpy as np
        from genesis.conjecture import generate as GN
        graphs = GN.data(np.random.default_rng(1), count=200)
        self.assertEqual(len(graphs), 200)
        cs = GN.conjectures(graphs)
        self.assertTrue(cs)
        mus = np.array([g[1] for g in graphs])
        for f, touch in cs:
            v = GN.values(f, graphs)
            self.assertTrue((v >= mus - GN.TOL).all(), f)                  # holds on the data
            self.assertEqual(int((np.abs(v - mus) <= GN.TOL).sum()), touch)
            self.assertGreater(touch, 0)                                    # sharp somewhere
        self.assertTrue(any(GN.equivalent(f, 'd + m') for f, _ in cs))      # Merris's bound, found from data
        forms = [f for f, _ in cs]
        self.assertFalse(any(GN.equivalent(a, b) for i, a in enumerate(forms) for b in forms[i + 1:]))


class ForbiddenConcept(unittest.TestCase):
    """The proving test's audit: the research plane's code names no forbidden concept; a planted one is caught;
    docstrings (which say what the code does not contain) are not code."""

    def test_the_research_plane_is_clean(self):
        from genesis.conjecture import audit as AU
        self.assertEqual(AU.scan(AU.research_plane(ROOT)), [])

    def test_a_planted_concept_is_caught(self):
        import tempfile
        from genesis.conjecture import audit as AU
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'x.py'
            f.write_text('"""No quotient here."""\ndef build_quotient(cells):\n    return "equitable"\n')
            stems = {h[3] for h in AU.scan([f])}
            self.assertEqual(stems, {'quotient', 'equitable'})
            self.assertEqual({h[3] for h in AU.scan([], extra=[('manifest', {'hint': 'use a Blow-Up'})])}, {'blowup'})
            self.assertEqual({h[3] for h in AU.scan([], extra=[('manifest', 'orbits of automorphisms')])},
                             {'orbit', 'automorph'})


class Boundary(unittest.TestCase):
    def test_the_split_covers_the_package(self):
        self.assertEqual({p.name for p in PKG.glob('*.py')}, set(RESEARCH_PLANE) | set(KERNEL_SIDE))

    def test_the_research_plane_imports_no_kernel_side(self):
        bad = []
        for name in RESEARCH_PLANE:
            for node in pyast.walk(pyast.parse((PKG / name).read_text())):
                if isinstance(node, (pyast.Import, pyast.ImportFrom)):
                    names = [a.name for a in node.names] + [getattr(node, 'module', None) or '']
                    kernel = ('sealed', 'verify', 'audit', 'wowii', 'invariants_ref')
                    if any(x.split('.')[-1] in kernel for x in names):
                        bad.append(name)
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
