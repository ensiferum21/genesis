"""Quality at equal time, and sequential stopping, for anytime comparisons (B20_R93's work orders).

When every strong method reaches the same value (saturation), time to that value is the only thing a study can
compare. On instances no method solves to the optimum within the budget, the question becomes: at the same budget,
whose answer is better? This module scores that the way the MaxSAT Evaluation 2026 scores its anytime tracks
(slides, p. 14): on instance i, a solver's score is

    (cost of the best known solution for i + 1) / (cost of the solver's solution for i + 1),   0 without a solution,

and solvers are ranked by their average score. Here a host's cost is the number of soft clauses falsified, the edges
left out (`edges - value`), and the best known solution is the best value any arm, budget or reference found.

Comparisons are paired over hosts: the difference of mean scores, with a percentile bootstrap interval (resampling
hosts), and a verdict against a preregistered margin `delta`:
  A_BETTER (the interval lies above +delta), B_BETTER (below -delta), EQUIVALENT (inside [-delta, +delta]),
  UNRESOLVED (otherwise).

Sequential stopping: a study with `looks` preregistered interim analyses (after the given numbers of hosts) uses, at
every look, an interval at level 1 - alpha / looks (Bonferroni over looks: valid for any dependence between looks,
conservative) and stops a comparison at the first look where its verdict is A_BETTER or B_BETTER (or EQUIVALENT,
when the plan allows stopping for equivalence). Once every comparison has stopped, the study stops.
"""
import math
import random

NO_SOLUTION = None


def score(best_cost, cost):
    """The MSE 2026 anytime score of one solution: (best + 1) / (cost + 1); 0 without a solution."""
    if cost is NO_SOLUTION:
        return 0.0
    if cost < best_cost:
        raise ValueError(f'a cost {cost} below the best known {best_cost}: the best known value is wrong')
    return (best_cost + 1) / (cost + 1)


def cost(edges, value):
    """Edges left out of a triangle-free subgraph with `value` edges (None: no solution)."""
    return NO_SOLUTION if value is None else edges - value


def host_scores(hosts, arms, budget):
    """{arm: [score per host]} at one budget. Each host is {'edges', 'best_value', 'values': {arm: {budget: value or
    None}}}; the best known value must be at least every value recorded for the host."""
    out = {a: [] for a in arms}
    for h in hosts:
        best = h['best_value']
        for a in arms:
            v = h['values'][a].get(budget, h['values'][a].get(str(budget)))
            if v is not None and v > best:
                raise ValueError(f"{a} found {v} above the host's best known value {best}")
            out[a].append(score(cost(h['edges'], best), cost(h['edges'], v)))
    return out


def bootstrap_diff(a, b, level=0.90, resamples=4000, seed=0):
    """Mean of a - b over paired hosts and its percentile bootstrap interval at `level`."""
    k = len(a)
    if k == 0 or len(b) != k:
        raise ValueError('paired score lists of equal, positive length are required')
    d = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    sims = sorted(sum(d[rng.randrange(k)] for _ in range(k)) / k for _ in range(resamples))
    tail = (1 - level) / 2
    lo = sims[max(0, int(math.floor(tail * resamples)))]
    hi = sims[min(resamples - 1, int(math.ceil((1 - tail) * resamples)) - 1)]
    return sum(d) / k, (lo, hi)


def verdict(interval, delta):
    lo, hi = interval
    if lo > delta:
        return 'A_BETTER'
    if hi < -delta:
        return 'B_BETTER'
    if -delta <= lo and hi <= delta:
        return 'EQUIVALENT'
    return 'UNRESOLVED'


def compare(scores_a, scores_b, delta, level=0.90, resamples=4000, seed=0):
    est, ci = bootstrap_diff(scores_a, scores_b, level, resamples, seed)
    return {'mean_difference': round(est, 6), 'interval': [round(ci[0], 6), round(ci[1], 6)], 'level': level,
            'delta': delta, 'verdict': verdict(ci, delta)}


def ranking(scores):
    """Arms by average score, best first (the Evaluation's ranking)."""
    return sorted(((a, sum(v) / len(v)) for a, v in scores.items() if v), key=lambda kv: -kv[1])


# ------------------------------------------------------------------------------------------- sequential stopping

def look_level(alpha, looks):
    """The interval level used at every look: 1 - alpha / looks (Bonferroni over the looks)."""
    if looks < 1 or not 0 < alpha < 1:
        raise ValueError('looks >= 1 and 0 < alpha < 1 are required')
    return 1 - alpha / looks


def sequential(scores_a, scores_b, schedule, delta, alpha=0.10, stop_for_equivalence=False, resamples=4000,
               seed=0):
    """Run the preregistered looks on hosts in their preregistered order: `schedule` lists the host counts at which
    to look (increasing; the last is the full sample). Returns every look's result and where it stopped."""
    if list(schedule) != sorted(set(schedule)) or schedule[-1] > len(scores_a):
        raise ValueError('the schedule must be increasing and within the hosts available')
    level = look_level(alpha, len(schedule))
    stop = {'A_BETTER', 'B_BETTER'} | ({'EQUIVALENT'} if stop_for_equivalence else set())
    out = []
    for n in schedule:
        r = compare(scores_a[:n], scores_b[:n], delta, level, resamples, seed)
        r['hosts'] = n
        out.append(r)
        if r['verdict'] in stop:
            return {'looks': out, 'stopped_at': n, 'verdict': r['verdict'], 'level': level}
    return {'looks': out, 'stopped_at': None, 'verdict': out[-1]['verdict'], 'level': level}
