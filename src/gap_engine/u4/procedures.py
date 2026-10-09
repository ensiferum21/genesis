"""Executable discovery procedures: typed programs over the research language.

A program is a sequence of operation names. The interpreter threads a fixed dataflow:
attempt -> (att), diagnose: att -> stuck, generalise: stuck -> conjs, specialise /
conjecture: goal -> conjs, refute: conjs -> conjs, prove: conjs -> lemmas (verified),
retry / deepen: goal -> solved. A program that uses a value before producing it is
ill-typed and rejected before running.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..kernel.budget import BudgetExceeded
from . import dsl

PRODUCES = {"attempt": "att", "diagnose": "stuck", "generalise": "conjs", "specialise": "conjs",
            "conjecture": "conjs", "refute": "conjs", "prove": "lemmas", "retry": "solved", "deepen": "solved"}
NEEDS = {"attempt": set(), "diagnose": {"att"}, "generalise": {"stuck"}, "specialise": set(),
         "conjecture": set(), "refute": {"conjs"}, "prove": {"conjs"}, "retry": set(), "deepen": set()}


def well_typed(prog: tuple[str, ...]) -> bool:
    have: set[str] = set()
    for op in prog:
        if op not in PRODUCES or not NEEDS[op] <= have:
            return False
        have.add(PRODUCES[op])
    return bool(prog) and PRODUCES[prog[-1]] in ("solved", "att")


@dataclass
class RunResult:
    solved: bool
    cost: float
    trace: list[str]
    lemmas: list[str]


def run(prog: tuple[str, ...], ctx: dsl.ResearchContext, goal, max_cost: float = 3.0) -> RunResult:
    if not well_typed(prog):
        raise ValueError(f"ill-typed program {prog}")
    start = ctx.broker.used
    start_trace = len(ctx.trace)
    st: dict = {}
    solved = False
    lemmas: list[str] = []
    try:
        for op in prog:
            if ctx.broker.used - start > max_cost:
                break
            if op == "attempt":
                st["att"] = dsl.op_attempt(ctx, goal)
                if st["att"].proved:
                    solved = True
                    break
            elif op == "diagnose":
                st["stuck"] = dsl.op_diagnose(ctx, st["att"])
            elif op == "generalise":
                st["conjs"] = dsl.op_generalise(ctx, st["stuck"])
            elif op == "specialise":
                st["conjs"] = dsl.op_specialise(ctx, goal)
            elif op == "conjecture":
                st["conjs"] = dsl.op_conjecture(ctx, goal)
            elif op == "refute":
                st["conjs"] = dsl.op_refute(ctx, st["conjs"])
            elif op == "prove":
                got = dsl.op_prove(ctx, st["conjs"])
                lemmas.extend(got)
            elif op == "retry":
                if dsl.op_retry(ctx, goal):
                    solved = True
                    break
            elif op == "deepen":
                if dsl.op_deepen(ctx, goal):
                    solved = True
                    break
    except BudgetExceeded:
        pass
    return RunResult(solved, ctx.broker.used - start, ctx.trace[start_trace:], lemmas)


BUILTIN = {
    "lemma_calculation": ("attempt", "diagnose", "generalise", "refute", "prove", "retry"),
    "variant_ladder": ("attempt", "specialise", "refute", "prove", "retry"),
    "theory_exploration": ("attempt", "conjecture", "refute", "prove", "retry"),
    "deepen": ("attempt", "deepen"),
}


def random_program(rng: np.random.Generator, min_len: int = 2, max_len: int = 7) -> tuple[str, ...]:
    """Sample a well-typed program from a small grammar prior:
    attempt [source [refute] [prove]] (retry | deepen), source in {diagnose generalise,
    specialise, conjecture}. Every sample is type-checked before use."""
    for _ in range(200):
        prog = ["attempt"]
        r = rng.random()
        if r < 0.4:
            prog += ["diagnose", "generalise"]
        elif r < 0.65:
            prog += ["specialise"]
        elif r < 0.8:
            prog += ["conjecture"]
        if len(prog) > 1:
            if rng.random() < 0.7:
                prog.append("refute")
            if rng.random() < 0.85:
                prog.append("prove")
        prog.append("retry" if ("prove" in prog or rng.random() < 0.5) else "deepen")
        t = tuple(prog)
        if well_typed(t) and min_len <= len(t) <= max_len:
            return t
    return BUILTIN["deepen"]
