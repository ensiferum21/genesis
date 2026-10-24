"""Processes as data, at any meta-level, under one fuel budget (Genesis Ω contract §10, §16.8).

A PROCESS is {'level': L, 'kind': name, 'params': {...}, 'lineage': [...]}: data that an executor runs. A process at
level L + 1 TRANSFORMS processes of level L: it proposes variants of a level-L process (`propose`) and keeps the one
whose measured yield is best. Because a transformer is itself a process, a level-(L + 2) process can transform it, and
so on; no level is hard-coded as the last. Every execution draws from one FUEL budget shared by all levels (each
measurement costs fuel, each proposal costs fuel), and a depth limit bounds the recursion, so a transformation can
never make execution unbounded: exhausting the fuel raises `OutOfFuel`, which the caller records as a failure.

`step(process, task, fuel, measure)` runs one process: a level-1 process is measured on the task directly
(`measure(process, task, fuel)`); a level-L process (L >= 2) improves `task` (a level L - 1 process) by trying
`params['variants']` mutations of it, each measured recursively, and returns the best (ties to the incumbent).
Mutation changes the numeric parameters of a process in `params['space']`, a field at a time, by the transformer's
own `params['step']`; the child records its parent in its lineage.
"""
import copy
import json
import random


class OutOfFuel(RuntimeError):
    pass


class Fuel:
    def __init__(self, units):
        self.left = int(units)
        self.spent = 0

    def take(self, k=1):
        if self.left < k:
            raise OutOfFuel(f'fuel exhausted after {self.spent} units')
        self.left -= k
        self.spent += k


MAX_DEPTH = 8


def key(proc):
    return json.dumps({k: proc[k] for k in ('level', 'kind', 'params')}, sort_keys=True)


def mutate(proc, transformer, rng):
    """A child of `proc`: one parameter of its `space` moved by the transformer's step (in index units)."""
    space = proc['params'].get('space', {})
    if not space:
        return copy.deepcopy(proc)
    child = copy.deepcopy(proc)
    name = sorted(space)[rng.randrange(len(space))]
    choices = space[name]
    i = choices.index(child['params'][name]) if child['params'][name] in choices else 0
    step = max(1, int(transformer['params'].get('step', 1)))
    j = min(len(choices) - 1, max(0, i + rng.choice((-step, step))))
    child['params'][name] = choices[j]
    child['lineage'] = proc.get('lineage', []) + [{'parent': key(proc), 'by': key(transformer), 'changed': name}]
    return child


def step(process, task, fuel, measure, rng=None, depth=0):
    """Run `process` on `task`. Level 1: returns measure(process, task, fuel). Level L >= 2: returns (best level-(L-1)
    process, its yield) after trying process['params']['variants'] mutations of `task`."""
    if depth > MAX_DEPTH:
        raise OutOfFuel('meta-recursion deeper than MAX_DEPTH')
    rng = rng or random.Random(0)
    fuel.take()
    if process['level'] == 1:
        return measure(process, task, fuel)
    if task['level'] != process['level'] - 1:
        raise ValueError('a level-L process transforms level L - 1 processes')
    sub_task = process['params'].get('subtask')

    def yield_of(p):
        if p['level'] == 1:
            return step(p, sub_task, fuel, measure, rng, depth + 1)
        _, y = step(p, p['params']['target'], fuel, measure, rng, depth + 1)
        return y
    best, best_y = task, yield_of(task)
    for _ in range(int(process['params'].get('variants', 1))):
        child = mutate(best, process, rng)
        y = yield_of(child)
        if y > best_y:
            best, best_y = child, y
    return best, best_y
