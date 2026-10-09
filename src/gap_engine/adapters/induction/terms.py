"""First-order terms over Nat and List, with parsing, printing, substitution and matching.

Representation (hashable tuples, fast to compare):
    variable     ("?", name)
    application  (fname, arg1, ..., argk)      constants are 1-tuples, e.g. ("Z",)
"""
from __future__ import annotations

import re
from typing import Iterator

Term = tuple

VAR = "?"


def V(name: str) -> Term:
    return (VAR, name)


def is_var(t: Term) -> bool:
    return t[0] == VAR


def head(t: Term) -> str:
    return t[0]


def args(t: Term) -> tuple:
    return () if is_var(t) else t[1:]


def size(t: Term) -> int:
    if is_var(t):
        return 1
    return 1 + sum(size(a) for a in t[1:])


def depth(t: Term) -> int:
    if is_var(t) or len(t) == 1:
        return 1
    return 1 + max(depth(a) for a in t[1:])


def variables(t: Term, acc: set | None = None) -> set:
    acc = set() if acc is None else acc
    if is_var(t):
        acc.add(t[1])
    else:
        for a in t[1:]:
            variables(a, acc)
    return acc


def var_order(t: Term) -> list[str]:
    """Variables in first-occurrence order."""
    out: list[str] = []

    def go(u):
        if is_var(u):
            if u[1] not in out:
                out.append(u[1])
        else:
            for a in u[1:]:
                go(a)
    go(t)
    return out


def symbols(t: Term, acc: dict | None = None) -> dict:
    acc = {} if acc is None else acc
    if not is_var(t):
        acc[t[0]] = acc.get(t[0], 0) + 1
        for a in t[1:]:
            symbols(a, acc)
    return acc


def subst(t: Term, s: dict) -> Term:
    if is_var(t):
        return s.get(t[1], t)
    if len(t) == 1:
        return t
    return (t[0],) + tuple(subst(a, s) for a in t[1:])


def match(pat: Term, t: Term, s: dict | None = None) -> dict | None:
    """Syntactic one-way matching: find s with subst(pat, s) == t."""
    s = {} if s is None else s
    stack = [(pat, t)]
    while stack:
        p, u = stack.pop()
        if p[0] == VAR:
            prev = s.get(p[1])
            if prev is None:
                s[p[1]] = u
            elif prev != u:
                return None
        else:
            if u[0] == VAR or p[0] != u[0] or len(p) != len(u):
                return None
            stack.extend(zip(p[1:], u[1:]))
    return s


def subterm(t: Term, path: tuple) -> Term:
    for i in path:
        t = t[i]
    return t


def replace_at(t: Term, path: tuple, new: Term) -> Term:
    if not path:
        return new
    i = path[0]
    return t[:i] + (replace_at(t[i], path[1:], new),) + t[i + 1:]


def positions(t: Term, path: tuple = ()) -> Iterator[tuple[tuple, Term]]:
    """Innermost-first (post-order) positions of non-variable subterms."""
    if not is_var(t):
        for i in range(1, len(t)):
            yield from positions(t[i], path + (i,))
        yield path, t


def rename_vars(t: Term, mapping: dict) -> Term:
    return subst(t, {k: V(v) for k, v in mapping.items()})


def show(t: Term) -> str:
    if is_var(t):
        return t[1]
    if t == ("Z",):
        return "Z"
    # numerals
    n, u = 0, t
    while u[0] == "S" and len(u) == 2:
        n += 1
        u = u[1]
    if u == ("Z",) and n > 0:
        return str(n)
    if len(t) == 1:
        return t[0]
    parts = [t[0]]
    for a in t[1:]:
        s = show(a)
        parts.append(s if (is_var(a) or len(a) == 1 or s.isdigit()) else f"({s})")
    return " ".join(parts)


def show_eq(lhs: Term, rhs: Term) -> str:
    return f"{show(lhs)} = {show(rhs)}"


def term_key(t: Term) -> tuple:
    """A total order on terms: smaller size first, then a structural tiebreak."""
    return (size(t), show(t))


def nat(n: int) -> Term:
    t: Term = ("Z",)
    for _ in range(n):
        t = ("S", t)
    return t


_TOK = re.compile(r"\s*(\(|\)|=|[A-Za-z_][A-Za-z0-9_']*|\d+)")


def tokenize(s: str) -> list[str]:
    pos, out = 0, []
    s = s.strip()
    while pos < len(s):
        m = _TOK.match(s, pos)
        if not m:
            raise SyntaxError(f"bad token at {s[pos:]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


class Parser:
    """Applicative syntax: `plus x (S y) = S (plus x y)`. Identifiers that are function
    symbols of the signature are applied to the following atoms; others are variables."""

    def __init__(self, arity: dict[str, int]):
        self.arity = arity

    def parse_term(self, s: str) -> Term:
        toks = tokenize(s)
        t, i = self._expr(toks, 0)
        if i != len(toks):
            raise SyntaxError(f"trailing tokens in {s!r}")
        return t

    def parse_eq(self, s: str) -> tuple[Term, Term]:
        if "=" not in s:
            raise SyntaxError(f"not an equation: {s!r}")
        l, r = s.split("=", 1)
        return self.parse_term(l), self.parse_term(r)

    def _atom(self, toks, i):
        tok = toks[i]
        if tok == "(":
            t, i = self._expr(toks, i + 1)
            if toks[i] != ")":
                raise SyntaxError("expected )")
            return t, i + 1
        if tok.isdigit():
            return nat(int(tok)), i + 1
        if tok in self.arity:
            if self.arity[tok] == 0:
                return (tok,), i + 1
            return None, i                     # function needs args: handled by _expr
        return V(tok), i + 1

    def _expr(self, toks, i):
        tok = toks[i]
        if tok in self.arity and self.arity[tok] > 0:
            f = tok
            i += 1
            argv = []
            for _ in range(self.arity[f]):
                if i >= len(toks) or toks[i] in (")", "="):
                    raise SyntaxError(f"{f} expects {self.arity[f]} arguments")
                if toks[i] in self.arity and self.arity[toks[i]] > 0:
                    a, i = self._expr_nested_error(toks, i)
                else:
                    a, i = self._atom(toks, i)
                argv.append(a)
            return (f,) + tuple(argv), i
        t, i = self._atom(toks, i)
        if t is None:
            raise SyntaxError(f"unexpected {tok!r}")
        return t, i

    def _expr_nested_error(self, toks, i):
        raise SyntaxError(f"unparenthesised application of {toks[i]!r} as an argument")
