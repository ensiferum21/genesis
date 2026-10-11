"""Active experiment selection and identifiability (roadmap W14).

The competing explanations for each task family are which method reaches the certified
optimum most often there. An action runs one method on one fresh task of one family, at
its CPU cost. The observation is binary: did the method reach the certified optimum?

The observation model is Beta–Bernoulli per (method, family), with a Beta(1, 1) prior.
The model is calibrated by checking, on held-out pools, that its predictive probability
for a hit matches the observed frequency.

Three policies, compared under equal budgets:
  * eig          expected information gain about which method is best in a family,
                 estimated by Monte Carlo from the posteriors, per unit cost;
  * round_robin  a fixed schedule over every action;
  * random       uniform over the actions.
Two more policies were added in B19 after the first DEV evaluation, in which eig lost to
both fixed and random selection; they are evaluated on fresh pools only:
  * kg           knowledge gradient with lookahead (KG*), exact for Beta-Bernoulli, per unit
                 cost;
  * top_two      top-two Thompson sampling in the family whose leader is least certain.
They are scored on the probability of naming the true best method per family, and on
downstream regret: the true hit rate of the best method minus that of the method named.
The truth is the hit rate over the whole real pool.

Identifiability. Two methods that every admissible action observes identically, because
they are the same decoder by a checked theorem, or because they produce the same outcome
on every pooled task, cannot be separated by these experiments. A family whose best
candidates fall into such a class is reported UNRESOLVED with the reason, never resolved
by an arbitrary tie-break.
"""
import math
import random


def _entropy(ps):
    return -sum(p * math.log(p) for p in ps if p > 0)


class Posterior:
    def __init__(self, methods, families):
        self.methods, self.families = list(methods), list(families)
        self.a = {(m, f): 1.0 for m in methods for f in families}
        self.b = {(m, f): 1.0 for m in methods for f in families}

    def update(self, m, f, hit):
        if hit:
            self.a[(m, f)] += 1
        else:
            self.b[(m, f)] += 1

    def best_distribution(self, f, rng, draws=400, overrides=None):
        counts = {m: 0 for m in self.methods}
        for _ in range(draws):
            samples = {}
            for m in self.methods:
                a, b = (overrides or {}).get((m, f), (self.a[(m, f)], self.b[(m, f)]))
                samples[m] = rng.betavariate(a, b)
            counts[max(self.methods, key=lambda m: (samples[m], m))] += 1
        return {m: c / draws for m, c in counts.items()}

    def predictive(self, m, f):
        return self.a[(m, f)] / (self.a[(m, f)] + self.b[(m, f)])


def eig(post, m, f, rng, draws=300):
    now = _entropy(post.best_distribution(f, rng, draws).values())
    p = post.predictive(m, f)
    after = 0.0
    for hit, prob in ((True, p), (False, 1 - p)):
        a, b = post.a[(m, f)] + hit, post.b[(m, f)] + (not hit)
        after += prob * _entropy(post.best_distribution(f, rng, draws, {(m, f): (a, b)}).values())
    return now - after


def _betabinom_pmf(h, k, a, b):
    from math import lgamma, exp
    lb = lambda x, y: lgamma(x) + lgamma(y) - lgamma(x + y)
    lc = lgamma(k + 1) - lgamma(h + 1) - lgamma(k - h + 1)
    return exp(lc + lb(h + a, k - h + b) - lb(a, b))


def kg_star(post, m, f, cost, horizons=(1, 2, 4, 8, 16)):
    """Knowledge gradient with lookahead (KG*): the largest expected gain in the best
    posterior mean of family f per unit cost, over k repeated observations of (m, f).
    Exact for Beta-Bernoulli (Beta-Binomial predictive); no Monte Carlo noise."""
    means = {x: post.a[(x, f)] / (post.a[(x, f)] + post.b[(x, f)]) for x in post.methods}
    now = max(means.values())
    other = max([v for x, v in means.items() if x != m], default=0.0)
    a, b = post.a[(m, f)], post.b[(m, f)]
    best = 0.0
    for k in horizons:
        gain = sum(_betabinom_pmf(h, k, a, b) * max(other, (a + h) / (a + b + k)) for h in range(k + 1)) - now
        if gain > 1e-12:                    # below that it is rounding, not information
            best = max(best, gain / (k * cost))
    return best


def run_policy(policy, pools, costs, budget, *, seed, methods, families, draws=300):
    """Spend `budget` CPU-seconds; pools[(m, f)] is a list of real outcomes drawn without
    replacement in a seed-dependent order. Returns the named best per family."""
    rng = random.Random(seed)
    order = {k: rng.sample(v, len(v)) for k, v in pools.items()}
    used = {k: 0 for k in pools}
    post = Posterior(methods, families)
    actions = [(m, f) for f in families for m in methods]
    spent, step, log = 0.0, 0, []
    while True:
        avail = [x for x in actions if used[x] < len(order[x]) and spent + costs[x] <= budget]
        if not avail:
            break
        if policy == 'round_robin':
            x = avail[step % len(avail)]
        elif policy == 'random':
            x = rng.choice(avail)
        elif policy == 'eig':
            x = max(avail, key=lambda a: (eig(post, a[0], a[1], rng, draws) / costs[a], a))
        elif policy == 'kg':
            x = max(avail, key=lambda a: (kg_star(post, a[0], a[1], costs[a]), a))
        elif policy == 'top_two':
            # top-two Thompson sampling (beta = 1/2) in the family whose leader is least certain
            fams = sorted({a[1] for a in avail})
            conf = {g: max(post.best_distribution(g, rng, draws).values()) for g in fams}
            g = min(fams, key=lambda g: (conf[g], g))
            ms = [a[0] for a in avail if a[1] == g]

            def sample_best():
                v = {m: rng.betavariate(post.a[(m, g)], post.b[(m, g)]) for m in ms}
                return max(ms, key=lambda m: (v[m], m))
            first = sample_best()
            pick = first
            if rng.random() >= 0.5 and len(ms) > 1:
                for _ in range(50):
                    pick = sample_best()
                    if pick != first:
                        break
            x = (pick, g)
        else:
            raise ValueError(policy)
        hit = order[x][used[x]]
        used[x] += 1
        spent += costs[x]
        post.update(x[0], x[1], hit)
        log.append(x)
        step += 1
    named = {f: max(methods, key=lambda m: (post.predictive(m, f), m)) for f in families}
    return {'named': named, 'pulls': len(log), 'spent': round(spent, 3),
            'pulls_by_action': {f'{m}@{f}': used[(m, f)] for (m, f) in actions}}


def equivalence_classes(methods, families, pools, declared=(), identity_pools=None):
    """Methods that no admissible action can tell apart: declared equal (a checked theorem),
    or producing the identical raw result on every pooled task in every family
    (`identity_pools`, per-task values rather than binary outcomes, which coincide by
    chance far more often)."""
    pools = identity_pools or pools
    parent = {m: m for m in methods}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for a, b in declared:
        parent[find(a)] = find(b)
    for i, a in enumerate(methods):
        for b in methods[i + 1:]:
            if all(pools[(a, f)] == pools[(b, f)] for f in families):
                parent[find(a)] = find(b)
    classes = {}
    for m in methods:
        classes.setdefault(find(m), []).append(m)
    return [sorted(c) for c in classes.values()]


def truth(pools, methods, families):
    rates = {(m, f): sum(pools[(m, f)]) / len(pools[(m, f)]) for m in methods for f in families}
    best = {}
    for f in families:
        top = max(rates[(m, f)] for m in methods)
        best[f] = sorted(m for m in methods if rates[(m, f)] == top)
    return rates, best


def resolve(named, best, classes):
    """The verdict for one family: RESOLVED, or UNRESOLVED when the named method shares an
    indistinguishable class with another method."""
    cls = next(c for c in classes if named in c)
    if len(cls) > 1:
        return {'verdict': 'UNRESOLVED', 'reason': f'{cls} cannot be distinguished by any admissible action',
                'class': cls}
    return {'verdict': 'RESOLVED', 'named': named, 'correct': named in best}


def evaluate(pools, costs, methods, families, *, budget, repetitions=100, declared=(), draws=200,
             identity_pools=None, policies=('eig', 'round_robin', 'random')):
    """Indistinguishable methods are collapsed first: each class is one hypothesis, so no
    budget is spent telling apart what no action can separate. The policies then compete
    on the class-level question, and every multi-member class is reported UNRESOLVED
    within itself."""
    rates, best = truth(pools, methods, families)
    classes = equivalence_classes(methods, families, pools, declared, identity_pools)
    reps = [c[0] for c in classes]
    out = {}
    for policy in policies:
        correct, regret = 0, 0.0
        for r in range(repetitions):
            res = run_policy(policy, {k: v for k, v in pools.items() if k[0] in reps}, costs, budget, seed=r,
                             methods=reps, families=families, draws=draws)
            for f in families:
                cls = next(c for c in classes if res['named'][f] in c)
                correct += bool(set(cls) & set(best[f]))
                regret += max(rates[(m, f)] for m in methods) - rates[(res['named'][f], f)]
        n = repetitions * len(families)
        out[policy] = {'p_correct_class': round(correct / n, 4), 'mean_regret': round(regret / n, 4)}
    within = [{'class': c, 'verdict': 'UNRESOLVED',
               'reason': 'identical observations under every admissible action'} for c in classes if len(c) > 1]
    return {'rates': {f'{m}@{f}': round(v, 4) for (m, f), v in rates.items()}, 'best': best,
            'classes': classes, 'within_class': within, 'policies': out, 'budget_cpu_s': budget,
            'repetitions': repetitions}


def calibration(pools, methods, families, *, split=0.5, seed=0):
    """Fit the Beta–Bernoulli model on one half of each pool and compare its predictive hit
    probability with the frequency on the other half."""
    rng = random.Random(seed)
    rows = []
    for m in methods:
        for f in families:
            xs = rng.sample(pools[(m, f)], len(pools[(m, f)]))
            k = int(len(xs) * split)
            fit, held = xs[:k], xs[k:]
            pred = (1 + sum(fit)) / (2 + len(fit))
            rows.append({'action': f'{m}@{f}', 'predicted': round(pred, 4),
                         'observed': round(sum(held) / len(held), 4) if held else None})
    errs = [abs(r['predicted'] - r['observed']) for r in rows if r['observed'] is not None]
    return {'rows': rows, 'mean_abs_error': round(sum(errs) / len(errs), 4) if errs else None}


__all__ = ['evaluate', 'run_policy', 'equivalence_classes', 'calibration', 'Posterior', 'eig', 'kg_star', 'truth',
           'resolve']
