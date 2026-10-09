"""Planted-synergy benchmark through the package (reproduces and extends the prototype).

Each arm's thresholds are calibrated on separate worlds to a matched false-discovery limit
(INV-23), evaluated on fresh worlds and on null worlds, at several budgets, with and
without common random numbers.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..adapters.synthetic import SyntheticWorld, WorldSpec
from ..engine.arms import ARMS, GRIDS
from ..kernel.invariants import inv23_matched_comparison


def score(world: SyntheticWorld, res) -> dict:
    truth = world.true_pairs()
    lib = set(res.direct)
    for a, b in res.pairs:
        lib |= {a, b}
    return dict(syn_recall=len(res.pairs & truth) / max(1, len(truth)),
                syn_fp=len(res.pairs - truth),
                direct_recall=len(res.direct & world.true_direct()) / len(world.direct),
                direct_fp=len(res.direct - world.true_direct()),
                value_frac=world.value_fraction(lib), spent=res.spent)


def _eval_one(args):
    arm, th, b, spec_kw, crn, seed, w, null = args
    spec = WorldSpec(**spec_kw)
    world = SyntheticWorld(spec, seed=hash((seed, w)) % (2 ** 31), null=null)
    fn = ARMS[arm][0]
    res = fn(world, float(b), seed * 1000 + w, crn, th)
    return b, score(world, res)


def evaluate(arm, th, budgets, n_worlds, spec_kw, crn, seed, null=False, pool=None):
    jobs = [(arm, th, b, spec_kw, crn, seed, w, null) for w in range(n_worlds) for b in budgets]
    rows = list(pool.map(_eval_one, jobs, chunksize=4)) if pool else [_eval_one(j) for j in jobs]
    out = {}
    for b in budgets:
        rs = [r for bb, r in rows if bb == b]
        out[b] = {k: float(np.mean([r[k] for r in rs])) for k in rs[0]}
        out[b]["syn_recall_sd"] = float(np.std([r["syn_recall"] for r in rs]))
    return out


def calibrate(arm, spec_kw, crn, cal_budget, n_worlds, limit_syn=0.5, limit_dir=0.5, pool=None):
    best, best_th = None, None
    for th in GRIDS[ARMS[arm][1]]:
        m = evaluate(arm, th, [cal_budget], n_worlds, spec_kw, crn, seed=99, pool=pool)[cal_budget]
        if m["syn_fp"] > limit_syn or m["direct_fp"] > limit_dir:
            continue
        key = (m["syn_recall"] + m["direct_recall"], m["value_frac"])
        if best is None or key > best:
            best, best_th = key, th
    return best_th


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="G,R,R+,U")
    ap.add_argument("--budgets", default="20,40,60,90,120,150")
    ap.add_argument("--n-dud", type=int, default=30)
    ap.add_argument("--fp-cost", type=float, default=0.25)
    ap.add_argument("--worlds", type=int, default=30)
    ap.add_argument("--cal-worlds", type=int, default=12)
    ap.add_argument("--null-worlds", type=int, default=20)
    ap.add_argument("--crn", default="0,1")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="experiments/results/synthetic.json")
    a = ap.parse_args(argv)
    budgets = [int(x) for x in a.budgets.split(",")]
    spec_kw = dict(n_dud=a.n_dud, fp_cost=a.fp_cost)
    out = {"spec": spec_kw, "budgets": budgets, "results": {}}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool:
        for crn in [c == "1" for c in a.crn.split(",")]:
            for arm in a.arms.split(","):
                th = calibrate(arm, spec_kw, crn, max(budgets), a.cal_worlds, pool=pool)
                key = f"crn={int(crn)}/{arm}"
                if th is None:
                    out["results"][key] = {"thresholds": None}
                    print(f"{key}: no setting meets the false-discovery limit", flush=True)
                    continue
                ev = evaluate(arm, th, budgets, a.worlds, spec_kw, crn, seed=1, pool=pool)
                nul = evaluate(arm, th, [max(budgets)], a.null_worlds, spec_kw, crn, seed=7, null=True,
                               pool=pool)[max(budgets)]
                inv23_matched_comparison(calibrated=True, null_world_reported=True)
                out["results"][key] = {"thresholds": th, "by_budget": ev,
                                       "null_false_synergies": nul["syn_fp"]}
                print(f"{key} th={th} null_fp={nul['syn_fp']:.2f} ({time.time() - t0:.0f}s)", flush=True)
                for b in budgets:
                    m = ev[b]
                    print(f"   B={b:4d} syn={m['syn_recall']:.2f} sfp={m['syn_fp']:.2f} dir={m['direct_recall']:.2f} "
                          f"dfp={m['direct_fp']:.2f} value={m['value_frac']:.2f}", flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
