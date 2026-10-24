"""The representation language, stage A (fixtures): relations as values with canonical forms and operators; gadgets
verified by enumeration and by a second, independent evaluation; the MILP synthesiser rediscovers known gadgets with
the fewest ancillas (none for 2-clauses, exactly-one and the AND gate; one for a 3-clause and 3-parity) and refuses
where none exists within its limits; transport across renamings and negations keeps exactness; the search baseline
finds easy gadgets; a tampered gadget is rejected."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.representation import gadgets as GD  # noqa: E402
from genesis.representation import relations as R  # noqa: E402


class Relations(unittest.TestCase):
    def test_values_and_canonical_forms(self):
        a = R.clause([True, False, True])
        b = R.clause([False, True, True])
        self.assertEqual(a.id(), b.id())                       # one orbit under renaming and negation
        self.assertNotEqual(a.id(), R.exactly(3, 1).id())
        self.assertEqual(R.exactly(3, 1).size(), 3)
        self.assertEqual(R.Relation.from_json(a.to_json()), a)
        c, (perm, flips) = a.canonical()
        self.assertEqual(a.transform(perm, flips), c)

    def test_operators(self):
        x = R.parity(3, 0)
        self.assertEqual(x.project(2), R.Relation(2, 0b1111))  # any pair of values extends to even parity
        self.assertEqual(x.complement(), R.parity(3, 1))
        both = R.clause([True, True]).conjoin(R.clause([False, True]), [0, 1], [0, 2], 3)
        self.assertTrue(all(both.contains(z) == ((z[0] or z[1]) and ((not z[0]) or z[2]))
                            for z in [R.assignment(i, 3) for i in range(8)]))
        self.assertEqual(R.and_gate(3).negate(2), R.from_predicate(3, lambda z: z[2] != (z[0] and z[1])))
        self.assertEqual(len(R.orbit_representatives(2)), 5)

    def test_refusals(self):
        with self.assertRaises(ValueError):
            R.Relation(7, 1)
        with self.assertRaises(ValueError):
            R.exactly(2, 1).extend(3, [0, 0])


class Gadgets(unittest.TestCase):
    def test_known_gadgets_verify_two_ways(self):
        rosenberg = GD.Gadget(3, 0, 0, [0, 0, 3], {(0, 1): 1, (0, 2): -2, (1, 2): -2})
        self.assertTrue(GD.check(rosenberg, R.and_gate(3))['exact'])
        self.assertTrue(GD.check_matrix(rosenberg, R.and_gate(3)))
        one_hot = GD.Gadget(3, 0, 1, [-1, -1, -1], {(0, 1): 2, (0, 2): 2, (1, 2): 2})
        self.assertTrue(GD.check(one_hot, R.exactly(3, 1))['exact'])
        tampered = GD.Gadget(3, 0, 1, [-1, -1, -1], {(0, 1): 2, (0, 2): 1, (1, 2): 2})
        self.assertFalse(GD.check(tampered, R.exactly(3, 1))['exact'])
        self.assertFalse(GD.check_matrix(tampered, R.exactly(3, 1)))

    def test_the_two_checkers_agree(self):
        rng = random.Random(4)
        for _ in range(200):
            k, m = rng.randint(1, 3), rng.randint(0, 2)
            n = k + m
            g = GD.Gadget(k, m, rng.randint(-2, 3), [rng.randint(-3, 3) for _ in range(n)],
                          {(i, j): rng.randint(-3, 3) for i in range(n) for j in range(i + 1, n)})
            rel = R.random_relation(k, rng)
            if rel.table:
                self.assertEqual(GD.check(g, rel)['exact'], GD.check_matrix(g, rel))

    def test_milp_finds_the_fewest_ancillas(self):
        cases = [(R.clause([True, True]), 0), (R.exactly(3, 1), 0), (R.and_gate(3), 0),
                 (R.clause([True, True, True]), 1), (R.parity(3, 0), 1), (R.exactly(4, 2), None)]
        for rel, want in cases:
            g, rep = GD.synthesize_milp(rel, max_ancillas=1, bound=6)
            if want is None:
                if g is not None:
                    self.assertTrue(GD.check(g, rel)['exact'])
                continue
            self.assertIsNotNone(g, rel)
            self.assertEqual(g.m, want, rel)
            self.assertTrue(GD.check(g, rel)['exact'] and GD.check_matrix(g, rel))
            self.assertEqual([t['ancillas'] for t in rep['tried']], list(range(want + 1)))

    def test_refusal_within_limits(self):
        g, rep = GD.synthesize_milp(R.clause([True, True, True]), max_ancillas=0, bound=6)
        self.assertIsNone(g)
        self.assertEqual(len(rep['tried']), 1)

    def test_transport_keeps_exactness(self):
        base = R.clause([True, True, True])
        g, _ = GD.synthesize_milp(base, max_ancillas=1, bound=6)
        rng = random.Random(7)
        for _ in range(20):
            perm = list(range(3))
            rng.shuffle(perm)
            flips = rng.randrange(8)
            self.assertTrue(GD.check(GD.transport(g, base, perm, flips), base.transform(perm, flips))['exact'])

    def test_search_baseline(self):
        g, rep = GD.synthesize_search(R.clause([True, False]), 0, random.Random(1), evaluations=5000)
        self.assertIsNotNone(g)
        self.assertTrue(GD.check(g, R.clause([True, False]))['exact'])
        self.assertLessEqual(rep['evaluations'], 5000)
        self.assertEqual(GD.Gadget.from_json(g.to_json()), g)


if __name__ == '__main__':
    unittest.main()
