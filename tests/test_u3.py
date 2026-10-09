import unittest

from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.invariants import InvariantViolation
from gap_engine.kernel.ledger import Ledger
from gap_engine.kernel.records import HarvestRecord
from gap_engine.u3.admission import admit_dataset
from gap_engine.u3.dream import default_ranker, g1_test, select_top
from gap_engine.u3.harvest import harvest

from tests.helpers import mini_world


class TestAdmission(unittest.TestCase):
    def test_unverified_and_sealed_removed(self):
        led = Ledger()
        w = mini_world(led)
        items = [HarvestRecord(text="plus x Z = x", source_task="t", kind="byproduct_lemma", kernel_verified=True),
                 HarvestRecord(text="plus x y = x", source_task="t", kind="fantasy", kernel_verified=False),
                 HarvestRecord(text="plus (len xs) (len ys) = len (app ys xs)", source_task="t",
                               kind="byproduct_lemma", kernel_verified=True)]
        man = admit_dataset("d", items, w.sealed, led)
        self.assertEqual([it.text for it in man.items], ["plus x Z = x"])
        self.assertEqual(man.rejected_unverified, 1)
        self.assertEqual(man.rejected_sealed, 1)
        with self.assertRaises(InvariantViolation):
            admit_dataset("d2", items, w.sealed, led, strict=True)
        # a forged kernel_verified flag is not trusted when a verifier is given
        forged = [HarvestRecord(text="plus x y = plus y y", source_task="t", kind="fantasy", kernel_verified=True)]
        known = {e.text() for e in w.store.lemmas.values()}
        man2 = admit_dataset("d3", forged, w.sealed, led, verifier=lambda t: t in known)
        self.assertEqual(man2.items, [])
        self.assertEqual(man2.rejected_unverified, 1)


class TestHarvest(unittest.TestCase):
    def test_harvest_only_adds_verified_non_sealed(self):
        w = mini_world()
        b = BudgetBroker.from_policy(100.0)
        before = set(w.pool)
        hv = harvest(w, b, seed=0)
        for lid in hv.new_pool:
            self.assertIn(lid, w.store.lemmas)            # kernel-verified
            self.assertFalse(w.sealed.near_duplicate(w.statement(lid)))
        self.assertTrue(set(w.pool) >= before)


class TestG1(unittest.TestCase):
    def test_identical_child_is_not_promoted(self):
        led = Ledger()
        w = mini_world(led)
        r0 = default_ranker(w)
        res = g1_test(w, r0, r0, k=3, train_cost=1.0, unit_cost=1.0, ledger=led, forecast=0.0)
        self.assertFalse(res.promoted)
        self.assertTrue(any(e["kind"] == "g1.forecast" for e in led.entries))
        self.assertTrue(len(select_top(w, r0, 3)) == 3)


if __name__ == "__main__":
    unittest.main()
