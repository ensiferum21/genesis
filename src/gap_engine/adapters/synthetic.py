"""Planted-synergy world (the prototype's benchmark, as a reality adapter).

Pool: direct contributors, synergy pairs (useless alone, valuable together), decoy pairs
(need a third ingredient that never exists) and duds. Each task requires a set of pool
members; including a member costs a small relative burden on every achievable task.
Ground truth is known, so recall and false discoveries can be scored exactly.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class WorldSpec:
    n_direct: int = 6
    n_syn: int = 6
    n_decoy: int = 6
    n_dud: int = 30
    tasks_per_group: int = 6
    n_easy_filler: int = 66
    n_hard_filler: int = 66
    p_hi: float = 0.85
    p_lo: float = 0.03
    p_easy: float = 0.60
    burden: float = 0.003
    fp_detect: float = 0.80
    fp_false: float = 0.03
    fp_cost: float = 0.25
    debt: float = 0.5


class SyntheticWorld:
    name = "synthetic"

    def __init__(self, spec: WorldSpec, seed: int, null: bool = False):
        rng = np.random.default_rng(seed)
        s = spec
        self.spec = s
        n = s.n_direct + 2 * s.n_syn + 2 * s.n_decoy + s.n_dud
        self.n = n
        idx = iter(rng.permutation(n))
        self.direct = [int(next(idx)) for _ in range(s.n_direct)]
        self.syn = [(int(next(idx)), int(next(idx))) for _ in range(s.n_syn)]
        self.decoy = [(int(next(idx)), int(next(idx))) for _ in range(s.n_decoy)]
        self.dud = [int(next(idx)) for _ in range(s.n_dud)]
        self.null = null
        tasks: list[tuple[str, tuple[int, ...]]] = []
        for c in self.direct:
            tasks += [("direct", (c,))] * s.tasks_per_group
        for a, b in self.syn:
            tasks += [("syn", (a, b) if not null else (-1,))] * s.tasks_per_group
        for a, b in self.decoy:
            tasks += [("decoy", (a, b, -1))] * s.tasks_per_group
        tasks += [("easy", ())] * s.n_easy_filler
        tasks += [("hard", (-1,))] * s.n_hard_filler
        self.kind = np.array([k for k, _ in tasks])
        self.req = [r for _, r in tasks]
        self.T = len(tasks)
        rel = np.zeros((n, self.T), bool)
        for t, r in enumerate(self.req):
            for c in r:
                if c >= 0:
                    rel[c, t] = True
        self.rel = rel
        self._fp_rng = np.random.default_rng(seed + 1_000_003)

    # ------------------------------------------------------------------ truth
    def true_pairs(self) -> set[tuple[int, int]]:
        return set() if self.null else {(min(a, b), max(a, b)) for a, b in self.syn}

    def true_direct(self) -> set[int]:
        return set(self.direct)

    def oracle_library(self) -> set[int]:
        lib = set(self.direct)
        if not self.null:
            for a, b in self.syn:
                lib |= {a, b}
        return lib

    # ------------------------------------------------------------------ adapter API
    def pool_ids(self) -> list[str]:
        return [f"c{i}" for i in range(self.n)]

    def n_tasks(self, split: str) -> int:
        return self.T

    def probs(self, X: np.ndarray) -> np.ndarray:
        s = self.spec
        X = np.asarray(X, bool)
        R = X.shape[0]
        burden = np.clip(1 - s.burden * X.sum(1), 0, 1)
        P = np.full((R, self.T), s.p_lo)
        for t, r in enumerate(self.req):
            if self.kind[t] == "easy":
                P[:, t] = s.p_easy * burden
                continue
            if any(c < 0 for c in r):
                continue
            ok = np.all(X[:, list(r)], axis=1)
            P[ok, t] = s.p_hi * burden[ok]
        return P

    def evaluate(self, X: np.ndarray, split: str, seed: int, crn: bool) -> np.ndarray:
        rng = np.random.default_rng([seed, {"DEV": 0, "SELECT": 1, "CONFIRM": 2, "SEALED": 3}.get(split, 9)])
        R = np.asarray(X).shape[0]
        U = np.broadcast_to(rng.random(self.T), (R, self.T)) if crn else rng.random((R, self.T))
        return (U < self.probs(X)).astype(np.int8)

    def library_eval_cost(self, n_items: int) -> float:
        return 1.0

    def fingerprint(self, i: int, seed: int) -> np.ndarray:
        s = self.spec
        rng = np.random.default_rng([seed, i, 17])
        det = rng.random(self.T) < s.fp_detect
        fal = rng.random(self.T) < s.fp_false
        return (self.rel[i] & det) | (~self.rel[i] & fal)

    def fingerprint_cost(self) -> float:
        return self.spec.fp_cost

    def _lib_to_X(self, library: frozenset[str]) -> np.ndarray:
        X = np.zeros((1, self.n), bool)
        for c in library:
            X[0, int(c[1:])] = True
        return X

    def outcomes(self, library: frozenset[str], split: str, reps: int, seed: int) -> np.ndarray:
        X = np.repeat(self._lib_to_X(library), reps, axis=0)
        return self.evaluate(X, split, seed, crn=False)

    def eval_cost(self, library: frozenset[str], split: str) -> float:
        return 1.0

    def heldout_value(self, lib: set[int]) -> float:
        X = np.zeros((1, self.n), bool)
        for c in lib:
            X[0, c] = True
        return float(self.probs(X).sum()) - self.spec.debt * len(lib)

    def value_fraction(self, lib: set[int]) -> float:
        v0, vo = self.heldout_value(set()), self.heldout_value(self.oracle_library())
        return (self.heldout_value(lib) - v0) / (vo - v0)
