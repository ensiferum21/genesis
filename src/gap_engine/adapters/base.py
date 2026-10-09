"""Reality adapter interface.

An adapter owns a domain (a synthetic world, inductive mathematics, Lean, a simulator)
and answers four questions for the engine:

* `evaluate(X, split, seed, crn)` - outcomes of many libraries at once (rows of X select
  pool members on top of the accepted base library);
* `fingerprint(i, seed)` - which probe tasks a pool member changes, cheaply;
* `outcomes(library, split, reps, seed)` - Gate J's split evaluator;
* costs of each of these in the one budget currency.

Splits: DEV (search and attribution), SELECT (gate checks), CONFIRM (gate unit test),
SEALED (judging only, behind kernel.sealed.SealedStore).
"""
from __future__ import annotations

from typing import Protocol

import numpy as np


class RealityAdapter(Protocol):
    name: str

    def pool_ids(self) -> list[str]: ...

    def n_tasks(self, split: str) -> int: ...

    def evaluate(self, X: np.ndarray, split: str, seed: int, crn: bool) -> np.ndarray:
        """X: (R, n_pool) bool. Returns (R, T) int outcomes on `split`."""
        ...

    def library_eval_cost(self, n_items: int) -> float: ...

    def fingerprint(self, i: int, seed: int) -> np.ndarray:
        """Bool vector over probe tasks that pool member i changes."""
        ...

    def fingerprint_cost(self) -> float: ...

    def outcomes(self, library: frozenset[str], split: str, reps: int, seed: int) -> np.ndarray: ...

    def eval_cost(self, library: frozenset[str], split: str) -> float: ...
