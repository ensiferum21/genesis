"""Statistics owned by the kernel.

Everything that turns outcomes into evidence lives here, so research code cannot pick a
friendlier estimator. Contents:

* per-task likelihood-ratio attribution for library dropout (U2), single vs AND-pair
* difference-in-means credit (equals Banzhaf value by maximum sample reuse at p = 1/2)
* Benjamini-Hochberg and e-BH false-discovery control; Holm family-wise control
* McNemar's exact test and Connor's sample-size formula
* two one-sided tests (TOST) with EQUIVALENT / DIFFERENT / INCONCLUSIVE verdicts
* the 2x2 cascade interaction estimator with a paired standard error
* inverse-propensity and doubly robust value estimates for allocation experiments (U5)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
from scipy import stats as sps


# --------------------------------------------------------------------------- likelihoods
def bernoulli_ll(k: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Bernoulli log-likelihood at the MLE for k successes in n trials (vectorised, safe)."""
    k = np.asarray(k, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(n > 0, k / np.maximum(n, 1), 0.5)
        a = np.where(k > 0, k * np.log(np.clip(p, 1e-12, 1)), 0.0)
        b = np.where(n - k > 0, (n - k) * np.log(np.clip(1 - p, 1e-12, 1)), 0.0)
    return a + b


@dataclass
class AttributionResult:
    direct: set[int]
    pairs: set[tuple[int, int]]
    single_votes: np.ndarray                       # (n,)
    pair_votes: dict[tuple[int, int], int]
    pair_pvalues: dict[tuple[int, int], float]     # Fisher-combined over won tasks
    single_pvalues: dict[int, float]
    task_winner: list[tuple[str, tuple[int, ...]] | None] = field(default_factory=list)


def llr_attribution(X: np.ndarray, Y: np.ndarray, cand_single: np.ndarray,
                    cand_pair: np.ndarray, tau: float, delta: float, min_tasks: int,
                    min_co: int = 4) -> AttributionResult:
    """Per-task model selection between 'success depends on i' and 'on i AND j'.

    X: (R, n) bool inclusion matrix; Y: (R, T) {0,1} outcomes.
    A pair wins a task if its LLR >= tau, beats the best single by delta, and success is
    more likely when both are present; else the best single wins if its LLR >= tau and
    its effect is positive. A candidate (pair) is declared when it wins >= min_tasks tasks.
    """
    X = np.asarray(X, dtype=bool)
    Y = np.asarray(Y)
    R, n = X.shape
    T = Y.shape[1]
    Xf = X.astype(np.float64)
    Yf = Y.astype(np.float64)
    N1 = Xf.sum(0)
    single_ok = np.asarray(cand_single, bool) & (N1 >= min_co) & ((R - N1) >= min_co)
    I, J = np.nonzero(np.triu(np.asarray(cand_pair, bool), 1))
    if len(I):
        co = (X[:, I] & X[:, J]).sum(0)
        keep = (co >= min_co) & ((R - co) >= min_co)
        I, J = I[keep], J[keep]
    sy = Yf.sum(0)
    valid = (sy >= 2) & (sy <= R - 2)
    ll0 = bernoulli_ll(sy, np.full_like(sy, float(R)))
    a = Xf.T @ Yf
    n1 = N1[:, None] + 0 * a
    llr1 = 2 * (bernoulli_ll(a, n1) + bernoulli_ll(sy - a, R - n1) - ll0)
    with np.errstate(divide="ignore", invalid="ignore"):
        pos1 = (a / np.maximum(n1, 1)) > ((sy - a) / np.maximum(R - n1, 1))
    llr1 = np.where(single_ok[:, None] & pos1, llr1, -1.0)
    b1 = llr1.max(0) if n else np.full(T, -1.0)
    arg1 = llr1.argmax(0) if n else np.zeros(T, int)
    if len(I):
        Z = (X[:, I] & X[:, J]).astype(np.float64)
        N11 = Z.sum(0)[:, None] + 0 * Yf[:1, :]
        A = Z.T @ Yf
        llr2 = 2 * (bernoulli_ll(A, N11) + bernoulli_ll(sy - A, R - N11) - ll0)
        with np.errstate(divide="ignore", invalid="ignore"):
            shape = (A / np.maximum(N11, 1)) > ((sy - A) / np.maximum(R - N11, 1))
        llr2 = np.where(shape, llr2, -1.0)
        b2 = llr2.max(0)
        arg2 = llr2.argmax(0)
    else:
        llr2 = np.zeros((0, T))
        b2 = np.full(T, -1.0)
        arg2 = np.zeros(T, int)
    pair_win = valid & (b2 >= tau) & (b2 >= b1 + delta)
    single_win = valid & ~pair_win & (b1 >= tau)
    sv = np.bincount(arg1[single_win], minlength=n) if n else np.zeros(0, int)
    winners: list[tuple[str, tuple[int, ...]] | None] = [None] * T
    single_llr_by: dict[int, list[float]] = {}
    for t in np.nonzero(single_win)[0]:
        i = int(arg1[t])
        winners[t] = ("single", (i,))
        single_llr_by.setdefault(i, []).append(float(llr1[i, t]))
    pair_votes: dict[tuple[int, int], int] = {}
    pair_llr_by: dict[tuple[int, int], list[float]] = {}
    for t in np.nonzero(pair_win)[0]:
        k = int(arg2[t])
        key = (int(min(I[k], J[k])), int(max(I[k], J[k])))
        winners[t] = ("pair", key)
        pair_votes[key] = pair_votes.get(key, 0) + 1
        pair_llr_by.setdefault(key, []).append(float(llr2[k, t]))
    direct = {int(i) for i in np.nonzero(sv >= min_tasks)[0]}
    pairs = {k for k, v in pair_votes.items() if v >= min_tasks}
    pair_p = {k: fisher_combine([sps.chi2.sf(max(x, 0.0), 1) for x in v])
              for k, v in pair_llr_by.items()}
    single_p = {i: fisher_combine([sps.chi2.sf(max(x, 0.0), 1) for x in v])
                for i, v in single_llr_by.items()}
    return AttributionResult(direct, pairs, sv, pair_votes, pair_p, single_p, winners)


def fisher_combine(pvals: Sequence[float]) -> float:
    p = np.clip(np.asarray(pvals, dtype=float), 1e-300, 1.0)
    if len(p) == 0:
        return 1.0
    stat = -2.0 * np.log(p).sum()
    return float(sps.chi2.sf(stat, 2 * len(p)))


def diff_in_means_credit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-candidate credit: mean(y | i in S) - mean(y | i not in S).

    With inclusion probability 1/2 this is the maximum-sample-reuse estimator of the
    Banzhaf value (Wang and Jia, AISTATS 2023)."""
    X = np.asarray(X, bool)
    y = np.asarray(y, float)
    out = np.zeros(X.shape[1])
    for i in range(X.shape[1]):
        inc = X[:, i]
        if inc.any() and (~inc).any():
            out[i] = y[inc].mean() - y[~inc].mean()
    return out


def diff_in_means_ci(X: np.ndarray, y: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """(n, 3) array of credit, lower, upper (Welch normal approximation)."""
    X = np.asarray(X, bool)
    y = np.asarray(y, float)
    z = sps.norm.ppf(1 - alpha / 2)
    out = np.zeros((X.shape[1], 3))
    for i in range(X.shape[1]):
        inc = X[:, i]
        a, b = y[inc], y[~inc]
        if len(a) < 2 or len(b) < 2:
            out[i] = (0.0, -np.inf, np.inf)
            continue
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        out[i] = (d, d - z * se, d + z * se)
    return out


# --------------------------------------------------------------------------- multiplicity
def benjamini_hochberg(pvals: Sequence[float], q: float) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    if m == 0:
        return np.zeros(0, bool)
    order = np.argsort(p)
    thresh = q * (np.arange(1, m + 1) / m)
    passed = p[order] <= thresh
    k = np.nonzero(passed)[0].max() + 1 if passed.any() else 0
    rej = np.zeros(m, bool)
    rej[order[:k]] = True
    return rej


def e_bh(evalues: Sequence[float], q: float) -> np.ndarray:
    """e-BH (Wang and Ramdas, 2022): reject the k largest e-values, k = max{k: e_(k) >= m/(q k)}."""
    e = np.asarray(evalues, dtype=float)
    m = len(e)
    if m == 0:
        return np.zeros(0, bool)
    order = np.argsort(-e)
    ks = np.arange(1, m + 1)
    ok = e[order] >= m / (q * ks)
    k = np.nonzero(ok)[0].max() + 1 if ok.any() else 0
    rej = np.zeros(m, bool)
    rej[order[:k]] = True
    return rej


def holm(pvals: Sequence[float], alpha: float) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    rej = np.zeros(m, bool)
    for rank, idx in enumerate(order):
        if p[idx] <= alpha / (m - rank):
            rej[idx] = True
        else:
            break
    return rej


# --------------------------------------------------------------------------- paired tests
@dataclass
class McNemarResult:
    b: int          # first arm solved, second not
    c: int          # second arm solved, first not
    pvalue: float   # exact two-sided
    diff: float     # (b - c) / n


def mcnemar(a: Sequence[bool], b: Sequence[bool]) -> McNemarResult:
    a = np.asarray(a, bool)
    b = np.asarray(b, bool)
    n10 = int((a & ~b).sum())
    n01 = int((~a & b).sum())
    nd = n10 + n01
    p = 1.0 if nd == 0 else float(min(1.0, 2 * sps.binom.cdf(min(n10, n01), nd, 0.5)))
    return McNemarResult(n10, n01, p, (n10 - n01) / max(1, len(a)))


def mcnemar_sample_size(p10: float, p01: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Connor (1987): tasks needed to detect p10 != p01 with a two-sided McNemar test."""
    psi = p10 + p01
    d = p10 - p01
    za = sps.norm.ppf(1 - alpha / 2)
    zb = sps.norm.ppf(power)
    n = (za * np.sqrt(psi) + zb * np.sqrt(psi - d * d)) ** 2 / (d * d)
    return int(np.ceil(n))


def paired_bootstrap_ci(a: Sequence[float], b: Sequence[float], n_boot: int = 2000,
                        alpha: float = 0.05, seed: int = 0) -> tuple[float, float, float]:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    boots = d[idx].mean(1)
    return float(d.mean()), float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2))


@dataclass
class TostResult:
    verdict: str          # EQUIVALENT | DIFFERENT | INCONCLUSIVE
    mean_diff: float
    ci90: tuple[float, float]
    ci95: tuple[float, float]
    margin: float
    p_lower: float
    p_upper: float


def tost_paired(a: Sequence[float], b: Sequence[float], margin: float,
                alpha: float = 0.05) -> TostResult:
    """Two one-sided tests on paired differences. Too little data is INCONCLUSIVE, never
    'no difference'."""
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    if n < 3:
        return TostResult("INCONCLUSIVE", float(d.mean()) if n else 0.0, (-np.inf, np.inf),
                          (-np.inf, np.inf), margin, 1.0, 1.0)
    m = d.mean()
    se = d.std(ddof=1) / np.sqrt(n)
    if se == 0:
        se = 1e-12
    df = n - 1
    p_lower = float(sps.t.sf((m + margin) / se, df))   # H0: mean <= -margin
    p_upper = float(sps.t.cdf((m - margin) / se, df))  # H0: mean >= +margin
    t90 = sps.t.ppf(1 - alpha, df)
    t95 = sps.t.ppf(1 - alpha / 2, df)
    ci90 = (float(m - t90 * se), float(m + t90 * se))
    ci95 = (float(m - t95 * se), float(m + t95 * se))
    if max(p_lower, p_upper) < alpha:
        verdict = "EQUIVALENT"
    elif ci95[0] > 0 or ci95[1] < 0:
        verdict = "DIFFERENT"
    else:
        verdict = "INCONCLUSIVE"
    return TostResult(verdict, float(m), ci90, ci95, margin, p_lower, p_upper)


# --------------------------------------------------------------------------- cascade
@dataclass
class CascadeEstimate:
    estimate: float
    se: float
    ci95: tuple[float, float]
    n_tasks: int


def cascade_2x2(y11: Sequence[float], y10: Sequence[float], y01: Sequence[float],
                y00: Sequence[float]) -> CascadeEstimate:
    """Cascade = (Y11 - Y01) - (Y10 - Y00) per task, averaged over the same later tasks.

    Index 1x = candidate present, x1 = research running (0 = frozen). All four arms must be
    scored on the same tasks, ideally under common random numbers."""
    arr = [np.asarray(v, float) for v in (y11, y10, y01, y00)]
    if len({len(v) for v in arr}) != 1:
        raise ValueError("all four arms must be scored on the same tasks")
    per_task = (arr[0] - arr[2]) - (arr[1] - arr[3])
    n = len(per_task)
    est = float(per_task.mean())
    se = float(per_task.std(ddof=1) / np.sqrt(n)) if n > 1 else float("inf")
    z = 1.959963984540054
    return CascadeEstimate(est, se, (est - z * se, est + z * se), n)


# --------------------------------------------------------------------------- allocation
def ipw_values(actions: Sequence[str], propensities: Sequence[float], rewards: Sequence[float],
               action_set: Iterable[str]) -> dict[str, float]:
    """Self-normalised inverse-propensity value per action from logged decisions."""
    actions = list(actions)
    p = np.asarray(propensities, float)
    r = np.asarray(rewards, float)
    out = {}
    for a in action_set:
        w = np.array([1.0 / pi if ai == a else 0.0 for ai, pi in zip(actions, p)])
        out[a] = float((w * r).sum() / w.sum()) if w.sum() > 0 else float("nan")
    return out


def doubly_robust_values(actions: Sequence[str], propensities: Sequence[float],
                         rewards: Sequence[float], model: dict[str, float],
                         action_set: Iterable[str]) -> dict[str, float]:
    """DR value per action: model prediction plus IPW-weighted residual correction."""
    actions = list(actions)
    p = np.asarray(propensities, float)
    r = np.asarray(rewards, float)
    n = len(actions)
    out = {}
    for a in action_set:
        base = model.get(a, 0.0)
        corr = sum((1.0 / pi) * (ri - base) for ai, pi, ri in zip(actions, p, r) if ai == a)
        out[a] = float(base + corr / max(1, n))
    return out
