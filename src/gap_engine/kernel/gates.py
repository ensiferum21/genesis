"""Gate J (joint admission) and the kernel-owned accepted library.

Gate J admits a bundle found by library dropout only if
  1. its dropout evidence survived false-discovery control,
  2. (pairs) an interaction test on SELECT confirms the joint structure:
     mean over tasks of y_ab - y_a - y_b + y_0 > 0 and y_ab > max(y_a, y_b),
  3. it beats the current library on CONFIRM as a unit (one-sided paired test).
Evidence for a bundle never admits a member alone (INV-18, enforced by `Library.admit`).
A "batch" bundle (several FDR-surviving bundles that individually lacked power) is tested
like a single: its joint gain on SELECT, then on CONFIRM, admitted only as a unit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

import numpy as np
from scipy import stats as sps

from .budget import BudgetBroker
from .invariants import InvariantViolation, inv18_no_member_alone
from .ledger import Ledger
from .records import Bundle, GateDecision


class SplitEvaluator(Protocol):
    def outcomes(self, library: frozenset[str], split: str, reps: int, seed: int) -> np.ndarray:
        """Return a (reps, T) 0/1 matrix of task outcomes on `split` ("DEV" | "SELECT" | "CONFIRM")."""
        ...

    def eval_cost(self, library: frozenset[str], split: str) -> float:
        ...


def _one_sided_t(d: np.ndarray) -> float:
    d = np.asarray(d, float)
    if len(d) < 2 or np.allclose(d, d[0]):
        return 0.0 if (len(d) and d.mean() > 0) else 1.0
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    return float(sps.t.sf(t, len(d) - 1))


@dataclass
class GateJ:
    evaluator: SplitEvaluator
    broker: BudgetBroker
    ledger: Ledger
    alpha: float = 0.05
    reps: int = 2

    def _eval(self, lib: frozenset[str], split: str, seed: int) -> np.ndarray:
        self.broker.charge("gate", self.evaluator.eval_cost(lib, split) * self.reps,
                           purpose=f"GateJ {split}")
        return self.evaluator.outcomes(lib, split, self.reps, seed).mean(0)

    def decide(self, bundle: Bundle, base: frozenset[str], seed: int = 0,
               gate_name: str = "J") -> GateDecision:
        members = tuple(sorted(bundle.members))
        self._gate_name = gate_name
        reasons: list[str] = []
        st: dict[str, float] = {}
        if not bundle.evidence.fdr_rejected:
            return self._log(GateDecision(gate="J", bundle=members, passed=False, stage="evidence",
                                          reasons=["dropout evidence did not survive FDR control"]))
        if bundle.evidence.credit is not None and bundle.evidence.credit[1] <= 0:
            reasons.append("credit interval includes zero (recorded, not blocking for pairs)")
        y0 = self._eval(base, "SELECT", seed)
        if len(members) >= 2 and bundle.kind == "pair":
            a, b = members[0], members[1]
            ya = self._eval(base | {a}, "SELECT", seed)
            yb = self._eval(base | {b}, "SELECT", seed)
            yab = self._eval(base | set(members), "SELECT", seed)
            inter = yab - ya - yb + y0
            gain_over_best = yab - np.maximum(ya, yb)
            p_inter = _one_sided_t(inter)
            st.update(select_interaction=float(inter.mean()), select_p=p_inter,
                      select_gain_over_best=float(gain_over_best.mean()))
            if not (inter.mean() > 0 and gain_over_best.mean() > 0 and p_inter < self.alpha):
                return self._log(GateDecision(gate="J", bundle=members, passed=False, stage="SELECT",
                                              reasons=reasons + ["joint structure not confirmed on SELECT"],
                                              stats=st))
        else:
            y1 = self._eval(base | set(members), "SELECT", seed)
            p_dir = _one_sided_t(y1 - y0)
            st.update(select_gain=float((y1 - y0).mean()), select_p=p_dir)
            if not ((y1 - y0).mean() > 0 and p_dir < self.alpha):
                return self._log(GateDecision(gate="J", bundle=members, passed=False, stage="SELECT",
                                              reasons=reasons + ["no direct gain on SELECT"], stats=st))
        c0 = self._eval(base, "CONFIRM", seed + 7919)
        c1 = self._eval(base | set(members), "CONFIRM", seed + 7919)
        p_conf = _one_sided_t(c1 - c0)
        st.update(confirm_gain=float((c1 - c0).mean()), confirm_p=p_conf)
        passed = bool((c1 - c0).mean() > 0 and p_conf < self.alpha)
        if not passed:
            reasons.append("no gain as a unit on CONFIRM")
        return self._log(GateDecision(gate="J", bundle=members, passed=passed,
                                      stage="CONFIRM" if passed else "CONFIRM-failed",
                                      reasons=reasons, stats=st))

    def decide_incremental(self, units: Sequence[Sequence[str]], base: frozenset[str], seed: int = 0,
                           gate_name: str = "J_incremental") -> GateDecision:
        """Build a batch on one half of SELECT, then validate it on the untouched half and
        on CONFIRM.  This is the round-2b follow-up to all-or-nothing batch admission.

        ``units`` are evidence-bearing proposal units (a single, pair, or larger bundle).
        A unit is never split while building the batch, preserving INV-18 for joint evidence.
        Units are considered in the caller's deterministic evidence-strength order.  A unit
        is kept only if it improves the SELECT-build half given the units already kept.
        The selected union is then tested from scratch on SELECT-validation and CONFIRM.
        Neither validation half participates in selection.
        """
        self._gate_name = gate_name
        norm_units: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()
        for raw in units:
            u = tuple(sorted(m for m in raw if m not in base))
            if not u or u in seen:
                continue
            seen.add(u)
            norm_units.append(u)
        if not norm_units:
            return self._log(GateDecision(gate=gate_name, bundle=(), passed=False,
                                          stage="evidence", reasons=["no new proposal units"]))

        y0 = self._eval(base, "SELECT", seed)
        n = len(y0)
        if n < 4:
            return self._log(GateDecision(gate=gate_name, bundle=(), passed=False,
                                          stage="SELECT-build",
                                          reasons=["SELECT too small for build/validation split"],
                                          stats={"select_tasks": float(n)}))
        rng = np.random.default_rng([seed, 0x4A17])
        perm = rng.permutation(n)
        cut = n // 2
        build_idx, valid_idx = perm[:cut], perm[cut:]

        selected: set[str] = set()
        y_cur = y0
        kept_units = 0
        # One evidence-ordered pass is intentionally linear in the number of proposals: the
        # previous all-or-nothing gate was cheap, so the repair must not consume the campaign
        # merely deciding admission. Pair/triple units preserve pure synergies.
        for u in norm_units:
            add = tuple(m for m in u if m not in selected)
            if not add:
                continue
            trial = frozenset(selected | set(add))
            y_trial = self._eval(base | trial, "SELECT", seed)
            marginal = float((y_trial[build_idx] - y_cur[build_idx]).mean())
            if marginal > 0:
                selected.update(add)
                y_cur = y_trial
                kept_units += 1

        members = tuple(sorted(selected))
        st = {"select_tasks": float(n), "build_tasks": float(len(build_idx)),
              "validation_tasks": float(len(valid_idx)), "proposal_units": float(len(norm_units)),
              "kept_units": float(kept_units), "selected_members": float(len(members)),
              "build_gain": float((y_cur[build_idx] - y0[build_idx]).mean())}
        if not members:
            return self._log(GateDecision(gate=gate_name, bundle=(), passed=False,
                                          stage="SELECT-build", reasons=["greedy build selected nothing"],
                                          stats=st))

        # y_cur is the full SELECT outcome vector for the selected union, but only the build
        # coordinates above were used to choose it.  The untouched coordinates now judge it.
        d_valid = y_cur[valid_idx] - y0[valid_idx]
        p_valid = _one_sided_t(d_valid)
        st.update(select_validation_gain=float(d_valid.mean()), select_validation_p=p_valid)
        if not (d_valid.mean() > 0 and p_valid < self.alpha):
            return self._log(GateDecision(gate=gate_name, bundle=members, passed=False,
                                          stage="SELECT-validation",
                                          reasons=["incremental batch did not validate on held-out SELECT"],
                                          stats=st))

        c0 = self._eval(base, "CONFIRM", seed + 7919)
        c1 = self._eval(base | set(members), "CONFIRM", seed + 7919)
        d_conf = c1 - c0
        p_conf = _one_sided_t(d_conf)
        st.update(confirm_gain=float(d_conf.mean()), confirm_p=p_conf)
        passed = bool(d_conf.mean() > 0 and p_conf < self.alpha)
        return self._log(GateDecision(gate=gate_name, bundle=members, passed=passed,
                                      stage="CONFIRM" if passed else "CONFIRM-failed",
                                      reasons=[] if passed else ["no gain as an incremental batch on CONFIRM"],
                                      stats=st))

    def decide_incremental_devbuild(self, units: Sequence[Sequence[str]], base: frozenset[str], seed: int = 0,
                                    gate_name: str = "J_incremental_devbuild") -> GateDecision:
        """Build a proposal batch using DEV only, then validate once on the *entire* SELECT
        split and finally on CONFIRM.

        This is the power-preserving repair motivated by the round-3 admission-starvation
        diagnosis. Proposal generation already uses DEV, so using DEV for composition does not
        spend any SELECT evidence on selection. SELECT is therefore a fully untouched validation
        panel. Evidence-bearing units are never split, preserving INV-18.

        This gate is intentionally *not* a weaker gate: alpha is unchanged and CONFIRM remains
        mandatory. It changes only where batch construction happens, increasing the number of
        untouched SELECT tasks available for validation.
        """
        self._gate_name = gate_name
        norm_units: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()
        for raw in units:
            u = tuple(sorted(m for m in raw if m not in base))
            if not u or u in seen:
                continue
            seen.add(u)
            norm_units.append(u)
        if not norm_units:
            return self._log(GateDecision(gate=gate_name, bundle=(), passed=False,
                                          stage="evidence", reasons=["no new proposal units"]))

        # DEV is selection data. Reusing it to compose DEV-generated proposal units is allowed;
        # no claim is made from DEV. The next two splits remain untouched until validation.
        y0_dev = self._eval(base, "DEV", seed)
        selected: set[str] = set()
        y_cur_dev = y0_dev
        kept_units = 0
        for u in norm_units:
            add = tuple(m for m in u if m not in selected)
            if not add:
                continue
            trial = frozenset(selected | set(add))
            y_trial = self._eval(base | trial, "DEV", seed)
            marginal = float((y_trial - y_cur_dev).mean())
            if marginal > 0:
                selected.update(add)
                y_cur_dev = y_trial
                kept_units += 1

        members = tuple(sorted(selected))
        st = {
            "dev_tasks": float(len(y0_dev)),
            "proposal_units": float(len(norm_units)),
            "kept_units": float(kept_units),
            "selected_members": float(len(members)),
            "dev_build_gain": float((y_cur_dev - y0_dev).mean()),
        }
        if not members:
            return self._log(GateDecision(gate=gate_name, bundle=(), passed=False,
                                          stage="DEV-build", reasons=["greedy DEV build selected nothing"],
                                          stats=st))

        # Entire SELECT is untouched by construction and is now used exactly once for validation.
        y0_sel = self._eval(base, "SELECT", seed + 313)
        y1_sel = self._eval(base | set(members), "SELECT", seed + 313)
        d_sel = y1_sel - y0_sel
        p_sel = _one_sided_t(d_sel)
        st.update(select_tasks=float(len(d_sel)), select_validation_gain=float(d_sel.mean()),
                  select_validation_p=p_sel)
        if not (d_sel.mean() > 0 and p_sel < self.alpha):
            return self._log(GateDecision(gate=gate_name, bundle=members, passed=False,
                                          stage="SELECT-validation",
                                          reasons=["DEV-built batch did not validate on full SELECT"], stats=st))

        c0 = self._eval(base, "CONFIRM", seed + 7919)
        c1 = self._eval(base | set(members), "CONFIRM", seed + 7919)
        d_conf = c1 - c0
        p_conf = _one_sided_t(d_conf)
        st.update(confirm_gain=float(d_conf.mean()), confirm_p=p_conf)
        passed = bool(d_conf.mean() > 0 and p_conf < self.alpha)
        return self._log(GateDecision(gate=gate_name, bundle=members, passed=passed,
                                      stage="CONFIRM" if passed else "CONFIRM-failed",
                                      reasons=[] if passed else ["no gain as a DEV-built batch on CONFIRM"],
                                      stats=st))

    def _log(self, d: GateDecision) -> GateDecision:
        d.gate = getattr(self, "_gate_name", "J")
        e = self.ledger.append(f"gate.{d.gate}", d.model_dump(exclude={"ledger_hash"}))
        d.ledger_hash = e["hash"]
        return d


@dataclass
class Library:
    """The accepted library. Only the kernel admits; every admission cites a gate decision."""

    ledger: Ledger
    items: dict[str, object] = field(default_factory=dict)
    history: list[tuple[str, ...]] = field(default_factory=list)

    def ids(self) -> frozenset[str]:
        return frozenset(self.items)

    def admit(self, ids: Sequence[str], payloads: dict[str, object], decision: GateDecision) -> None:
        """Admit `ids`, trusting only the ledger: the cited entry must be a gate record that
        passed, and its *ledgered* bundle (not the caller's object) decides what may enter.
        A ledgered decision can be used once."""
        entry = next((e for e in self.ledger.entries if e["hash"] == decision.ledger_hash), None) \
            if decision.ledger_hash else None
        if entry is None:
            raise InvariantViolation("admission cites a gate decision that is not in the ledger")
        if not entry["kind"].startswith("gate."):
            raise InvariantViolation(f"cited ledger entry is a {entry['kind']!r}, not a gate decision")
        rec = entry["payload"]
        if not rec.get("passed"):
            raise InvariantViolation("admission without a passing gate decision")
        if any(e["kind"] == "library.admit" and e["payload"].get("decision") == entry["hash"]
               for e in self.ledger.entries):
            raise InvariantViolation("gate decision already used for an admission")
        bundle = tuple(sorted(rec["bundle"]))
        inv18_no_member_alone(list(ids), list(bundle), "J" if len(bundle) > 1 else rec.get("gate", ""))
        if not set(ids) <= set(bundle):
            raise InvariantViolation("admitting items that the gate decision does not cover")
        for i in ids:
            self.items[i] = payloads.get(i)
        self.history.append(tuple(sorted(ids)))
        self.ledger.append("library.admit", {"ids": sorted(ids), "decision": decision.ledger_hash})

    def admit_base(self, ids: Sequence[str], payloads: dict[str, object], reason: str) -> None:
        """Admit trusted starting items (definitions, axioms). Ledgered with the reason."""
        for i in ids:
            self.items[i] = payloads.get(i)
        self.ledger.append("library.base", {"ids": sorted(ids), "reason": reason})


def first_order_gate(evaluator: SplitEvaluator, broker: BudgetBroker, ledger: Ledger,
                     cand: str, base: frozenset[str], alpha: float = 0.05, reps: int = 2,
                     seed: int = 0) -> GateDecision:
    """The current spec's direct-value gate for a single candidate (used by arm G)."""
    gj = GateJ(evaluator, broker, ledger, alpha, reps)
    from .records import BundleEvidence
    b = Bundle(members=(cand,), kind="single",
               evidence=BundleEvidence(votes=0, pvalue=0.0, fdr_rejected=True))
    return gj.decide(b, base, seed, gate_name="first_order")
