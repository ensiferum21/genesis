import unittest

import numpy as np

from gap_engine.adapters.induction.checker import LemmaStore
from gap_engine.adapters.induction.mutate import SEALED_MUTATIONS, TRAIN_MUTATIONS, mutate
from gap_engine.adapters.induction.tasks import PROPERTIES, validated_properties
from gap_engine.adapters.induction.theory import Equation, Theory
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.invariants import InvariantViolation, inv19_only_sealed_judges
from gap_engine.u4 import dsl
from gap_engine.u4.cegis import fit_decision_list
from gap_engine.u4.compress import compress
from gap_engine.u4.procedures import BUILTIN, random_program, run, well_typed

TH = Theory.default()
P = TH.parser()


class TestPrograms(unittest.TestCase):
    def test_typing(self):
        self.assertTrue(well_typed(BUILTIN["lemma_calculation"]))
        self.assertFalse(well_typed(("attempt", "generalise", "retry")))      # stuck not produced
        self.assertFalse(well_typed(("refute", "retry")))
        rng = np.random.default_rng(0)
        for _ in range(50):
            self.assertTrue(well_typed(random_program(rng)))

    def test_lemma_calculation_solves_rev_rev(self):
        goal = Equation(*P.parse_eq("rev (rev xs) = xs"))
        ctx = dsl.ResearchContext(TH, LemmaStore(TH), {}, BudgetBroker(total=100.0), fuel=60, seed=0)
        self.assertFalse(dsl.op_attempt(ctx, goal).proved)
        res = run(BUILTIN["lemma_calculation"], ctx, goal, max_cost=2.0)
        self.assertTrue(res.solved)
        for lid in res.lemmas:
            self.assertIn(lid, ctx.store.lemmas)            # every lemma kernel-verified

    def test_compression_prefers_frequent_long_chain(self):
        lc = BUILTIN["lemma_calculation"]
        traces = [lc] * 4 + [("attempt", "deepen")] * 3
        top = compress(traces, top=2)
        self.assertEqual(top[0][0], lc)


class TestPreconditions(unittest.TestCase):
    def test_decision_list_fits_simple_rule(self):
        data = [({"a": True, "b": False}, True)] * 5 + [({"a": False, "b": False}, False)] * 5 + \
               [({"a": True, "b": True}, True)] * 3 + [({"a": False, "b": True}, False)] * 3
        dl = fit_decision_list(data)
        self.assertTrue(dl({"a": True, "b": False}))
        self.assertFalse(dl({"a": False, "b": True}))
        self.assertEqual(dl.size(), 1)

    def test_counterfactual_worlds_cannot_judge(self):
        cf = mutate(TH, "plus_second_arg", TRAIN_MUTATIONS, "counterfactual")
        with self.assertRaises(InvariantViolation):
            inv19_only_sealed_judges(cf.origin)
        sealed = mutate(TH, "plus_swap", SEALED_MUTATIONS, "sealed")
        inv19_only_sealed_judges(sealed.origin)

    def test_mutations_preserve_semantics(self):
        for fam, origin in ((TRAIN_MUTATIONS, "counterfactual"), (SEALED_MUTATIONS, "sealed")):
            for name in fam:
                th = mutate(TH, name, fam, origin)
                ok, bad = validated_properties(th, PROPERTIES[:40])
                self.assertEqual(bad, [], name)


if __name__ == "__main__":
    unittest.main()
