"""First-order subset, finite model finder, independent evaluator, E wrapper and Experiment B."""
import json
from pathlib import Path
import tempfile
import unittest

from genesis.fol import Model, ParseError, check_model, evaluate, parse, signature, to_tptp
from genesis.verification.tools import available

READY = available('cadical') and available('eprover')
GROUP = ['![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))', '![X]: mul(e,X) = X', '![X]: mul(inv(X),X) = e']


def z2():
    mul = {(a, b): (a + b) % 2 for a in range(2) for b in range(2)}
    return Model(2, {'mul': mul, 'e': {(): 0}, 'inv': {(0,): 0, (1,): 1}}, {})


class Syntax(unittest.TestCase):
    def test_round_trip_through_tptp(self):
        for text in GROUP + ['![X,Y,Z]: (mul(X,Y) = mul(X,Z) => Y = Z)', '![U]: ((![X]: mul(U,X) = X) => U = e)',
                             '?[X]: ~(p(X) | q(X,e)) <=> $true', 'mul(e,e) != e']:
            f = parse(text)
            self.assertEqual(parse(to_tptp(f)), f, text)

    def test_malformed_and_inconsistent_inputs(self):
        for bad in ['![x]: p(x)', 'mul(X,', 'X', 'p(X) q']:
            with self.assertRaises(ParseError):
                parse(bad)
        with self.assertRaises(ParseError):
            signature([parse('f(e) = e'), parse('f(e,e) = e')])


class Evaluator(unittest.TestCase):
    def test_z2_is_an_abelian_group(self):
        sig = signature([parse(a) for a in GROUP])
        self.assertEqual(check_model(z2(), [parse(a) for a in GROUP], sig), (True, None))
        self.assertTrue(evaluate(parse('![X,Y]: mul(X,Y) = mul(Y,X)'), z2()))
        self.assertFalse(evaluate(parse('![X]: mul(X,X) = X'), z2()))

    def test_partial_or_out_of_domain_tables_are_rejected(self):
        m = z2(); del m.functions['mul'][(1, 1)]
        self.assertFalse(check_model(m, [parse(a) for a in GROUP], signature([parse(a) for a in GROUP]))[0])
        m = z2(); m.functions['inv'][(1,)] = 7
        self.assertFalse(check_model(m, [parse(a) for a in GROUP], signature([parse(a) for a in GROUP]))[0])


@unittest.skipUnless(READY, 'pinned CaDiCaL / E prover missing')
class ModelFinding(unittest.TestCase):
    def test_smallest_nonabelian_group_is_found_and_independently_checked(self):
        from genesis.modelfind import find_model
        formulas = [parse(a) for a in GROUP] + [('not', parse('![X,Y]: mul(X,Y) = mul(Y,X)'))]
        model, record = find_model(formulas, max_size=6, seconds=60)
        self.assertEqual((record['status'], record['size']), ('MODEL_FOUND', 6))
        self.assertTrue(check_model(model, formulas, signature(formulas))[0])

    def test_no_model_is_not_a_proof(self):
        from genesis.modelfind import find_model
        model, record = find_model([parse(a) for a in GROUP] + [('not', parse('![X]: mul(X,e) = X'))], max_size=4)
        self.assertIsNone(model)
        self.assertEqual(record['status'], 'NO_MODEL_UP_TO_SIZE')
        self.assertNotIn('PROVED', json.dumps(record))

    def test_e_proves_a_true_goal_and_does_not_prove_a_false_one(self):
        from genesis.verification.eprover import prove
        axioms = [parse(a) for a in GROUP]
        good = prove(axioms, parse('![X]: mul(X,e) = X'), seconds=20)
        self.assertEqual(good['status'], 'THEOREM')
        self.assertFalse(good['proof_replayed'])
        bad = prove(axioms, parse('![X,Y]: mul(X,Y) = mul(Y,X)'), seconds=3)
        self.assertNotEqual(bad['status'], 'THEOREM')


@unittest.skipUnless(READY, 'pinned CaDiCaL / E prover missing')
class ExperimentB(unittest.TestCase):
    def test_small_preregistered_run(self):
        from genesis.experiment_b import ExperimentBPrereg, run_experiment, family, family_digest
        from genesis.store import Store
        prereg = ExperimentBPrereg(problems=4, budget_seconds=4)
        self.assertEqual(family_digest(family(prereg.seed, 4, 3)), family_digest(family(prereg.seed, 4, 3)))
        with tempfile.TemporaryDirectory() as d:
            summary = run_experiment(Path(d) / 'b', prereg)
            self.assertIn(summary['gate']['decision'], ('CONTINUE', 'KILL'))
            self.assertEqual(summary['contradictions'], [])
            self.assertFalse(summary['promotion_allowed'])
            states = {r['status'] for r in summary['rows']}
            self.assertTrue(states <= {'PROVED', 'GHOST_FOUND', 'UNSETTLED', 'HARNESS_ERROR'})
            self.assertEqual(len(summary['rows']), 4 * 3)
            with Store(Path(d) / 'b') as s:
                s.verify()
                for (h,) in s.db.execute('SELECT receipt FROM attempts'):
                    outcome = s.get(h)['outcome']
                    if outcome['status'] == 'GHOST_FOUND':
                        self.assertIn('ghost', outcome)


if __name__ == '__main__':
    unittest.main()
