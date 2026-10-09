"""Shared admission policy used by every arm and by the v2 campaign.

Proposals (singles, pairs, bundles) are gated strongest first given the current library;
members already admitted are dropped so a pair whose partner is in the library is tested
as the remaining single (compounding). Proposals that fail individually are then offered to the kernel's incremental batch gate:
it builds a subset on half of SELECT and validates it on the untouched half plus CONFIRM.
Evidence-bearing pair/triple proposal units are never split (INV-18).
"""
from __future__ import annotations

from ..kernel.budget import BudgetExceeded
from ..kernel.gates import GateJ, Library, first_order_gate
from ..kernel.records import Bundle, BundleEvidence


def _admit_bundle(w, lib: Library, gate: GateJ, members: tuple[str, ...], pvalue: float, kind: str, seed: int):
    """Gate a proposal given the current library. Members already admitted are dropped, so
    a pair whose partner is in the library is tested as the remaining single (compounding)."""
    members = tuple(m for m in members if m not in lib.items)
    if not members:
        return False
    kind = "single" if len(members) == 1 else kind
    b = Bundle(members=members, kind=kind, evidence=BundleEvidence(votes=1, pvalue=pvalue, fdr_rejected=True))
    if kind == "single":
        d = first_order_gate(w, gate.broker, gate.ledger, members[0], lib.ids(), alpha=gate.alpha, reps=1, seed=seed)
    else:
        d = gate.decide(b, lib.ids(), seed=seed)
    if d.passed:
        lib.admit(list(members), {m: None for m in members}, d)
        for m in members:
            w.accepted_extra.append(m)
            if m in w.pool:
                w.pool.remove(m)
    return d.passed


def admit_proposals(w, lib: Library, gate: GateJ, props, seed: int, max_individual: int = 0,
                    strategy: str = "select_split") -> None:
    """Shared admission policy for every arm.  Round 2b showed that individual gating spent
    budget without producing admissions, so the default sends all evidence-bearing proposal
    units to the kernel's incremental batch builder.  ``max_individual`` remains available for
    controlled ablations; any units not admitted there are still eligible for incremental build.
    Selection uses a SELECT build half and final validation uses untouched SELECT plus CONFIRM."""
    rest = []
    n_try = 0
    for members, p, kind in props:
        if n_try >= max_individual:
            rest.append(members)
            continue
        try:
            ok = _admit_bundle(w, lib, gate, tuple(members), p, kind, seed + n_try)
        except BudgetExceeded:
            return
        n_try += 1
        if not ok:
            rest.append(members)
    if strategy not in ("select_split", "dev_build_full_select"):
        raise ValueError(f"unknown admission strategy {strategy!r}")
    units = [tuple(m for m in ms if m not in lib.items) for ms in rest]
    units = [u for u in units if u]
    if units:
        try:
            if strategy == "dev_build_full_select":
                d = gate.decide_incremental_devbuild(units, lib.ids(), seed=seed + 999)
            else:
                d = gate.decide_incremental(units, lib.ids(), seed=seed + 999)
            if d.passed:
                members = tuple(d.bundle)
                lib.admit(list(members), {m: None for m in members}, d)
                for m in members:
                    w.accepted_extra.append(m)
                    if m in w.pool:
                        w.pool.remove(m)
        except BudgetExceeded:
            pass


