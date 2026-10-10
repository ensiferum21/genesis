"""Harder public/private panel generation (beyond the 24-edge exhaustive range).

Panels are defined only by generator parameters and a seed. No task is kept or
dropped because of how any solver arm performs on it — that would bias the
comparison. The only filter is arm-independent: the evaluator must be able to
certify the optimum (SAT/DRAT upper bound meeting a checked witness) within a
time limit; uncertifiable hosts are skipped and counted.

Isomorphism-distinctness uses the exposure GraphIndex, which works for every
host size, unlike the bounded canonical labelling used for small panels.
"""
from itertools import combinations
import random

from .exposure import GraphIndex
from .models import GraphTask

FAMILIES = ('erdos', 'bipartite_noise', 'planted_dense', 'two_scale')


def _host(rng, n, family, density):
    edges = []
    half = n // 2
    for u, v in combinations(range(n), 2):
        if family == 'erdos':
            p = density
        elif family == 'bipartite_noise':
            p = min(0.95, density * 1.7) if (u < half) != (v < half) else density * 0.25
        elif family == 'planted_dense':
            p = min(0.95, density * 2.0) if u < half and v < half else density * 0.7
        else:  # two_scale: dense core plus sparse periphery
            p = min(0.9, density * 2.2) if u < n // 3 and v < n // 3 else density * 0.8
        if rng.random() < p:
            edges.append((u, v))
    return tuple(edges)


def make_hard_panel(seed, count, domain, split, *, n_range=(12, 20), edge_range=(30, 64), density=0.32,
                    exposure=None, certify=True, certify_seconds=60, max_tries=None):
    """Return (tasks, stats). With certify=True each task carries no optimum (that stays private);
    stats records how many hosts were skipped as uncertifiable within the limit."""
    rng = random.Random(seed)
    index = GraphIndex()
    seen_public = exposure or GraphIndex()
    tasks, skipped_uncertifiable, skipped_duplicate, tries = [], 0, 0, 0
    max_tries = max_tries or count * 200
    while len(tasks) < count and tries < max_tries:
        tries += 1
        n = rng.randint(*n_range)
        family = rng.choice(FAMILIES)
        edges = _host(rng, n, family, density)
        if not edge_range[0] <= len(edges) <= edge_range[1]:
            continue
        if seen_public.find(n, edges) is not None or index.find(n, edges) is not None:
            skipped_duplicate += 1
            continue
        task = GraphTask(task_id=f'{split.lower()}-hard-{seed}-{len(tasks):04}', domain=domain, n=n, edges=edges,
                         family=f'{family}-n{n}', split=split)
        if certify:
            from .verification.sat import certified_bounds
            from .dsl import solve
            from .models import SolverProgram
            start = solve(task, SolverProgram(rounds=4), 100000, seed)['selected']
            bounds = certified_bounds(task, seconds=certify_seconds, start_witness=start)
            if bounds['status'] != 'OPTIMALITY_CHECKED':
                skipped_uncertifiable += 1
                continue
        index.add(n, edges, task.task_id)
        tasks.append(task)
    if len(tasks) != count:
        raise RuntimeError(f'only {len(tasks)} of {count} certifiable distinct hosts within {max_tries} tries')
    return tasks, {'tries': tries, 'skipped_uncertifiable': skipped_uncertifiable,
                   'skipped_duplicate': skipped_duplicate, 'generator': 'panels.make_hard_panel-v1',
                   'parameters': {'n_range': n_range, 'edge_range': edge_range, 'density': density,
                                  'families': FAMILIES, 'certify_seconds': certify_seconds}}
