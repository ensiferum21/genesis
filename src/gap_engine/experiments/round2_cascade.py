"""SUPERSEDED by round2b_cascade.py (this version scores CONFIRM, which Gate J also uses, so
its estimates are in-sample). Compounding re-measured on round-2 worlds with the improved V2 (power-sized rounds,
carried proposer), using the 2x2 cascade on CONFIRM tasks."""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ..engine.arms import arm_dropout
from ..engine.loop import Campaign
from ..kernel import stats
from ..kernel.budget import BudgetBroker
from ..kernel.ledger import Ledger
from .round2_bench import FOCUS, NAMES, load_r2, prior_ranker


def first_bundle(name: str, th: dict) -> list[str]:
    w = load_r2(name)
    b = BudgetBroker.from_policy(150.0, Ledger())
    res = arm_dropout(w, 150.0, 7, False, th, broker=b)
    bundles = sorted([x for x in res.bundles if x.evidence.fdr_rejected], key=lambda x: x.evidence.pvalue)
    for x in bundles:
        if x.kind == "pair":
            return list(x.members)
    return list(bundles[0].members) if bundles else []


def condition(name: str, A: list[str], present: bool, running: bool, seed: int, budget: float) -> np.ndarray:
    w = load_r2(name)
    if present:
        w.base_ids = list(w.base_ids) + A
        w.pool = [p for p in w.pool if p not in A]
    if running:
        led = Ledger()
        Campaign(w, budget, seed, policy="u5", ledger=led, round_policy="power", focus_size=FOCUS,
                 prior_ranker=prior_ranker(w, led)).run(max_steps=60)
    return w.run_library([], "CONFIRM", seed).astype(float)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=300.0)
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--th", default='{"tau": 10, "delta": 2, "min_tasks": 2, "min_ov": 1}')
    ap.add_argument("--out", default="experiments/results/round2_cascade.json")
    a = ap.parse_args(argv)
    th = json.loads(a.th)
    seeds = [int(s) for s in a.seeds.split(",")]
    out = {}
    t0 = time.time()
    for nm in NAMES[1:]:
        A = first_bundle(nm, th)
        if not A:
            out[nm] = {"bundle": [], "note": "no bundle"}
            continue
        w = load_r2(nm)
        arms = {k: np.mean([condition(nm, A, p, r, s, a.budget) for s in seeds], axis=0)
                for k, (p, r) in {"y11": (True, True), "y10": (True, False), "y01": (False, True),
                                  "y00": (False, False)}.items()}
        c = stats.cascade_2x2(arms["y11"], arms["y10"], arms["y01"], arms["y00"])
        out[nm] = {"bundle": [w.statement(i) for i in A], "estimate": c.estimate, "se": c.se, "ci95": c.ci95,
                   "n_tasks": c.n_tasks, "means": {k: float(v.mean()) for k, v in arms.items()},
                   "naive_y11_minus_y00": float(arms["y11"].mean() - arms["y00"].mean())}
        print(nm, json.dumps(out[nm]), f"({time.time() - t0:.0f}s)", flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
