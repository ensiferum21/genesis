"""Discovery tasks for the portfolio (`autonomy.portfolio`, B20_R148): three of Genesis's own program languages, each
with its verifier, as `portfolio.Task`s.

  * `acquire`: experiment-choice rules in the acquisition language (`science.acquire`; B20_R129's language), for the
    hidden-cause causal benchmark (`causal.sem`, `causal.active3`). A program's score on a split is minus the mean
    number of experiments it needs, over the split's worlds, before the decisions reach the hidden-cause F1 that all
    experiments give (B20_R129's primary measure), under the instrument's `theory` model. Deterministic.
  * `mcx2`: max-cut engine programs (`candidate_kinds.mcx2`, the pinned native binary; B20_R125's language) on
    generated graphs of the max-cut domain. A program's score on a split is the mean, over the split's graphs, of its
    cut divided by the cut of the builder's REX (`mcx2.DEFAULT`) at the same CPU budget (REX's reference run: one
    fixed seed, computed once per graph). Every cut is the checked value of the returned partition. Noisy (CPU-time
    budgets and seeds): `rep` gives the run's seed.
  * `formula`: planted ranking tasks in the same expression language over synthetic features: a hidden target
    program ranks items; a candidate's score is the Spearman rank correlation of its values with the target's over
    the split's items (1.0 is reachable: the target itself is in the language). Deterministic. A positive control with
    a known optimum.
Each split ('A', 'V', 'T') is a disjoint sample (worlds, graphs or items) drawn from its own seed; the T split is the
study's and is never charged to an arm.
"""
import json
import math
import random
import statistics

import numpy as np

from . import portfolio as P


# ------------------------------------------------------------------------------------------- the expression language

def _expr_descriptor(prog):
    """Size bucket, aggregate and the root operator: the cells of a quality-diversity archive over expressions."""
    from ..science import acquire as Q
    t = prog['expr']
    root = t[0] if isinstance(t, list) else ('leaf' if isinstance(t, str) else 'const')
    return (min(Q.size(prog), 15) // 3, prog['agg'], root)


def _depth(t):
    return 1 + max(_depth(x) for x in t[1:]) if isinstance(t, list) else 0


# ------------------------------------------------------------------------------------------- acquisition rules

ACQ_FAMILIES = {          # (p, h, density): B20_R129's BASE and SHIFT, and two more settings
    'base': (10, 3, 0.2), 'shift': (14, 4, 0.15), 'sparse': (12, 2, 0.1), 'dense': (8, 3, 0.35)}
ACQ_NOISE, ACQ_K, ACQ_N, ACQ_NINT = 'gauss', 3, 3000, 1000
EPS = 1e-12


class _World:
    """One prepared world under the theory model (B20_R129's `World`, without its bookkeeping)."""

    def __init__(self, row):
        from ..causal import active3 as A3
        from ..science import design as D
        self.p, self.truth, self.prep = row['prep']['p'], row['truth'], row['prep']
        self.dom = A3.CausalDomain(row['prep'], A3.THEORY)
        self.beliefs = D.Beliefs(self.dom)
        self._f1 = {}
        _, trail = D.run(self.dom, {'kind': 'order', 'order': list(range(self.p))}, self.p, beliefs=self.beliefs)
        self.full = self.f1(trail[-1])

    def f1(self, decisions):
        from ..causal import active3 as A3
        from ..causal import admg as A
        k = json.dumps(sorted(decisions.items()))
        if k not in self._f1:
            ans = A3.answer(self.p, decisions)
            if A.validate(ans, self.p):
                raise ValueError('an invalid answer')
            self._f1[k] = A.score(self.truth, ans)['bidirected']['f1']
        return self._f1[k]

    def needed(self, prog):
        from ..science import design as D
        _, trail = D.run(self.dom, {'kind': 'program', 'program': prog}, self.p, beliefs=self.beliefs,
                         stop=lambda k, dec: self.f1(dec) >= self.full - EPS)
        return len(trail) - 1


def acquire_worlds(family, seed, n):
    """n prepared worlds of a family (rows as B20_R129 stores them)."""
    from ..causal import active3 as A3
    from ..causal import sem as S
    p, h, d = ACQ_FAMILIES[family]
    rows = []
    for k in range(n):
        s = seed + k
        view, truth = S.instance(s, p, h, d, ACQ_NOISE, ACQ_K, ACQ_N)
        rows.append({'seed': s, 'prep': A3.prepare(view, truth, ACQ_NINT, s), 'truth': truth})
    return rows


def acquire_task(family, splits, name=None):
    """`splits`: {'A': rows, 'V': rows, 'T': rows} (from `acquire_worlds`)."""
    from ..science import acquire as Q
    worlds = {s: [_World(r) for r in rows] for s, rows in splits.items()}

    def evaluate(prog, split, rep):          # no cache of programs: every charged evaluation does its work
        return -statistics.mean(w.needed(prog) for w in worlds[split])
    return P.Task(name=name or f'acquire:{family}', domain='acquire', family=family,
                  random=Q.random_program, mutate=Q.mutate, crossover=Q.crossover, size=Q.size,
                  descriptor=_expr_descriptor, evaluate=evaluate, noisy=False,
                  info={'settings': ACQ_FAMILIES[family], 'worlds': {s: len(w) for s, w in worlds.items()},
                        'references': {'eig': Q.EIG, 'dec': Q.DEC, 'degree': Q.DEGREE,
                                       'decfall': {'agg': 'sum', 'expr': 'decfall'}}})


# ------------------------------------------------------------------------------------------- max-cut engine programs

MCX_FAMILIES = {'erdos': ('erdos', {'n': 200, 'p': 0.05}), 'planar': ('planar2', {'n': 200, 'density': 0.9}),
                'torus': ('torus2d_pm1', {'rows': 14, 'cols': 14}), 'erdos_pm1': ('erdos_pm1', {'n': 200, 'p': 0.05})}


def mcx_graphs(family, seed, n):
    from ..domains import adapter
    fam, params = MCX_FAMILIES[family]
    tasks, _, _ = adapter('maxcut_v1').generate(seed, n, 'DEV', fam, params, excluded=set())
    return tasks


def _mcx_value(task, config, seconds, seed):
    from types import SimpleNamespace
    from ..candidate_kinds import mcx2 as K
    from ..graphs_maxcut import check_cut
    out = K.solve(SimpleNamespace(n=task.n, edges=task.edges), {'cpu_seconds': seconds, 'config': config}, seconds,
                  seed)
    checked = check_cut(task, out['side'])
    if checked['value'] != out['value']:
        raise RuntimeError('mcx2 returned a cut whose checked value differs')
    return out['value']


def mcx_task(family, splits, seconds=0.02, name=None):
    """`splits`: {'A': graphs, 'V': graphs, 'T': graphs} (`mcx_graphs`). Scores relative to REX at `seconds`."""
    from ..candidate_kinds import mcx2 as K
    from . import selfimprove as SI
    ref = {s: [_mcx_value(g, dict(K.DEFAULT), seconds, 1) for g in gs] for s, gs in splits.items()}
    for s, vs in ref.items():
        if any(v <= 0 for v in vs):
            raise ValueError('a reference cut is not positive; the ratio is undefined')

    def evaluate(cfg, split, rep):
        vals = [_mcx_value(g, cfg, seconds, 1000003 * (rep + 1) + i) / ref[split][i]
                for i, g in enumerate(splits[split])]
        return statistics.mean(vals)
    return P.Task(name=name or f'mcx2:{family}', domain='mcx2', family=family,
                  random=SI.random_engine, mutate=lambda c, rng: SI.mutate(c, rng), crossover=SI.crossover,
                  size=SI.size, descriptor=SI.descriptor, evaluate=evaluate, noisy=True,
                  info={'family': MCX_FAMILIES[family], 'seconds': seconds,
                        'graphs': {s: len(g) for s, g in splits.items()},
                        'reference': 'REX (mcx2 DEFAULT) at the same budget, seed 1', 'references': {
                            'rex': dict(K.DEFAULT)}})


# ------------------------------------------------------------------------------------------- planted formulas

FORMULA_FEATURES = ('f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'one')
FORMULA_TARGETS = {
    'small': {'agg': 'sum', 'expr': ['*', 'f0', 'f1']},
    'medium': {'agg': 'sum', 'expr': ['-', ['+', 'f0', ['sq', 'f2']], ['*', 'f3', 'f4']]},
    'large': {'agg': 'sum', 'expr': ['*', ['max', 'f1', ['sqrt', ['*', 'f2', 'f5']]], ['inv1', ['-', 'f0', 'f3']]]},
    'mixed': {'agg': 'sum', 'expr': ['+', ['min', 'f0', 'f4'], ['*', 2.0, ['sqrt', 'f5']]]},
}


def formula_items(seed, n):
    rng = np.random.default_rng([seed, 7])
    X = {f'f{i}': (rng.lognormal(0.0, 0.75, n) if i % 2 else rng.uniform(-2.0, 2.0, n)) for i in range(6)}
    X['one'] = np.ones(n)
    return X


def _values(prog, X):
    from ..science import acquire as Q
    return np.nan_to_num(Q._ev(prog['expr'], X), nan=0.0, posinf=1e12, neginf=-1e12)


def spearman(a, b):
    from scipy.stats import rankdata
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def formula_task(family, splits, name=None):
    """`splits`: {'A': items, 'V': items, 'T': items} (`formula_items`)."""
    from ..science import acquire as Q
    target = FORMULA_TARGETS[family]
    F = FORMULA_FEATURES
    want = {s: _values(target, X) for s, X in splits.items()}

    def evaluate(prog, split, rep):
        return spearman(_values(prog, splits[split]), want[split])
    return P.Task(name=name or f'formula:{family}', domain='formula', family=family,
                  random=lambda rng: Q.random_program(rng, F), mutate=lambda p, rng: Q.mutate(p, rng, F),
                  crossover=lambda a, b, rng: Q.crossover(a, b, rng, F), size=Q.size, descriptor=_expr_descriptor,
                  evaluate=evaluate, noisy=False,
                  info={'target': target, 'items': {s: len(X['one']) for s, X in splits.items()},
                        'optimum': 1.0, 'references': {'target': target}})


__all__ = ['ACQ_FAMILIES', 'MCX_FAMILIES', 'FORMULA_TARGETS', 'FORMULA_FEATURES', 'acquire_worlds', 'acquire_task',
           'mcx_graphs', 'mcx_task', 'formula_items', 'formula_task', 'spearman']
