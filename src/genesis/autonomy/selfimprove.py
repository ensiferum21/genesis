"""Self-improvement on two levels (B20_R126): the system writes max-cut engines, and improves how it writes them.

Daniel, 24 Oct 2026: "I want it to be able to invent to improve itself multiple times better than us doing this
process and the process itself to be improved." This module is the machinery; the studies that test it are B20_R127
(level 1) and B20_R128 (level 2). Nothing here is a claim.

**Level 1, the inventor.** A genome is an `mcx2-v1` configuration: a search program over physics operators
(`candidate_kinds/mcx2.py`) and its options. The inventor searches that space with the steady-state evolutionary search
of `autonomy.feedback`, under the feedback contract version 2 (the judge holds confirmation splits B and C and releases
only improvements larger than its own noise), so that it cannot fool itself. Its operators:
  * `random_engine`: 1 to 6 statements (at least one B or b), every option drawn from the kind's space;
  * mutations, chosen by the PROCESS's weights: `arg` (rescale one statement's argument), `insert`, `delete`,
    `replace` (another operator at one place), `swap` (two adjacent statements), `option` (one option redrawn),
    `duplicate` (one statement repeated);
  * crossover: a one-point splice of the two programs, each option from either parent.

**Level 2, the process.** A PROCESS is the inventor's own settings: population, children per generation, leaders
re-evaluated, tournament size, crossover probability, and the weight of each mutation. `search(process, ...)` is
`feedback.steady_state_search` with those settings as parameters; with ORIGINAL (feedback's constants, equal weights)
it makes exactly the same draws and returns exactly the same result (a test checks it). A process is judged by what
it produces: the held-out score of the engine a level-1 search with that process returns, at a fixed evaluation
budget. `mutate_process` / `crossover_process` let a level-2 search evolve processes by that measure.

**What "better than us" means here.** An engine's score on a graph is its cut divided by the cut of the builder's
hybrid (REX, `mcx2` DEFAULT) on that graph at the same budget, so a score above 1 is better than the human design
there. The final judges are held-out graphs and Gset, in the studies.
"""
import copy
import json
import math
import random
import statistics

from ..candidate_kinds import mcx2 as K
from . import feedback as FB

MUTATIONS = ('arg', 'insert', 'delete', 'replace', 'swap', 'option', 'duplicate')
ORIGINAL = {'pop': FB.POP, 'children': FB.CHILDREN, 'leaders': FB.LEADERS, 'tournament': FB.TOURNAMENT,
            'p_cross': FB.P_CROSS, 'weights': {m: 1.0 for m in MUTATIONS}}
PROCESS_SPACE = {'pop': (8, 12, 16, 24, 32), 'children': (4, 8, 12, 16), 'leaders': (0, 1, 2, 4),
                 'tournament': (2, 3, 4, 6), 'p_cross': (0.0, 0.1, 0.25, 0.5),
                 'weight': (0.25, 0.5, 1.0, 2.0, 4.0)}
_ARG_OPS = tuple(K.ARG_RANGE)
_ALL_OPS = tuple(K.OPS)


# ---------------------------------------------------------------------------------------------------- level 1: engines

def _random_stmt(rng, op=None):
    op = op or rng.choice(_ALL_OPS)
    if op in K.ARG_RANGE:
        lo, hi = K.ARG_RANGE[op]
        hi = min(hi, {'B': 2000, 'b': 2000, 'S': 100000, 'P': 20}[op])
        return (op, int(round(math.exp(rng.uniform(math.log(lo), math.log(hi))))))
    return (op, None)


def _valid(cfg):
    return K.check_config(cfg) is None


def random_engine(rng):
    while True:
        n = rng.randint(1, 6)
        st = [_random_stmt(rng) for _ in range(n)]
        if not any(op in 'Bb' for op, _ in st):
            st[rng.randrange(n)] = _random_stmt(rng, rng.choice('Bb'))
        cfg = {k: rng.choice(v) for k, v in K.SPACE.items()}
        cfg['prog'] = K.render(st)
        if _valid(cfg):
            return cfg


def mutate(cfg, rng, weights=None):
    weights = weights or ORIGINAL['weights']
    kinds = list(MUTATIONS)
    for _ in range(50):
        c = copy.deepcopy(cfg)
        st = K.statements(c['prog'])
        m = rng.choices(kinds, [weights[k] for k in kinds])[0]
        i = rng.randrange(len(st))
        if m == 'arg':
            idx = [j for j, (op, a) in enumerate(st) if a is not None]
            if not idx:
                continue
            j = rng.choice(idx)
            op, a = st[j]
            lo, hi = K.ARG_RANGE[op]
            st[j] = (op, max(lo, min(hi, int(round(a * math.exp(rng.uniform(-math.log(10), math.log(10))))))))
        elif m == 'insert':
            st.insert(rng.randint(0, len(st)), _random_stmt(rng))
        elif m == 'delete':
            if len(st) < 2:
                continue
            del st[i]
        elif m == 'replace':
            st[i] = _random_stmt(rng)
        elif m == 'swap':
            if len(st) < 2:
                continue
            j = rng.randrange(len(st) - 1)
            st[j], st[j + 1] = st[j + 1], st[j]
        elif m == 'option':
            k = rng.choice(sorted(K.SPACE))
            c[k] = rng.choice(K.SPACE[k])
        else:
            st.insert(i, st[i])
        if len(st) > K.MAX_STATEMENTS or not any(op in 'Bb' for op, _ in st):
            continue
        c['prog'] = K.render(st)
        if _valid(c) and c != cfg:
            return c
    return copy.deepcopy(cfg)


def crossover(a, b, rng):
    for _ in range(20):
        sa, sb = K.statements(a['prog']), K.statements(b['prog'])
        st = sa[:rng.randint(0, len(sa))] + sb[rng.randint(0, len(sb)):]
        if not st or len(st) > K.MAX_STATEMENTS or not any(op in 'Bb' for op, _ in st):
            continue
        c = {k: (a[k] if rng.random() < 0.5 else b[k]) for k in K.SPACE}
        c['prog'] = K.render(st)
        if _valid(c) and c != a:
            return c
    return mutate(a, rng)


def size(cfg):
    return len(K.statements(cfg['prog']))


def engine_ops(weights=None):
    return {'random': random_engine, 'mutate': lambda p, rng: mutate(p, rng, weights),
            'crossover': crossover, 'size': size}


# ----------------------------------------------------------------------------- the search, with the process as data

def check_process(proc):
    if not isinstance(proc, dict) or set(proc) != set(ORIGINAL):
        return f'a process gives exactly {sorted(ORIGINAL)}'
    for k in ('pop', 'children', 'leaders', 'tournament', 'p_cross'):
        if proc[k] not in PROCESS_SPACE[k] and proc[k] != ORIGINAL[k]:
            return f'{k} must be one of {PROCESS_SPACE[k]}'
    if set(proc['weights']) != set(MUTATIONS) or any(
            w not in PROCESS_SPACE['weight'] and w != 1.0 for w in proc['weights'].values()):
        return f'weights: one of {PROCESS_SPACE["weight"]} for each of {MUTATIONS}'
    if proc['tournament'] > proc['pop'] or proc['leaders'] > proc['pop']:
        return 'tournament and leaders cannot exceed the population'
    return None


def search(process, ops, evaluate, max_evals, seed, contract=True, calibrate='BC', cost=None):
    """`feedback.steady_state_search` with the process's settings in place of feedback's constants."""
    why = check_process(process)
    if why:
        raise ValueError(why)
    saved = (FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS)
    FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS = (process['pop'], process['children'],
                                                                   process['leaders'], process['tournament'],
                                                                   process['p_cross'])
    try:
        return FB.steady_state_search(ops, evaluate, max_evals, seed, contract=contract, calibrate=calibrate,
                                      cost=cost)
    finally:
        FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS = saved


# ----------------------------------------------------------------------------------------- level 2: processes

def random_process(rng):
    while True:
        p = {k: rng.choice(PROCESS_SPACE[k]) for k in ('pop', 'children', 'leaders', 'tournament', 'p_cross')}
        p['weights'] = {m: rng.choice(PROCESS_SPACE['weight']) for m in MUTATIONS}
        if check_process(p) is None:
            return p


def mutate_process(proc, rng):
    for _ in range(50):
        p = copy.deepcopy(proc)
        k = rng.choice(('pop', 'children', 'leaders', 'tournament', 'p_cross', 'weights', 'weights'))
        if k == 'weights':
            m = rng.choice(MUTATIONS)
            p['weights'][m] = rng.choice(PROCESS_SPACE['weight'])
        else:
            p[k] = rng.choice(PROCESS_SPACE[k])
        if check_process(p) is None and p != proc:
            return p
    return copy.deepcopy(proc)


def crossover_process(a, b, rng):
    for _ in range(20):
        p = {k: (a[k] if rng.random() < 0.5 else b[k]) for k in ('pop', 'children', 'leaders', 'tournament', 'p_cross')}
        p['weights'] = {m: (a['weights'][m] if rng.random() < 0.5 else b['weights'][m]) for m in MUTATIONS}
        if check_process(p) is None:
            return p
    return mutate_process(a, rng)


def key(x):
    return json.dumps(x, sort_keys=True)


def summary_stats(values):
    return {'mean': statistics.mean(values), 'n': len(values),
            'sd': statistics.stdev(values) if len(values) > 1 else 0.0}


__all__ = ['MUTATIONS', 'ORIGINAL', 'PROCESS_SPACE', 'random_engine', 'mutate', 'crossover', 'size', 'engine_ops',
           'check_process', 'search', 'random_process', 'mutate_process', 'crossover_process', 'key']
