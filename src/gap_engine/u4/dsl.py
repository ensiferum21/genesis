"""The research language: a closed set of operations, each checked by its owner.

Operations act on a ResearchContext (theory, verified lemma store, current library,
solver settings, budget). Every call is appended to the context's trace, which is what
U4 compresses into procedures. No operation can mark anything verified: `prove` hands
proofs to the kernel's LemmaStore and only verified lemmas are returned.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from ..adapters.induction.checker import CheckError, LemmaStore, check_proof
from ..adapters.induction.conjecture import THEMES, canonical, generalise_stuck, generate
from ..adapters.induction.prover import Attempt, Prover
from ..adapters.induction.terms import V, subst, var_order
from ..adapters.induction.theory import LIST, NAT, Equation, Theory, counterexample, default_var_sort
from ..kernel.budget import BudgetBroker, BudgetExceeded

OPS = ("attempt", "diagnose", "generalise", "refute", "prove", "retry", "specialise", "conjecture", "deepen")

COST = {"attempt": 0.02, "diagnose": 0.0, "generalise": 0.005, "refute": 0.005, "prove": 0.05,
        "retry": 0.02, "specialise": 0.005, "conjecture": 0.5, "deepen": 0.1}


@dataclass
class ResearchContext:
    theory: Theory
    store: LemmaStore
    library: dict
    broker: BudgetBroker
    fuel: int = 150
    deep_fuel: int = 3000
    seed: int = 0
    trace: list = field(default_factory=list)
    new_lemmas: dict = field(default_factory=dict)

    def charge(self, op: str, k: float = 1.0, record: bool = True) -> None:
        self.broker.charge("research", COST[op] * k, purpose=op)
        if record:
            self.trace.append(op)

    def lib(self) -> dict:
        # Research-visible dictionaries are never proof authorities. Any
        # caller-injected or tampered lemma must fail before solver execution.
        self.store.assert_theory_matches(self.theory)
        requested = {**self.library, **self.new_lemmas}
        trusted = self.store.verified_subset(requested)
        if requested != trusted:
            raise CheckError("research library differs from verified lemma snapshots")
        return trusted


def op_attempt(ctx: ResearchContext, goal: Equation) -> Attempt:
    ctx.charge("attempt")
    att = Prover(ctx.theory, ctx.lib(), fuel=ctx.fuel, max_depth=2, seed=ctx.seed).prove(goal)
    if att.proved:
        try:
            check_proof(ctx.theory, ctx.lib(), goal, att.proof)
        except CheckError:
            att.proved = False
    return att


def op_diagnose(ctx: ResearchContext, att: Attempt) -> list[tuple]:
    ctx.charge("diagnose")
    ihs = att.stuck_ih if len(att.stuck_ih) == len(att.stuck) else [None] * len(att.stuck)
    return list(zip(att.stuck, ihs))[-3:]


def op_generalise(ctx: ResearchContext, stuck: list[tuple]) -> list[Equation]:
    ctx.charge("generalise", max(1, len(stuck)))
    out = []
    for s, ih in stuck:
        out.extend(generalise_stuck(ctx.theory, s, max_out=4, ih=ih))
    return out


def op_refute(ctx: ResearchContext, conjs: list[Equation]) -> list[Equation]:
    ctx.charge("refute", max(1, len(conjs)))
    rng = np.random.default_rng(ctx.seed + 3)
    return [c for c in conjs if counterexample(ctx.theory, c, rng, trials=60) is None]


def op_prove(ctx: ResearchContext, conjs: list[Equation], limit: int = 6) -> list[str]:
    got = []
    ctx.trace.append("prove")
    for c in conjs[:limit]:
        ctx.charge("prove", record=False)
        att = Prover(ctx.theory, ctx.lib(), fuel=ctx.deep_fuel, max_depth=2, seed=ctx.seed).prove(c)
        if not att.proved:
            continue
        lid = "R" + hashlib.sha1(c.text().encode()).hexdigest()[:10]
        try:
            ctx.store.verify(lid, c, att.proof)
        except CheckError:
            continue
        ctx.new_lemmas[lid] = c
        got.append(lid)
    return got


def op_retry(ctx: ResearchContext, goal: Equation) -> bool:
    ctx.charge("retry")
    att = Prover(ctx.theory, ctx.lib(), fuel=ctx.fuel, max_depth=2, seed=ctx.seed + 1).prove(goal)
    if not att.proved:
        return False
    try:
        return check_proof(ctx.theory, ctx.lib(), goal, att.proof)
    except CheckError:
        return False


def op_specialise(ctx: ResearchContext, goal: Equation) -> list[Equation]:
    """Variant ladder: instantiate one variable with a constructor pattern."""
    ctx.charge("specialise")
    out = []
    for v in var_order(goal.lhs):
        if default_var_sort(v) == NAT:
            pats = [("S", V("x9"))]
        else:
            pats = [("Cons", V("x9"), V("xs9"))]
        for p in pats:
            out.append(canonical(Equation(subst(goal.lhs, {v: p}), subst(goal.rhs, {v: p}))))
    return out


def op_conjecture(ctx: ResearchContext, goal: Equation, max_size: int = 5) -> list[Equation]:
    ctx.charge("conjecture")
    from ..adapters.induction.terms import symbols
    syms = set(symbols(goal.lhs)) | set(symbols(goal.rhs))
    themes = [t for t, ss in THEMES.items() if t in syms]
    if not themes:
        return []
    cs = generate(ctx.theory, ctx.lib(), themes=themes[:2], max_size=max_size, seed=ctx.seed,
                  max_terms=800, verify_trials=40)
    return [c.eq for c in cs]


def op_deepen(ctx: ResearchContext, goal: Equation) -> bool:
    ctx.charge("deepen")
    att = Prover(ctx.theory, ctx.lib(), fuel=ctx.fuel * 8, max_depth=3, seed=ctx.seed).prove(goal)
    if not att.proved:
        return False
    try:
        return check_proof(ctx.theory, ctx.lib(), goal, att.proof)
    except CheckError:
        return False
