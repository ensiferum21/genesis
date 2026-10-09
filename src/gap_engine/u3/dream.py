"""U3 dream cycles: harvested, kernel-admitted experience trains the next proposer
generation, which is promoted only through gate G1.

G1 (as specified): the child must beat its parent at matched total compute - the child's
training cost is converted into extra selection budget for the parent - with a sealed
(pre-registered, ledgered) forecast, a retention check on DEV (>= 98% of the parent's
solves) and rollback on failure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats as sps

from ..adapters.induction.adapter import InductionWorld
from ..kernel.budget import BudgetBroker, BudgetExceeded, load_policy
from ..kernel.ledger import Ledger
from ..kernel.records import GenerationRecord, HarvestRecord
from ..u2.design import DropoutConfig, run_dropout
from .admission import admit_dataset
from .harvest import harvest, usage_labels
from .proposer_model import Featuriser, LemmaRanker


def default_ranker(world: InductionWorld) -> LemmaRanker:
    vocab = sorted(set(world.theory.funs) | {"S", "Z", "Cons", "Nil"})
    return LemmaRanker(Featuriser(vocab))


def select_top(world: InductionWorld, ranker: LemmaRanker, k: int, fp_touch: dict | None = None) -> list[str]:
    cands = list(world.pool)
    if not cands or k <= 0:
        return []
    eqs = [world.store.verified_subset(cands)[c] for c in cands]
    extras = [{"fp_touch": (fp_touch or {}).get(c, 0.0)} for c in cands]
    s = ranker.score(eqs, extras)
    order = np.argsort(-s, kind="stable")
    return [cands[i] for i in order[:k]]


def _solves(world, extra, split, seeds):
    return np.concatenate([world.run_library(extra, split, s) for s in seeds]).astype(float)


@dataclass
class G1Result:
    promoted: bool
    child_select: float
    parent_select: float
    p_value: float
    retention: float
    forecast: float
    reasons: list


def g1_test(world: InductionWorld, parent: LemmaRanker, child: LemmaRanker, k: int, train_cost: float,
            unit_cost: float, ledger: Ledger, forecast: float, seeds=(11, 12, 13), alpha: float = 0.10,
            retention_floor: float | None = None, fp_touch: dict | None = None) -> G1Result:
    retention_floor = retention_floor or load_policy()["u3"]["retention_floor"]
    extra = int(math.ceil(train_cost / unit_cost))
    ledger.append("g1.forecast", {"child": child.gen_id, "parent": parent.gen_id, "forecast_gain": forecast,
                                  "k": k, "parent_extra": extra})
    lib_child = select_top(world, child, k, fp_touch)
    lib_parent = select_top(world, parent, k + extra, fp_touch)
    yc = _solves(world, lib_child, "SELECT", seeds)
    yp = _solves(world, lib_parent, "SELECT", seeds)
    d = yc - yp
    if np.allclose(d, 0):
        p = 1.0
    else:
        nz = d[d != 0]
        p = float(sps.binomtest(int((nz > 0).sum()), len(nz), 0.5, alternative="greater").pvalue)
    dc = _solves(world, lib_child, "DEV", seeds).sum()
    dp = _solves(world, lib_parent, "DEV", seeds).sum()
    retention = float(dc / dp) if dp > 0 else 1.0
    reasons = []
    if not (yc.sum() > yp.sum()):
        reasons.append("child does not beat parent at matched compute on SELECT")
    elif p >= alpha:
        reasons.append(f"gain not significant (sign test p={p:.3f})")
    if retention < retention_floor:
        reasons.append(f"retention {retention:.3f} below {retention_floor}")
    promoted = not reasons
    ledger.append("g1.decision", {"child": child.gen_id, "promoted": promoted, "child_select": float(yc.mean()),
                                  "parent_select": float(yp.mean()), "p": p, "retention": retention,
                                  "reasons": reasons})
    return G1Result(promoted, float(yc.mean()), float(yp.mean()), p, retention, forecast, reasons)


def label_pool(world: InductionWorld, broker: BudgetBroker, seed: int, runs: int = 120) -> dict[str, int]:
    """Verified usefulness labels: cited by a successful DEV proof in some dropout library,
    or part of a bundle whose dropout evidence survived FDR control."""
    cfg = DropoutConfig(tau=10, delta=2, min_tasks=1, fdr_q=0.10, mode="plain")
    rd = run_dropout(world, broker, seed, cfg, max_runs=runs, category="labelling")
    labels = {c: 0 for c in world.pool}
    if rd is not None:
        for b in rd.bundles:
            if b.evidence.fdr_rejected:
                for m in b.members:
                    labels[m] = 1
        rng = np.random.default_rng(seed)
        for r in rng.choice(rd.X.shape[0], size=min(12, rd.X.shape[0]), replace=False):
            extra = [world.pool[i] for i in np.nonzero(rd.X[r])[0]]
            for lid, cnt in usage_labels(world, extra, "DEV", seed + int(r)).items():
                if lid in labels and cnt > 0:
                    labels[lid] = 1
    return labels


def dream_cycle(world: InductionWorld, parent: LemmaRanker, broker: BudgetBroker, ledger: Ledger,
                seed: int, k: int = 12, label_runs: int = 120, gen_id: str = "gen1",
                train_cost_per_item: float = 0.01, unit_cost: float = 1.0,
                fp_touch: dict | None = None) -> tuple[LemmaRanker, GenerationRecord, dict]:
    hv = harvest(world, broker, seed=seed)
    labels = label_pool(world, broker, seed, runs=label_runs)
    items = [HarvestRecord(text=world.statement(c), source_task="pool", kind="byproduct_lemma",
                           kernel_verified=c in world.store.verified_subset(world.store.order), label=float(labels[c])) for c in labels]
    verified_texts = {e.text() for e in world.store.verified_subset(world.store.order).values()}
    man = admit_dataset(f"{gen_id}-data", items, world.sealed, ledger,
                        verifier=lambda t: t in verified_texts)
    texts = {it.text for it in man.items}
    use = [c for c in labels if world.statement(c) in texts]
    train_cost = train_cost_per_item * len(use)
    try:
        broker.charge("dream_training", train_cost, purpose=f"train {gen_id}")
    except BudgetExceeded:
        rec = GenerationRecord(gen_id=gen_id, parent=parent.gen_id, kind="lemma-ranker", train_items=0,
                               train_cost=0.0, promoted=False, reasons=["training budget exhausted"])
        return parent, rec, {"harvest": hv}
    eqs = [world.store.verified_subset(use)[c] for c in use]
    ys = [labels[c] for c in use]
    extras = [{"fp_touch": (fp_touch or {}).get(c, 0.0)} for c in use]
    child = parent.fit(eqs, ys, extras, gen_id=gen_id)
    # sealed forecast: in-sample rank correlation is the child's own (optimistic) forecast
    forecast = float(np.mean(ys)) if ys else 0.0
    res = g1_test(world, parent, child, k, train_cost, unit_cost, ledger, forecast, fp_touch=fp_touch)
    rec = GenerationRecord(gen_id=gen_id, parent=parent.gen_id, kind="lemma-ranker", train_items=len(use),
                           train_cost=train_cost, promoted=res.promoted, reasons=res.reasons,
                           metrics={"child_select": res.child_select, "parent_select": res.parent_select,
                                    "p": res.p_value, "retention": res.retention,
                                    "positives": float(sum(ys))})
    ledger.append("generation", rec.model_dump())
    return (child if res.promoted else parent), rec, {"harvest": hv, "labels": labels, "g1": res}
