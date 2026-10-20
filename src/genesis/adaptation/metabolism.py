"""Metabolism of the adaptation cell: what a study costs, learned from what earlier studies cost.

The cell predicts a design's wall time from its demand (runs and the time budgeted for them, plus certification per
host) and one overhead per run that it fits to its own earlier studies: their run logs give the wall time each took
(summed over resumed segments), their evidence gives what they ran. Nothing here is declared by hand except the
fallback overhead used before any study can be read.
"""
import re

DEFAULT_MODEL = {'overhead_s': 0.25, 'largest_study_s': 0.0, 'largest_n_seen': 63, 'fitted_on': {}}
_STAMP = re.compile(r'^\[\s*([0-9.]+)s\]')


def observed_wall_s(run_log):
    """Wall seconds a study ran: the last timestamp of each segment of its run log (a new segment starts at every
    'pinned to CPU' line), summed."""
    total, seg = 0.0, 0.0
    for line in run_log.splitlines():
        if 'pinned to CPU' in line:
            total, seg = total + seg, 0.0
        m = _STAMP.match(line)
        if m:
            seg = max(seg, float(m.group(1)))
    return total + seg


def demand(design):
    """(runs per host, budgeted seconds per host, certification seconds per host)."""
    arms, reps, lad = design.get('arms', 1), design.get('reps', 3), design.get('ladder', ())
    longs = design.get('long_budgets', ())
    long_arms = len(design.get('long_arm_names') or ()) or (1 if longs else 0)
    runs = arms * reps * len(lad) + long_arms * len(longs)
    budget = arms * reps * sum(lad) + long_arms * sum(longs)
    return runs, budget, design.get('certification_mean_s', 0)


def probe_cost(design, model=None):
    model = model or DEFAULT_MODEL
    return sum(p['hosts'] * (p['budget_s'] + model['overhead_s']) for p in (design.get('probes') or {}).values()
               if isinstance(p, dict))


def predict(design, model=None):
    model = model or DEFAULT_MODEL
    runs, budget, cert = demand(design)
    return design.get('hosts', 0) * (budget + model['overhead_s'] * runs + cert) + probe_cost(design, model)


def fit(studies):
    """A cost model from finished studies (`receptors.Study`): the median per-run overhead over the studies whose run
    logs are readable, the largest study's wall time and the largest instance seen."""
    from .design import design_of
    per, walls, sizes = {}, {}, [63]
    for st in studies:
        wall = observed_wall_s(st.run_log)
        d = design_of(st)
        sizes += d['sizes']
        if wall <= 0 or not d['hosts']:
            continue
        runs, budget, cert = demand(d)
        walls[st.profile.study] = round(wall, 1)
        c = (wall / d['hosts'] - budget - cert) / runs if runs else 0
        if c > 0:
            per[st.profile.study] = round(c, 4)
    if not per:
        return dict(DEFAULT_MODEL, largest_n_seen=max(sizes))
    cs = sorted(per.values())
    med = cs[len(cs) // 2] if len(cs) % 2 else (cs[len(cs) // 2 - 1] + cs[len(cs) // 2]) / 2
    return {'overhead_s': round(med, 4), 'largest_study_s': max(walls.values()), 'largest_n_seen': max(sizes),
            'fitted_on': {k: {'wall_s': walls[k], 'overhead_s': per.get(k)} for k in walls}}


def residuals(studies, model):
    """Predicted against observed wall time, per study (how well the cell knows its own costs)."""
    from .design import design_of
    out = {}
    for st in studies:
        wall = observed_wall_s(st.run_log)
        if wall > 0:
            out[st.profile.study] = {'observed_s': round(wall), 'predicted_s': round(predict(design_of(st), model))}
    return out
