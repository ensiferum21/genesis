"""Trusted proof checker for equational induction proofs (the truth kernel of this domain).

The checker does not import or trust the prover. It re-derives every goal itself and
replays every rewrite step. A proof is one of

    {"rule": "rewrite", "left": [step...], "right": [step...]}
        apply the steps to the goal's two sides; the results must be identical
    {"rule": "induction", "var": v, "fresh": [names], "base": proof, "step": proof}
        structural induction on v (Nat: Z | S n'; List: Nil | Cons h t); the checker
        builds the base and step goals and the induction hypothesis itself

and a step is (path, ref, direction, subst) with ref one of
    ("def", f, k)       the k-th defining equation of f in the theory
    ("lemma", id)       a lemma already verified in the LemmaStore (no self-reference)
    ("ih", level)       the induction hypothesis introduced at nesting level `level`

Soundness rules enforced here:
* every rewrite instance is checked syntactically: subst(from) must equal the subterm;
* substitutions are well-sorted and bind every variable of the rewritten-to side;
* eigenvariables introduced by induction steps are fixed: no IH instance may substitute
  them (an IH is about one particular predecessor, not all of them);
* fresh names must not clash with variables in scope;
* lemma references must point to previously verified lemmas (acyclic by construction).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import hashlib
import json

from .proof_codec import encode

from .terms import Term, V, is_var, replace_at, subst, subterm, variables
from .theory import LIST, NAT, Equation, Theory, default_var_sort


class CheckError(ValueError):
    pass


@dataclass
class _Ctx:
    theory: Theory
    lemmas: dict
    var_sorts: dict
    fixed: frozenset = frozenset()
    ihs: tuple = ()                 # tuple of (Equation, fixed_at_level)


def _sort(ctx: _Ctx, t: Term) -> str:
    try:
        return ctx.theory.sort_of(t, ctx.var_sorts)
    except (TypeError, KeyError) as e:
        raise CheckError(f"ill-sorted term: {e}")


def _equation_for(ctx: _Ctx, ref) -> tuple[Equation, frozenset]:
    kind = ref[0]
    if kind == "def":
        _, f, k = ref
        if f not in ctx.theory.defs or not (0 <= k < len(ctx.theory.defs[f])):
            raise CheckError(f"unknown definition {ref}")
        r = ctx.theory.defs[f][k]
        return Equation(r.lhs, r.rhs), frozenset()
    if kind == "lemma":
        eq = ctx.lemmas.get(ref[1])
        if eq is None:
            raise CheckError(f"lemma {ref[1]!r} is not verified")
        return eq, frozenset()
    if kind == "ih":
        lvl = ref[1]
        if not (0 <= lvl < len(ctx.ihs)):
            raise CheckError(f"no induction hypothesis at level {lvl}")
        return ctx.ihs[lvl]
    raise CheckError(f"bad reference {ref!r}")


def _apply_step(ctx: _Ctx, t: Term, step) -> Term:
    try:
        path, ref, direction, sub = step
    except (TypeError, ValueError):
        raise CheckError("malformed step")
    path = tuple(path)
    eq, frozen = _equation_for(ctx, tuple(ref))
    src, dst = (eq.lhs, eq.rhs) if direction == 1 else (eq.rhs, eq.lhs)
    if direction not in (1, -1):
        raise CheckError("direction must be +1 or -1")
    sub = dict(sub)
    for v in sub:
        if v in frozen:
            raise CheckError(f"IH instance substitutes fixed eigenvariable {v!r}")
    # rule variables keep their own sorts (from their names); bound values must agree
    for v, val in sub.items():
        want = ctx.var_sorts.get(v) if (ref[0] == "ih") else default_var_sort(v)
        if want is None:
            want = default_var_sort(v)
        if _sort(ctx, val) != want:
            raise CheckError(f"ill-sorted binding {v}")
    need = variables(dst) - set(sub)
    if ref[0] == "ih":
        need -= set(frozen)                 # fixed vars stay as themselves
        need_src = variables(src) - set(sub) - set(frozen)
    else:
        need_src = variables(src) - set(sub)
    if need or need_src:
        raise CheckError(f"unbound rule variables {sorted(need | need_src)}")
    try:
        target = subterm(t, path)
    except (IndexError, TypeError):
        raise CheckError(f"bad path {path}")
    if subst(src, sub) != target:
        raise CheckError("rewrite instance does not match the subterm")
    return replace_at(t, path, subst(dst, sub))


def _check(ctx: _Ctx, goal: Equation, proof: dict) -> None:
    if _sort(ctx, goal.lhs) != _sort(ctx, goal.rhs):
        raise CheckError("goal sides have different sorts")
    rule = proof.get("rule")
    if rule == "rewrite":
        l, r = goal.lhs, goal.rhs
        for st in proof.get("left", []):
            l = _apply_step(ctx, l, st)
        for st in proof.get("right", []):
            r = _apply_step(ctx, r, st)
        if l != r:
            raise CheckError("rewrite chains do not meet")
        return
    if rule == "induction":
        v = proof["var"]
        if v not in goal.vars():
            raise CheckError(f"induction variable {v!r} not in goal")
        if v in ctx.fixed:
            raise CheckError(f"cannot induct on fixed eigenvariable {v!r}")
        sort = ctx.var_sorts.get(v) or default_var_sort(v)
        fresh = list(proof["fresh"])
        in_scope = goal.vars() | set(ctx.fixed) | set(ctx.var_sorts)
        if any(f in in_scope for f in fresh) or len(set(fresh)) != len(fresh):
            raise CheckError("fresh names clash with variables in scope")
        if sort == NAT:
            if len(fresh) != 1:
                raise CheckError("Nat induction needs one fresh name")
            (n,) = fresh
            base_t, step_t, pred = ("Z",), ("S", V(n)), V(n)
            new_sorts = {n: NAT}
        elif sort == LIST:
            if len(fresh) != 2:
                raise CheckError("List induction needs two fresh names")
            h, tl = fresh
            base_t, step_t, pred = ("Nil",), ("Cons", V(h), V(tl)), V(tl)
            new_sorts = {h: NAT, tl: LIST}
        else:
            raise CheckError(f"no induction principle for sort {sort}")
        s_base = {v: base_t}
        base_goal = Equation(subst(goal.lhs, s_base), subst(goal.rhs, s_base))
        _check(ctx, base_goal, proof["base"])
        sorts2 = dict(ctx.var_sorts)
        sorts2.update(new_sorts)
        fixed2 = ctx.fixed | frozenset(fresh)
        ih = Equation(subst(goal.lhs, {v: pred}), subst(goal.rhs, {v: pred}))
        step_goal = Equation(subst(goal.lhs, {v: step_t}), subst(goal.rhs, {v: step_t}))
        ctx2 = _Ctx(ctx.theory, ctx.lemmas, sorts2, fixed2, ctx.ihs + ((ih, fixed2),))
        _check(ctx2, step_goal, proof["step"])
        return
    raise CheckError(f"unknown proof rule {rule!r}")


def check_proof(theory: Theory, lemmas: dict, goal: Equation, proof: dict) -> bool:
    """Low-level replay, RELATIVE to caller-supplied axioms and lemma premises.

    This function does not authenticate ``lemmas`` or the mathematical theory.
    For admission, use LemmaStore.verify; for solving, obtain premises from
    LemmaStore.verified_subset. A True result alone is not a theorem certificate.
    """
    sorts = {v: default_var_sort(v) for v in goal.vars()}
    _check(_Ctx(theory, lemmas, sorts), goal, proof)
    return True


def _proof_digest(proof: dict) -> str:
    """Canonical, non-executable identity of the *entire* submitted proof tree.

    Distinguishes tuple and list encodings; rejects non-JSON evidence. This digest
    is not a replacement for check_proof, which runs on first admission.
    """
    try:
        payload = json.dumps(encode(proof), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        raise CheckError(f"malformed proof identity: {exc}") from exc
    return hashlib.sha256(payload).hexdigest()


def _theory_digest(theory: Theory) -> str:
    """Deterministic identity of *all* proof-relevant signature/axiom data.

    Only a consistency check within the Python process. It cannot attest the
    original theory or defend against malicious code controlling this process.
    """
    try:
        payload = {
            "schema": "genesis-induction-theory-v1",
            "name": theory.name,
            "origin": theory.origin,
            "funs": theory.funs,
            "defs": {f: [{"rid": r.rid, "lhs": r.lhs, "rhs": r.rhs}
                         for r in rules] for f, rules in theory.defs.items()},
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise CheckError(f"invalid theory identity: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class LemmaStore:
    """Kernel-side store of verified lemmas. Only `verify` adds to it.

    Reused IDs are idempotent *only* for the exact same statement and proof.
    A conflicting reuse raises rather than returning a false acknowledgement.
    """

    theory: Theory
    lemmas: dict = field(default_factory=dict)        # id -> Equation
    proofs: dict = field(default_factory=dict)
    order: list = field(default_factory=list)
    proof_digests: dict = field(default_factory=dict)
    # Private admission-time proof identities. Public proof_digests is a
    # convenience index, NOT an authority: a caller can rewrite both a stored
    # proof and its public digest after verification.
    _trusted_proof_digests: dict = field(default_factory=dict, repr=False)
    # Separate validated snapshots; never use caller-visible mutable `lemmas`
    # as an authority when checking new proofs. This is tamper detection, NOT
    # isolation from malicious code in the same Python process.
    _trusted_lemmas: dict = field(default_factory=dict)
    # The public theory is deliberately mutable for counterfactual research.
    # Proof admission must instead use the deep-copied, pinned snapshot.
    _trusted_theory: Theory | None = field(default=None, repr=False)
    _pinned_theory_sha256: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (self.lemmas or self.proofs or self.order or self._trusted_lemmas
                or self.proof_digests or self._trusted_proof_digests):
            # Constructing a pre-populated store cannot bootstrap trust.
            self._legacy_needs_replay = True
            return
        self._trusted_theory = deepcopy(self.theory)
        self._pinned_theory_sha256 = _theory_digest(self._trusted_theory)

    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)
        if ("_trusted_lemmas" not in state
                or "_trusted_theory" not in state
                or "_pinned_theory_sha256" not in state
                or "_trusted_proof_digests" not in state):
            # Historical pickles lack proof or theory snapshots. Never trust
            # the public registry or unpinned axioms without replay.
            self._trusted_lemmas = {}
            self._trusted_proof_digests = {}
            self._legacy_needs_replay = True

    def _require_pinned_theory(self) -> None:
        pin = self._pinned_theory_sha256
        if not pin or self._trusted_theory is None:
            raise CheckError("no pinned theory; full replay against trusted source required")
        if (_theory_digest(self.theory) != pin
                or _theory_digest(self._trusted_theory) != pin):
            raise CheckError("theory differs from pinned verified snapshot")

    def replay_legacy(self, *, trusted_theory: Theory | None = None) -> None:
        """Rebuild verified snapshots, fail-closed on unpinned old archives.

        An archive without a theory pin needs a separately authenticated
        original theory. Passing an arbitrary theory does not prove custody.
        This is internal replay, not an independent Lean verification.
        """
        if not getattr(self, "_legacy_needs_replay", False):
            self._require_pinned_theory()
            return
        if self._trusted_theory is not None and self._pinned_theory_sha256:
            self._require_pinned_theory()
            replay_theory = self._trusted_theory
        else:
            if trusted_theory is None:
                raise CheckError("legacy theory unpinned; trusted original theory required")
            replay_theory = deepcopy(trusted_theory)
            if _theory_digest(self.theory) != _theory_digest(replay_theory):
                raise CheckError("legacy theory differs from supplied trusted original")
        candidate = LemmaStore(replay_theory)
        if set(self.order) != set(self.lemmas) or len(self.order) != len(self.lemmas):
            raise CheckError("legacy lemma registry/order mismatch")
        if set(self.proofs) != set(self.lemmas):
            raise CheckError("legacy proof registry mismatch")
        for lid in self.order:
            candidate.verify(lid, self.lemmas[lid], self.proofs[lid])
        self._trusted_theory = deepcopy(candidate._trusted_theory)
        self._pinned_theory_sha256 = candidate._pinned_theory_sha256
        self._trusted_lemmas = deepcopy(candidate._trusted_lemmas)
        self.proof_digests = deepcopy(candidate.proof_digests)
        self._trusted_proof_digests = deepcopy(candidate._trusted_proof_digests)
        self._legacy_needs_replay = False

    def _require_intact_registry(self) -> None:
        """Detect mutations of any caller-visible proof admission evidence.

        This compares every public proof against a separately snapshotted
        admission digest. It does not establish a security boundary against
        malicious code able to mutate private Python objects in this process.
        """
        ids = set(self.order)
        if (len(ids) != len(self.order)
                or ids != set(self.lemmas)
                or ids != set(self.proofs)
                or ids != set(self.proof_digests)
                or ids != set(self._trusted_lemmas)
                or ids != set(self._trusted_proof_digests)):
            raise CheckError("verified lemma evidence registry mismatch (registry differs)")
        for lid in self.order:
            if self.lemmas[lid] != self._trusted_lemmas[lid]:
                raise CheckError("public lemma registry differs from verified snapshots")
            if (self.proof_digests[lid] != self._trusted_proof_digests[lid]
                    or _proof_digest(self.proofs[lid]) != self._trusted_proof_digests[lid]):
                raise CheckError("stored proof differs from admission-time trusted digest")

    def assert_theory_matches(self, theory: Theory) -> None:
        """Reject detached or mutated world axioms before any solver/checker use.

        A world may be counterfactual, but its proof store must have been built
        for that exact world. This remains local integrity, not external trust.
        """
        if getattr(self, "_legacy_needs_replay", False):
            raise CheckError("legacy lemma registry requires full proof replay")
        self._require_pinned_theory()
        if _theory_digest(theory) != self._pinned_theory_sha256:
            raise CheckError("solver theory differs from kernel-pinned theory")

    def verified_subset(self, ids) -> dict[str, Equation]:
        """Return only kernel-admitted lemma snapshots, never public mutable values.

        This is a same-process integrity check, not independent verification or
        protection from a hostile process. A tampered registry fails closed even
        when a requested ID is not the one that was modified.
        """
        if getattr(self, "_legacy_needs_replay", False):
            raise CheckError("legacy lemma registry requires full proof replay")
        self._require_pinned_theory()
        self._require_intact_registry()
        selected = {}
        for lid in ids:
            if lid not in self._trusted_lemmas:
                raise CheckError(f"unverified lemma requested: {lid!r}")
            selected[lid] = deepcopy(self._trusted_lemmas[lid])
        return selected

    def replay_all(self) -> bool:
        """Replay every retained proof against the pinned theory, in admission order.

        Required before exporting proof claims; local replay is NOT Lean or
        independent proof checking. Rejects mutated evidence, IDs and axioms.
        """
        if getattr(self, "_legacy_needs_replay", False):
            raise CheckError("legacy lemma registry requires full proof replay")
        self._require_pinned_theory()
        self._require_intact_registry()
        candidate = LemmaStore(self._trusted_theory)
        for lid in self.order:
            if self.lemmas[lid] != self._trusted_lemmas[lid]:
                raise CheckError("public lemma registry differs from verified snapshots")
            if _proof_digest(self.proofs[lid]) != self.proof_digests[lid]:
                raise CheckError("stored proof differs from verified digest")
            candidate.verify(lid, self._trusted_lemmas[lid], self.proofs[lid])
        if candidate._trusted_lemmas != self._trusted_lemmas:
            raise CheckError("stored lemmas differ from independent local replay")
        return True

    def verify(self, lid: str, eq: Equation, proof: dict) -> bool:
        if getattr(self, "_legacy_needs_replay", False):
            raise CheckError("legacy lemma registry requires full proof replay")
        self._require_pinned_theory()
        self._require_intact_registry()
        digest = _proof_digest(proof)
        if lid in self._trusted_lemmas:
            if (self._trusted_lemmas[lid] != eq
                    or self._trusted_proof_digests.get(lid) != digest):
                raise CheckError(f"conflicting reuse of verified lemma ID {lid!r}")
            return True
        deps = _lemma_refs(proof)
        if lid in deps:
            raise CheckError("a lemma may not cite itself")
        check_proof(self._trusted_theory, self._trusted_lemmas, eq, proof)
        # Store two independent snapshots. Caller-visible lemmas are for solving
        # convenience only, not for the kernel's trusted rule lookup.
        self._trusted_lemmas[lid] = deepcopy(eq)
        self.lemmas[lid] = deepcopy(eq)
        self.proofs[lid] = deepcopy(proof)
        self.proof_digests[lid] = digest
        self._trusted_proof_digests[lid] = digest
        self.order.append(lid)
        return True

    def __contains__(self, lid: str) -> bool:
        return lid in self.lemmas


def _lemma_refs(proof: dict) -> set:
    out = set()
    if proof.get("rule") == "rewrite":
        for st in list(proof.get("left", [])) + list(proof.get("right", [])):
            if st[1][0] == "lemma":
                out.add(st[1][1])
    elif proof.get("rule") == "induction":
        out |= _lemma_refs(proof["base"]) | _lemma_refs(proof["step"])
    return out
