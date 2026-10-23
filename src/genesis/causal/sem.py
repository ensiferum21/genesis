"""Planted linear structural equation models with hidden confounders and several environments (B20_R117).

Model. Observed variables X_1..X_p and hidden variables L_1..L_h, all centred:
    X = X B + L G + E,      i.e.  X = (L G + E) (I - B)^-1      (rows are samples)
  * B (p x p): B[i, j] != 0 iff i -> j. A random order of the observed variables; each forward pair is an edge with
    probability `density`; weights are sign x U(W_LOW, W_HIGH).
  * G (h x p): each hidden variable has exactly two observed children, a pair no other hidden variable confounds
    (when the pair is directly adjacent the truth has both edges, a "bow"); loadings are sign x U(W_LOW, W_HIGH).
  * Noise: independent, non-Gaussian (`laplace` or `uniform`) or `gauss`, unit variance before scaling. Hidden
    variables use the same family.
  * Environments: environment 0 is the reference; in each other environment a random third of the observed
    variables have their noise scaled by U(1.5, 3) (a soft intervention on the noise; the graph and weights stay).
    The total sample size N is split evenly over the K environments.
  * Interventions (for later studies): `sample(..., intervene=i)` draws data with X_i set to fresh noise of unit
    variance, cutting every edge into it, from observed and hidden parents alike.

Everything is drawn from `numpy.random.Generator`s seeded by the instance seed, so an instance is reproducible from
(seed, params). The hidden part (which pairs are confounded, the loadings, the hidden variables' values) has its own
streams, so for one seed and K the graph, the environments and the observed noise are the same whatever h is: a
study can add hidden variables to an otherwise identical instance. The candidate's view is the data only; the truth
is the evaluator's.
"""
import math

import numpy as np

W_LOW, W_HIGH = 0.5, 1.5
NOISES = ('laplace', 'uniform', 'gauss')
ENV_SCALE = (1.5, 3.0)


def _noise(rng, family, size):
    if family == 'laplace':
        return rng.laplace(0.0, 1.0 / math.sqrt(2.0), size)
    if family == 'uniform':
        return rng.uniform(-math.sqrt(3.0), math.sqrt(3.0), size)
    if family == 'gauss':
        return rng.standard_normal(size)
    raise ValueError(f'unknown noise family {family!r}')


def _weight(rng):
    return float(rng.choice((-1.0, 1.0)) * rng.uniform(W_LOW, W_HIGH))


def planted(seed, p, h, density, noise='laplace', k_env=1):
    """The truth of one instance: graph, weights, hidden variables, environments."""
    if not (2 <= p <= 50 and 0 <= h <= p * (p - 1) // 2 and 0.0 <= density <= 1.0 and k_env >= 1):
        raise ValueError('parameters out of range')
    if noise not in NOISES:
        raise ValueError(f'unknown noise family {noise!r}')
    rng = np.random.default_rng(seed)
    order = [int(v) for v in rng.permutation(p)]
    B = np.zeros((p, p))
    for a in range(p):
        for b in range(a + 1, p):
            if rng.random() < density:
                B[order[a], order[b]] = _weight(rng)
    scales = [[1.0] * p]
    for _ in range(1, k_env):
        s = [1.0] * p
        for v in rng.choice(p, size=max(1, round(p / 3)), replace=False):
            s[int(v)] = float(rng.uniform(*ENV_SCALE))
        scales.append(s)
    hrng = np.random.default_rng([seed, 2])     # the hidden part: the same graph and environments for any h
    pairs = [(i, j) for i in range(p) for j in range(i + 1, p)]
    chosen = [pairs[int(k)] for k in hrng.choice(len(pairs), size=h, replace=False)] if h else []
    G = np.zeros((h, p))
    for k, (i, j) in enumerate(chosen):
        G[k, i], G[k, j] = _weight(hrng), _weight(hrng)
    return {'seed': int(seed), 'p': p, 'h': h, 'density': density, 'noise': noise, 'k_env': k_env,
            'order': order, 'B': B.tolist(), 'G': G.tolist(), 'confounded': [list(c) for c in sorted(chosen)],
            'scales': scales}


def sample(truth, n, rng, env=0, intervene=None, hidden_rng=None):
    """n samples (n x p) of environment `env`; with `intervene=i`, X_i is set to fresh unit noise. The hidden
    variables are drawn from `hidden_rng` when given (so the observed noise does not depend on h)."""
    p, h = truth['p'], truth['h']
    B, G = np.array(truth['B']), np.array(truth['G']).reshape(h, p)
    scale = np.array(truth['scales'][env])
    if intervene is not None:
        B, G, scale = B.copy(), G.copy(), scale.copy()
        B[:, intervene] = 0.0
        G[:, intervene] = 0.0
        scale[intervene] = 1.0
    E = _noise(rng, truth['noise'], (n, p)) * scale
    L = _noise(hidden_rng if hidden_rng is not None else rng, truth['noise'], (n, h))
    return (L @ G + E) @ np.linalg.inv(np.eye(p) - B)


def instance(seed, p, h, density, noise='laplace', k_env=1, n_total=3000):
    """(view, truth): the view holds the environments' data only."""
    truth = planted(seed, p, h, density, noise, k_env)
    rng, hrng = np.random.default_rng([seed, 1]), np.random.default_rng([seed, 3])
    per = n_total // k_env
    data = [sample(truth, per, rng, env=k, hidden_rng=hrng) for k in range(k_env)]
    return {'p': p, 'environments': data}, truth
