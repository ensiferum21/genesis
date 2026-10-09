"""The trainable proposer of this domain: a lemma-usefulness ranker.

Given a candidate lemma, predict whether adding it to the library will help the solver
(label from verified experience: cited by successful proofs, or positive dropout credit).
The engine proves and evaluates candidates in ranked order under a fixed budget, so a
better ranker means a better library per unit of compute. Models are versioned as
generations (u3.dream) and promoted only through G1.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression

from ..adapters.induction.conjecture import conj_features
from ..adapters.induction.theory import Equation

NUMERIC = ["size_l", "size_r", "depth_l", "n_vars", "n_syms", "vars_balanced", "rhs_is_var",
           "has_list", "n_defined"]


@dataclass
class Featuriser:
    vocab: list[str]

    def __call__(self, eq: Equation, extra: dict | None = None) -> np.ndarray:
        f = conj_features(eq)
        num = [float(f[k]) for k in NUMERIC]
        syms = set(f["symbols"])
        onehot = [1.0 if s in syms else 0.0 for s in self.vocab]
        ex = extra or {}
        return np.array(num + onehot + [float(ex.get("fp_touch", 0.0)), float(ex.get("size_gap", f["size_l"] - f["size_r"]))])


@dataclass
class LemmaRanker:
    featuriser: Featuriser
    model: LogisticRegression | None = None
    gen_id: str = "gen0-heuristic"
    trained_on: int = 0
    meta: dict = field(default_factory=dict)

    def score(self, eqs: list[Equation], extras: list[dict] | None = None) -> np.ndarray:
        extras = extras or [{}] * len(eqs)
        if self.model is None:
            # heuristic generation 0: prefer small, balanced, non-collapsing lemmas that touch probes
            out = []
            for eq, ex in zip(eqs, extras):
                f = conj_features(eq)
                out.append(-0.3 * (f["size_l"] + f["size_r"]) + 1.0 * f["vars_balanced"]
                           + 0.5 * float(ex.get("fp_touch", 0.0)) - 0.5 * f["rhs_is_var"])
            return np.array(out)
        X = np.stack([self.featuriser(e, x) for e, x in zip(eqs, extras)])
        return self.model.predict_proba(X)[:, 1]

    def fit(self, eqs: list[Equation], labels: list[int], extras: list[dict] | None = None,
            gen_id: str = "gen1", C: float = 1.0) -> "LemmaRanker":
        extras = extras or [{}] * len(eqs)
        X = np.stack([self.featuriser(e, x) for e, x in zip(eqs, extras)])
        y = np.asarray(labels, int)
        if len(set(y.tolist())) < 2:
            return LemmaRanker(self.featuriser, None, gen_id + "-degenerate", len(y))
        m = LogisticRegression(C=C, max_iter=2000, class_weight="balanced")
        m.fit(X, y)
        return LemmaRanker(self.featuriser, m, gen_id, len(y))
