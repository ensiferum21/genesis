"""U5: bottleneck accounting, randomised allocation experiments, learning-progress task
choice and an audited STOP.

The scheduler treats every intervention as an arm with a value-per-cost posterior
(Gaussian, discounted). A preregistered fraction of decisions is assigned uniformly at
random and logged with its propensity (INV-21); value estimates for the report are
doubly robust over those logs. STOP fires when, for `k` consecutive checks, the upper
confidence bound of the best arm's value per cost is below the shadow price of compute and
learning progress is flat; a preregistered fraction of STOPs is audited by continuing the
line on a capped budget (INV-22).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ..kernel import stats
from ..kernel.invariants import inv21_randomised_slice, inv22_stop_audit
from ..kernel.ledger import Ledger
from ..kernel.records import InterventionLog, StopRecord


@dataclass
class ArmStats:
    n: float = 0.0
    mean: float = 0.0
    m2: float = 0.0
    prior_mean: float = 0.1
    prior_n: float = 1.0
    discount: float = 0.9
    var_floor: float = 0.01          # on the scale of value per unit cost (tasks per unit)

    def update(self, x: float) -> None:
        self.n = self.discount * self.n + 1.0
        w = 1.0 / self.n
        d = x - self.mean
        self.mean += w * d
        self.m2 = self.discount * self.m2 + d * (x - self.mean)

    def posterior(self) -> tuple[float, float]:
        n = self.n + self.prior_n
        mu = (self.n * self.mean + self.prior_n * self.prior_mean) / n
        var = (self.m2 / max(self.n, 1.0) + self.var_floor) / n
        return mu, float(np.sqrt(var))


@dataclass
class Scheduler:
    arms: list[str]
    ledger: Ledger
    rng: np.random.Generator
    explore_frac: float = 0.10
    shadow_price: float = 0.05
    stop_k: int = 3
    lp_window: int = 4
    stats: dict = field(default_factory=dict)
    logs: list[InterventionLog] = field(default_factory=list)
    below: int = 0
    step: int = 0

    def __post_init__(self):
        for a in self.arms:
            self.stats.setdefault(a, ArmStats())

    def choose(self, eligible: list[str], cluster: str = "") -> tuple[str, bool, float]:
        """Return (arm, randomised?, propensity)."""
        self.step += 1
        eligible = [a for a in eligible if a in self.stats]
        if self.rng.random() < self.explore_frac:
            arm = eligible[int(self.rng.integers(len(eligible)))]
            prop = self.explore_frac / len(eligible)
            inv21_randomised_slice(prop, policy_override=False)
            return arm, True, prop
        draws = {a: self.rng.normal(*self.stats[a].posterior()) for a in eligible}
        arm = max(draws, key=draws.get)
        # propensity of the greedy branch is approximated by (1 - eps) for the logged arm
        return arm, False, (1 - self.explore_frac) + self.explore_frac / len(eligible)

    def record(self, arm: str, randomised: bool, propensity: float, cost: float, reward: float,
               cluster: str = "") -> None:
        vpc = reward / max(cost, 1e-6)
        self.stats[arm].update(vpc)
        log = InterventionLog(step=self.step, kind=arm, randomised=randomised, propensity=propensity,
                              cost=cost, reward=reward, cluster=cluster)
        self.logs.append(log)
        self.ledger.append("u5.intervention", log.model_dump())

    def ucb_best(self) -> float:
        return max(m + 2 * s for m, s in (self.stats[a].posterior() for a in self.arms))

    def learning_progress(self, history: list[float]) -> float:
        if len(history) < self.lp_window + 1:
            return float("inf")
        h = np.asarray(history[-(self.lp_window + 1):], float)
        x = np.arange(len(h))
        return float(abs(np.polyfit(x, h, 1)[0]))

    def should_stop(self, history: list[float], lp_floor: float = 0.05) -> bool:
        flat = self.learning_progress(history) <= lp_floor
        cheap = self.ucb_best() < self.shadow_price
        self.below = self.below + 1 if (flat and cheap) else 0
        return self.below >= self.stop_k

    def dr_report(self) -> dict[str, float]:
        rnd = [l for l in self.logs if l.randomised]
        model = {a: self.stats[a].posterior()[0] for a in self.arms}
        if not rnd:
            return {a: float("nan") for a in self.arms}
        return stats.doubly_robust_values([l.kind for l in rnd], [l.propensity for l in rnd],
                                          [l.reward / max(l.cost, 1e-6) for l in rnd], model, self.arms)


@dataclass
class StopAuditor:
    ledger: Ledger
    rng: np.random.Generator
    audit_frac: float = 0.10
    stops: list[StopRecord] = field(default_factory=list)
    n_audited: int = 0

    def stop(self, line: str, tried: list[str], estimates: dict[str, float], reversal: str) -> StopRecord:
        rec = StopRecord(line=line, reason="UCB below shadow price and flat learning progress", tried=tried,
                         final_estimates=estimates, reversal_observation=reversal)
        import math
        need = math.floor(self.audit_frac * (len(self.stops) + 1))
        if self.n_audited < need or self.rng.random() < self.audit_frac:
            rec.audited = True
            self.n_audited += 1
        self.stops.append(rec)
        self.ledger.append("u5.stop", rec.model_dump())
        inv22_stop_audit(len(self.stops), self.n_audited, self.audit_frac)
        return rec


def clusters_of(tasks, key: Callable) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, t in enumerate(tasks):
        out.setdefault(key(t), []).append(i)
    return out
