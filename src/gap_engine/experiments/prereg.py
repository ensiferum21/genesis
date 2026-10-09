"""Preregistration: written and hash-locked before any run; verified before analysis."""
from __future__ import annotations

import json
import os

from ..kernel.ledger import _canonical, sha256_hex


class PreregViolation(RuntimeError):
    pass


def write_prereg(path: str, plan: dict) -> str:
    if os.path.exists(path):
        raise PreregViolation(f"{path} exists; a preregistration is never overwritten")
    body = dict(plan)
    h = sha256_hex(_canonical(body))
    with open(path, "w") as fh:
        json.dump({"plan": body, "sha256": h}, fh, indent=1)
    with open(path + ".lock", "w") as fh:
        fh.write(h)
    return h


def load_verified(path: str) -> dict:
    with open(path) as fh:
        doc = json.load(fh)
    h = sha256_hex(_canonical(doc["plan"]))
    with open(path + ".lock") as fh:
        lock = fh.read().strip()
    if h != doc["sha256"] or h != lock:
        raise PreregViolation("preregistration changed after it was locked")
    return doc["plan"]
