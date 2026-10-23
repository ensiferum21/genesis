"""Baselines for the hidden-confounder benchmark, written from their papers (B20_R117). None of them is Genesis's.

  * `empty`: no edges (the floor).
  * `pc`: the PC algorithm, order-independent ("PC-stable", Colombo and Maathuis 2014), with Fisher's z test of
    partial correlation (Spirtes, Glymour and Scheines 2000; Kalisch and Buehlmann 2007), unshielded colliders
    oriented by the separating sets, then Meek's rules R1-R3 (Meek 1995). An edge that two colliders orient both
    ways is left undirected. PC assumes no hidden variables.
  * `pc_oracle`: the same algorithm told the true conditional independences among the observed variables
    (d-separation in the planted DAG): what PC would answer with infinite data. Its errors are the hidden
    variables' alone.
  * `lingam`: DirectLiNGAM (Shimizu et al. 2011) with the pairwise likelihood-ratio measure of Hyvaerinen and Smith
    (2013) and their maximum-entropy approximation of differential entropy; then each variable is regressed on the
    variables before it and a coefficient kept if its two-sided t test has p < alpha. It assumes no hidden variables
    and non-Gaussian noise.

Data from several environments are centred per environment and pooled: the naive use, which assumes one
distribution. A method gets the view {'p', 'environments'} and returns an answer in `admg`'s format.
"""
from itertools import combinations
import math

import numpy as np
from scipy import stats

ALPHA = 0.01


def pooled(view):
    return np.vstack([np.asarray(X) - np.asarray(X).mean(axis=0) for X in view['environments']])


def empty(view, **_):
    return {'directed': [], 'undirected': [], 'bidirected': []}


# ----------------------------------------------------------------------------------------------------------- PC

def fisher_z(C, n):
    """A test indep(i, j, S) -> bool from the correlation matrix C of n samples."""
    def indep(i, j, S, alpha):
        idx = [i, j, *S]
        P = np.linalg.pinv(C[np.ix_(idx, idx)])
        r = -P[0, 1] / math.sqrt(abs(P[0, 0] * P[1, 1]))
        r = min(0.999999, max(-0.999999, r))
        z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(max(1, n - len(S) - 3))
        return 2 * (1 - stats.norm.cdf(abs(z))) > alpha
    return indep


def skeleton(p, indep, alpha):
    adj = {i: set(range(p)) - {i} for i in range(p)}
    sepset = {}
    level = 0
    while True:
        snap = {i: set(adj[i]) for i in range(p)}
        tested = False
        for i in range(p):
            for j in sorted(snap[i]):
                if j not in adj[i]:
                    continue
                others = sorted(snap[i] - {j})
                if len(others) < level:
                    continue
                tested = True
                for S in combinations(others, level):
                    if indep(i, j, S, alpha):
                        adj[i].discard(j)
                        adj[j].discard(i)
                        sepset[(i, j)] = sepset[(j, i)] = set(S)
                        break
        if not tested:
            return adj, sepset
        level += 1


def orient(p, adj, sepset):
    """Colliders, then Meek's R1-R3. Returns (directed, undirected) edge lists."""
    arrow = set()                       # (a, b): an arrowhead at b on a - b
    for k in range(p):
        for i, j in combinations(sorted(adj[k]), 2):
            if j not in adj[i] and k not in sepset.get((i, j), set()):
                arrow.add((i, k))
                arrow.add((j, k))
    both = {(a, b) for (a, b) in arrow if (b, a) in arrow}
    arrow -= both                       # conflicting colliders: left undirected

    def directed(a, b):
        return (a, b) in arrow and (b, a) not in arrow

    def undirected(a, b):
        return b in adj[a] and (a, b) not in arrow and (b, a) not in arrow and (a, b) not in both
    changed = True
    while changed:
        changed = False
        for a in range(p):
            for b in sorted(adj[a]):
                if not undirected(a, b):
                    continue
                r1 = any(directed(c, a) and b not in adj[c] and c != b for c in adj[a])
                r2 = any(directed(a, c) and directed(c, b) for c in adj[a] & adj[b])
                r3 = any(directed(c, b) and directed(d, b) and undirected(a, c) and undirected(a, d) and d not in adj[c]
                         for c, d in combinations(sorted(adj[a] & adj[b]), 2))
                if r1 or r2 or r3:
                    arrow.add((a, b))
                    changed = True
    d, u = [], []
    for a in range(p):
        for b in sorted(adj[a]):
            if directed(a, b):
                d.append([a, b])
            elif a < b and not directed(b, a):
                u.append([a, b])
    return d, u


def _acyclic_part(p, d, u):
    """Directed edges that would close a cycle (possible with conflicting colliders) are made undirected."""
    from .admg import _cyclic
    keep = []
    for e in d:
        if _cyclic(p, [tuple(x) for x in keep + [e]]):
            u.append(sorted(e))
        else:
            keep.append(e)
    return keep, sorted(u)


def pc(view, alpha=ALPHA, **_):
    X = pooled(view)
    p = view['p']
    adj, sepset = skeleton(p, fisher_z(np.corrcoef(X, rowvar=False), X.shape[0]), alpha)
    d, u = _acyclic_part(p, *orient(p, adj, sepset))
    return {'directed': d, 'undirected': u, 'bidirected': []}


def pc_oracle(view, truth=None, **_):
    from .admg import d_separated, full_dag
    if truth is None:
        raise ValueError('the oracle needs the truth')
    parents, p = full_dag(truth), truth['p']
    adj, sepset = skeleton(p, lambda i, j, S, alpha: d_separated(parents, i, j, S), None)
    d, u = _acyclic_part(p, *orient(p, adj, sepset))
    return {'directed': d, 'undirected': u, 'bidirected': []}


# ---------------------------------------------------------------------------------------------------- DirectLiNGAM

K1, K2, GAMMA = 79.047, 7.4129, 0.37457


def _entropy(u):
    """Maximum-entropy approximation of the differential entropy of a standardised variable (Hyvaerinen 1998)."""
    return ((1 + math.log(2 * math.pi)) / 2 - K1 * (np.mean(np.log(np.cosh(u))) - GAMMA) ** 2
            - K2 * (np.mean(u * np.exp(-u ** 2 / 2))) ** 2)


def _residual(xi, xj):
    return xi - (np.cov(xi, xj, bias=True)[0, 1] / np.var(xj)) * xj


def _std(x):
    return (x - x.mean()) / x.std()


def causal_order(X):
    """DirectLiNGAM's order with the pairwise likelihood-ratio measure."""
    X = np.array(X, dtype=float)
    p = X.shape[1]
    remaining, order = list(range(p)), []
    while len(remaining) > 1:
        Z = np.column_stack([_std(X[:, k]) for k in remaining])
        scores = []
        for a in range(len(remaining)):
            m = 0.0
            for b in range(len(remaining)):
                if a == b:
                    continue
                xi, xj = Z[:, a], Z[:, b]
                ri_j, rj_i = _residual(xi, xj), _residual(xj, xi)
                diff = (_entropy(xj) + _entropy(_std(ri_j))) - (_entropy(xi) + _entropy(_std(rj_i)))
                m += min(0.0, diff) ** 2
            scores.append(-m)
        k = remaining[int(np.argmax(scores))]
        order.append(k)
        for b in remaining:                 # regress the chosen variable out of the rest
            if b != k:
                X[:, b] = _residual(X[:, b], X[:, k])
        remaining.remove(k)
    return order + remaining


def lingam(view, alpha=ALPHA, **_):
    X = pooled(view)
    n, p = X.shape
    order = causal_order(X)
    d = []
    for pos in range(1, p):
        j, pre = order[pos], order[:pos]
        A = X[:, pre]
        coef, *_ = np.linalg.lstsq(A, X[:, j], rcond=None)
        resid = X[:, j] - A @ coef
        dof = max(1, n - len(pre))
        s2 = resid @ resid / dof
        cov = s2 * np.linalg.pinv(A.T @ A)
        for k, i in enumerate(pre):
            se = math.sqrt(max(cov[k, k], 1e-300))
            if 2 * (1 - stats.t.cdf(abs(coef[k] / se), dof)) < alpha:
                d.append([i, j])
    return {'directed': sorted(d), 'undirected': [], 'bidirected': []}


METHODS = {'empty': empty, 'pc': pc, 'pc_oracle': pc_oracle, 'lingam': lingam}
