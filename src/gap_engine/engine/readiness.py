"""DEV-only, budget-accounted admission readiness for an *experimental* V2 candidate.

This controller never evaluates SELECT, CONFIRM, or SEALED. It only decides when
there is enough DEV-side signal and remaining budget to invoke the *unchanged*
GateJ validation. A readiness estimate is a heuristic, NOT a p-value, proof of
power, or evidence of a confirmed improvement.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

from ..kernel.gates import _one_sided_t


def min_optimistic_wins(n: int, alpha: float) -> int | None:
    """Minimum no-loss binary wins passing the EXISTING t-test at alpha.

    The no-loss assumption is deliberately optimistic. A failed forecast can
    defer admission, but a passing forecast never substitutes for validation.
    """
    if n < 2:
        return None
    for k in range(1, n + 1):
        d = np.zeros(n, dtype=float)
        d[:k] = 1.0
        if d.mean() > 0 and _one_sided_t(d) < alpha:
            return k
    return None


@dataclass(frozen=True)
class ReadinessDecision:
    ready: bool
    reason: str
    units: int
    dev_gain: float
    projected_select_wins: int
    projected_confirm_wins: int
    min_select_wins: int | None
    min_confirm_wins: int | None
    estimated_gate_cost: float


class AdmissionReadinessBuffer:
    """Keep FDR-supported units across dropout rounds; preflight on DEV only.

    Evidence units remain atomic (INV-18). Repeated sightings are deduplicated,
    not treated as independent observations. Failed attempted batches are retired
    until a *new* proposal unit appears, avoiding repeated SELECT queries.
    """

    def __init__(self, world, library, gate, ledger, *, min_reserve: float = 2.0):
        self.world = world
        self.library = library
        self.gate = gate
        self.ledger = ledger
        self.min_reserve = min_reserve
        self.pending: dict[tuple[str, ...], tuple[float, str]] = {}
        self.attempted: set[tuple[str, ...]] = set()

    def offer(self, proposals: Sequence[tuple[Sequence[str], float, str]]) -> int:
        n = 0
        for members, p, kind in proposals:
            unit = tuple(sorted(set(m for m in members if m not in self.library.items)))
            if not unit or unit in self.attempted or not math.isfinite(float(p)) or not 0 <= float(p) <= 1:
                continue
            # FDR evidence has already been checked by caller. Do not pool
            # p-values across rounds, and do not split a synergy unit.
            if unit not in self.pending:
                self.pending[unit] = (float(p), kind)
                n += 1
        self.ledger.append("admission.buffer", {"new_units": n, "pending_units": len(self.pending)})
        return n

    def _ordered(self):
        return sorted(self.pending, key=lambda u: (self.pending[u][0], u))

    def minimum_gate_reserve(self) -> float:
        base = self.library.ids()
        # Lower bound for one-unit DEV build + full untouched SELECT + CONFIRM.
        e = self.world.eval_cost
        return 2 * e(base, "DEV") + 2 * e(base, "SELECT") + 2 * e(base, "CONFIRM") + self.min_reserve

    def _gate_cost(self, n_units: int) -> float:
        base = self.library.ids()
        e = self.world.eval_cost
        # Conservatively use the union of all buffered units as a possible
        # evaluation library; some adapters charge more for larger libraries.
        union = base | frozenset(m for u in self.pending for m in u)
        return ((n_units + 1) * max(e(base, "DEV"), e(union, "DEV"))
                + 2 * max(e(base, "SELECT"), e(union, "SELECT"))
                + 2 * max(e(base, "CONFIRM"), e(union, "CONFIRM"))) * self.gate.reps

    def preflight(self, seed: int) -> ReadinessDecision:
        units = self._ordered()
        if not units:
            return ReadinessDecision(False, "no_evidence", 0, 0., 0, 0, None, None, 0.)
        cost = self._gate_cost(len(units))
        # Account for the preflight's own DEV evaluations and future measurements.
        dev_probe_cost = (len(units) + 1) * self.world.eval_cost(self.library.ids(), "DEV") * self.gate.reps
        if cost + dev_probe_cost + self.min_reserve > self.gate.broker.remaining:
            return ReadinessDecision(False, "insufficient_reserved_budget", len(units), 0., 0, 0,
                                     None, None, cost)
        nsel, nconf = self.world.n_tasks("SELECT"), self.world.n_tasks("CONFIRM")
        ks = min_optimistic_wins(nsel, self.gate.alpha)
        kc = min_optimistic_wins(nconf, self.gate.alpha)
        if ks is None or kc is None:
            return ReadinessDecision(False, "insufficient_panel_size", len(units), 0., 0, 0, ks, kc, cost)

        # Charge EVERY preflight evaluation. DEV is research-visible; the
        # gate's untouched SELECT/CONFIRM are never accessed here.
        base = self.library.ids()
        y0 = self.gate._eval(base, "DEV", seed)
        current = y0
        chosen: set[str] = set()
        for unit in units:
            trial = frozenset(chosen | set(unit))
            ytrial = self.gate._eval(base | trial, "DEV", seed)
            if (ytrial - current).mean() > 0:
                chosen.update(unit)
                current = ytrial
        gain = float((current - y0).mean())
        ps = int(math.floor(max(0., gain) * nsel + 1e-9))
        pc = int(math.floor(max(0., gain) * nconf + 1e-9))
        ready = bool(chosen and ps >= ks and pc >= kc)
        return ReadinessDecision(ready, "dev_forecast_ready" if ready else "low_dev_forecast",
                                 len(units), gain, ps, pc, ks, kc, cost)

    def try_admit(self, seed: int) -> ReadinessDecision:
        d = self.preflight(seed)
        self.ledger.append("admission.readiness", {**d.__dict__, "seed": seed})
        if not d.ready:
            return d
        from .admission import admit_proposals
        units = self._ordered()
        props = [(u, self.pending[u][0], self.pending[u][1]) for u in units]
        before = len(self.world.accepted_extra)
        gate_logs_before = sum(e["kind"].startswith("gate.") for e in self.ledger.entries)
        # This invokes the EXISTING kernel-owned DEV-build/full-SELECT/CONFIRM
        # gate, with alpha unchanged. A readiness prediction cannot admit items.
        admit_proposals(self.world, self.library, self.gate, props, seed,
                        strategy="dev_build_full_select")
        new_admissions = len(self.world.accepted_extra) - before
        gate_logs_after = sum(e["kind"].startswith("gate.") for e in self.ledger.entries)
        if gate_logs_after == gate_logs_before:
            # Gate J may have exhausted budget mid-evaluation; this is NOT a
            # statistically valid rejection and must not be silently counted as one.
            self.ledger.append("admission.invalid_attempt", {
                "reason": "gate_did_not_record_decision", "units": len(units)})
        for u in units:
            self.attempted.add(u)
            self.pending.pop(u, None)
        self.ledger.append("admission.buffer_gate_attempt", {
            "units": len(units), "new_admissions": new_admissions,
            "passed": new_admissions > 0,
            "valid_gate_decision": gate_logs_after > gate_logs_before})
        return d
