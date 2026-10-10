"""Research market and scheduling (spec §34).

    score(a) = E[verified_progress] + l_info*E[info_gain] + l_cap*E[future_capability]
             + l_opt*option_value - l_cost*expected_cost - l_risk*irreversibility
    Selection = Pareto prefilter + budgeted portfolio + reserved diversity quota.

Predictions are untrusted estimates. They are recalibrated per action kind from
realized DEV outcomes (a simple ratio estimator), and the calibration table is
part of the research policy, which must be frozen before any confirmation.
The stop-thinking rule (§34.1) ends work on an obligation when no legal action
is worth its price and no high-criticality verification is pending.
"""
from dataclasses import dataclass, field
from pydantic import Field
from .common import digest
from .models import StrictModel


class MarketPolicy(StrictModel):
    schema_version: str = 'genesis-market-policy-v1'
    lambda_info: float = Field(default=0.5, ge=0)
    lambda_cap: float = Field(default=0.3, ge=0)
    lambda_opt: float = Field(default=0.2, ge=0)
    lambda_cost: float = Field(default=1.0, ge=0)
    lambda_risk: float = Field(default=2.0, ge=0)
    diversity_slots: int = Field(default=1, ge=0, le=8)
    convergence_window: int = Field(default=3, ge=1, le=32)
    resource_price: float = Field(default=0.01, ge=0)   # value per CPU-second below which work stops


class Proposal(StrictModel):
    proposal_id: str
    kind: str                    # e.g. 'ghost_census', 'barrier_escape', 'branch_program'
    structural_class: str        # for diversity: representation / search family
    world: str
    expected_progress: float = Field(ge=0)
    info_gain: float = Field(ge=0)
    future_capability: float = Field(ge=0)
    option_value: float = Field(ge=0)
    expected_cost: float = Field(gt=0)      # CPU-seconds
    irreversibility: float = Field(default=0, ge=0, le=1)
    verification_obligation: bool = False  # True if it discharges a pending high-criticality check


@dataclass
class Calibration:
    """Per-kind ratio of realized to predicted progress and cost (DEV only)."""
    progress: dict = field(default_factory=dict)   # kind -> [predicted_sum, realized_sum]
    cost: dict = field(default_factory=dict)

    def adjust(self, p):
        pr = self.progress.get(p.kind); co = self.cost.get(p.kind)
        f_progress = (pr[1] + 1) / (pr[0] + 1) if pr else 1.0
        f_cost = (co[1] + 1) / (co[0] + 1) if co else 1.0
        return p.model_copy(update={'expected_progress': p.expected_progress * f_progress,
                                    'expected_cost': max(1e-6, p.expected_cost * f_cost)})

    def observe(self, p, realized_progress, realized_cost):
        a = self.progress.setdefault(p.kind, [0.0, 0.0]); a[0] += p.expected_progress; a[1] += realized_progress
        b = self.cost.setdefault(p.kind, [0.0, 0.0]); b[0] += p.expected_cost; b[1] += realized_cost

    def error(self):
        """Mean absolute log-ratio of realized vs predicted progress across kinds (0 = calibrated)."""
        import math
        terms = [abs(math.log((r + 1) / (q + 1))) for q, r in self.progress.values()]
        return sum(terms) / len(terms) if terms else None

    def snapshot(self):
        return {'progress': {k: list(v) for k, v in sorted(self.progress.items())},
                'cost': {k: list(v) for k, v in sorted(self.cost.items())}}


def score(p, policy):
    return (p.expected_progress + policy.lambda_info * p.info_gain + policy.lambda_cap * p.future_capability
            + policy.lambda_opt * p.option_value - policy.lambda_cost * p.expected_cost * policy.resource_price
            - policy.lambda_risk * p.irreversibility)


def _vector(p):
    return (p.expected_progress, p.info_gain, p.future_capability, p.option_value, -p.expected_cost, -p.irreversibility)


def pareto(proposals):
    def dominates(a, b):
        va, vb = _vector(a), _vector(b)
        return all(x >= y for x, y in zip(va, vb)) and any(x > y for x, y in zip(va, vb))
    return [p for p in proposals if not any(dominates(q, p) for q in proposals if q is not p)]


def allocate(proposals, budget, policy, *, calibration=None, recent_classes=()):
    """Choose a portfolio within `budget` CPU-seconds. Returns (selected, decision record)."""
    calibration = calibration or Calibration()
    adjusted = [calibration.adjust(p) for p in proposals]
    front = pareto(adjusted)
    ranked = sorted(front, key=lambda p: (-score(p, policy) / p.expected_cost, p.proposal_id))
    selected, spent = [], 0.0
    converged = (len(recent_classes) >= policy.convergence_window
                 and len(set(recent_classes[-policy.convergence_window:])) == 1)
    reserved = []
    if converged and policy.diversity_slots:
        dominant = recent_classes[-1]
        others = sorted((p for p in adjusted if p.structural_class != dominant),
                        key=lambda p: (-score(p, policy), p.proposal_id))
        reserved = others[:policy.diversity_slots]
    for p in reserved + ranked:
        if p in selected or spent + p.expected_cost > budget:
            continue
        if score(p, policy) <= 0 and not p.verification_obligation and p not in reserved:
            continue
        selected.append(p); spent += p.expected_cost
    record = {'policy': policy.model_dump(mode='json'), 'budget': budget, 'spent': round(spent, 6),
              'pareto_front': [p.proposal_id for p in front], 'reserved_for_diversity': [p.proposal_id for p in reserved],
              'selected': [p.proposal_id for p in selected], 'converged': converged,
              'calibration': calibration.snapshot()}
    record['decision_id'] = digest(record)
    return selected, record


def should_stop(proposals, policy, *, calibration=None, pending_critical=False):
    """§34.1: stop if every legal action's predicted marginal value is below its resource price
    and no high-criticality verification obligation is unresolved."""
    if pending_critical:
        return False, 'high-criticality verification obligation pending'
    calibration = calibration or Calibration()
    worth = [p for p in proposals if score(calibration.adjust(p), policy) > 0]
    if worth:
        return False, f'{len(worth)} action(s) still worth their price'
    return True, 'no legal action exceeds its resource price: return UNSETTLED / anytime bound'
