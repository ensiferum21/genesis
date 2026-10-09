"""Certified preconditions by counterexample-guided synthesis (CEGIS) over counterfactual
worlds, judged on sealed worlds.

For a procedure P, the data are (features of a failed goal, did P solve it). We fit the
smallest decision list that explains the data, then an adversary searches *training*
counterfactual worlds for goals where the precondition holds but P fails (over-claim) or
fails to hold although P succeeds (over-restriction). Counterexamples are added and the
list is refitted. After `rounds` attack rounds the status is SURVIVED_N (N = rounds with no
over-claim found). Precision and recall are measured only on SEALED-family worlds
(INV-19); generated worlds never judge.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from ..adapters.induction.checker import LemmaStore
from ..adapters.induction.mutate import SEALED_MUTATIONS, TRAIN_MUTATIONS, random_mutant
from ..adapters.induction.tasks import PROPERTIES, validated_properties
from ..adapters.induction.theory import Theory
from ..kernel.budget import BudgetBroker
from ..kernel.invariants import inv19_only_sealed_judges
from ..kernel.records import ProcedureContract
from . import dsl
from .features import goal_features
from .procedures import run


@dataclass
class DecisionList:
    rules: list[tuple[tuple[str, bool], ...]] = field(default_factory=list)

    def __call__(self, f: dict) -> bool:
        return any(all(f.get(k) == v for k, v in r) for r in self.rules)

    def text(self) -> str:
        if not self.rules:
            return "never"
        return " OR ".join("(" + " AND ".join(k if v else f"not {k}" for k, v in r) + ")" for r in self.rules)

    def size(self) -> int:
        return sum(len(r) for r in self.rules)


def fit_decision_list(data: list[tuple[dict, bool]], max_rules: int = 3, max_lits: int = 2,
                      min_precision: float = 0.7, min_cover: int = 2, lit_penalty: float = 0.3) -> DecisionList:
    """Greedy sequential covering, preferring short rules (Occam)."""
    if not data:
        return DecisionList()
    keys = sorted(data[0][0])
    lits = [(k, v) for k in keys for v in (True, False)]
    remaining = list(data)
    rules = []
    for _ in range(max_rules):
        pos_left = [d for d in remaining if d[1]]
        if len(pos_left) < min_cover:
            break
        best, best_score = None, -1e9
        for n in range(1, max_lits + 1):
            for combo in itertools.combinations(lits, n):
                if len({k for k, _ in combo}) < n:
                    continue
                cov = [d for d in remaining if all(d[0].get(k) == v for k, v in combo)]
                p = sum(1 for d in cov if d[1])
                q = len(cov) - p
                if p < min_cover or p / max(1, len(cov)) < min_precision:
                    continue
                score = p - 2.0 * q - lit_penalty * n
                if score > best_score:
                    best, best_score = combo, score
        if best is None:
            break
        rules.append(tuple(best))
        remaining = [d for d in remaining if not all(d[0].get(k) == v for k, v in best)]
    return DecisionList(rules)


def _failed_goals(theory: Theory, tasks, fuel: int):
    feats = []
    for eq in tasks:
        f = goal_features(theory, eq, {}, fuel=fuel)
        if not f["base_solved"]:
            feats.append((eq, f))
    return feats


def _label(prog, theory: Theory, eq, seed: int, max_cost: float) -> bool:
    ctx = dsl.ResearchContext(theory, LemmaStore(theory), {}, BudgetBroker(total=1e9), seed=seed)
    return run(prog, ctx, eq, max_cost=max_cost).solved


def world_tasks(theory: Theory, n: int, rng) -> list:
    props, _ = validated_properties(theory, PROPERTIES, seed=int(rng.integers(1 << 30)))
    idx = rng.permutation(len(props))[:n]
    return [props[i] for i in idx]


@dataclass
class CegisReport:
    contract: ProcedureContract
    data_size: int
    counterexamples: int
    rounds_clean: int
    sealed_confusion: dict
    dl: DecisionList = field(default_factory=DecisionList)


def certify(name: str, prog: tuple[str, ...], base: Theory, seed: int = 0, n_init_worlds: int = 3,
            tasks_per_world: int = 40, rounds: int = 3, probes_per_round: int = 12, max_cost: float = 1.5,
            fuel: int = 150, sealed_worlds: int = 3, sealed_tasks: int = 40) -> CegisReport:
    rng = np.random.default_rng(seed)
    data: list[tuple[dict, bool]] = []
    worlds = [base] + [random_mutant(base, rng, TRAIN_MUTATIONS, "counterfactual") for _ in range(n_init_worlds - 1)]
    for th in worlds:
        for eq, f in _failed_goals(th, world_tasks(th, tasks_per_world, rng), fuel):
            data.append((f, _label(prog, th, eq, seed, max_cost)))
    dl = fit_decision_list(data)
    cex_total, clean = 0, 0
    for r in range(rounds):
        th = random_mutant(base, rng, TRAIN_MUTATIONS, "counterfactual", k=2)
        cands = _failed_goals(th, world_tasks(th, 60, rng), fuel)
        rng.shuffle(cands)
        found = 0
        probed = 0
        for eq, f in cands:
            if probed >= probes_per_round:
                break
            pred = dl(f)
            if not pred and rng.random() > 0.3:
                continue                       # mostly attack the claim; sometimes check restriction
            probed += 1
            y = _label(prog, th, eq, seed + r, max_cost)
            if pred != y:
                found += 1
                data.append((f, y))
        cex_total += found
        if found == 0:
            clean += 1
        else:
            dl = fit_decision_list(data)
    # sealed judging (INV-19): a different mutation family, never seen by the adversary
    tp = fp = fn = tn = 0
    for k in range(sealed_worlds):
        th = random_mutant(base, np.random.default_rng(10_000 + seed * 31 + k), SEALED_MUTATIONS, "sealed")
        inv19_only_sealed_judges(th.origin)
        for eq, f in _failed_goals(th, world_tasks(th, sealed_tasks, np.random.default_rng(20_000 + k)), fuel):
            y = _label(prog, th, eq, seed + 99, max_cost)
            p = dl(f)
            tp += p and y
            fp += p and not y
            fn += (not p) and y
            tn += (not p) and (not y)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    status = "SURVIVED_N" if clean > 0 else "PROPOSED"
    contract = ProcedureContract(name=name, signature="goal -> solved", precondition=dl.text(), status=status,
                                 adversarial_rounds=clean, sealed_precision=prec, sealed_recall=rec,
                                 steps=list(prog), stop_rules=[f"cost <= {max_cost}"],
                                 cost_per_call=max_cost, provenance=[f"cegis seed={seed}"])
    return CegisReport(contract, len(data), cex_total, clean, {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, dl)
