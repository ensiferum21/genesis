"""The feedback contract (B20_R103): what a research worker may learn from the judge while it searches.

Why (Daniel's research alert of 22 Oct 2026, `docs/RESEARCH_ALERTS.md`). A search that selects on repeated feedback
from the same evaluation data reports gains where none exist. Two things inflate it:
  * the best of many noisy measurements lies above the truth (the winner's curse);
  * every candidate has a persistent quirk on the particular evaluation data that no re-run removes (overfitting the
    validation set).
Genesis's claims are judged on fresh hosts, so the claims are protected; the searches themselves were not, and were
never shown to stop on a problem without signal. In Genesis's own program searches (B20_R79-R85), one evaluation's
noise is 0.12-0.18 edges, and the top tenth of all evaluated programs spans only about 0.3 edges: most of the
progress at the top is within noise.

The contract (fixed; the fixed-threshold variant, the one the alert's guarantee covers; a "ladder" in the sense of
Blum and Hardt, ICML 2015):
  * **Data.** Split in two. The worker searches freely on A, its training data, as before. The judge holds B, which the
    worker never sees, and keeps every B evaluation privately. The final number is measured on held-out test data
    neither has seen.
  * **Calibration** (once, before any submission). The initial population and CALIBRATION_EXTRA more random programs
    are each evaluated once on A and once on B. Over those programs the differences A - B cancel each program's true
    quality and keep both kinds of noise; their standard deviation is the noise of a difference between two programs
    on B. tau = Z x its 90% upper confidence limit (chi-square), so that an unlucky calibration does not lower the bar.
    tau is fixed for the whole search.
  * **Submission.** After every generation, the worker may submit its current best program. The judge evaluates each
    distinct program on B at most once, so resubmitting cannot fish for luck. If the program beats the incumbent's B
    score by more than tau, it is *released*: it becomes the incumbent, and the worker learns its B score. Otherwise
    the worker learns "not better", and no number.
  * **Stop.** PATIENCE generations in a row without a release end the search, as does the evaluation budget.
  * **Report.** The reported number is the incumbent's released B score, never a training score.

`steady_state_search` is `invention.solver_search`'s program search: the same constants, tournament, crossover,
mutation, leader re-evaluation and final choice. The evaluation is passed in, and the budget is counted in
evaluations so that runs replicate exactly. Without a judge, it reports its final choice's mean of FINAL_EVALS fresh
evaluations on A, as `solver_search` reports its training means.
"""
import json
import random
import statistics

POP, CHILDREN, LEADERS, TOURNAMENT, P_CROSS = 16, 8, 2, 3, 0.25
FINALISTS, FINAL_EVALS = 4, 4
CALIBRATION_EXTRA = 16
Z, PATIENCE = 3.0, 40     # Z: a false release per submission at most P(N(0,1) > 3) = 0.13%, so about 5% over a
                         # stalled search of PATIENCE submissions (development looks with Z = 2.5 released noise)


class Judge:
    """Holds the confirmation data B; releases a submission only if it beats the incumbent by more than tau."""

    def __init__(self, evaluate, calibration, incumbent, z=Z, patience=PATIENCE):
        self.evaluate, self.patience = evaluate, patience
        self.start_program = incumbent
        from scipy.stats import chi2
        diffs = [evaluate(p, 'A') - evaluate(p, 'B') for p in calibration]
        k = len(diffs) - 1
        self.tau = z * statistics.stdev(diffs) * (k / chi2.ppf(0.10, k)) ** 0.5
        self.seen = {}
        self.incumbent = incumbent
        self.best = self.start = self._b(incumbent)
        self.releases = self.submissions = self.run_of_rejections = 0
        self.private = [('calibration', [round(d, 6) for d in diffs]), ('start', self.start)]

    def _b(self, program):
        key = json.dumps(program, sort_keys=True)
        if key not in self.seen:
            self.seen[key] = self.evaluate(program, 'B')
        return self.seen[key]

    def submit(self, program):
        """The released B score, or None ("not better")."""
        key = json.dumps(program, sort_keys=True)
        fresh = key not in self.seen
        y = self._b(program)
        if not fresh:                                  # already judged: the same answer, nothing new; a generation
            self.run_of_rejections += 1                # without a release counts towards stopping
            return None
        self.submissions += 1
        self.private.append(('submission', round(y, 6)))
        if y > self.best + self.tau:
            self.best, self.incumbent = y, program
            self.releases += 1
            self.run_of_rejections = 0
            return y
        self.run_of_rejections += 1
        return None

    @property
    def stopped(self):
        return self.run_of_rejections >= self.patience


class Entry:
    def __init__(self, program, size):
        self.program, self.size = program, size
        self.key = json.dumps(program, sort_keys=True)
        self.scores = []

    @property
    def fitness(self):
        return statistics.mean(self.scores)

    def rank(self):
        return (-self.fitness, self.size, self.key)


def steady_state_search(ops, evaluate, max_evals, seed, contract=False):
    """`invention.solver_search`'s algorithm with the evaluation passed in and an evaluation budget.

    ops: {'random': f(rng), 'mutate': f(p, rng), 'crossover': f(a, b, rng), 'size': f(p)};
    evaluate(program, split) -> float with split 'A' (the worker's data) or 'B' (the judge's).
    Returns (winner, report); report['reported'] is the number the worker would report."""
    rng = random.Random(seed)
    seen = {}
    count = [0]

    def ev(p, split):
        count[0] += 1
        return evaluate(p, split)

    def score(e):
        e.scores.append(ev(e.program, 'A'))

    def new(program):
        key = json.dumps(program, sort_keys=True)
        if key in seen:
            return None
        e = seen[key] = Entry(program, ops['size'](program))
        score(e)
        return e

    J = None

    def left():
        return count[0] < max_evals and not (J is not None and J.stopped)

    pop = []
    while len(pop) < POP and left():
        e = new(ops['random'](rng))
        if e is not None:
            pop.append(e)
    if contract:
        pop.sort(key=Entry.rank)
        extra = []
        while len(extra) < CALIBRATION_EXTRA:
            p = ops['random'](rng)
            k = json.dumps(p, sort_keys=True)
            if k not in seen and all(json.dumps(x, sort_keys=True) != k for x in extra):
                extra.append(p)
        J = Judge(ev, [e.program for e in pop] + extra, pop[0].program)
    gen = 0
    while left():
        gen += 1
        pop.sort(key=Entry.rank)

        def pick():
            return min(rng.sample(pop, TOURNAMENT), key=Entry.rank)
        children = []
        tries = 0
        while len(children) < CHILDREN and tries < 10 * CHILDREN and left():
            tries += 1
            p = (ops['crossover'](pick().program, pick().program, rng) if rng.random() < P_CROSS
                 else ops['mutate'](pick().program, rng))
            e = new(p)
            if e is not None:
                children.append(e)
        for e in pop[:LEADERS]:
            if left():
                score(e)
        pop = sorted(pop + children, key=Entry.rank)[:POP]
        if J is not None and left():
            J.submit(pop[0].program)
    pop.sort(key=Entry.rank)
    if J is None:
        finals = []
        for e in pop[:FINALISTS]:
            finals.append((statistics.mean(ev(e.program, 'A') for _ in range(FINAL_EVALS)), e))
        reported, best = max(finals, key=lambda x: (x[0], -x[1].size, x[1].key))
        winner = best.program
    else:
        winner, reported = J.incumbent, J.best
    return winner, {'generations': gen, 'evaluations': count[0], 'distinct_programs': len(seen),
                    'reported': reported,
                    'judge': None if J is None else {'tau': J.tau, 'start': J.start, 'releases': J.releases,
                                                     'submissions': J.submissions, 'stopped': J.stopped}}
