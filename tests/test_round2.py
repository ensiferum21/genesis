import os
import tempfile
import unittest

import numpy as np

from gap_engine.adapters.induction.suite import exclude_handwritten, partition, partition_weighted
from gap_engine.engine.loop import Campaign
from gap_engine.kernel.ledger import Ledger
from gap_engine.u3.dream import default_ranker, select_top
from gap_engine.u3.experience import ExperienceStore

from tests.helpers import mini_world


class TestSuites(unittest.TestCase):
    def test_partition_is_disjoint_and_complete(self):
        tasks = [f"t{i}" for i in range(103)]
        parts = partition(tasks, 4, seed=1)
        flat = [t for p in parts for t in p]
        self.assertEqual(sorted(flat), sorted(tasks))
        self.assertEqual(len(set(flat)), len(flat))


class TestSuiteHygiene(unittest.TestCase):
    def test_partition_weighted_sizes_and_disjointness(self):
        tasks = [f"t{i}" for i in range(100)]
        parts = partition_weighted(tasks, [0.13, 0.29, 0.29, 0.29], seed=3)
        self.assertEqual([len(p) for p in parts], [13, 29, 29, 29])
        flat = [t for p in parts for t in p]
        self.assertEqual(sorted(flat), sorted(tasks))

    def test_exclude_handwritten_drops_properties_and_near_copies(self):
        fresh = "qrev zs (qrev ys (qrev xs ys)) = qrev (app xs (app ys zs)) ys"
        kept, removed = exclude_handwritten(["len (rev xs) = len xs", "len (app ys xs) = len (app xs ys)", fresh])
        self.assertEqual(kept, [fresh])
        self.assertEqual(len(removed), 2)

    def test_world_visible_splits_never_contain_sealed_items(self):
        from gap_engine.adapters.induction.adapter import build_world_from_suite
        # a suite that contains hand-written properties verbatim: with screening, none of the
        # sealed items may reappear in DEV/SELECT/CONFIRM
        texts = ["len (rev xs) = len xs", "sum (rev xs) = sum xs", "rev (rev xs) = xs",
                 "minus (plus x y) y = x", "plus x (plus y z) = plus y (plus x z)",
                 "len (app xs ys) = len (app ys xs)", "app (rev xs) (rev ys) = rev (app ys xs)",
                 "rot (len xs) xs = xs", "sum (app xs ys) = sum (app ys xs)", "double x = plus x x"]
        with tempfile.TemporaryDirectory() as d:
            w = build_world_from_suite("iso", texts, seed=5, cache_dir=d, split=(0.2, 0.1, 0.1), conj_size=4)
            for sp in ("DEV", "SELECT", "CONFIRM"):
                for eq in w.tasks[sp]:
                    self.assertFalse(w.sealed.near_duplicate(eq.text()), (sp, eq.text()))
            self.assertGreater(sum(w.meta["visible_screened"].values()), 0)
            for lid in w.pool:
                self.assertIsNone(w.screen_reason(w.statement(lid)))
            # the cache key depends on the inputs: a different suite is not served from cache
            w2 = build_world_from_suite("iso", texts[:6], seed=5, cache_dir=d, split=(0.2, 0.1, 0.1), conj_size=4)
            self.assertNotEqual(w2.meta["cache_key"], w.meta["cache_key"])


class TestExperience(unittest.TestCase):
    def test_store_roundtrip_screens_sealed_and_detects_tamper(self):
        w = mini_world()
        led = Ledger()
        labels = {c: (1 if i % 2 == 0 else 0) for i, c in enumerate(w.pool)}
        st = ExperienceStore()
        n = st.add_world_labels(w, labels, "mini", cost=10.0, ledger=led)
        self.assertEqual(n, len(w.pool))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "exp.json")
            st.save(p)
            st2 = ExperienceStore.load(p)
            self.assertEqual(st2.items, st.items)
            r = st2.ranker_for(w, default_ranker(w), led)
            self.assertIsNotNone(r)
            # a sealed statement smuggled into the store is screened out on load
            st2.items.append({"text": "plus (len xs) (len ys) = len (app ys xs)", "label": 1, "source": "x"})
            st2.ranker_for(w, default_ranker(w), led)
            ev = [e for e in led.entries if e["kind"] == "experience.load"][-1]["payload"]
            self.assertEqual(ev["rejected_sealed"], 1)
            # editing the saved file is detected
            import json
            with open(p) as fh:
                doc = json.load(fh)
            doc["items"][0]["label"] = 1 - doc["items"][0]["label"]
            with open(p, "w") as fh:
                json.dump(doc, fh)
            with self.assertRaises(ValueError):
                ExperienceStore.load(p)

    def test_forged_false_statement_is_not_trained_on(self):
        w = mini_world()
        led = Ledger()
        st = ExperienceStore(items=[{"text": "plus x y = x", "label": 1, "source": "forged"},
                                    {"text": "plus x Z = x", "label": 1, "source": "ok"}])
        st.ranker_for(w, default_ranker(w), led)
        ev = [e for e in led.entries if e["kind"] == "experience.load"][-1]["payload"]
        self.assertEqual(ev["rejected_unverified"], 1)
        self.assertEqual(ev["kept"], 1)
        self.assertTrue(any(e["kind"] == "dataset.admitted" for e in led.entries))

    def test_held_out_gate_tasks_are_not_trained_on(self):
        w = mini_world()
        led = Ledger()
        held = w.tasks["SELECT"][0].text()
        st = ExperienceStore(items=[{"text": held, "label": 1, "source": "x"}])
        st.ranker_for(w, default_ranker(w), led)
        ev = [e for e in led.entries if e["kind"] == "experience.load"][-1]["payload"]
        self.assertEqual(ev["kept"], 0)


class TestPowerRounds(unittest.TestCase):
    def test_power_round_policy_runs_within_budget(self):
        w = mini_world()
        c = Campaign(w, 80.0, seed=0, policy="u5", round_policy="power", focus_size=4)
        c.do_admit()
        rounds = [e["payload"] for e in c.ledger.entries if e["kind"] == "u5.round"]
        self.assertEqual(len(rounds), 1)
        self.assertLessEqual(rounds[0]["R"], int(0.6 * 80.0) + 1)
        self.assertGreaterEqual(rounds[0]["R_need"], 60)
        self.assertLessEqual(c.broker.used, 80.0 + 1e-9)


class TestFocusRotation(unittest.TestCase):
    def test_none_is_fixed_top_and_rotate_retires_untested_evidence(self):
        w = mini_world()
        c0 = Campaign(w, 80.0, seed=0, policy="u5", round_policy="power", focus_size=4)
        c0._retired.update(w.pool[:3])                      # ignored without rotation
        self.assertEqual(c0._focus_set(list(w.pool)), select_top(w, c0.ranker, 4))
        w = mini_world()
        c = Campaign(w, 80.0, seed=0, policy="u5", round_policy="power", focus_size=4,
                     focus_rotation="rotate", rotate_after=1, explore_share=0.0)
        pool = list(w.pool)
        first = c._focus_set(pool)
        self.assertEqual(len(first), 4)
        c._retired.update(first[:2])
        second = c._focus_set(pool)
        self.assertTrue(set(first[:2]).isdisjoint(second))
        self.assertEqual(second[:2], first[2:])          # next-ranked candidates move up
        c._retired.update(pool[:-1])                       # exhausted: a new pass starts
        third = c._focus_set(pool)
        self.assertEqual(third, first)
        self.assertTrue(any(e["kind"] == "u5.focus_reset" for e in c.ledger.entries))

    def test_unfocused_rounds_do_not_retire(self):
        w = mini_world()                                    # 8 candidates < focus 40: unfocused
        c = Campaign(w, 80.0, seed=0, policy="u5", round_policy="power", focus_size=40,
                     focus_rotation="rotate", rotate_after=1)
        c.do_admit()
        self.assertEqual(len(c._retired), 0)

    def test_focused_null_rounds_retire(self):
        w = mini_world()
        c = Campaign(w, 200.0, seed=0, policy="u5", round_policy="power", focus_size=3,
                     focus_rotation="rotate", rotate_after=1, explore_share=0.0)
        c.do_admit()
        rounds = [e["payload"] for e in c.ledger.entries if e["kind"] == "u5.round"]
        self.assertEqual(rounds[0]["eligible"], 3)
        self.assertGreater(len(c._retired) + len(w.accepted_extra), 0)

    def test_campaign_pool_additions_are_screened(self):
        w = mini_world()
        c = Campaign(w, 80.0, seed=0, policy="u5")
        from gap_engine.adapters.induction.adapter import _lid
        from gap_engine.adapters.induction.prover import Prover
        for held in w.tasks["SELECT"] + w.tasks["CONFIRM"]:
            att = Prover(w.theory, dict(w.store.lemmas), fuel=20000).prove(held)
            if att.proved:
                break
        self.assertTrue(att.proved)
        lid = _lid(held)
        w.store.verify(lid, held, att.proof)
        self.assertFalse(c._add_to_pool(lid, "procedure"))
        self.assertNotIn(lid, w.pool)
        self.assertTrue(any(e["kind"] == "pool.refused" for e in c.ledger.entries))

    def test_rotate_round_logs_and_stays_within_budget(self):
        w = mini_world()
        c = Campaign(w, 80.0, seed=0, policy="u5", round_policy="power", focus_size=4, focus_rotation="rotate")
        c.do_admit()
        rounds = [e["payload"] for e in c.ledger.entries if e["kind"] == "u5.round"]
        self.assertEqual(rounds[0]["rotation"], "rotate")
        self.assertLessEqual(c.broker.used, 80.0 + 1e-9)
        with self.assertRaises(ValueError):
            Campaign(mini_world(), 80.0, seed=0, focus_rotation="spin")


if __name__ == "__main__":
    unittest.main()
