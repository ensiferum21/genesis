"""Checked feature extractors for goals (the vocabulary of procedure preconditions).

Each feature is a deterministic function of (theory, goal, base-solver attempt). Features
are boolean so that preconditions are small readable formulas.
"""
from __future__ import annotations

from ..adapters.induction.prover import Prover, recursion_positions
from ..adapters.induction.terms import is_var, positions, size, depth, symbols, variables
from ..adapters.induction.theory import LIST, Equation, Theory, default_var_sort


def accumulator_params(theory: Theory) -> dict[str, set[int]]:
    """Argument positions passed a *grown* value in a recursive call (e.g. qrev's 2nd)."""
    out: dict[str, set[int]] = {}
    for f, rules in theory.defs.items():
        for r in rules:
            for _, sub in positions(r.rhs):
                if sub[0] != f:
                    continue
                for i, a in enumerate(sub[1:], start=1):
                    if not is_var(a) and a[0] in ("Cons", "S") and i <= len(r.lhs) - 1:
                        pat = r.lhs[i]
                        if is_var(pat):
                            out.setdefault(f, set()).add(i)
    return out


def _has_snoc(t) -> bool:
    for _, sub in positions(t):
        if sub[0] == "app" and len(sub) == 3 and sub[2][0] == "Cons" and sub[2][2] == ("Nil",):
            return True
    return False


def goal_features(theory: Theory, goal: Equation, library: dict, fuel: int = 150) -> dict[str, bool]:
    acc = accumulator_params(theory)
    rec = recursion_positions(theory)
    f: dict[str, bool] = {}
    syms = set(symbols(goal.lhs)) | set(symbols(goal.rhs))
    vs = goal.vars()
    f["has_list_var"] = any(default_var_sort(v) == LIST for v in vs)
    f["many_vars"] = len(vs) >= 3
    f["big_goal"] = size(goal.lhs) + size(goal.rhs) >= 10
    f["deep_goal"] = max(depth(goal.lhs), depth(goal.rhs)) >= 4
    f["rhs_is_var"] = is_var(goal.rhs) or is_var(goal.lhs)
    # accumulator called with a non-variable accumulator argument: needs generalisation
    acc_const = False
    for side in (goal.lhs, goal.rhs):
        for _, sub in positions(side):
            for i in acc.get(sub[0], ()):
                if i < len(sub) and not is_var(sub[i]):
                    acc_const = True
    f["accumulator_constant"] = acc_const
    f["uses_accumulator_fn"] = any(s in acc for s in syms)
    # a recursive function applied with a non-variable recursion argument (e.g. rot (len xs) xs)
    nonvar_rec = False
    for side in (goal.lhs, goal.rhs):
        for _, sub in positions(side):
            for i in rec.get(sub[0], ()):
                if i < len(sub) and not is_var(sub[i]) and sub[i][0] not in ("Z", "Nil", "S", "Cons"):
                    nonvar_rec = True
    f["nonvar_recursion_arg"] = nonvar_rec
    f["second_arg_recursion"] = any(2 in rec.get(s, set()) and 1 not in rec.get(s, set()) for s in syms)
    f["nested_same_fn"] = any(sub[0] == a[0] for side in (goal.lhs, goal.rhs) for _, sub in positions(side)
                              for a in sub[1:] if not is_var(a) and len(a) > 1)
    att = Prover(theory, library, fuel=fuel, max_depth=2, seed=0).prove(goal)
    f["base_solved"] = att.proved
    f["out_of_fuel"] = "out_of_fuel" in att.trace
    f["stuck_snoc"] = any(_has_snoc(s.lhs) or _has_snoc(s.rhs) for s in att.stuck)
    rep = False
    for s in att.stuck:
        seen = {}
        for side in (s.lhs, s.rhs):
            for _, sub in positions(side):
                if len(sub) > 1:
                    seen[sub] = seen.get(sub, 0) + 1
        if any(c >= 2 and size(t) >= 2 for t, c in seen.items()):
            rep = True
    f["stuck_repeated_subterm"] = rep
    for s in ("rev", "qrev", "rot", "mult", "app", "len", "sum", "take", "drop", "minus", "max", "min",
              "double", "half", "replicate", "incall", "plus"):
        f[f"sym_{s}"] = s in syms
    return f
