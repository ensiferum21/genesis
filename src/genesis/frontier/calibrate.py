"""Forecast-calibration rules the Frontier can search (research plane; G2, `docs/OMEGA_FOUNDRY.md` §3, B20_R170).

F3 (B20_R156) found the forecaster's 90% intervals covering about 66%, biased low, and a textbook correction (a
degrees-of-freedom rescaling of the bootstrap residuals) did not repair it. G2 does not write a better patch by
hand. It gives the engine a small grammar of UPDATE RULES, each mapping the engine's own resolved forecasts to an
adjustment of its future intervals, and lets a meta-search choose among them by what they do for allocation.

A rule is a point of GRID (flat keys, so that `meta.MetaDomain` can search them as policy parameters):
  cal_signal  'none'      the fixed forecaster (the identity rule; the defaults);
              'resolved'  a forecast is resolved when its branch's compute reaches the horizon: the truth is the
                          branch's first observation at or past it;
              'hindcast'  each new forecast is paired with a hindcast: the same forecaster, run on the branch's own
                          past up to the same fraction of its present compute, forecasting the present, and resolved
                          at once against the present observation (rolling-origin evaluation, Tashman 2000). It does
                          not wait for branches to reach their horizons, so it is not limited to the branches the
                          allocator favours;
  cal_form    'scale'     the half-widths are multiplied (s_hi above the median, s_lo below);
              'shift'     the interval is moved by d half-widths (a bias correction);
              'both'      shift, then scale;
  cal_sides   'both' or 'hi' (scale only the upper side, the one the allocator's index reads);
  cal_cond    'global', or 'frac': separate state per band of the observed fraction t/H ([0, 0.5), [0.5, 0.8),
              [0.8, 1]); coverage in F3 rose with that fraction;
  cal_update  'aci'       adaptive conformal steps (Gibbs and Candes 2021): s <- s exp(gamma (miss - ALPHA)) per side,
                          d <- d + 2 gamma (1[truth above the shifted median] - 1/2);
              'quantile'  split-conformal quantiles over a window of the last round(2/gamma) resolved forecasts:
                          d = the median of u, then s_hi and s_lo = the (1 - ALPHA) quantiles of the residuals
                          about the shifted median, each in units of its raw half-width;
  cal_rate    gamma, the step (and through it the window).

Everything is a function of the rule and the resolved forecasts, so a run with a rule is as deterministic as without
one. Normalised residuals: r_hi = (truth - m) / (hi - mid) and r_lo = (m - truth) / (mid - lo), with m the shifted
median; u = (truth - mid) / w, with w the raw half-width (hi - lo) / 2. Bounds keep a rule from running away:
s in [0.25, 8], d in [-3, 3].
"""
import math

import numpy as np

GRID = {'cal_signal': ['none', 'resolved', 'hindcast'], 'cal_form': ['scale', 'shift', 'both'],
        'cal_sides': ['both', 'hi'], 'cal_cond': ['global', 'frac'], 'cal_update': ['aci', 'quantile'],
        'cal_rate': [0.01, 0.05]}
DEFAULT = {'cal_signal': 'none', 'cal_form': 'scale', 'cal_sides': 'both', 'cal_cond': 'global',
           'cal_update': 'aci', 'cal_rate': 0.05}
ALPHA = 0.05                     # per side: the nominal 90% interval
FRAC_BANDS = (0.5, 0.8)
S_MIN, S_MAX, D_MAX = 0.25, 8.0, 3.0
MIN_QUANTILE = 10                # resolved residuals before a quantile rule moves off its start


def rule_of(params):
    """The rule's keys from a policy's parameters (defaults for absent keys), validated against GRID."""
    rule = {k: params.get(k, v) for k, v in DEFAULT.items()}
    for k, v in rule.items():
        if v not in GRID[k]:
            raise ValueError(f'{k}={v!r} is not in the grammar')
    return rule


def canonical(rule):
    """Rules that behave identically map to one key (with no signal, the other keys do nothing)."""
    rule = rule_of(rule)
    if rule['cal_signal'] == 'none':
        return dict(DEFAULT)
    if rule['cal_form'] == 'shift':
        rule['cal_sides'] = 'both'
    return rule


def _band(frac):
    return sum(frac >= b for b in FRAC_BANDS)


class Calibrator:
    def __init__(self, params=None):
        self.rule = rule_of(params or {})
        self.active = self.rule['cal_signal'] != 'none'
        self.state = {}
        self.resolved = 0

    def _st(self, frac):
        k = str(_band(frac) if self.rule['cal_cond'] == 'frac' else 0)
        if k not in self.state:
            self.state[k] = {'s_hi': 1.0, 's_lo': 1.0, 'd': 0.0, 'q': []}
        return self.state[k]

    def adjust(self, fc, frac):
        """The calibrated forecast (a new dict); the raw one when the rule is the identity or the interval is open."""
        if not self.active:
            return fc
        lo, mid, hi = fc['lo'], fc['mid'], fc['hi']
        if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
            return fc
        st = self._st(frac)
        form = self.rule['cal_form']
        w = (hi - lo) / 2
        if form in ('shift', 'both'):
            dlt = st['d'] * w
            lo, mid, hi = lo + dlt, mid + dlt, hi + dlt
        if form in ('scale', 'both'):
            hi = mid + st['s_hi'] * (hi - mid)
            if self.rule['cal_sides'] == 'both':
                lo = mid - st['s_lo'] * (mid - lo)
        return dict(fc, lo=float(lo), mid=float(mid), hi=float(hi))

    def resolve(self, fc, frac, truth):
        """Learn from one raw forecast whose truth is now known."""
        if not self.active:
            return
        lo, mid, hi = fc['lo'], fc['mid'], fc['hi']
        if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo or not math.isfinite(truth):
            return
        st = self._st(frac)
        self.resolved += 1
        form, upd, g = self.rule['cal_form'], self.rule['cal_update'], float(self.rule['cal_rate'])
        w = (hi - lo) / 2
        m = mid + (st['d'] * w if form in ('shift', 'both') else 0.0)
        u = (truth - mid) / w
        if upd == 'aci':
            r_hi = (truth - m) / (hi - mid) if hi > mid else math.inf
            r_lo = (m - truth) / (mid - lo) if mid > lo else math.inf
            if form in ('shift', 'both'):
                st['d'] = min(D_MAX, max(-D_MAX, st['d'] + 2 * g * ((truth > m) - 0.5)))
            if form in ('scale', 'both'):
                st['s_hi'] = min(S_MAX, max(S_MIN, st['s_hi'] * math.exp(g * ((r_hi > st['s_hi']) - ALPHA))))
                if self.rule['cal_sides'] == 'both':
                    st['s_lo'] = min(S_MAX, max(S_MIN, st['s_lo'] * math.exp(g * ((r_lo > st['s_lo']) - ALPHA))))
            return
        win = max(MIN_QUANTILE, int(round(2 / g)))
        st['q'] = (st['q'] + [[float(u), (hi - mid) / w, (mid - lo) / w]])[-win:]
        if len(st['q']) < MIN_QUANTILE:
            return
        q = np.array(st['q'])
        if form in ('shift', 'both'):
            st['d'] = float(min(D_MAX, max(-D_MAX, np.median(q[:, 0]))))
        if form in ('scale', 'both'):
            d = st['d'] if form == 'both' else 0.0
            with np.errstate(divide='ignore', invalid='ignore'):
                r_hi = np.where(q[:, 1] > 0, (q[:, 0] - d) / q[:, 1], np.inf)
                r_lo = np.where(q[:, 2] > 0, (d - q[:, 0]) / q[:, 2], np.inf)
            st['s_hi'] = float(min(S_MAX, max(S_MIN, np.quantile(r_hi, 1 - ALPHA))))
            if self.rule['cal_sides'] == 'both':
                st['s_lo'] = float(min(S_MAX, max(S_MIN, np.quantile(r_lo, 1 - ALPHA))))

    def to_json(self):
        return {'rule': self.rule, 'state': self.state, 'resolved': self.resolved}

    def load(self, data):
        if data.get('rule', self.rule) != self.rule:
            raise ValueError('a saved calibrator of another rule')
        self.state = {k: dict(v) for k, v in data.get('state', {}).items()}
        self.resolved = data.get('resolved', 0)


def hindcast_origin(ts, frac):
    """The index of the last observation at or before frac x the present compute, or None if fewer than 4 points
    would remain (the forecaster's minimum) or no observation is left to forecast."""
    if len(ts) < 5:
        return None
    cut = ts[-1] * frac
    j = int(np.searchsorted(np.asarray(ts, float), cut, side='right')) - 1
    return j if 3 <= j < len(ts) - 1 else None
