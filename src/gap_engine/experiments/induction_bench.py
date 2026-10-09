"""The first head-to-head experiment, run on inductive mathematics (lesion worlds).

Arms (identical total budget B, in DEV-library-evaluation units):
  D   strongest direct solver: no library growth; its whole budget is converted into extra
      search (fuel and depth 3) on each sealed theorem
  G   current spec: test candidates one at a time, first-order gate, admit
  R   rival as written: G plus shared-failure pair tests; pairs through Gate J
  R+  strongest pair testing (fingerprint-ranked, localised, interaction-confirmed)
  U   U1 + U2: library dropout (auto-switching to blocks), bundles through Gate J
  V2  the full Gap Engine v2 campaign (U1-U5 under the U5 scheduler)
Thresholds are calibrated on a separate calibration world (maximising CONFIRM solves) and
every arm also runs on an inert-pool null world, where any admission is a false discovery
(INV-23). Final libraries are judged only through the SealedStore (INV-19).
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..adapters.induction.adapter import build_world, judge_sealed
from ..engine.arms import arm_dropout, arm_gate, arm_pairs_strong, arm_rival
from ..engine.loop import Campaign
from ..kernel import stats
from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.gates import GateJ, Library, first_order_gate
from ..kernel.invariants import inv23_matched_comparison
from ..kernel.ledger import Ledger
from ..kernel.records import Bundle, BundleEvidence
from ..engine.admission import admit_proposals
from .prereg import load_verified, write_prereg

CACHE = "experiments/cache"

GRIDS = {
    "G": [dict(direct=d, pair=1, rep=1, single_rep=1) for d in (1, 2, 3)],
    "R": [dict(direct=d, pair=p, rep=1, single_rep=1) for d in (1, 2) for p in (1, 2)],
    "R+": [dict(min_ov=m, pair=p, inter=1.0, rep=1) for m in (1, 2) for p in (1.0, 2.0)],
    "U": [dict(tau=t, delta=2, min_tasks=k, min_ov=m) for t in (10, 20) for k in (1, 2) for m in (1, 2)],
}


def load_world(seed: int, null: bool = False):
    w = build_world(seed=seed, lesion=True, cache_dir=CACHE)
    if null:
        b = BudgetBroker(total=1e9)
        inert = [lid for i, lid in enumerate(w.pool) if not w.fingerprint(i, 0).any()]
        w.pool = inert
        w.name += "-null"
    return w


def run_arm(arm: str, seed: int, th: dict | None, budget: float, null: bool = False, crn: bool = False) -> dict:
    t0 = time.time()
    w = load_world(seed, null)
    led = Ledger()
    out = {"arm": arm, "world": seed, "null": null, "budget": budget}
    if arm == "D":
        dev_n, sealed_n = w.n_tasks("DEV"), w.sealed.size("SEALED")
        fuel = int(min(60000, budget * dev_n * w.solver.fuel / max(1, sealed_n)))
        j = judge_sealed(w, [], seed=seed, actor="D", fuel=fuel, max_depth=3, unsafe_dev=True)
        out.update(admitted=[], spent=budget, fuel=fuel)
    elif arm == "V2":
        camp = Campaign(w, budget, seed, policy="u5", ledger=led)
        res = camp.run(max_steps=60)
        j = judge_sealed(w, [], seed=seed, actor="V2", unsafe_dev=True)
        out.update(admitted=[w.statement(i) for i in w.accepted_extra], spent=res.spent,
                   steps=res.steps, generations=res.generations, stops=res.stops, dr=res.dr_values)
    else:
        search = BudgetBroker.from_policy(0.85 * budget, Ledger(), name=f"{arm}-search")
        fn = {"G": arm_gate, "R": arm_rival, "R+": arm_pairs_strong, "U": arm_dropout}[arm]
        res = fn(w, 0.85 * budget, seed, crn, th, broker=search)
        gb = BudgetBroker.from_policy(budget - search.used, led, name=f"{arm}-gate")
        lib = Library(led)
        gate = GateJ(w, gb, led, alpha=0.05, reps=1)
        ids = w.pool_ids()
        props: list[tuple[tuple[str, ...], float, str]] = []
        if arm == "U":
            for b in res.bundles:
                if b.evidence.fdr_rejected:
                    props.append((b.members, b.evidence.pvalue, b.kind))
        else:
            for (i, j_) in sorted(res.pairs):
                props.append(((ids[i], ids[j_]), -res.scores.get((i, j_), 0.0), "pair"))
            for i in sorted(res.direct):
                props.append(((ids[i],), -res.scores.get(i, 0.0), "single"))
        props.sort(key=lambda x: x[1])
        admit_proposals(w, lib, gate, props, seed)
        out.update(admitted=[w.statement(i) for i in w.accepted_extra], spent=search.used + gb.used,
                   proposals=len(props), notes=res.notes)
        j = judge_sealed(w, [], seed=seed, actor=arm, unsafe_dev=True)
    keys = sorted(j["outcomes"])
    out["sealed"] = [int(j["outcomes"][k]) for k in keys]
    out["sealed_solved"] = int(sum(out["sealed"]))
    out["confirm_solved"] = int(w.run_library([], "CONFIRM", seed).sum())
    out["seconds"] = round(time.time() - t0, 1)
    return out


def _job(args):
    return run_arm(*args)


def calibrate(pool, cal_seed: int, budget: float) -> dict:
    chosen = {}
    for arm, grid in GRIDS.items():
        jobs = [(arm, cal_seed, th, budget, False) for th in grid]
        res = list(pool.map(_job, jobs))
        best = max(range(len(grid)), key=lambda k: (res[k]["confirm_solved"], -k))
        chosen[arm] = grid[best]
        print(f"calibrated {arm}: {grid[best]} confirm={[r['confirm_solved'] for r in res]}", flush=True)
    return chosen


def analyse(results: list[dict], margin: float) -> dict:
    by_arm: dict[str, list[int]] = {}
    for r in sorted(results, key=lambda r: r["world"]):
        if r["null"]:
            continue
        by_arm.setdefault(r["arm"], []).extend(r["sealed"])
    arms = sorted(by_arm)
    n = len(next(iter(by_arm.values())))
    rate = {a: float(np.mean(v)) for a, v in by_arm.items()}
    family = [("U", "G"), ("U", "D"), ("R+", "G"), ("R+", "D")]
    tests = []
    for a, b in family:
        if a in by_arm and b in by_arm:
            m = stats.mcnemar(np.array(by_arm[a], bool), np.array(by_arm[b], bool))
            tests.append({"a": a, "b": b, "a_only": m.b, "b_only": m.c, "p": m.pvalue, "diff": m.diff})
    rej = stats.holm([t["p"] for t in tests], 0.05) if tests else []
    for t, r in zip(tests, rej):
        t["holm_reject"] = bool(r)
    secondary = []
    for a, b in [("V2", "U"), ("V2", "D"), ("V2", "G"), ("R", "G")]:
        if a in by_arm and b in by_arm:
            m = stats.mcnemar(np.array(by_arm[a], bool), np.array(by_arm[b], bool))
            secondary.append({"a": a, "b": b, "a_only": m.b, "b_only": m.c, "p": m.pvalue, "diff": m.diff})
    tost = None
    if "U" in by_arm and "R+" in by_arm:
        t = stats.tost_paired(by_arm["U"], by_arm["R+"], margin)
        tost = {"verdict": t.verdict, "mean_diff": t.mean_diff, "ci90": t.ci90, "margin": margin}
    # the inert-pool null is a null only for arms that select from the pool; V2 generates
    # its own candidates, so its run there is reported as discovery, not as false discovery
    null_admits = {r["arm"]: len(r["admitted"]) for r in results if r["null"] and r["arm"] != "V2"}
    v2_inert = [{"admitted": r["admitted"], "sealed_solved": r["sealed_solved"]}
                for r in results if r["null"] and r["arm"] == "V2"]
    power_n = stats.mcnemar_sample_size(0.10, 0.05, 0.05 / 4, 0.8)
    return {"n_sealed_tasks": n, "solve_rate": rate, "primary": tests, "secondary": secondary,
            "tost_U_vs_Rplus": tost, "null_world_admissions": null_admits,
            "v2_inert_pool_discovery": v2_inert,
            "pilot": n < power_n, "tasks_needed_for_power": power_n}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", default="0,1,2")
    ap.add_argument("--cal-world", type=int, default=3)
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--arms", default="D,G,R,R+,U,V2")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--prereg", default="experiments/prereg_induction.json")
    ap.add_argument("--out", default="experiments/results/induction_headtohead.json")
    a = ap.parse_args(argv)
    worlds = [int(x) for x in a.worlds.split(",")]
    arms = a.arms.split(",")
    plan = {"experiment": "first head-to-head, inductive lesion worlds", "arms": arms, "worlds": worlds,
            "calibration_world": a.cal_world, "budget": a.budget,
            "primary_outcome": "sealed theorems proved (kernel-checked), paired by task",
            "primary_tests": "McNemar exact, Holm over U-G, U-D, R+-G, R+-D at alpha 0.05",
            "equivalence": "TOST U vs R+ with margin 0.03 on paired outcomes",
            "decision_rules": ["adopt U only if it beats G and D after Holm",
                               "if U and R+ are TOST-equivalent, adopt R+ (simpler)",
                               "if D beats every engine arm, withdraw library machinery for this domain",
                               "fewer tasks than the power analysis requires: report as pilot"],
            "null_world": "inert-pool variant of world 0; any admission by a pool-selecting arm is a "
                          "false discovery (V2 generates candidates, so its run is reported separately)"}
    if not os.path.exists(a.prereg):
        write_prereg(a.prereg, plan)
    plan = load_verified(a.prereg)
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool:
        chosen = calibrate(pool, a.cal_world, a.budget)
        jobs = []
        for s in worlds:
            for arm in arms:
                jobs.append((arm, s, chosen.get(arm), a.budget, False))
        for arm in arms:
            if arm != "D":
                jobs.append((arm, worlds[0], chosen.get(arm), a.budget, True))
        results = []
        for r in pool.map(_job, jobs):
            results.append(r)
            print(f"{'NULL ' if r['null'] else ''}{r['arm']:3s} world {r['world']}: sealed {r['sealed_solved']}/"
                  f"{len(r['sealed'])} confirm {r['confirm_solved']} admitted {len(r['admitted'])} "
                  f"spent {r['spent']:.0f} ({r['seconds']}s, total {time.time() - t0:.0f}s)", flush=True)
    load_verified(a.prereg)
    inv23_matched_comparison(calibrated=True, null_world_reported=True)
    analysis = analyse(results, margin=0.03)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump({"plan": plan, "thresholds": chosen, "results": results, "analysis": analysis}, fh, indent=1,
                  default=str)
    print(json.dumps(analysis, indent=1, default=str))


if __name__ == "__main__":
    main()
