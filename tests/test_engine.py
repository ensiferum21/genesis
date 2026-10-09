import unittest

import numpy as np

from gap_engine.adapters.synthetic import SyntheticWorld, WorldSpec
from gap_engine.engine.arms import ARMS
from gap_engine.engine.loop import Campaign
from gap_engine.experiments.prereg import PreregViolation, load_verified, write_prereg
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.u1.archive import SteppingStoneArchive
from gap_engine.u1.fingerprint import measure_fingerprints
from gap_engine.u2.design import DropoutConfig, plan_design

from tests.helpers import mini_world


class TestSyntheticArms(unittest.TestCase):
    def test_dropout_beats_gate_on_planted_synergies(self):
        w = SyntheticWorld(WorldSpec(), seed=3)
        u = ARMS["U"][0](w, 120.0, 1, False, dict(tau=10, delta=2, min_tasks=3, min_ov=2))
        g = ARMS["G"][0](w, 120.0, 1, False, dict(direct=5, pair=4, rep=1, single_rep=1))
        truth = w.true_pairs()
        self.assertGreaterEqual(len(u.pairs & truth), 4)
        self.assertEqual(len(g.pairs), 0)
        self.assertLessEqual(u.spent, 120.0 + 1e-9)

    def test_auto_switches_to_blocks_on_large_pools(self):
        w = SyntheticWorld(WorldSpec(n_dud=270, fp_cost=0.1), seed=4)
        u = ARMS["U"][0](w, 150.0, 1, False, dict(tau=15, delta=2, min_tasks=2, min_ov=2))
        self.assertEqual(u.notes["mode"], "blocked")
        self.assertGreaterEqual(len(u.pairs & w.true_pairs()), 2)

    def test_blocked_design_raises_co_inclusion(self):
        rng = np.random.default_rng(0)
        X, rec, _ = plan_design(300, 150, rng, DropoutConfig(mode="blocked"), proposals=[(1, 2, 5), (3, 4, 5)])
        self.assertGreater((X[:, 1] & X[:, 2]).sum(), 10)
        Xp, recp, _ = plan_design(300, 150, rng, DropoutConfig(mode="plain"))
        self.assertLess((Xp[:, 1] & Xp[:, 2]).sum(), 5)


class TestU1(unittest.TestCase):
    def test_fingerprints_and_archive(self):
        w = SyntheticWorld(WorldSpec(), seed=5)
        fps = measure_fingerprints(w, BudgetBroker.from_policy(100.0), seed=0)
        self.assertTrue(fps.measured.all())
        props = fps.pair_proposals(min_ov=2)
        truth = w.true_pairs()
        self.assertTrue(any((i, j) in truth for i, j, _ in props[:20]))
        arch = SteppingStoneArchive(n_clusters=4)
        clusters = np.arange(w.T) % 4
        kept = sum(arch.offer(f"c{i}", fps.F[i], clusters) for i in range(w.n))
        self.assertGreater(kept, 0)
        self.assertLessEqual(len(arch.members()), arch.cap)

    def test_fingerprint_budget_cap_respected(self):
        w = SyntheticWorld(WorldSpec(), seed=5)
        b = BudgetBroker.from_policy(20.0)          # fingerprint cap 25% = 5 units = 20 probes
        fps = measure_fingerprints(w, b, seed=0)
        self.assertLessEqual(b.spent.get("fingerprint", 0.0), 5.0 + 1e-9)
        self.assertLess(fps.measured.sum(), w.n)


class TestCampaign(unittest.TestCase):
    def test_campaign_runs_within_budget_and_ledger_verifies(self):
        w = mini_world()
        c = Campaign(w, 60.0, seed=0, policy="u5")
        res = c.run(max_steps=8)
        self.assertLessEqual(res.spent, 60.0 + 1e-6)
        self.assertTrue(c.ledger.verify())
        for lid in res.accepted:                   # every admission cites a ledgered gate decision
            self.assertIn(lid, w.store.lemmas)
        admits = [e for e in c.ledger.entries if e["kind"] == "library.admit"]
        for e in admits:
            self.assertTrue(any(g["hash"] == e["payload"]["decision"] for g in c.ledger.entries))


class TestPrereg(unittest.TestCase):
    def test_lock(self):
        import os, tempfile, json
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "pre.json")
            write_prereg(p, {"a": 1})
            self.assertEqual(load_verified(p), {"a": 1})
            with self.assertRaises(PreregViolation):
                write_prereg(p, {"a": 2})
            with open(p) as fh:
                doc = json.load(fh)
            doc["plan"]["a"] = 2
            with open(p, "w") as fh:
                json.dump(doc, fh)
            with self.assertRaises(PreregViolation):
                load_verified(p)


if __name__ == "__main__":
    unittest.main()
