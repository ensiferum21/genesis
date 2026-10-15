"""B20_R26 (s15.3, W10): quotient representations. These tests cover the exact pattern solver
against brute force, the Python transport model against exhaustive checks, the method's witness
validity, and the family's bounds."""
import random
import unittest

from genesis.formal_research import triangle_theory as T
from genesis.invention import quotients as QT
from genesis.invention import representations as RP


def brute(W, K):
    arcs = [(a, b) for a in range(K) for b in range(K) if a != b]
    best = 0
    for mask in range(1 << len(arcs)):
        Q = [arcs[i] for i in range(len(arcs)) if mask >> i & 1]
        if QT.pattern_ok(Q):
            best = max(best, sum(W[a][b] for a, b in Q))
    return best


class Pattern(unittest.TestCase):
    def test_exact_against_brute_force(self):
        rng = random.Random(26)
        for K in (2, 3, 4):
            for _ in range(25):
                W = [[rng.randrange(0, 7) if a != b else 0 for b in range(K)] for a in range(K)]
                value, Q = QT.best_pattern(W, K)
                self.assertEqual(value, brute(W, K))
                self.assertEqual(value, sum(W[a][b] for a, b in Q))
                self.assertTrue(QT.pattern_ok(Q))

    def test_triple_check_is_the_repository_definition(self):
        rng = random.Random(27)
        for _ in range(400):
            k = rng.randrange(1, 5)
            Q = frozenset((a, b) for a in range(k) for b in range(k) if rng.random() < 0.35)
            self.assertEqual(QT.pattern_ok(Q), T.tf(Q))

    def test_two_blocks_equal_cross_2(self):
        value, Q = QT.best_pattern([[0, 3], [5, 0]], 2)
        self.assertEqual((value, Q), (8, [(0, 1), (1, 0)]))


class Transport(unittest.TestCase):
    def test_triangle_free_patterns_lift_to_triangle_free_subsets(self):
        rng = random.Random(28)
        for _ in range(500):
            k = rng.randrange(2, 5)
            Q = frozenset((a, b) for a in range(k) for b in range(k) if rng.random() < 0.4)
            q = {v: rng.randrange(k) for v in range(6)}
            H = frozenset((u, v) for u in range(6) for v in range(6) if rng.random() < 0.4)
            L = QT.lift(q, Q, H)
            self.assertTrue(L <= H)
            if T.tf(Q):
                self.assertTrue(T.tf(L))

    def test_a_pattern_triple_can_lift_to_a_triangle(self):
        Q = {(0, 1), (1, 2), (0, 2)}
        self.assertFalse(T.tf(QT.lift({0: 0, 1: 1, 2: 2}, Q, {(0, 1), (1, 2), (0, 2)})))


class Method(unittest.TestCase):
    def test_valid_witness_and_bounds(self):
        rng = random.Random(29)
        n = 24
        E = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < 0.3]
        for K in (3, 5):
            o = QT.quotient_and_repair(n, E, K, RP.tf_add_ok, cpu_seconds=0.2, seed=1)
            self.assertTrue(T.tf(frozenset(map(tuple, o['witness']))))
            self.assertTrue(set(map(tuple, o['witness'])) <= set(E))
            self.assertTrue(QT.pattern_ok(map(tuple, o['pattern'])))
            self.assertGreaterEqual(o['value'], o['decoded_before_repair'])
        with self.assertRaises(RP.ProposalError):
            QT.quotient_and_repair(n, E, QT.MAX_BLOCKS + 1, RP.tf_add_ok, cpu_seconds=0.1)
        with self.assertRaises(RP.ProposalError):
            QT.proposal(1)
        self.assertEqual(QT.proposal(4)['id'], 'quotient_4')

    def test_obligations_are_stated_over_the_repository_definitions(self):
        conjs = {c['id']: c for c in QT.conjectures()}
        self.assertEqual(set(conjs), {'quotient_image', 'quotient_sound_tf'})
        self.assertEqual(conjs['quotient_sound_tf']['concl'], 'GT.TriangleFree (QT.lift q Q H)')
        self.assertTrue(any(b.get('hyp') and b['lean'] == 'GT.TriangleFree Q' for b in conjs['quotient_sound_tf']['binders']))
        self.assertIn('def lift (q : ℕ → ℕ) (Q : GT.Edges) (H : GT.Edges)', QT.SOURCE)


if __name__ == '__main__':
    unittest.main()
