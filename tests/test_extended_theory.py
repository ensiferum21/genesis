"""DEV-only semantic checks for the opt-in extended inductive signature."""
import unittest
import numpy as np

from gap_engine.adapters.induction.extended import EXTENDED_DEFS, extended_theory
from gap_engine.adapters.induction.theory import Theory


class TestExtendedTheory(unittest.TestCase):
    def test_default_unchanged(self):
        th = Theory.default()
        for f in EXTENDED_DEFS:
            self.assertNotIn(f, th.funs)

    def test_definitions_well_sorted(self):
        th = extended_theory()
        self.assertEqual(set(EXTENDED_DEFS), set(th.funs) - set(Theory.default().funs))
        self.assertTrue(all(th.well_sorted_eq(r.lhs, r.rhs) for f in EXTENDED_DEFS for r in th.defs[f]))

    def test_randomized_semantics_against_independent_python(self):
        th = extended_theory()
        p = th.parser()
        rng = np.random.default_rng(42)
        for _ in range(40):
            xs = tuple(map(int, rng.integers(0, 6, size=int(rng.integers(0, 5)))))
            ys = tuple(map(int, rng.integers(0, 6, size=int(rng.integers(0, 5)))))
            n = int(rng.integers(0, 6))
            env = {'xs': xs, 'ys': ys, 'n': n, 'x': n}
            cases = {
                'snoc xs x': xs + (n,),
                'mapplus n xs': tuple(n + x for x in xs),
                'mapdouble xs': tuple(2 * x for x in xs),
                'countzero xs': sum(x == 0 for x in xs),
                'filterzero xs': tuple(x for x in xs if x == 0),
                'sumsquares xs': sum(x * x for x in xs),
                'zipplus xs ys': tuple(x + y for x, y in zip(xs, ys)),
            }
            for expr, expected in cases.items():
                self.assertEqual(th.evaluate(p.parse_term(expr), env), expected, expr)
            def interleave(a, b):
                return () if not a and not b else (b if not a else (a[0],) + interleave(b, a[1:]))
            self.assertEqual(th.evaluate(p.parse_term('interleave xs ys'), env), interleave(xs, ys))


if __name__ == '__main__':
    unittest.main()

class TestProofCodec(unittest.TestCase):
    def test_induction_proof_json_roundtrip_rechecks(self):
        import json
        from gap_engine.adapters.induction.proof_codec import encode, decode
        from gap_engine.adapters.induction.theory import Equation
        from gap_engine.adapters.induction.prover import Prover
        from gap_engine.adapters.induction.checker import check_proof
        th = extended_theory()
        eq = Equation(*th.parser().parse_eq('len (snoc xs x) = S (len xs)'))
        att = Prover(th, {}, fuel=4000).prove(eq)
        self.assertTrue(att.proved)
        pf = decode(json.loads(json.dumps(encode(att.proof))))
        self.assertTrue(check_proof(th, {}, eq, pf))
