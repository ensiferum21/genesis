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

**Amendment (24 Oct 2026, before any study ran; Daniel: "use this to adapt and make it even better").** Three
additions, all data the process level can choose:
  * `algorithm`: 'steady' (the contract's steady-state search, as above) or 'map-elites', a quality-diversity
    archive (Mouret and Clune 2015) whose cells are engine traits (`descriptor`: how many levels, which kinds of
    physics operator the program uses); parents are drawn from the archive's cells, children enter a cell if they
    rank better than its occupant, and the archive's best is submitted to the same judge every generation;
  * `calib_extra`: how many extra random engines calibrate the judge (feedback's CALIBRATION_EXTRA, 16 in ORIGINAL);
    with the population, it sets how much of the budget goes to confirming instead of searching;
  * `seeded_ops(ops, seeds)`: a search that starts from given engines (the system's own earlier winners, for
    generations that compound) before drawing random ones.

**Second amendment (24 Oct 2026, 09:51; Daniel: "We can learn from failures too right?"), before any study ran:**
  * `adapt` (a process setting): adaptive operator selection, learning from failure inside a search (prior art:
    probability matching, Goldberg 1990; Fialho et al. 2010). Every child made by a mutation is credited with whether
    its first score reached its parent's; each kind of mutation is then chosen in proportion to its process weight
    times its smoothed success rate ((successes + 1) / (attempts + 2)), so kinds that keep failing are tried less;
  * a library of MACROS, building blocks the inventor learns from its own best engines: `learn_macros` finds the
    contiguous runs of 2 to 4 statements that recur most in the given engines' programs, and with a library
    `engine_ops` adds a `macro` mutation that inserts one (in the spirit of library learning, e.g. DreamCoder, Ellis et
    al. 2021). Macros are expanded in the program, so the engine and its checks are unchanged.

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
            'p_cross': FB.P_CROSS, 'weights': {m: 1.0 for m in MUTATIONS}, 'algorithm': 'steady',
            'calib_extra': FB.CALIBRATION_EXTRA, 'adapt': False}
PROCESS_SPACE = {'pop': (8, 12, 16, 24, 32), 'children': (4, 8, 12, 16), 'leaders': (0, 1, 2, 4),
                 'tournament': (2, 3, 4, 6), 'p_cross': (0.0, 0.1, 0.25, 0.5),
                 'weight': (0.25, 0.5, 1.0, 2.0, 4.0), 'algorithm': ('steady', 'map-elites'),
                 'calib_extra': (4, 8, 16), 'adapt': (False, True)}
SCALARS = ('pop', 'children', 'leaders', 'tournament', 'p_cross', 'algorithm', 'calib_extra', 'adapt')
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


def mutate(cfg, rng, weights=None, library=None, used=None):
    """A valid mutant. `library`: macros (lists of statements) for the `macro` mutation; `used`: a list that receives
    the kind of mutation made."""
    weights = weights or ORIGINAL['weights']
    kinds = list(MUTATIONS) + (['macro'] if library else [])
    for _ in range(50):
        c = copy.deepcopy(cfg)
        st = K.statements(c['prog'])
        m = rng.choices(kinds, [weights.get(k, 1.0) for k in kinds])[0]
        i = rng.randrange(len(st))
        if m == 'macro':
            st[i:i] = list(rng.choice(library))
        elif m == 'arg':
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
            if used is not None:
                used.append(m)
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


def engine_ops(weights=None, library=None):
    return {'random': random_engine, 'mutate': lambda p, rng: mutate(p, rng, weights, library),
            'crossover': crossover, 'size': size, 'library': library}


def learn_macros(engines, k=6):
    """The k contiguous runs of 2-4 statements that recur most (in at least two places) in the engines' programs,
    longest first among equals; ties by first appearance."""
    counts, first = {}, {}
    for e in engines:
        st = K.statements(e['prog'])
        for n in (2, 3, 4):
            for i in range(len(st) - n + 1):
                g = tuple(st[i:i + n])
                counts[g] = counts.get(g, 0) + 1
                first.setdefault(g, len(first))
    ranked = sorted((g for g, c in counts.items() if c >= 2), key=lambda g: (-counts[g], -len(g), first[g]))
    return [list(g) for g in ranked[:k]]


class Adaptive:
    """Adaptive operator selection: wraps the operators and the evaluation so that every mutation kind is credited
    with whether its children's first A score reached their parent's latest, and draws kinds in proportion to
    weight x (successes + 1) / (attempts + 2)."""

    def __init__(self, weights, library=None):
        self.base = dict(weights)
        self.library = library
        self.stats = {k: [0, 0] for k in list(MUTATIONS) + ['macro']}
        self.pending = {}          # child key -> (kind, parent key)
        self.last = {}             # program key -> its latest A score

    def weights(self):
        return {k: self.base.get(k, 1.0) * (s + 1) / (a + 2) for k, (s, a) in self.stats.items()}

    def ops(self):
        def mut(p, rng):
            used = []
            c = mutate(p, rng, self.weights(), self.library, used)
            if used:
                self.pending[key(c)] = (used[0], key(p))
            return c
        return {'random': random_engine, 'mutate': mut, 'crossover': crossover, 'size': size}

    def evaluate(self, evaluate):
        def ev(p, split):
            v = evaluate(p, split)
            if split == 'A':
                k = key(p)
                if k in self.pending:
                    kind, parent = self.pending.pop(k)
                    st = self.stats[kind]
                    st[1] += 1
                    if parent in self.last and v >= self.last[parent]:
                        st[0] += 1
                self.last[k] = v
            return v
        return ev


# ----------------------------------------------------------------------------- the search, with the process as data

def check_process(proc):
    if not isinstance(proc, dict) or set(proc) != set(ORIGINAL):
        return f'a process gives exactly {sorted(ORIGINAL)}'
    for k in SCALARS:
        if proc[k] not in PROCESS_SPACE[k] and proc[k] != ORIGINAL[k]:
            return f'{k} must be one of {PROCESS_SPACE[k]}'
    if set(proc['weights']) != set(MUTATIONS) or any(
            w not in PROCESS_SPACE['weight'] and w != 1.0 for w in proc['weights'].values()):
        return f'weights: one of {PROCESS_SPACE["weight"]} for each of {MUTATIONS}'
    if proc['tournament'] > proc['pop'] or proc['leaders'] > proc['pop']:
        return 'tournament and leaders cannot exceed the population'
    return None


def search(process, ops, evaluate, max_evals, seed, contract=True, calibrate='BC', cost=None):
    """The process's algorithm with its settings: 'steady' is `feedback.steady_state_search` with the process's
    settings in place of feedback's constants; 'map-elites' is `qd_search`."""
    why = check_process(process)
    if why:
        raise ValueError(why)
    if process['adapt']:
        ad = Adaptive(process['weights'], ops.get('library'))
        ops = dict(ad.ops(), random=ops['random'])
        evaluate = ad.evaluate(evaluate)
    if process['algorithm'] == 'map-elites':
        return qd_search(process, ops, evaluate, max_evals, seed, calibrate=calibrate, cost=cost)
    saved = (FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS, FB.CALIBRATION_EXTRA)
    FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS, FB.CALIBRATION_EXTRA = (
        process['pop'], process['children'], process['leaders'], process['tournament'], process['p_cross'],
        process['calib_extra'])
    try:
        return FB.steady_state_search(ops, evaluate, max_evals, seed, contract=contract, calibrate=calibrate,
                                      cost=cost)
    finally:
        FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS, FB.CALIBRATION_EXTRA = saved


def descriptor(cfg):
    """An engine's cell in the quality-diversity archive: (levels: 1, 2-3 or 4+), and which kinds of operator its
    program uses (exchange X, cluster moves I, coarse-graining C, recombination M or H, restart R)."""
    ops = {op for op, _ in K.statements(cfg['prog'])}
    lv = 0 if cfg['levels'] == 1 else (1 if cfg['levels'] <= 3 else 2)
    return (lv, 'X' in ops, 'I' in ops, 'C' in ops, bool(ops & {'M', 'H'}), 'R' in ops)


def qd_search(process, ops, evaluate, max_evals, seed, calibrate='BC', cost=None):
    """MAP-Elites under the feedback contract: the same judge, calibration and submissions as the steady search;
    parents from the archive's cells; returns (the judge's incumbent, report)."""
    rng = random.Random(seed)
    seen, archive, count, cost = {}, {}, [0], cost or {}

    def ev(p, split):
        count[0] += cost.get(split, 1)
        return evaluate(p, split)

    def new(program):
        k = key(program)
        if k in seen:
            return None
        e = seen[k] = FB.Entry(program, ops['size'](program))
        e.scores.append(ev(program, 'A'))
        return e

    def place(e):
        c = descriptor(e.program)
        if c not in archive or e.rank() < archive[c].rank():
            archive[c] = e
    J = None

    def left():
        return count[0] < max_evals and not (J is not None and J.stopped)
    init = []
    while len(init) < process['pop'] and left():
        e = new(ops['random'](rng))
        if e is not None:
            init.append(e)
            place(e)
    init.sort(key=FB.Entry.rank)
    extra = []
    while len(extra) < process['calib_extra']:
        p = ops['random'](rng)
        if key(p) not in seen and all(key(x) != key(p) for x in extra):
            extra.append(p)
    J = FB.Judge(ev, [e.program for e in init] + extra, init[0].program, calibrate=calibrate)
    gen = 0
    while left():
        gen += 1
        cells = sorted(archive.values(), key=FB.Entry.rank)
        made, tries = 0, 0
        while made < process['children'] and tries < 10 * process['children'] and left():
            tries += 1
            a = rng.choice(cells)
            p = (ops['crossover'](a.program, rng.choice(cells).program, rng) if rng.random() < process['p_cross']
                 else ops['mutate'](a.program, rng))
            e = new(p)
            if e is not None:
                place(e)
                made += 1
        for e in sorted(archive.values(), key=FB.Entry.rank)[:process['leaders']]:
            if left():
                e.scores.append(ev(e.program, 'A'))
        if left():
            J.submit(min(archive.values(), key=FB.Entry.rank).program)
    return J.incumbent, {'generations': gen, 'evaluations': count[0], 'distinct_programs': len(seen),
                         'reported': J.best, 'cells': len(archive),
                         'judge': {'tau': J.tau, 'start': J.start, 'releases': J.releases,
                                   'submissions': J.submissions, 'stopped': J.stopped}}


def seeded_ops(ops, seeds):
    """The same operators, except that the first draws of `random` return the given engines (in order)."""
    queue = list(seeds)
    out = dict(ops)

    def random_or_seed(rng):
        return queue.pop(0) if queue else ops['random'](rng)
    out['random'] = random_or_seed
    return out


# ----------------------------------------------------------------------------------------- level 2: processes

def random_process(rng):
    while True:
        p = {k: rng.choice(PROCESS_SPACE[k]) for k in SCALARS}
        p['weights'] = {m: rng.choice(PROCESS_SPACE['weight']) for m in MUTATIONS}
        if check_process(p) is None:
            return p


def mutate_process(proc, rng):
    for _ in range(50):
        p = copy.deepcopy(proc)
        k = rng.choice(SCALARS + ('weights', 'weights'))
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
        p = {k: (a[k] if rng.random() < 0.5 else b[k]) for k in SCALARS}
        p['weights'] = {m: (a['weights'][m] if rng.random() < 0.5 else b['weights'][m]) for m in MUTATIONS}
        if check_process(p) is None:
            return p
    return mutate_process(a, rng)


def key(x):
    return json.dumps(x, sort_keys=True)


def summary_stats(values):
    return {'mean': statistics.mean(values), 'n': len(values),
            'sd': statistics.stdev(values) if len(values) > 1 else 0.0}


__all__ = ['MUTATIONS', 'ORIGINAL', 'PROCESS_SPACE', 'SCALARS', 'random_engine', 'mutate', 'crossover', 'size',
           'engine_ops', 'learn_macros', 'Adaptive', 'check_process', 'search', 'descriptor', 'qd_search',
           'seeded_ops', 'random_process', 'mutate_process', 'crossover_process', 'key']
