"""The proving test's mechanism 4 (`docs/OMEGA_FRONTIER.md` §7b; Daniel, 28 Oct 2026): operators acting on Γ's own
operations (`conjecture/operations.py`), derivation in the conjecture domain, the engine's derive action with
replay on resume, and procedures that carry derivations."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.conjecture import attack as AT  # noqa: E402
from genesis.conjecture import operations as OP  # noqa: E402
from genesis.conjecture import verify as V  # noqa: E402
from genesis.conjecture.domain import ConjectureDomain  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402

try:
    import networkx as nx
except ImportError:                                # pragma: no cover
    nx = None


def nx_matrix(H, order):
    return nx.to_numpy_array(H, nodelist=order, dtype=np.int64)


class Space(unittest.TestCase):
    def test_every_table_is_a_graph_operation(self):
        rng = np.random.default_rng(1)
        G = AT.GammaRep(8)
        X, Y = G._build(('P', 3)), G._build(('C', 4))
        for t in range(1 << len(OP.PAIRS)):
            A = OP.rule_product(X, Y, t)
            self.assertTrue(((A == 0) | (A == 1)).all())
            self.assertTrue((A == A.T).all() and not A.diagonal().any())
        self.assertFalse(OP.rule_product(X, Y, 0).any())
        full = OP.rule_product(X, Y, (1 << len(OP.PAIRS)) - 1)
        self.assertEqual(int(full.sum()), 12 * 11)
        for _ in range(40):
            X, Y = G._build(G.random(rng, 2)), G._build(G.random(rng, 2))
            if len(X) * len(Y) <= 64:
                P = np.kron(X, np.eye(len(Y), dtype=np.int64)) + np.kron(np.eye(len(X), dtype=np.int64), Y)
                self.assertTrue((OP.rule_product(X, Y, OP.CARTESIAN) == P).all())   # Γ's own product is a point

    @unittest.skipIf(nx is None, 'networkx is not installed')
    def test_the_decoder_is_exact_against_networkx_products(self):
        """Four points networkx names, as a check of the decoder (the builder's check; nothing in the research plane
        names or favours any point)."""
        X, Y = nx.path_graph(3), nx.cycle_graph(4)
        AX, AY = nx_matrix(X, range(3)), nx_matrix(Y, range(4))
        order = [(u, v) for u in range(3) for v in range(4)]
        named = {'cartesian': (nx.cartesian_product, [('same', 'adj'), ('adj', 'same')]),
                 'tensor': (nx.tensor_product, [('adj', 'adj')]),
                 'strong': (nx.strong_product, [('same', 'adj'), ('adj', 'same'), ('adj', 'adj')]),
                 'lexicographic': (nx.lexicographic_product, [('adj', 'same'), ('adj', 'adj'), ('adj', 'non'),
                                                              ('same', 'adj')])}
        for name, (fn, pairs) in named.items():
            self.assertTrue((OP.rule_product(AX, AY, OP.table_of(pairs)) == nx_matrix(fn(X, Y), order)).all(), name)

    def test_the_operators_are_uniform_and_stay_in_the_space(self):
        rng = np.random.default_rng(3)
        flips = [0] * len(OP.PAIRS)
        for _ in range(4000):
            t = OP.mutate_table(OP.CARTESIAN, rng)
            d = t ^ OP.CARTESIAN
            self.assertEqual(bin(d).count('1'), 1)
            flips[d.bit_length() - 1] += 1
        self.assertTrue(all(400 <= f <= 600 for f in flips), flips)            # 500 expected each
        for _ in range(200):
            a, b = int(rng.integers(256)), int(rng.integers(256))
            c = OP.recombine_tables(a, b, rng)
            self.assertEqual(c & ~(a | b), 0)
            self.assertEqual((a & b) & ~c, 0)
            self.assertLess(c, 256)


POSED = {'q1': ('d + 1', 'vertex'), 'q2': ('2*d', 'vertex')}


class Derive(unittest.TestCase):
    def test_the_domain_derives_new_operations(self):
        dom = ConjectureDomain(POSED)
        a = dom.derive('q1', 'gamma', 7)
        self.assertEqual(a, 'derived0')
        self.assertEqual(dom.derive('q1', 'gamma', 7), 'derived0')                # same seed: same operation set
        b = dom.derive('q2', a, 11)
        self.assertEqual(len(dom.derived[b]['ops']), 2)
        self.assertEqual(dom.derived[b]['from'], a)
        self.assertIsNone(dom.derive('q1', 'edges', 7))                          # not a Γ representation
        self.assertIn(b, dom.approaches('q1')['representation'])
        other = ConjectureDomain(POSED)
        self.assertEqual(other.derive('q1', 'gamma', 7), 'derived0')
        self.assertEqual(other.derived['derived0'], dom.derived['derived0'])     # deterministic in the seed
        rep = OP.GammaPlus(10, dom.derived[b]['ops'])
        rng = np.random.default_rng(0)
        built = 0
        for _ in range(60):
            g = rep.random(rng)
            A = rep.graph(g)
            if A is not None:
                built += 1
                self.assertTrue((A == A.T).all() and not A.diagonal().any())
        self.assertGreater(built, 10)

    def frontier(self, p_derive, seed=3, max_steps=None, path=None, budget=4000):
        dom = ConjectureDomain(POSED, n_values=(6, 8))
        m = Manifest(dom, V.verifier(POSED), budget=budget, quantum=100)
        if path is not None and Path(path).exists():
            e = Frontier.load(path, m, policy_params={'p_derive': p_derive})
        else:
            e = Frontier(m, 'frontier', seed=seed, policy_params={'p_derive': p_derive})
        return dom, e, e.run(max_steps)

    def test_the_engine_derives_and_a_resumed_run_ends_the_same(self):
        dom, whole, _ = self.frontier(0.5)
        derived = [ev for ev in whole.events if ev['kind'] == 'derive']
        self.assertTrue(derived)
        self.assertTrue(any(b['direction']['representation'].startswith('derived') for b in whole.branches.values()))
        self.assertEqual(whole.best_verified.get('q1'), 1.0)                      # the false bound is still refuted
        self.assertFalse(whole.best_verified.get('q2'))                           # the proved one is not
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'e.json'
            _, first, status = self.frontier(0.5, max_steps=12)
            self.assertEqual(status, 'paused')
            first.save(path)
            dom2, second, status = self.frontier(0.5, path=path)
            self.assertEqual(status, 'done')
        self.assertEqual([ev['kind'] for ev in second.events], [ev['kind'] for ev in whole.events])
        self.assertEqual(second.best_verified, whole.best_verified)
        self.assertEqual(dom2.derived, dom.derived)

    def test_off_by_default(self):
        _, e, _ = self.frontier(0.0)
        self.assertFalse([ev for ev in e.events if ev['kind'] == 'derive'])

    def test_a_procedure_carries_its_derivations(self):
        from genesis.frontier import procedure as PR
        dom, e, _ = self.frontier(0.5)
        derived_branches = [b for b in e.branches.values() if b['direction']['representation'].startswith('derived')]
        self.assertTrue(derived_branches)
        b = derived_branches[0]
        e.events.append({'kind': 'verified', 'problem': 'q1', 'branch': b['id'], 'value': 1.0, 'step': 0,
                         'spent': e.spent})                    # a stand-in record of a discovery in that branch
        proc = PR.extract(e, 'q1')
        self.assertEqual(proc['steps'][0]['op'], 'derive')
        self.assertEqual(proc['steps'][0]['from'], 'gamma')
        self.assertTrue(proc['steps'][0]['seeds'])
        self.assertNotIn(b['direction']['representation'], repr(proc['steps']))   # names no representation it made
        # replayed by the improved inventor on a fresh domain: the same operations are derived again
        fresh = ConjectureDomain({'p9': ('d + 1', 'vertex')}, n_values=(6, 8))
        m = Manifest(fresh, V.verifier({'p9': ('d + 1', 'vertex')}), budget=2000, quantum=100)
        f = Frontier(m, 'procedure', seed=5, policy_params={'procedures': [proc], 'rho': 0.9})
        f.run()
        want = dom.derived[b['direction']['representation']]['ops']
        self.assertIn(want, [x['ops'] for x in fresh.derived.values()])



class Library(unittest.TestCase):
    """Mechanism 1: library learning over Γ (`conjecture/library.py`)."""
    B = AT.GammaRep.BINARY

    def test_a_recurring_piece_becomes_a_macro(self):
        from genesis.conjecture import library as LB
        a = ('union', ('join', ('E', 3), ('K', 2)), ('P', 4))
        b = ('prod', ('C', 5), ('join', ('E', 7), ('K', 4)))
        c = ('compl', ('S', 3))
        skel = LB.learn([a, b, c], self.B)
        self.assertEqual(skel, ('join', ('E', None), ('K', None)))
        self.assertIsNone(LB.learn([a, c], self.B))                     # recurring in one source only
        self.assertIsNone(LB.learn([a, b], self.B, known=[skel]))       # already known, nothing else recurs
        rep = LB.GammaLib(10, {}, {'m0': skel})
        A = rep.graph(('union', ('m0', 2, 3), ('P', 2)))
        B = rep.graph(('union', ('join', ('E', 2), ('K', 3)), ('P', 2)))
        self.assertTrue((A == B).all())
        # hierarchical: a macro may contain an earlier one
        deep = LB.learn([('corona', ('m0', 2, 2), ('E', 1)), ('corona', ('m0', 5, 1), ('E', 3))], self.B)
        self.assertEqual(deep, ('corona', ('m0', None, None), ('E', None)))
        rep2 = LB.GammaLib(10, {}, {'m0': skel, 'm1': deep})
        self.assertEqual(rep2.size(('m1', 2, 2, 1)), 4 * 2)
        rng = np.random.default_rng(0)
        drew = sum(1 for _ in range(200) if rep2._base(rng)[0] in ('m0', 'm1'))
        self.assertTrue(40 <= drew <= 80, drew)                          # LIBRARY_SHARE 0.3 of new leaves

    def test_a_macro_with_a_derived_operation_expands_and_builds(self):
        """B20R177-LIBRARY: a macro learned from a derived representation's programs contains its operation; the
        library representation carries it, so the macro's slots are counted and it expands and builds."""
        from genesis.conjecture import library as LB
        ops = {'r7': 7}
        binary = self.B + ('r7',)
        a = ('union', ('r7', ('C', 4), ('E', 3)), ('P', 2))
        b = ('join', ('K', 2), ('r7', ('C', 5), ('E', 2)))
        skel = LB.learn([a, b], binary)
        self.assertEqual(skel, ('r7', ('C', None), ('E', None)))
        self.assertEqual(LB.ops_in(skel), {'r7': 7})
        lib = LB.GammaLib(12, {}, {'m0': skel})                          # as the domain builds it: no ops passed
        self.assertIn('r7', lib.BINARY)
        self.assertEqual(LB.slots(skel, lib.BINARY), 2)
        g = ('m0', 4, 3)
        self.assertEqual(lib.expand(g), ('r7', ('C', 4), ('E', 3)))
        plain = OP.GammaPlus(12, ops)
        self.assertEqual(lib.size(g), plain.size(('r7', ('C', 4), ('E', 3))))
        self.assertTrue((lib._build(g) == plain._build(('r7', ('C', 4), ('E', 3)))).all())
        rng = np.random.default_rng(5)
        for _ in range(300):                                             # drawn leaves carry the right arity
            leaf = lib._base(rng)
            if leaf[0] == 'm0':
                self.assertEqual(len(leaf), 3)
                lib.size(leaf)
        # the defect as it was: without the operation the slots are miscounted and the expansion fails
        broken = OP.GammaPlus(12, {})
        self.assertEqual(LB.slots(skel, broken.BINARY), 0)
        with self.assertRaises((RuntimeError, StopIteration)):
            LB.fill(skel, [], broken.BINARY)
        # a library whose macros use no derived operation is built exactly as before
        plain_skel = ('join', ('E', None), ('K', None))
        self.assertEqual(LB.GammaLib(10, {}, {'m0': plain_skel}).BINARY, AT.GammaRep.BINARY)

    def test_the_domain_learns_from_its_own_runners_deterministically(self):
        def domain():
            dom = ConjectureDomain(POSED, representations=('gamma',), n_values=(8,))
            for i in range(12):
                d = {'problem': 'q1', 'representation': 'gamma', 'method': ('hill', 'evolution')[i % 2],
                     'params': {'n': 8}, 'op': 'seed', 'parent': None}
                dom.step('q1', d, 100 + i, 0, 150)
            return dom
        a, b = domain(), domain()
        na, nb = a.learn('q1', 'fp'), b.learn('q1', 'fp')
        self.assertEqual(na, nb)
        self.assertEqual(a.macros, b.macros)
        if na is not None:                                               # what Genesis's own searches repeated
            from genesis.conjecture import library as LB
            skel = a.macros['m0']
            sources = [r.best_g for r in a._runners.values() if r.best_g is not None]
            self.assertGreaterEqual(sum(1 for g in sources if skel in LB.pieces(g, self.B)), 2)
            self.assertIn(na, a.approaches('q1')['representation'])
            d = {'problem': 'q1', 'representation': na, 'method': 'hill', 'params': {'n': 8}, 'op': 'seed',
                 'parent': None}
            pts, _ = a.step('q1', d, 7, 0, 100)
            self.assertTrue(pts)
        fresh = ConjectureDomain(POSED)
        fresh.restore(json_round(a.state()))
        self.assertEqual(fresh.macros, a.macros)
        self.assertEqual(fresh.libraries, a.libraries)


def json_round(x):
    import json
    return json.loads(json.dumps(x, default=list))


class Transfer(unittest.TestCase):
    """The proving test's part 4 mechanics: a procedure extracted in the Laplacian domain runs unchanged in the
    invariant domain (invented statements only; family B stays sealed)."""

    def test_a_derivation_procedure_crosses_domains(self):
        from genesis.conjecture import invariants as I
        from genesis.conjecture import statement as ST
        from genesis.conjecture.invariant_domain import InvariantDomain
        from genesis.frontier import procedure as PR
        dom = ConjectureDomain(POSED, n_values=(6, 8))
        e = Frontier(Manifest(dom, V.verifier(POSED), budget=4000, quantum=100), 'frontier', seed=3,
                     policy_params={'p_derive': 0.5})
        e.run()
        b = next(b for b in e.branches.values() if b['direction']['representation'].startswith('derived'))
        e.events.append({'kind': 'verified', 'problem': 'q1', 'branch': b['id'], 'value': 1.0, 'step': 0,
                         'spent': e.spent})
        proc = PR.extract(e, 'q1')
        posed = {'s1': 'alpha <= max_degree', 's2': 'radius <= diameter'}

        def verify(pid, art):
            G = I.Graph(art['n'], [tuple(x) for x in art['edges']])
            return 1.0 if G.connected() and ST.Statement(posed[pid]).check(G)['violated'] else 0.0
        inv = InvariantDomain(posed, n_values=(6, 8))
        f = Frontier(Manifest(inv, verify, budget=3000, quantum=100), 'procedure', seed=6,
                     policy_params={'procedures': [proc], 'rho': 0.9})
        f.run()
        want = dom.derived[b['direction']['representation']]['ops']
        self.assertIn(want, [x['ops'] for x in inv.derived.values()])            # the same operations, re-derived
        used = [x for x in f.branches.values() if x['direction'].get('op') == 'procedure'
                and inv.derived.get(x['direction']['representation'], {}).get('ops') == want]
        self.assertTrue(used)                                                     # and searched with
        self.assertEqual(f.best_verified.get('s1'), 1.0)
        self.assertFalse(f.best_verified.get('s2'))


class Cap(unittest.TestCase):
    """One size cap for every program representation (`ConjectureDomain(program_max_n=...)`): by default Γ, derived and
    library programs stop at attack.MAX_N vertices, as before; with a cap, every one of them builds up to it."""
    BIG = ('prod', ('K', 10), ('C', 10))                             # 100 vertices

    def test_the_default_is_unchanged(self):
        self.assertEqual(AT.MAX_N, 64)
        for rep in (AT.GammaRep(8), OP.GammaPlus(8, {'r1': OP.CARTESIAN}), self.lib(8, None)):
            self.assertEqual(rep.max_n, AT.MAX_N)
            self.assertIsNone(rep.graph(self.BIG))
            self.assertEqual(rep.graph(('prod', ('K', 4), ('C', 4))).shape, (16, 16))

    def test_a_cap_applies_to_every_program_representation(self):
        for rep in (AT.GammaRep(8, 400), OP.GammaPlus(8, {'r1': OP.CARTESIAN}, 400), self.lib(8, 400)):
            A = rep.graph(self.BIG)
            self.assertEqual(A.shape, (100, 100))
            self.assertIsNone(rep.graph(('prod', ('K', 20), ('C', 21))))        # 420 > 400

    def test_the_domain_passes_its_cap(self):
        dom = ConjectureDomain(POSED, n_values=(6, 8), program_max_n=400)
        self.assertEqual(dom._rep_for({'representation': 'gamma', 'params': {'n': 8}}).max_n, 400)
        dom.derived['derived0'] = {'ops': {'r9': OP.CARTESIAN}, 'from': 'gamma'}
        self.assertEqual(dom._rep_for({'representation': 'derived0', 'params': {'n': 8}}).max_n, 400)
        plain = ConjectureDomain(POSED, n_values=(6, 8))
        self.assertIsNone(plain._rep_for({'representation': 'gamma', 'params': {'n': 8}}))  # the runner's own Γ

    @staticmethod
    def lib(n, cap):
        from genesis.conjecture import library as LB
        return LB.GammaLib(n, {}, {}, cap)



class Sizes(unittest.TestCase):
    """A program's computed size is the size of the graph it builds, for Γ, derived and library programs. The size
    gates the cap, so a size below the built one lets graphs past it: until 28 Oct 2026 the star S_k (k leaves and a
    centre) counted k, and nested products of stars built graphs of thousands of vertices under a cap of 64 (the
    out-of-memory kill of B20_R157's first attempt)."""

    def check(self, rep, rng, k=4000):
        seen = 0
        for _ in range(k):
            g = rep.random(rng, depth=4)
            for _ in range(int(rng.integers(0, 4))):
                g = rep.mutate(g, rng)
            s = rep.size(g)
            if s > 200:
                continue
            self.assertEqual(rep._build(g).shape[0], s, g)
            A = rep.graph(g)
            self.assertTrue(A is None or A.shape[0] <= rep.max_n)
            seen += 1
        self.assertGreater(seen, k // 4)

    def test_gamma(self):
        self.assertEqual(AT.GammaRep(8).size(('S', 3)), 4)
        self.assertEqual(AT.GammaRep(8)._build(('S', 3)).shape, (4, 4))
        self.check(AT.GammaRep(12), np.random.default_rng(1))

    def test_derived_and_library(self):
        from genesis.conjecture import library as LB
        ops = {'r1': OP.table_of([('adj', 'adj')]), 'r2': OP.table_of([('same', 'adj'), ('adj', 'non')])}
        self.check(OP.GammaPlus(12, ops), np.random.default_rng(2))
        macro = LB.skeleton(('join', ('S', 3), ('prod', ('K', 2), ('P', 3))), OP.GammaPlus(12, ops).BINARY) \
            if hasattr(LB, 'skeleton') else None
        lib = LB.GammaLib(12, ops, {'m0': macro} if macro is not None else {})
        self.check(lib, np.random.default_rng(3))

    def test_library_learning_can_be_switched_off(self):
        from unittest import mock
        for flag, want in ((True, 'library0'), (False, None)):
            dom = ConjectureDomain(POSED, n_values=(6, 8), library=flag)
            with mock.patch.object(ConjectureDomain, 'learn', return_value='library0'):
                self.assertEqual(dom.abstract('q1', 'unseen'), want)        # no example: library learning, if on

    def test_the_cap_holds_for_stars(self):
        rep = AT.GammaRep(12)
        g = ('prod', ('S', 7), ('prod', ('S', 7), ('S', 7)))            # 8^3 = 512 vertices, not 343
        self.assertEqual(rep.size(g), 512)
        self.assertIsNone(rep.graph(g))


if __name__ == '__main__':
    unittest.main()
