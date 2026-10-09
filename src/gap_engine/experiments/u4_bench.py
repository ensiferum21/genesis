"""U4 acceptance in miniature: learned procedures with certified preconditions vs baselines.

1. Explore random well-typed programs on failed goals of the base theory and of TRAIN
   counterfactual theories; compress the successful traces into procedures.
2. Certify each procedure's precondition by CEGIS (attacks in TRAIN worlds).
3. On SEALED-family worlds only, compare invocation policies on goals the base solver
   fails: none / always (every procedure in order) / precondition-gated / one random.
Metrics: goals solved, compute spent, wasted invocations, solves per unit compute.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ..adapters.induction.checker import LemmaStore
from ..adapters.induction.mutate import SEALED_MUTATIONS, TRAIN_MUTATIONS, mutate, random_mutant
from ..adapters.induction.theory import Theory
from ..kernel.budget import BudgetBroker
from ..kernel.invariants import inv19_only_sealed_judges
from ..u4 import dsl
from ..u4.cegis import _failed_goals, certify, fit_decision_list, world_tasks
from ..u4.compress import compress, explore
from ..u4.features import goal_features
from ..u4.procedures import run


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--out", default="experiments/results/u4_procedures.json")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(a.seed)
    base = Theory.default()
    t0 = time.time()
    # 1. exploration + compression on training worlds
    traces = []
    train_worlds = [base] + [mutate(base, n, TRAIN_MUTATIONS, "counterfactual") for n in list(TRAIN_MUTATIONS)[:2]]
    for th in train_worlds:
        failed = [eq for eq, _ in _failed_goals(th, world_tasks(th, 50, rng), 150)]
        mk = lambda th=th: dsl.ResearchContext(th, LemmaStore(th), {}, BudgetBroker(total=1e9), seed=a.seed)
        log = explore(mk, failed, rng, episodes_per_task=4, max_cost=1.5)
        traces += log.successes
    procs = compress(traces, top=a.top)
    print(f"explored: {len(traces)} successful traces; procedures: {procs} ({time.time() - t0:.0f}s)", flush=True)
    # 2. CEGIS certification
    contracts = []
    for k, (prog, gain) in enumerate(procs):
        rep = certify(f"proc{k}", prog, base, seed=a.seed + k)
        contracts.append((prog, rep))
        print(f"proc{k} {prog}: {rep.contract.status} pre={rep.contract.precondition} "
              f"sealed P={rep.contract.sealed_precision} R={rep.contract.sealed_recall} ({time.time() - t0:.0f}s)",
              flush=True)
    gated = [(prog, rep.dl) for prog, rep in contracts]
    # 3. sealed evaluation of invocation policies
    policies = {"none": 0, "always": 0, "precondition": 0, "random_one": 0}
    cost = {k: 0.0 for k in policies}
    wasted = {k: 0 for k in policies}
    n_goals = 0
    for name in SEALED_MUTATIONS:
        th = mutate(base, name, SEALED_MUTATIONS, "sealed")
        inv19_only_sealed_judges(th.origin)
        for eq, f in _failed_goals(th, world_tasks(th, 60, np.random.default_rng(777)), 150):
            n_goals += 1
            def attempt(prog):
                ctx = dsl.ResearchContext(th, LemmaStore(th), {}, BudgetBroker(total=1e9), seed=a.seed)
                r = run(prog, ctx, eq, max_cost=1.5)
                return r.solved, r.cost
            for pol in ("always", "precondition", "random_one"):
                if pol == "always":
                    order = [p for p, _ in gated]
                elif pol == "precondition":
                    order = [p for p, dl in gated if dl(f)]
                else:
                    order = [gated[int(rng.integers(len(gated)))][0]] if gated else []
                for prog in order:
                    ok, c = attempt(prog)
                    cost[pol] += c
                    if ok:
                        policies[pol] += 1
                        break
                    wasted[pol] += 1
    res = {"procedures": [{"program": list(p), "status": r.contract.status,
                           "precondition": r.contract.precondition,
                           "sealed_precision": r.contract.sealed_precision,
                           "sealed_recall": r.contract.sealed_recall,
                           "sealed_confusion": r.sealed_confusion,
                           "counterexamples": r.counterexamples, "rounds_clean": r.rounds_clean}
                          for p, r in contracts],
           "sealed_goals": n_goals, "solved": policies, "cost": cost, "wasted_invocations": wasted,
           "solves_per_unit": {k: (policies[k] / cost[k] if cost[k] else None) for k in policies},
           "seconds": round(time.time() - t0)}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({k: res[k] for k in ("sealed_goals", "solved", "cost", "wasted_invocations", "solves_per_unit")},
                     indent=1))


if __name__ == "__main__":
    main()
