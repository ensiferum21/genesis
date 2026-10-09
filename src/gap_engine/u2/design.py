"""U2 library dropout: designs, attribution and bundles.

Plain design: each run includes each pool member independently with probability p.
Blocked design: fingerprint-proposed pairs are also switched on together with probability
q, so a proposed pair co-occurs in about q of runs instead of p^2. The engine switches to
blocks when plain dropout would give a pair fewer than `min_joint` expected co-inclusions
and pair proposals exist (the prototype's scaling failure: p^2 R ~ 1 at 300 candidates).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..kernel import stats
from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.records import Bundle, BundleEvidence, DropoutDesignRecord


@dataclass
class DropoutConfig:
    tau: float = 15.0
    delta: float = 2.0
    min_tasks: int = 3
    target_size: float = 25.0
    block_target: float = 12.0        # expected members switched on by blocks per run
    q_max: float = 0.3
    min_joint: float = 8.0            # switch to blocks below this many expected co-inclusions
    mode: str = "auto"                # "plain" | "blocked" | "auto"
    fdr_q: float = 0.10


def plan_design(n: int, R: int, rng: np.random.Generator, cfg: DropoutConfig,
                proposals: list[tuple[int, int, int]] | None = None,
                eligible: np.ndarray | None = None) -> tuple[np.ndarray, DropoutDesignRecord, np.ndarray]:
    """Return (X, record, cand_pair). X: (R, n) inclusion matrix."""
    eligible = np.ones(n, bool) if eligible is None else np.asarray(eligible, bool)
    n_el = max(1, int(eligible.sum()))
    p_plain = min(0.5, cfg.target_size / n_el)
    mode = cfg.mode
    if mode == "auto":
        mode = "blocked" if (proposals and p_plain ** 2 * R < cfg.min_joint) else "plain"
    cand_pair = np.zeros((n, n), bool)
    blocks: list[tuple[int, int]] = []
    if mode == "blocked" and proposals:
        blocks = [(i, j) for i, j, _ in proposals if eligible[i] and eligible[j]]
        K = len(blocks)
        q = min(cfg.q_max, (cfg.block_target / 2.0) / max(1, K))
        p = min(0.5, max(0.0, cfg.target_size - cfg.block_target) / n_el)
        X = (rng.random((R, n)) < p) & eligible[None, :]
        act = rng.random((R, K)) < q
        for k, (i, j) in enumerate(blocks):
            X[act[:, k], i] = True
            X[act[:, k], j] = True
            cand_pair[i, j] = cand_pair[j, i] = True
    else:
        mode = "plain"
        q = 0.0
        p = p_plain
        X = (rng.random((R, n)) < p) & eligible[None, :]
        cand_pair = eligible[:, None] & eligible[None, :]
        if proposals:
            # proposals are only a ranking hint in plain mode; all eligible pairs are tested
            pass
    rec = DropoutDesignRecord(pool_ids=[str(i) for i in range(n)], p=float(p),
                              blocks=[(str(i), str(j)) for i, j in blocks], q=float(q), runs=R,
                              seed_policy="independent", mode=mode)
    return X, rec, cand_pair


@dataclass
class DropoutRound:
    X: np.ndarray
    Y: np.ndarray
    attribution: stats.AttributionResult
    design: DropoutDesignRecord
    bundles: list[Bundle]
    cost: float


def run_dropout(adapter, broker: BudgetBroker, seed: int, cfg: DropoutConfig,
                proposals: list[tuple[int, int, int]] | None = None,
                eligible: np.ndarray | None = None, split: str = "DEV", crn: bool = False,
                category: str = "evaluation", max_runs: int | None = None) -> DropoutRound | None:
    """Spend the affordable budget on dropout runs, then attribute and FDR-control."""
    ids = adapter.pool_ids()
    n = len(ids)
    unit = adapter.library_eval_cost(int(cfg.target_size))
    R = broker.affordable_units(category, unit)
    if max_runs is not None:
        R = min(R, max_runs)
    if R < 8:
        return None
    rng = np.random.default_rng([seed, 4242])
    X, rec, cand_pair = plan_design(n, R, rng, cfg, proposals, eligible)
    try:
        broker.charge(category, unit * R, purpose=f"dropout {rec.mode} R={R}")
    except BudgetExceeded:
        return None
    Y = adapter.evaluate(X, split, seed, crn)
    el = np.ones(n, bool) if eligible is None else np.asarray(eligible, bool)
    att = stats.llr_attribution(X, Y, el, cand_pair, cfg.tau, cfg.delta, cfg.min_tasks)
    bundles = make_bundles(att, ids, X, Y, cfg.fdr_q)
    return DropoutRound(X, Y, att, rec, bundles, unit * R)


def make_bundles(att: stats.AttributionResult, ids: list[str], X: np.ndarray, Y: np.ndarray,
                 fdr_q: float) -> list[Bundle]:
    """Declared singles and pairs become bundles; FDR control is applied jointly over all
    declared hypotheses with Benjamini-Hochberg on their combined p-values."""
    hyps: list[tuple[str, tuple[int, ...], int, float]] = []
    for i in sorted(att.direct):
        hyps.append(("single", (i,), int(att.single_votes[i]), att.single_pvalues.get(i, 1.0)))
    for pr in sorted(att.pairs):
        hyps.append(("pair", pr, att.pair_votes[pr], att.pair_pvalues.get(pr, 1.0)))
    if not hyps:
        return []
    rej = stats.benjamini_hochberg([h[3] for h in hyps], fdr_q)
    total = Y.sum(1).astype(float)
    ci = stats.diff_in_means_ci(X, total)
    out = []
    for (kind, members, votes, p), ok in zip(hyps, rej):
        cred = tuple(float(v) for v in ci[members[0]]) if kind == "single" else None
        out.append(Bundle(members=tuple(ids[m] for m in members), kind=kind,
                          evidence=BundleEvidence(votes=votes, pvalue=float(p), fdr_rejected=bool(ok),
                                                  credit=cred)))
    return out
