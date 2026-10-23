"""Proposing the interventions that resolve hidden causes (B20_R119): Genesis's active procedure and its comparators.

The question from Daniel's research alert: when measurements cannot explain what is seen, can the system propose
the experiment that would? Here the experiment is a hard intervention do(X_t), which the benchmark can perform
(`sem.sample(..., intervene=t)`), at a budget of m interventions of n_int samples each.

What one intervention tells. Under do(X_t), X_t is cut from every cause, observed or hidden. In a linear model a
neighbour X_j still depends on X_t only if t is an ancestor of j. So for an adjacent pair (i, j):
  * do(X_i) with dependence: i -> j;
  * do(X_i) and do(X_j) both without dependence: neither causes the other, so the adjacency is a hidden common
    cause alone (i <-> j);
  * one intervention without dependence: i is not a cause of j (j -> i or i <-> j); the observational mark decides
    between them, and a claimed i -> j is withdrawn.
Dependence is Pearson's correlation test at alpha 0.01 (linear model; exact cancellations have measure zero).

The procedure (`resolve`):
  1. FCI on the observational data (the established method that allows hidden variables; `causal.fci`) gives the
     adjacencies and marks.
  2. Each adjacent pair gets a suspicion of a hidden cause from the observational data: FCI's marks (1 for <->,
     0.5 undecided, 0 for a tail) and, with several environments, whether the regression of each variable on the
     other changes across environments (Cochran's Q on the per-environment slopes, alpha 0.01; a direct cause's
     slope does not change when only noise variances change, a hidden cause's does). A direction-free pair that is
     non-invariant both ways scores 1, one way 0.5, neither 0; the suspicion is the mean of the available scores.
  3. Targets are chosen by a strategy, one at a time:
       - `random`: uniformly among the variables not yet intervened on;
       - `degree`: the highest-degree variable in FCI's skeleton (a common heuristic);
       - `suspicion` (Genesis's): the variable whose unresolved adjacent pairs carry the most suspicion, a pair
         counting fully until one endpoint is intervened on and half until both are.
     Ties break by the variable index (`random` by its seed). A reference strategy, `oracle`, is told the truth and
     intervenes on the endpoints of the hidden causes first (then by degree): the ceiling of target choice.
  4. The answer combines the interventions with FCI's marks as above.
The comparators share every step but the choice of targets.
"""
import numpy as np
from scipy import stats

from . import fci as F
from . import methods as PCM
from . import sem as S

ALPHA = 0.01
STRATEGIES = ('random', 'degree', 'suspicion')
REFERENCE = ('oracle',)          # told the truth: the endpoints of the hidden causes first (a ceiling, not a method)


def slope_heterogeneity(envs, i, j):
    """Cochran's Q p-value for the slope of X_j on X_i across environments (1.0 with one environment)."""
    if len(envs) < 2:
        return 1.0
    b, w = [], []
    for X in envs:
        x, y = X[:, i] - X[:, i].mean(), X[:, j] - X[:, j].mean()
        sxx = float(x @ x)
        slope = float(x @ y) / sxx
        resid = y - slope * x
        var = float(resid @ resid) / max(1, len(x) - 2) / sxx
        b.append(slope)
        w.append(1.0 / max(var, 1e-12))
    b, w = np.array(b), np.array(w)
    mean = float((w * b).sum() / w.sum())
    q = float((w * (b - mean) ** 2).sum())
    return float(stats.chi2.sf(q, len(envs) - 1))


def suspicion(view, answer, adj):
    envs = [np.asarray(X) for X in view['environments']]
    marks = {}
    for e in answer['bidirected']:
        marks[tuple(sorted(e))] = 1.0
    for e in answer['undirected']:
        marks[tuple(sorted(e))] = 0.5
    for e in answer['directed']:
        marks[tuple(sorted(e))] = 0.0
    out = {}
    for i in range(view['p']):
        for j in adj[i]:
            if i < j:
                scores = [marks.get((i, j), 0.5)]
                if len(envs) > 1:
                    non = (slope_heterogeneity(envs, i, j) < ALPHA) + (slope_heterogeneity(envs, j, i) < ALPHA)
                    scores.append(non / 2)
                out[(i, j)] = float(np.mean(scores))
    return out


def choose(strategy, p, adj, susp, done, rng, truth=None):
    left = [v for v in range(p) if v not in done]
    if not left:
        return None
    if strategy == 'oracle':
        for pair in truth['confounded']:
            for v in pair:
                if v not in done:
                    return v
        strategy = 'degree'
    if strategy == 'random':
        return int(rng.choice(left))
    if strategy == 'degree':
        return max(left, key=lambda v: (len(adj[v]), -v))

    def gain(v):
        g = 0.0
        for u in adj[v]:
            s = susp.get(tuple(sorted((u, v))), 0.0)
            g += s if u not in done else s / 2
        return g
    return max(left, key=lambda v: (gain(v), -v))


def dependent(x, y, alpha=ALPHA):
    r, pval = stats.pearsonr(x, y)
    return bool(pval < alpha)


def resolve(view, truth, strategy, budget, n_int, seed):
    """FCI, then `budget` interventions chosen by `strategy`; returns (answer, record)."""
    if strategy not in STRATEGIES + REFERENCE:
        raise ValueError(f'unknown strategy {strategy!r}')
    X = PCM.pooled(view)
    g, _ = F.run(view['p'], PCM.fisher_z(np.corrcoef(X, rowvar=False), X.shape[0]), PCM.ALPHA)
    base = F.to_answer(g)
    p, adj = view['p'], {i: set(g.adj[i]) for i in range(view['p'])}
    susp = suspicion(view, base, adj)
    rng = np.random.default_rng([seed, 7])
    data_rng = np.random.default_rng([seed, 11])
    done, tests = [], {}
    for _ in range(budget):
        t = choose(strategy, p, adj, susp, done, rng, truth)
        if t is None:
            break
        done.append(t)
        Xi = S.sample(truth, n_int, data_rng, env=0, intervene=t)
        for j in sorted(adj[t]):
            tests[(t, j)] = dependent(Xi[:, t], Xi[:, j])
    mark = {}
    for e in base['directed']:
        mark[tuple(sorted(e))] = ('d', tuple(e))
    for e in base['undirected']:
        mark[tuple(sorted(e))] = ('u', None)
    for e in base['bidirected']:
        mark[tuple(sorted(e))] = ('b', None)
    for (i, j), m in list(mark.items()):
        ij, ji = tests.get((i, j)), tests.get((j, i))
        if ij:
            mark[(i, j)] = ('d', (i, j))
        elif ji:
            mark[(i, j)] = ('d', (j, i))
        elif ij is False and ji is False:
            mark[(i, j)] = ('b', None)
        elif ij is False and m == ('d', (i, j)):
            mark[(i, j)] = ('u', None)
        elif ji is False and m == ('d', (j, i)):
            mark[(i, j)] = ('u', None)
    d = sorted([list(e) for k, (t, e) in mark.items() if t == 'd'])
    u = sorted([list(k) for k, (t, _) in mark.items() if t == 'u'])
    b = sorted([list(k) for k, (t, _) in mark.items() if t == 'b'])
    d, u = PCM._acyclic_part(p, d, u)
    return ({'directed': d, 'undirected': u, 'bidirected': b},
            {'targets': done, 'base': base, 'suspicion': {f'{i}-{j}': s for (i, j), s in sorted(susp.items())}})
