"""What the system can do now, read from its code and its evidence, and the work orders a design implies.

A design element is executable when the code provides it (the task model's size cap, the solver keys the candidate
kinds pin) or when some earlier study demonstrably did it (its evidence shows upper bounds, quality at equal time,
sequential stopping, first-hit times, probes). Anything else a composed design needs becomes a work order: the
cell does not pretend the next study can run before it can.
"""
import importlib

FEATURES = {
    'upper_bounds': 'a proven upper bound per host',
    'quality_at_equal_time': 'a quality-at-equal-time analysis (values at equal budgets, with intervals)',
    'sequential_stopping': 'preregistered interim looks with stopping boundaries in the runner',
    'internal_tts': "first-hit times reported by the focal method on its own clock, checked against its witness",
    'new_family': 'a new host family on which the strong methods disagree',
}


def _solver_keys():
    keys = set()
    for mod in ('genesis.candidate_kinds.maxsat', 'genesis.candidate_kinds.maxsat2026'):
        try:
            keys |= set(importlib.import_module(mod).SOLVERS)
        except Exception:                     # a kind that cannot load provides nothing
            pass
    return keys


def _model_cap():
    try:
        from ..models import GraphTask
        return next(m.le for m in GraphTask.model_fields['n'].metadata if hasattr(m, 'le'))
    except Exception:
        return 63


def _longest(d):
    """The longest run a finished study made: its long budgets and its probes (a probe at a home budget is a long run,
    B20_R97)."""
    xs = list(d.get('long_budgets') or ())
    xs += [p['budget_s'] for p in (d.get('probes') or {}).values() if isinstance(p, dict) and 'budget_s' in p]
    return max(xs, default=0)


def scan(designs):
    """Capabilities from the code and from the designs of finished studies (`design.design_of`). Sizes: the small
    task model's cap, or the largest hosts a finished study ran, whichever is larger (B20_R97: a larger model in the
    code counts once a study has used it; before that, an instance size is a work order)."""
    demo = {f: sorted(d['study'] for d in designs if d.get(f)) for f in FEATURES}
    demo['probes'] = sorted(d['study'] for d in designs if d.get('probes'))
    ran = max((max(d['sizes']) for d in designs if d.get('sizes')), default=0)
    small = _model_cap()
    return {'max_n': max(small, ran), 'model_cap': small, 'solver_keys': sorted(_solver_keys()),
            'min_run_s': min((min(d['ladder']) for d in designs if d.get('ladder')), default=None),
            'largest_long_budget_s': max((_longest(d) for d in designs), default=0),
            'demonstrated': demo}


def work_orders(design, caps):
    out = []
    big = max(design.get('sizes') or [0])
    if big > caps['max_n']:
        if caps['max_n'] <= caps.get('model_cap', caps['max_n']):
            what = (f"instances up to n = {big}: the task model stops at n = {caps['max_n']} and the native engine's "
                    'vertex sets are 64-bit; a larger model and an engine with multiword sets are needed')
        else:
            what = (f"instances up to n = {big}: the largest hosts any study has run have n = {caps['max_n']}; run the "
                    'engine and the champions at that size first (memory, encoding time, bounds)')
        out.append({'need': 'extend_domain', 'what': what})
    for k in design.get('competitors', ()):
        if k not in caps['solver_keys']:
            out.append({'need': 'acquire_baseline', 'what': f'{k}: obtain, build from source, pin and add to a kind'})
    for f, what in FEATURES.items():
        if design.get(f) and not caps['demonstrated'].get(f):
            out.append({'need': f, 'what': f'{what}: no earlier study has done it'})
    if design.get('probes') and not caps['demonstrated'].get('probes'):
        out.append({'need': 'probe_at_home_budget', 'what': 'runs of the flagged arms at their home budget: '
                    + ', '.join(sorted(design['probes']))})
    if caps.get('min_run_s') and design.get('ladder') and min(design['ladder']) < caps['min_run_s']:
        out.append({'need': 'harness_resolution', 'what': f"run times down to {min(design['ladder'])} s: the "
                    f"shortest any study has run is {caps['min_run_s']} s; test that the harness enforces it"})
    if design.get('long_budgets') and max(design['long_budgets']) > caps.get('largest_long_budget_s', 0):
        out.append({'need': 'long_budgets', 'what': f"budgets up to {max(design['long_budgets'])} s: the longest "
                    f"run so far was {caps.get('largest_long_budget_s', 0)} s; cost and resumption must be planned"})
    if design.get('arm_harness_fix'):
        out.append({'need': 'fix_arm_harness', 'what': 'check how ' + ', '.join(design['arm_harness_fix'])
                    + ' is run against its Evaluation run script and fix what differs'})
    if design.get('tuning'):
        t = design['tuning']
        out.append({'need': 'retune_where_lost', 'what': f"a configuration race (as B20_R89) on hosts like those lost "
                    f"(families {t['families']}, sizes {t['sizes']}) against {', '.join(t['against'])}"})
    if design.get('components_from'):
        out.append({'need': 'borrow_from_winner', 'what': 'study the mechanism of ' + ', '.join(
            design['components_from']) + ', add it to the method as a component and ablate it'})
    if str(design.get('focal_identity', '')).startswith('new:'):
        out.append({'need': 'new_method', 'what': 'a re-tuned or different focal method'})
    if design.get('catalog_refresh'):
        out.append({'need': 'refresh_catalog', 'what': "read the newest Evaluation's results and update "
                    'baselines.json and its as-of date'})
    if design.get('harness_fix'):
        out.append({'need': 'fix_harness', 'what': design['harness_fix']})
    return out
