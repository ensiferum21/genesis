"""Causal discovery as a domain of the experimental scientist (B20_R129; Genesis Ω, P1): the causal adapter of
`science.design`.

**Questions.** Every adjacent pair (i, j), i < j, of FCI's skeleton on the pooled observational data.
**Hypotheses** (everything the planted domain allows for an adjacent pair):
  * `ij`: i causes j directly (perhaps also confounded: an edge with a hidden cause beside it, a "bow", answers to
    the same experiments and is marked by its edge);
  * `ji`: j causes i directly;
  * `conf`: a hidden common cause and no direct edge;
  * `none`: neither; the adjacency is an error of FCI's tests.
**Experiments.** Intervening on one variable t (N_INT fresh samples with X_t set to fresh noise, every edge into it
cut); it touches the pairs of t. **Outcome** for each neighbour j: `active2.classify` (direct: X_j depends on X_t
with t's adjacent descendants held fixed; indirect: X_j depends on X_t only through them; none: X_j does not
depend on X_t).

**What an experiment predicts under each hypothesis** (the instrument's model), seen from t, two versions:
  * `theory`, from the causal assumptions alone. t -> j: direct with high probability (0.90). j -> t: t cannot reach
    j in an acyclic graph, so none (0.90). conf and none: no direct edge, so never direct but for test errors
    (0.05); indirect when t reaches j by another path (0.25), else none (0.70). Priors from FCI's mark: a direction
    a -> b gives a -> b 0.55, b -> a 0.10, conf 0.25, none 0.10; FCI's <-> gives conf 0.55, the others 0.15; an
    undirected or o-o mark gives each direction 0.30, conf 0.25, none 0.15. A pair flagged by the observational
    residual signal (`active2`, p < 0.01) has the weight of conf tripled.
  * `calibrated`, estimated by simulation (`calibrate`): the same experiments run on CALIBRATION worlds drawn from the
    domain's generator with their truth known (never the worlds a study tests on). The prior is the frequency of each
    hypothesis given FCI's mark and the flag, and the prediction the frequency of each outcome given the hypothesis
    seen from t, each count plus one (Laplace). This makes the likelihoods correspond to the actual data-generating
    process and instrument, errors included, which the theory version only assumes.

**The lab is drawn once** (`prepare`): the outcome of intervening on every variable, from a generator seeded by
(instance, variable), so every strategy that runs an experiment sees the same result (common random numbers) and no
strategy can be favoured by luckier data. The view and FCI are computed once per instance as well.

**The answer** from the decisions: ij or ji a directed edge, conf a hidden-cause mark, none no mark; the directed part
is made acyclic as in `methods` (an edge that would close a cycle becomes undirected).

Comparators specific to this domain: `degree_order` (highest degree in FCI's skeleton first) and the reference
`oracle_order` (the endpoints of the planted hidden causes first, then by degree; it reads the truth).
"""
import numpy as np

from . import active2 as V2
from . import fci as F
from . import methods as PCM
from . import sem as S

HYPS = ('ij', 'ji', 'conf', 'none')
OUTCOMES = ('direct', 'indirect', 'none')
RELATIONS = ('cause', 'effect', 'conf', 'none')        # a hypothesis seen from the intervened variable t
MARKS = ('fwd', 'bwd', 'b', 'u')                       # FCI's mark on (i, j), i < j: i -> j, j -> i, <->, other
FOCUS = 'conf'

THEORY = {
    'prior': {'fwd': {'ij': 0.55, 'ji': 0.10, 'conf': 0.25, 'none': 0.10},
              'bwd': {'ij': 0.10, 'ji': 0.55, 'conf': 0.25, 'none': 0.10},
              'b': {'ij': 0.15, 'ji': 0.15, 'conf': 0.55, 'none': 0.15},
              'u': {'ij': 0.30, 'ji': 0.30, 'conf': 0.25, 'none': 0.15}},
    'flag_conf_factor': 3.0,
    'predict': {'cause': {'direct': 0.90, 'indirect': 0.05, 'none': 0.05},
                'effect': {'direct': 0.05, 'indirect': 0.05, 'none': 0.90},
                'conf': {'direct': 0.05, 'indirect': 0.25, 'none': 0.70},
                'none': {'direct': 0.05, 'indirect': 0.25, 'none': 0.70}}}


def key(i, j):
    return f'{min(i, j)}-{max(i, j)}'


def ends(q):
    i, j = q.split('-')
    return int(i), int(j)


def relation(h, t, q):
    """Hypothesis h about pair q seen from the intervened variable t."""
    i, j = ends(q)
    if h in ('conf', 'none'):
        return h
    return 'cause' if (h == 'ij') == (t == i) else 'effect'


def true_hypothesis(truth, q):
    i, j = ends(q)
    if truth['B'][i][j] != 0.0:
        return 'ij'
    if truth['B'][j][i] != 0.0:
        return 'ji'
    if [i, j] in truth['confounded']:
        return 'conf'
    return 'none'


def prepare(view, truth, n_int, seed):
    """FCI, its skeleton, its marks and the flags (from the view), and the lab: the outcome of intervening on every
    variable (from the truth, the evaluator's simulator). JSON-serialisable."""
    p = view['p']
    X = PCM.pooled(view)
    g, _ = F.run(p, PCM.fisher_z(np.corrcoef(X, rowvar=False), X.shape[0]), PCM.ALPHA)
    base = F.to_answer(g)
    adj = {i: set(g.adj[i]) for i in range(p)}
    susp = V2.suspicion(view, adj)
    marks = {}
    for (i, j), m in V2.decide(base, {}).items():
        marks[key(i, j)] = ('fwd' if m == ('d', (i, j)) else 'bwd' if m == ('d', (j, i)) else
                            'b' if m[0] == 'b' else 'u')
    flagged = sorted(key(i, j) for (i, j), sc in susp.items() if sc >= V2.FLAG_SCORE)
    lab = {}
    for t in range(p):
        Xt = S.sample(truth, n_int, np.random.default_rng([seed, 11, t]), env=0, intervene=t)
        lab[str(t)] = {str(j): V2.classify(Xt, t, j, adj) for j in sorted(adj[t])}
    return {'p': p, 'fci': base, 'adj': {str(i): sorted(adj[i]) for i in range(p)}, 'marks': marks,
            'flagged': flagged, 'lab': lab}


def calibrate(prepared_truths):
    """The `calibrated` model from [(prepared, truth)] of calibration worlds."""
    prior = {f'{m}|{f}': {h: 1.0 for h in HYPS} for m in MARKS for f in (0, 1)}
    pred = {r: {o: 1.0 for o in OUTCOMES} for r in RELATIONS}
    for prep, truth in prepared_truths:
        for q, m in prep['marks'].items():
            h = true_hypothesis(truth, q)
            prior[f"{m}|{int(q in prep['flagged'])}"][h] += 1
            for t in ends(q):
                o = prep['lab'][str(t)][str(ends(q)[1] if t == ends(q)[0] else ends(q)[0])]
                pred[relation(h, t, q)][o] += 1
    norm = lambda d: {k: v / sum(d.values()) for k, v in d.items()}     # noqa: E731
    return {'prior': {k: norm(v) for k, v in prior.items()}, 'predict': {k: norm(v) for k, v in pred.items()}}


def model_prior(model, mark, flagged):
    if 'flag_conf_factor' in model:
        p = dict(model['prior'][mark])
        if flagged:
            p['conf'] *= model['flag_conf_factor']
    else:
        p = dict(model['prior'][f'{mark}|{int(flagged)}'])
    z = sum(p.values())
    return [p[h] / z for h in HYPS]


class CausalDomain:
    """`science.design.Domain` for one prepared instance under one model of the instrument."""
    focus = FOCUS

    def __init__(self, prepared, model):
        self.prep, self.model = prepared, model
        self._qs = sorted(prepared['marks'], key=lambda q: ends(q))

    def questions(self):
        return self._qs

    def hypotheses(self):
        return HYPS

    def outcomes(self):
        return OUTCOMES

    def prior(self, q):
        return model_prior(self.model, self.prep['marks'][q], q in self.prep['flagged'])

    def experiments(self):
        return list(range(self.prep['p']))

    def touches(self, t):
        return [key(t, j) for j in self.prep['adj'][str(t)]]

    def predict(self, q, t):
        return [[self.model['predict'][relation(h, t, q)][o] for o in OUTCOMES] for h in HYPS]

    def execute(self, t):
        return {key(t, int(j)): o for j, o in self.prep['lab'][str(t)].items()}


def answer(p, decisions):
    d, b = [], []
    for q, h in decisions.items():
        i, j = ends(q)
        if h == 'ij':
            d.append([i, j])
        elif h == 'ji':
            d.append([j, i])
        elif h == 'conf':
            b.append([i, j])
    d, u = PCM._acyclic_part(p, sorted(d), [])
    return {'directed': d, 'undirected': sorted(u), 'bidirected': sorted(b)}


def degree_order(prepared):
    p = prepared['p']
    return sorted(range(p), key=lambda v: (-len(prepared['adj'][str(v)]), v))


def oracle_order(prepared, truth):
    out = []
    for pair in truth['confounded']:
        for v in pair:
            if v not in out:
                out.append(v)
    return out + [v for v in degree_order(prepared) if v not in out]
