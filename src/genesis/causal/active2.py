"""Proposing the interventions that resolve hidden causes, version 2 (B20_R121): the two repairs B20_R120 pointed to.

B20_R120 (NOT_SHOWN) found, after the fact, two weaknesses in version 1 (`causal.active`, kept unchanged):
  1. **The suspicion signal barely separated confounded pairs** (0.53 against 0.48): FCI's marks and slope changes
     across environments carry little information at 3,000 samples.
  2. **The decision rule read ancestry as direct causation:** under do(X_i), dependence of X_j only shows that i is an
     ancestor of j, so a hidden-cause pair with a path i -> k -> j was turned into i -> j.

Version 2 changes exactly these two things; FCI, the strategies' shape, the budgets and the scoring stay.

**1. Suspicion from LiNGAM residuals (linear non-Gaussian models).** DirectLiNGAM (`causal.methods`, which
assumes nothing is hidden) is fitted to the pooled data. Each variable j is then regressed on its LiNGAM parents
within each environment. If the model were right, the residual would be independent of every parent; a hidden common
cause of j and a parent i leaves it uncorrelated with X_i but *dependent* on it, since the noise is non-Gaussian.
Dependence is tested by the correlations of three non-linear transforms of each (x^2, tanh x, x^3 against r^2,
tanh r, r^3), Fisher's z, the smallest p-value Bonferroni-corrected over the 9 correlations and the K environments.
The suspicion of an adjacent pair (FCI's skeleton) is -log10 of the smaller p-value over the pair's LiNGAM parent
relations (capped at 12, divided by 12); a pair with no LiNGAM edge between its ends scores 0. This is the principle
of LiNGAM with hidden variables (Hoyer et al. 2008) and of RCD (Maeda and Shimizu 2020): prior art, used here as the
signal for choosing experiments. The strategy `suspicion` uses this score; `random`, `degree` and `oracle` are as in
version 1. (A pairwise version, regressing X_j on X_i alone, was tried first on B20_R120's instances and did not
separate confounded pairs: AUC 0.54 against 0.83 for this one; see B20_R121's record.)

**2. Direct causation under intervention.** Under do(X_t):
  * the descendants of t are the variables that depend on X_t (Pearson, alpha 0.01);
  * for a neighbour j that depends on X_t, X_j is regressed on X_t and on the descendants of t adjacent to j in FCI's
    skeleton (the candidate mediators); a significant coefficient (t test, alpha 0.01) means t -> j directly;
  * otherwise t is an ancestor of j but not a direct cause. Since FCI keeps them adjacent (no observed set separates
    them), the adjacency is explained by a hidden common cause: t <-> j, from one intervention.
  * a neighbour that does not depend on X_t: t causes neither directly nor indirectly; with an intervention on j as
    well, the same three outcomes decide the pair from j's side, and two "not an ancestor" results give t <-> j.
Conditioning on a mediator that is also a child of j can make a non-direct pair look direct (a collider). That is the
same error version 1 always made, so the repair can only remove errors of the kind found, not add that one.

**3. Flagging (the observational baseline it must beat).** The signal of repair 1 can mark hidden causes without any
experiment: every adjacent pair whose residual dependence is significant (p < 0.01) becomes <->. This is the
observational use of the prior-art principle, so with `flag=True` the interventions only *add* to it: a flagged pair
stays <-> unless an intervention finds a direct cause between its ends (then the experiment decides), and unflagged
pairs are decided as without flags. An experiment can thus refute a flag but never erase one by being silent. Whether experiments chosen by Genesis
add anything over flagging, and whether its choice beats random experiments, is what B20_R122 tests.
"""
import numpy as np
from scipy import stats

from . import active as V1
from . import fci as F
from . import methods as PCM
from . import sem as S

ALPHA = 0.01
STRATEGIES = V1.STRATEGIES
FLAG_ALPHA = 0.01
FLAG_SCORE = -np.log10(FLAG_ALPHA) / 12.0     # the suspicion of a pair whose p-value is FLAG_ALPHA
REFERENCE = V1.REFERENCE


def _nl_dependence_p(x, r):
    """Smallest Bonferroni-corrected p-value of 9 non-linear correlations between standardised x and r."""
    x = (x - x.mean()) / x.std()
    r = (r - r.mean()) / r.std()
    fx = (x ** 2, np.tanh(x), x ** 3)
    gr = (r ** 2, np.tanh(r), r ** 3)
    n = len(x)
    best = 1.0
    for a in fx:
        for b in gr:
            c = float(np.corrcoef(a, b)[0, 1])
            c = min(0.999999, max(-0.999999, c))
            z = 0.5 * np.log((1 + c) / (1 - c)) * np.sqrt(max(1, n - 3))
            best = min(best, float(2 * stats.norm.sf(abs(z))))
    return min(1.0, best * 9)


def residual_p(envs, j, parents, i):
    """p-value that X_j's residual on its parents depends on parent X_i (Bonferroni over the environments)."""
    ps = []
    for X in envs:
        A = X[:, parents] - X[:, parents].mean(axis=0)
        y = X[:, j] - X[:, j].mean()
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        ps.append(_nl_dependence_p(X[:, i] - X[:, i].mean(), y - A @ coef))
    return min(1.0, min(ps) * len(ps))


def suspicion(view, adj):
    envs = [np.asarray(X) for X in view['environments']]
    lg = PCM.lingam(view)
    parents = {j: sorted(a for a, b in lg['directed'] if b == j) for j in range(view['p'])}
    out = {}
    for i in range(view['p']):
        for j in adj[i]:
            if i < j:
                p = 1.0
                if i in parents[j]:
                    p = min(p, residual_p(envs, j, parents[j], i))
                if j in parents[i]:
                    p = min(p, residual_p(envs, i, parents[i], j))
                out[(i, j)] = min(12.0, -np.log10(max(p, 1e-300))) / 12.0
    return out


def classify(Xt, t, j, adj, alpha=ALPHA):
    """Under do(X_t): 'direct', 'indirect' (ancestor, not a direct cause) or 'none' (not an ancestor) for j."""
    p = Xt.shape[1]
    desc = {k for k in range(p) if k != t and V1.dependent(Xt[:, t], Xt[:, k], alpha)}
    if j not in desc:
        return 'none'
    med = sorted((desc & adj[j]) - {j})
    A = np.column_stack([Xt[:, t]] + [Xt[:, k] for k in med])
    A = A - A.mean(axis=0)
    y = Xt[:, j] - Xt[:, j].mean()
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    dof = max(1, len(y) - A.shape[1])
    cov = (resid @ resid / dof) * np.linalg.pinv(A.T @ A)
    tstat = coef[0] / np.sqrt(max(cov[0, 0], 1e-300))
    return 'direct' if 2 * stats.t.sf(abs(tstat), dof) < alpha else 'indirect'


def decide(base, tests):
    """Combine FCI's answer with the interventions' classifications {(t, j): outcome}."""
    mark = {}
    for e in base['directed']:
        mark[tuple(sorted(e))] = ('d', tuple(e))
    for e in base['undirected']:
        mark[tuple(sorted(e))] = ('u', None)
    for e in base['bidirected']:
        mark[tuple(sorted(e))] = ('b', None)
    for (i, j), m in list(mark.items()):
        ij, ji = tests.get((i, j)), tests.get((j, i))
        if ij == 'direct':
            mark[(i, j)] = ('d', (i, j))
        elif ji == 'direct':
            mark[(i, j)] = ('d', (j, i))
        elif 'indirect' in (ij, ji) or (ij == 'none' and ji == 'none'):
            mark[(i, j)] = ('b', None)
        elif ij == 'none' and m == ('d', (i, j)):
            mark[(i, j)] = ('u', None)
        elif ji == 'none' and m == ('d', (j, i)):
            mark[(i, j)] = ('u', None)
    return mark


def resolve(view, truth, strategy, budget, n_int, seed, rule='v2', signal='v2', flag=False):
    """FCI, then `budget` interventions chosen by `strategy`; `rule` and `signal` select version 1 or 2 of the
    decision rule and of the suspicion. With `flag`, an adjacent pair whose signal is significant (p < FLAG_ALPHA,
    version 2 signal only) is marked <-> unless an intervention found a direct cause between its ends.
    Returns (answer, record)."""
    if strategy not in STRATEGIES + REFERENCE:
        raise ValueError(f'unknown strategy {strategy!r}')
    if rule not in ('v1', 'v2') or signal not in ('v1', 'v2'):
        raise ValueError('rule and signal are v1 or v2')
    X = PCM.pooled(view)
    g, _ = F.run(view['p'], PCM.fisher_z(np.corrcoef(X, rowvar=False), X.shape[0]), PCM.ALPHA)
    base = F.to_answer(g)
    p, adj = view['p'], {i: set(g.adj[i]) for i in range(view['p'])}
    susp = suspicion(view, adj) if signal == 'v2' else V1.suspicion(view, base, adj)
    rng = np.random.default_rng([seed, 7])
    data_rng = np.random.default_rng([seed, 11])
    done, tests = [], {}
    for _ in range(budget):
        t = V1.choose(strategy, p, adj, susp, done, rng, truth)
        if t is None:
            break
        done.append(t)
        Xt = S.sample(truth, n_int, data_rng, env=0, intervene=t)
        for j in sorted(adj[t]):
            if rule == 'v2':
                tests[(t, j)] = classify(Xt, t, j, adj)
            else:
                tests[(t, j)] = 'direct' if V1.dependent(Xt[:, t], Xt[:, j]) else 'none'
    mark = decide(base, tests)
    if flag:
        if signal != 'v2':
            raise ValueError('flagging uses the version 2 signal')
        for (i, j), sc in susp.items():
            if (i, j) in mark and sc >= FLAG_SCORE and 'direct' not in (tests.get((i, j)), tests.get((j, i))):
                mark[(i, j)] = ('b', None)
    d = sorted([list(e) for k, (t, e) in mark.items() if t == 'd'])
    u = sorted([list(k) for k, (t, _) in mark.items() if t == 'u'])
    b = sorted([list(k) for k, (t, _) in mark.items() if t == 'b'])
    d, u = PCM._acyclic_part(p, d, u)
    return ({'directed': d, 'undirected': u, 'bidirected': b},
            {'targets': done, 'base': base, 'tests': {f'{i}-{j}': o for (i, j), o in sorted(tests.items())},
             'suspicion': {f'{i}-{j}': s for (i, j), s in sorted(susp.items())}})
