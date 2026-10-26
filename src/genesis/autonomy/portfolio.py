"""A portfolio of discovery processes and an allocator between them (Genesis Ω², stage Ω10; B20_R148).

Why (Daniel's report "Beyond Genesis-Ω", 24-26 Oct 2026; `docs/OMEGA_META_ADAPTIVE.md`). Genesis's inventors each run
ONE fixed search process (B20_R127-R129: the steady-state evolutionary search of `autonomy.feedback`). The report's
central recommendation: no fixed search harness is reliably best, so Genesis should keep a portfolio of discovery
processes and learn which deserve compute, judging every arm by verified progress per unit of compute on tasks it has
not seen. This module is that machinery, LLM-free (directive item 10): the "Explorers" are program searches over
Genesis's own languages.

**A task** (`Task`) is a search space and a verifier: `random(rng)`, `mutate(p, rng)`, `crossover(a, b, rng)`,
`size(p)`, `descriptor(p)` (a hashable trait for quality-diversity archives) and `evaluate(p, split, rep)`, a number
where higher is better. Splits: 'A' (search), 'V' (validation: chooses each arm's answer), 'T' (test: measured by the
study at checkpoints, never charged, never shown to any arm). `rep` is the repetition index of a noisy evaluation:
the same (program, split, rep) always means the same run, so arms see common random numbers.

**A harness** is a discovery process written as a generator: it yields a program, receives its A score, yields the
next. It can therefore be paused and resumed between any two evaluations, which is what an allocator needs. Six
harnesses, all prior art (none is new):
  * `best_of_n`: independent random programs (the "raw sampling" control the report insists on);
  * `hill_climb`: (1+1) local search on one program, restarting after `stall` evaluations without improvement;
  * `anneal`: simulated annealing over programs (Kirkpatrick et al. 1983), its temperature scaled to the spread of the
    first scores and cooled geometrically over `horizon` evaluations;
  * `evolution`: the steady-state evolutionary search of `autonomy.feedback` (Genesis's current inventor) with its
    constants (population 16, 8 children, tournament 3, crossover 0.25, 2 leaders re-evaluated), without a judge;
  * `map_elites`: a quality-diversity archive over the task's descriptor (Mouret and Clune 2015);
  * `racing`: successive halving over batches of random programs with re-evaluation of survivors (Jamieson and
    Talwalkar 2016), restarted with a fresh batch when one survivor remains.
A harness's incumbent is its program with the best mean A score (ties: more evaluations, smaller, then by key).

**An arm** (`run_arm`) spends exactly a budget of B evaluations (A and V evaluations each cost 1) and is measured at
log-spaced checkpoints B/2^J, ..., B/2, B. At every round boundary and checkpoint it validates (on V, once per
distinct program, charged) the incumbents of the harnesses that ran since; its ANSWER is the validated program with
the best V score. The study measures the answer on T. Arms (allocators):
  * `single:<h>`: harness h gets everything (G0 is `single:evolution`, the current inventor's search);
  * `uniform`: the six harnesses in turn, one round each (G1, a portfolio with fixed allocation);
  * `halving`: successive halving ACROSS harnesses (G2): stages of equal budget, shared equally among the live
    harnesses; after each, they are ranked by their best validated score and the best 1/ETA (rounded up; ETA = 3,
    so 6 -> 2 -> 1) continue from where they were;
  * `bandit`: UCB1 over harnesses on their best validated score, normalised to the range of current scores, with a
    reserved exploration share (every `explore`-th round goes to the least-used harness: the plan's metabolism rule
    of at least 10% for unfamiliar approaches);
  * `halving_tuned` (G3): `halving` with each harness's parameters chosen beforehand on development tasks
    (`tune_params`), frozen before any test task is seen.

**Metrics** (`audc`, `normalise`): per task, quality q = (T(answer) - T_low) / (T_high - T_low), with T_low the median T
score of reference random programs and T_high the best T score any arm's answer reached on that task (or a stated
reference, if higher); the area under the discovery curve is the trapezoid mean of q over the log-spaced checkpoints
(equal weight per doubling of compute). CPU (of evaluations, including the native solvers they run as child
processes, and of the arm's own logic) is recorded as a second currency.
"""
from dataclasses import dataclass, field
import json
import math
import os
import random
import statistics
import time
from typing import Callable

HARNESSES = ('best_of_n', 'hill_climb', 'anneal', 'evolution', 'map_elites', 'racing')
DEFAULTS = {
    'best_of_n': {},
    'hill_climb': {'stall': 30},
    'anneal': {'t_end': 0.01, 'probe': 8},
    'evolution': {'pop': 16, 'children': 8, 'tournament': 3, 'p_cross': 0.25, 'leaders': 2},
    'map_elites': {'init': 16, 'p_cross': 0.1},
    'racing': {'batch': 16},
}
PARAM_SPACE = {      # what `tune_params` may choose from (G3); DEFAULTS are points of it
    'hill_climb': {'stall': (10, 30, 100)},
    'anneal': {'t_end': (0.001, 0.01, 0.1), 'probe': (8,)},
    'evolution': {'pop': (8, 16, 32), 'children': (4, 8, 16), 'tournament': (2, 3, 5), 'p_cross': (0.0, 0.25, 0.5),
                  'leaders': (0, 2)},
    'map_elites': {'init': (8, 16, 32), 'p_cross': (0.0, 0.1, 0.3)},
    'racing': {'batch': (8, 16, 32)},
    'best_of_n': {},
}
ARMS = tuple(f'single:{h}' for h in HARNESSES) + ('uniform', 'halving', 'bandit', 'halving_tuned')
ETA = 3              # successive halving keeps the best 1/ETA of the harnesses at each stage (6 -> 2 -> 1)
G0, G1, G2, G3 = 'single:evolution', 'uniform', 'halving', 'halving_tuned'


def key(p):
    return json.dumps(p, sort_keys=True)


def cpu_now():
    """CPU seconds of this process and of its finished children (an evaluation may run a native solver)."""
    t = os.times()
    return t.user + t.system + t.children_user + t.children_system


@dataclass
class Task:
    name: str
    domain: str
    family: str
    random: Callable
    mutate: Callable
    crossover: Callable
    size: Callable
    descriptor: Callable
    evaluate: Callable                 # (program, split, rep) -> float, higher is better
    noisy: bool = False
    info: dict = field(default_factory=dict)


# ------------------------------------------------------------------------------------------------------ harnesses

class Harness:
    """Base: book-keeping of scores; subclasses implement `run`, a generator (score = yield program)."""
    name = None

    def __init__(self, task, rng, params=None, horizon=None):
        self.task, self.rng = task, rng
        self.p = dict(DEFAULTS[self.name], **(params or {}))
        self.horizon = horizon
        self.stats = {}                 # key -> [sum, n, program]
        self.evals = 0
        self._gen = self.run()
        self._pending = next(self._gen)

    def mean(self, p):
        s = self.stats.get(key(p))
        return s[0] / s[1] if s else None

    def reps(self, p):
        s = self.stats.get(key(p))
        return s[1] if s else 0

    def propose(self):
        return self._pending

    def feed(self, score):
        k = key(self._pending)
        s = self.stats.setdefault(k, [0.0, 0, self._pending])
        s[0] += score
        s[1] += 1
        self.evals += 1
        self._pending = self._gen.send(score)

    def incumbent(self):
        if not self.stats:
            return None
        return min(self.stats.items(), key=lambda kv: (-kv[1][0] / kv[1][1], -kv[1][1], self.task.size(kv[1][2]),
                                                       kv[0]))[1][2]

    def run(self):
        raise NotImplementedError


class BestOfN(Harness):
    name = 'best_of_n'

    def run(self):
        while True:
            yield self.task.random(self.rng)


class HillClimb(Harness):
    name = 'hill_climb'

    def run(self):
        while True:
            x = self.task.random(self.rng)
            s = yield x
            stall = 0
            while stall < self.p['stall']:
                c = self.task.mutate(x, self.rng)
                sc = yield c
                if sc > s:
                    x, s, stall = c, sc, 0
                else:
                    if sc == s:
                        x = c                     # sideways moves allowed (plateaus), still counted as a stall
                    stall += 1


class Anneal(Harness):
    name = 'anneal'

    def run(self):
        probe = []
        for _ in range(self.p['probe']):
            x = self.task.random(self.rng)
            probe.append(((yield x), x))
        spread = statistics.pstdev([s for s, _ in probe]) or 1e-9
        s, x = max(probe, key=lambda t: t[0])
        t0, t_end = spread, spread * self.p['t_end']
        horizon = max(1, (self.horizon or 1000) - self.p['probe'])
        i = 0
        while True:
            T = t0 * (t_end / t0) ** min(1.0, i / horizon)
            c = self.task.mutate(x, self.rng)
            sc = yield c
            i += 1
            if sc >= s or self.rng.random() < math.exp((sc - s) / max(T, 1e-12)):
                x, s = c, sc


class Evolution(Harness):
    """Steady state, as `autonomy.feedback.steady_state_search` without a judge: tournament selection on mean A
    score, crossover or mutation, leaders re-evaluated each generation, the population the best `pop` by mean."""
    name = 'evolution'

    def rank(self, p):
        return (-self.mean(p), -self.reps(p), self.task.size(p), key(p))

    def run(self):
        pop, tries = [], 0
        while len(pop) < self.p['pop']:
            x = self.task.random(self.rng)
            tries += 1
            if self.reps(x) == 0 or tries > 50 * self.p['pop']:      # distinct, unless the space is tiny
                yield x
                pop.append(x)
        while True:
            pop.sort(key=self.rank)
            kids = []
            for _ in range(self.p['children']):
                def pick():
                    cand = self.rng.sample(pop, min(self.p['tournament'], len(pop)))
                    return min(cand, key=self.rank)
                if self.rng.random() < self.p['p_cross']:
                    c = self.task.crossover(pick(), pick(), self.rng)
                else:
                    c = self.task.mutate(pick(), self.rng)
                yield c
                kids.append(c)
            for x in pop[:self.p['leaders']]:
                yield x
            seen, merged = set(), []
            for x in pop + kids:
                if key(x) not in seen:
                    seen.add(key(x))
                    merged.append(x)
            pop = sorted(merged, key=self.rank)[:self.p['pop']]


class MapElites(Harness):
    name = 'map_elites'

    def run(self):
        archive = {}

        def place(x, s):
            d = self.task.descriptor(x)
            if d not in archive or s > archive[d][1]:
                archive[d] = (x, s)
        for _ in range(self.p['init']):
            x = self.task.random(self.rng)
            place(x, (yield x))
        while True:
            cells = sorted(archive.values(), key=lambda t: key(t[0]))
            a = self.rng.choice(cells)[0]
            if self.rng.random() < self.p['p_cross']:
                c = self.task.crossover(a, self.rng.choice(cells)[0], self.rng)
            else:
                c = self.task.mutate(a, self.rng)
            place(c, (yield c))


class Racing(Harness):
    name = 'racing'

    def run(self):
        while True:
            live = [self.task.random(self.rng) for _ in range(self.p['batch'])]
            for x in live:
                yield x
            while len(live) > 1:
                live = sorted(live, key=lambda x: (-self.mean(x), key(x)))[:max(1, len(live) // 2)]
                if len(live) > 1:
                    for x in live:
                        yield x


CLASSES = {c.name: c for c in (BestOfN, HillClimb, Anneal, Evolution, MapElites, Racing)}


# ------------------------------------------------------------------------------------------------------ the arm run

class ArmRun:
    """One arm on one task: the harnesses, the budget, validation and the answer."""

    def __init__(self, task, arm, budget, seed, params=None, rounds=32, explore=10):
        if arm not in ARMS:
            raise ValueError(f'unknown arm {arm!r}')
        self.task, self.arm, self.budget, self.seed = task, arm, budget, seed
        self.round = max(1, budget // rounds)
        self.explore = explore
        names = [arm.split(':', 1)[1]] if arm.startswith('single:') else list(HARNESSES)
        params = params or {}
        self.h = {n: CLASSES[n](task, random.Random(f'{seed}:{n}'), params.get(n), horizon=budget) for n in names}
        self.used = 0
        self.v = {}                  # key -> (V score, program)
        self.validated_by = {n: [] for n in names}     # per harness, the V scores of its validated incumbents
        self.alloc = {n: 0 for n in names}
        self.cpu = {'evaluate': 0.0, 'logic': 0.0}
        self.trace = []

    def left(self):
        return self.budget - self.used

    def _eval(self, p, split, rep):
        c0 = cpu_now()
        v = self.task.evaluate(p, split, rep)
        self.cpu['evaluate'] += cpu_now() - c0
        return v

    def give(self, name, n):
        """Run harness `name` for up to n evaluations (fewer if the budget ends)."""
        h = self.h[name]
        for _ in range(min(n, self.left())):
            c0 = time.process_time()
            p = h.propose()
            rep = h.reps(p)
            self.cpu['logic'] += time.process_time() - c0
            s = self._eval(p, 'A', rep)
            c0 = time.process_time()
            h.feed(s)
            self.cpu['logic'] += time.process_time() - c0
            self.used += 1
            self.alloc[name] += 1

    def validate(self, names):
        """Validate (once per distinct program, each costing 1) the incumbents of `names`; returns nothing."""
        for n in names:
            p = self.h[n].incumbent()
            if p is None:
                continue
            k = key(p)
            if k not in self.v:
                if self.left() <= 0:
                    continue
                self.v[k] = (self._eval(p, 'V', 0), p)
                self.used += 1
            self.validated_by[n].append(self.v[k][0])

    def answer(self):
        if not self.v:
            return None
        return max(self.v.values(), key=lambda t: (t[0], -self.task.size(t[1]), key(t[1])))[1]

    def best_v(self, name):
        xs = self.validated_by[name]
        return max(xs) if xs else -math.inf


def checkpoints(budget, J=5):
    return sorted({max(1, budget >> j) for j in range(J, -1, -1)})


def run_arm(task, arm, budget, seed, params=None, J=5, rounds=32, explore=10, on_checkpoint=None):
    """Spend `budget` evaluations in rounds of budget/rounds A evaluations, each followed by the validation of the
    harness that ran (one V evaluation if its incumbent is new; one evaluation is always kept for it). At every
    checkpoint (`checkpoints`) call on_checkpoint(evals_used, answer, run). Returns the run."""
    r = ArmRun(task, arm, budget, seed, params=params, rounds=rounds, explore=explore)
    names = list(r.h)
    for h in r.h.values():
        if isinstance(h, Anneal):
            h.horizon = max(1, budget // len(names))         # cools over its fair share of the budget
    marks, mi = checkpoints(budget, J), 0
    live = list(names)
    halving = arm in ('halving', 'halving_tuned')
    stages = (math.ceil(math.log(len(names), ETA)) + 1) if halving else 1
    bounds = [round(budget * (i + 1) / stages) for i in range(stages)]
    stage, turn, count = 0, 0, {n: 0 for n in names}
    quota = {}

    def set_quota():
        start = r.used
        share = (bounds[stage] - start) // len(live)
        quota.clear()
        quota.update({n: share for n in live})
    if halving:
        set_quota()

    def schedule():
        nonlocal turn
        turn += 1
        if halving:              # equal shares within a stage, given in rounds, in order
            left = [n for n in live if quota[n] > 0]
            return left[(turn - 1) % len(left)] if left else live[(turn - 1) % len(live)]
        if arm != 'bandit':
            return live[(turn - 1) % len(live)]
        unused = [n for n in names if count[n] == 0]
        if unused:
            return unused[0]
        if turn % r.explore == 0:
            return min(names, key=lambda x: (count[x], names.index(x)))
        vals = {x: r.best_v(x) for x in names}
        finite = [v for v in vals.values() if v > -math.inf]
        lo, hi = (min(finite), max(finite)) if finite else (0.0, 1.0)
        span = (hi - lo) or 1.0
        return max(names, key=lambda x: (((vals[x] - lo) / span if vals[x] > -math.inf else 0.0)
                                         + math.sqrt(2 * math.log(turn) / count[x]), -names.index(x)))

    def mark(m):
        r.validate(names)
        a = r.answer()
        if on_checkpoint:
            on_checkpoint(m, a, r)
        r.trace.append({'mark': m, 'evals': r.used, 'alloc': dict(r.alloc), 'live': list(live),
                        'answer': key(a) if a else None})

    while r.left() > 1:
        n = schedule()
        count[n] += 1
        size = min(r.round, r.left() - 1)
        if halving and quota.get(n, 0) > 0:
            size = min(size, quota[n])
        before = r.used
        r.give(n, size)
        if halving:
            quota[n] = quota.get(n, 0) - (r.used - before)
        r.validate([n])
        if halving and stage < stages - 1 and (r.used >= bounds[stage] or all(q <= 0 for q in quota.values())):
            r.validate(live)
            live = sorted(live, key=lambda x: (-r.best_v(x), names.index(x)))[:max(1, math.ceil(len(live) / ETA))]
            stage += 1
            set_quota()
        while mi < len(marks) and r.used >= marks[mi] - 1:
            mark(marks[mi])
            mi += 1
    while mi < len(marks):
        mark(marks[mi])
        mi += 1
    r.live = live
    return r


# ------------------------------------------------------------------------------------------------------ metrics

def normalise(score, low, high):
    if high <= low:
        return 1.0 if score >= high else 0.0
    return (score - low) / (high - low)


def audc(qs):
    """Trapezoid mean of qualities at log-spaced (equally spaced in log compute) checkpoints."""
    if len(qs) == 1:
        return qs[0]
    return (qs[0] / 2 + sum(qs[1:-1]) + qs[-1] / 2) / (len(qs) - 1)


T_REPS_NOISY = 2         # a noisy task's answer is measured on T as the mean of this many runs (never charged)


def measure(task, program, split='T'):
    """The study's measurement of a program (uncharged): the mean of T_REPS_NOISY runs for a noisy task."""
    reps = T_REPS_NOISY if task.noisy else 1
    return statistics.mean(task.evaluate(program, split, k) for k in range(reps))


def reference_low(task, n=32, seed=0):
    """The median measured score of n random programs (the floor of the normalisation)."""
    rng = random.Random(f'reference:{seed}')
    return statistics.median(measure(task, task.random(rng)) for _ in range(n))


def curve(task, arm, budget, seed, params=None, J=5):
    """(measured scores of the arm's answer at each checkpoint, the run)."""
    out = []
    r = run_arm(task, arm, budget, seed, params=params, J=J,
                on_checkpoint=lambda m, a, run: out.append(measure(task, a) if a is not None else None))
    return out, r


def audc_of(scores, low, high):
    """AUDC of a curve of measured scores (a missing answer counts as the floor)."""
    return audc([normalise(low if v is None else v, low, high) for v in scores])


# ------------------------------------------------------------------------------------------------------ G3's tuning

def tune_params(dev_tasks, budget, seeds, lows, candidates_per_harness=4, seed=0, log=None):
    """For each harness, choose its parameters on development tasks: `candidates_per_harness` settings drawn from
    PARAM_SPACE (DEFAULTS always the first), each run as `single:<h>` on every dev task and seed; quality is
    normalised per task by `lows[task.name]` and the best score any tuning run reached on it; the setting with the
    best mean AUDC wins (ties: the earlier, so DEFAULTS). No test task is seen. Returns ({harness: params}, report)."""
    rng = random.Random(f'tune:{seed}')
    runs = {}
    settings = {}
    for h in HARNESSES:
        space = PARAM_SPACE[h]
        ss = [dict(DEFAULTS[h])]
        tries = 0
        while len(ss) < candidates_per_harness and space and tries < 200:
            tries += 1
            c = dict(DEFAULTS[h], **{k: rng.choice(v) for k, v in space.items()})
            if c not in ss:
                ss.append(c)
        settings[h] = ss
        for i, c in enumerate(ss):
            for t in dev_tasks:
                for sd in seeds:
                    runs[(h, i, t.name, sd)] = curve(t, f'single:{h}', budget, f'tune:{sd}', params={h: c})[0]
    high = {t.name: max(v for (h, i, tn, sd), vs in runs.items() if tn == t.name for v in vs if v is not None)
            for t in dev_tasks}
    chosen, report = {}, {}
    for h in HARNESSES:
        score = {i: statistics.mean(audc_of(runs[(h, i, t.name, sd)], lows[t.name], high[t.name])
                                    for t in dev_tasks for sd in seeds) for i in range(len(settings[h]))}
        best = max(score, key=lambda i: (score[i], -i))
        chosen[h] = settings[h][best]
        report[h] = {'settings': settings[h], 'audc': {str(i): round(v, 6) for i, v in score.items()}, 'chosen': best}
        if log:
            log(f'tuned {h}: {chosen[h]} (mean AUDC by setting {report[h]["audc"]})')
    return chosen, report


__all__ = ['HARNESSES', 'DEFAULTS', 'PARAM_SPACE', 'ARMS', 'ETA', 'G0', 'G1', 'G2', 'G3', 'Task', 'Harness',
           'CLASSES', 'ArmRun', 'run_arm', 'checkpoints', 'normalise', 'audc', 'audc_of', 'measure', 'curve',
           'reference_low', 'tune_params', 'key', 'T_REPS_NOISY', 'cpu_now']
