"""Compounding on round-2b worlds: the preregistered 2x2 cascade, scored on SEALED.

y11: bundle A admitted first, then a V2 campaign      y10: A admitted, no campaign
y01: no A, V2 campaign                                 y00: neither
cascade = (y11 - y10) - (y01 - y00): how much more the campaign adds when A is already in
the library. Positive = compounding; negative = substitution (the campaign would have found
A, or an equivalent, anyway). Each condition's final library is judged on the world's sealed
suite by the kernel, so no gate has seen the outcome tasks (round 2 scored CONFIRM).
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
from .prereg import load_verified
from .round2b_bench import FOCUS, NAMES, load_r2b, prior_ranker


def first_bundle(name: str, th: dict) -> list[str]:
    w = load_r2b(name)
    b = BudgetBroker.from_policy(150.0, Ledger())
    res = arm_dropout(w, 150.0, 7, False, th, broker=b)
    bundles = sorted([x for x in res.bundles if x.evidence.fdr_rejected], key=lambda x: x.evidence.pvalue)
    for x in bundles:
        if x.kind == "pair":
            return list(x.members)
    return list(bundles[0].members) if bundles else []


def condition(name: str, A: list[str], present: bool, running: bool, seed: int, budget: float) -> np.ndarray:
    w = load_r2b(name)
    if present:
        w.base_ids = list(w.base_ids) + A
        w.pool = [p for p in w.pool if p not in A]
    if running:
        led = Ledger()
        Campaign(w, budget, seed, policy="u5", ledger=led, round_policy="power", focus_size=FOCUS,
                 prior_ranker=prior_ranker(w, led)).run(max_steps=60)
    j = judge_sealed(w, [], seed=500 + seed, actor=f"cascade-{int(present)}{int(running)}", unsafe_dev=True)
    return np.array([j["outcomes"][k] for k in sorted(j["outcomes"])], float)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default="experiments/prereg_round2b.json")
    ap.add_argument("--results", default="experiments/results/round2b.json")
    ap.add_argument("--out", default="experiments/results/round2b_cascade.json")
    a = ap.parse_args(argv)
    plan = load_verified(a.prereg)["cascade"]
    with open(a.results) as fh:
        th = json.load(fh)["thresholds"]["U"]
    out, est, ses = {}, [], []
    t0 = time.time()
    for nm in NAMES[1:]:
        A = first_bundle(nm, th)
        if not A:
            out[nm] = {"bundle": [], "note": "no FDR-surviving bundle"}
            continue
        w = load_r2b(nm)
        arms = {k: np.mean([condition(nm, A, p, r, s, plan["budget"]) for s in plan["seeds"]], axis=0)
                for k, (p, r) in {"y11": (True, True), "y10": (True, False), "y01": (False, True),
                                  "y00": (False, False)}.items()}
        c = stats.cascade_2x2(arms["y11"], arms["y10"], arms["y01"], arms["y00"])
        out[nm] = {"bundle": [w.statement(i) for i in A], "estimate": c.estimate, "se": c.se, "ci95": c.ci95,
                   "n_tasks": c.n_tasks, "means": {k: float(v.mean()) for k, v in arms.items()}}
        est.append(c.estimate)
        ses.append(c.se)
        print(nm, json.dumps(out[nm]), f"({time.time() - t0:.0f}s)", flush=True)
    if est:
        wts = np.array([1.0 / max(s, 1e-9) ** 2 for s in ses])
        pooled = float(np.sum(wts * np.array(est)) / wts.sum())
        se = float(np.sqrt(1.0 / wts.sum()))
        out["pooled"] = {"estimate": pooled, "se": se, "ci95": [pooled - 1.96 * se, pooled + 1.96 * se],
                         "method": "inverse-variance weighted mean of per-world estimates"}
        print("pooled", json.dumps(out["pooled"]), flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump({"plan": plan, "results": out}, fh, indent=1)


if __name__ == "__main__":
    main()
