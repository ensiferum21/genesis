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
from genesis.conjecture import statement as ST  # noqa: E402
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


_ATLAS = {}


def connected_atlas(max_n):
    if max_n not in _ATLAS:
        _ATLAS[max_n] = [I.Graph(H.number_of_nodes(), list(H.edges())) for H in nx.graph_atlas_g()
                         if 2 <= H.number_of_nodes() <= max_n and nx.is_connected(H)]
    return _ATLAS[max_n]


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
        self.assertEqual((len(W.PROVED), len(W.DISPROVED), len(W.OPEN)), (29, 25, 9))
        self.assertEqual(len(W.ALL), 63)
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
            c = ST.Statement(W.TEXT[k], max_n=60).check(G)                 # the posed text agrees
            self.assertTrue(c['violated'] and c['score'] > 0, k)

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


def _agree(test, k, G):
    """The two transcriptions give the same verdict; the posed text's score is positive exactly when violated; for a
    plain inequality, the score is the kernel's margin lhs - rhs (plus 1 when violated)."""
    r, c = W.ALL[k][1](G), ST.Statement(W.TEXT[k], max_n=60).check(G)
    test.assertEqual(c['violated'], W.violated(r), (k, G.n, G.edges))
    test.assertEqual(c['score'] > 0, c['violated'], (k, G.n, G.edges))
    if r['kind'] == 'ineq' and ST.parse(W.TEXT[k])[1] is None:
        test.assertAlmostEqual(c['score'] - (1.0 if c['violated'] else 0.0),
                               float(r['lhs'] - r['rhs']) if c['violated'] else min(0.0, float(r['lhs'] - r['rhs'])),
                               places=9, msg=(k, G.n, G.edges))


class PosedText(unittest.TestCase):
    """The statements as the research plane receives them (`wowii.TEXT`, `statement.py`)."""

    def test_every_statement_is_posed_and_parses(self):
        self.assertEqual(set(W.TEXT), set(W.ALL))
        for k, text in W.TEXT.items():
            ST.parse(text)

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_the_two_transcriptions_agree_on_every_connected_graph_up_to_7_vertices(self):
        for G in connected_atlas(7):
            for k in W.TEXT:
                _agree(self, k, G)

    def test_the_two_transcriptions_agree_on_random_graphs_of_8_to_10_vertices(self):
        rng = random.Random(7)
        done = 0
        while done < 60:
            n = rng.randint(8, 10)
            G = random_graph(rng, n, rng.choice([0.25, 0.4, 0.6]))
            if G.connected():
                for k in W.TEXT:
                    _agree(self, k, G)
                done += 1


class StatementLanguage(unittest.TestCase):
    def test_exact_square_roots(self):
        self.assertEqual(ST.sqrt(4), 2)
        self.assertEqual(ST.sqrt(Fraction(9, 4)), Fraction(3, 2))
        self.assertEqual(ST.sqrt(0), 0)
        self.assertEqual(ST.sqrt(-3), 0)                              # Lean's Real.sqrt
        r8, r2 = ST.sqrt(8), ST.sqrt(2)
        self.assertEqual((r8.q, r8.s, r2.q, r2.s), (2, 2, 1, 2))      # sqrt 8 = 2 sqrt 2
        self.assertEqual(ST.sub(r8, ST.mul(2, r2)), 0)
        self.assertEqual(ST.mul(r2, r2), 2)
        self.assertEqual(ST.div(1, r2), ST.mul(Fraction(1, 2), r2))
        with self.assertRaises(ValueError):
            ST.add(ST.sqrt(2), ST.sqrt(3))

    def test_signs_floors_and_ceilings_match_high_precision(self):
        from decimal import Decimal, getcontext
        getcontext().prec = 80
        rng = random.Random(13)
        for _ in range(3000):
            p = Fraction(rng.randint(-500, 500), rng.randint(1, 30))
            q = Fraction(rng.randint(-50, 50), rng.randint(1, 30))
            s = rng.choice([2, 3, 5, 6, 7, 10, 11, 13, 17, 19, 23, 29, 30])
            x = ST.Surd.make(p, q, s)
            ref = Decimal(p.numerator) / Decimal(p.denominator) + \
                Decimal(q.numerator) / Decimal(q.denominator) * Decimal(s).sqrt()
            self.assertEqual(ST.sign(x), (ref > 0) - (ref < 0))
            self.assertEqual(ST.floor(x), math.floor(ref))
            self.assertEqual(ST.ceil(x), math.ceil(ref))

    def test_lean_conventions(self):
        P3 = I.Graph(3, [(0, 1), (1, 2)])
        ctx = ST._Context(P3)
        ev = lambda t: ST.value(ST._Parser(ST.tokens(t)).expr(), ctx)
        self.assertEqual(ev('5/0'), 0)
        self.assertEqual(ev('idiv(7, 2)'), 3)
        self.assertEqual(ev('idiv(7, 0)'), 0)
        self.assertEqual(ev('mod(7, 0)'), 7)
        self.assertEqual(ev('nat_sub(2, 5)'), 0)
        self.assertEqual(ev('ceil(1/2*sqrt(8))'), 2)
        self.assertEqual(ev('n + deg_sq_sum@complement'), 3 + 2)       # the complement of P3 is K2 + K1
        self.assertEqual(ev('cond(has_c4, 1, avg_l)'), Fraction(4, 3))
        self.assertEqual(ev('ind(alpha == 2)'), 1)

    def test_logarithms_and_conjunctions(self):
        b = ST.ln(Fraction(30, 11))                                    # 1 < ln(30/11) < 2 (conjecture 103's file)
        self.assertEqual((ST.floor(ST.sub(10, b)), ST.ceil(ST.sub(10, b)), ST.sign(ST.sub(b, 1))), (8, 9, 1))
        self.assertEqual(ST.ln(1), 0)
        self.assertEqual(ST.ln(0), 0)
        self.assertEqual(ST.floor(ST.mul(-2, ST.ln(Fraction(1, 3)))), 2)    # 2 ln 3 = 2.197...
        with self.assertRaises(ValueError):
            ST.sqrt(b)
        self.assertEqual(W.floor_minus_ln(10, Fraction(30, 11)), 8)
        self.assertEqual(W.floor_minus_ln(Fraction(7, 2), 1), 3)
        P3 = I.Graph(3, [(0, 1), (1, 2)])
        self.assertTrue(ST.Statement('n > 2 & alpha == 2 -> b <= 3').check(P3)['score'] <= 0)
        self.assertTrue(ST.Statement('n > 2 & alpha == 2 -> b <= 2').check(P3)['violated'])
        self.assertFalse(ST.Statement('n > 3 & alpha == 2 -> b <= 2').check(P3)['violated'])

    def test_malformed_statements_are_refused(self):
        for bad in ('alpha <=', 'foo <= 1', 'dist_min(alpha) <= 1', 'alpha@cube <= 1', 'ceil(1, 2) <= 1',
                    'alpha <= 1 -> b <= 2 -> n <= 3', '$ <= 1'):
            with self.assertRaises(ValueError, msg=bad):
                ST.parse(bad)


class Domain(unittest.TestCase):
    def test_the_frontier_refutes_invented_false_statements_and_never_the_true(self):
        """On invented statements only (family B stays sealed): two false, three true."""
        from genesis.conjecture.invariant_domain import InvariantDomain
        from genesis.frontier.engine import Frontier
        from genesis.frontier.manifest import Manifest
        posed = {'p1': 'alpha <= max_degree', 'p2': 'matching <= idiv(n, 2)', 'p3': 'radius <= diameter',
                 'p4': 'girth <= 4 -> ham_path', 'p5': 'diameter <= 2*radius'}

        def verify(pid, art):                       # a stand-in kernel check for invented statements
            G = I.Graph(art['n'], [tuple(e) for e in art['edges']])
            return 1.0 if G.connected() and ST.Statement(posed[pid]).check(G)['violated'] else 0.0
        dom = InvariantDomain(posed, n_values=(6, 8))
        e = Frontier(Manifest(dom, verify, budget=4000, quantum=100), 'frontier', seed=2)
        e.run()
        self.assertEqual({k for k, v in e.best_verified.items() if v > 0}, {'p1', 'p4'})
        self.assertTrue(dom.statement('p1').startswith('invariant: '))

    def test_the_kernel_verifier(self):
        verify = W.verifier({'q': 32, 'r': 1})
        P5 = {'n': 5, 'edges': [[0, 1], [1, 2], [2, 3], [3, 4]]}
        self.assertEqual(verify('q', P5), 1.0)                       # the counterexample the source gives
        self.assertEqual(verify('r', P5), 0.0)                       # a proved statement
        self.assertEqual(verify('q', {'n': 5, 'edges': [[0, 1], [1, 2], [3, 4]]}), 0.0)    # disconnected
        self.assertEqual(verify('q', {'n': 5, 'edges': [[0, 9]]}), 0.0)                     # out of range
        self.assertEqual(verify('q', {'n': 'x', 'edges': []}), 0.0)
        self.assertEqual(verify('missing', P5), 0.0)


class Reference(unittest.TestCase):
    """The kernel's independent invariants (`invariants_ref.py`) against the research plane's."""
    FUNCS = ('b', 'indep_num', 'ls', 'largest_induced_tree', 'largest_induced_forest', 'radius', 'path_number',
             'max_degree_vertices', 'hamiltonian_path', 'average_indep_neighbours', 'periphery', 'residue', 'girth',
             'center', 'diameter', 'average_eccentricity', 'second_smallest_degree', 'min_degree_vertices',
             'matching_number', 'indep_domination_number', 'vertex_connectivity', 'ng', 'min_spanning_paths',
             'min_indep_neighbours', 'min_degree', 'max_temp', 'max_indep_neighbours', 'max_degree', 'eccentricities',
             'dp', 'degree_l2_norm_squared', 'average_degree', 'alpha_core_size', 'domination_number',
             'total_domination_number', 'max_triangles', 'freq_min_triangles', 'hh_zero_step', 'max_even_correction',
             'min_complement_edge_neighbourhood', 'well_totally_dominated', 'pendants', 'triangle_free', 'alpha_two',
             'low_degree_vertices')

    def test_it_shares_no_code_with_the_research_plane(self):
        import ast as pyast
        src = (ROOT / 'src/genesis/conjecture/invariants_ref.py').read_text()
        mods = set()
        for node in pyast.walk(pyast.parse(src)):
            if isinstance(node, pyast.Import):
                mods |= {a.name for a in node.names}
            elif isinstance(node, pyast.ImportFrom):
                mods.add('.' * node.level + (node.module or ''))
        self.assertEqual(mods, {'fractions', 'itertools', 'networkx'})

    def _pairs(self):
        pairs = [(G.n, G.edges) for G in connected_atlas(7)]
        rng = random.Random(3)
        while len(pairs) < 995 + 30:
            G = random_graph(rng, rng.randint(8, 10), rng.choice([0.3, 0.5]))
            if G.connected():
                pairs.append((G.n, G.edges))
        return pairs

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_every_invariant_agrees(self):
        from genesis.conjecture import invariants_ref as R
        for n, e in self._pairs():
            ga, gb = I.Graph(n, e), R.Graph(n, e)
            self.assertEqual((ga.edges, ga.adj, ga.dist(), ga.degrees()), (gb.edges, gb.adj, gb.dist(), gb.degrees()))
            self.assertEqual((ga.complement().edges, I.square(ga).edges), (gb.complement().edges, R.square(gb).edges))
            for f in self.FUNCS:
                self.assertEqual(getattr(I, f)(ga), getattr(R, f)(gb), (f, n, e))
            for f in ('dist_min', 'ecc_set', 'dist_max_set', 'dist_avg_set'):
                for S in ([0], list(range(n)), [v for v in range(n) if v % 2], I.center(ga)):
                    self.assertEqual(getattr(I, f)(ga, S), getattr(R, f)(gb, S), (f, n, e, S))
            low = I.low_degree_vertices(ga)
            high = [v for v in range(n) if v not in low]
            self.assertEqual((I.indep_on(ga, high), I.internal_edges(ga, low)), (R.indep_on(gb, high),
                                                                                R.internal_edges(gb, low)))
            for v in range(n):
                self.assertEqual((I.triangles_at(ga, v), I.even_horizontal(ga, v)),
                                 (R.triangles_at(gb, v), R.even_horizontal(gb, v)))
                self.assertEqual(I.dist_even(ga, v), R.dist_even(gb, v))
                self.assertEqual(I.indep_num_within(ga, ga.adj[v]), R.indep_num_within(gb, gb.adj[v]))

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_ls_is_the_most_leaves_of_a_spanning_tree(self):
        """Lean's definition, by enumerating spanning trees, on every connected graph up to 6 vertices."""
        from genesis.conjecture import invariants_ref as R
        for G in connected_atlas(6):
            H = nx.Graph(G.edges)
            most = max(sum(1 for _, d in T.degree() if d == 1) for T in nx.SpanningTreeIterator(H))
            self.assertEqual(R.ls(R.Graph(G.n, G.edges)), most, G.edges)

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_the_evaluators_agree_under_both_implementations(self):
        for G in connected_atlas(6):
            for k in W.ALL:
                a, b = W.evaluate_both(k, G.n, G.edges)
                self.assertEqual(a, b, (k, G.edges))
        for k, (build, _) in W.COUNTEREXAMPLES.items():
            G = build()
            if G.n <= 18 and k != 194:                 # 194's 18 vertices defeat the backtracking path search
                a, b = W.evaluate_both(k, G.n, G.edges)
                self.assertTrue(W.violated(a) and W.violated(b), k)

    def test_the_verifier_needs_both(self):
        log = []
        verify = W.verifier({'q': 32}, log=log)
        self.assertEqual(verify('q', {'n': 5, 'edges': [[0, 1], [1, 2], [2, 3], [3, 4]]}), 1.0)
        self.assertEqual(log, [])
        old = W._reference                                # a reference that disagrees refuses the certificate
        broken = type('Broken', (), {'__getattr__': lambda self, name: getattr(old, name),
                                     'path_number': staticmethod(lambda G: 99)})()
        try:
            W._reference = broken
            self.assertEqual(verify('q', {'n': 5, 'edges': [[0, 1], [1, 2], [2, 3], [3, 4]]}), 0.0)
        finally:
            W._reference = old
        self.assertEqual(len(log), 1)
        self.assertEqual((log[0]['research'], log[0]['reference']), (True, False))


if __name__ == '__main__':
    unittest.main()
