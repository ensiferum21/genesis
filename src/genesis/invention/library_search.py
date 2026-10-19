"""Program search with a library (B20_R82): B20_R78's search, unchanged in its algorithm and constants
(`solver_search`), over programs that may call a fixed library of earlier generations' discoveries
(`solver_library`). With an empty library it is the same search over the same language as B20_R79's, which makes it
the control for the library's effect: the only difference between a generation and its control is the library.
"""
import json
import random
import statistics
import time

from ..common import digest
from . import solver_library as SL
from . import solver_search as SS


def _seed(program, task_id, round_):
    return int(digest({'program': program, 'task': task_id, 'round': round_})[:12], 16)


def evaluate(program, rep_by_id, hosts, budget, round_):
    rep = rep_by_id[program['rep']]
    vals = [len(SL.run(program, rep, t.n, t.edges, budget, _seed(program, t.task_id, round_))) for t in hosts]
    return statistics.mean(vals), vals


class Entry(SS.Entry):
    def __init__(self, program):
        self.program = program
        self.key = json.dumps(program, sort_keys=True)
        self.scores = []
        self.size = SL.size(program)


def search(hosts, reps, rep_by_id, library, seconds, seed, log=print, history=None):
    """As `solver_search.search`, with every program carrying `library`; returns (winner, report)."""
    rng = random.Random(seed)
    t_end = time.process_time() + seconds
    seen, evals = {}, 0

    def score(e):
        nonlocal evals
        mean, vals = evaluate(e.program, rep_by_id, hosts, SS.BUDGET, len(e.scores))
        e.scores.append(mean)
        evals += 1
        if history is not None:
            history.append({'body': e.program['body'], 'rep': e.program['rep'], 'round': len(e.scores) - 1,
                            'mean': round(mean, 4), 'values': vals,
                            'cpu_s': round(time.process_time() - (t_end - seconds), 2)})

    def new(program):
        key = json.dumps(program, sort_keys=True)
        if key in seen:
            return None
        e = seen[key] = Entry(program)
        score(e)
        return e

    pop = []
    while len(pop) < SS.POP:
        e = new(SL.random_program(rng, reps, library))
        if e is not None:
            pop.append(e)
    gen = 0
    while time.process_time() < t_end:
        gen += 1
        pop.sort(key=Entry.rank)

        def pick():
            return min(rng.sample(pop, SS.TOURNAMENT), key=Entry.rank)
        children, tries = [], 0
        while len(children) < SS.CHILDREN and tries < 10 * SS.CHILDREN and time.process_time() < t_end:
            tries += 1
            p = (SL.crossover(pick().program, pick().program, rng, reps) if rng.random() < SS.P_CROSS
                 else SL.mutate(pick().program, rng, reps))
            e = new(p)
            if e is not None:
                children.append(e)
        for e in pop[:SS.LEADERS]:
            if time.process_time() < t_end:
                score(e)
        pop = sorted(pop + children, key=Entry.rank)[:SS.POP]
        if gen % 10 == 0:
            b = pop[0]
            log(f'gen {gen}: {evals} evaluations, best {b.fitness:.2f} over {len(b.scores)} (size {b.size}) '
                f'{json.dumps(b.program["body"])} rep {b.program["rep"]}')
    pop.sort(key=Entry.rank)
    finals = []
    for e in pop[:SS.FINALISTS]:
        vals = [evaluate(e.program, rep_by_id, hosts, b, 1000 + s)[0] for b in SS.FINAL_BUDGETS
                for s in range(SS.FINAL_SEEDS)]
        finals.append((statistics.mean(vals), e))
        log(f'finalist {statistics.mean(vals):.2f} (search fitness {e.fitness:.2f}, size {e.size}) '
            f'{json.dumps(e.program["body"])} rep {e.program["rep"]}')
    best = max(finals, key=lambda x: (x[0], -x[1].size, x[1].key))[1]
    report = {'generations': gen, 'evaluations': evals, 'distinct_programs': len(seen),
              'finalists': [{'body': e.program['body'], 'rep': e.program['rep'], 'final_mean': round(m, 4),
                             'search_fitness': round(e.fitness, 4), 'size': e.size} for m, e in finals],
              'macro_use_in_final_population': sum(any(s[0] == 'macro' for b, _ in SL._blocks(e.program) for s in b)
                                                   for e in pop)}
    return best.program, report
