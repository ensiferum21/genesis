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


if __name__ == '__main__':
    unittest.main()
