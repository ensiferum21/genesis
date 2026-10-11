"""Sample-size and power analysis from DEV pilot data (roadmap W07, §12.1).

"Set a sample size from pilot estimates and a stated power target; do not tune it
using confirmation outcomes." `required_sample` reads only pilot rows whose tasks are
DEV material (each row carries its split) and simulates the registered decision rule.

Effect model (headroom-limited integer improvements). Edges are integers and a task on
which the candidate already reaches the certified optimum cannot improve. So a design
effect of e edges per task is simulated as: resample pilot tasks within each family,
centre the paired differences on zero (the pilot's own effect is removed, never used),
then give each resampled task with headroom (optimum - candidate > 0) whole extra edges
with the probability that makes the family's expected gain e. If the headroom in the
pilot cannot carry e, the design is reported INFEASIBLE rather than simulated.

Decision rule simulated. The registered one: Holm at the worst rank (alpha / family
size), the bootstrap lower bound above zero, and the estimate at or above the minimum
useful effect. The sign-flip p-value is computed exactly when at most EXACT_LIMIT
differences are non-zero and by the normal approximation otherwise; the bootstrap bound
by the normal approximation. `approximation_check` compares with the exact analysis.

Design floor. A sample size below `min_tasks_per_stratum` is never chosen: tiny panels
make every sensitivity analysis degenerate (a single task can flip a family). The floor is
a stated design choice in the record, not a statistical result.
"""
from collections import defaultdict
from itertools import product
import math
from statistics import NormalDist
import random

from .common import digest
from .kernel.analysis import analyze, check_plan, plan_core

Z = NormalDist()
EXACT_LIMIT = 14


class NonDevPilot(ValueError):
    pass


def _pilot(rows, headroom='candidate'):
    """Per stratum, (paired difference, headroom) cells. `headroom`:
      candidate  optimum − candidate value (the B16 model);
      centred    optimum − (candidate value − the stratum's mean difference): the headroom of
                 the centred candidate that the simulation actually perturbs. The two agree
                 when the pilot's mean difference is near zero; they differ when the pilot
                 candidate is already much better than the baseline (added in B19, where the
                 B16 model reported a near-ceiling candidate as INFEASIBLE)."""
    if headroom not in ('candidate', 'centred'):
        raise ValueError(headroom)
    by = defaultdict(list)
    for r in rows:
        if r.get('split') != 'DEV':
            raise NonDevPilot(f"pilot row {r.get('task_id')!r} is not DEV material ({r.get('split')!r})")
        if r.get('status') != 'SCORED':
            continue
        if type(r.get('optimum')) is not int:
            raise ValueError(f"pilot row {r.get('task_id')!r} needs the certified optimum (headroom model)")
        d = r['candidate']['value'] - r['baseline']['value']
        by[r['stratum']].append((d, r['optimum'] - r['candidate']['value']))
    if not by or any(len(v) < 2 for v in by.values()):
        raise ValueError('every pilot stratum needs at least two scored tasks')
    if headroom == 'centred':
        for st, cells in by.items():
            mean = sum(d for d, _ in cells) / len(cells)
            by[st] = [(d, math.floor(h + mean + 1e-9)) for d, h in cells]
    return dict(sorted(by.items()))


def _p_value(sample):
    k = len(sample)
    t = sum(sum(v) / len(v) for v in sample.values()) / k
    cells = [(s, d) for s, v in sample.items() for d in v if d != 0]
    if len(cells) <= EXACT_LIMIT:
        sizes = {s: len(v) for s, v in sample.items()}
        hits = 0
        for signs in product((1, -1), repeat=len(cells)):
            tot = defaultdict(float)
            for (s, d), g in zip(cells, signs):
                tot[s] += g * d
            hits += sum(tot[s] / sizes[s] for s in sizes) / k >= t - 1e-12
        return hits / 2 ** len(cells), t
    var0 = sum(sum(d * d for d in v) / len(v) ** 2 for v in sample.values()) / k ** 2
    return (1.0 if var0 == 0 else 1 - Z.cdf(t / math.sqrt(var0))), t


def _decision(sample, plan, alpha_rank):
    p, t = _p_value(sample)
    k = len(sample)
    se = math.sqrt(sum((sum((d - sum(v) / len(v)) ** 2 for d in v) / max(1, len(v) - 1)) / len(v)
                       for v in sample.values()) / k ** 2)
    lower = t - Z.inv_cdf(1 - plan['alpha']) * se
    return p <= alpha_rank and lower > 0 and t >= plan['minimum_useful_effect']


def _bump_probability(cells, effect):
    room = [h for _, h in cells]
    with_room = sum(1 for h in room if h > 0) / len(room)
    if effect == 0:
        return 0.0
    if with_room == 0:
        return None
    q = effect / with_room
    return q if q <= max(room) else None     # whole edges per task cannot exceed the headroom


def _simulate(pilot, plan, n, effect, rng):
    sample = {}
    for s, cells in pilot.items():
        mean = sum(d for d, _ in cells) / len(cells)
        q = _bump_probability(cells, effect)
        draws = []
        for _ in range(n):
            d, h = cells[rng.randrange(len(cells))]
            bump = 0
            if h > 0 and q:
                bump = min(h, int(q) + (rng.random() < q - int(q)))
            draws.append(d - mean + bump)
        sample[s] = draws
    return sample


def simulate_power(pilot, plan, tasks_per_stratum, *, effect=None, sims=1000):
    problems = check_plan(plan)
    if problems:
        raise ValueError('plan: ' + '; '.join(problems))
    effect = plan['design_effect'] if effect is None else effect
    if any(_bump_probability(c, effect) is None for c in pilot.values()):
        return None                                   # the pilot's headroom cannot carry this effect
    alpha_rank = plan['alpha'] / plan['multiplicity']['family_size']
    rng = random.Random(int(digest({'plan': plan_core(plan), 'n': tasks_per_stratum, 'effect': effect})[:16], 16))
    return sum(_decision(_simulate(pilot, plan, tasks_per_stratum, effect, rng), plan, alpha_rank)
               for _ in range(sims)) / sims


def required_sample(pilot_rows, plan, *, min_tasks_per_stratum=10,
                    grid=(10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200), sims=1000, headroom='candidate'):
    pilot = _pilot(pilot_rows, headroom)
    grid = sorted({n for n in grid if n >= min_tasks_per_stratum} | {min_tasks_per_stratum})
    table, chosen = [], None
    for n in grid:
        power = simulate_power(pilot, plan, n, sims=sims)
        table.append({'tasks_per_stratum': n, 'total_tasks': n * len(pilot),
                      'power': None if power is None else round(power, 4)})
        if power is not None and chosen is None and power >= plan['power_target']:
            chosen = table[-1]
    at = chosen['tasks_per_stratum'] if chosen else grid[-1]
    at_threshold = simulate_power(pilot, plan, at, effect=plan['minimum_useful_effect'], sims=sims)
    null_rate = simulate_power(pilot, plan, at, effect=0.0, sims=sims)
    stats = {}
    for s, cells in pilot.items():
        ds = [d for d, _ in cells]
        mean = sum(ds) / len(ds)
        stats[s] = {'tasks': len(ds), 'mean_difference': round(mean, 4),
                    'sd': round(math.sqrt(sum((d - mean) ** 2 for d in ds) / (len(ds) - 1)), 4),
                    'share_with_headroom': round(sum(h > 0 for _, h in cells) / len(cells), 4)}
    feasible = table[0]['power'] is not None
    extra = {} if headroom == 'candidate' else {'headroom_reference': headroom}
    return {**extra, 'schema': 'genesis-power-analysis-v1', 'plan_core_sha256': digest(plan_core(plan)),
            'pilot_strata': stats, 'pilot_rows_sha256': digest(pilot_rows),
            'design_effect': plan['design_effect'], 'minimum_useful_effect': plan['minimum_useful_effect'],
            'power_target': plan['power_target'], 'min_tasks_per_stratum': min_tasks_per_stratum,
            'assumed_holm_rank_alpha': plan['alpha'] / plan['multiplicity']['family_size'],
            'table': table, 'chosen': chosen,
            'status': 'CHOSEN' if chosen else ('INFEASIBLE' if not feasible else 'NOT_REACHED_IN_GRID'),
            'power_at_minimum_useful_effect': None if at_threshold is None else round(at_threshold, 4),
            'false_positive_rate_at_zero_effect': None if null_rate is None else round(null_rate, 4),
            'model': 'headroom-limited integer improvements over centred DEV pilot differences',
            'note': 'pilot effect sizes are reported but never used to set the effect; only spread and headroom are'}


def approximation_check(pilot_rows, plan, tasks_per_stratum, *, sims=40, headroom='candidate'):
    """Share of simulated studies on which the simulated decision equals the exact analysis."""
    pilot = _pilot(pilot_rows, headroom)
    rng = random.Random(int(digest({'check': plan_core(plan), 'n': tasks_per_stratum})[:16], 16))
    alpha_rank = plan['alpha'] / plan['multiplicity']['family_size']
    agree = 0
    for i in range(sims):
        sample = _simulate(pilot, plan, tasks_per_stratum, plan['design_effect'], rng)
        sample = {s: [float(round(d)) for d in ds] for s, ds in sample.items()}
        rows = [{'task_id': f'{s}-{i}-{j}', 'stratum': s, 'status': 'SCORED',
                 'candidate': {'value': 100 + int(d), 'run': 'SUCCESS', 'cpu_ns': 1},
                 'baseline': {'value': 100, 'run': 'SUCCESS', 'cpu_ns': 1}}
                for s, ds in sample.items() for j, d in enumerate(ds)]
        agree += (analyze(rows, plan)['decision'] == 'SUPPORTED') == _decision(sample, plan, alpha_rank)
    return agree / sims


__all__ = ['required_sample', 'simulate_power', 'approximation_check', 'NonDevPilot']
