"""Discovery funnel: where failed tasks are lost, measured by hindsight.

For a sample of failed DEV tasks under the current library:
  retrieve/admit - some single pool lemma already solves it (the item exists, not admitted)
  plan           - no single lemma does, but a discovery procedure solves it
  propose        - neither: new conjectures are needed
  check          - the solver claimed a proof the checker rejected (should stay at zero)
The bottleneck is the stage with the largest recoverable loss per unit cost.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..adapters.induction.checker import CheckError, check_proof
from ..adapters.induction.prover import Prover
from ..kernel.budget import BudgetBroker, BudgetExceeded


@dataclass
class Funnel:
    sampled: int = 0
    retrieve: int = 0
    plan: int = 0
    propose: int = 0
    check_rejects: int = 0
    by_task: dict = field(default_factory=dict)

    def shares(self) -> dict[str, float]:
        n = max(1, self.sampled)
        return {"retrieve": self.retrieve / n, "plan": self.plan / n, "propose": self.propose / n,
                "check": self.check_rejects / n}

    def bottleneck(self, unit_costs: dict[str, float] | None = None) -> str:
        c = unit_costs or {"retrieve": 1.0, "plan": 1.5, "propose": 3.0, "check": 1.0}
        sh = self.shares()
        return max(sh, key=lambda k: sh[k] / c[k])


def measure_funnel(world, broker: BudgetBroker, seed: int, sample: int = 12, lemmas_per_task: int = 8,
                   procedure=None, make_ctx=None) -> Funnel:
    rng = np.random.default_rng(seed)
    lib = world._library([])
    fails = []
    for t, eq in enumerate(world.tasks["DEV"]):
        att = Prover(world.theory, lib, fuel=world.solver.fuel, max_depth=world.solver.max_depth,
                     seed=seed * 7919 + t).prove(eq)
        if att.proved:
            try:
                check_proof(world.theory, lib, eq, att.proof)
                continue
            except CheckError:
                pass
        fails.append(t)
    fn = Funnel()
    if not fails:
        return fn
    pick = rng.choice(fails, size=min(sample, len(fails)), replace=False)
    try:
        broker.charge("funnel", 0.05 * len(pick) * lemmas_per_task, purpose="funnel hindsight")
    except BudgetExceeded:
        return fn
    for t in pick:
        eq = world.tasks["DEV"][int(t)]
        fn.sampled += 1
        cands = list(world.pool)
        rng.shuffle(cands)
        hit = False
        for lid in cands[:lemmas_per_task]:
            if world.solve(eq, {**lib, **world.store.verified_subset([lid])}, seed):
                hit = True
                break
        if hit:
            fn.retrieve += 1
            fn.by_task[int(t)] = "retrieve"
            continue
        if procedure is not None and make_ctx is not None:
            from ..u4.procedures import run
            if run(procedure, make_ctx(), eq, max_cost=1.5).solved:
                fn.plan += 1
                fn.by_task[int(t)] = "plan"
                continue
        fn.propose += 1
        fn.by_task[int(t)] = "propose"
    return fn
