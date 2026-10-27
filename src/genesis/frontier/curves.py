"""Discovery-curve extrapolation with honest uncertainty (research plane; F1, `docs/OMEGA_FRONTIER.md` §4.3).

A branch's curve f(t) is the true quality of its incumbent after compute t; the engine sees noisy observations y_i
of it (exact ones in an exact domain). `forecast(t, y, H)` says where f will be at compute H, as quantiles
(lo, mid, hi) = (5%, 50%, 95%).

Families, each linear in (a, b) once its shape parameters are fixed:
    weibull   f = a - b * exp(-(t/tau)^k)        k in KAPPAS, tau on a fine log grid relative to t_max
    pow       f = a - b * (t + t0)^(-c)          c on a grid in [0.1, 3]
    log       f = a + b * log(1 + t/t0)          unbounded (capped by `ceiling` if the domain has one)
    flat      f = a
with b >= 0 (a curve that does not fall). Every (family, shape) is fitted by least squares on the observations (at
most MAX_POINTS of them; beyond that, consecutive observations are averaged in pairs, with weights); the fits are
weighted by AICc (Akaike weights). Uncertainty: a moving-block residual bootstrap, every sample refitted over every
shape at once (vectorised), and one model drawn per sample from that sample's weights; the bootstrap's half-widths
are then widened by INFLATE about the median, to cover shape error the bootstrap cannot see (the value was set on
development curves of the planted types, disclosed in the F1 record). This is a light version of
the ensemble of Domhan, Springenberg and Hutter (IJCAI 2015), who weighted 11 families by MCMC.

A curve that is still flat cannot reveal a later rise (a "slow starter"). The allocator's patience and reserved
exploration handle that (`allocate.py`); the calibration tests report coverage by the share of the horizon observed.
"""
import math

import numpy as np

MAX_POINTS = 256
TAU_GRID = tuple(float(x) for x in np.geomspace(0.02, 12.0, 64))
KAPPAS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
POW_C = (0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
INFLATE = 1.25       # half-widths widened about the median (set on development curves, disclosed)


def _prepare(t, y):
    """(t, y, w): observations, pair-averaged (weights = counts) until at most MAX_POINTS remain."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    w = np.ones(len(t))
    while len(t) > MAX_POINTS:
        k = len(t) // 2 * 2
        tt = (t[:k:2] * w[:k:2] + t[1:k:2] * w[1:k:2]) / (w[:k:2] + w[1:k:2])
        yy = (y[:k:2] * w[:k:2] + y[1:k:2] * w[1:k:2]) / (w[:k:2] + w[1:k:2])
        ww = w[:k:2] + w[1:k:2]
        if k < len(t):
            tt, yy, ww = np.append(tt, t[-1]), np.append(yy, y[-1]), np.append(ww, w[-1])
        t, y, w = tt, yy, ww
    return t, y, w


def _shapes(t_max):
    """[(family, shape, k_params, g)] where the model is f = a + b * g(t); g None for flat."""
    t0 = max(1.0, t_max / 50.0)
    out = [('flat', None, 1, None)]
    for k in KAPPAS:
        for s in TAU_GRID:
            tau = s * t_max
            out.append(('weibull', (k, tau), 4, lambda x, k=k, tau=tau: -np.exp(-(np.maximum(x, 0.0) / tau) ** k)))
    for c in POW_C:
        out.append(('pow', (c, t0), 3, lambda x, c=c, t0=t0: -(x + t0) ** (-c)))
    out.append(('log', (t0,), 3, lambda x, t0=t0: np.log1p(np.maximum(x, 0.0) / t0)))
    return out


class _Model:
    """All shapes evaluated at the observation times and at H, for vectorised fits."""

    def __init__(self, t, w, H):
        self.shapes = _shapes(float(t[-1]))
        self.w = w / w.sum()
        self.n_eff = float(w.sum())
        G = [np.zeros(len(t)) if g is None else g(t) for _, _, _, g in self.shapes]
        self.G = np.array(G)                                       # (S, n)
        self.GH = np.array([0.0 if g is None else float(g(np.array([float(H)]))[0]) for _, _, _, g in self.shapes])
        self.k = np.array([kp for _, _, kp, _ in self.shapes], float)
        self.flat = np.array([g is None for _, _, _, g in self.shapes])

    def fit(self, Y):
        """Y (B, n) -> a (B, S), b (B, S), aicc (B, S)."""
        w = self.w
        Gm = self.G @ w                                            # (S,)
        Ym = Y @ w                                                 # (B,)
        Gc = self.G - Gm[:, None]                                  # (S, n)
        sxx = (Gc ** 2) @ w                                        # (S,)
        Yc = Y - Ym[:, None]                                       # (B, n)
        sxy = (Yc * w) @ Gc.T                                      # (B, S)
        b = np.where(sxx[None, :] > 1e-15, np.maximum(0.0, sxy / np.where(sxx > 1e-15, sxx, 1.0)[None, :]), 0.0)
        b[:, self.flat] = 0.0
        a = Ym[:, None] - b * Gm[None, :]
        # weighted residual sum of squares in closed form (no (B, S, n) tensor)
        Syy = (Y ** 2) @ w                                         # (B,)
        Syg = Y @ (self.G * w).T                                   # (B, S)
        Sgg = (self.G ** 2) @ w                                    # (S,)
        rss = (Syy[:, None] - 2 * a * Ym[:, None] - 2 * b * Syg + a ** 2 + 2 * a * b * Gm[None, :]
               + b ** 2 * Sgg[None, :]) * self.n_eff
        n = self.n_eff
        rss = np.maximum(rss, 1e-12 * n)
        aic = n * np.log(rss / n) + 2 * self.k[None, :]
        corr = np.where(n - self.k - 1 > 0, 2 * self.k * (self.k + 1) / np.maximum(n - self.k - 1, 1e-9), 1e6)
        return a, b, aic + corr[None, :]

    def predict(self, a, b):
        return a + b * self.GH[None, :]


def _akaike(aic):
    w = np.exp(-(aic - aic.min(axis=1, keepdims=True)) / 2)
    return w / w.sum(axis=1, keepdims=True)


def point(t, y, H, ceiling=None):
    """The AICc-weighted forecast at H (no uncertainty)."""
    t, y, w = _prepare(t, y)
    if len(t) < 4:
        return float(y[-1]) if len(y) else 0.0
    M = _Model(t, w, H)
    a, b, aic = M.fit(y[None, :])
    v = float((_akaike(aic) * M.predict(a, b)).sum())
    return min(v, ceiling) if ceiling is not None else v


def forecast(t, y, H, B=100, rng=None, ceiling=None, block=3):
    """{'lo', 'mid', 'hi', 'n'} for f(H). With fewer than 4 observations the interval is open above."""
    rng = rng if rng is not None else np.random.default_rng(0)
    t, y, w = _prepare(t, y)
    n = len(t)
    last = float(y[-1]) if n else 0.0
    if n < 4:
        return {'lo': -math.inf, 'mid': last, 'hi': ceiling if ceiling is not None else math.inf, 'n': n}
    M = _Model(t, w, H)
    a0, b0, aic0 = M.fit(y[None, :])
    w0 = _akaike(aic0)[0]
    fitted = (w0[:, None] * (a0[0][:, None] + b0[0][:, None] * M.G)).sum(axis=0)
    resid = y - fitted
    nb = math.ceil(n / block)
    starts = rng.integers(0, max(1, n - block + 1), size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    idx = np.minimum(idx, n - 1)
    Y = fitted[None, :] + resid[idx]
    a, b, aic = M.fit(Y)
    W = _akaike(aic)
    P = M.predict(a, b)                                            # (B, S)
    cum = W.cumsum(axis=1)
    u = rng.random(B)[:, None]
    pick = (cum < u).sum(axis=1).clip(0, P.shape[1] - 1)
    sims = P[np.arange(B), pick]
    if ceiling is not None:
        sims = np.minimum(sims, ceiling)
    lo, mid, hi = (float(np.quantile(sims, q)) for q in (0.05, 0.5, 0.95))
    lo, hi = mid - INFLATE * (mid - lo), mid + INFLATE * (hi - mid)
    if ceiling is not None:
        hi = min(hi, ceiling)
    return {'lo': lo, 'mid': mid, 'hi': hi, 'n': n}


def p_exceeds(t, y, H, level, B=100, rng=None, ceiling=None):
    """The bootstrap share of forecasts of f(H) above `level`."""
    rng = rng if rng is not None else np.random.default_rng(0)
    t, y, w = _prepare(t, y)
    if len(t) < 4:
        return 0.5
    fc_rng = rng
    M = _Model(t, w, H)
    a0, b0, aic0 = M.fit(y[None, :])
    w0 = _akaike(aic0)[0]
    fitted = (w0[:, None] * (a0[0][:, None] + b0[0][:, None] * M.G)).sum(axis=0)
    resid = y - fitted
    Y = fitted[None, :] + fc_rng.choice(resid, size=(B, len(t)), replace=True)
    a, b, aic = M.fit(Y)
    W = _akaike(aic)
    P = M.predict(a, b)
    pick = (W.cumsum(axis=1) < fc_rng.random(B)[:, None]).sum(axis=1).clip(0, P.shape[1] - 1)
    sims = P[np.arange(B), pick]
    if ceiling is not None:
        sims = np.minimum(sims, ceiling)
    return float(np.mean(sims > level))
