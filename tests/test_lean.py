import os
import tempfile
import unittest

from gap_engine.adapters.induction.lean_export import dependency_closure, export_lean_certified
from gap_engine.adapters.induction.lean_selfcheck import parse_lean_term, selfcheck

from tests.helpers import mini_world


def _export(d):
    w = mini_world()
    order = dependency_closure(w.store, list(w.pool))
    items = [(i, "lemma", w.store.lemmas[i], w.store.proofs[i], w.statement(i)) for i in order]
    p = os.path.join(d, "x.lean")
    rep = export_lean_certified(w.theory, items, p)
    return w, p, rep


class TestCertifiedExport(unittest.TestCase):
    def test_export_is_self_consistent_and_mutants_are_caught(self):
        with tempfile.TemporaryDirectory() as d:
            w, p, rep = _export(d)
            self.assertEqual(rep["lemmas"], len(w.pool))
            with open(p) as fh:
                txt = fh.read()
            self.assertIn("induction x generalizing y with", txt)
            self.assertIn("congrArg (fun (hole : N) => N.S hole)", txt)
            ok = selfcheck(p, w.theory)
            self.assertTrue(ok["ok"], ok["problems"])
            self.assertGreater(ok["steps"], 10)
            mutants = {
                # a false calc step
                "step": txt.replace("_ = N.S (N.S (g_plus n1 y)) :=", "_ = N.S (g_plus n1 y) :=", 1),
                # a chain whose start is not the case goal
                "endpoint": txt.replace("calc g_plus (N.S n1) N.Z = N.S (g_plus n1 N.Z) := rfl",
                                        "calc g_plus (N.S n1) (N.S N.Z) = N.S (g_plus n1 (N.S N.Z)) := rfl", 1),
                # a citation of a lemma that is defined later
                "order": txt.replace("(ih0 (y := y))", "(lemma_7 y)", 1),
                # an IH instantiated at the wrong value
                "ih_value": txt.replace("(ih0 (y := y))", "(ih0 (y := N.Z))", 1),
                # a wrong congruence context
                "context": txt.replace("(congrArg (fun (hole : N) => N.S hole) (ih0 (y := y)))",
                                       "(congrArg (fun (hole : N) => N.S (N.S hole)) (ih0 (y := y)))", 1),
                # an rfl that is not definitional
                "rfl": txt.replace("_ = N.S (g_plus N.Z y) := rfl", "_ = N.S (g_plus y N.Z) := rfl", 1),
                # an induction hypothesis used where it is not in scope
                "scope": txt.replace("_ = N.S (N.S (g_plus n1 y)) := (congrArg (fun (hole : N) => N.S hole) (ih0 (y := y)))",
                                     "_ = N.S (N.S (g_plus n1 y)) := (congrArg (fun (hole : N) => N.S hole) (ih3 (y := y)))", 1),
            }
            for name, m in mutants.items():
                self.assertNotEqual(m, txt, name)
                q = os.path.join(d, f"{name}.lean")
                with open(q, "w") as fh:
                    fh.write(m)
                self.assertFalse(selfcheck(q, w.theory)["ok"], name)

    def test_export_rechecks_certificates(self):
        w = mini_world()
        i = w.pool[1]
        bad = {"rule": "rewrite", "left": [], "right": []}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Exception):
                export_lean_certified(w.theory, [(i, "lemma", w.store.lemmas[i], bad, "")],
                                      os.path.join(d, "bad.lean"))

    def test_lemma_citations_are_checked_exactly(self):
        from gap_engine.adapters.induction.checker import LemmaStore
        from gap_engine.adapters.induction.prover import Prover
        from gap_engine.adapters.induction.theory import Equation, Theory
        from gap_engine.adapters.induction.adapter import _lid
        th = Theory.default()
        P = th.parser()
        st = LemmaStore(th)
        items = []
        for s_ in ["plus x Z = x", "plus x (S y) = S (plus x y)", "plus x y = plus y x",
                   "plus (S Z) Z = S Z"]:
            eq = Equation(*P.parse_eq(s_))
            att = Prover(th, dict(st.lemmas), fuel=20000).prove(eq)
            self.assertTrue(att.proved, s_)
            st.verify(_lid(eq), eq, att.proof)
            items.append((_lid(eq), "lemma", eq, att.proof, s_))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.lean")
            export_lean_certified(th, items, p)
            with open(p) as fh:
                txt = fh.read()
            self.assertIn("theorem lemma_3 : g_plus (N.S N.Z) N.Z = N.S N.Z := by", txt)   # ground theorem
            ok = selfcheck(p, th)
            self.assertTrue(ok["ok"], ok["problems"])
            self.assertEqual(ok["theorems"], 4)
            self.assertGreater(ok["cited_steps"], 0)
            muts = {"swap": txt.replace("(lemma_1 y n1)", "(lemma_1 n1 y)", 1),
                    "symm": txt.replace("(Eq.symm (lemma_0 y))", "(lemma_0 y)", 1)}
            for name, m in muts.items():
                self.assertNotEqual(m, txt, name)
                q = os.path.join(d, f"{name}.lean")
                with open(q, "w") as fh:
                    fh.write(m)
                self.assertFalse(selfcheck(q, th)["ok"], name)

    def test_term_round_trip(self):
        self.assertEqual(parse_lean_term("g_plus (N.S x) N.Z"), ("plus", ("S", ("?", "x")), ("Z",)))
        self.assertEqual(parse_lean_term("L.Cons h (g_rev ts)"), ("Cons", ("?", "h"), ("rev", ("?", "ts"))))


if __name__ == "__main__":
    unittest.main()
