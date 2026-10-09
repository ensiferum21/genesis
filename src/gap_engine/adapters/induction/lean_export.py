"""Export a theory and verified lemmas/theorems to a Lean 4 file, proof for proof.

NOT CHECKED BY LEAN IN THIS WORKSPACE (no Lean toolchain is reachable from the build
sandbox). `export_lean_certified` translates each certificate that the trusted checker
verified into Lean tactic text step for step: definitions become structural recursion on
fresh types `N` and `L`; each rewrite chain becomes a `calc` whose steps are `rfl` (one
defining equation, which holds definitionally) or `congrArg (fun hole => C[hole]) pf` with
`pf` an exported lemma applied to explicit arguments, or an induction hypothesis with named
arguments; each induction node becomes `induction v generalizing ... with`. Everything is
core Lean 4 (no Mathlib). `lean_selfcheck.py` re-reads the generated text and re-checks
every step independently of this module; only a real Lean run can confirm elaboration.
"""
from __future__ import annotations

from .terms import is_var, var_order
from .theory import LIST, NAT, Equation, Theory, default_var_sort

PREFIX = "g_"


def _lean_term(t) -> str:
    if is_var(t):
        return t[1].replace("'", "_")
    f = t[0]
    if f == "Z":
        return "N.Z"
    if f == "Nil":
        return "L.Nil"
    name = {"S": "N.S", "Cons": "L.Cons"}.get(f, PREFIX + f)
    args = " ".join(_lean_term(a) if (is_var(a) or len(a) == 1) else f"({_lean_term(a)})" for a in t[1:])
    return f"{name} {args}"


def _sort_name(s: str) -> str:
    return "N" if s == NAT else "L"


def _defs(theory: Theory) -> list[str]:
    out = []
    order = ["plus", "minus", "max", "min", "half", "double", "mult", "app", "len", "sum", "replicate",
             "incall", "take", "drop", "rev", "qrev", "rot"]
    for f in order + [g for g in theory.funs if g not in order]:
        if f not in theory.funs:
            continue
        argsorts, res = theory.funs[f]
        sig = " → ".join(_sort_name(s) for s in argsorts) + f" → {_sort_name(res)}"
        out.append(f"def {PREFIX}{f} : {sig}")
        for r in theory.defs[f]:
            pats = ", ".join(_lean_term(a) if (is_var(a) or len(a) == 1) else f"({_lean_term(a)})"
                             for a in r.lhs[1:])
            out.append(f"  | {pats} => {_lean_term(r.rhs)}")
        out.append("")
    return out


# --------------------------------------------------------------------------- certificate-faithful export
def _lv(name: str) -> str:
    return name.replace("'", "_")


def _wrap(t) -> str:
    s = _lean_term(t)
    return s if (is_var(t) or len(t) == 1) else f"({s})"


def _lean_ctx(t, path: tuple, hole: str = "hole") -> str:
    """Lean text of `t` with the subterm at `path` replaced by the variable `hole`."""
    if not path:
        return hole
    i = path[0]
    f = t[0]
    name = {"S": "N.S", "Cons": "L.Cons"}.get(f, PREFIX + f)
    parts = []
    for k, a in enumerate(t[1:], start=1):
        if k == i:
            inner = _lean_ctx(a, path[1:], hole)
            parts.append(inner if len(path) == 1 else f"({inner})")
        else:
            parts.append(_wrap(a))
    return f"{name} {' '.join(parts)}"


class _Exporter:
    """Translates a verified certificate into Lean 4 tactic text, step for step.

    rewrite node  -> `calc` over the replayed intermediate terms; each step is `rfl` for a
                     defining equation (structural recursion reduces definitionally) or
                     `congrArg (fun hole => C[hole]) (lemma args)` / `... (ihK (v := t))`;
    induction node -> `induction v generalizing <non-fixed vars> with | Z | S n ihK ...`.
    The intermediate terms come from the trusted checker's own replay function, so the text
    mirrors exactly what our checker accepted.
    """

    def __init__(self, theory: Theory, lemmas: dict, lean_names: dict, binders: dict):
        self.theory = theory
        self.lemmas = lemmas                 # id -> Equation (verified)
        self.names = lean_names              # id -> Lean theorem name
        self.binders = binders               # id -> ordered variable list of that theorem

    def _pf(self, ctx, t, step) -> tuple[str, object]:
        from .checker import _apply_step
        from .terms import subterm
        path, ref, direction, sub = step
        path = tuple(path)
        t2 = _apply_step(ctx, t, step)
        ref = tuple(ref)
        if ref[0] == "def":
            return "rfl", t2
        sub = dict(sub)
        if ref[0] == "lemma":
            args = " ".join(_wrap(sub[v]) if v in sub else "_" for v in self.binders[ref[1]])
            core = f"{self.names[ref[1]]} {args}".strip()
        else:
            lvl = ref[1]
            eq, frozen = ctx.ihs[lvl]
            gen = [v for v in var_order(eq.lhs) + var_order(eq.rhs) if v not in frozen]
            seen = []
            for v in gen:
                if v not in seen:
                    seen.append(v)
            args = " ".join(f"({_lv(v)} := {_lean_term(sub[v])})" for v in seen if v in sub)
            core = f"ih{lvl} {args}".strip()
        core = f"({core})" if direction == 1 else f"(Eq.symm ({core}))"
        if path:
            srt = _sort_name(self.theory.sort_of(subterm(t, path), ctx.var_sorts))
            core = f"(congrArg (fun (hole : {srt}) => {_lean_ctx(t, path)}) {core})"
        return core, t2

    def proof(self, ctx, goal: Equation, proof: dict, indent: int) -> list[str]:
        from .checker import _Ctx
        from .terms import V, subst
        pad = " " * indent
        if proof["rule"] == "rewrite":
            chain = []                                   # (proof text, from, to)
            t = goal.lhs
            for st in proof.get("left", []):
                pf, t2 = self._pf(ctx, t, st)
                chain.append((pf, t, t2))
                t = t2
            rterms, rpfs = [goal.rhs], []
            r = goal.rhs
            for st in proof.get("right", []):
                pf, r2 = self._pf(ctx, r, st)
                rpfs.append(pf)
                rterms.append(r2)
                r = r2
            for k in range(len(rpfs) - 1, -1, -1):     # walk the right chain backwards
                pf = rpfs[k]
                chain.append(("rfl" if pf == "rfl" else f"(Eq.symm {pf})", rterms[k + 1], rterms[k]))
            if not chain:
                return [f"{pad}rfl"]
            out = [f"{pad}calc {_lean_term(chain[0][1])} = {_lean_term(chain[0][2])} := {chain[0][0]}"]
            for pf, _, b in chain[1:]:
                out.append(f"{pad}  _ = {_lean_term(b)} := {pf}")
            return out
        v = proof["var"]
        sort = ctx.var_sorts.get(v) or default_var_sort(v)
        fresh = list(proof["fresh"])
        gen = [x for x in goal.vars() if x != v and x not in ctx.fixed]
        gen = [x for x in var_order(goal.lhs) + var_order(goal.rhs) if x in gen]
        gen = list(dict.fromkeys(gen))
        lvl = len(ctx.ihs)
        g = f" generalizing {' '.join(_lv(x) for x in gen)}" if gen else ""
        out = [f"{pad}induction {_lv(v)}{g} with"]
        if sort == NAT:
            (n,) = fresh
            base_t, step_t, pred, new_sorts = ("Z",), ("S", V(n)), V(n), {n: NAT}
            out.append(f"{pad}| Z =>")
            base_lines_at = len(out)
            step_head = f"{pad}| S {_lv(n)} ih{lvl} =>"
        else:
            h, tl = fresh
            base_t, step_t, pred, new_sorts = ("Nil",), ("Cons", V(h), V(tl)), V(tl), {h: NAT, tl: LIST}
            out.append(f"{pad}| Nil =>")
            base_lines_at = len(out)
            step_head = f"{pad}| Cons {_lv(h)} {_lv(tl)} ih{lvl} =>"
        base_goal = Equation(subst(goal.lhs, {v: base_t}), subst(goal.rhs, {v: base_t}))
        out[base_lines_at:base_lines_at] = self.proof(ctx, base_goal, proof["base"], indent + 2)
        sorts2 = dict(ctx.var_sorts)
        sorts2.update(new_sorts)
        fixed2 = ctx.fixed | frozenset(fresh)
        ih = Equation(subst(goal.lhs, {v: pred}), subst(goal.rhs, {v: pred}))
        step_goal = Equation(subst(goal.lhs, {v: step_t}), subst(goal.rhs, {v: step_t}))
        ctx2 = _Ctx(ctx.theory, ctx.lemmas, sorts2, fixed2, ctx.ihs + ((ih, fixed2),))
        out.append(step_head)
        out += self.proof(ctx2, step_goal, proof["step"], indent + 2)
        return out


def export_lean_certified(theory: Theory, items: list[tuple[str, str, Equation, dict, str]], path: str,
                          header: str = "") -> dict:
    """items: (id, kind, equation, verified proof, note) in dependency order, where kind is
    "lemma" (may be cited by later items) or "theorem". Every cited lemma must appear
    earlier in `items`. Each proof is re-checked by the trusted checker before export, and
    the Lean text is generated from the checker's own replay. Returns a small report."""
    from .checker import _Ctx, check_proof
    lemmas: dict = {}
    names: dict = {}
    binders: dict = {}
    out = ["/-", "  Gap Engine v2 export (certificate-faithful). Generated; NOT checked by Lean here (the",
           "  build workspace has no Lean toolchain). Every proof below is a step-for-step",
           "  translation of a certificate that the repository's trusted checker",
           "  (src/gap_engine/adapters/induction/checker.py) re-verified during this export:",
           "  `rfl` steps unfold a defining equation, `congrArg` steps rewrite with a previously",
           "  exported lemma or an induction hypothesis at an explicit position.",
           "  Check with: lake env lean GapEngineExport.lean  (Lean 4, core only; no Mathlib).",
           header, "-/", "", "namespace GapEngine", "",
           "inductive N where", "  | Z : N", "  | S : N → N", "  deriving Repr, DecidableEq", "",
           "inductive L where", "  | Nil : L", "  | Cons : N → L → L", "  deriving Repr, DecidableEq", ""]
    out += _defs(theory)
    report = {"lemmas": 0, "theorems": 0, "steps": 0}
    for k, (iid, kind, eq, proof, note) in enumerate(items):
        check_proof(theory, lemmas, eq, proof)          # raises if anything is off
        vs = list(dict.fromkeys(var_order(eq.lhs) + var_order(eq.rhs)))
        nm = f"{'lemma' if kind == 'lemma' else 'thm'}_{k}"
        bnd = " ".join(f"({_lv(v)} : {_sort_name(default_var_sort(v))})" for v in vs)
        ex = _Exporter(theory, lemmas, names, binders)
        ctx = _Ctx(theory, lemmas, {v: default_var_sort(v) for v in eq.vars()})
        body = ex.proof(ctx, eq, proof, 2)
        report["steps"] += sum(1 for ln in body if ":=" in ln)
        if note:
            out.append(f"-- {note}")
        out.append(f"theorem {nm}{' ' + bnd if bnd else ''} : {_lean_term(eq.lhs)} = {_lean_term(eq.rhs)} := by")
        out += body
        out.append("")
        if kind == "lemma":
            lemmas[iid] = eq
            names[iid] = nm
            binders[iid] = vs
            report["lemmas"] += 1
        else:
            report["theorems"] += 1
    out += ["end GapEngine", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(out))
    report["path"] = path
    return report


def dependency_closure(store, ids: list[str]) -> list[str]:
    """`ids` plus every lemma their certificates cite, in the store's verification order."""
    from .checker import _lemma_refs
    need: set = set()
    stack = list(ids)
    while stack:
        i = stack.pop()
        if i in need:
            continue
        need.add(i)
        stack.extend(_lemma_refs(store.proofs[i]))
    return [i for i in store.order if i in need]
