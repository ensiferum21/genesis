"""Append-only, hash-chained ledger.

Every kernel decision (charge, admission, refusal, sealed access, STOP) is written here.
Each entry carries the SHA-256 of the previous entry, so any edit or deletion breaks
`verify()`. The ledger is the audit trail the review reads; research code can append
only through kernel APIs that pass it in.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

GENESIS = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Ledger:
    """In-memory hash chain, optionally mirrored to a JSONL file."""

    path: str | None = None
    entries: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.path and os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as fh:
                self.entries = [json.loads(line) for line in fh if line.strip()]
            self.verify()

    @property
    def head(self) -> str:
        return self.entries[-1]["hash"] if self.entries else GENESIS

    def append(self, kind: str, payload: dict, actor: str = "kernel") -> dict:
        body = {
            "seq": len(self.entries),
            "ts": time.time(),
            "kind": kind,
            "actor": actor,
            "payload": payload,
            "prev": self.head,
        }
        body["hash"] = sha256_hex(_canonical({k: v for k, v in body.items() if k != "hash"}))
        self.entries.append(body)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(_canonical(body) + "\n")
        return body

    def verify(self) -> bool:
        prev = GENESIS
        for i, e in enumerate(self.entries):
            if e["seq"] != i or e["prev"] != prev:
                raise LedgerCorrupt(f"chain broken at seq {i}")
            expect = sha256_hex(_canonical({k: v for k, v in e.items() if k != "hash"}))
            if expect != e["hash"]:
                raise LedgerCorrupt(f"hash mismatch at seq {i}")
            prev = e["hash"]
        return True

    def of_kind(self, kind: str) -> Iterator[dict]:
        return (e for e in self.entries if e["kind"] == kind)

    def __len__(self) -> int:
        return len(self.entries)

    def __bool__(self) -> bool:
        # an empty ledger is still a ledger: never let `ledger or Ledger()` swap it out
        return True


class LedgerCorrupt(RuntimeError):
    pass
