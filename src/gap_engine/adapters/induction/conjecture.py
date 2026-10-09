"""Conjecture generation by enumeration and testing (QuickSpec-style), plus lemma
calculation from stuck subgoals.

Terms over a small signature are enumerated by size, evaluated on a fixed sample of random
environments, and grouped by their value signatures. A term whose signature matches an
earlier representative yields a conjecture `term = representative`; only representatives
are used to build larger terms, which keeps the enumeration small. Conjectures already
derivable by normalisation with the current rules are dropped as known.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from .prover import Normaliser, PRECEDENCE, RW, orient
from .terms import V, Term, is_var, positions, rename_vars, size, subst, term_key, var_order, variables
from .theory import LIST, NAT, CONSTRUCTORS, Equation, Theory, counterexample, default_var_sort, random_value

VARS = {NAT: ["x", "y", "z"], LIST: ["xs", "ys", "zs"]}

THEMES = {
    "plus": ["plus", "S", "Z"],
    "mult": ["mult", "plus", "S", "Z"],
    "double": ["double", "half", "plus", "Z"],
    "minus": ["minus", "plus", "Z", "S"],
    "maxmin": ["max", "min", "plus"],
    "app": ["app", "Nil", "Cons"],
    "rev": ["rev", "app", "Nil", "Cons"],
    "qrev": ["qrev", "rev", "app", "Nil"],
    "len": ["len", "app", "plus", "rev"],
    "sum": ["sum", "app", "plus", "rev"],
    "rot": ["rot", "len", "app"],
    "takedrop": ["take", "drop", "app", "len", "plus", "min", "minus"],
    "replicate": ["replicate", "len", "app", "plus", "sum", "mult"],
    "incall": ["incall", "len", "sum", "app", "plus", "rev"],
}


@dataclass
class Conjecture:
    eq: Equation
    theme: str
    origin: str = "enumeration"            # "enumeration" | "lemma_calculation"
    features: dict = field(default_factory=dict)

    def text(self) -> str:
        return self.eq.text()


def canonical(eq: Equation) -> Equation:
    """Rename variables per sort in first-occurrence order (x, y, z / xs, ys, zs ...)."""
    order = var_order(eq.lhs) + [v for v in var_order(eq.rhs) if v not in var_order(eq.lhs)]
    counters = {NAT: 0, LIST: 0}
    mapping = {}
    for v in order:
        s = default_var_sort(v)
        pool = VARS[s]
        k = counters[s]
        mapping[v] = pool[k] if k < len(pool) else f"{pool[0]}{k}"
        counters[s] += 1
    tmp = {v: f"__t{i}" for i, v in enumerate(order)}
    l = rename_vars(rename_vars(eq.lhs, tmp), {tmp[v]: mapping[v] for v in order})
    r = rename_vars(rename_vars(eq.rhs, tmp), {tmp[v]: mapping[v] for v in order})
    if term_key(r) > term_key(l):
        l, r = r, l
    return Equation(l, r)


class Enumerator:
    def __init__(self, theory: Theory, n_envs: int = 40, seed: int = 0):
        self.theory = theory
        rng = np.random.default_rng(seed)
        self.envs = []
        for k in range(n_envs):
            env = {}
            for s, names in VARS.items():
                for nm in names:
                    env[nm] = random_value(s, rng, max_nat=2 + k % 4, max_len=1 + k % 4)
            self.envs.append(env)

    def signature(self, t: Term) -> tuple:
        out = []
        for env in self.envs:
            try:
                out.append(self.theory.evaluate(t, env, [3000]))
            except (RecursionError, OverflowError, ValueError):
                out.append("!")
        return tuple(out)

    def enumerate(self, symbols: list[str], max_size: int, max_terms: int = 4000) -> list[tuple[Term, Term]]:
        """Return (term, representative) pairs with equal signatures."""
        sig_of = lambda f: self.theory.sig(f)
        reps: dict[tuple[str, int], list[Term]] = {}
        seen: dict[tuple, Term] = {}
        pairs: list[tuple[Term, Term]] = []
        count = 0
        for s, names in VARS.items():
            reps[(s, 1)] = []
            for nm in names:
                t = V(nm)
                reps[(s, 1)].append(t)
                seen.setdefault((s, self.signature(t)), t)
        for f in symbols:
            argsorts, res = sig_of(f)
            if not argsorts:
                t = (f,)
                sg = self.signature(t)
                if (res, sg) not in seen:
                    seen[(res, sg)] = t
                    reps[(res, 1)].append(t)
        for k in range(2, max_size + 1):
            for f in symbols:
                argsorts, res = sig_of(f)
                a = len(argsorts)
                if a == 0:
                    continue
                for parts in _compositions(k - 1, a):
                    pools = [reps.get((argsorts[i], parts[i]), []) for i in range(a)]
                    if any(not p for p in pools):
                        continue
                    for argv in itertools.product(*pools):
                        t = (f,) + tuple(argv)
                        count += 1
                        if count > max_terms:
                            return pairs
                        sg = self.signature(t)
                        if all(v == "!" for v in sg):
                            continue
                        key = (res, sg)
                        if key in seen:
                            pairs.append((t, seen[key]))
                        else:
                            seen[key] = t
                            reps.setdefault((res, k), []).append(t)
        return pairs


def _compositions(n: int, k: int):
    if k == 1:
        yield (n,)
        return
    for i in range(1, n - k + 2):
        for rest in _compositions(n - i, k - 1):
            yield (i,) + rest


def known_by_rewriting(theory: Theory, lemmas: dict, eq: Equation) -> bool:
    table = {f: k for k, f in enumerate(PRECEDENCE)}
    rules = [RW(r.rid, r.lhs, r.rhs, 1) for r in theory.all_rules()]
    for lid, e in lemmas.items():
        rules.extend(orient(("lemma", lid), e, table))
    N = Normaliser(rules, [0], 5000, table)
    try:
        return N.norm(eq.lhs)[0] == N.norm(eq.rhs)[0]
    except Exception:
        return False


def generate(theory: Theory, lemmas: dict, themes: list[str] | None = None, max_size: int = 6,
             seed: int = 0, max_terms: int = 3000, verify_trials: int = 120,
             prune: bool = True) -> list[Conjecture]:
    """Enumerate, test and prune conjectures.

    Pruning (QuickSpec-style): candidates are visited smallest first; a candidate is dropped
    when it follows by rewriting from the definitions, the verified lemmas and the
    candidates already kept (treated as true for pruning only; they are still unproven)."""
    en = Enumerator(theory, seed=seed)
    rng = np.random.default_rng(seed + 1)
    raw: dict[str, tuple[Equation, str]] = {}
    for th_name in (themes or list(THEMES)):
        syms = [s for s in THEMES[th_name] if s in theory.funs or s in CONSTRUCTORS]
        for t, r in en.enumerate(syms, max_size, max_terms):
            eq = canonical(Equation(t, r))
            if eq.lhs == eq.rhs or eq.text() in raw:
                continue
            if not theory.well_sorted_eq(eq.lhs, eq.rhs):
                continue
            if variables(eq.rhs) - variables(eq.lhs) and variables(eq.lhs) - variables(eq.rhs):
                continue
            raw[eq.text()] = (eq, th_name)
    ordered = sorted(raw.values(), key=lambda p: (size(p[0].lhs) + size(p[0].rhs), p[0].text()))
    table = {f: k for k, f in enumerate(PRECEDENCE)}
    rules = [RW(r.rid, r.lhs, r.rhs, 1) for r in theory.all_rules()]
    for lid, e in lemmas.items():
        rules.extend(orient(("lemma", lid), e, table))
    kept: list[Conjecture] = []
    for eq, th_name in ordered:
        if prune:
            N = Normaliser(rules, [0], 20000, table)
            try:
                if N.norm(eq.lhs)[0] == N.norm(eq.rhs)[0]:
                    continue
            except Exception:
                pass
        if counterexample(theory, eq, rng, trials=verify_trials) is not None:
            continue
        kept.append(Conjecture(eq, th_name, "enumeration", features=conj_features(eq)))
        if prune:
            rules.extend(orient(("conj", eq.text()), eq, table))
    return kept


def ih_backward(stuck: Equation, ih: Equation | None) -> list[Equation]:
    """If the IH says f(t) = t for an eigenvariable t, replace t in the stuck goal by f(t)
    ("backward fertilisation"), which exposes a common subterm to generalise."""
    if ih is None:
        return []
    out = []
    for a, b in ((ih.lhs, ih.rhs), (ih.rhs, ih.lhs)):
        if is_var(b) and not is_var(a):
            inner = {sub for _, sub in positions(a) if sub != a and b[1] in variables(sub)}

            def side(t):
                if any(sub in inner for _, sub in positions(t)):
                    return t                       # this side already holds part of the IH
                return _replace_all(t, b, a)
            e = Equation(side(stuck.lhs), side(stuck.rhs))
            if e != stuck:
                out.append(e)
    return out


def generalise_stuck(theory: Theory, stuck: Equation, max_out: int = 6,
                     ih: Equation | None = None) -> list[Equation]:
    """Lemma calculation: propose the stuck goal itself and versions in which a non-variable
    subterm occurring on both sides (or twice) is generalised to a fresh variable; with an
    IH in scope, also after backward fertilisation."""
    out = _generalise_one(theory, stuck, max_out)
    for alt in ih_backward(stuck, ih):
        out += [e for e in _generalise_one(theory, alt, max_out)[1:] if e.text() not in {o.text() for o in out}]
    return out[: max_out * 2]


def _generalise_one(theory: Theory, stuck: Equation, max_out: int) -> list[Equation]:
    cands = [canonical(stuck)]
    counts: dict[Term, int] = {}
    for side in (stuck.lhs, stuck.rhs):
        for _, sub in positions(side):
            if len(sub) > 1:
                counts[sub] = counts.get(sub, 0) + 1
    sorts = {v: default_var_sort(v) for v in stuck.vars()}
    for sub, c in sorted(counts.items(), key=lambda kv: -size(kv[0])):
        if c < 2 or size(sub) < 2:
            continue
        try:
            res = theory.sort_of(sub, sorts)
        except (TypeError, KeyError):
            continue
        fresh = "zs9" if res == LIST else "z9"
        g = Equation(_replace_all(stuck.lhs, sub, V(fresh)), _replace_all(stuck.rhs, sub, V(fresh)))
        if g.lhs != g.rhs:
            cands.append(canonical(g))
        if len(cands) >= max_out:
            break
    uniq, seen = [], set()
    for e in cands:
        if e.text() not in seen:
            seen.add(e.text())
            uniq.append(e)
    return uniq


def _replace_all(t: Term, old: Term, new: Term) -> Term:
    if t == old:
        return new
    if is_var(t) or len(t) == 1:
        return t
    return (t[0],) + tuple(_replace_all(a, old, new) for a in t[1:])


def conj_features(eq: Equation) -> dict:
    from .terms import depth, symbols
    sl, sr = symbols(eq.lhs), symbols(eq.rhs)
    allsym = set(sl) | set(sr)
    vl, vr = variables(eq.lhs), variables(eq.rhs)
    return {
        "size_l": size(eq.lhs), "size_r": size(eq.rhs), "depth_l": depth(eq.lhs),
        "n_vars": len(vl | vr), "n_syms": len(allsym), "vars_balanced": float(vl == vr),
        "rhs_is_var": float(eq.rhs[0] == "?"), "has_list": float(any(default_var_sort(v) == LIST for v in vl | vr)),
        "n_defined": sum(1 for s in allsym if s not in CONSTRUCTORS),
        "symbols": sorted(allsym),
    }
