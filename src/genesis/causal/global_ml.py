"""Global interpretation of every regime at once (B20_R130; Genesis Ω, Ω1): the established full-experiment
estimator, and a multi-regime maximum-likelihood estimator for any set of experiments.

Why. Development looks for B20_R130 (24 Oct 2026, disclosed in its script) found that the per-pair framework of
`active3` reaches a hidden-cause F1 of only about 0.5 even with every experiment, while the established estimator for
linear models with latent confounders reaches about 0.7 from the same data. The per-pair framework asks only about
FCI's adjacencies and judges each pair from a coarse test; a global estimator uses every regime's covariance for
every pair at once.

Model. Linear structural equations with correlated errors (an acyclic directed mixed graph's linear model):
    X = X B + e,   cov(e) = Omega       (rows are samples; B[i, j] != 0 iff i -> j; Omega[i, j] != 0 iff i <-> j)
so Sigma = (I - B)^-T Omega (I - B)^-1. A hard intervention on t cuts every edge into t, from observed and hidden
parents alike: column t of B is zero and row and column t of Omega are zero except its variance.

`llc` (established; Hyttinen, Eberhardt and Hoyer, JMLR 2012, for single-variable experiments on every variable):
the total effects T[t, :] are the regression slopes of each X_j on X_t under do(t); then B = I - T^-1 and
Omega = (I - B)^T Sigma (I - B) from the observational covariance. With every variable intervened on, the model is
identified (their pair condition).

`fit` (builder-written for any subset of experiments): maximum likelihood of B and Omega = L L^T jointly over the
observational regime and every done experiment,
    F = sum_r n_r [log det Omega_r - 2 log|det(I - B_r)| + tr(Omega_r^-1 (I - B_r)^T S_r (I - B_r))] / N
        + lam_b sum |B_ij| + lam_o sum_{i<j} |Omega_ij|          (smoothed absolute values)
with analytic gradients (checked against finite differences in the tests) and L-BFGS from B = 0, Omega = S_0. With
every experiment it estimates what `llc` estimates; with fewer, the penalties choose the sparsest explanation among
those the data leave open. The regime-specific variance of an intervened variable is its sample variance.

`answer`: a directed edge where |B| exceeds `tb` (the larger direction), else a hidden-cause mark where the
correlation of Omega exceeds `to`; one mark per pair (the scorer's format), directed part acyclic as in `methods`.
"""
import numpy as np
from scipy.optimize import minimize

from . import methods as PCM

EPS = 1e-6
LAM_B, LAM_O = 0.02, 0.02


def covariances(X0, experiments):
    """[(S, n, t)]: the observational regime (t None) and each experiment {t: X_t}."""
    reg = [(np.cov(X0, rowvar=False, bias=True), X0.shape[0], None)]
    for t in sorted(experiments):
        X = experiments[t]
        reg.append((np.cov(X, rowvar=False, bias=True), X.shape[0], int(t)))
    return reg


def llc(regimes, p):
    """The established estimator; needs an experiment on every variable. Returns (B, Omega)."""
    S0 = next(S for S, n, t in regimes if t is None)
    T = np.eye(p)
    have = set()
    for S, n, t in regimes:
        if t is not None:
            T[t, :] = S[t, :] / S[t, t]
            T[t, t] = 1.0
            have.add(t)
    if have != set(range(p)):
        raise ValueError('llc needs an experiment on every variable')
    B = np.eye(p) - np.linalg.inv(T)
    np.fill_diagonal(B, 0.0)
    M = np.eye(p) - B
    return B, M.T @ S0 @ M


def _unpack(theta, p):
    B = np.zeros((p, p))
    off = ~np.eye(p, dtype=bool)
    B[off] = theta[:p * p - p]
    L = np.zeros((p, p))
    L[np.tril_indices(p)] = theta[p * p - p:]
    return B, L


def objective(theta, regimes, p, lam_b=LAM_B, lam_o=LAM_O):
    """(F, gradient) of the penalised negative log-likelihood per sample."""
    B, L = _unpack(theta, p)
    Om = L @ L.T
    F = 0.0
    gB = np.zeros((p, p))
    gOm = np.zeros((p, p))
    N = 0
    for S, n, t in regimes:
        Br, Omr = B.copy(), Om.copy()
        if t is not None:
            Br[:, t] = 0.0
            Omr[t, :] = 0.0
            Omr[:, t] = 0.0
            Omr[t, t] = S[t, t]
        M = np.eye(p) - Br
        sm, ldm = np.linalg.slogdet(M)
        so, ldo = np.linalg.slogdet(Omr)
        if sm == 0 or so <= 0:
            return 1e12, np.zeros_like(theta)
        K = np.linalg.inv(Omr)
        W = M.T @ S @ M
        F += n * (ldo - 2 * ldm + np.trace(K @ W))
        gBr = -(2 * S @ M @ K - 2 * np.linalg.inv(M).T)
        G = K - K @ W @ K
        if t is not None:
            gBr[:, t] = 0.0
            G[t, :] = 0.0
            G[:, t] = 0.0
        gB += n * gBr
        gOm += n * G
        N += n
    F /= N
    gB /= N
    gOm /= N
    off = ~np.eye(p, dtype=bool)
    sb = np.sqrt(B[off] ** 2 + EPS)
    F += lam_b * sb.sum()
    gB[off] += lam_b * B[off] / sb
    so_ = np.sqrt(Om ** 2 + EPS)
    F += lam_o * so_[off].sum() / 2
    gp = np.zeros((p, p))
    gp[off] = lam_o / 2 * Om[off] / so_[off]
    gOm += gp
    gL = (gOm + gOm.T) @ L
    return F, np.concatenate([gB[off], gL[np.tril_indices(p)]])


def fit(regimes, p, lam_b=LAM_B, lam_o=LAM_O, maxiter=500):
    """(B, Omega, converged) by L-BFGS from B = 0, Omega = the observational covariance."""
    S0 = next(S for S, n, t in regimes if t is None)
    L0 = np.linalg.cholesky(S0 + 1e-9 * np.eye(p))
    theta = np.concatenate([np.zeros(p * p - p), L0[np.tril_indices(p)]])
    res = minimize(objective, theta, args=(regimes, p, lam_b, lam_o), jac=True, method='L-BFGS-B',
                   options={'maxiter': maxiter})
    B, L = _unpack(res.x, p)
    return B, L @ L.T, bool(res.success)


def answer(B, Om, tb, to):
    p = B.shape[0]
    d = np.sqrt(np.abs(np.diag(Om)))
    R = Om / np.outer(d, d)
    dirs, bis = [], []
    for i in range(p):
        for j in range(i + 1, p):
            if max(abs(B[i, j]), abs(B[j, i])) > tb:
                dirs.append([i, j] if abs(B[i, j]) >= abs(B[j, i]) else [j, i])
            elif abs(R[i, j]) > to:
                bis.append([i, j])
    d_, u = PCM._acyclic_part(p, sorted(dirs), [])
    return {'directed': d_, 'undirected': sorted(u), 'bidirected': sorted(bis)}
