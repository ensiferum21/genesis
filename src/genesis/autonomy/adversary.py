"""The adversary (B20_R96): it searches for the hosts on which the system does worst, so the next study aims at the
system's weaknesses instead of the builder's guesses (co-evolving problems with solvers, as POET, Wang et al. 2019).

A point is a host family and its parameters inside the large domain's family space. Its hardness for the system is
measured by an injected function on a few hosts drawn at that point (in a study: the best champion's anytime score
minus the system's at equal time, or the system's gap to its certified bound). The search is a (mu + lambda)
evolution: the mu hardest points so far each produce lambda / mu mutants (parameters moved by a fraction of their
range, clipped); points are measured once and cached; the result is every point measured, hardest first.
"""
import random


def _clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def mutate_point(point, space, rng, scale=0.15):
    fam, params = point
    out = {}
    for k, v in params.items():
        lo, hi = space[fam][k]
        if k == 'n':
            out[k] = int(_clip(round(v + rng.gauss(0, scale * (hi - lo) / 4)), lo, hi))
        else:
            out[k] = round(_clip(v + rng.gauss(0, scale * (hi - lo)), lo, hi), 3)
    return (fam, out)


def search(space, starts, hardness, generations=4, mu=3, lam=6, seed=0):
    """`space`: {family: {param: (lo, hi)}}; `starts`: [(family, params)]; `hardness(point) -> float` (larger is
    harder for the system). Returns [(hardness, point)] for every point measured, hardest first."""
    rng = random.Random(seed)
    cache = {}

    def key(p):
        return (p[0], tuple(sorted(p[1].items())))

    def measure(p):
        k = key(p)
        if k not in cache:
            cache[k] = (float(hardness(p)), p)
        return cache[k][0]
    for p in starts:
        measure(p)
    for _ in range(generations):
        best = sorted(cache.values(), key=lambda hp: -hp[0])[:mu]
        for _, p in best:
            for _ in range(max(1, lam // mu)):
                measure(mutate_point(p, space, rng))
    return sorted(cache.values(), key=lambda hp: (-hp[0], str(key(hp[1]))))
