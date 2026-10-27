"""Genesis's own conjectures: upper bounds on the Laplacian spectral radius posed from its own data (research plane;
F5, `docs/OMEGA_FRONTIER.md` §5.6).

**Data** (the teaching ban, §3.3): graphs Genesis generates itself with the attack representations' random draws
(edge bits, trees, bounded degree, Gamma programs) at small n. There is no curated list, and the source is logged.
**Candidates**: local bounds in the Brankov-Hansen-Stevanovic form, mu <= max over vertices of f(d, m), built from a
small grammar:
    f = (a*X + b*Y) / c,   f = sqrt((a*X2 + b*Y2) / c),   f = root4((a*X4 + b*Y4) / c)
where X, Y range over the monomials in d and m of degree 1 (2 or 4 under the roots), with a, b in 1..8 and c in
{1, 2, 4}. Every candidate is homogeneous of degree 1.
**Kept** (TxGraffiti's practice, Davila 2024): a candidate that
  * holds on every data graph (in floating point, tolerance 1e-9);
  * is sharp on at least one (touch number > 0: equality within 1e-9);
  * is not dominated: no kept candidate is at most it on every data graph with a strictly smaller value somewhere.
Formulas that agree on random points are one conjecture (the first kept). Kept candidates are conjectures: by
Pepper's rule each is assumed false until an attack at the full budget fails,
and none is ever reported as a theorem. A conjecture equal on random points to a known bound (the kernel's sealed
set, or a classical one) is labelled a rediscovery by the kernel, not here.
"""
import itertools
import math

import numpy as np

from . import attack as AT
from . import expr as E

DEG1 = ('d', 'm')
DEG2 = ('d^2', 'm^2', 'd*m', 'd^3/m', 'm^3/d')
DEG4 = ('d^4', 'm^4', 'd^2*m^2', 'd^3*m', 'd*m^3')
COEF = tuple(range(1, 9))
DENOM = (1, 2, 4)
TOL = 1e-9


def data(rng, count=600, n_values=(4, 5, 6, 7, 8, 10)):
    """[(adjacency, mu, degrees, m)]: Genesis's own graphs (no isolated vertex)."""
    out = []
    reps = ('edges', 'tree', 'bounded', 'gamma')
    tries = 0
    while len(out) < count and tries < count * 20:
        tries += 1
        n = int(rng.choice(n_values))
        rep = AT.REPRESENTATIONS[reps[tries % len(reps)]](n)
        A = rep.graph(rep.random(rng))
        if A is None or len(A) < 2:
            continue
        deg = A.sum(axis=1).astype(float)
        if deg.min() == 0:
            continue
        m = (A @ deg) / deg
        L = (np.diag(A.sum(axis=1)) - A).astype(float)
        mu = float(np.linalg.eigvalsh(L)[-1])
        out.append((A, mu, deg, m))
    return out


def grammar():
    """Every candidate formula text of the grammar (deduplicated)."""
    seen, out = set(), []
    for X, Y in itertools.combinations_with_replacement(DEG1, 2):
        for a, b, c in itertools.product(COEF, COEF, DENOM):
            out.append(f'({a}*{X} + {b}*{Y})/{c}' if X != Y else f'({a + b}*{X})/{c}')
    for wrap, monos in (('sqrt', DEG2), ('root4', DEG4)):
        for X, Y in itertools.combinations(monos, 2):
            for a, b, c in itertools.product(COEF, COEF, DENOM):
                out.append(f'{wrap}(({a}*{X} + {b}*{Y})/{c})')
    res = []
    for f in out:
        key = E.render(E.parse(f, 'vertex'))
        if key not in seen:
            seen.add(key)
            res.append(f)
    return res


def values(formula, graphs):
    fn = E.compile_numpy(E.parse(formula, 'vertex'))
    out = np.empty(len(graphs))
    for i, (A, mu, deg, m) in enumerate(graphs):
        v = fn({'d': deg, 'm': m})
        v = np.broadcast_to(np.asarray(v, float), deg.shape)
        out[i] = np.nan if np.isnan(v).any() else float(v.max())
    return out


def conjectures(graphs, limit=None):
    """[(formula, touch number)] kept by the rules above, sharpest first."""
    mus = np.array([g[1] for g in graphs])
    kept = []
    for f in grammar():
        v = values(f, graphs)
        if np.isnan(v).any() or (v < mus - TOL).any():
            continue
        touch = int((np.abs(v - mus) <= TOL).sum())
        if touch == 0:
            continue
        kept.append((f, touch, v))
    # dominance: drop f if some other kept g is <= f everywhere and < somewhere
    out, reps = [], []
    for i, (f, t, v) in enumerate(kept):
        dominated = any((w <= v + TOL).all() and (w < v - TOL).any() for j, (g, s, w) in enumerate(kept) if j != i)
        if dominated or any(equivalent(f, g) for g in reps):          # one formula per function
            continue
        reps.append(f)
        out.append((f, t))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out[:limit] if limit else out


def equivalent(f, g, kind='vertex', rng=None, points=200):
    """True if two formulas agree on random points (a rediscovery check, for the kernel's use)."""
    rng = rng or np.random.default_rng(0)
    a, b = E.compile_numpy(E.parse(f, kind)), E.compile_numpy(E.parse(g, kind))
    names = E.VERTEX_VARS if kind == 'vertex' else E.EDGE_VARS
    env = {v: rng.uniform(0.5, 30, points) for v in names}
    x, y = np.asarray(a(env), float), np.asarray(b(env), float)
    ok = ~(np.isnan(x) | np.isnan(y))
    return bool(ok.sum() > points // 2 and np.allclose(x[ok], y[ok], rtol=1e-9, atol=1e-9))
