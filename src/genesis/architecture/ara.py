"""The ARA cycle (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §0, §8, §9; ARA-1):

    model -> diagnose -> propose -> synthesise -> evaluate on dev -> submit -> keep

`cycle(view, ...)` runs it once on an environment view, within `budget` units (the view's evaluation units plus the
sense units ARA's own computations cost), and returns what it did. The arms:
  * **modify**: the best variant on dev (fitted on dev_a, valued on dev_b's held-out repeats, the same draws as the
    diagnosis's) is submitted if its dev gain over the incumbent is at least the diagnosis's MATERIAL;
  * **solve** (no modification): when the diagnosis is NONE, or no variant qualifies, ARA keeps the incumbent; every
    AG ends in the kernel reattempt node, so the original objective is always what is finally run;
  * **stop**: when the budget would be exceeded.
Rewrites are ranked by the diagnosis's localisation (operators on the implicated roles first, a uniform prior
within); with `diagnose=False` the same generator runs in a seeded random order with no ladder (the blind-rewrite
control). Holes are filled on dev_a only. Variants are explored to depth `depth` by limitation inversion
(`rewrite.followups`) from the best ones. Among variants within MATERIAL of the best, the smallest is preferred
(complexity is never rewarded).

`tune_only(view, ...)` is the tuning-only control: the incumbent's own operators kept, only parameter values,
searched sets and budget shares varied (every candidate classifies as TUNING), chosen on dev at the same budget.

`submit` is a callable supplied by whoever holds the judge (ARA imports no kernel module): submit(variant, claimed,
units) -> verdict.
"""
import copy
import itertools
import random

from . import diagnose as D
from . import graph as G
from . import rewrite as R

MAX_VARIANTS = 14
DEPTH = 2
DEFAULT_CONFIG = {'max_variants': MAX_VARIANTS, 'depth': DEPTH, 'exact_repeats': D.EXACT_REPEATS,
                  'battery_random': D.BATTERY_RANDOM, 'edge_aggs': ['mean', 'sd'], 'material': D.MATERIAL,
                  'ranking': 'localised'}
CONFIG_SPACE = {'max_variants': [1, 2, 4, 8, 14, 20], 'depth': [1, 2, 3], 'exact_repeats': [4, 6, 8, 12],
                'battery_random': [6, 12, 24, 48], 'edge_aggs': [['mean', 'sd'], ['mean', 'sd', 'frac_pos', 'cv']],
                'material': [0.025, 0.05, 0.1], 'ranking': ['localised', 'localised_prior', 'blind']}


class Account:
    """ARA's spending: the view's evaluation units and the sense units of its own computations."""

    def __init__(self, view, budget):
        self.view, self.budget = view, budget
        self.start = view.units
        self.sense = 0.0

    @property
    def spent(self):
        return (self.view.units - self.start) + self.sense

    def can(self, cost):
        return self.spent + cost <= self.budget + 1e-9


def dev_value(lab, run, view):
    ch = G.choose(run['policy'], view.graphs('dev_b'), lab.sense_cache)
    vals = lab.per_instance(ch)
    return sum(vals) / len(vals)


def config_of(config):
    """ARA's own settings (an object ARA itself can rewrite, B20_R144): DEFAULT_CONFIG overridden by `config`, every
    value checked against CONFIG_SPACE (or equal to the default)."""
    c = dict(DEFAULT_CONFIG, **(config or {}))
    for k, v in c.items():
        if k not in DEFAULT_CONFIG:
            raise ValueError(f'unknown setting {k!r}')
        if v != DEFAULT_CONFIG[k] and v not in CONFIG_SPACE[k]:
            raise ValueError(f'{k}={v!r} is outside the settings space')
    return c


def rank(ag, rws, ladder, seed, prior=None):
    """Rewrites in the order ARA tries them. `ladder` None: a seeded random order (blind). Otherwise operators on the
    roles the ladder implicates first. `prior` ({term: {operator: weight}}, learned elsewhere from earlier outcomes)
    orders the implicated rewrites by the weight of their operator for the ladder's diagnosis (ties as before)."""
    if ladder is None:
        rng = random.Random(f'blind|{seed}')
        out = list(rws)
        rng.shuffle(out)
        return out
    roles = set(ladder['located'])
    if 'Sense' in roles or 'Features' in roles:
        roles |= {'Sense', 'Features'}
    first = [r for r in rws if R.role_of(ag, r) in roles]
    rest = [r for r in rws if R.role_of(ag, r) not in roles]
    if prior:
        w = prior.get(ladder.get('diagnosis'), {})
        first = sorted(first, key=lambda r: -w.get(r['op'], 0.0))         # stable: ties keep the generator's order
    return first + rest


def cycle(view, seed=0, budget=None, diagnose=True, submit=None, archive=(), max_variants=None, depth=None,
          config=None, prior=None, hint=None):
    """One ARA cycle. `config`: ARA's own settings (`config_of`); explicit max_variants and depth override it.
    `prior`: an operator prior for `rank`. `hint`: roles to treat as implicated in place of the ladder's (a stand-in
    a meta-study's kernel may pass; ARA never derives one itself)."""
    cfg = config_of(config)
    max_variants = cfg['max_variants'] if max_variants is None else max_variants
    depth = cfg['depth'] if depth is None else depth
    if cfg['ranking'] == 'blind':
        diagnose = False
    budget = budget if budget is not None else 4 * view.budget
    acct = Account(view, budget)
    trace = {'arm': None, 'diagnosis': None, 'variants': [], 'submitted': None, 'verdict': None}
    inc = view.incumbent
    lab = D.Lab(view, seed, exact_repeats=cfg['exact_repeats'])
    if diagnose:
        lad = D.ladder(view, inc, seed, lab=lab, config=cfg)
        if hint is not None:
            lad = dict(lad, located=list(hint), diagnosis=lad['diagnosis'] if lad['diagnosis'] != 'NONE' else 'HINT')
        acct.sense += lab.sense_units
        trace['diagnosis'] = {k: lad[k] for k in ('diagnosis', 'significant', 'located', 'terms', 'range',
                                                  'material', 'values')}
        material, base_run = lad['material'], lad['incumbent_run']
        if lad['diagnosis'] == 'NONE':
            trace['arm'] = 'solve'
            return _finish(trace, acct, lab, view, inc, base_run)
    else:
        lad = None
        base_run = G.execute(inc, view, 'dev_a', seed=seed, sense_cache=lab.sense_cache, draws=lab.draws)
        material = None
    base = dev_value(lab, base_run, view)
    if material is None:                    # blind: the same MATERIAL rule from the dev tables, without the ladder
        material = _material(lab, cfg['material'])
    synth = R.Synthesis(view, lab, seed, archive)
    queue = [(r, inc, 1) for r in rank(inc, R.generate(inc, archive), lad, seed,
                                       prior if cfg['ranking'] == 'localised_prior' else None)]
    seen, tried = {G.ag_id(inc)}, 0
    while queue and tried < max_variants:
        rw, parent, d = queue.pop(0)
        if not acct.can(parent['budget']['total']):
            trace['arm'] = 'stop'
            break
        s0 = synth.sense_units
        variant, fill = R.realise(parent, rw, synth)
        acct.sense += synth.sense_units - s0
        if variant is None or G.ag_id(variant) in seen:
            trace['variants'].append({'rewrite': rw, 'refused': fill if variant is None else 'duplicate'})
            continue
        seen.add(G.ag_id(variant))
        tried += 1
        try:
            run = G.execute(variant, view, 'dev_a', seed=seed, sense_cache=lab.sense_cache, draws=lab.draws)
        except G.BudgetExceeded as e:
            trace['variants'].append({'rewrite': rw, 'refused': f'budget: {e}'})
            continue
        acct.sense += sum(v for k, v in run['charges'].items() if variant['nodes'][k]['role'] == 'Sense')
        v = dev_value(lab, run, view)
        rec = {'rewrite': rw, 'class': G.classify(inc, variant), 'dev_value': v, 'gain': v - base,
               'variant': variant, 'run': run, 'depth': d, 'fill': _public(fill)}
        trace['variants'].append(rec)
        if d < depth and v - base >= material:
            queue = [(r, variant, d + 1) for r in R.followups(variant, rw, archive)] + queue
    scored = [x for x in trace['variants'] if 'dev_value' in x]
    if not scored or max(x['gain'] for x in scored) < material:
        trace['arm'] = trace['arm'] or 'solve'
        return _finish(trace, acct, lab, view, inc, base_run)
    top = max(x['dev_value'] for x in scored)
    near = [x for x in scored if x['dev_value'] >= top - material]
    best = min(near, key=lambda x: (G.size_of(x['variant']), -x['dev_value']))
    trace['arm'] = 'modify'
    trace['submitted'] = {'rewrite': best['rewrite'], 'class': best['class'], 'dev_gain': best['gain'],
                          'variant': best['variant']}
    if submit is not None:
        trace['verdict'] = submit(best['variant'], {'policy': best['run']['policy'],
                                                    'charges': best['run']['charges'], 'seed': seed}, acct.spent)
    return _finish(trace, acct, lab, view, best['variant'], best['run'])


def _material(lab, fraction=None):
    nb = len(lab.value_b)
    K = lab.K
    o = [lab.value_b[i][max(range(K), key=lambda c: (lab.choose_b[i][c], -c))] for i in range(nb)]
    single = max(range(K), key=lambda c: (sum(lab.value_b[i][c] for i in range(nb)), -c))
    rng_ = sum(o[i] - lab.value_b[i][single] for i in range(nb)) / nb
    return (D.MATERIAL if fraction is None else fraction) * rng_ if rng_ > 0 else float('inf')


def _public(fill):
    if not isinstance(fill, dict):
        return fill
    return {k: v for k, v in fill.items() if k in ('expr', 'op', 'scale', 'score', 'rediscovery', 'tried',
                                                   'source', 'fingerprint')}


def _finish(trace, acct, lab, view, final_ag, final_run):
    """The mandatory return to the objective: the final AG's policy (the reattempt), and what was spent."""
    trace['final'] = {'ag': final_ag, 'policy': final_run['policy'], 'is_incumbent':
                      G.ag_id(final_ag) == G.ag_id(view.incumbent)}
    trace['units'] = {'view': acct.view.units - acct.start, 'sense': round(acct.sense, 6), 'spent': acct.spent,
                      'budget': acct.budget}
    for v in trace['variants']:
        v.pop('run', None)
    return trace


# ------------------------------------------------------------------------------------------------ tuning only

TUNE_GRID = {'repeats': (1, 2, 4, 8), 'steps': (30, 120, 480), 'step': (0.001, 0.05, 0.2), 'k': (2, 4, 8),
             'start': ('keep', None)}


def tune_candidates(ag, seed):
    """TUNING-class variants of the incumbent: parameter values, liftable parameters and budget shares."""
    nodes = ag['nodes']
    options = []
    for n in sorted(nodes):
        nd = nodes[n]
        if nd['kernel']:
            continue
        if nd['role'] == 'Evaluator':
            options.append([(n, 'repeats', r) for r in TUNE_GRID['repeats']])
        if nd['role'] == 'Search':
            for p in ('steps', 'step', 'k', 'start'):
                options.append([(n, p, v) for v in TUNE_GRID[p]])
        if nd['role'] == 'Policy':
            for p in G.LIFTABLE.get(nd['op'], ()):
                options.append([(n, 'lift', p), (n, 'lift', None)])
    out = []
    for combo in itertools.product(*options):
        new = copy.deepcopy(ag)
        for n, p, v in combo:
            nd = new['nodes'][n]
            if p == 'lift':
                if v is not None:
                    nd['searched'] = sorted(set(nd['searched']) | {v})
            elif p == 'start':
                if v is None:
                    nd['params'].pop('start', None)
            else:
                nd['params'][p] = v
        new['lineage'] = {'parent': G.ag_id(ag), 'tuning': [list(c) for c in combo]}
        if G.classify(ag, new) == 'TUNING' and G.admissible(ag, new) is None:
            out.append(new)
    rng = random.Random(f'tune|{seed}')
    rng.shuffle(out)
    return out


def tune_only(view, seed=0, budget=None, submit=None):
    budget = budget if budget is not None else 4 * view.budget
    acct = Account(view, budget)
    lab = D.Lab(view, seed)
    inc = view.incumbent
    base_run = G.execute(inc, view, 'dev_a', seed=seed, sense_cache=lab.sense_cache, draws=lab.draws)
    base = dev_value(lab, base_run, view)
    best = (base, inc, base_run)
    n = 0
    for cand in tune_candidates(inc, seed):
        if not acct.can(cand['budget']['total']):
            break
        try:
            run = G.execute(cand, view, 'dev_a', seed=seed, sense_cache=lab.sense_cache, draws=lab.draws)
        except G.BudgetExceeded:
            continue
        acct.sense += sum(v for k, v in run['charges'].items() if cand['nodes'][k]['role'] == 'Sense')
        n += 1
        v = dev_value(lab, run, view)
        if v > best[0] + 1e-12:
            best = (v, cand, run)
    material = _material(lab)
    trace = {'arm': 'tuning', 'tried': n, 'dev_gain': best[0] - base, 'variants': [], 'verdict': None}
    if best[1] is not inc and best[0] - base >= material and submit is not None:
        trace['verdict'] = submit(best[1], {'policy': best[2]['policy'], 'charges': best[2]['charges'], 'seed': seed},
                                  acct.spent)
    return _finish(trace, acct, lab, view, best[1], best[2])


__all__ = ['MAX_VARIANTS', 'DEPTH', 'DEFAULT_CONFIG', 'CONFIG_SPACE', 'Account', 'config_of', 'cycle', 'tune_only',
           'tune_candidates', 'rank', 'dev_value']
