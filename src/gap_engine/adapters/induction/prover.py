"""Untrusted proof search: rewriting plus structural induction, emitting checkable proofs.

Strategy (a small Boyer-Moore-style prover):
  1. normalise both sides with definitions, library lemmas and induction hypotheses
     (innermost rewriting; lemmas oriented by a lexicographic path order, permutative
     lemmas used as ordered rewrites);
  2. if the normal forms differ, try one IH application at any position ("fertilisation");
  3. otherwise induct on a variable chosen by recursion analysis (ties broken by the seed),
     recursively, up to `max_depth` nested inductions.
Every success returns a proof object for checker.check_proof. Every failure records the
stuck (normalised) subgoals, which U3 harvests and U4 diagnoses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from .terms import V, Term, is_var, match, replace_at, subst, term_key, var_order, variables, positions
from .theory import LIST, NAT, Equation, Theory, default_var_sort

PRECEDENCE = ["Z", "Nil", "S", "Cons", "plus", "minus", "max", "min", "half", "double", "mult",
              "app", "len", "sum", "replicate", "incall", "take", "drop", "rev", "qrev", "rot"]


class OutOfFuel(Exception):
    pass


def _prec(f: str, table: dict) -> tuple:
    return (table.get(f, len(PRECEDENCE) + 1), f)


def _gprec(u: Term, table: dict) -> tuple:
    if u[0] == "?":
        return (-1, u[1])
    return _prec(u[0], table)


def lpo_gt_ground(s: Term, t: Term, table: dict) -> bool:
    """LPO with goal variables treated as constants below every function symbol.

    Total on such terms and well-founded; any rule oriented by `lpo_gt` decreases under it,
    so ordered rewriting with this check terminates even with AC lemmas present."""
    if s == t:
        return False
    if s[0] != "?":
        for si in s[1:]:
            if si == t or lpo_gt_ground(si, t, table):
                return True
    ps, pt = _gprec(s, table), _gprec(t, table)
    if ps > pt:
        return all(lpo_gt_ground(s, ti, table) for ti in (t[1:] if t[0] != "?" else ()))
    if s[0] == t[0] and s[0] != "?" and len(s) == len(t):
        for i in range(1, len(s)):
            if s[i] != t[i]:
                if not lpo_gt_ground(s[i], t[i], table):
                    return False
                return all(lpo_gt_ground(s, tj, table) for tj in t[1:])
    return False


def lpo_gt(s: Term, t: Term, table: dict) -> bool:
    if is_var(t):
        return s != t and t[1] in variables(s)
    if is_var(s):
        return False
    for si in s[1:]:
        if si == t or lpo_gt(si, t, table):
            return True
    ps, pt = _prec(s[0], table), _prec(t[0], table)
    if ps > pt:
        return all(lpo_gt(s, ti, table) for ti in t[1:])
    if s[0] == t[0] and len(s) == len(t):
        for i in range(1, len(s)):
            if s[i] != t[i]:
                if not lpo_gt(s[i], t[i], table):
                    return False
                return all(lpo_gt(s, tj, table) for tj in t[1:])
        return False
    return False


def match_rigid(pat: Term, t: Term, rigid: frozenset) -> dict | None:
    s: dict = {}
    stack = [(pat, t)]
    while stack:
        p, u = stack.pop()
        if p[0] == "?":
            if p[1] in rigid:
                if u != p:
                    return None
                continue
            prev = s.get(p[1])
            if prev is None:
                s[p[1]] = u
            elif prev != u:
                return None
        else:
            if u[0] == "?" or p[0] != u[0] or len(p) != len(u):
                return None
            stack.extend(zip(p[1:], u[1:]))
    return s


@dataclass
class RW:
    ref: tuple
    src: Term
    dst: Term
    direction: int
    ordered: bool = False
    rigid: frozenset = frozenset()


def orient(ref: tuple, eq: Equation, table: dict, rigid: frozenset = frozenset()) -> list[RW]:
    l, r = eq.lhs, eq.rhs
    vl, vr = variables(l) - rigid, variables(r) - rigid
    out = []
    if lpo_gt(l, r, table) and vr <= vl and not is_var(l):
        out.append(RW(ref, l, r, 1, False, rigid))
    elif lpo_gt(r, l, table) and vl <= vr and not is_var(r):
        out.append(RW(ref, r, l, -1, False, rigid))
    else:
        if vr <= vl and not is_var(l):
            out.append(RW(ref, l, r, 1, True, rigid))
        if vl <= vr and not is_var(r):
            out.append(RW(ref, r, l, -1, True, rigid))
    return out


class Normaliser:
    def __init__(self, rules: list[RW], counter: list, fuel: int, table: dict | None = None):
        self.table = table or {f: k for k, f in enumerate(PRECEDENCE)}
        self.by_head: dict[str, list[RW]] = {}
        for rw in rules:
            self.by_head.setdefault(rw.src[0], []).append(rw)
        self.memo: dict = {}
        self.counter = counter
        self.fuel = fuel

    def _tick(self, k: int = 1):
        self.counter[0] += k
        if self.counter[0] > self.fuel:
            raise OutOfFuel

    def norm(self, t: Term, depth: int = 0) -> tuple[Term, list]:
        if t[0] == "?":
            return t, []
        hit = self.memo.get(t)
        if hit is not None:
            return hit
        if depth > 60:
            raise OutOfFuel
        steps: list = []
        cur = t
        for i in range(1, len(t)):
            a_nf, a_steps = self.norm(cur[i], depth + 1)
            if a_steps:
                steps.extend((((i,) + p), r, d, s) for (p, r, d, s) in a_steps)
                cur = cur[:i] + (a_nf,) + cur[i + 1:]
        for rw in self.by_head.get(cur[0], ()):
            self._tick()
            s = match_rigid(rw.src, cur, rw.rigid) if rw.rigid else match(rw.src, cur)
            if s is None:
                continue
            new = subst(rw.dst, s)
            if rw.ordered and not lpo_gt_ground(cur, new, self.table):
                continue
            self._tick(2)
            steps.append(((), rw.ref, rw.direction, s))
            nf, more = self.norm(new, depth + 1)
            steps.extend(more)
            res = (nf, steps)
            self.memo[t] = res
            return res
        res = (cur, steps)
        self.memo[t] = res
        return res


@dataclass
class Attempt:
    proved: bool
    proof: dict | None
    cost: int
    stuck: list[Equation] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    lemmas_used: set = field(default_factory=set)
    byproducts: list = field(default_factory=list)   # (Equation, proof) proven without any IH
    stuck_ih: list = field(default_factory=list)     # IH in scope for each stuck goal (or None)


def recursion_positions(theory: Theory) -> dict[str, set[int]]:
    pos: dict[str, set[int]] = {}
    for f, rules in theory.defs.items():
        for r in rules:
            for i, a in enumerate(r.lhs[1:], start=1):
                if not is_var(a):
                    pos.setdefault(f, set()).add(i)
    return pos


class Prover:
    def __init__(self, theory: Theory, library: dict[str, Equation], fuel: int = 4000,
                 max_depth: int = 2, max_vars: int = 2, seed: int = 0):
        self.theory = theory
        self.library = library
        self.fuel = fuel
        self.max_depth = max_depth
        self.max_vars = max_vars
        self.rng = np.random.default_rng(seed)
        self.table = {f: k for k, f in enumerate(PRECEDENCE)}
        self.rec_pos = recursion_positions(theory)
        base: list[RW] = []
        for r in theory.all_rules():
            base.append(RW(r.rid, r.lhs, r.rhs, 1))
        for lid, eq in library.items():
            base.extend(orient(("lemma", lid), eq, self.table))
        self.base_rules = base
        self._fresh = 0

    # ------------------------------------------------------------------ helpers
    def fresh(self, stem: str, taken: set) -> str:
        while True:
            self._fresh += 1
            name = f"{stem}{self._fresh}"
            if name not in taken:
                return name

    def induction_candidates(self, goal: Equation, fixed: frozenset) -> list[str]:
        score: dict[str, float] = {}
        for side in (goal.lhs, goal.rhs):
            for _, sub in positions(side):
                for i in self.rec_pos.get(sub[0], ()):
                    a = sub[i]
                    if is_var(a) and a[1] not in fixed:
                        score[a[1]] = score.get(a[1], 0) + 1
        vs = [v for v in var_order(goal.lhs) + var_order(goal.rhs) if v not in fixed]
        seen = []
        for v in vs:
            if v not in seen:
                seen.append(v)
        noise = {v: self.rng.random() * 0.5 for v in seen}
        seen.sort(key=lambda v: -(score.get(v, 0) + noise[v]))
        return seen[: self.max_vars]

    # ------------------------------------------------------------------ search
    def prove(self, goal: Equation) -> Attempt:
        counter = [0]
        att = Attempt(False, None, 0)
        try:
            pf = self._prove(goal, 0, (), frozenset(), counter, att,
                             {v: default_var_sort(v) for v in goal.vars()})
        except OutOfFuel:
            pf = None
            att.trace.append("out_of_fuel")
        att.cost = counter[0]
        if pf is not None:
            att.proved = True
            att.proof = pf
            att.lemmas_used = _lemmas_in(pf)
        return att

    def _rewrite_proof(self, goal: Equation, rules: list[RW], counter) -> tuple[dict | None, Term, Term]:
        N = Normaliser(rules, counter, self.fuel, self.table)
        l, ls = N.norm(goal.lhs)
        r, rs = N.norm(goal.rhs)
        if l == r:
            return {"rule": "rewrite", "left": ls, "right": rs}, l, r
        return None, l, r

    def _prove(self, goal, depth, ihs, fixed, counter, att, sorts) -> dict | None:
        rules = list(self.base_rules)
        for lvl, (ih, ih_fixed) in enumerate(ihs):
            rules.extend(orient(("ih", lvl), ih, self.table, ih_fixed))
        pf, l, r = self._rewrite_proof(goal, rules, counter)
        if pf is not None:
            att.trace.append(f"rewrite@{depth}")
            return pf
        # fertilisation: one IH application anywhere, then normalise again
        for lvl, (ih, ih_fixed) in enumerate(ihs):
            for src, dst, d in ((ih.lhs, ih.rhs, 1), (ih.rhs, ih.lhs, -1)):
                if variables(dst) - ih_fixed - variables(src):
                    continue
                for side_name, side in (("L", l), ("R", r)):
                    for path, sub in positions(side):
                        counter[0] += 1
                        s = match_rigid(src, sub, ih_fixed)
                        if s is None:
                            continue
                        new_side = replace_at(side, path, subst(dst, s))
                        g2 = Equation(new_side, r) if side_name == "L" else Equation(l, new_side)
                        pf2, _, _ = self._rewrite_proof(g2, rules, counter)
                        if pf2 is not None:
                            att.trace.append(f"fertilise@{depth}")
                            return self._compose_fertilise(goal, rules, counter, side_name, path,
                                                           ("ih", lvl), d, s, pf2)
        att.stuck.append(Equation(l, r))
        att.stuck_ih.append(ihs[-1][0] if ihs else None)
        if depth >= self.max_depth:
            return None
        for v in self.induction_candidates(goal, fixed):
            sort = sorts.get(v) or default_var_sort(v)
            taken = set(sorts) | goal.vars() | set(fixed)
            if sort == NAT:
                n = self.fresh("n", taken)
                fresh = [n]
                base_t, step_t, pred = ("Z",), ("S", V(n)), V(n)
                new_sorts = {n: NAT}
            else:
                h = self.fresh("h", taken)
                t = self.fresh("ts", taken | {h})
                fresh = [h, t]
                base_t, step_t, pred = ("Nil",), ("Cons", V(h), V(t)), V(t)
                new_sorts = {h: NAT, t: LIST}
            att.trace.append(f"induct {v}@{depth}")
            base_goal = Equation(subst(goal.lhs, {v: base_t}), subst(goal.rhs, {v: base_t}))
            bp = self._prove(base_goal, depth + 1, ihs, fixed, counter, att, sorts)
            if bp is None:
                continue
            if not ihs and not fixed:
                att.byproducts.append((base_goal, bp))
            ih = Equation(subst(goal.lhs, {v: pred}), subst(goal.rhs, {v: pred}))
            fixed2 = fixed | frozenset(fresh)
            step_goal = Equation(subst(goal.lhs, {v: step_t}), subst(goal.rhs, {v: step_t}))
            sorts2 = dict(sorts)
            sorts2.update(new_sorts)
            sp = self._prove(step_goal, depth + 1, ihs + ((ih, fixed2),), fixed2, counter, att, sorts2)
            if sp is None:
                continue
            return {"rule": "induction", "var": v, "fresh": fresh, "base": bp, "step": sp}
        return None

    def _compose_fertilise(self, goal, rules, counter, side_name, path, ref, d, s, pf2):
        """Proof = normalise side, apply the IH once at `path`, then pf2's chains."""
        N = Normaliser(rules, counter, self.fuel, self.table)
        l, ls = N.norm(goal.lhs)
        r, rs = N.norm(goal.rhs)
        step = (path, ref, d, s)
        if side_name == "L":
            return {"rule": "rewrite", "left": ls + [step] + pf2["left"], "right": rs + pf2["right"]}
        return {"rule": "rewrite", "left": ls + pf2["left"], "right": rs + [step] + pf2["right"]}


def _lemmas_in(pf: dict) -> set:
    out = set()
    if pf["rule"] == "rewrite":
        for st in pf["left"] + pf["right"]:
            if st[1][0] == "lemma":
                out.add(st[1][1])
    else:
        out |= _lemmas_in(pf["base"]) | _lemmas_in(pf["step"])
    return out
