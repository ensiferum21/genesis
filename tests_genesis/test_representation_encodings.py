"""The representation language, stage B (fixtures): encodings of finite-domain variables as searched objects with
decoders and validity relations; lifted relations (partial where codes go unused); finite-domain problems compiled
through an encoding are exact for Max-CSP by brute force (one-hot and 2-bit codes for 3 colours, 2-bit codes for 4);
the encoding search returns a feasible cheapest table and every gadget it admitted is exact."""
from itertools import product
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.representation import compile as C  # noqa: E402
from genesis.representation import encodings as E  # noqa: E402
from genesis.representation import gadgets as GD  # noqa: E402
from genesis.representation import library as LB  # noqa: E402
from genesis.representation import relations as R  # noqa: E402

NEQ = {'neq': (lambda v: v[0] != v[1], 2)}


def synth(rel, uniform):
    return GD.synthesize_milp(rel, max_ancillas=2, bound=8, uniform=uniform, time_limit=20)


def library_for(enc):
    return E.cost(enc, NEQ, {'neq': 1}, 1, LB.EMPTY, synth)[2]


class Encodings(unittest.TestCase):
    def test_objects_and_decoders(self):
        oh, bi = E.one_hot(3), E.binary(4)
        self.assertEqual([oh.decode(c) for c in oh.code], [0, 1, 2])
        self.assertIsNone(oh.decode((1, 1, 0)))
        self.assertIsNone(bi.validity())
        self.assertEqual(oh.validity(), R.exactly(3, 1))
        self.assertIsInstance(oh.lift(NEQ['neq'][0], 2), R.Partial)
        self.assertNotIsInstance(bi.lift(NEQ['neq'][0], 2), R.Partial)
        self.assertEqual(bi.lift(NEQ['neq'][0], 2), R.from_predicate(4, lambda z: (z[0], z[1]) != (z[2], z[3])))
        self.assertEqual(E.Encoding.from_json(oh.to_json()).code, oh.code)
        with self.assertRaises(ValueError):
            E.Encoding(3, 2, [(0, 0), (0, 0), (1, 1)])

    def test_tables(self):
        self.assertEqual(len(list(E.tables(3, 2))), 6)              # one class of pattern sets, 3! value orders
        def key(code):                                               # the class of a pattern set under bit symmetry
            from itertools import permutations
            return min(tuple(sorted(tuple(p[q[j]] ^ (f >> j & 1) for j in range(3)) for p in code))
                       for q in permutations(range(3)) for f in range(8))
        self.assertIn(key(E.one_hot(3).code), {key(t.code) for t in E.tables(3, 3)})

    def test_partial_gadgets(self):
        rel = E.one_hot(3).lift(NEQ['neq'][0], 2)
        g, rep = GD.synthesize_milp(rel, max_ancillas=0, bound=4, uniform=True)
        self.assertIsNotNone(g)
        self.assertTrue(GD.check(g, rel)['exact'] and GD.check_matrix(g, rel))
        self.assertEqual(g.size()[0], 3)                             # the textbook sum_c x_uc x_vc

    def test_colouring_is_exact_through_any_encoding(self):
        rng = random.Random(21)
        for enc in (E.one_hot(3), E.binary(3), E.binary(4)):
            lib = library_for(enc)
            for _ in range(4):
                n = 4
                edges = rng.sample([(u, v) for u in range(n) for v in range(u + 1, n)], 4)
                fd = {'n': n, 'D': enc.D, 'constraints': [{'name': 'neq', 'vars': list(e), 'weight': 1}
                                                          for e in edges]}
                bp = E.compile_fd(fd, enc, NEQ)
                bqp, info = C.compile(bp, lib, 'max_csp')
                v, z = C.brute_force(bqp)
                direct = min(E.verify_fd(fd, list(col), NEQ) for col in product(range(enc.D), repeat=n))
                self.assertEqual(v, direct, enc)
                self.assertEqual(E.verify_fd(fd, E.decode_fd(C.decode(z, info), enc, n), NEQ), v)

    def test_factorisation_discovers_the_textbook_decomposition(self):
        pieces, uniform = E.factorize(E.one_hot(4), NEQ['neq'][0], 2)
        self.assertTrue(uniform)
        self.assertEqual(sorted(sorted(p[0]) for p in pieces), [[c, 4 + c] for c in range(4)])
        for bits, rel in pieces:                                     # each: not both of colour c
            self.assertFalse(rel.contains([1, 1]))
            self.assertTrue(rel.contains([0, 1]) and rel.contains([1, 0]) and rel.contains([0, 0]))
        self.assertIsNone(E.factorize(E.binary(4), NEQ['neq'][0], 2))

    def test_plans_choose_whole_or_factors_and_stay_exact(self):
        rng = random.Random(23)
        for enc in (E.one_hot(4), E.binary(4), E.one_hot(3)):
            anc, nz, lib, plan = E.cost(enc, NEQ, {'neq': 1}, 1, LB.EMPTY, synth)
            self.assertEqual(plan['neq']['form'], 'whole' if enc.b == 2 else 'factors', enc)
            for _ in range(3):
                n = 3
                edges = [(0, 1), (1, 2), (0, 2)][:rng.randint(2, 3)]
                fd = {'n': n, 'D': enc.D, 'constraints': [{'name': 'neq', 'vars': list(e), 'weight': 1}
                                                          for e in edges]}
                bqp, info = C.compile(E.compile_fd(fd, enc, NEQ, plan), lib, 'max_csp')
                v, z = C.brute_force(bqp)
                direct = min(E.verify_fd(fd, list(col), NEQ) for col in product(range(enc.D), repeat=n))
                self.assertEqual(v, direct, enc)
                self.assertEqual(E.verify_fd(fd, E.decode_fd(C.decode(z, info), enc, n), NEQ), v)

    def test_search(self):
        best, lib, scored = E.search(4, NEQ, {'neq': 10}, 5, [2], synth=synth)
        self.assertTrue(best['feasible'])
        self.assertEqual(best['variables'], 5 * 2 + 10 * best['details']['neq']['ancillas'])
        self.assertEqual(len(scored), 24)
        for slots in lib['entries'].values():
            for e in slots.values():
                if e is not None:
                    rel = R.relation_from_json(e['relation'])
                    self.assertTrue(GD.check(GD.Gadget.from_json(e['gadget']), rel)['exact'])


if __name__ == '__main__':
    unittest.main()
