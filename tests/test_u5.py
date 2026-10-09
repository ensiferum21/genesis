import unittest

import numpy as np

from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.invariants import InvariantViolation, inv21_randomised_slice, inv22_stop_audit
from gap_engine.kernel.ledger import Ledger
from gap_engine.u5.funnel import measure_funnel
from gap_engine.u5.scheduler import Scheduler, StopAuditor

from tests.helpers import mini_world


class TestScheduler(unittest.TestCase):
    def test_randomised_slice_logged_with_propensity(self):
        led = Ledger()
        s = Scheduler(["a", "b", "c"], led, np.random.default_rng(0), explore_frac=0.5)
        n_rand = 0
        for _ in range(200):
            arm, rnd, prop = s.choose(["a", "b", "c"])
            s.record(arm, rnd, prop, cost=1.0, reward={"a": 1.0, "b": 0.2, "c": 0.0}[arm])
            n_rand += rnd
            self.assertTrue(0 < prop <= 1)
        self.assertGreater(n_rand, 60)
        dr = s.dr_report()
        self.assertGreater(dr["a"], dr["c"])
        counts = {k: sum(1 for l in s.logs if l.kind == k and not l.randomised) for k in "abc"}
        self.assertGreater(counts["a"], counts["c"])          # Thompson exploits the best arm

    def test_inv21(self):
        with self.assertRaises(InvariantViolation):
            inv21_randomised_slice(0.0, False)
        with self.assertRaises(InvariantViolation):
            inv21_randomised_slice(0.1, True)

    def test_stop_rule_needs_flat_progress_and_low_value(self):
        s = Scheduler(["a"], Ledger(), np.random.default_rng(0), shadow_price=10.0, stop_k=2)
        for _ in range(10):
            s.record("a", False, 1.0, cost=1.0, reward=0.0)
        rising = [float(i) for i in range(10)]
        self.assertFalse(s.should_stop(rising) or s.should_stop(rising))
        flat = [5.0] * 10
        s.below = 0
        self.assertFalse(s.should_stop(flat))
        self.assertTrue(s.should_stop(flat))

    def test_stop_audit_fraction(self):
        aud = StopAuditor(Ledger(), np.random.default_rng(0), audit_frac=0.2)
        for i in range(20):
            aud.stop(f"line{i}", ["a"], {"a": 0.0}, "x")
        self.assertGreaterEqual(aud.n_audited, 4)
        with self.assertRaises(InvariantViolation):
            inv22_stop_audit(20, 1, 0.2)


class TestFunnel(unittest.TestCase):
    def test_funnel_classifies_failures(self):
        w = mini_world()
        fn = measure_funnel(w, BudgetBroker.from_policy(100.0), seed=0, sample=8)
        self.assertGreater(fn.sampled, 0)
        self.assertEqual(fn.retrieve + fn.plan + fn.propose, fn.sampled)
        self.assertIn(fn.bottleneck(), {"retrieve", "plan", "propose", "check"})
        self.assertEqual(fn.check_rejects, 0)


if __name__ == "__main__":
    unittest.main()
