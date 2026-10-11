"""Sample-size and power analysis from DEV pilot data (roadmap W07, §12.1).

"Set a sample size from pilot estimates and a stated power target; do not tune it
using confirmation outcomes." `required_sample` reads only pilot rows whose tasks are
DEV material (each row carries its split), estimates the within-family spread of the
paired differences, and simulates the registered decision rule at the plan's
design effect to find the smallest number of tasks per family reaching the target.

The simulation uses the large-sample normal approximation of the stratified
sign-flip test and of the bootstrap lower bound (both exact in the analysis itself);
`approximation_check` compares the two on simulated data so a reviewer can see the
size of the approximation error.
"""
from collections import defaultdict
import math
from statistics import NormalDist
import random

from .common import digest
from .kernel.analysis import analyze, check_plan, holm, plan_core

Z = NormalDist()


class NonDevPilot(ValueError):
    pass


def _strata(rows):
    by = defaultdict(list)
    for r in rows:
        if r.get('split') != 'DEV':
            raise NonDevPilot(f"pilot row {r.get('task_id')!r} is not DEV material ({r.get('split')!r})")
        if r.get('status') != 'SCORED':
            continue
        by[r['stratum']].append(r['candidate']['value'] - r['baseline']['value'])
    if not by or any(len(v) < 2 for v in by.values()):
        raise ValueError('every pilot stratum needs at least two scored tasks')
    return dict(sorted(by.items()))


def _approx_decision(sample, plan, alpha_rank):
    k = len(sample)
    t = sum(sum(v) / len(v) for v in sample.values()) / k
    var0 = sum(sum(d * d for d in v) / len(v) ** 2 for v in sample.values()) / k ** 2
    p = 1.0 if var0 == 0 else 1 - Z.cdf(t / math.sqrt(var0))
    se = math.sqrt(sum((sum((d - sum(v) / len(v)) ** 2 for d in v) / max(1, len(v) - 1)) / len(v)
                       for v in sample.values()) / k ** 2)
    lower = t - Z.inv_cdf(1 - plan['alpha']) * se
    return p <= alpha_rank and lower > 0 and t >= plan['minimum_useful_effect']


def simulate_power(pilot, plan, tasks_per_stratum, *, effect=None, sims=2000):
    """Power of the registered decision at `effect` (default: the plan's design effect) with
    `tasks_per_stratum` tasks in each pilot stratum, the worst Holm rank assumed (alpha/m)."""
    problems = check_plan(plan)
    if problems:
        raise ValueError('plan: ' + '; '.join(problems))
    effect = plan['design_effect'] if effect is None else effect
    centered = {s: [d - sum(v) / len(v) for d in v] for s, v in pilot.items()}
    alpha_rank = plan['alpha'] / plan['multiplicity']['family_size']
    rng = random.Random(int(digest({'plan': plan_core(plan), 'n': tasks_per_stratum, 'effect': effect})[:16], 16))
    hits = 0
    for _ in range(sims):
        sample = {s: [v[rng.randrange(len(v))] + effect for _ in range(tasks_per_stratum)]
                  for s, v in centered.items()}
        hits += _approx_decision(sample, plan, alpha_rank)
    return hits / sims


def required_sample(pilot_rows, plan, *, grid=(2, 3, 4, 6, 8, 10, 12, 16, 20, 25, 30, 40, 50, 60, 80, 100),
                    sims=2000):
    pilot = _strata(pilot_rows)
    table = []
    chosen = None
    for n in grid:
        power = simulate_power(pilot, plan, n, sims=sims)
        table.append({'tasks_per_stratum': n, 'total_tasks': n * len(pilot), 'power': round(power, 4)})
        if chosen is None and power >= plan['power_target']:
            chosen = table[-1]
    at_threshold = simulate_power(pilot, plan, chosen['tasks_per_stratum'] if chosen else grid[-1],
                                  effect=plan['minimum_useful_effect'], sims=sims)
    null_rate = simulate_power(pilot, plan, chosen['tasks_per_stratum'] if chosen else grid[-1], effect=0.0,
                               sims=sims)
    stats = {s: {'tasks': len(v), 'mean_difference': round(sum(v) / len(v), 4),
                 'sd': round(math.sqrt(sum((d - sum(v) / len(v)) ** 2 for d in v) / (len(v) - 1)), 4)}
             for s, v in pilot.items()}
    return {'schema': 'genesis-power-analysis-v1', 'plan_core_sha256': digest(plan_core(plan)), 'pilot_strata': stats,
            'pilot_rows_sha256': digest(pilot_rows), 'design_effect': plan['design_effect'],
            'minimum_useful_effect': plan['minimum_useful_effect'], 'power_target': plan['power_target'],
            'assumed_holm_rank_alpha': plan['alpha'] / plan['multiplicity']['family_size'],
            'table': table, 'chosen': chosen, 'power_at_minimum_useful_effect': round(at_threshold, 4),
            'false_positive_rate_at_zero_effect': round(null_rate, 4),
            'method': 'normal approximation of the registered stratified sign-flip test and bootstrap bound; '
                      'resampling centred DEV pilot differences shifted to the effect',
            'note': 'pilot effect sizes are reported but never used to tune the effect; only their spread is'}


def approximation_check(pilot_rows, plan, tasks_per_stratum, *, sims=40):
    """How often the approximate decision agrees with the exact registered analysis."""
    pilot = _strata(pilot_rows)
    centered = {s: [d - sum(v) / len(v) for d in v] for s, v in pilot.items()}
    rng = random.Random(int(digest({'check': plan, 'n': tasks_per_stratum})[:16], 16))
    agree = 0
    alpha_rank = plan['alpha'] / plan['multiplicity']['family_size']
    for i in range(sims):
        sample = {s: [v[rng.randrange(len(v))] + plan['design_effect'] for _ in range(tasks_per_stratum)]
                  for s, v in centered.items()}
        rows = []
        for s, ds in sample.items():
            for j, d in enumerate(ds):
                base = 100
                cand = base + round(d)
                rows.append({'task_id': f'{s}-{i}-{j}', 'stratum': s, 'status': 'SCORED',
                             'candidate': {'value': max(0, cand), 'run': 'SUCCESS', 'cpu_ns': 1},
                             'baseline': {'value': base, 'run': 'SUCCESS', 'cpu_ns': 1}})
        exact = analyze(rows, plan)['decision'] == 'SUPPORTED'
        rounded = {s: [float(round(d)) for d in ds] for s, ds in sample.items()}
        agree += exact == _approx_decision(rounded, plan, alpha_rank)
    return agree / sims


__all__ = ['required_sample', 'simulate_power', 'approximation_check', 'NonDevPilot', 'holm']
