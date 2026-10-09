"""DEV-only readiness is not allowed to certify anything or peek at held-out splits."""
import unittest
import numpy as np

from gap_engine.engine.readiness import AdmissionReadinessBuffer, min_optimistic_wins
from gap_engine.engine.loop import Campaign
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.gates import GateJ, Library
from gap_engine.kernel.ledger import Ledger
from tests.helpers import mini_world


class SpyWorld:
    def __init__(self, dev_wins=5):
        self.dev_wins = dev_wins
        self.calls = []
        self.pool = ['a']
        self.base_ids = []
        self.accepted_extra = []

    def n_tasks(self, split):
        return 20

    def eval_cost(self, library, split):
        return 1.0

    def outcomes(self, library, split, reps, seed):
        self.calls.append(split)
        n = self.dev_wins if split == 'DEV' else 5
        v = np.zeros(20, dtype=np.int8)
        if 'a' in library:
            v[:n] = 1
        return np.tile(v, (reps, 1))


class TestReadiness(unittest.TestCase):
    def setup_buffer(self, dev_wins=5, budget=100):
        w = SpyWorld(dev_wins)
        led = Ledger()
        lib = Library(led)
        broker = BudgetBroker.from_policy(budget, led)
        gate = GateJ(w, broker, led, alpha=0.05, reps=1)
        return w, led, lib, broker, gate, AdmissionReadinessBuffer(w, lib, gate, led)

    def test_optimistic_threshold_does_not_change_alpha(self):
        self.assertEqual(min_optimistic_wins(20, 0.05), 3)
        self.assertIsNone(min_optimistic_wins(1, 0.05))

    def test_preflight_never_looks_at_select_confirm_or_sealed(self):
        w, led, lib, broker, gate, buf = self.setup_buffer()
        buf.offer([(('a',), .01, 'single')])
        d = buf.preflight(123)
        self.assertTrue(d.ready)
        self.assertEqual(w.calls, ['DEV', 'DEV'])
        self.assertEqual(broker.spent['gate'], 2.0)
        self.assertEqual(len(w.accepted_extra), 0)
        self.assertTrue(led.verify())

    def test_gate_alone_can_admit_and_no_repeated_same_unit(self):
        w, led, lib, broker, gate, buf = self.setup_buffer()
        buf.offer([(('a',), .01, 'single'), (('a',), .01, 'single')])
        self.assertEqual(len(buf.pending), 1)
        d = buf.try_admit(42)
        self.assertTrue(d.ready)
        self.assertIn('SELECT', w.calls)
        self.assertIn('CONFIRM', w.calls)
        self.assertEqual(w.accepted_extra, ['a'])
        self.assertEqual(buf.pending, {})
        self.assertEqual(buf.offer([(('a',), .01, 'single')]), 0)
        self.assertTrue(led.verify())

    def test_weak_dev_signal_defers_without_peeking(self):
        w, led, lib, broker, gate, buf = self.setup_buffer(dev_wins=1)
        buf.offer([(('a',), .01, 'single')])
        d = buf.try_admit(123)
        self.assertFalse(d.ready)
        self.assertEqual(d.reason, 'low_dev_forecast')
        self.assertEqual(w.calls, ['DEV', 'DEV'])
        self.assertEqual(len(w.accepted_extra), 0)
        self.assertEqual(len(buf.pending), 1)
        self.assertTrue(led.verify())

    def test_insufficient_budget_defers_without_any_evaluation(self):
        w, led, lib, broker, gate, buf = self.setup_buffer(budget=6)
        buf.offer([(('a',), .01, 'single')])
        d = buf.try_admit(0)
        self.assertFalse(d.ready)
        self.assertEqual(d.reason, 'insufficient_reserved_budget')
        self.assertEqual(w.calls, [])
        self.assertTrue(led.verify())

    def test_experimental_policy_does_not_change_frozen_v2n(self):
        w = mini_world()
        old = Campaign(w, 60, seed=1, admission_strategy='select_split')
        self.assertIsNone(old.readiness_buffer)
        w = mini_world()
        new = Campaign(w, 60, seed=1, admission_strategy='power_aware_devbuffer')
        self.assertIsNotNone(new.readiness_buffer)
        self.assertEqual(new.gate.alpha, .05)


if __name__ == '__main__':
    unittest.main()
