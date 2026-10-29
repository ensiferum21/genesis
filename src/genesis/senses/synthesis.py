"""Sense synthesis by search, and a library of composite primitives (Batch R2, second part; research plane;
`docs/OMEGA_RECURSIVE_INVENTION.md` §4.1).

**The task a sense serves.** A decision over instances: n instances, K choices, and a score matrix M (n x K, larger
is better), for example each engine's relative cut on each graph. A sense x (one number per instance) is worth what
the best one-threshold rule over it earns: choose c_lo below a threshold and c_hi above it (`stump`). Its VALUE is
that rule's mean per-instance score under k-fold cross-validation by instance (fit on k - 1 folds, score on the
held-out fold), so that a sense is not credited for fitting noise. The baseline is the best single choice for every
instance, cross-validated the same way; the oracle is the per-instance best.

**The search** (`synthesise`): a steady-state evolutionary search over the sense language (`senses/graph.py`: its
random senses, mutations and crossovers, which keep types and bounds), population POP, tournament selection, and a
budget counted in candidate senses evaluated. Every evaluation is charged: SENSE_UNIT per expression node per
instance (`charges`). The result names the winner, its cross-validated value, the baseline, the oracle and the
history. The winner's value is the search's own estimate: a study must measure it again on instances the search never
saw (the winner's curse).

**The library** (`Library`, `learn`, `gate`). A composite primitive is a typed subtree that recurred in the winners
of independent searches (at least MIN_SUPPORT of them). It is named by its digest and used as a leaf ['lib', name]:
it costs one node of description length, so later searches can reach larger senses within the language's size bound
(MAX_SIZE on the surface tree; at most EXPANDED_MAX nodes once expanded). A library is an immutable value with a
version and a parent. `learn` only proposes entries; `gate` admits a proposed library only if searches with it beat
searches without it, at the same budget, on tasks the library was not learned from (held-out values, paired by task
and seed). Nothing here decides a study's claim.
"""
import hashlib
import json
import math
import random

import numpy as np

from . import graph as SG

SENSE_UNIT = 0.002
POP, TOURNAMENT, P_CROSS, P_LIB = 24, 3, 0.25, 0.2
FOLDS = 4
MIN_SUPPORT = 2
EXPANDED_MAX = 4 * SG.MAX_SIZE


def _digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()


# --------------------------------------------------------------------------------------------- the library

class Library:
    def __init__(self, entries=(), parent=None):
        self.entries = {e['name']: dict(e) for e in entries}
        self.parent = parent
        self.version = _digest([parent, sorted(self.entries)])[:16]

    def __len__(self):
        return len(self.entries)

    def type_of(self, name):
        return self.entries[name]['type']

    def extend(self, new):
        return Library(list(self.entries.values()) + [e for e in new if e['name'] not in self.entries],
                       parent=self.version)

    def to_json(self):
        return {'version': self.version, 'parent': self.parent, 'entries': [self.entries[k] for k in sorted(self.entries)]}


EMPTY = Library()


def _is_lib(t):
    return isinstance(t, list) and len(t) == 2 and t[0] == 'lib'


def expand(t, lib=EMPTY):
    if _is_lib(t):
        if t[1] not in lib.entries:
            raise ValueError(f'unknown library entry {t[1]!r}')
        return expand(lib.entries[t[1]]['expr'], lib)
    if isinstance(t, list):
        return [t[0]] + [expand(a, lib) for a in t[1:]]
    return t


def type_of(t, lib=EMPTY):
    if _is_lib(t):
        if t[1] not in lib.entries:
            raise ValueError(f'unknown library entry {t[1]!r}')
        return lib.type_of(t[1])
    if isinstance(t, list) and t and t[0] in SG.OPS:
        out, args = SG.OPS[t[0]]
        if len(t) != 1 + len(args):
            raise ValueError(f'{t[0]} takes {len(args)} arguments')
        for a, want in zip(t[1:], args):
            if type_of(a, lib) != want:
                raise ValueError(f'{t[0]} expects {want}')
        return out
    return SG.type_of(t)


def check(t, lib=EMPTY):
    """None, or why t is not a scalar sense of the language with the library: typed, a surface of at most MAX_SIZE
    nodes and depth MAX_DEPTH, and at most EXPANDED_MAX nodes once expanded."""
    try:
        if type_of(t, lib) != 'S':
            return 'a sense is scalar-valued'
    except ValueError as e:
        return str(e)
    if SG.size(t) > SG.MAX_SIZE or SG.depth(t) > SG.MAX_DEPTH:
        return f'at most {SG.MAX_SIZE} nodes and depth {SG.MAX_DEPTH} on the surface'
    if SG.size(expand(t, lib)) > EXPANDED_MAX:
        return f'at most {EXPANDED_MAX} nodes expanded'
    return None


def evaluate(t, ctx, lib=EMPTY):
    why = check(t, lib)
    if why:
        raise ValueError(why)
    with np.errstate(all='ignore'):
        v = float(SG._ev(expand(t, lib), ctx))
    return v if math.isfinite(v) else 0.0


def values(t, contexts, lib=EMPTY, charges=None):
    """The sense on every instance (contexts: `SG.Context`s), charged SENSE_UNIT x expanded size per instance."""
    if charges is not None:
        charges['sense'] = charges.get('sense', 0.0) + SENSE_UNIT * SG.size(expand(t, lib)) * len(contexts)
    return np.array([evaluate(t, c, lib) for c in contexts])


# --------------------------------------------------------------------------------------------- the decision

def stump(x, M):
    """(theta, total) of the best one-threshold rule over x: theta = (threshold, c_lo, c_hi); a global choice if no
    split helps (threshold +inf)."""
    n, K = M.shape
    tot = M.sum(0)
    c = int(np.argmax(tot))
    best = ((math.inf, c, c), float(tot[c]))
    order = np.argsort(x, kind='stable')
    xs, cum = x[order], np.cumsum(M[order], axis=0)
    for p in range(n - 1):
        if xs[p + 1] <= xs[p]:
            continue
        left = cum[p]
        v = float(left.max() + (tot - left).max())
        if v > best[1] + 1e-12:
            best = (((xs[p] + xs[p + 1]) / 2, int(np.argmax(left)), int(np.argmax(tot - left))), v)
    return best


def act(theta, x):
    t, lo, hi = theta
    return np.where(x <= t, lo, hi)


def folds(n, k=FOLDS, seed=0):
    idx = np.random.default_rng(seed).permutation(n)
    return [np.sort(idx[i::k]) for i in range(k)]


def cv_value(x, M, fs):
    """The stump's mean held-out per-instance score over the folds."""
    out = np.empty(len(x))
    for f in fs:
        train = np.setdiff1d(np.arange(len(x)), f)
        theta, _ = stump(x[train], M[train])
        out[f] = M[f, act(theta, x[f])]
    return float(out.mean())


def baseline(M, fs):
    out = np.empty(len(M))
    for f in fs:
        train = np.setdiff1d(np.arange(len(M)), f)
        out[f] = M[f, int(np.argmax(M[train].sum(0)))]
    return float(out.mean())


def oracle(M):
    return float(M.max(axis=1).mean())


# --------------------------------------------------------------------------------------------- the search

def _random(rng, lib):
    t = SG.random_sense(rng)
    return _lib_insert(t, rng, lib) if len(lib) and rng.random() < P_LIB else t


def _lib_insert(t, rng, lib):
    """Replace a random subtree by a library leaf of the same type (if one fits the bounds)."""
    paths = list(SG._paths(t))
    rng.shuffle(paths)
    names = sorted(lib.entries)
    for path, sub in paths:
        try:
            ty = type_of(sub, lib)
        except ValueError:
            continue
        fits = [n for n in names if lib.type_of(n) == ty]
        if not fits:
            continue
        c = SG._replace(t, path, ['lib', rng.choice(fits)])
        if check(c, lib) is None:
            return c
    return t


def _mutate(t, rng, lib):
    if len(lib) and rng.random() < P_LIB:
        c = _lib_insert(t, rng, lib)
        if c != t:
            return c
    for _ in range(20):
        c = SG.mutate(t, rng) if not _has_lib(t) else _mutate_keep(t, rng, lib)
        if check(c, lib) is None:
            return c
    return _random(rng, lib)


def _has_lib(t):
    return _is_lib(t) or (isinstance(t, list) and any(_has_lib(a) for a in t[1:]))


def _mutate_keep(t, rng, lib):
    """A mutation of a tree with library leaves: a random non-library subtree regrown, library leaves kept."""
    paths = [(p, s) for p, s in SG._paths(t) if not _inside_lib(t, p)]
    path, sub = rng.choice(paths)
    ty = type_of(sub, lib)
    return SG._replace(t, path, SG.random_tree(ty, rng, len(path), max_depth=min(SG.MAX_DEPTH - 1, len(path) + 2)))


def _inside_lib(t, path):
    node = t
    for i in path:
        if _is_lib(node):
            return True
        node = node[i]
    return _is_lib(node) and False


def _crossover(a, b, rng, lib):
    for _ in range(20):
        pa, sa = rng.choice(list(SG._paths(a)))
        try:
            ta = type_of(sa, lib)
        except ValueError:
            continue
        cands = []
        for p, s in SG._paths(b):
            try:
                if type_of(s, lib) == ta:
                    cands.append(s)
            except ValueError:
                pass
        if not cands:
            continue
        c = SG._replace(a, pa, rng.choice(cands))
        if check(c, lib) is None:
            return c
    return a


def synthesise(contexts, M, budget, seed=0, lib=EMPTY, k=FOLDS):
    """Search the sense language (with the library) for the sense whose stump earns most under cross-validation.
    Returns {'sense', 'value', 'baseline', 'oracle', 'evaluated', 'charges', 'history'}."""
    M = np.asarray(M, dtype=np.float64)
    rng = random.Random(f'synthesise|{seed}')
    fs = folds(len(M), k, seed)
    charges, cache, history = {}, {}, []

    def score(t):
        key = json.dumps(t, sort_keys=True)
        if key not in cache:
            cache[key] = cv_value(values(t, contexts, lib, charges), M, fs)
            history.append(max(cache.values()))
        return cache[key]

    pop = []
    while len(pop) < min(POP, budget):
        t = _random(rng, lib)
        pop.append((score(t), t))
    while len(cache) < budget:
        def pick():
            return max(rng.sample(pop, min(TOURNAMENT, len(pop))), key=lambda x: x[0])[1]
        child = _crossover(pick(), pick(), rng, lib) if rng.random() < P_CROSS else _mutate(pick(), rng, lib)
        before = len(cache)
        v = score(child)
        if len(cache) == before:                      # a repeat costs nothing and changes nothing
            if len(history) > 50 * budget:
                break
            continue
        worst = min(range(len(pop)), key=lambda i: (pop[i][0], -i))
        if v > pop[worst][0]:
            pop[worst] = (v, child)
    best = max(pop, key=lambda x: (x[0], -SG.size(x[1])))
    return {'sense': best[1], 'value': best[0], 'baseline': baseline(M, fs), 'oracle': oracle(M),
            'evaluated': len(cache), 'charges': charges, 'history': history[::max(1, len(history) // 50)]}


# --------------------------------------------------------------------------------------------- learning the library

def subtrees(t, lib=EMPTY):
    """Every typed subtree of t with at least 2 nodes, the whole sense included (library leaves stay leaves)."""
    out = []
    for _, s in SG._paths(t):
        if isinstance(s, list) and not _is_lib(s) and SG.size(s) >= 2:
            try:
                out.append((type_of(s, lib), s))
            except ValueError:
                pass
    return out


def learn(winners, lib=EMPTY, min_support=MIN_SUPPORT, max_new=4):
    """Proposed entries: subtrees recurring in at least `min_support` distinct winners, most supported first, then
    largest; at most `max_new`. A subtree contained in a larger proposed one with the same support is dropped."""
    support = {}
    for i, w in enumerate(winners):
        for ty, s in subtrees(w, lib):
            key = json.dumps(s, sort_keys=True)
            support.setdefault(key, {'type': ty, 'expr': s, 'winners': set()})['winners'].add(i)
    cands = [v for v in support.values() if len(v['winners']) >= min_support]
    cands.sort(key=lambda v: (-len(v['winners']), -SG.size(v['expr']), json.dumps(v['expr'], sort_keys=True)))
    chosen = []
    for v in cands:
        ks = json.dumps(v['expr'], sort_keys=True)
        if any(ks in json.dumps(c['expr'], sort_keys=True) and len(c['winners']) == len(v['winners']) for c in chosen):
            continue
        chosen.append(v)
        if len(chosen) >= max_new:
            break
    return [{'name': 'c_' + _digest(v['expr'])[:10], 'type': v['type'], 'expr': v['expr'],
             'size': SG.size(expand(v['expr'], lib)), 'support': len(v['winners']),
             'lineage': {'from': 'winners', 'parent_library': lib.version}} for v in chosen]


def gate(lib_old, lib_new, tasks, budget, seeds):
    """Admit lib_new only if searches with it beat searches with lib_old at the same budget on `tasks` (each
    (contexts, M_train, contexts_test, M_test), none used to learn it): the winner's held-out stump value, paired by
    task and seed. Returns {'admitted', 'wins', 'losses', 'mean_gain', 'pairs'}."""
    pairs = []
    for ti, (ctx_tr, M_tr, ctx_te, M_te) in enumerate(tasks):
        M_tr, M_te = np.asarray(M_tr, float), np.asarray(M_te, float)
        for s in seeds:
            vals = []
            for lib in (lib_old, lib_new):
                r = synthesise(ctx_tr, M_tr, budget, seed=s, lib=lib)
                x_tr, x_te = values(r['sense'], ctx_tr, lib), values(r['sense'], ctx_te, lib)
                theta, _ = stump(x_tr, M_tr)
                vals.append(float(M_te[np.arange(len(M_te)), act(theta, x_te)].mean()))
            pairs.append({'task': ti, 'seed': s, 'old': vals[0], 'new': vals[1]})
    d = [p['new'] - p['old'] for p in pairs]
    wins, losses = sum(x > 1e-12 for x in d), sum(x < -1e-12 for x in d)
    mean = float(np.mean(d)) if d else 0.0
    return {'admitted': mean > 0 and wins > losses, 'wins': wins, 'losses': losses, 'mean_gain': mean, 'pairs': pairs}
