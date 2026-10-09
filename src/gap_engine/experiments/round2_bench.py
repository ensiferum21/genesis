"""Round 2 of the head-to-head. SUPERSEDED by round2b_bench.py: an independent review found
sealed theorems in this round's visible splits and an unscreened pool path in V2
(docs/RESULTS.md §9.1). Kept to document what ran; the loader reproduces the round-2
worlds, but campaign code has since changed (pool screening, verified experience), so V2/UR
reruns will not match round2.json exactly.

Original description: the three fixes from the implementation report, tested.

Changes from round 1:
  * larger, independent sealed suites: a diverse lemma-dependent task pool is partitioned
    into DISJOINT worlds (one calibration world, three evaluation worlds); hand-written
    properties appear only in DEV / SELECT / CONFIRM;
  * V2 sizes its own dropout rounds from the co-inclusions its design needs ("power" rounds);
  * U3 carries a proposer generation across worlds: an experience store built on the
    calibration world (150-run labels, cost reported) seeds V2's ranker and focuses dropout.
Arms: D, G, R+, U (round-1 winner), UR (U focused by the carried ranker: isolates U3),
V2 (power rounds + focus + carried ranker), V2n (power rounds, no carried ranker).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..adapters.induction.adapter import build_world_from_suite, judge_sealed
from ..adapters.induction.suite import partition_weighted
from ..engine.admission import admit_proposals
from ..engine.arms import arm_dropout, arm_gate, arm_pairs_strong
from ..engine.loop import Campaign
from ..kernel import stats
from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.gates import GateJ, Library
from ..kernel.invariants import inv23_matched_comparison
from ..kernel.ledger import Ledger
from ..u3.dream import default_ranker, label_pool, select_top
from ..u3.experience import ExperienceStore
from .induction_bench import GRIDS
from .prereg import load_verified, write_prereg

CACHE = "experiments/cache"
POOL = "experiments/cache/task_pool_round2.json"
EXP = "experiments/cache/experience_r2cal.json"
NAMES = ["r2-cal", "r2-w1", "r2-w2", "r2-w3"]
FOCUS = 40


def load_r2(name: str, null: bool = False):
    with open(POOL) as fh:
        tasks = json.load(fh)["tasks"]
    parts = partition_weighted(tasks, [0.13, 0.29, 0.29, 0.29], seed=2026)
    k = NAMES.index(name)
    # round 2 as it ran (SUPERSEDED by round 2b): legacy cache key, visible splits unscreened
    w = build_world_from_suite(name, parts[k], seed=100 + k, cache_dir=CACHE, split=(0.15, 0.125, 0.125),
                               cache_key=f"{name}.pkl", screen_visible=False)
    if null:
        w.pool = [lid for i, lid in enumerate(w.pool) if not w.fingerprint(i, 0).any()]
        w.name += "-null"
    return w


def prior_ranker(w, led: Ledger):
    store = ExperienceStore.load(EXP)
    return store.ranker_for(w, default_ranker(w), led, gen_id="gen-prior-r2cal")


def build_experience(runs: int = 150) -> dict:
    if os.path.exists(EXP):
        return ExperienceStore.load(EXP).sources
    w = load_r2("r2-cal")
    led = Ledger()
    b = BudgetBroker(total=1e9, ledger=led)
    labels = label_pool(w, b, seed=7, runs=runs)
    st = ExperienceStore()
    st.add_world_labels(w, labels, "r2-cal", cost=b.used, ledger=led)
    st.save(EXP)
    return st.sources


def run_arm(arm: str, name: str, th: dict | None, budget: float, null: bool = False) -> dict:
    t0 = time.time()
    w = load_r2(name, null)
    seed = 100 + NAMES.index(name)
    led = Ledger()
    out = {"arm": arm, "world": name, "null": null, "budget": budget}
    if arm == "D":
        fuel = int(min(200000, budget * w.n_tasks("DEV") * w.solver.fuel / max(1, w.sealed.size("SEALED"))))
        j = judge_sealed(w, [], seed=seed, actor="D", fuel=fuel, max_depth=3, unsafe_dev=True)
        out.update(admitted=[], spent=budget, fuel=fuel)
    elif arm in ("V2", "V2n"):
        kw = dict(round_policy="power")
        if arm == "V2":
            kw.update(focus_size=FOCUS, prior_ranker=prior_ranker(w, led))
        camp = Campaign(w, budget, seed, policy="u5", ledger=led, **kw)
        res = camp.run(max_steps=80)
        j = judge_sealed(w, [], seed=seed, actor=arm, unsafe_dev=True)
        rounds = [e["payload"] for e in led.entries if e["kind"] == "u5.round"]
        out.update(admitted=[w.statement(i) for i in w.accepted_extra], spent=res.spent, steps=res.steps,
                   generations=res.generations, stops=res.stops, rounds=rounds)
    else:
        search = BudgetBroker.from_policy(0.85 * budget, Ledger(), name=f"{arm}-search")
        if arm == "UR":
            pr = prior_ranker(w, led)
            top = set(select_top(w, pr, FOCUS))
            eligible = np.array([c in top for c in w.pool])
            res = arm_dropout(w, 0.85 * budget, seed, False, th, broker=search, eligible=eligible)
        else:
            fn = {"G": arm_gate, "R+": arm_pairs_strong, "U": arm_dropout}[arm]
            res = fn(w, 0.85 * budget, seed, False, th, broker=search)
        gb = BudgetBroker.from_policy(budget - search.used, led, name=f"{arm}-gate")
        lib = Library(led)
        gate = GateJ(w, gb, led, alpha=0.05, reps=1)
        ids = w.pool_ids()
        props = []
        if arm in ("U", "UR"):
            props = [(b.members, b.evidence.pvalue, b.kind) for b in res.bundles if b.evidence.fdr_rejected]
        else:
            props = [((ids[i], ids[j_]), -res.scores.get((i, j_), 0.0), "pair") for (i, j_) in sorted(res.pairs)]
            props += [((ids[i],), -res.scores.get(i, 0.0), "single") for i in sorted(res.direct)]
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


def _job(a):
    return run_arm(*a)


def calibrate(pool, budget: float) -> dict:
    chosen = {}
    for arm, grid_key in (("G", "G"), ("R+", "R+"), ("U", "U")):
        grid = GRIDS[grid_key]
        res = list(pool.map(_job, [(arm, "r2-cal", th, budget, False) for th in grid]))
        best = max(range(len(grid)), key=lambda k: (res[k]["confirm_solved"], -k))
        chosen[arm] = grid[best]
        print(f"calibrated {arm}: {grid[best]} confirm={[r['confirm_solved'] for r in res]}", flush=True)
    chosen["UR"] = chosen["U"]
    return chosen


PRIMARY = [("V2", "U"), ("UR", "U"), ("U", "G"), ("U", "D")]
SECONDARY = [("V2", "V2n"), ("V2n", "U"), ("V2", "D"), ("R+", "G"), ("UR", "G")]


def analyse(results: list[dict], budget: float, margin: float = 0.03) -> dict:
    by: dict[str, list[int]] = {}
    for r in sorted(results, key=lambda r: r["world"]):
        if r["null"] or r["budget"] != budget:
            continue
        by.setdefault(r["arm"], []).extend(r["sealed"])
    if not by:
        return {}
    n = len(next(iter(by.values())))

    def mc(a, b):
        m = stats.mcnemar(np.array(by[a], bool), np.array(by[b], bool))
        return {"a": a, "b": b, "a_only": m.b, "b_only": m.c, "p": m.pvalue, "diff": m.diff}

    prim = [mc(a, b) for a, b in PRIMARY if a in by and b in by]
    rej = stats.holm([t["p"] for t in prim], 0.05) if prim else []
    for t, r in zip(prim, rej):
        t["holm_reject"] = bool(r)
    sec = [mc(a, b) for a, b in SECONDARY if a in by and b in by]
    tost = None
    if "U" in by and "R+" in by:
        t = stats.tost_paired(by["U"], by["R+"], margin)
        tost = {"verdict": t.verdict, "mean_diff": t.mean_diff, "ci90": t.ci90}
    null = {r["arm"]: len(r["admitted"]) for r in results if r["null"] and r["budget"] == budget}
    return {"budget": budget, "n_sealed": n, "solve_rate": {a: float(np.mean(v)) for a, v in by.items()},
            "primary": prim, "secondary": sec, "tost_U_vs_Rplus": tost, "null_world_admissions": null,
            "pilot": n < stats.mcnemar_sample_size(0.10, 0.05, 0.05 / 4, 0.8)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--budgets", default="150,400,1000")
    ap.add_argument("--arms", default="D,G,R+,U,UR,V2,V2n")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--prereg", default="experiments/prereg_round2.json")
    ap.add_argument("--out", default="experiments/results/round2.json")
    a = ap.parse_args(argv)
    budgets = [float(x) for x in a.budgets.split(",")]
    arms = a.arms.split(",")
    plan = {"experiment": "round 2: power-sized rounds, carried proposer, larger independent sealed suites",
            "arms": arms, "budgets": budgets, "worlds": NAMES[1:], "calibration_world": NAMES[0],
            "primary_family_per_budget": [f"{x} vs {y}" for x, y in PRIMARY],
            "test": "McNemar exact on pooled sealed theorems, Holm within each budget at alpha 0.05",
            "equivalence": "TOST U vs R+ margin 0.03",
            "carried_proposer": "ranker trained on experience from the calibration world only (150-run labels)",
            "null_world": "inert-pool variant of r2-w1 for pool-selecting arms (G, R+, U, UR)",
            "decision_rules": ["adopt V2 over U only if V2 beats U after Holm at some budget and never loses",
                               "credit U3 only if UR beats U after Holm",
                               "fewer sealed tasks than the power analysis requires: pilot"]}
    if not os.path.exists(a.prereg):
        write_prereg(a.prereg, plan)
    plan = load_verified(a.prereg)
    t0 = time.time()
    for nm in NAMES:
        w = load_r2(nm)
        print(f"world {nm}: DEV {w.n_tasks('DEV')} SELECT {w.n_tasks('SELECT')} CONFIRM {w.n_tasks('CONFIRM')} "
              f"SEALED {w.sealed.size('SEALED')} pool {len(w.pool)} ({time.time() - t0:.0f}s)", flush=True)
    src = build_experience()
    print(f"experience: {src} ({time.time() - t0:.0f}s)", flush=True)
    results = []
    with ProcessPoolExecutor(a.workers) as pool:
        chosen = calibrate(pool, 150.0)
        jobs = [(arm, nm, chosen.get(arm), b, False) for b in budgets for nm in NAMES[1:] for arm in arms]
        jobs += [(arm, NAMES[1], chosen.get(arm), b, True) for b in budgets for arm in ("G", "R+", "U", "UR")
                 if arm in arms]
        for r in pool.map(_job, jobs):
            results.append(r)
            print(f"{'NULL ' if r['null'] else ''}B={r['budget']:.0f} {r['arm']:3s} {r['world']}: sealed "
                  f"{r['sealed_solved']}/{len(r['sealed'])} admitted {len(r['admitted'])} spent {r['spent']:.0f} "
                  f"({r['seconds']}s, total {time.time() - t0:.0f}s)", flush=True)
            with open(a.out + ".partial", "w") as fh:
                json.dump(results, fh, default=str)
    load_verified(a.prereg)
    inv23_matched_comparison(calibrated=True, null_world_reported=True)
    analysis = {f"B{int(b)}": analyse(results, b) for b in budgets}
    with open(a.out, "w") as fh:
        json.dump({"plan": plan, "thresholds": chosen, "experience": src, "results": results,
                   "analysis": analysis}, fh, indent=1, default=str)
    for k, v in analysis.items():
        print(k, json.dumps({"rates": {a_: round(x, 3) for a_, x in v["solve_rate"].items()},
                             "primary": [(t["a"], t["b"], t["a_only"], t["b_only"], round(t["p"], 5),
                                          t["holm_reject"]) for t in v["primary"]]}))


if __name__ == "__main__":
    main()
