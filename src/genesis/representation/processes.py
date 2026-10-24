"""Representation synthesis as a typed executable process, improvable at any meta-level (directive items 9 and 11).

A level-1 process of kind `gadget-synthesizer` is the MILP synthesiser with its settings as data (`max_ancillas`,
`bound`, `uniform`) and a search space for them. Run on a task (a set of relations), it yields the number of exact
gadgets it produces, each verified by `gadgets.check` and `gadgets.check_matrix`; every synthesis attempt costs one
unit of the shared `Fuel` (`autonomy.process`), so every level spends from one budget and recursion is bounded.

A level-L process (L >= 2) improves a level-(L-1) one through `autonomy.process.step` (mutating the parameters within
their space, keeping the best by measured yield on its TRAINING relations). Improvement is not taken on trust:
`promotion_gate` re-measures the candidate and the incumbent on UNFAMILIAR relations (a held-out set neither saw) at
the same fuel per relation, and admits the candidate only if it is strictly better there. That is the measure the
directive asks for: verified useful discoveries on unfamiliar tasks at matched total compute, not recursion depth,
candidate counts or complexity.
"""
import copy

from ..autonomy import process as P
from . import gadgets as GD
from .relations import relation_from_json

SPACE = {'max_ancillas': [0, 1, 2], 'bound': [1, 2, 3, 4, 6, 8]}


def synthesizer(max_ancillas=0, bound=1, uniform=False):
    return {'level': 1, 'kind': 'gadget-synthesizer', 'lineage': [],
            'params': {'max_ancillas': max_ancillas, 'bound': bound, 'uniform': uniform, 'space': copy.deepcopy(SPACE)}}


def improver(level, variants=4, step=1, target=None, subtask=None):
    return {'level': level, 'kind': 'parameter-improver', 'lineage': [],
            'params': {'variants': variants, 'step': step, 'target': target, 'subtask': subtask,
                       'space': {'variants': [1, 2, 4, 8], 'step': [1, 2, 3]}}}


def measure(process, task, fuel):
    """Exact gadgets produced on the task's relations (one fuel unit per synthesis)."""
    if process['kind'] != 'gadget-synthesizer':
        raise ValueError('only gadget synthesisers are measured directly')
    p = process['params']
    found = 0
    for rj in task['relations']:
        fuel.take()
        rel = relation_from_json(rj)
        g, _ = GD.synthesize_milp(rel, max_ancillas=p['max_ancillas'], bound=p['bound'], uniform=p['uniform'],
                                  time_limit=10)
        if g is not None and GD.check(g, rel)['exact'] and GD.check_matrix(g, rel):
            found += 1
    return found


def promotion_gate(candidate, incumbent, unfamiliar, fuel_per_relation=1):
    """Admit `candidate` (a level-1 synthesiser) over `incumbent` only if it produces strictly more verified gadgets
    on relations neither saw, each with the same fuel. Returns (admit, candidate yield, incumbent yield)."""
    budget = fuel_per_relation * len(unfamiliar['relations'])
    yc = measure(candidate, unfamiliar, P.Fuel(budget))
    yi = measure(incumbent, unfamiliar, P.Fuel(budget))
    return yc > yi, yc, yi


__all__ = ['SPACE', 'synthesizer', 'improver', 'measure', 'promotion_gate']
