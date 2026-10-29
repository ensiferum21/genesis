"""Allocation policies (research plane; F1, `docs/OMEGA_FRONTIER.md` §4.5).

A policy looks at the engine's state and returns one action: ('advance', branch id) or ('open', direction).

`FrontierPolicy` (the engine's own). Compute is split into exploration and exploitation, and exploration is held to
a share eps of the compute spent so far:
  * first, problems revealed by a result are opened (branch out), then representations invented by abstraction
    (never-before-used directions);
  * a branch younger than `patience` quanta (too few points for a forecast) is advanced; that compute counts as
    exploration, as does compute given to a reactivated branch until it is `patience` quanta older;
  * if exploration is below eps x spent, a new direction is opened: imagine (the most novel of k), mutate a leading
    branch, recombine two leading branches on one problem, or reactivate a paused one;
  * otherwise the mature active branch with the largest index is advanced:
        I_b = max(0, hi_b(H_b) - best_p) + lam_lp * LP_b + lam_con * consilience_b
    where hi_b is the 95% forecast (`curves.forecast`) at the compute b would reach with a fair share of what is
    left, best_p the best verified value on b's problem, LP_b the learning progress (the gain per quantum over the
    last window, times the window) and consilience_b the shared-cluster bonus (`converge`);
  * a mature branch is paused (kept, not deleted) once it has had pause_min_share of the budget and its 95% forecast
    cannot beat what is already verified on its problem;
  * then, the value of opening a new direction on a problem (the upper half of every branch's current level, above
    that problem's best verified value: an empirical prior of what a direction reaches) is compared with the best
    index, and a direction is opened on that problem if it is larger;
  * eps adapts: x1.5 after `stall` steps without a material verified improvement (1% of the total, at least 0.005),
    x0.9 after one, within
    [eps_min, eps_max]; the divergence alarm (no cluster reached independently after alarm_share of the budget, with
    abstraction on) lifts it to at least 0.3.
Comparators (F3): `UniformPolicy` (round robin, random openings), `HalvingPolicy` (successive halving across
directions, as `autonomy.portfolio`'s G2), `UCBPolicy` (UCB1 on current levels), `RandomPolicy`.
"""
import math

import numpy as np

from . import calibrate as CAL
from . import curves as CV
from . import direction as D
from . import statefeat as SF

GRID = 1.25          # forecast horizons are rounded up to this geometric grid (cache reuse at scale)
DEFAULTS = {'eps': 0.25, 'eps_min': 0.1, 'eps_max': 0.4, 'stall': 40, 'lam_lp': 1.0, 'lam_con': 0.02,
            'patience_quanta': 4, 'pause_min_share': 0.01, 'k_imagine': 8, 'B': 60, 'window': 8,
            'alarm_share': 0.25, 'p_derive': 0.0, 'state_feature': None, 'log_decisions': False, **CAL.DEFAULT}


def level(br, last=3):
    ys = br['ys'][-last:]
    return sum(ys) / len(ys) if ys else -math.inf


def slope(br, window):
    ts, ys = br['ts'][-window:], br['ys'][-window:]
    if len(ts) < 3:
        return 0.0
    t, y = np.array(ts), np.array(ys)
    tc = t - t.mean()
    den = float((tc ** 2).sum())
    return 0.0 if den == 0 else max(0.0, float((tc * (y - y.mean())).sum() / den))


class FrontierPolicy:
    name = 'frontier'

    def __init__(self, params=None):
        self.p = dict(DEFAULTS, **(params or {}))
        self.eps = self.p['eps']
        self.last_improvement = 0
        self.explore_extra = 0.0                 # compute given to reactivated branches during their patience
        self._total = 0.0                        # the total verified value at the last material improvement
        self._fc_cache = {}
        self.calib = CAL.Calibrator(self.p)      # G2: the identity unless a calibration rule is set
        self._pending = {}                       # branch id -> [[H, raw forecast, t/H], ...] awaiting their truth
        self._fc_used = {}                       # forecast key -> the calibrated forecast last used
        self.decisions = []                      # G4: logged exploitation decisions (when log_decisions)
        sf = self.p['state_feature']
        if sf is not None and not SF.check(sf.get('expr')):
            raise ValueError(f'not a state feature: {sf!r}')

    def to_json(self):
        out = {'eps': self.eps, 'last_improvement': self.last_improvement, 'explore_extra': self.explore_extra,
               'total': self._total}
        if self.calib.active:
            out['calib'] = self.calib.to_json()
            out['pending'] = {str(k): v for k, v in self._pending.items() if v}
        return out

    def load(self, data):
        self.eps, self.last_improvement = data['eps'], data['last_improvement']
        self.explore_extra = data.get('explore_extra', 0.0)
        self._total = data.get('total', 0.0)
        if 'calib' in data:
            self.calib.load(data['calib'])
            self._pending = {int(k): v for k, v in data.get('pending', {}).items()}

    def observe(self, eng, improved):
        total = eng.total()
        improved = improved and total >= self._total * 1.01 + 0.005    # a material improvement
        if improved:
            self._total = total
            self.last_improvement = eng.step_count
            self.eps = max(self.p['eps_min'], self.eps * 0.9)
        elif eng.step_count - self.last_improvement >= self.p['stall']:
            self.last_improvement = eng.step_count
            self.eps = min(self.p['eps_max'], self.eps * 1.5)
        if (eng.spent >= self.p['alarm_share'] * eng.budget and not eng.clusters.converged()
                and eng.abstraction):
            self.eps = min(self.p['eps_max'], max(self.eps, 0.3))
        if self.calib.active and self._pending:
            self._resolve(eng)

    def _resolve(self, eng):
        """G2 'resolved' signal: a forecast whose branch has reached its horizon meets its truth, the branch's first
        observation at or past the horizon."""
        for bid in sorted(self._pending):
            items, b = self._pending[bid], eng.branches[bid]
            keep = []
            for H, fc, frac in items:
                if b['t'] >= H:
                    i = int(np.searchsorted(np.asarray(b['ts'], float), H - 1e-9, side='left'))
                    self.calib.resolve(fc, frac, float(b['ys'][min(i, len(b['ys']) - 1)]))
                else:
                    keep.append([H, fc, frac])
            self._pending[bid] = keep

    def forecast(self, eng, br, H):
        """The forecast at the horizon H rounded up to a geometric grid above the branch's compute (ratio GRID), so
        that a branch's forecast is recomputed only when it has new points or its horizon moves by a grid step."""
        t = max(br['t'], eng.quantum)
        k = max(0, math.ceil(math.log(max(H, t) / t) / math.log(GRID) - 1e-12))
        Hk = t * GRID ** k
        key = (br['id'], len(br['ts']), k)
        if key not in self._fc_cache:
            rng = np.random.default_rng(eng.seed_for('fc', br['id'], len(br['ts'])))
            self._fc_cache[key] = dict(CV.forecast(br['ts'], br['ys'], Hk, B=self.p['B'], rng=rng), H=Hk)
            if self.calib.active:
                self._learn(eng, br, self._fc_cache[key], Hk)
        if not self.calib.active:
            return self._fc_cache[key]
        adj = self.calib.adjust(self._fc_cache[key], br['t'] / Hk)
        self._fc_used[key] = adj
        return adj

    def _learn(self, eng, br, fc, H):
        """G2: queue a new raw forecast for resolution, or resolve its hindcast at once."""
        frac = br['t'] / H
        if self.calib.rule['cal_signal'] == 'resolved':
            self._pending.setdefault(br['id'], []).append([H, {k: fc[k] for k in ('lo', 'mid', 'hi')}, frac])
            return
        j = CAL.hindcast_origin(br['ts'], frac)
        if j is None:
            return
        rng = np.random.default_rng(eng.seed_for('hc', br['id'], len(br['ts'])))
        hc = CV.forecast(br['ts'][:j + 1], br['ys'][:j + 1], br['ts'][-1], B=self.p['B'], rng=rng)
        self.calib.resolve(hc, br['ts'][j] / br['ts'][-1], float(br['ys'][-1]))

    def patience(self, eng):
        return self.p['patience_quanta'] * eng.quantum

    def young(self, eng, b):
        return b['t'] < self.patience(eng) or b['t'] < b.get('young_until', 0.0)

    def explored(self, eng):
        P = self.patience(eng)
        return sum(min(b['t'], P) for b in eng.branches.values()) + self.explore_extra

    def choose(self, eng):
        rng = eng.rng
        # 1. branch out: a revealed problem with no branch yet
        for prob in eng.problem_order():
            if not any(b['direction']['problem'] == prob for b in eng.branches.values()):
                parent = eng.best_branch_overall()
                g = eng.grammar(prob)
                if parent is not None:
                    d = D.make(prob, parent['direction']['representation'], parent['direction']['method'],
                               parent['direction']['params'], op='branch_out', parent=D.descriptor(parent['direction']))
                    if D.valid(d, g):
                        return ('open', d)
                return ('open', D.imagine(g, prob, rng, eng.archive, self.p['k_imagine']))
        # 2. an invented representation not yet tried
        for prob, rep in eng.invented:
            if not any(b['direction']['problem'] == prob and b['direction']['representation'] == rep
                       for b in eng.branches.values()):
                lead = eng.best_branch(prob)
                g = eng.grammar(prob)
                method = lead['direction']['method'] if lead else rng.choice(g['method'])
                params = lead['direction']['params'] if lead else {k: rng.choice(v) for k, v in g['params'].items()}
                return ('open', D.make(prob, rep, method, params, op='imagine'))
        active = [b for b in eng.branches.values() if not b['paused']]
        # 3. young branches (exploration in progress)
        young = [b for b in active if self.young(eng, b)]
        if young:
            b = min(young, key=lambda b: (b['t'], b['id']))
            if b['t'] >= self.patience(eng):                 # a reactivated branch's extra patience
                self.explore_extra += eng.quantum
            return ('advance', b['id'])
        # 4. exploration, held to eps of the compute spent
        if not active or self.explored(eng) < self.eps * (eng.spent + eng.quantum):
            return self.explore(eng)
        # 5. exploitation by the index
        remaining = max(eng.quantum, eng.budget - eng.spent)
        share = remaining / max(1, len(active))
        best, best_i = None, -math.inf
        cands = []
        for b in sorted(active, key=lambda b: b['id']):
            H = b['t'] + share
            fc = self.forecast(eng, b, H)
            target = eng.best_verified.get(b['direction']['problem'], 0.0)
            if b['t'] >= self.p['pause_min_share'] * eng.budget and fc['hi'] <= target:
                b['paused'] = True
                eng.log('pause', branch=b['id'], hi=round(fc['hi'], 6), target=round(target, 6))
                continue
            gain = max(0.0, fc['hi'] - target)
            lp = slope(b, self.p['window']) * self.p['window'] * eng.quantum
            con = eng.clusters.branch_bonus(b['id'])
            idx = gain + self.p['lam_lp'] * lp + self.p['lam_con'] * con
            sf, logging = self.p['state_feature'], self.p['log_decisions']
            if sf is not None or logging:
                prims = SF.primitives(b, fc, target, gain, lp, con, idx, H)
                if sf is not None:
                    idx += sf['weight'] * SF.evaluate(sf['expr'], prims)
                if logging:
                    cands.append((idx, b['id'], prims))
            if idx > best_i:
                best, best_i = b, idx
        if best is None:
            return self.explore(eng)
        if self.p['log_decisions'] and len(cands) >= 2:
            top = sorted(cands, key=lambda c: (-c[0], c[1]))[:2]
            self.decisions.append({'step': eng.step_count, 'spent': eng.spent, 'top': [
                {'bid': bid, 'prims': pr, 'branch': {'direction': eng.branches[bid]['direction'],
                                                     'seed': eng.branches[bid]['seed'], 't': eng.branches[bid]['t'],
                                                     'ys': list(eng.branches[bid]['ys'][-3:])}}
                for _, bid, pr in top]})
        # 6. the value of opening a new direction on a problem: what directions reach (the levels of every branch so
        #    far, an empirical prior), above the problem's best verified value; the upper half of those samples
        prob, v_open = self.open_value(eng)
        if prob is not None and v_open > best_i:
            return ('open', D.imagine(eng.grammar(prob), prob, rng, eng.archive, self.p['k_imagine']))
        return ('advance', best['id'])

    def open_value(self, eng):
        levels = sorted(level(b) for b in eng.branches.values() if b['ys'])
        if len(levels) < 4:
            return None, -math.inf
        top = levels[len(levels) // 2:]
        best_p, best_v = None, -math.inf
        for prob in eng.problem_order():
            target = eng.best_verified.get(prob, 0.0)
            v = sum(max(0.0, x - target) for x in top) / len(top)
            if v > best_v:
                best_p, best_v = prob, v
        return best_p, best_v

    def explore(self, eng):
        rng = eng.rng
        probs = eng.problem_order()
        paused = [b for b in eng.branches.values() if b['paused']]
        leaders = sorted([b for b in eng.branches.values() if b['ys']], key=lambda b: (-level(b), b['id']))[:4]
        derivable = [b for b in leaders if b['direction']['representation'] not in eng.underivable()]
        if self.p['p_derive'] > 0 and derivable and rng.random() < self.p['p_derive']:
            lead = rng.choice(derivable)                     # derive a representation from a leader's
            d = lead['direction']
            return ('derive', (d['problem'], d['representation'], d['method'], d['params']))
        r = rng.random()
        if r < 0.15 and paused:
            b = rng.choice(sorted(paused, key=lambda b: b['id']))
            b['paused'] = False
            b['young_until'] = b['t'] + self.patience(eng)
            self.explore_extra += eng.quantum
            eng.log('reactivate', branch=b['id'])
            return ('advance', b['id'])
        if r < 0.45 and leaders:
            lead = rng.choice(leaders)
            g = eng.grammar(lead['direction']['problem'])
            for _ in range(6):
                d = D.mutate(lead['direction'], g, rng, neighbours=())
                if D.descriptor(d) not in eng.tried:
                    return ('open', d)
        if r < 0.6 and len(leaders) >= 2:
            a, b = rng.sample(leaders, 2)
            d = D.recombine(a['direction'], b['direction'], rng)
            if d is not None and D.descriptor(d) not in eng.tried:
                return ('open', d)
        prob = rng.choice(probs)
        return ('open', D.imagine(eng.grammar(prob), prob, rng, eng.archive, self.p['k_imagine']))


class UniformPolicy:
    """Round robin over open branches; with probability eps a random new direction."""
    name = 'uniform'

    def __init__(self, params=None):
        self.eps = (params or {}).get('eps', 0.2)
        self.turn = 0

    def to_json(self):
        return {'turn': self.turn}

    def load(self, data):
        self.turn = data['turn']

    def observe(self, eng, improved):
        pass

    def choose(self, eng):
        ids = sorted(eng.branches)
        if not ids or eng.rng.random() < self.eps:
            prob = eng.rng.choice(eng.problem_order())
            return ('open', D.sample(eng.grammar(prob), prob, eng.rng))
        self.turn += 1
        return ('advance', ids[self.turn % len(ids)])


class RandomPolicy(UniformPolicy):
    name = 'random'

    def choose(self, eng):
        ids = sorted(eng.branches)
        if not ids or eng.rng.random() < self.eps:
            prob = eng.rng.choice(eng.problem_order())
            return ('open', D.sample(eng.grammar(prob), prob, eng.rng))
        return ('advance', eng.rng.choice(ids))


class UCBPolicy:
    """UCB1 over branches on their current level (mean of the last 3 observations), normalised to the range of
    current levels; with probability eps a random new direction."""
    name = 'ucb'

    def __init__(self, params=None):
        self.eps = (params or {}).get('eps', 0.1)
        self.c = (params or {}).get('c', 1.0)

    def to_json(self):
        return {}

    def load(self, data):
        pass

    def observe(self, eng, improved):
        pass

    def choose(self, eng):
        brs = [b for b in eng.branches.values() if b['ys']]
        if len(brs) < 2 or eng.rng.random() < self.eps:
            prob = eng.rng.choice(eng.problem_order())
            return ('open', D.sample(eng.grammar(prob), prob, eng.rng))
        lv = {b['id']: level(b) for b in brs}
        lo, hi = min(lv.values()), max(lv.values())
        span = (hi - lo) or 1.0
        n = sum(len(b['ys']) for b in brs)
        best = max(brs, key=lambda b: ((lv[b['id']] - lo) / span
                                       + self.c * math.sqrt(2 * math.log(n) / len(b['ys'])), b['id']))
        return ('advance', best['id'])


class HalvingPolicy:
    """Successive halving across directions: a pool of `pool` random directions; each rung gives every live branch
    `rung` quanta (tripled each rung); the best third by current level survive; then a fresh pool."""
    name = 'halving'

    def __init__(self, params=None):
        p = params or {}
        self.pool, self.eta, self.rung0 = p.get('pool', 18), p.get('eta', 3), p.get('rung', 2)
        self.live, self.queue, self.rung, self.to_open = [], [], self.rung0, 0

    def to_json(self):
        return {'live': self.live, 'queue': self.queue, 'rung': self.rung, 'to_open': self.to_open}

    def load(self, data):
        self.live, self.queue, self.rung, self.to_open = data['live'], data['queue'], data['rung'], data['to_open']

    def observe(self, eng, improved):
        pass

    def choose(self, eng):
        if not self.live and not self.to_open:
            self.to_open, self.rung = self.pool, self.rung0
        if self.to_open:
            self.to_open -= 1
            prob = eng.rng.choice(eng.problem_order())
            return ('open', D.sample(eng.grammar(prob), prob, eng.rng))
        if not self.queue:
            # rung finished: keep the best third
            ranked = sorted(self.live, key=lambda i: (-level(eng.branches[i]), i))
            keep = max(1, len(ranked) // self.eta)
            if len(ranked) == 1:
                self.live = []
                return self.choose(eng)
            self.live = ranked[:keep]
            self.rung *= self.eta
            self.queue = [i for i in self.live for _ in range(self.rung)]
        return ('advance', self.queue.pop(0))

    def opened(self, branch_id):
        self.live.append(branch_id)
        self.queue.extend([branch_id] * self.rung)


POLICIES = {'frontier': FrontierPolicy, 'uniform': UniformPolicy, 'random': RandomPolicy, 'ucb': UCBPolicy,
            'halving': HalvingPolicy}
