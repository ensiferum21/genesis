"""Results must not depend on Python's per-process hash seed (found by the round-2b
fact-check: Gate J iterated a set of lemma ids, so gate decisions changed between
processes)."""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBE = r"""
import json
from tests.helpers import mini_world
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.gates import GateJ
from gap_engine.kernel.ledger import Ledger
from gap_engine.kernel.records import Bundle, BundleEvidence
from gap_engine.engine.loop import Campaign
w = mini_world()
lib = frozenset(w.pool)
out = {"outcomes": w.outcomes(lib, "DEV", 1, 3).tolist()}
led = Ledger()
gate = GateJ(w, BudgetBroker(total=1e6, ledger=led), led, alpha=0.05, reps=1)
b = Bundle(members=tuple(w.pool[:4]), kind="batch", evidence=BundleEvidence(votes=1, pvalue=0.0, fdr_rejected=True))
d = gate.decide(b, frozenset(), seed=5)
out["gate"] = [d.passed, d.stage, sorted(d.stats.items())]
w2 = mini_world()
c = Campaign(w2, 120.0, seed=1, policy="u5", round_policy="power")
c.run(max_steps=12)
out["campaign"] = sorted(w2.accepted_extra)
print(json.dumps(out))
"""


class TestLibraryOrder(unittest.TestCase):
    def test_outcomes_hand_the_solver_a_sorted_library(self):
        from tests.helpers import mini_world
        w = mini_world()
        seen = []
        w.run_library = lambda extra, split, seed: (seen.append(list(extra)) or __import__("numpy").zeros(1))
        w.outcomes(frozenset(reversed(w.pool)), "DEV", 2, 0)
        self.assertTrue(seen)
        for extra in seen:
            self.assertEqual(extra, sorted(extra))


HEAVY = r"""
import json
from gap_engine.experiments.round2b_bench import load_r2b
from gap_engine.engine.arms import arm_dropout
from gap_engine.engine.admission import admit_proposals
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.gates import GateJ, Library
from gap_engine.kernel.ledger import Ledger
th = {"tau": 20, "delta": 2, "min_tasks": 1, "min_ov": 1}
w = load_r2b("r2b-w3"); led = Ledger()
search = BudgetBroker.from_policy(340.0, Ledger(), name="s")
res = arm_dropout(w, 340.0, 203, False, th, broker=search)
gate = GateJ(w, BudgetBroker.from_policy(400.0 - search.used, led, name="g"), led, alpha=0.05, reps=1)
props = sorted([(b.members, b.evidence.pvalue, b.kind) for b in res.bundles if b.evidence.fdr_rejected], key=lambda x: x[1])
admit_proposals(w, Library(led), gate, props, 203)
print(json.dumps(sorted(w.accepted_extra)))
"""


@unittest.skipUnless(os.environ.get("GAP_SLOW_TESTS"), "set GAP_SLOW_TESTS=1 (needs the cached round-2b worlds)")
class TestRound2bReplayHashSeed(unittest.TestCase):
    def test_u_admission_replay_identical_across_hash_seeds(self):
        outs = []
        for h in ("0", "1"):
            env = dict(os.environ, PYTHONHASHSEED=h, PYTHONPATH=os.path.join(ROOT, "src") + os.pathsep + ROOT)
            r = subprocess.run([sys.executable, "-c", HEAVY], cwd=ROOT, env=env, capture_output=True, text=True,
                               timeout=900)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            outs.append(r.stdout.strip().splitlines()[-1])
        self.assertEqual(outs[0], outs[1])


class TestHashSeedIndependence(unittest.TestCase):
    def test_gate_and_campaign_identical_across_hash_seeds(self):
        outs = []
        for h in ("0", "1", "2"):
            env = dict(os.environ, PYTHONHASHSEED=h, PYTHONPATH=os.path.join(ROOT, "src") + os.pathsep + ROOT)
            r = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True,
                               timeout=600)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            outs.append(json.loads(r.stdout.strip().splitlines()[-1]))
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[0], outs[2])


if __name__ == "__main__":
    unittest.main()
