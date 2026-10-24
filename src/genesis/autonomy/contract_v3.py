"""A candidate feedback contract, version 3 (research plane; under test in B20_R132; adopted nowhere).

**The protected judge is untouched.** `autonomy/feedback.py` (the contract versions 1 and 2) is not modified, and
every claim Genesis makes under the contract keeps using it. This module reuses its `Judge` class unchanged, and its
search algorithm, so that the only difference version 3 makes is the set of programs the judge calibrates on.
Adopting version 3 for any claim is a decision for the human supervisor.

**Why a candidate.** In B20_R127 the judge released nothing in nine engine searches: the best training gains
(+0.04% to +0.24%) were 4 to 60 times smaller than tau (0.75% to 2.45%). Version 2 calibrates tau on B - C differences
of RANDOM programs (the initial population and extra random ones). Random engines differ from one another far more,
split by split, than the near-incumbent programs a search actually submits, so their B - C differences may overstate
the noise of the comparisons the judge makes.

**Version 3.** The judge calibrates on LOCAL_CALIBRATION distinct one-step mutations of its starting incumbent
(`local_calibration`; drawn with a generator of their own, seeded from the search's seed and the incumbent). The
formula (tau = Z x the standard deviation of the B - C differences x its 90% chi-square upper factor), the release
rule, submissions, stopping and reporting are version 2's (`feedback.Judge` with `calibrate='BC'`).

**The same search.** `steady_state_search` is `feedback.steady_state_search`'s algorithm, line for line; with
`calibration='BC'` it returns exactly what `feedback.steady_state_search(..., calibrate='BC')` returns (a test checks
it). With `calibration='local'` it still draws version 2's extra calibration programs (and discards them), so the two
versions make the same draws: given evaluations that depend only on (program, split, occurrence), they evaluate the
same programs in the same order until one of them stops.

**What is not known.** Whether version 3 releases true improvements, and only those, on real engines: B20_R132
measures it against the truth on fresh graphs, with planted gains of known size and a zero-signal control. Submissions
far from the incumbent (crossovers of distant programs) may carry more noise than the local calibration sees.
"""
import json
import random

from . import feedback as FB

LOCAL_CALIBRATION = 16


def local_calibration(ops, incumbent, seed, n=None):
    """n (LOCAL_CALIBRATION) distinct one-step mutations of the incumbent, none equal to it, drawn with a generator of
    their own (seeded from the search's seed and the incumbent)."""
    n = LOCAL_CALIBRATION if n is None else n
    inc = json.dumps(incumbent, sort_keys=True)
    rng = random.Random(f'{seed}|local|{inc}')
    out, keys, tries = [], {inc}, 0
    while len(out) < n and tries < 50 * n:
        tries += 1
        p = ops['mutate'](incumbent, rng)
        k = json.dumps(p, sort_keys=True)
        if k not in keys:
            keys.add(k)
            out.append(p)
    if len(out) < 3:
        raise ValueError('fewer than 3 distinct mutations of the incumbent: version 3 cannot calibrate')
    return out


def steady_state_search(ops, evaluate, max_evals, seed, calibration='local', cost=None, constants=None):
    """`feedback.steady_state_search(..., contract=True, calibrate='BC')`'s algorithm; `calibration` 'BC' (version 2's
    calibration set) or 'local' (version 3's). `constants`: {'pop', 'children', 'leaders', 'tournament', 'p_cross',
    'calib_extra'} (default: feedback's). Returns (winner, report) as feedback's does."""
    if calibration not in ('BC', 'local'):
        raise ValueError("calibration must be 'BC' or 'local'")
    c = {'pop': FB.POP, 'children': FB.CHILDREN, 'leaders': FB.LEADERS, 'tournament': FB.TOURNAMENT,
         'p_cross': FB.P_CROSS, 'calib_extra': FB.CALIBRATION_EXTRA}
    c.update(constants or {})
    rng = random.Random(seed)
    seen = {}
    count = [0]
    cost = cost or {}

    def ev(p, split):
        count[0] += cost.get(split, 1)
        return evaluate(p, split)

    def score(e):
        e.scores.append(ev(e.program, 'A'))

    def new(program):
        key = json.dumps(program, sort_keys=True)
        if key in seen:
            return None
        e = seen[key] = FB.Entry(program, ops['size'](program))
        score(e)
        return e

    J = None

    def left():
        return count[0] < max_evals and not (J is not None and J.stopped)

    pop = []
    while len(pop) < c['pop'] and left():
        e = new(ops['random'](rng))
        if e is not None:
            pop.append(e)
    pop.sort(key=FB.Entry.rank)
    extra = []
    while len(extra) < c['calib_extra']:
        p = ops['random'](rng)
        k = json.dumps(p, sort_keys=True)
        if k not in seen and all(json.dumps(x, sort_keys=True) != k for x in extra):
            extra.append(p)
    if calibration == 'local':
        J = FB.Judge(ev, local_calibration(ops, pop[0].program, seed), pop[0].program, calibrate='BC')
    else:
        J = FB.Judge(ev, [e.program for e in pop] + extra, pop[0].program, calibrate='BC')
    gen = 0
    while left():
        gen += 1
        pop.sort(key=FB.Entry.rank)

        def pick():
            return min(rng.sample(pop, c['tournament']), key=FB.Entry.rank)
        children = []
        tries = 0
        while len(children) < c['children'] and tries < 10 * c['children'] and left():
            tries += 1
            p = (ops['crossover'](pick().program, pick().program, rng) if rng.random() < c['p_cross']
                 else ops['mutate'](pick().program, rng))
            e = new(p)
            if e is not None:
                children.append(e)
        for e in pop[:c['leaders']]:
            if left():
                score(e)
        pop = sorted(pop + children, key=FB.Entry.rank)[:c['pop']]
        if left():
            J.submit(pop[0].program)
    return J.incumbent, {'generations': gen, 'evaluations': count[0], 'distinct_programs': len(seen),
                         'reported': J.best,
                         'judge': {'tau': J.tau, 'start': J.start, 'releases': J.releases,
                                   'submissions': J.submissions, 'stopped': J.stopped}}


__all__ = ['LOCAL_CALIBRATION', 'local_calibration', 'steady_state_search']
