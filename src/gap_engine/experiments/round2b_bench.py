"""Round 2b: the round-2 head-to-head re-run on leak-free worlds (round 2 is SUPERSEDED).

The independent review of round 2 found (and we confirmed):
  1. hand-written properties sat in the task pool, so some sealed theorems were also
     DEV/SELECT/CONFIRM tasks (6 visible items across the three test worlds);
  2. `Campaign.do_procedure` added lemmas to the pool without the sealed/held-out screen,
     and V2 admitted a sealed theorem of r2-w2 that way;
  3. the carried experience bypassed `admit_dataset` and could include held-out gate tasks;
  4. the analysis applied Holm only within each budget, had no null-world runs for V2/V2n,
     and passed literal True flags to the INV-23 check.

Round 2b fixes all four:
  * pool = round-2 pool minus anything equal or near-equal to a hand-written property or
    textbook lemma (`exclude_handwritten`), re-partitioned with a NEW seed; worlds are built
    with `screen_visible=True` and content-hashed cache keys;
  * every lemma a campaign creates enters the pool through `InductionWorld.screen_reason`;
  * experience is rebuilt on the 2b calibration world and re-admitted into each test world
    through `admit_dataset` with a verifier for that world; its file hash is preregistered;
  * Holm runs over ALL primary comparisons at ALL budgets (12 tests); V2 and V2n get
    inert-pool runs too (reported as discoveries, because V2 creates its own lemmas); INV-23
    flags are computed from the results.
Arms and budgets are unchanged from round 2 (D, G, R+, U, UR, V2, V2n at 150/400/1000).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..adapters.induction.adapter import build_world_from_suite, judge_sealed
from ..adapters.induction.suite import exclude_handwritten, partition_weighted
from ..engine.admission import admit_proposals
from ..engine.arms import arm_dropout, arm_gate, arm_pairs_strong
from ..engine.loop import Campaign
from ..kernel import stats
from ..kernel.budget import BudgetBroker
from ..kernel.gates import GateJ, Library
from ..kernel.invariants import inv23_matched_comparison
from ..kernel.ledger import Ledger
from ..u3.dream import default_ranker, label_pool, select_top
from ..u3.experience import ExperienceStore
from .induction_bench import GRIDS
from .prereg import load_verified, write_prereg

CACHE = "experiments/cache"
POOL = "experiments/cache/task_pool_round2.json"
EXP = "experiments/cache/experience_r2bcal.json"
NAMES = ["r2b-cal", "r2b-w1", "r2b-w2", "r2b-w3"]
WEIGHTS = [0.13, 0.29, 0.29, 0.29]
PARTITION_SEED = 2027                     # round 2 used 2026
SPLIT = (0.15, 0.125, 0.125)
FOCUS = 40
PRIMARY = [("V2", "U"), ("UR", "U"), ("U", "G"), ("U", "D")]
SECONDARY = [("V2", "V2n"), ("V2n", "U"), ("V2", "D"), ("R+", "G"), ("UR", "G")]
NULL_ARMS = ("G", "R+", "U", "UR", "V2", "V2n")


def file_sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def suites() -> tuple[list[list[str]], dict]:
    with open(POOL) as fh:
        tasks = json.load(fh)["tasks"]
    kept, removed = exclude_handwritten(tasks)
    parts = partition_weighted(kept, WEIGHTS, seed=PARTITION_SEED)
    info = {"pool_file_sha256": file_sha256(POOL), "pool_tasks": len(tasks), "excluded_handwritten": removed,
            "kept": len(kept), "partition_seed": PARTITION_SEED, "weights": WEIGHTS,
            "suite_sha256": hashlib.sha256(json.dumps(parts).encode()).hexdigest()}
    return parts, info


def load_r2b(name: str, null: bool = False):
    parts, _ = suites()
    k = NAMES.index(name)
    w = build_world_from_suite(name, parts[k], seed=200 + k, cache_dir=CACHE, split=SPLIT, screen_visible=True)
    if null:
        w.pool = [lid for i, lid in enumerate(w.pool) if not w.fingerprint(i, 0).any()]
        w.name += "-null"
    return w


def prior_ranker(w, led: Ledger):
    return ExperienceStore.load(EXP).ranker_for(w, default_ranker(w), led, gen_id="gen-prior-r2bcal")


def build_experience(runs: int = 150) -> dict:
    if os.path.exists(EXP):
        return ExperienceStore.load(EXP).sources
    w = load_r2b(NAMES[0])
    led = Ledger()
    b = BudgetBroker(total=1e9, ledger=led)      # cost is reported, and disclosed as amortised
    labels = label_pool(w, b, seed=7, runs=runs)
    st = ExperienceStore()
    st.add_world_labels(w, labels, NAMES[0], cost=b.used, ledger=led)
    st.save(EXP)
    return st.sources


def run_arm(arm: str, name: str, th: dict | None, budget: float, null: bool = False) -> dict:
    t0 = time.time()
    w = load_r2b(name, null)
    seed = 200 + NAMES.index(name)
    led = Ledger()
    out = {"arm": arm, "world": name, "null": null, "budget": budget}
    if arm == "D":
        fuel = int(min(200000, budget * w.n_tasks("DEV") * w.solver.fuel / max(1, w.sealed.size("SEALED"))))
        j = judge_sealed(w, [], seed=seed, actor="D", fuel=fuel, max_depth=3, unsafe_dev=True)
        out.update(admitted=[], spent=budget, fuel=fuel)
    elif arm in ("V2", "V2n", "V2r"):
        kw = dict(round_policy="power")
        if arm in ("V2", "V2r"):
            kw.update(focus_size=FOCUS, prior_ranker=prior_ranker(w, led))
        if arm == "V2r":
            kw.update(focus_rotation="rotate")
        camp = Campaign(w, budget, seed, policy="u5", ledger=led, **kw)
        res = camp.run(max_steps=80)
        j = judge_sealed(w, [], seed=seed, actor=arm, unsafe_dev=True)
        rounds = [e["payload"] for e in led.entries if e["kind"] == "u5.round"]
        refused = [e["payload"] for e in led.entries if e["kind"] == "pool.refused"]
        out.update(admitted=[w.statement(i) for i in w.accepted_extra], spent=res.spent, steps=res.steps,
                   generations=res.generations, stops=res.stops, rounds=rounds, pool_refused=refused)
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
    for arm in ("G", "R+", "U"):
        grid = GRIDS[arm]
        res = list(pool.map(_job, [(arm, NAMES[0], th, budget, False) for th in grid]))
        best = max(range(len(grid)), key=lambda k: (res[k]["confirm_solved"], -k))
        chosen[arm] = grid[best]
        print(f"calibrated {arm}: {grid[best]} confirm={[r['confirm_solved'] for r in res]}", flush=True)
    chosen["UR"] = chosen["U"]
    return chosen


def analyse(results: list[dict], budgets: list[float], margin: float = 0.03) -> dict:
    per_budget = {}
    family = []
    for budget in budgets:
        by: dict[str, list[int]] = {}
        for r in sorted(results, key=lambda r: r["world"]):
            if r["null"] or r["budget"] != budget:
                continue
            by.setdefault(r["arm"], []).extend(r["sealed"])
        if not by:
            continue
        n = len(next(iter(by.values())))

        def mc(a, b):
            m = stats.mcnemar(np.array(by[a], bool), np.array(by[b], bool))
            return {"a": a, "b": b, "budget": budget, "a_only": m.b, "b_only": m.c, "p": m.pvalue, "diff": m.diff}

        prim = [mc(a, b) for a, b in PRIMARY if a in by and b in by]
        family += prim
        sec = [mc(a, b) for a, b in SECONDARY if a in by and b in by]
        tost = None
        if "U" in by and "R+" in by:
            t = stats.tost_paired(by["U"], by["R+"], margin)
            tost = {"verdict": t.verdict, "mean_diff": t.mean_diff, "ci90": t.ci90}
        null = {r["arm"]: {"admitted": len(r["admitted"]), "sealed_solved": r["sealed_solved"]}
                for r in results if r["null"] and r["budget"] == budget}
        per_budget[f"B{int(budget)}"] = {
            "n_sealed": n, "solve_rate": {a: float(np.mean(v)) for a, v in by.items()},
            "primary": prim, "secondary": sec, "tost_U_vs_Rplus": tost, "null_world": null,
            "pilot": n < stats.mcnemar_sample_size(0.10, 0.05, 0.05 / (len(PRIMARY) * len(budgets)), 0.8)}
    rej = stats.holm([t["p"] for t in family], 0.05) if family else []
    for t, r in zip(family, rej):
        t["holm_reject_all_budgets"] = bool(r)
    return {"per_budget": per_budget, "holm_family_size": len(family)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--budgets", default="150,400,1000")
    ap.add_argument("--arms", default="D,G,R+,U,UR,V2,V2n")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--prereg", default="experiments/prereg_round2b.json")
    ap.add_argument("--out", default="experiments/results/round2b.json")
    ap.add_argument("--build_only", action="store_true")
    a = ap.parse_args(argv)
    budgets = [float(x) for x in a.budgets.split(",")]
    arms = a.arms.split(",")
    t0 = time.time()
    _, suite_info = suites()
    for nm in NAMES:
        w = load_r2b(nm)
        print(f"world {nm}: DEV {w.n_tasks('DEV')} SELECT {w.n_tasks('SELECT')} CONFIRM {w.n_tasks('CONFIRM')} "
              f"SEALED {w.sealed.size('SEALED')} pool {len(w.pool)} visible_screened {w.meta['visible_screened']} "
              f"({time.time() - t0:.0f}s)", flush=True)
    src = build_experience()
    print(f"experience: {src} ({time.time() - t0:.0f}s)", flush=True)
    if a.build_only:
        return
    plan = {"experiment": "round 2b: round 2 re-run on leak-free worlds (round 2 superseded)",
            "arms": arms, "budgets": budgets, "worlds": NAMES[1:], "calibration_world": NAMES[0],
            "suites": suite_info, "experience_file_sha256": file_sha256(EXP), "experience_sources": src,
            "primary_family": [f"{x} vs {y} at B={int(b)}" for b in budgets for x, y in PRIMARY],
            "test": "McNemar exact on pooled sealed theorems; Holm over the whole primary family "
                    f"({len(PRIMARY) * len(budgets)} tests) at alpha 0.05",
            "equivalence": "TOST U vs R+ margin 0.03",
            "null_world": f"inert-pool variant of {NAMES[1]} for {', '.join(NULL_ARMS)}; V2/V2n create their own "
                          "lemmas, so their inert-pool admissions are reported as discoveries, not false positives",
            "not_included": "V2r (focus rotation, added after round 2) is not in the confirmatory set; its "
                            "development evidence is reported separately (rotation_dev, never on test worlds)",
            "experience_cost_note": "the calibration-world labelling cost is reported and not charged to V2/UR",
            "cascade": {"design": "2x2 (bundle A present/absent x campaign run/not run), scored on SEALED through "
                                  "the kernel judge (round 2 scored CONFIRM, which Gate J also uses)",
                        "campaign": "V2 configuration (power rounds, focus 40, carried ranker)", "budget": 300,
                        "seeds": [0, 1], "bundle": "first FDR-surviving pair of a U round at B=150 on DEV",
                        "report": "per-world estimates with 95% CI and the inverse-variance pooled estimate"},
            "decision_rules": ["adopt V2 over U only if V2 beats U after Holm (whole family) and never loses",
                               "credit U3 only if UR beats U after Holm (whole family)",
                               "fewer sealed tasks than the power analysis requires: pilot"]}
    if not os.path.exists(a.prereg):
        write_prereg(a.prereg, plan)
    plan = load_verified(a.prereg)
    if plan["experience_file_sha256"] != file_sha256(EXP) or plan["suites"]["suite_sha256"] != suite_info["suite_sha256"]:
        raise SystemExit("experience file or suites differ from the preregistration")
    results = []
    with ProcessPoolExecutor(a.workers) as pool:
        chosen = calibrate(pool, 150.0)
        jobs = [(arm, nm, chosen.get(arm), b, False) for b in budgets for nm in NAMES[1:] for arm in arms]
        jobs += [(arm, NAMES[1], chosen.get(arm), b, True) for b in budgets for arm in NULL_ARMS if arm in arms]
        for r in pool.map(_job, jobs):
            results.append(r)
            print(f"{'NULL ' if r['null'] else ''}B={r['budget']:.0f} {r['arm']:3s} {r['world']}: sealed "
                  f"{r['sealed_solved']}/{len(r['sealed'])} admitted {len(r['admitted'])} spent {r['spent']:.0f} "
                  f"({r['seconds']}s, total {time.time() - t0:.0f}s)", flush=True)
            with open(a.out + ".partial", "w") as fh:
                json.dump(results, fh, default=str)
    load_verified(a.prereg)
    calibrated = all(arm in chosen for arm in ("G", "R+", "U", "UR") if arm in arms)
    null_reported = all(any(r["null"] and r["arm"] == arm and r["budget"] == b for r in results)
                        for arm in NULL_ARMS if arm in arms for b in budgets)
    inv23_matched_comparison(calibrated=calibrated, null_world_reported=null_reported)
    analysis = analyse(results, budgets)
    with open(a.out, "w") as fh:
        json.dump({"plan": plan, "thresholds": chosen, "experience": src, "results": results,
                   "analysis": analysis}, fh, indent=1, default=str)
    for k, v in analysis["per_budget"].items():
        print(k, json.dumps({"rates": {a_: round(x, 3) for a_, x in v["solve_rate"].items()},
                             "primary": [(t["a"], t["b"], t["a_only"], t["b_only"], round(t["p"], 5),
                                          t["holm_reject_all_budgets"]) for t in v["primary"]]}))


if __name__ == "__main__":
    main()
