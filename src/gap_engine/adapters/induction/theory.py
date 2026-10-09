"""Theories: a signature, constructor sorts and recursive definitions as rewrite rules.

The default theory is Peano naturals and lists of naturals with the classic functions of
the TIP / IsaPlanner inductive benchmarks. Theories are values: U4's counterfactual worlds
are mutated copies (a definition changed, a function removed), checked and evaluated by
the same code.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .terms import Parser, Term, V, is_var, show_eq

NAT, LIST = "Nat", "List"

CONSTRUCTORS = {"Z": ((), NAT), "S": ((NAT,), NAT), "Nil": ((), LIST), "Cons": ((NAT, LIST), LIST)}


def default_var_sort(name: str) -> str:
    base = name.rstrip("'0123456789_")
    if base in ("acc",) or (len(base) >= 2 and base.endswith("s")) or base.startswith("t_"):
        return LIST
    return NAT


@dataclass
class Rule:
    rid: tuple                     # ("def", fname, k)
    lhs: Term
    rhs: Term


DEFAULT_DEFS = {
    "plus": ((NAT, NAT), NAT, ["plus Z y = y", "plus (S x) y = S (plus x y)"]),
    "mult": ((NAT, NAT), NAT, ["mult Z y = Z", "mult (S x) y = plus y (mult x y)"]),
    "double": ((NAT,), NAT, ["double Z = Z", "double (S x) = S (S (double x))"]),
    "half": ((NAT,), NAT, ["half Z = Z", "half (S Z) = Z", "half (S (S x)) = S (half x)"]),
    "minus": ((NAT, NAT), NAT, ["minus Z y = Z", "minus (S x) Z = S x", "minus (S x) (S y) = minus x y"]),
    "max": ((NAT, NAT), NAT, ["max Z y = y", "max (S x) Z = S x", "max (S x) (S y) = S (max x y)"]),
    "min": ((NAT, NAT), NAT, ["min Z y = Z", "min (S x) Z = Z", "min (S x) (S y) = S (min x y)"]),
    "app": ((LIST, LIST), LIST, ["app Nil ys = ys", "app (Cons x xs) ys = Cons x (app xs ys)"]),
    "len": ((LIST,), NAT, ["len Nil = Z", "len (Cons x xs) = S (len xs)"]),
    "rev": ((LIST,), LIST, ["rev Nil = Nil", "rev (Cons x xs) = app (rev xs) (Cons x Nil)"]),
    "qrev": ((LIST, LIST), LIST, ["qrev Nil acc = acc", "qrev (Cons x xs) acc = qrev xs (Cons x acc)"]),
    "sum": ((LIST,), NAT, ["sum Nil = Z", "sum (Cons x xs) = plus x (sum xs)"]),
    "take": ((NAT, LIST), LIST, ["take Z xs = Nil", "take (S n) Nil = Nil",
                                 "take (S n) (Cons x xs) = Cons x (take n xs)"]),
    "drop": ((NAT, LIST), LIST, ["drop Z xs = xs", "drop (S n) Nil = Nil",
                                 "drop (S n) (Cons x xs) = drop n xs"]),
    "rot": ((NAT, LIST), LIST, ["rot Z xs = xs", "rot (S n) Nil = Nil",
                                "rot (S n) (Cons x xs) = rot n (app xs (Cons x Nil))"]),
    "replicate": ((NAT, NAT), LIST, ["replicate Z x = Nil", "replicate (S n) x = Cons x (replicate n x)"]),
    "incall": ((LIST,), LIST, ["incall Nil = Nil", "incall (Cons x xs) = Cons (S x) (incall xs)"]),
}


@dataclass
class Theory:
    name: str = "peano-lists"
    funs: dict[str, tuple[tuple[str, ...], str]] = field(default_factory=dict)  # defined fns
    defs: dict[str, list[Rule]] = field(default_factory=dict)
    origin: str = "base"            # "base" | "counterfactual" | "sealed"

    @classmethod
    def default(cls) -> "Theory":
        th = cls()
        for f, (argsorts, res, eqs) in DEFAULT_DEFS.items():
            th.funs[f] = (argsorts, res)
        p = th.parser()
        for f, (_, _, eqs) in DEFAULT_DEFS.items():
            th.defs[f] = [Rule(("def", f, k), *p.parse_eq(e)) for k, e in enumerate(eqs)]
        return th

    # ------------------------------------------------------------------ signature
    def arity(self) -> dict[str, int]:
        a = {c: len(s[0]) for c, s in CONSTRUCTORS.items()}
        a.update({f: len(s[0]) for f, s in self.funs.items()})
        return a

    def parser(self) -> Parser:
        return Parser(self.arity())

    def sig(self, f: str) -> tuple[tuple[str, ...], str]:
        if f in CONSTRUCTORS:
            return CONSTRUCTORS[f]
        return self.funs[f]

    def all_rules(self) -> list[Rule]:
        return [r for rs in self.defs.values() for r in rs]

    def rule(self, rid: tuple) -> Rule:
        _, f, k = rid
        return self.defs[f][k]

    def sort_of(self, t: Term, var_sorts: dict[str, str]) -> str:
        if is_var(t):
            return var_sorts.get(t[1]) or default_var_sort(t[1])
        argsorts, res = self.sig(t[0])
        if len(argsorts) != len(t) - 1:
            raise TypeError(f"arity mismatch in {t[0]}")
        for a, s in zip(t[1:], argsorts):
            if self.sort_of(a, var_sorts) != s:
                raise TypeError(f"ill-sorted argument to {t[0]}")
        return res

    def well_sorted_eq(self, lhs: Term, rhs: Term, var_sorts: dict[str, str] | None = None) -> bool:
        try:
            return self.sort_of(lhs, var_sorts or {}) == self.sort_of(rhs, var_sorts or {})
        except (TypeError, KeyError):
            return False

    def copy(self) -> "Theory":
        return copy.deepcopy(self)

    def describe(self) -> list[str]:
        return [show_eq(r.lhs, r.rhs) for r in self.all_rules()]

    # ------------------------------------------------------------------ evaluation
    def evaluate(self, t: Term, env: dict, fuel: list | None = None):
        """Evaluate a term to a value: Nat -> int, List -> tuple[int, ...]."""
        fuel = fuel if fuel is not None else [20000]
        fuel[0] -= 1
        if fuel[0] < 0:
            raise RecursionError("evaluation fuel exhausted")
        if is_var(t):
            return env[t[1]]
        f = t[0]
        if f == "Z":
            return 0
        if f == "S":
            v = self.evaluate(t[1], env, fuel)
            if v > 10_000:
                raise OverflowError
            return v + 1
        if f == "Nil":
            return ()
        if f == "Cons":
            return (self.evaluate(t[1], env, fuel),) + self.evaluate(t[2], env, fuel)
        vals = [self.evaluate(a, env, fuel) for a in t[1:]]
        for r in self.defs[f]:
            b = _vmatch_args(r.lhs[1:], vals)
            if b is not None:
                return self.evaluate(r.rhs, b, fuel)
        raise ValueError(f"no rule of {f} matches {vals}")


def _vmatch(p: Term, v, b: dict) -> bool:
    if p[0] == "?":
        b[p[1]] = v
        return True
    f = p[0]
    if f == "Z":
        return v == 0
    if f == "S":
        return isinstance(v, int) and v > 0 and _vmatch(p[1], v - 1, b)
    if f == "Nil":
        return v == ()
    if f == "Cons":
        return isinstance(v, tuple) and len(v) > 0 and _vmatch(p[1], v[0], b) and _vmatch(p[2], v[1:], b)
    raise ValueError(f"non-constructor pattern {f}")


def _vmatch_args(pats, vals):
    b: dict = {}
    for p, v in zip(pats, vals):
        if not _vmatch(p, v, b):
            return None
    return b


@dataclass(frozen=True)
class Equation:
    lhs: Term
    rhs: Term

    def text(self) -> str:
        return show_eq(self.lhs, self.rhs)

    def vars(self) -> set:
        from .terms import variables
        return variables(self.lhs) | variables(self.rhs)


def random_value(sort: str, rng, max_nat: int = 6, max_len: int = 5):
    if sort == NAT:
        return int(rng.integers(0, max_nat + 1))
    n = int(rng.integers(0, max_len + 1))
    return tuple(int(x) for x in rng.integers(0, max_nat + 1, size=n))


def counterexample(th: Theory, eq: Equation, rng, trials: int = 60) -> dict | None:
    """Random testing: return an environment falsifying eq, or None if none found."""
    vs = sorted(eq.vars())
    sorts = {v: default_var_sort(v) for v in vs}
    for k in range(trials):
        env = {v: random_value(sorts[v], rng, max_nat=3 + k % 5, max_len=2 + k % 4) for v in vs}
        try:
            if th.evaluate(eq.lhs, env) != th.evaluate(eq.rhs, env):
                return env
        except (RecursionError, OverflowError):
            continue
    return None
