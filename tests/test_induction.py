import unittest

import numpy as np

from gap_engine.adapters.induction.checker import CheckError, LemmaStore, check_proof
from gap_engine.adapters.induction.conjecture import canonical, generalise_stuck, generate
from gap_engine.adapters.induction.prover import Prover, lpo_gt, lpo_gt_ground, PRECEDENCE
from gap_engine.adapters.induction.tasks import PROPERTIES, TEXTBOOK, validated_properties
from gap_engine.adapters.induction.terms import V, show
from gap_engine.adapters.induction.theory import Equation, Theory, counterexample

TH = Theory.default()
P = TH.parser()


def E(s):
    return Equation(*P.parse_eq(s))


class TestTerms(unittest.TestCase):
    def test_parse_show_roundtrip(self):
        for s in ["plus x (S y) = S (plus x y)", "rev (app xs (Cons x Nil)) = Cons x (rev xs)",
                  "take n (take m xs) = take (min n m) xs"]:
            eq = E(s)
            self.assertEqual(E(eq.text()), eq)

    def test_evaluation(self):
        self.assertEqual(TH.evaluate(P.parse_term("plus 2 3"), {}), 5)
        self.assertEqual(TH.evaluate(P.parse_term("rev xs"), {"xs": (1, 2, 3)}), (3, 2, 1))
        self.assertEqual(TH.evaluate(P.parse_term("rot 1 xs"), {"xs": (1, 2, 3)}), (2, 3, 1))

    def test_all_properties_survive_testing(self):
        ok, bad = validated_properties(TH, PROPERTIES + TEXTBOOK)
        self.assertEqual(bad, [])

    def test_counterexample_found_for_false(self):
        self.assertIsNotNone(counterexample(TH, E("plus x y = x"), np.random.default_rng(0)))
        self.assertIsNotNone(counterexample(TH, E("rev xs = xs"), np.random.default_rng(0)))


class TestOrdering(unittest.TestCase):
    T = {f: k for k, f in enumerate(PRECEDENCE)}

    def test_lpo_orients_classics(self):
        for s in ["plus x Z = x", "plus x (S y) = S (plus x y)", "app (app xs ys) zs = app xs (app ys zs)",
                  "len (app xs ys) = plus (len xs) (len ys)", "qrev xs ys = app (rev xs) ys"]:
            eq = E(s)
            self.assertTrue(lpo_gt(eq.lhs, eq.rhs, self.T), s)

    def test_ground_lpo_total_on_permutations(self):
        a, b = P.parse_term("plus x y"), P.parse_term("plus y x")
        self.assertNotEqual(lpo_gt_ground(a, b, self.T), lpo_gt_ground(b, a, self.T))


class TestProverAndChecker(unittest.TestCase):
    def prove(self, s, lib=None, fuel=6000, depth=2):
        lib = lib or {}
        att = Prover(TH, lib, fuel=fuel, max_depth=depth).prove(E(s))
        return att

    def test_classics_prove_and_check(self):
        lib = {}
        for s in ["plus x Z = x", "plus x (S y) = S (plus x y)", "plus x y = plus y x",
                  "app xs Nil = xs", "app (app xs ys) zs = app xs (app ys zs)",
                  "rev (app xs ys) = app (rev ys) (rev xs)", "rev (rev xs) = xs",
                  "app (take n xs) (drop n xs) = xs"]:
            att = self.prove(s, lib)
            self.assertTrue(att.proved, s)
            self.assertTrue(check_proof(TH, lib, E(s), att.proof))
            lib[s] = E(s)

    def test_false_statements_never_proved(self):
        for s in ["plus x y = x", "rev xs = xs", "app xs ys = app ys xs", "minus x y = minus y x",
                  "len (app xs ys) = len xs"]:
            self.assertFalse(self.prove(s, fuel=4000).proved, s)

    def test_lemmas_are_needed_at_solver_budget(self):
        lib = {"z": E("plus x Z = x"), "s": E("plus x (S y) = S (plus x y)")}
        self.assertFalse(Prover(TH, {}, fuel=60, max_depth=2).prove(E("plus x y = plus y x")).proved)
        self.assertTrue(Prover(TH, lib, fuel=60, max_depth=2).prove(E("plus x y = plus y x")).proved)
        only_z = {"z": lib["z"]}
        self.assertFalse(Prover(TH, only_z, fuel=60, max_depth=1).prove(E("plus x y = plus y x")).proved)


class TestCheckerAdversarial(unittest.TestCase):
    def test_forged_ih_substitution_rejected(self):
        # "x = Z" is false; forge a step case that instantiates the fixed eigenvariable
        goal = Equation(V("x"), ("Z",))
        forged = {"rule": "induction", "var": "x", "fresh": ["n1"],
                  "base": {"rule": "rewrite", "left": [], "right": []},
                  "step": {"rule": "rewrite",
                           "left": [((1,), ("ih", 0), 1, {"n1": ("S", V("n1"))})], "right": []}}
        with self.assertRaises(CheckError):
            check_proof(TH, {}, goal, forged)

    def test_unverified_lemma_rejected(self):
        goal = E("plus x y = plus y x")
        pf = {"rule": "rewrite", "left": [((), ("lemma", "comm"), 1, {"x": V("x"), "y": V("y")})], "right": []}
        with self.assertRaises(CheckError):
            check_proof(TH, {}, goal, pf)

    def test_mismatched_instance_rejected(self):
        goal = E("plus Z y = y")
        pf = {"rule": "rewrite", "left": [((), ("def", "plus", 1), 1, {"x": V("y"), "y": V("y")})], "right": []}
        with self.assertRaises(CheckError):
            check_proof(TH, {}, goal, pf)

    def test_ill_sorted_binding_rejected(self):
        goal = E("plus Z y = y")
        pf = {"rule": "rewrite", "left": [((), ("def", "plus", 0), 1, {"y": ("Nil",)})], "right": []}
        with self.assertRaises(CheckError):
            check_proof(TH, {}, goal, pf)

    def test_fresh_clash_rejected(self):
        goal = E("plus x Z = x")
        good = Prover(TH, {}, fuel=1000).prove(goal).proof
        bad = dict(good)
        bad["fresh"] = ["x"]
        with self.assertRaises(CheckError):
            check_proof(TH, {}, goal, bad)

    def test_self_citation_rejected(self):
        st = LemmaStore(TH)
        goal = E("plus x Z = x")
        pf = {"rule": "rewrite", "left": [((), ("lemma", "L"), 1, {"x": V("x")})], "right": []}
        with self.assertRaises(CheckError):
            st.verify("L", goal, pf)

    def test_legacy_snapshot_requires_replay(self):
        st = LemmaStore(TH)
        refl = {"rule": "rewrite", "left": [], "right": []}
        st.verify("L", E("Z = Z"), refl)
        old = dict(st.__dict__)
        old.pop("_trusted_lemmas")
        restored = LemmaStore.__new__(LemmaStore)
        restored.__setstate__(old)
        with self.assertRaisesRegex(CheckError, "requires full proof replay"):
            restored.verify("L2", E("Z = Z"), refl)
        restored.replay_legacy()
        self.assertTrue(restored.verify("L2", E("Z = Z"), refl))

    def test_forged_legacy_snapshot_cannot_replay(self):
        st = LemmaStore(TH)
        refl = {"rule": "rewrite", "left": [], "right": []}
        st.verify("L", E("Z = Z"), refl)
        old = dict(st.__dict__)
        old.pop("_trusted_lemmas")
        old["lemmas"] = {"L": E("Z = S Z")}
        restored = LemmaStore.__new__(LemmaStore)
        restored.__setstate__(old)
        with self.assertRaises(CheckError):
            restored.replay_legacy()
        with self.assertRaises(CheckError):
            restored.verify("BAD", E("Z = S Z"), refl)

    def test_mutated_public_registry_cannot_certify_false_theorem(self):
        st = LemmaStore(TH)
        refl = {"rule": "rewrite", "left": [], "right": []}
        st.verify("L", E("Z = Z"), refl)
        st.lemmas["L"] = E("Z = S Z")
        forged = {"rule": "rewrite",
                  "left": [((), ("lemma", "L"), 1, {})], "right": []}
        with self.assertRaisesRegex(CheckError, "registry differs"):
            st.verify("BAD", E("Z = S Z"), forged)
        self.assertNotIn("BAD", st.lemmas)

    def test_injected_public_lemma_rejected(self):
        st = LemmaStore(TH)
        st.lemmas["INJECTED"] = E("Z = S Z")
        with self.assertRaisesRegex(CheckError, "registry differs"):
            st.verify("L", E("Z = Z"), {"rule": "rewrite", "left": [], "right": []})

    def test_duplicate_id_different_unproved_goal_rejected(self):
        st = LemmaStore(TH)
        refl = {"rule": "rewrite", "left": [], "right": []}
        self.assertTrue(st.verify("same_id", E("Z = Z"), refl))
        with self.assertRaisesRegex(CheckError, "conflicting reuse"):
            st.verify("same_id", E("Z = S Z"), refl)
        self.assertEqual(st.lemmas["same_id"], E("Z = Z"))
        self.assertEqual(len(st.order), 1)

    def test_duplicate_id_different_proof_rejected_even_if_goal_same(self):
        st = LemmaStore(TH)
        eq = E("Z = Z")
        refl = {"rule": "rewrite", "left": [], "right": []}
        self.assertTrue(st.verify("same_id", eq, refl))
        self.assertTrue(st.verify("same_id", eq, {"right": [], "left": [], "rule": "rewrite"}))
        with self.assertRaisesRegex(CheckError, "conflicting reuse"):
            st.verify("same_id", eq, {"rule": "rewrite", "left": [], "right": [], "extra": 1})
        with self.assertRaisesRegex(CheckError, "conflicting reuse"):
            st.verify("same_id", eq, {"rule": "unknown"})

    def test_lemma_proof_snapshot_rejects_caller_mutation(self):
        st = LemmaStore(TH)
        eq = E("Z = Z")
        proof = {"rule": "rewrite", "left": [], "right": []}
        st.verify("L", eq, proof)
        proof["rule"] = "unknown"
        self.assertEqual(st.proofs["L"]["rule"], "rewrite")
        with self.assertRaises(CheckError):
            st.verify("L", eq, proof)
        self.assertTrue(st.verify("L", eq, {"rule": "rewrite", "left": [], "right": []}))

    def test_lemma_proof_snapshot_detects_store_mutation(self):
        st = LemmaStore(TH)
        eq = E("Z = Z")
        proof = {"rule": "rewrite", "left": [], "right": []}
        st.verify("L", eq, proof)
        st.proofs["L"]["rule"] = "unknown"
        with self.assertRaises(CheckError):
            st.verify("L", eq, proof)

    def test_wrong_final_terms_rejected(self):
        goal = E("plus Z y = Z")
        pf = {"rule": "rewrite", "left": [((), ("def", "plus", 0), 1, {"y": V("y")})], "right": []}
        with self.assertRaises(CheckError):
            check_proof(TH, {}, goal, pf)


class TestConjectures(unittest.TestCase):
    def test_generation_finds_textbook_lemmas(self):
        cs = generate(TH, {}, themes=["plus", "app", "len"], max_size=6, max_terms=2000)
        texts = {c.text() for c in cs}
        self.assertIn("plus x Z = x", texts)
        self.assertIn("app xs Nil = xs", texts)
        for c in cs:
            self.assertIsNone(counterexample(TH, c.eq, np.random.default_rng(5), trials=100), c.text())

    def test_canonical_renaming(self):
        self.assertEqual(canonical(E("plus b a = plus a b")).text(), canonical(E("plus y x = plus x y")).text())

    def test_lemma_calculation_from_stuck_goal(self):
        att = Prover(TH, {}, fuel=200, max_depth=1).prove(E("rev (rev xs) = xs"))
        self.assertFalse(att.proved)
        stuck = att.stuck[-1]
        props = generalise_stuck(TH, stuck)
        self.assertTrue(any("rev (app" in p.text() for p in props))


if __name__ == "__main__":
    unittest.main()
