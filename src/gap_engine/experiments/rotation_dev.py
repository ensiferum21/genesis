"""DEVELOPMENT evidence for V2 focus rotation (post-round-2 change). NOT CONFIRMATORY.

Round-2 diagnosis (from non-sealed campaign logs): V2's focus set, the prior ranker's top-40,
never changed, so after its first admissions V2 kept re-testing the same 40 candidates. The
fix (`Campaign(focus_rotation="rotate")`) retires candidates that were in focus for
`rotate_after` rounds without FDR-surviving evidence, and draws a share of the focus at
random from the rest of the pool.

This script never touches a test world's sealed suite (round-2b test worlds r2b-w1..w3 and
the superseded round-2 test worlds are refused). It measures on:
  * r2b-cal, the round-2b calibration world (several campaign seeds). There the carried
    ranker is IN-SAMPLE (it was trained on r2b-cal labels), so the clean comparison is V2f vs
    V2fr (focus with the default ranker, without / with rotation);
  * the round-1 worlds s1..s3, whose sealed suites were already used by round 1, with the
    carried r2b-cal ranker (out-of-sample for those worlds): V2 vs V2r.
Rotation's exploration draws use a dedicated RNG, so V2 and V2r share every other random
draw for the same seed.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..adapters.induction.adapter import judge_sealed
from ..engine.loop import Campaign
from ..kernel import stats
from ..kernel.ledger import Ledger
from .induction_bench import load_world
from .round2b_bench import FOCUS, NAMES as R2B, load_r2b, prior_ranker

ARMS = {
    "V2f": dict(prior=False, rotation="none"),
    "V2fr": dict(prior=False, rotation="rotate"),
    "V2": dict(prior=True, rotation="none"),
    "V2r": dict(prior=True, rotation="rotate"),
}


FORBIDDEN = set(R2B[1:]) | {"r2-w1", "r2-w2", "r2-w3"}


def _load(world: str):
    if world in FORBIDDEN:
        raise ValueError(f"{world} is a test world; development runs may not judge its sealed suite")
    if world.startswith("r2b-"):
        return load_r2b(world)
    if world.startswith("world-s"):
        return load_world(int(world.split("-s")[1]))
    raise ValueError(f"unknown development world {world!r}")


def run(arm: str, world: str, seed: int, budget: float) -> dict:
    t0 = time.time()
    w = _load(world)
    led = Ledger()
    cfg = ARMS[arm]
    kw = dict(round_policy="power", focus_size=FOCUS, focus_rotation=cfg["rotation"])
    if cfg["prior"]:
        kw["prior_ranker"] = prior_ranker(w, led)
    camp = Campaign(w, budget, seed, policy="u5", ledger=led, **kw)
    res = camp.run(max_steps=80)
    rounds = [e["payload"] for e in led.entries if e["kind"] == "u5.round"]
    resets = sum(1 for e in led.entries if e["kind"] == "u5.focus_reset")
    j = judge_sealed(w, [], seed=1000 + seed, actor=arm, unsafe_dev=True)
    keys = sorted(j["outcomes"])
    return {"arm": arm, "world": world, "seed": seed, "budget": budget,
            "sealed": [int(j["outcomes"][k]) for k in keys], "sealed_solved": int(sum(j["outcomes"].values())),
            "dev_solved": int(w.run_library([], "DEV", seed).sum()), "admitted": len(w.accepted_extra),
            "rounds": len(rounds), "max_retired": max([r.get("retired", 0) for r in rounds] or [0]),
            "focus_resets": resets, "spent": res.spent, "seconds": round(time.time() - t0, 1)}


def _job(a):
    return run(*a)


def summarise(results: list[dict], pairs: list[tuple[str, str]]) -> dict:
    out = {}
    for a, b in pairs:
        for budget in sorted({r["budget"] for r in results}):
            ra = {(r["world"], r["seed"]): r for r in results if r["arm"] == a and r["budget"] == budget}
            rb = {(r["world"], r["seed"]): r for r in results if r["arm"] == b and r["budget"] == budget}
            keys = sorted(set(ra) & set(rb))
            if not keys:
                continue
            diffs = [ra[k]["sealed_solved"] - rb[k]["sealed_solved"] for k in keys]
            wins, losses = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
            n = sum(len(ra[k]["sealed"]) for k in keys)
            sign = stats.mcnemar([True] * wins + [False] * losses, [False] * wins + [True] * losses)
            ta = np.concatenate([ra[k]["sealed"] for k in keys]).astype(bool)
            tb = np.concatenate([rb[k]["sealed"] for k in keys]).astype(bool)
            task = stats.mcnemar(ta, tb)
            out[f"{a}_vs_{b}_B{int(budget)}"] = {
                "runs": len(keys), "mean_rate_a": sum(ra[k]["sealed_solved"] for k in keys) / n,
                "mean_rate_b": sum(rb[k]["sealed_solved"] for k in keys) / n,
                "per_run_diff": diffs, "run_wins": wins, "run_losses": losses,
                "sign_test_p": sign.pvalue, "task_pairs_a_only": task.b, "task_pairs_b_only": task.c,
                "task_pairs_p": task.pvalue,
                "note": "development evidence; runs on the same world share tasks, so both tests "
                        "are descriptive, not confirmatory"}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--budgets", default="400,1000")
    ap.add_argument("--cal_seeds", default="0,1,2,3,4")
    ap.add_argument("--r1_worlds", default="world-s1,world-s2,world-s3")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="experiments/results/rotation_dev.json")
    a = ap.parse_args(argv)
    budgets = [float(x) for x in a.budgets.split(",")]
    for wn in ["r2b-cal"] + [x for x in a.r1_worlds.split(",") if x]:
        if wn in FORBIDDEN:
            raise SystemExit(f"{wn} is a test world")
    jobs = [(arm, "r2b-cal", s, b) for b in budgets for s in map(int, a.cal_seeds.split(","))
            for arm in ("V2f", "V2fr", "V2", "V2r")]
    jobs += [(arm, wn, 0, b) for b in budgets for wn in a.r1_worlds.split(",") if wn for arm in ("V2", "V2r")]
    results = []
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool:
        for r in pool.map(_job, jobs):
            results.append(r)
            print(f"B={r['budget']:.0f} {r['arm']:4s} {r['world']} s{r['seed']}: sealed {r['sealed_solved']}/"
                  f"{len(r['sealed'])} dev {r['dev_solved']} admitted {r['admitted']} rounds {r['rounds']} "
                  f"retired<={r['max_retired']} resets {r['focus_resets']} ({r['seconds']}s, "
                  f"total {time.time() - t0:.0f}s)", flush=True)
    cal = [r for r in results if r["world"] == "r2b-cal"]
    r1 = [r for r in results if r["world"] != "r2b-cal"]
    summary = {"r2b_cal": summarise(cal, [("V2fr", "V2f"), ("V2r", "V2")]),
               "round1_worlds": summarise(r1, [("V2r", "V2")])}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump({"status": "DEVELOPMENT EVIDENCE - NOT CONFIRMATORY", "doc": __doc__, "results": results,
                   "summary": summary}, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
