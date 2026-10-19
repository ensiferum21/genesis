"""Program search over the solver language (B20_R78): the system looks for a solver itself.

A standard steady-state evolutionary search over programs (genetic programming: Koza 1992; hyper-heuristics that
generate heuristics, Burke et al. 2010), with no human-written program in it: the population starts from random
programs of `solver_programs.random_program`, and children come from `mutate` and `crossover`.

Fitness: the mean, over the training hosts, of the size of the best edge set the program finds in BUDGET CPU
seconds (one run per host, in process, seeded from the program, the host and the evaluation round). A program that
is evaluated again (the current leaders are, each generation) keeps the mean of its evaluations, so a lucky run is
diluted. Ties are broken towards smaller programs.

Loop (all constants fixed): POP random programs; then, until the search's CPU time is spent: CHILDREN children,
each by crossover of two tournament winners (probability P_CROSS) or by mutation of one (tournament of TOURNAMENT);
the LEADERS best programs are evaluated once more; the population keeps the POP best of parents and children.
Final choice: the FINALISTS best programs are each run on every training host at FINAL_BUDGETS with FINAL_SEEDS
fresh seeds; the highest mean wins (ties: smaller). The search sees only its training hosts.
"""
import json
import random
import statistics
import time

from ..common import digest
from . import solver_programs as SP

POP, CHILDREN, LEADERS, TOURNAMENT, P_CROSS = 16, 8, 2, 3, 0.25
BUDGET = 0.25
FINALISTS, FINAL_BUDGETS, FINAL_SEEDS = 4, (0.25, 1.0), 2


def _seed(program, task_id, round_):
    return int(digest({'program': program, 'task': task_id, 'round': round_})[:12], 16)


def evaluate(program, rep_by_id, hosts, budget, round_):
    """Mean best size over the hosts, one run each."""
    rep = rep_by_id[program['rep']]
    vals = [len(SP.run(program, rep, t.n, t.edges, budget, _seed(program, t.task_id, round_))) for t in hosts]
    return statistics.mean(vals), vals


class Entry:
    def __init__(self, program):
        self.program = program
        self.key = json.dumps(program, sort_keys=True)
        self.scores = []
        self.size = SP.size(program)

    @property
    def fitness(self):
        return statistics.mean(self.scores)

    def rank(self):
        return (-self.fitness, self.size, self.key)


def search(hosts, reps, rep_by_id, seconds, seed, log=print, history=None):
    """Run the search for `seconds` of CPU time; returns (winner program, report)."""
    rng = random.Random(seed)
    t_end = time.process_time() + seconds
    seen = {}
    evals = 0

    def score(e):
        nonlocal evals
        mean, vals = evaluate(e.program, rep_by_id, hosts, BUDGET, len(e.scores))
        e.scores.append(mean)
        evals += 1
        if history is not None:
            history.append({'program': e.program, 'round': len(e.scores) - 1, 'mean': round(mean, 4),
                            'values': vals, 'cpu_s': round(time.process_time() - (t_end - seconds), 2)})

    def new(program):
        key = json.dumps(program, sort_keys=True)
        if key in seen:
            return None
        e = seen[key] = Entry(program)
        score(e)
        return e

    pop = []
    while len(pop) < POP:
        e = new(SP.random_program(rng, reps))
        if e is not None:
            pop.append(e)
    gen = 0
    while time.process_time() < t_end:
        gen += 1
        pop.sort(key=Entry.rank)

        def pick():
            return min(rng.sample(pop, TOURNAMENT), key=Entry.rank)
        children = []
        tries = 0
        while len(children) < CHILDREN and tries < 10 * CHILDREN and time.process_time() < t_end:
            tries += 1
            p = (SP.crossover(pick().program, pick().program, rng, reps) if rng.random() < P_CROSS
                 else SP.mutate(pick().program, rng, reps))
            e = new(p)
            if e is not None:
                children.append(e)
        for e in pop[:LEADERS]:
            if time.process_time() < t_end:
                score(e)
        pop = sorted(pop + children, key=Entry.rank)[:POP]
        if gen % 10 == 0:
            b = pop[0]
            log(f'gen {gen}: {evals} evaluations, best {b.fitness:.2f} over {len(b.scores)} '
                f'(size {b.size}) {b.key}')
    pop.sort(key=Entry.rank)
    finals = []
    for e in pop[:FINALISTS]:
        vals = []
        for b in FINAL_BUDGETS:
            for s in range(FINAL_SEEDS):
                vals.append(evaluate(e.program, rep_by_id, hosts, b, 1000 + s)[0])
        finals.append((statistics.mean(vals), e))
        log(f'finalist {statistics.mean(vals):.2f} (search fitness {e.fitness:.2f}, size {e.size}) {e.key}')
    best = max(finals, key=lambda x: (x[0], -x[1].size, x[1].key))[1]
    report = {'generations': gen, 'evaluations': evals, 'distinct_programs': len(seen),
              'finalists': [{'program': e.program, 'final_mean': round(m, 4), 'search_fitness': round(e.fitness, 4),
                             'search_evaluations': len(e.scores), 'size': e.size} for m, e in finals],
              'population': [{'program': e.program, 'fitness': round(e.fitness, 4), 'evaluations': len(e.scores)}
                             for e in pop]}
    return best.program, report


def anatomy(program):
    """Which kinds of step the program uses (for the rediscovery question; descriptive)."""
    used = []

    def walk(b):
        for s in b:
            used.append(tuple(s[:3]) if s[0] in ('edges', 'sweep') else tuple(s[:3]) if s[0] == 'relabel' else (s[0],))
            if s[0] == 'repeat':
                walk(s[2])
            elif s[0] == 'loop':
                walk(s[1])
            elif s[0] == 'split':
                walk(s[2])
                walk(s[3])
    walk(program['body'])
    ops = {u[0] for u in used}
    return {'representation': program['rep'],
            'swap_like': any(u[0] in ('edges', 'sweep') and u[1] == 'drop' and u[2] in ('improve', 'sideways')
                             for u in used),
            'kick': any(u[0] in ('edges', 'sweep') and u[1] == 'force' for u in used),
            'cut_search': bool(ops & {'descent', 'relabel'}),
            'restarts': 'init' in ops,
            'phases': 'split' in ops,
            'returns_to_best': 'best' in ops,
            'steps': sorted({' '.join(map(str, u)) for u in used})}
