"""Decision-relevant state features for the Frontier's own allocator, found by counterexamples (research plane;
Foundry G4, `docs/OMEGA_FOUNDRY.md` §3, B20_R172).

The allocator advances the mature branch with the largest index I = max(0, hi - target) + lam_lp LP + lam_con con.
When two branches look alike to I but are not alike in what advancing them yields, I is missing a distinction:
ARA's SENSE_BLIND class, turned on the engine's own controller. G4 finds such distinctions from the engine's own
decisions:
  1. **record** (`FrontierPolicy` with `log_decisions`): at each exploitation decision, the two leading candidates
     and their PRIMITIVES (statistics of the branch's own history and forecast, below);
  2. **replay** (`replay_gain`): from the decision's state, advance each of the two branches alone by k quanta
     through the domain's public `step` (a pure function of the branch's direction, seed and compute in the planted
     world), and measure the gain in its level. This is an experiment the engine pays for: 2 k quanta per decision,
     returned so that a study charges it;
  3. **propose** (`propose`): search the feature language (each primitive, and every difference, product and ratio
     of two) for the expression e and weight w for which ranking by I + w e agrees best with the replays. The whole
     search is cross-validated (two folds over decisions: search on one, score on the other), and a feature is
     proposed only if that held-out agreement beats I alone by MIN_GAIN with a one-sided z of at least Z_MIN
     (weighted pairs, paired with I alone);
  4. a proposed feature enters the index as the policy parameter `state_feature` = {'expr', 'weight'}; whether it
     is kept is the kernel's decision on held-out worlds at matched total compute (B20_R172), never this module's.

PRIMITIVES (all from what the engine itself sees):
  gain, lp, con, index     the index's own terms and value
  level, hi, mid, width    the branch's level (mean of its last 3 observations) and its forecast (hi - lo = width)
  head                     mid - level: how much more the forecast expects
  t, n, frac               the branch's compute, its number of points, t / H
  slope4, slope16, curv    least-squares slopes over the last 4 and 16 points, and their difference
  since                    compute since the branch's running maximum last rose by more than 1% of its range
  noise                    the standard deviation of the branch's successive differences over its last 16 points
"""
import json
import math

import numpy as np

PRIMS = ('gain', 'lp', 'con', 'index', 'level', 'hi', 'mid', 'width', 'head', 't', 'n', 'frac', 'slope4', 'slope16',
         'curv', 'since', 'noise')
OPS = ('-', '*', '/')
MIN_GAIN = 0.02            # held-out agreement a feature must add to be proposed
Z_MIN = 1.645              # and its one-sided z over the held-out pairs (weighted, paired with the index alone)
WEIGHTS = tuple(float(x) for x in (-4, -2, -1, -0.5, -0.25, -0.1, 0.1, 0.25, 0.5, 1, 2, 4))


def _slope(ts, ys):
    if len(ts) < 3:
        return 0.0
    t, y = np.asarray(ts, float), np.asarray(ys, float)
    tc = t - t.mean()
    den = float((tc ** 2).sum())
    return 0.0 if den == 0 else float((tc * (y - y.mean())).sum() / den)


def primitives(br, fc, target, gain, lp, con, index, H):
    ts, ys = br['ts'], br['ys']
    level = sum(ys[-3:]) / len(ys[-3:]) if ys else 0.0
    s4, s16 = _slope(ts[-4:], ys[-4:]), _slope(ts[-16:], ys[-16:])
    since = 0.0
    if ys:
        rng = (max(ys) - min(ys)) or 1.0
        run, last = -math.inf, ts[0]
        for t, y in zip(ts, ys):
            if y > run + 0.01 * rng:
                run, last = y, t
        since = float(ts[-1] - last)
    d = np.diff(np.asarray(ys[-17:], float))
    lo, mid, hi = fc['lo'], fc['mid'], fc['hi']
    fin = lambda x: float(x) if math.isfinite(x) else 0.0          # noqa: E731
    return {'gain': fin(gain), 'lp': fin(lp), 'con': fin(con), 'index': fin(index), 'level': fin(level),
            'hi': fin(hi), 'mid': fin(mid), 'width': fin(hi - lo) if math.isfinite(hi - lo) else 0.0,
            'head': fin(mid - level), 't': float(br['t']), 'n': float(len(ts)), 'frac': fin(br['t'] / H) if H else 0.0,
            'slope4': s4, 'slope16': s16, 'curv': s4 - s16, 'since': since,
            'noise': float(d.std()) if len(d) >= 2 else 0.0}


def check(expr):
    if isinstance(expr, str):
        return expr in PRIMS
    return (isinstance(expr, list) and len(expr) == 3 and expr[0] in OPS and isinstance(expr[1], str)
            and isinstance(expr[2], str) and expr[1] in PRIMS and expr[2] in PRIMS)


def evaluate(expr, prims):
    if not check(expr):
        raise ValueError(f'not a state feature: {expr!r}')
    if isinstance(expr, str):
        return prims[expr]
    op, a, b = expr[0], prims[expr[1]], prims[expr[2]]
    if op == '-':
        return a - b
    if op == '*':
        return a * b
    return a / b if abs(b) > 1e-12 else 0.0


def language():
    """Every feature expression: the primitives, then every ordered pair under '-' and '/', unordered under '*'."""
    out = list(PRIMS)
    for i, a in enumerate(PRIMS):
        for j, b in enumerate(PRIMS):
            if a == b:
                continue
            out.append(['-', a, b])
            out.append(['/', a, b])
            if i < j:
                out.append(['*', a, b])
    return out


def replay_gain(domain, br, k, quantum):
    """The gain in level from advancing the branch alone by k quanta from its present state, through the domain's
    public step (no engine state changes). Returns (gain, compute used)."""
    d, seed, t = br['direction'], br['seed'], br['t']
    ys = list(br['ys'][-3:])
    base = sum(ys) / len(ys) if ys else 0.0
    future = []
    for _ in range(k):
        pts, _ = domain.step(d['problem'], d, seed, t, quantum)
        for t1, y in pts:
            t = t1
            future.append(y)
    after = sum(future[-3:]) / len(future[-3:]) if future else base
    return after - base, k * quantum


def counterexamples(domain, decisions, k, quantum, max_pairs=None):
    """Replay the two leading candidates of each logged decision: [{'a': prims, 'b': prims, 'gain_a', 'gain_b'}],
    and the compute the replays used. Branch states are the ones logged at decision time."""
    pairs, used = [], 0
    for dec in decisions[:max_pairs] if max_pairs else decisions:
        if len(dec['top']) < 2:
            continue
        a, b = dec['top'][0], dec['top'][1]
        ga, ca = replay_gain(domain, a['branch'], k, quantum)
        gb, cb = replay_gain(domain, b['branch'], k, quantum)
        used += ca + cb
        pairs.append({'a': a['prims'], 'b': b['prims'], 'gain_a': ga, 'gain_b': gb, 'step': dec['step']})
    return pairs, used


def _arrays(pairs, expr=None):
    """(index_a, index_b, feature_a, feature_b, weight, b_better) as arrays over the pairs with a gain difference."""
    keep = [p for p in pairs if p['gain_b'] != p['gain_a']]
    ia = np.array([p['a']['index'] for p in keep], float)
    ib = np.array([p['b']['index'] for p in keep], float)
    if expr is None:
        fa = fb = np.zeros(len(keep))
    else:
        fa = np.array([evaluate(expr, p['a']) for p in keep], float)
        fb = np.array([evaluate(expr, p['b']) for p in keep], float)
    w = np.array([abs(p['gain_b'] - p['gain_a']) for p in keep], float)
    better = np.array([p['gain_b'] > p['gain_a'] for p in keep], bool)
    return ia, ib, fa, fb, w, better


def _right(arr, weight):
    """Per pair: 1 if the ranking puts the branch with the larger replayed gain first, 0.5 on a tie, else 0."""
    ia, ib, fa, fb, w, better = arr
    sa, sb = ia + weight * fa, ib + weight * fb
    right = np.where(better, sb > sa, sa > sb).astype(float)
    return np.where(sa == sb, 0.5, right)


def _agree(arr, weight):
    w = arr[4]
    if w.sum() == 0:
        return 0.5
    return float((w * _right(arr, weight)).sum() / w.sum())


def agreement(pairs, expr=None, weight=0.0):
    """The share of pairs (weighted by |gain difference|) in which ranking by index + weight x feature puts the branch
    with the larger replayed gain first; ties count half."""
    return _agree(_arrays(pairs, expr), weight)


def _scale(arr):
    """A typical size of the feature's difference within pairs, relative to the index's, so that WEIGHTS are relative
    to the index's own scale."""
    ia, ib, fa, fb, _, _ = arr
    mi = float(np.median(np.abs(ia - ib))) if len(ia) else 0.0
    me = float(np.median(np.abs(fa - fb))) if len(fa) else 0.0
    if me <= 1e-12:
        return 0.0
    return mi / me if mi > 1e-12 else 1.0 / me


def _fit(arr):
    s = _scale(arr)
    if s == 0.0:
        return None
    return s * max(WEIGHTS, key=lambda c: (_agree(arr, c * s), -abs(c)))


def _search(pairs, lang):
    """The (agreement, expr, weight) with the best agreement on these pairs (ties to the earlier expression)."""
    best = None
    for expr in lang:
        arr = _arrays(pairs, expr)
        w = _fit(arr)
        if w is None:
            continue
        a = _agree(arr, w)
        if best is None or a > best[0] + 1e-12:
            best = (a, expr, w)
    return best


def propose(pairs, folds=2):
    """A feature for the index, if the whole search procedure, cross-validated, beats the index alone by MIN_GAIN in
    held-out agreement: {'expr', 'weight', 'held_out', 'baseline', 'searched', 'folds'} or None.

    Each fold searches the language on the other folds' pairs only and is scored on its own, so the held-out estimate
    is of the procedure (search included), not of the best of 697 expressions on the held-out pairs. The feature
    returned is the procedure's choice on all pairs. Folds split the pairs by decision order."""
    if len(pairs) < 2 * folds:
        return None
    parts = [pairs[i::folds] for i in range(folds)]
    lang = language()
    base = float(np.mean([agreement(p) for p in parts]))
    held, chosen, diffs, weights = [], [], [], []
    for f in range(folds):
        train = [x for g, part in enumerate(parts) if g != f for x in part]
        got = _search(train, lang)
        if got is None:
            return None
        arr = _arrays(parts[f], got[1])
        held.append(_agree(arr, got[2]))
        chosen.append(got[1])
        diffs.append(_right(arr, got[2]) - _right(arr, 0.0))
        weights.append(arr[4])
    held_out = float(np.mean(held))
    d, w = np.concatenate(diffs), np.concatenate(weights)
    if w.sum() == 0:
        return None
    mean = float((w * d).sum() / w.sum())
    n_eff = float(w.sum() ** 2 / (w ** 2).sum())
    var = float((w * (d - mean) ** 2).sum() / w.sum())
    z = mean / math.sqrt(var / n_eff) if var > 0 else (math.inf if mean > 0 else 0.0)
    if held_out < base + MIN_GAIN or z < Z_MIN:
        return None
    _, expr, w = _search(pairs, lang)
    return {'expr': expr, 'weight': float(w), 'held_out': held_out, 'baseline': base, 'searched': len(lang),
            'folds': chosen, 'z': z}


def canonical(feature):
    return json.dumps(feature, sort_keys=True) if feature else None
