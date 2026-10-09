"""Search strategies compared in the head-to-head protocol.

G   current spec: test every candidate alone, admit those with direct value, no pair search
R   rival as written: G, then pairs ranked by shared failures (Jaccard of unsolved sets)
R+  strongest pair testing: no singles phase; fingerprint-ranked pairs scored on the tasks
    both fingerprints touch; an interaction test confirms each pair
U   U1 + U2: library dropout, switching to fingerprint-blocked dropout when plain dropout
    would give pairs too few co-inclusions

Every arm spends through its own BudgetBroker with the same total. Thresholds come from
calibration on separate worlds (experiments/calibrate.py), never from the evaluation world.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.records import Bundle
from ..u1.fingerprint import measure_fingerprints
from ..u2.design import DropoutConfig, run_dropout


@dataclass
class ArmResult:
    direct: set[int]
    pairs: set[tuple[int, int]]
    bundles: list[Bundle] = field(default_factory=list)
    spent: float = 0.0
    notes: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)      # evidence strength per single / pair


def _run(adapter, broker, X, split, seed, crn, purpose):
    unit = adapter.library_eval_cost(int(np.asarray(X).sum(1).max()) if len(X) else 0)
    broker.charge("evaluation", unit * len(X), purpose=purpose)
    return adapter.evaluate(X, split, seed, crn).astype(float)


def _singles(adapter, broker, seed, crn, single_rep):
    n = len(adapter.pool_ids())
    R = 3 + n * single_rep
    if broker.remaining < R * adapter.library_eval_cost(1):
        return None
    X = np.zeros((R, n), bool)
    for r in range(single_rep):
        for i in range(n):
            X[3 + r * n + i, i] = True
    Y = _run(adapter, broker, X, "DEV", seed, crn, "singles phase")
    base = Y[:3].mean(0)
    single = {i: np.mean([Y[3 + r * n + i] for r in range(single_rep)], axis=0) for i in range(n)}
    return base, single


def arm_gate(adapter, budget: float, seed: int, crn: bool, th: dict, broker: BudgetBroker | None = None) -> ArmResult:
    broker = broker or BudgetBroker.from_policy(budget, name="G")
    ph = _singles(adapter, broker, seed, crn, th["single_rep"])
    if ph is None:
        return ArmResult(set(), set(), spent=broker.used)
    base, single = ph
    gains = {i: float(y.sum() - base.sum()) for i, y in single.items()}
    direct = {i for i, g in gains.items() if g >= th["direct"]}
    return ArmResult(direct, set(), spent=broker.used, scores={i: gains[i] for i in direct})


def arm_rival(adapter, budget: float, seed: int, crn: bool, th: dict, broker: BudgetBroker | None = None) -> ArmResult:
    broker = broker or BudgetBroker.from_policy(budget, name="R")
    n = len(adapter.pool_ids())
    ph = _singles(adapter, broker, seed, crn, th["single_rep"])
    if ph is None:
        return ArmResult(set(), set(), spent=broker.used)
    base, single = ph
    gains = {i: float(y.sum() - base.sum()) for i, y in single.items()}
    direct = {i for i, g in gains.items() if g >= th["direct"]}
    scores: dict = {i: gains[i] for i in direct}
    pool = [i for i in range(n) if i not in direct]
    uns = {i: single[i] < 0.5 for i in pool}

    def jac(p):
        a, b = uns[p[0]], uns[p[1]]
        return (a & b).sum() / max(1, (a | b).sum())

    cand = sorted(itertools.combinations(pool, 2), key=lambda p: -jac(p))
    k = int(broker.remaining // (th["rep"] * adapter.library_eval_cost(2)))
    pairs = set()
    if k > 0:
        cand = cand[:k]
        X = np.zeros((len(cand) * th["rep"], n), bool)
        for c, (i, j) in enumerate(cand):
            X[c * th["rep"]:(c + 1) * th["rep"], [i, j]] = True
        Y = _run(adapter, broker, X, "DEV", seed + 1, crn, "rival pair tests")
        for c, (i, j) in enumerate(cand):
            yij = Y[c * th["rep"]:(c + 1) * th["rep"]].mean(0)
            st = float(yij.sum() - single[i].sum() - single[j].sum() + base.sum())
            if st >= th["pair"]:
                pairs.add((min(i, j), max(i, j)))
                scores[(min(i, j), max(i, j))] = st
    return ArmResult(direct, pairs, spent=broker.used, scores=scores)


def arm_pairs_strong(adapter, budget: float, seed: int, crn: bool, th: dict,
                     broker: BudgetBroker | None = None) -> ArmResult:
    broker = broker or BudgetBroker.from_policy(budget, name="R+")
    n = len(adapter.pool_ids())
    fps = measure_fingerprints(adapter, broker, seed)
    fp = fps.F
    props = fps.pair_proposals(min_ov=th["min_ov"], cap=None)
    unit = adapter.library_eval_cost(2)
    try:
        base = _run(adapter, broker, np.zeros((3, n), bool), "DEV", seed, crn, "R+ base").mean(0)
    except BudgetExceeded:
        return ArmResult(set(), set(), spent=broker.used)
    direct, pairs = set(), set()
    scores: dict = {}

    def one(members, rep, s):
        X = np.zeros((rep, n), bool)
        X[:, list(members)] = True
        return _run(adapter, broker, X, "DEV", s, crn, "R+ test").mean(0)

    for idx, (i, j, _) in enumerate(props):
        if broker.remaining < unit * (th["rep"] + 2):
            break
        loc = fp[i] & fp[j]
        yij = one((i, j), th["rep"], seed)
        if (yij[loc] - base[loc]).sum() < th["pair"]:
            continue
        yi = one((i,), 1, seed)
        yj = one((j,), 1, seed)
        inter = (yij[loc] - yi[loc] - yj[loc] + base[loc]).sum()
        if inter >= th["inter"]:
            pairs.add((min(i, j), max(i, j)))
            scores[(min(i, j), max(i, j))] = float(inter)
        else:
            for c, yc in ((i, yi), (j, yj)):
                g = float((yc[fp[c]] - base[fp[c]]).sum())
                if g >= th["pair"]:
                    direct.add(c)
                    scores[c] = max(scores.get(c, 0.0), g)
    return ArmResult(direct, pairs, spent=broker.used, notes={"proposals": len(props)}, scores=scores)


def arm_dropout(adapter, budget: float, seed: int, crn: bool, th: dict,
                broker: BudgetBroker | None = None, eligible: np.ndarray | None = None) -> ArmResult:
    """U: plain dropout, or fingerprint-blocked dropout when co-inclusions would be too few."""
    broker = broker or BudgetBroker.from_policy(budget, name="U")
    n = len(adapter.pool_ids())
    cfg = DropoutConfig(tau=th["tau"], delta=th["delta"], min_tasks=th["min_tasks"],
                        mode=th.get("mode", "auto"), min_joint=th.get("min_joint", 8.0),
                        fdr_q=th.get("fdr_q", 0.10))
    unit = adapter.library_eval_cost(int(cfg.target_size))
    n_el = n if eligible is None else int(np.asarray(eligible).sum())
    p_plain = min(0.5, cfg.target_size / max(1, n_el))
    R_est = broker.remaining / unit
    proposals = None
    need_blocks = cfg.mode == "blocked" or (cfg.mode == "auto" and p_plain ** 2 * R_est < cfg.min_joint)
    if need_blocks:
        members = None if eligible is None else [i for i in range(n) if eligible[i]]
        fps = measure_fingerprints(adapter, broker, seed, members=members)
        proposals = fps.pair_proposals(min_ov=th.get("min_ov"), cap=80)
    rd = run_dropout(adapter, broker, seed, cfg, proposals=proposals, crn=crn, eligible=eligible)
    if rd is None:
        return ArmResult(set(), set(), spent=broker.used)
    ids = adapter.pool_ids()
    idx = {c: k for k, c in enumerate(ids)}
    direct = {idx[b.members[0]] for b in rd.bundles if b.kind == "single" and b.evidence.fdr_rejected}
    pairs = {tuple(sorted(idx[m] for m in b.members)) for b in rd.bundles
             if b.kind == "pair" and b.evidence.fdr_rejected}
    return ArmResult(direct, pairs, rd.bundles, spent=broker.used,
                     notes={"mode": rd.design.mode, "runs": rd.design.runs})


ARMS = {
    "G": (arm_gate, "pair"),
    "R": (arm_rival, "pair"),
    "R+": (arm_pairs_strong, "strong"),
    "U": (arm_dropout, "drop"),
}

GRIDS = {
    "pair": [dict(direct=d, pair=p, rep=r, single_rep=s)
             for d in (3, 5, 7, 9) for p in (3, 4, 6, 8) for r in (1, 2) for s in (1, 2)],
    "strong": [dict(min_ov=m, pair=p, inter=i, rep=r)
               for m in (2, 3) for p in (1.5, 2.0, 2.5, 3.0) for i in (1.0, 1.5, 2.0, 2.5) for r in (1, 2)],
    "drop": [dict(tau=t, delta=d, min_tasks=k, min_ov=m)
             for t in (10, 15, 20, 30) for d in (2, 5) for k in (2, 3) for m in (2, 3)],
}
