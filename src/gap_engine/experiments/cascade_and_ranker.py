"""Two U3-side measurements on the inductive worlds.

cascade: the corrected compounding estimand. For the first bundle U admits in a world (A),
score four conditions on the same later tasks (CONFIRM), averaged over campaign seeds:
    y11 A present, research running   (v2 campaign continues from base + A)
    y10 A present, research frozen
    y01 A absent,  research running
    y00 A absent,  research frozen
cascade = (y11 - y01) - (y10 - y00), with a paired standard error over tasks.

ranker: does the proposer trained on one world's verified experience (U3) pick better
libraries in other worlds than the generation-0 heuristic? Top-k libraries are judged on
CONFIRM and through the sealed store.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ..adapters.induction.adapter import judge_sealed
from ..engine.arms import arm_dropout
from ..engine.loop import Campaign
from ..kernel import stats
from ..kernel.budget import BudgetBroker
from ..kernel.ledger import Ledger
from ..u3.dream import default_ranker, label_pool, select_top
from .induction_bench import load_world


def first_bundle(seed: int) -> list[str]:
    w = load_world(seed)
    b = BudgetBroker.from_policy(150.0, Ledger())
    res = arm_dropout(w, 150.0, seed, False, dict(tau=10, delta=2, min_tasks=2, min_ov=1), broker=b)
    bundles = sorted([x for x in res.bundles if x.evidence.fdr_rejected], key=lambda x: x.evidence.pvalue)
    for x in bundles:
        if x.kind == "pair":
            return list(x.members)
    return list(bundles[0].members) if bundles else []


def condition(seed: int, A: list[str], present: bool, running: bool, camp_seed: int, budget: float) -> np.ndarray:
    w = load_world(seed)
    if present:
        w.base_ids = list(w.base_ids) + A
        w.pool = [p for p in w.pool if p not in A]
    if running:
        Campaign(w, budget, camp_seed, policy="u5").run(max_steps=40)
    return w.run_library([], "CONFIRM", camp_seed).astype(float)


def cascade(worlds, camp_seeds, budget) -> dict:
    out = {}
    for s in worlds:
        A = first_bundle(s)
        if not A:
            out[s] = {"bundle": [], "note": "U admitted nothing"}
            continue
        w = load_world(s)
        arms = {}
        for key, (pres, run_) in {"y11": (True, True), "y10": (True, False), "y01": (False, True),
                                  "y00": (False, False)}.items():
            arms[key] = np.mean([condition(s, A, pres, run_, cs, budget) for cs in camp_seeds], axis=0)
        c = stats.cascade_2x2(arms["y11"], arms["y10"], arms["y01"], arms["y00"])
        out[s] = {"bundle": [w.statement(i) for i in A], "estimate": c.estimate, "se": c.se, "ci95": c.ci95,
                  "n_tasks": c.n_tasks, "means": {k: float(v.mean()) for k, v in arms.items()}}
        print(f"world {s}: A={out[s]['bundle']} cascade={c.estimate:.3f} ci95=({c.ci95[0]:.3f},{c.ci95[1]:.3f}) "
              f"means={out[s]['means']}", flush=True)
    return out


def ranker_transfer(train_world: int, test_worlds, ks=(5, 10, 20)) -> dict:
    w = load_world(train_world)
    b = BudgetBroker(total=1e9)
    labels = label_pool(w, b, seed=train_world, runs=150)
    r0 = default_ranker(w)
    eqs = [w.store.verified_subset([c])[c] for c in labels]
    r1 = r0.fit(eqs, [labels[c] for c in labels], gen_id="gen1-transfer")
    out = {"train_world": train_world, "positives": int(sum(labels.values())), "n": len(labels), "tests": {}}
    for s in test_worlds:
        for k in ks:
            row = {}
            for name, r in (("heuristic", r0), ("learned", r1)):
                wt = load_world(s)
                top = select_top(wt, r, k)
                wt.accepted_extra = top
                row[name] = {"confirm": int(wt.run_library([], "CONFIRM", 0).sum()),
                             "sealed": judge_sealed(wt, [], seed=0, actor=f"ranker-{name}", unsafe_dev=True)["solved"]}
            out["tests"][f"world{s}-k{k}"] = row
            print(f"world {s} k={k}: {row}", flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", default="0,1,2")
    ap.add_argument("--camp-seeds", default="0,1,2")
    ap.add_argument("--budget", type=float, default=200.0)
    ap.add_argument("--out", default="experiments/results/cascade_ranker.json")
    a = ap.parse_args(argv)
    worlds = [int(x) for x in a.worlds.split(",")]
    t0 = time.time()
    res = {"cascade": cascade(worlds, [int(x) for x in a.camp_seeds.split(",")], a.budget)}
    res["ranker"] = ranker_transfer(3, worlds)
    res["seconds"] = round(time.time() - t0)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1, default=str)


if __name__ == "__main__":
    main()
