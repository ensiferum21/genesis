"""Executable forms of the v2 invariants (INV-18 .. INV-23).

Each function raises `InvariantViolation` and is called by the kernel component that
owns the decision. Tests in tests/test_invariants.py try to break each one.
"""
from __future__ import annotations

from typing import Iterable, Sequence


class InvariantViolation(RuntimeError):
    pass


def inv18_no_member_alone(admit_ids: Sequence[str], decision_bundle: Sequence[str],
                          decision_gate: str) -> None:
    """INV-18: joint evidence never admits a member alone (any multi-member bundle)."""
    if len(decision_bundle) > 1:
        if tuple(sorted(admit_ids)) != tuple(sorted(decision_bundle)):
            raise InvariantViolation(
                f"INV-18: bundle {tuple(decision_bundle)} passed Gate J; admitting "
                f"{tuple(admit_ids)} alone is forbidden")


def inv19_only_sealed_judges(world_origin: str) -> None:
    """INV-19: generated or counterfactual worlds may train and attack, never judge."""
    if world_origin != "sealed":
        raise InvariantViolation(f"INV-19: a {world_origin!r} world cannot be used to judge")


def inv20_training_admission(kernel_verified: Iterable[bool], sealed_hits: int) -> None:
    """INV-20: only kernel-verified items enter weights; sealed items excluded."""
    if not all(kernel_verified):
        raise InvariantViolation("INV-20: unverified item in a training dataset")
    if sealed_hits:
        raise InvariantViolation(f"INV-20: {sealed_hits} sealed or near-duplicate items present")


def inv21_randomised_slice(logged_propensity: float, policy_override: bool) -> None:
    """INV-21: randomised allocation decisions carry propensities and cannot be overridden."""
    if not (0.0 < logged_propensity <= 1.0):
        raise InvariantViolation("INV-21: randomised decision logged without a valid propensity")
    if policy_override:
        raise InvariantViolation("INV-21: policy attempted to override a randomised decision")


def inv22_stop_audit(n_stopped: int, n_audited: int, audit_frac: float) -> None:
    """INV-22: a preregistered fraction of stopped lines continues as an audit."""
    import math
    need = math.floor(audit_frac * n_stopped)
    if n_audited < need:
        raise InvariantViolation(f"INV-22: {n_audited} audits for {n_stopped} stops; need {need}")


def inv23_matched_comparison(calibrated: bool, null_world_reported: bool) -> None:
    """INV-23: strategy comparisons at a matched false-discovery limit, with null worlds."""
    if not calibrated:
        raise InvariantViolation("INV-23: comparison without calibration to a matched FDR limit")
    if not null_world_reported:
        raise InvariantViolation("INV-23: comparison without null-world false discoveries")
