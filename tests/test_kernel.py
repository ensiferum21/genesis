import os
import tempfile
import unittest

import numpy as np

from gap_engine.kernel import stats
from gap_engine.kernel.budget import BudgetBroker, BudgetExceeded
from gap_engine.kernel.gates import GateJ, Library, first_order_gate
from gap_engine.kernel.invariants import InvariantViolation
from gap_engine.kernel.ledger import Ledger, LedgerCorrupt
from gap_engine.kernel.records import Bundle, BundleEvidence
from gap_engine.kernel.sealed import SealedStore


class TestLedger(unittest.TestCase):
    def test_chain_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            led = Ledger(p)
            for i in range(5):
                led.append("x", {"i": i})
            self.assertTrue(Ledger(p).verify())
            led.entries[2]["payload"]["i"] = 99
            with self.assertRaises(LedgerCorrupt):
                led.verify()


class TestBudget(unittest.TestCase):
    def test_caps_and_total(self):
        b = BudgetBroker.from_policy(100.0)
        b.charge("evaluation", 50)
        with self.assertRaises(BudgetExceeded):
            b.charge("fingerprint", 26)          # cap 25% of 100
        b.charge("fingerprint", 25)
        with self.assertRaises(BudgetExceeded):
            b.charge("evaluation", 26)           # total 101 > 100
        self.assertEqual(b.affordable_units("evaluation", 5.0), 5)
        self.assertTrue(any(e["kind"] == "budget.refused" for e in b.ledger.entries))

    def test_charges_land_in_the_given_empty_ledger(self):
        led = Ledger()
        b = BudgetBroker.from_policy(10.0, led)
        b.charge("evaluation", 1.0, purpose="x")
        self.assertEqual([e["kind"] for e in led.entries], ["budget.charge"])

    def test_negative_charge_rejected(self):
        b = BudgetBroker.from_policy(10.0)
        with self.assertRaises(ValueError):
            b.charge("evaluation", -1)


class TestSealed(unittest.TestCase):
    def test_screen_and_judge(self):
        s = SealedStore()
        s.seal("CONFIRM", [("plus x y = plus y x", 1), ("len (app xs ys) = plus (len xs) (len ys)", 2)])
        kept, rej = s.screen(["plus x y = plus y x", "PLUS  x y = plus y x", "rev (rev xs) = xs"])
        self.assertEqual(rej, [0, 1])
        self.assertEqual(kept, [2])
        from gap_engine.kernel.sealed import SealedAccessError
        with self.assertRaises(SealedAccessError):
            s.judge("CONFIRM", lambda item: item == 1, actor="test", purpose="unit")
        res = s.judge("CONFIRM", lambda item: item == 1, actor="test",
                      purpose="unit", unsafe_dev_callback=True)
        self.assertFalse(res["independent_custody_proven"])
        self.assertFalse(res["eligible_for_scientific_promotion"])
        self.assertEqual(res["solved"], 1)
        self.assertNotIn("plus", str(res["outcomes"]))   # only opaque hashes leak


class TestStats(unittest.TestCase):
    def test_mcnemar_sample_size_matches_doc(self):
        self.assertEqual(stats.mcnemar_sample_size(0.10, 0.05, 0.05, 0.8), 469)
        self.assertEqual(stats.mcnemar_sample_size(0.10, 0.05, 0.0125, 0.8), 667)

    def test_bh(self):
        rej = stats.benjamini_hochberg([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205], 0.05)
        self.assertEqual(rej.tolist(), [True, True, False, False, False, False, False, False])

    def test_ebh(self):
        rej = stats.e_bh([100.0, 50.0, 1.0, 0.5], 0.1)
        self.assertEqual(rej.tolist(), [True, True, False, False])

    def test_holm(self):
        self.assertEqual(stats.holm([0.01, 0.04, 0.03, 0.005], 0.05).tolist(), [True, False, False, True])

    def test_tost(self):
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 400)
        r = stats.tost_paired(a, a + rng.normal(0, 0.05, 400), margin=0.05)
        self.assertEqual(r.verdict, "EQUIVALENT")
        r = stats.tost_paired(a, a - 1.0, margin=0.1)
        self.assertEqual(r.verdict, "DIFFERENT")
        r = stats.tost_paired(a[:5], a[:5] + rng.normal(0, 1, 5), margin=0.01)
        self.assertEqual(r.verdict, "INCONCLUSIVE")

    def test_cascade(self):
        y11 = np.array([1, 1, 1, 0.5]); y10 = np.array([0.5, 0.5, 0.5, 0.5])
        y01 = np.array([0.5, 0.5, 0.5, 0.5]); y00 = np.array([0.5, 0.5, 0.5, 0.5])
        c = stats.cascade_2x2(y11, y10, y01, y00)
        self.assertAlmostEqual(c.estimate, 0.375)
        with self.assertRaises(ValueError):
            stats.cascade_2x2(y11, y10[:3], y01, y00)

    def test_attribution_recovers_pair_and_single(self):
        rng = np.random.default_rng(1)
        R, n = 200, 20
        X = rng.random((R, n)) < 0.5
        T = 12
        P = np.full((R, T), 0.03)
        P[:, :6] = np.where((X[:, 3] & X[:, 7])[:, None], 0.85, 0.03)
        P[:, 6:12] = np.where(X[:, 11][:, None], 0.85, 0.03)
        Y = (rng.random((R, T)) < P).astype(int)
        res = stats.llr_attribution(X, Y, np.ones(n, bool), np.ones((n, n), bool), 15, 2, 3)
        self.assertIn((3, 7), res.pairs)
        self.assertIn(11, res.direct)
        self.assertNotIn(3, res.direct)
        self.assertLess(res.pair_pvalues[(3, 7)], 1e-6)

    def test_ipw_dr(self):
        acts = ["a", "b", "a", "b"]
        v = stats.ipw_values(acts, [0.5] * 4, [1, 0, 1, 0], ["a", "b"])
        self.assertEqual(v, {"a": 1.0, "b": 0.0})
        dr = stats.doubly_robust_values(acts, [0.5] * 4, [1, 0, 1, 0], {"a": 1.0, "b": 0.0}, ["a", "b"])
        self.assertEqual(dr, {"a": 1.0, "b": 0.0})


class _ToyEval:
    """Two candidates that only work together on SELECT and CONFIRM."""

    def outcomes(self, library, split, reps, seed):
        rng = np.random.default_rng(seed + {"SELECT": 1, "CONFIRM": 2}[split])
        T = 40
        p = np.full(T, 0.05)
        if {"a", "b"} <= library:
            p[:20] = 0.9
        return (rng.random((reps, T)) < p).astype(int)

    def eval_cost(self, library, split):
        return 1.0


class TestGateJ(unittest.TestCase):
    def setUp(self):
        self.led = Ledger()
        self.broker = BudgetBroker.from_policy(1000.0, self.led)
        self.lib = Library(self.led)
        self.gj = GateJ(_ToyEval(), self.broker, self.led, alpha=0.05, reps=3)

    def test_pair_passes_and_member_alone_refused(self):
        b = Bundle(members=("a", "b"), kind="pair",
                   evidence=BundleEvidence(votes=5, pvalue=1e-6, fdr_rejected=True))
        d = self.gj.decide(b, frozenset())
        self.assertTrue(d.passed, d.reasons)
        with self.assertRaises(InvariantViolation):
            self.lib.admit(["a"], {"a": 1}, d)                  # INV-18
        self.lib.admit(["a", "b"], {"a": 1, "b": 2}, d)
        self.assertEqual(self.lib.ids(), frozenset({"a", "b"}))

    def test_single_fails_first_order(self):
        d = first_order_gate(_ToyEval(), self.broker, self.led, "a", frozenset())
        self.assertFalse(d.passed)

    def test_unlogged_decision_refused(self):
        b = Bundle(members=("a", "b"), kind="pair",
                   evidence=BundleEvidence(votes=5, pvalue=1e-6, fdr_rejected=True))
        d = self.gj.decide(b, frozenset())
        forged = d.model_copy(update={"ledger_hash": "f" * 64})
        with self.assertRaises(InvariantViolation):
            self.lib.admit(["a", "b"], {}, forged)

    def test_forged_and_mutated_decisions_refused(self):
        # (a) a fabricated decision citing a non-gate ledger entry
        self.broker.charge("evaluation", 1.0, purpose="x")
        charge_hash = self.led.entries[-1]["hash"]
        from gap_engine.kernel.records import GateDecision
        forged = GateDecision(gate="J", bundle=("fakeA", "fakeB"), passed=True, stage="CONFIRM",
                              ledger_hash=charge_hash)
        with self.assertRaises(InvariantViolation):
            self.lib.admit(["fakeA", "fakeB"], {}, forged)
        # (b) a real failed decision with its flag flipped by research code
        b = Bundle(members=("a", "b"), kind="pair",
                   evidence=BundleEvidence(votes=5, pvalue=0.3, fdr_rejected=False))
        d = self.gj.decide(b, frozenset())
        self.assertFalse(d.passed)
        d.passed = True
        with self.assertRaises(InvariantViolation):
            self.lib.admit(["a", "b"], {}, d)
        # (c) relabelling the gate does not bypass INV-18
        b2 = Bundle(members=("a", "b"), kind="pair",
                    evidence=BundleEvidence(votes=5, pvalue=1e-6, fdr_rejected=True))
        d2 = self.gj.decide(b2, frozenset())
        self.assertTrue(d2.passed)
        d2.gate = "first_order"
        with self.assertRaises(InvariantViolation):
            self.lib.admit(["a"], {}, d2)
        # (d) a decision can be used once
        self.lib.admit(["a", "b"], {}, d2)
        with self.assertRaises(InvariantViolation):
            self.lib.admit(["a", "b"], {}, d2)

    def test_fdr_rejected_bundle_blocked(self):
        b = Bundle(members=("a", "b"), kind="pair",
                   evidence=BundleEvidence(votes=5, pvalue=0.3, fdr_rejected=False))
        self.assertFalse(self.gj.decide(b, frozenset()).passed)


class _IncrementalEval:
    """good solves every task; bad poisons a library containing it."""

    def outcomes(self, library, split, reps, seed):
        T = 40
        y = np.zeros((reps, T), dtype=int)
        if "good" in library and "bad" not in library:
            y[:] = 1
        return y

    def eval_cost(self, library, split):
        return 1.0


class _DevBuildEval:
    """DEV is used to build; full SELECT and CONFIRM independently validate."""

    def __init__(self):
        self.calls = []

    def outcomes(self, library, split, reps, seed):
        self.calls.append(split)
        T = {"DEV": 12, "SELECT": 24, "CONFIRM": 20}[split]
        y = np.zeros((reps, T), dtype=int)
        if "good" in library and "bad" not in library:
            y[:] = 1
        return y

    def eval_cost(self, library, split):
        return 1.0


class TestIncrementalGate(unittest.TestCase):
    def test_harmful_unit_is_dropped_before_validation(self):
        led = Ledger()
        broker = BudgetBroker.from_policy(1000.0, led)
        gate = GateJ(_IncrementalEval(), broker, led, alpha=0.05, reps=1)
        # Put the harmful proposal first: selection must reject it rather than letting it sink
        # the useful proposal, which is exactly the round-2b all-or-nothing failure mode.
        d = gate.decide_incremental([("bad",), ("good",)], frozenset(), seed=17)
        self.assertTrue(d.passed, (d.stage, d.reasons, d.stats))
        self.assertEqual(d.bundle, ("good",))
        lib = Library(led)
        lib.admit(["good"], {"good": 1}, d)
        self.assertEqual(lib.ids(), frozenset({"good"}))

    def test_dev_build_preserves_full_select_for_validation(self):
        led = Ledger()
        ev = _DevBuildEval()
        gate = GateJ(ev, BudgetBroker.from_policy(1000.0, led), led, alpha=0.05, reps=1)
        d = gate.decide_incremental_devbuild([("bad",), ("good",)], frozenset(), seed=19)
        self.assertTrue(d.passed, (d.stage, d.reasons, d.stats))
        self.assertEqual(d.bundle, ("good",))
        self.assertEqual(d.stats["select_tasks"], 24.0)
        # All composition calls happen on DEV; SELECT is touched only for final base/candidate validation.
        first_select = ev.calls.index("SELECT")
        self.assertTrue(all(x == "DEV" for x in ev.calls[:first_select]))
        self.assertEqual(ev.calls.count("SELECT"), 2)
        self.assertEqual(ev.calls.count("CONFIRM"), 2)

    def test_joint_unit_is_never_split(self):
        class PairEval(_IncrementalEval):
            def outcomes(self, library, split, reps, seed):
                T = 40
                y = np.zeros((reps, T), dtype=int)
                if {"a", "b"} <= library:
                    y[:] = 1
                return y
        led = Ledger()
        gate = GateJ(PairEval(), BudgetBroker.from_policy(1000.0, led), led, alpha=0.05, reps=1)
        d = gate.decide_incremental([("a", "b")], frozenset(), seed=3)
        self.assertTrue(d.passed)
        self.assertEqual(d.bundle, ("a", "b"))
        with self.assertRaises(InvariantViolation):
            Library(led).admit(["a"], {"a": 1}, d)



if __name__ == "__main__":
    unittest.main()
