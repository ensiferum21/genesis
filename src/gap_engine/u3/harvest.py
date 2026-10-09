"""U3 hindsight harvesting: verified experience from every attempt, failures included.

Three sources, all kernel-checked before anything is kept:
  * byproducts - subgoals the solver proved without an induction hypothesis in scope
    (standalone theorems), even when the overall attempt failed;
  * lemma calculation - stuck subgoals generalised into conjectures, tested, then proven;
  * solved DEV tasks - a solved task is a theorem and becomes a candidate lemma.
Every harvested statement is canonicalised, screened against sealed items, and verified by
the LemmaStore before it may enter the candidate pool or a training dataset.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..adapters.induction.adapter import InductionWorld, _lid
from ..adapters.induction.checker import CheckError
from ..adapters.induction.conjecture import canonical, conj_features, generalise_stuck, known_by_rewriting
from ..adapters.induction.prover import Prover
from ..adapters.induction.theory import Equation, counterexample
from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.records import HarvestRecord


@dataclass
class HarvestResult:
    new_pool: list[str] = field(default_factory=list)
    records: list[HarvestRecord] = field(default_factory=list)
    attempts: int = 0
    rejected_sealed: int = 0
    rejected_false: int = 0
    by_source: dict = field(default_factory=dict)


def _simplify(world: InductionWorld, eq: Equation) -> Equation:
    """Normalise both sides with the definitions and the accepted library, so harvested
    statements are stated in simplest form (no reducible subterms)."""
    from ..adapters.induction.prover import Normaliser, PRECEDENCE, RW, orient
    table = {f: k for k, f in enumerate(PRECEDENCE)}
    rules = [RW(r.rid, r.lhs, r.rhs, 1) for r in world.theory.all_rules()]
    for lid, e in world._library([]).items():
        rules.extend(orient(("lemma", lid), e, table))
    N = Normaliser(rules, [0], 20000, table)
    try:
        return Equation(N.norm(eq.lhs)[0], N.norm(eq.rhs)[0])
    except Exception:
        return eq


def _subsumed(world: InductionWorld, eq: Equation) -> bool:
    """True if eq is an instance (either orientation) of a lemma already in the pool or library."""
    from ..adapters.induction.terms import match, subst
    for lid in list(world.pool) + list(world.base_ids) + list(world.accepted_extra):
        g = world.store.verified_subset([lid])[lid]
        for a, b in ((g.lhs, g.rhs), (g.rhs, g.lhs)):
            s_ = match(a, eq.lhs)
            if s_ is not None and subst(b, s_) == eq.rhs:
                return True
            s_ = match(a, eq.rhs)
            if s_ is not None and subst(b, s_) == eq.lhs:
                return True
    return False


def _admit_lemma(world: InductionWorld, eq: Equation, proof: dict | None, source: str, res: HarvestResult,
                 deep_fuel: int, rng) -> None:
    simp = _simplify(world, eq)
    if simp != eq:
        eq, proof = simp, None                         # re-prove the simplified statement
    eq = canonical(eq)
    if eq.lhs == eq.rhs:
        return
    text = eq.text()
    if world.screen_reason(text) is not None:      # sealed near-duplicate or held-out gate task
        res.rejected_sealed += 1
        return
    lid = _lid(eq)
    if lid in world.store.verified_subset(world.store.order):
        return
    if _subsumed(world, eq):
        return
    lib = world._library([])
    if known_by_rewriting(world.theory, lib, eq):
        return                                         # already a consequence of the library
    if proof is None:
        if counterexample(world.theory, eq, rng, trials=80) is not None:
            res.rejected_false += 1
            return
        att = Prover(world.theory, {**lib, **world.store.verified_subset(world.pool)},
                     fuel=deep_fuel, max_depth=2).prove(eq)
        if not att.proved:
            return
        proof = att.proof
        cite_lib = {**lib, **world.store.verified_subset(world.pool)}
    else:
        cite_lib = None
    try:
        world.store.verify(lid, eq, proof)
    except CheckError:
        # the proof may be for the uncanonicalised statement: re-prove canonical form
        att = Prover(world.theory, cite_lib or lib, fuel=deep_fuel, max_depth=2).prove(eq)
        if not att.proved:
            return
        try:
            world.store.verify(lid, eq, att.proof)
        except CheckError:
            return
    if lid not in world.pool and lid not in world.base_ids:
        world.pool.append(lid)
        res.new_pool.append(lid)
    res.records.append(HarvestRecord(text=text, source_task=source, kind="byproduct_lemma",
                                     kernel_verified=True))
    res.by_source[source.split(":")[0]] = res.by_source.get(source.split(":")[0], 0) + 1


def harvest(world: InductionWorld, broker: BudgetBroker, seed: int = 0, deep_fuel: int = 3000,
            max_stuck_per_task: int = 2, category: str = "harvest") -> HarvestResult:
    """Run the solver over DEV with the current library and harvest verified experience.

    Cost: one library evaluation for the sweep plus 0.02 units per deep proof attempt."""
    res = HarvestResult()
    rng = np.random.default_rng(seed)
    try:
        broker.charge(category, 1.0, purpose="harvest sweep")
    except BudgetExceeded:
        return res
    lib = world._library([])
    for t, eq in enumerate(world.tasks["DEV"]):
        att = Prover(world.theory, lib, fuel=world.solver.fuel, max_depth=world.solver.max_depth,
                     seed=seed * 7919 + t).prove(eq)
        res.attempts += 1
        if att.proved:
            _admit_lemma(world, eq, None, f"solved:{t}", res, deep_fuel, rng)
        for geq, gpf in att.byproducts:
            _admit_lemma(world, geq, gpf, f"byproduct:{t}", res, deep_fuel, rng)
        ihs = att.stuck_ih if len(att.stuck_ih) == len(att.stuck) else [None] * len(att.stuck)
        for st, ih in list(zip(att.stuck, ihs))[-max_stuck_per_task:]:
            for cand in generalise_stuck(world.theory, st, max_out=3, ih=ih):
                try:
                    broker.charge(category, 0.02, purpose="lemma calculation")
                except BudgetExceeded:
                    return res
                _admit_lemma(world, cand, None, f"stuck:{t}", res, deep_fuel, rng)
    return res


def usage_labels(world: InductionWorld, extra: list[str], split: str = "DEV", seed: int = 0) -> dict[str, int]:
    """How many tasks' successful proofs cite each lemma (a verified usefulness label)."""
    lib = world._library(extra)
    counts: dict[str, int] = {}
    for t, eq in enumerate(world.tasks[split]):
        att = Prover(world.theory, lib, fuel=world.solver.fuel, max_depth=world.solver.max_depth,
                     seed=seed * 7919 + t).prove(eq)
        if att.proved:
            for lid in att.lemmas_used:
                counts[lid] = counts.get(lid, 0) + 1
    return counts


def features_for(world: InductionWorld, lid: str) -> dict:
    return conj_features(world.store.verified_subset([lid])[lid])
