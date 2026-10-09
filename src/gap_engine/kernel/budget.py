"""One-currency budget broker.

All spend (evaluations, fingerprint probes, training, exploration, audits) is charged
here in a single currency. Category caps are shares of the total and are enforced by the
broker, never by policy code. A refused charge raises `BudgetExceeded` and is ledgered.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .ledger import Ledger

_POLICY = os.path.join(os.path.dirname(__file__), "..", "..", "..", "constitution", "policy.json")


def load_policy(path: str | None = None) -> dict:
    p = path or os.path.normpath(_POLICY)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetBroker:
    total: float
    ledger: Ledger = field(default_factory=Ledger)
    caps_share: dict[str, float] = field(default_factory=dict)
    spent: dict[str, float] = field(default_factory=dict)
    name: str = "campaign"

    @classmethod
    def from_policy(cls, total: float, ledger: Ledger | None = None, name: str = "campaign",
                    policy: dict | None = None) -> "BudgetBroker":
        pol = policy or load_policy()
        return cls(total=float(total), ledger=ledger if ledger is not None else Ledger(),
                   caps_share=dict(pol["budget"]["category_caps_share"]), name=name)

    @property
    def used(self) -> float:
        return float(sum(self.spent.values()))

    @property
    def remaining(self) -> float:
        return self.total - self.used

    def cap(self, category: str) -> float:
        share = self.caps_share.get(category)
        return self.total if share is None else share * self.total

    def can_afford(self, category: str, amount: float) -> bool:
        if amount < 0:
            return False
        if self.used + amount > self.total + 1e-9:
            return False
        return self.spent.get(category, 0.0) + amount <= self.cap(category) + 1e-9

    def charge(self, category: str, amount: float, purpose: str = "") -> float:
        amount = float(amount)
        if amount < 0:
            raise ValueError("negative charge")
        if not self.can_afford(category, amount):
            self.ledger.append("budget.refused", {
                "broker": self.name, "category": category, "amount": amount, "purpose": purpose,
                "used": self.used, "total": self.total,
                "category_spent": self.spent.get(category, 0.0), "category_cap": self.cap(category)})
            raise BudgetExceeded(f"{self.name}: cannot charge {amount:.3f} to {category} "
                                 f"(used {self.used:.3f}/{self.total:.3f}, "
                                 f"category {self.spent.get(category, 0.0):.3f}/{self.cap(category):.3f})")
        self.spent[category] = self.spent.get(category, 0.0) + amount
        self.ledger.append("budget.charge", {"broker": self.name, "category": category,
                                             "amount": amount, "purpose": purpose})
        return amount

    def affordable_units(self, category: str, unit_cost: float) -> int:
        if unit_cost <= 0:
            raise ValueError("unit cost must be positive")
        by_total = (self.total - self.used) / unit_cost
        by_cap = (self.cap(category) - self.spent.get(category, 0.0)) / unit_cost
        return max(0, int(min(by_total, by_cap) + 1e-9))

    def report(self) -> dict:
        return {"broker": self.name, "total": self.total, "used": self.used,
                "by_category": dict(self.spent)}
