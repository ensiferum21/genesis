"""The experimental scientist (Genesis Ω, P1; B20_R129): choose each experiment by what it is expected to reveal,
update beliefs by Bayes' rule, choose again.

Why. Genesis chose experiments no better than random four times (B20_R120, R122 at two budgets, R124): every target
came from an observational score fixed in advance. B20_R124 showed where choosing matters: with Gaussian data an
oracle's 4 experiments did what 8 random ones did. A scientist that learns must use what each result reveals to
choose the next, and its beliefs must follow from a model of what each experiment would show under each explanation,
or it can grow confident without growing right.

**The decision layer knows nothing about any domain.** A domain (`Domain`) poses QUESTIONS, each with competing
HYPOTHESES and a prior over them, offers EXPERIMENTS, and says which questions an experiment touches, what it predicts
(for every touched question and hypothesis, the probability of each OUTCOME: its model of the instrument), and what
running it gives (`execute`). Questions are independent a priori and outcomes independent given the hypotheses (a
factored model). Causal discovery is the first adapter (`causal.active3`); the same layer can choose which algorithm
component to ablate or which explanation of a solver's failure to test (P2).

**Beliefs.** The posterior of a question depends only on the outcomes observed on it, so it is computed from that
history and cached by it.

**The decision.** For every question, the hypothesis of highest posterior (the Bayes decision under 0-1 loss; ties to
the domain's order of hypotheses).

**Acquisitions** (each scores every experiment not yet run; the scientist runs the highest, ties to the earliest; all
experiments cost the same here, so dividing by cost changes nothing and is left out):
  * `eig`: expected information gain, the sum over the questions it touches of the mutual information between the
    hypothesis and the outcome (Lindley 1956; for causal structure Murphy 2001, Tong and Koller 2001);
  * `dec`: expected decision improvement, the sum over touched questions of E_o[max_h P(h | o)] - max_h P(h): how much
    the probability that the decision is right is expected to rise (the expected value of sample information under
    0-1 loss; Raiffa and Schlaifer 1961);
  * `hybrid`: eig + lam x dec;
  * `static_eig`: eig computed once from the PRIOR and never updated: the non-adaptive baseline, which isolates the value
    of adapting to results from the value of a better first ranking;
  * `program`: a rule Genesis wrote in its own acquisition language (`science.acquire`);
  * `random`; and domain heuristics (`order`: a fixed order the domain gives, e.g. by degree).

Per touched question q and experiment e the features are: `eig`, `dec`, `decf` (expected improvement of the decision
"is it the domain's FOCUS hypothesis or not"); `eigall`, `decall`, `decfall`, the same for observing e together with
every other experiment still available that touches q (a lookahead past one step: some questions are answered only by
two experiments together, which a one-step value undervalues); `ent` (entropy over log of the number of hypotheses),
`maxp`, `pf` (the focus hypothesis's probability), `seen` (outcomes observed on q so far), `left` (experiments still
available that touch q, e included), `one` (1).
"""
import math

import numpy as np

FEATURES = ('eig', 'dec', 'decf', 'eigall', 'decall', 'decfall', 'ent', 'maxp', 'pf', 'seen', 'left', 'one')
MAX_LOOKAHEAD = 3


class Domain:
    """The interface a domain implements (`causal.active3.CausalDomain` is the first)."""
    focus = None

    def questions(self):                 # -> list of question keys
        raise NotImplementedError

    def hypotheses(self):                # -> tuple of hypothesis names (the same for every question)
        raise NotImplementedError

    def prior(self, q):                  # -> np.array over hypotheses
        raise NotImplementedError

    def experiments(self):               # -> list of experiment keys
        raise NotImplementedError

    def touches(self, e):                # -> list of questions experiment e informs
        raise NotImplementedError

    def outcomes(self):                  # -> tuple of outcome names
        raise NotImplementedError

    def predict(self, q, e):             # -> np.array (hypotheses x outcomes): P(outcome | hypothesis, e) on q
        raise NotImplementedError

    def execute(self, e):                # -> {q: outcome} for every q in touches(e)
        raise NotImplementedError


def entropy(p):
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def _value(p, L, focus_index):
    """(information gain, decision improvement, focus-decision improvement) of an observation whose outcome
    table given the hypotheses is L (H x outcomes)."""
    joint = p[:, None] * L
    po = joint.sum(axis=0)
    eig = entropy(p) - sum(po[o] * entropy(joint[:, o] / po[o]) for o in range(L.shape[1]) if po[o] > 0)
    dec = float(joint.max(axis=0).sum() - p.max())
    if focus_index is None:
        decf = 0.0
    else:
        jf = joint[focus_index]
        pf = float(p[focus_index])
        decf = float(np.maximum(jf, po - jf).sum() - max(pf, 1 - pf))
    return max(0.0, float(eig)), max(0.0, dec), max(0.0, decf)


def joint_table(tables):
    """The outcome table of several experiments observed together (outcomes independent given the hypothesis)."""
    out = tables[0]
    for L in tables[1:]:
        out = (out[:, :, None] * L[:, None, :]).reshape(L.shape[0], -1)
    return out


def features(p, L, focus_index, seen, rest=()):
    """The features of one (question, experiment): p over hypotheses, L the predicted outcome table (H x O),
    `rest` the tables of the other experiments still available that touch the question (the `...all` features
    value observing all of them with this one: a lookahead past one step, at most MAX_LOOKAHEAD experiments)."""
    eig, dec, decf = _value(p, L, focus_index)
    allv = _value(p, joint_table([L] + list(rest)[:MAX_LOOKAHEAD - 1]), focus_index) if rest else (eig, dec, decf)
    return {'eig': eig, 'dec': dec, 'decf': decf, 'eigall': allv[0], 'decall': allv[1], 'decfall': allv[2],
            'ent': entropy(p) / math.log(len(p)), 'maxp': float(p.max()),
            'pf': 0.0 if focus_index is None else float(p[focus_index]), 'seen': float(seen),
            'left': float(1 + len(rest)), 'one': 1.0}


class Beliefs:
    """Posteriors from the observation history of each question, cached by that history (valid across runs of the
    same domain, since a posterior depends only on the outcomes observed)."""

    def __init__(self, domain):
        self.d = domain
        self.H = domain.hypotheses()
        self.O = {o: k for k, o in enumerate(domain.outcomes())}
        self.focus = None if domain.focus is None else self.H.index(domain.focus)
        self._post, self._feat, self._pred = {}, {}, {}

    def pred(self, q, e):
        k = (q, e)
        if k not in self._pred:
            self._pred[k] = np.asarray(self.d.predict(q, e), dtype=float)
        return self._pred[k]

    def posterior(self, q, hist):
        k = (q, hist)
        if k not in self._post:
            if not hist:
                p = np.asarray(self.d.prior(q), dtype=float)
            else:
                prev = self.posterior(q, hist[:-1])
                e, o = hist[-1]
                p = prev * self.pred(q, e)[:, self.O[o]]
                p = p / p.sum() if p.sum() > 0 else prev      # an outcome the model calls impossible is ignored
            self._post[k] = p
        return self._post[k]

    def feature(self, q, hist, e, rest=()):
        k = (q, hist, e, rest)
        if k not in self._feat:
            self._feat[k] = features(self.posterior(q, hist), self.pred(q, e), self.focus, len(hist),
                                     [self.pred(q, x) for x in rest])
        return self._feat[k]


class Run:
    """One scientist's run on a domain: the experiments done, the history of every question, the decisions."""

    def __init__(self, domain, beliefs=None):
        self.d = domain
        self.b = beliefs or Beliefs(domain)
        self.qs = list(domain.questions())
        self.hist = {q: () for q in self.qs}
        self.done = []
        self.observations = []
        self.by_q = {q: [] for q in self.qs}
        for e in domain.experiments():
            for q in domain.touches(e):
                self.by_q[q].append(e)

    def left(self):
        return [e for e in self.d.experiments() if e not in self.done]

    def do(self, e):
        obs = self.d.execute(e)
        for q in self.d.touches(e):
            self.hist[q] = tuple(sorted(self.hist[q] + ((e, obs[q]),), key=repr))
        self.done.append(e)
        self.observations.append({'experiment': e, 'outcomes': {str(q): o for q, o in obs.items()}})
        return obs

    def posterior(self, q):
        return self.b.posterior(q, self.hist[q])

    def decisions(self):
        return {q: self.b.H[int(np.argmax(self.posterior(q)))] for q in self.qs}

    def total_entropy(self):
        return sum(entropy(self.posterior(q)) for q in self.qs)


# ------------------------------------------------------------------------------------------------- acquisitions

def _pairs(run, left, prior=False):
    """(experiment index in `left`, feature dict) for every touched question; with `prior`, from the prior."""
    out = []
    avail = set(run.d.experiments()) if prior else set(left)
    for k, e in enumerate(left):
        for q in run.d.touches(e):
            rest = tuple(x for x in run.by_q[q] if x != e and x in avail)
            out.append((k, run.b.feature(q, () if prior else run.hist[q], e, rest)))
    return out


def _sum_by(left, pairs, name):
    s = [0.0] * len(left)
    for k, f in pairs:
        s[k] += f[name]
    return s


def _best(left, scores):
    scores = [round(float(x), 12) for x in scores]
    m = max(scores)
    return left[scores.index(m)]


def choose(run, acq, rng):
    """The next experiment by acquisition `acq` ({'kind': ..., ...}), or None when none is left."""
    left = run.left()
    if not left:
        return None
    kind = acq['kind']
    if kind == 'random':
        return left[int(rng.integers(len(left)))]
    if kind == 'order':
        return next(e for e in acq['order'] if e in left)
    if kind in ('eig', 'dec', 'static_eig'):
        pairs = _pairs(run, left, prior=kind == 'static_eig')
        return _best(left, _sum_by(left, pairs, 'dec' if kind == 'dec' else 'eig'))
    if kind == 'hybrid':
        pairs = _pairs(run, left)
        eig, dec = _sum_by(left, pairs, 'eig'), _sum_by(left, pairs, 'dec')
        return _best(left, [a + acq['lam'] * b for a, b in zip(eig, dec)])
    if kind == 'program':
        from . import acquire
        return _best(left, acquire.scores(acq['program'], len(left), _pairs(run, left)))
    raise ValueError(f'unknown acquisition {kind!r}')


def run(domain, acq, budget, rng=None, beliefs=None, stop=None):
    """Run `budget` experiments chosen by `acq`; returns the Run and the decisions after 0, 1, ... experiments.
    `stop(k, decisions)` may end the run early (it returns True when no further step is needed)."""
    r = Run(domain, beliefs)
    trail = [r.decisions()]
    if stop is not None and stop(0, trail[0]):
        return r, trail
    for k in range(budget):
        e = choose(r, acq, rng)
        if e is None:
            break
        r.do(e)
        trail.append(r.decisions())
        if stop is not None and stop(k + 1, trail[-1]):
            break
    return r, trail
