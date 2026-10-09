"""Legacy in-process DEV-only store, NOT an independent sealed evaluator.

Its data and near-duplicate oracle are research-accessible. Calling a Python
solver callback with protected data leaks that data. Production evaluations MUST
use an independently operated, isolated custodian, not this class. Legacy DEV
callback judging is blocked by default and requires explicit unsafe opt-in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .ledger import Ledger, sha256_hex


def normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def shingles(text: str, k: int = 3) -> set[str]:
    toks = re.findall(r"[a-z0-9_]+|[^\sa-z0-9_]", normalise(text))
    if len(toks) < k:
        return {" ".join(toks)}
    return {" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


class SealedAccessError(PermissionError):
    pass


@dataclass
class SealedStore:
    ledger: Ledger = field(default_factory=Ledger)
    near_dup_jaccard: float = 0.8
    _items: dict[str, dict[str, Any]] = field(default_factory=dict)  # name -> {key: item}
    _hashes: dict[str, str] = field(default_factory=dict)            # hash -> suite
    _shingles: list[tuple[str, set[str]]] = field(default_factory=list)

    def seal(self, suite: str, items: Iterable[tuple[str, Any]]) -> int:
        """Register (text_form, payload) pairs under a suite name. Returns count."""
        bucket = self._items.setdefault(suite, {})
        n = 0
        for text, payload in items:
            h = sha256_hex(normalise(text))
            bucket[h] = payload
            self._hashes[h] = suite
            self._shingles.append((h, shingles(text)))
            n += 1
        self.ledger.append("sealed.register", {"suite": suite, "count": n})
        return n

    def suites(self) -> list[str]:
        return list(self._items)

    def size(self, suite: str) -> int:
        return len(self._items.get(suite, {}))

    def is_sealed(self, text: str) -> bool:
        return sha256_hex(normalise(text)) in self._hashes

    def near_duplicate(self, text: str) -> bool:
        if self.is_sealed(text):
            return True
        s = shingles(text)
        return any(jaccard(s, t) >= self.near_dup_jaccard for _, t in self._shingles)

    def screen(self, texts: Iterable[str]) -> tuple[list[int], list[int]]:
        """Return (kept_indices, rejected_indices); rejection = sealed or near-duplicate."""
        kept, rejected = [], []
        for i, t in enumerate(texts):
            (rejected if self.near_duplicate(t) else kept).append(i)
        self.ledger.append("sealed.screen", {"kept": len(kept), "rejected": len(rejected)})
        return kept, rejected

    def judge(self, suite: str, solver: Callable[[Any], bool], *, actor: str,
              purpose: str, unsafe_dev_callback: bool = False) -> dict:
        """DEV ONLY. A Python callback can exfiltrate every protected payload.

        Explicit unsafe opt-in is allowed solely for old, non-promotable DEV
        experiments; neither ledger entries nor hashes establish isolation.
        """
        if not unsafe_dev_callback:
            self.ledger.append('sealed.judge.blocked',
                               {'suite': suite, 'actor': actor, 'reason': 'in-process callback unsafe'})
            raise SealedAccessError('in-process sealed judge disabled; use external custodian')
        if suite not in self._items:
            raise SealedAccessError(f"unknown sealed suite {suite!r}")
        outcomes = {h: bool(solver(payload)) for h, payload in self._items[suite].items()}
        self.ledger.append("sealed.dev_unsafe_judge", {"suite": suite, "actor": actor, "purpose": purpose,
                                            "n": len(outcomes), "solved": sum(outcomes.values())})
        return {"suite": suite, "n": len(outcomes), "solved": int(sum(outcomes.values())),
                "outcomes": outcomes, "independent_custody_proven": False,
                "evidence_class": "UNTRUSTED_DEV_ONLY_IN_PROCESS_CALLBACK",
                "eligible_for_scientific_promotion": False}
