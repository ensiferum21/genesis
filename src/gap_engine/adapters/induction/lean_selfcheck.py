"""Independent re-reading of an exported Lean file (a translation check, NOT a Lean run).

No Lean toolchain is reachable from the build workspace, so this module re-checks the
generated TEXT on its own, without using the exporter or the trusted checker:

* every term parses back into the theory's term language;
* every theorem's proof is replayed: `induction v generalizing gs with` cases are tracked,
  the goal of each case is the statement with the constructor substituted, and each case's
  induction hypothesis is that goal at the predecessor, quantified over `gs`;
* every `calc` chain starts at its case goal's left side and ends at its right side
  (syntactically);
* every step's justification proves exactly that step:
    `rfl`                      both sides have the same normal form under the theory's
                               defining equations (a sufficient condition for Lean's
                               definitional unfolding of structural recursion);
    `lemma_k a1 .. an`         the cited theorem's statement instantiated with its binders
                               in order (all binders supplied, theorem defined earlier);
    `ihK (v := t) ..`          the case's hypothesis instantiated by name (every
                               generalized variable supplied, no others, IH in scope);
    `Eq.symm p`, `congrArg (fun (hole : S) => C) p`  composed as Lean would;
* every step is also a true equation on random values (a second, semantic net);
* parentheses balance on every code line.

What stays unchecked: Lean's own syntax and elaboration (tactic layout, named-argument
elaboration, universe and instance details). The export header says so.
"""
from __future__ import annotations

import re

import numpy as np

from .terms import match, subst
from .theory import Theory

_TOK = re.compile(r"\(|\)|[A-Za-z_][A-Za-z0-9_.']*")
_PTOK = re.compile(r"\(|\)|:=|=>|:|[A-Za-z_][A-Za-z0-9_.']*")
RFL = "rfl"


class SelfCheckError(ValueError):
    pass


# --------------------------------------------------------------------------- terms
def parse_lean_term(text: str) -> tuple:
    toks = _TOK.findall(text)
    if not toks:
        raise SelfCheckError("empty term")
    pos = [0]

    def atom():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            v = app()
            if pos[0] >= len(toks) or toks[pos[0]] != ")":
                raise SelfCheckError(f"expected ) in {text!r}")
            pos[0] += 1
            return v
        if t == ")":
            raise SelfCheckError(f"unexpected ) in {text!r}")
        return _sym(t)

    def app():
        head = atom()
        args = []
        while pos[0] < len(toks) and toks[pos[0]] != ")":
            args.append(atom())
        if not args:
            return head
        if head[0] == "?":
            raise SelfCheckError(f"variable applied to arguments in {text!r}")
        return (head[0],) + tuple(args)

    v = app()
    if pos[0] != len(toks):
        raise SelfCheckError(f"trailing tokens in {text!r}")
    return v


def _sym(t: str) -> tuple:
    m = {"N.Z": ("Z",), "L.Nil": ("Nil",), "N.S": ("S",), "L.Cons": ("Cons",)}
    if t in m:
        return m[t]
    if t.startswith("g_"):
        return (t[2:],)
    return ("?", t)


def _split_top(s: str, sep: str) -> tuple[str, str]:
    depth = 0
    for i, c in enumerate(s):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and s.startswith(sep, i):
            return s[:i], s[i + len(sep):]
    raise SelfCheckError(f"no top-level {sep!r} in {s!r}")


def _resolve(t, bind: dict):
    for _ in range(64):
        t2 = subst(t, bind)
        if t2 == t:
            return t
        t = t2
    raise SelfCheckError("cyclic case bindings")


def _def_nf(theory: Theory, t, fuel: list):
    """Innermost normal form under the defining equations only."""
    fuel[0] -= 1
    if fuel[0] < 0:
        raise SelfCheckError("normalisation fuel exhausted")
    if t[0] == "?" or len(t) == 1:
        return t
    t = (t[0],) + tuple(_def_nf(theory, a, fuel) for a in t[1:])
    for r in theory.defs.get(t[0], []):
        s = match(r.lhs, t)
        if s is not None:
            return _def_nf(theory, subst(r.rhs, s), fuel)
    return t


def _value(th: Theory, t, env):
    if t[0] == "?":
        return env[t[1]]
    return th.evaluate(t, env, [200000])


def _rand(sort: str, rng):
    if sort == "N":
        return int(rng.integers(0, 5))
    n = int(rng.integers(0, 4))
    return tuple(int(x) for x in rng.integers(0, 5, size=n))


# --------------------------------------------------------------------------- justifications
def _sexp(text: str) -> list:
    toks = _PTOK.findall(text)
    pos = [0]

    def item():
        if pos[0] >= len(toks):
            raise SelfCheckError("unbalanced justification")
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            out = []
            while pos[0] < len(toks) and toks[pos[0]] != ")":
                out.append(item())
            if pos[0] >= len(toks):
                raise SelfCheckError("unbalanced justification")
            pos[0] += 1
            return out
        if t == ")":
            raise SelfCheckError("unbalanced justification")
        return t

    out = []
    while pos[0] < len(toks):
        out.append(item())
    return out


def _unwrap(x):
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x


def _text(x) -> str:
    if isinstance(x, str):
        return x
    return " ".join(f"({_text(y)})" if isinstance(y, list) else y for y in x)


class _Proof:
    def __init__(self, stmts: dict, defined: set):
        self.stmts = stmts                   # name -> (binders, lhs, rhs)
        self.defined = defined

    def eval(self, x, ihs: dict):
        """Equation (l, r) proved by justification `x`, or RFL."""
        x = _unwrap(x)
        if x == "rfl":
            return RFL
        if not isinstance(x, list):
            return self._cite(x, [], ihs)
        head = _unwrap(x[0])
        if head == "Eq.symm":
            if len(x) != 2:
                raise SelfCheckError("Eq.symm takes one argument")
            v = self.eval(x[1], ihs)
            return v if v == RFL else (v[1], v[0])
        if head == "congrArg":
            if len(x) != 3:
                raise SelfCheckError("congrArg takes a function and a proof")
            lam = x[1]
            if not (isinstance(lam, list) and len(lam) >= 4 and lam[0] == "fun" and lam[2] == "=>"):
                raise SelfCheckError("congrArg function is not `fun (hole : S) => C`")
            binder = lam[1]
            if not (isinstance(binder, list) and len(binder) == 3 and binder[1] == ":"):
                raise SelfCheckError("bad lambda binder")
            hole = binder[0]
            ctx = parse_lean_term(_text(lam[3:]))
            v = self.eval(x[2], ihs)
            if v == RFL:
                return RFL
            return subst(ctx, {hole: v[0]}), subst(ctx, {hole: v[1]})
        return self._cite(head, x[1:], ihs)

    def _cite(self, head, args: list, ihs: dict):
        if not isinstance(head, str):
            raise SelfCheckError("bad citation")
        if head in self.stmts:
            if head not in self.defined:
                raise SelfCheckError(f"cites {head} before it is defined")
            binders, L, R = self.stmts[head]
            if len(args) != len(binders):
                raise SelfCheckError(f"{head} applied to {len(args)} arguments, needs {len(binders)}")
            sg = {b: parse_lean_term(_text(a)) for b, a in zip(binders, args)}
            return subst(L, sg), subst(R, sg)
        if re.fullmatch(r"ih\d+", head):
            if head not in ihs:
                raise SelfCheckError(f"{head} used outside its case")
            L, R, gens = ihs[head]
            sg = {}
            for a in args:
                if not (isinstance(a, list) and len(a) >= 3 and a[1] == ":="):
                    raise SelfCheckError(f"{head} argument is not named")
                sg[a[0]] = parse_lean_term(_text(a[2:]))
            if set(sg) != set(gens):
                raise SelfCheckError(f"{head} instantiated with {sorted(sg)}, generalized {sorted(gens)}")
            return subst(L, sg), subst(R, sg)
        if re.fullmatch(r"(lemma|thm)_\d+", head):
            raise SelfCheckError(f"cites {head} before it is defined")
        raise SelfCheckError(f"unknown justification head {head!r}")


# --------------------------------------------------------------------------- driver
class _Frame:
    def __init__(self, indent: int, bind: dict, sorts: dict, ihs: dict):
        self.indent, self.bind, self.sorts, self.ihs = indent, bind, sorts, ihs


def selfcheck(path: str, theory: Theory, trials: int = 12, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    with open(path) as fh:
        lines = fh.read().split("\n")
    stmts: dict = {}
    defined: set = set()
    report = {"theorems": 0, "steps": 0, "rfl_steps": 0, "cited_steps": 0, "problems": []}
    in_comment = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("/-"):
            in_comment = True
        if in_comment:
            in_comment = not ln.rstrip().endswith("-/")
            i += 1
            continue
        if not ln.lstrip().startswith("--") and ln.count("(") != ln.count(")"):
            report["problems"].append(f"line {i + 1}: unbalanced parentheses")
        m = re.match(r"theorem (\w+)((?: \(\w+ : [NL]\))*) : (.*) := by$", ln)
        if not m:
            if ln.startswith("theorem "):
                report["problems"].append(f"line {i + 1}: unparsed theorem header")
            i += 1
            continue
        name = m.group(1)
        binders = re.findall(r"\((\w+) : ([NL])\)", m.group(2))
        try:
            l_txt, r_txt = _split_top(m.group(3), " = ")
            lhs_t, rhs_t = parse_lean_term(l_txt.strip()), parse_lean_term(r_txt.strip())
        except SelfCheckError as e:
            report["problems"].append(f"{name}: {e}")
            i += 1
            continue
        j = i + 1
        block = []
        while j < len(lines) and lines[j].startswith("  "):
            block.append((j, lines[j]))
            j += 1
        if not block:
            report["problems"].append(f"{name}: empty proof")
        try:
            _check_block(theory, name, lhs_t, rhs_t, dict(binders), block, _Proof(stmts, defined), rng,
                         trials, report)
        except (SelfCheckError, KeyError, IndexError) as e:
            report["problems"].append(f"{name}: {e!r}")
        stmts[name] = ([b for b, _ in binders], lhs_t, rhs_t)
        defined.add(name)
        report["theorems"] += 1
        i = j
    report["ok"] = not report["problems"]
    return report


def _check_block(theory, name, lhs_t, rhs_t, sorts, block, prover: _Proof, rng, trials, report):
    frames = [_Frame(0, {}, dict(sorts), {})]
    chain: list[tuple] = []
    ind_info: dict[int, tuple] = {}

    def flush(frame: _Frame):
        if not chain:
            return
        gl, gr = _resolve(lhs_t, frame.bind), _resolve(rhs_t, frame.bind)
        if chain[0][0] != gl or chain[-1][1] != gr:
            report["problems"].append(f"{name}: chain does not run from the case goal's left to right side")
        chain.clear()

    for k, ln in block:
        ind = len(ln) - len(ln.lstrip())
        s = ln.strip()
        while len(frames) > 1 and ind < frames[-1].indent:
            flush(frames[-1])
            frames.pop()
        mi = re.match(r"induction (\w+)(?: generalizing ((?:\w+ ?)+))? with$", s)
        if mi:
            flush(frames[-1])
            gens = (mi.group(2) or "").split()
            v = mi.group(1)
            if v not in frames[-1].sorts:
                raise SelfCheckError(f"induction on {v}, which is not a free variable of the case")
            ind_info[ind] = (v, gens, frames[-1])
            continue
        mc = re.match(r"\| (Z|S|Nil|Cons)((?: \w+)*) =>$", s)
        if mc:
            if ind not in ind_info:
                raise SelfCheckError(f"case line {k + 1} without an induction")
            v, gens, parent = ind_info[ind]
            while frames[-1] is not parent:
                flush(frames[-1])
                frames.pop()
            ctor, names = mc.group(1), mc.group(2).split()
            want = {"Z": 0, "S": 2, "Nil": 0, "Cons": 3}[ctor]
            if len(names) != want:
                raise SelfCheckError(f"case {ctor} binds {names}")
            vsort = parent.sorts[v]
            if (ctor in ("Z", "S")) != (vsort == "N"):
                raise SelfCheckError(f"case {ctor} for a variable of sort {vsort}")
            sorts2 = {x: srt for x, srt in parent.sorts.items() if x != v}
            ihs2 = dict(parent.ihs)
            gl, gr = _resolve(lhs_t, parent.bind), _resolve(rhs_t, parent.bind)
            if ctor == "Z":
                ct = ("Z",)
            elif ctor == "Nil":
                ct = ("Nil",)
            elif ctor == "S":
                ct = ("S", ("?", names[0]))
                sorts2[names[0]] = "N"
                ihs2[names[1]] = (subst(gl, {v: ("?", names[0])}), subst(gr, {v: ("?", names[0])}), gens)
            else:
                ct = ("Cons", ("?", names[0]), ("?", names[1]))
                sorts2[names[0]], sorts2[names[1]] = "N", "L"
                ihs2[names[2]] = (subst(gl, {v: ("?", names[1])}), subst(gr, {v: ("?", names[1])}), gens)
            bind2 = dict(parent.bind)
            bind2[v] = ct
            frames.append(_Frame(ind + 2, bind2, sorts2, ihs2))
            continue
        frame = frames[-1]
        if s == "rfl":
            gl, gr = _resolve(lhs_t, frame.bind), _resolve(rhs_t, frame.bind)
            if _def_nf(theory, gl, [100000]) != _def_nf(theory, gr, [100000]):
                report["problems"].append(f"{name}: bare rfl at line {k + 1} is not definitional")
            report["steps"] += 1
            report["rfl_steps"] += 1
            continue
        mcalc = re.match(r"(calc|_ =)\s+(.*)$", s)
        if not mcalc:
            report["problems"].append(f"{name}: unrecognised line {k + 1}: {s[:60]}")
            continue
        if mcalc.group(1) == "calc":
            flush(frame)
            eq_txt, pf = _split_top(mcalc.group(2), " := ")
            a_txt, b_txt = _split_top(eq_txt, " = ")
            a = parse_lean_term(a_txt.strip())
        else:
            if not chain:
                raise SelfCheckError(f"`_ =` without a preceding calc at line {k + 1}")
            b_txt, pf = _split_top(mcalc.group(2), " := ")
            a = chain[-1][1]
        b = parse_lean_term(b_txt.strip())
        try:
            got = prover.eval(_sexp(pf.strip()), frame.ihs)
        except SelfCheckError as e:
            report["problems"].append(f"{name}: line {k + 1}: {e}")
            got = None
        if got == RFL:
            report["rfl_steps"] += 1
            if _def_nf(theory, a, [100000]) != _def_nf(theory, b, [100000]):
                report["problems"].append(f"{name}: rfl step at line {k + 1} is not definitional")
        elif got is not None:
            report["cited_steps"] += 1
            if got != (a, b):
                report["problems"].append(f"{name}: justification at line {k + 1} proves a different equation")
        for _ in range(trials):
            env = {v: _rand(s_, rng) for v, s_ in frame.sorts.items()}
            try:
                if _value(theory, a, env) != _value(theory, b, env):
                    report["problems"].append(f"{name}: false calc step at line {k + 1}")
                    break
            except (RecursionError, OverflowError, KeyError) as e:
                report["problems"].append(f"{name}: evaluation failed at line {k + 1} ({e!r})")
                break
        chain.append((a, b))
        report["steps"] += 1
    while frames:
        flush(frames[-1])
        frames.pop()
