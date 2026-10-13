"""DEV-only difficulty calibration (roadmap W05: "harder DEV tasks avoid ceiling effects
without being selected using confirmation results"; B16 "stronger DEV calibration").

The B13 panels were too easy: on 95 of 96 tasks some solver already reached the exact
optimum, so no improvement experiment could show anything. Calibration measures, on
freshly generated DEV tasks only, for each family setting:

  certified_fraction  share of tasks whose optimum the evaluator can certify
  ceiling_rate        share where the best fixed baseline already reaches the optimum
  mean_headroom       mean (optimum - best baseline) / optimum
  reference_seconds   evaluator cost of the certified optimum (ground truth, not solver budget)

and selects settings with a rule frozen in SELECTION_RULE before any run. Every setting
tried is kept in the record, selected or not. Only split='DEV' tasks are ever measured:
`measure` refuses anything else, and the record lists the splits it used.

Calibrated panels for later studies are drawn from the selected settings with a new seed
and any split; the parameters were fixed on DEV material only.
"""
import statistics
import time

from .common import canonical, digest, utcnow
from .domains import ADAPTERS, Unsupported
from .dsl import baseline_programs
from .execution import execute
from .models import Limits

SCHEMA = 'genesis-dev-calibration-v1'
SELECTION_RULE = {
    'certified_fraction_min': 0.9,
    'ceiling_rate_min': 0.1,
    'ceiling_rate_max': 0.6,
    'mean_headroom_min': 0.02,
    'reference_seconds_median_max': 15.0,
    'order': 'closest ceiling_rate to 0.35, then lower median reference_seconds, then setting order',
    'select_at_most': 4,
}
# B20_R12 (the user's decision of 13 Oct 2026): E1's candidate is already optimal on most hosts of
# the family SELECTION_RULE chose, so E1 cannot be powered there; the frozen rule excludes harder
# families by design (the fixed baselines must reach the optimum on >= 10% of hosts). A second,
# separately versioned rule selects E1's family only. Like the first, it never looks at a candidate:
# it bounds the fixed baselines' ceiling rate from above instead (harder for them), and keeps the
# certification, headroom and evaluator-speed limits. SELECTION_RULE and the domain adoption are
# unchanged; studies adopt a rule's record under configs/dev_calibration.json 'studies'.
SELECTION_RULE_E1_HARD = {
    'name': 'e1-hard-v1',
    'certified_fraction_min': 0.9,
    'ceiling_rate_min': 0.0,
    'ceiling_rate_max': 0.25,
    'ceiling_rate_target': 0.0,
    'mean_headroom_min': 0.02,
    'reference_seconds_median_max': 15.0,
    'order': 'closest ceiling_rate to 0.0 (hardest for the fixed baselines), then lower median reference_seconds, '
             'then setting order',
    'select_at_most': 4,
}
RULES = (SELECTION_RULE, SELECTION_RULE_E1_HARD)
RULES_BY_NAME = {r['name']: r for r in RULES if 'name' in r}     # the unnamed rule is SELECTION_RULE
CALIBRATION_LIMITS = Limits(queries=1000, cpu_seconds=2)
DEFAULT_GRID = {
    'c4_host_v2': [
        ('erdos', {'n': 10, 'p': 0.45}), ('erdos', {'n': 12, 'p': 0.3}), ('erdos', {'n': 12, 'p': 0.45}),
        ('erdos', {'n': 12, 'p': 0.6}), ('erdos', {'n': 14, 'p': 0.3}), ('erdos', {'n': 14, 'p': 0.45}),
        ('erdos', {'n': 16, 'p': 0.3}), ('erdos', {'n': 16, 'p': 0.4}), ('erdos', {'n': 20, 'p': 0.25}),
        ('bipartite', {'n': 12, 'p': 0.6}), ('bipartite', {'n': 16, 'p': 0.5}),
        ('planted_cluster', {'n': 12, 'p_in': 0.8, 'p_out': 0.25}),
        ('planted_cluster', {'n': 16, 'p_in': 0.7, 'p_out': 0.2}),
    ],
    'triangle_free_host_v1': [
        ('erdos', {'n': 10, 'p': 0.45}), ('erdos', {'n': 12, 'p': 0.3}), ('erdos', {'n': 12, 'p': 0.5}),
        ('erdos', {'n': 14, 'p': 0.35}), ('erdos', {'n': 16, 'p': 0.3}),
        ('planted_cluster', {'n': 12, 'p_in': 0.8, 'p_out': 0.25}),
        ('planted_cluster', {'n': 16, 'p_in': 0.7, 'p_out': 0.2}),
    ],
}


class ConfirmationMaterialRefused(ValueError):
    pass


def require_dev(tasks):
    bad = sorted({t.split for t in tasks if t.split != 'DEV'})
    if bad:
        raise ConfirmationMaterialRefused(f'calibration measures DEV tasks only; refused splits {bad}')


def measure(tasks, *, limits=CALIBRATION_LIMITS, reference_seconds=30, seed=0):
    """Per-task rows for DEV tasks: certified optimum (or UNSUPPORTED) and every baseline's value."""
    require_dev(tasks)
    rows = []
    for t in tasks:
        a = ADAPTERS[t.domain]
        start = time.monotonic()
        ref = a.reference(t, seconds=reference_seconds)
        seconds = round(time.monotonic() - start, 3)
        values = {}
        for name, program in sorted(baseline_programs().items()):
            r = execute(t, program, limits, int(digest({'seed': seed, 'task': t.task_id})[:12], 16))
            values[name] = r.get('result', {}).get('value') if r['status'] == 'SUCCESS' else None
        row = {'task_sha256': digest(t.model_dump(mode='json')), 'edges': len(t.edges),
               'reference': ref.record() if isinstance(ref, Unsupported) else
               {'status': ref['status'], 'value': ref['value'], 'method': ref['method']},
               'reference_seconds': seconds, 'baselines': values}
        rows.append(row)
    return rows


def summarize(rows):
    certified = [r for r in rows if r['reference']['status'] == 'FINITE_CERTIFIED']
    ceilings, headrooms = [], []
    for r in certified:
        best = max((v for v in r['baselines'].values() if v is not None), default=0)
        opt = r['reference']['value']
        ceilings.append(best == opt)
        headrooms.append((opt - best) / opt if opt else 0.0)
    n = len(rows)
    return {'tasks': n, 'certified': len(certified),
            'certified_fraction': round(len(certified) / n, 4) if n else 0.0,
            'ceiling_rate': round(sum(ceilings) / len(ceilings), 4) if ceilings else None,
            'mean_headroom': round(statistics.fmean(headrooms), 4) if headrooms else None,
            'reference_seconds_median': round(statistics.median(r['reference_seconds'] for r in rows), 3) if rows else None,
            'mean_edges': round(statistics.fmean(r['edges'] for r in rows), 2) if rows else None}


def eligible(summary, rule=SELECTION_RULE):
    s = summary
    reasons = []
    if s['certified_fraction'] < rule['certified_fraction_min']:
        reasons.append('too few certified optima')
    if s['ceiling_rate'] is None or not rule['ceiling_rate_min'] <= s['ceiling_rate'] <= rule['ceiling_rate_max']:
        reasons.append('ceiling rate outside the band')
    if s['mean_headroom'] is None or s['mean_headroom'] < rule['mean_headroom_min']:
        reasons.append('too little headroom')
    if s['reference_seconds_median'] is None or s['reference_seconds_median'] > rule['reference_seconds_median_max']:
        reasons.append('evaluator too slow')
    return reasons


def select(settings, rule=SELECTION_RULE):
    ok = [s for s in settings if not s['ineligible_because']]
    target = rule.get('ceiling_rate_target', 0.35)
    ok.sort(key=lambda s: (abs(s['summary']['ceiling_rate'] - target), s['summary']['reference_seconds_median'],
                           s['index']))
    return [{'family': s['family'], 'params': s['params'], 'index': s['index']} for s in ok[:rule['select_at_most']]]


def calibrate(domain, grid=None, *, seed=20261101, tasks_per_setting=8, limits=CALIBRATION_LIMITS,
              reference_seconds=30, rule=SELECTION_RULE, progress=None):
    a = ADAPTERS[domain]
    grid = grid if grid is not None else DEFAULT_GRID[domain]
    seen, settings, task_hashes = set(), [], []
    for i, (family, params) in enumerate(grid):
        tasks, seen, gen = a.generate(seed + 1000 * i, tasks_per_setting, 'DEV', family, params, excluded=seen)
        rows = measure(tasks, limits=limits, reference_seconds=reference_seconds, seed=seed)
        summary = summarize(rows)
        settings.append({'index': i, 'family': family, 'params': params, 'generator': gen, 'summary': summary,
                         'ineligible_because': eligible(summary, rule), 'rows': rows})
        task_hashes += [r['task_sha256'] for r in rows]
        if progress:
            progress(settings[-1])
    from .verification.tools import PINS
    return {'schema': SCHEMA, 'domain': domain, 'created_at': utcnow(), 'seed': seed,
            'splits_used': ['DEV'], 'rule': rule, 'limits': limits.model_dump(mode='json'),
            'baselines': {k: v.model_dump(mode='json') for k, v in sorted(baseline_programs().items())},
            'reference_seconds': reference_seconds, 'tasks_per_setting': tasks_per_setting,
            'grid': [{'family': f, 'params': p} for f, p in grid], 'settings': settings,
            'selected': select(settings, rule), 'task_sha256s': task_hashes,
            'tool_pins_sha256': digest(PINS.read_text()),
            'note': 'DEV material only; no SELECT, CONFIRM or FUTURE task was generated or measured'}


def record_problems(record):
    """Structural checks a reviewer (or later code) applies before using a calibration."""
    out = []
    if record.get('schema') != SCHEMA:
        out.append('not a calibration record')
        return out
    if record.get('splits_used') != ['DEV']:
        out.append('calibration used material other than DEV')
    rule = record.get('rule')
    name = rule.get('name') if isinstance(rule, dict) else None
    if name is None:
        if rule != SELECTION_RULE:
            out.append('selection rule differs from the frozen SELECTION_RULE')
    elif name not in RULES_BY_NAME:
        out.append(f'selection rule {name!r} is not a registered rule')
    elif rule != RULES_BY_NAME[name]:
        out.append(f'selection rule differs from the frozen, registered rule {name!r}')
    if select(record['settings'], record['rule']) != record['selected']:
        out.append('selected settings do not follow from the recorded measurements and rule')
    for s in record['settings']:
        if summarize(s['rows']) != s['summary'] or eligible(s['summary'], record['rule']) != s['ineligible_because']:
            out.append(f"setting {s['index']} summary does not follow from its rows")
    return out


def calibrated_panel(record, seed, count, split, excluded=()):
    """Draw `count` tasks round-robin from the selected settings (parameters chosen on DEV only)."""
    problems = record_problems(record)
    if problems:
        raise ValueError('unusable calibration: ' + '; '.join(problems))
    if not record['selected']:
        raise ValueError('calibration selected no setting')
    a = ADAPTERS[record['domain']]
    chosen = record['selected']
    per = [count // len(chosen) + (1 if i < count % len(chosen) else 0) for i in range(len(chosen))]
    out, seen = [], set(excluded)
    for i, (s, k) in enumerate(zip(chosen, per)):
        if k:
            tasks, seen, _ = a.generate(seed + 7919 * i, k, split, s['family'], s['params'], excluded=seen)
            out += tasks
    return out, seen


def record_digest(record):
    return digest(record)


def compact(record):
    """The record without per-task rows (for configs); the full record is the evidence."""
    return {**{k: v for k, v in record.items() if k != 'settings'},
            'settings': [{k: v for k, v in s.items() if k != 'rows'} for s in record['settings']],
            'full_record_sha256': digest(record)}


__all__ = ['calibrate', 'measure', 'summarize', 'select', 'calibrated_panel', 'record_problems', 'require_dev',
           'compact', 'canonical', 'SELECTION_RULE', 'SELECTION_RULE_E1_HARD', 'RULES']


CONFIG = 'configs/dev_calibration.json'


def load(domain, repo=None, study=None):
    """The adopted calibration for `domain`: the evidence record named (by path and SHA-256) in
    configs/dev_calibration.json, re-checked with record_problems before use. With ``study`` (for
    example 'e1'), the study's own adoption under 'studies' is used instead, and its record must use
    the rule the adoption names."""
    import json
    from pathlib import Path
    repo = Path(repo) if repo else Path(__file__).resolve().parents[2]
    cfg = json.loads((repo / CONFIG).read_text())
    entry = (cfg.get('studies', {}).get(study, {}) if study else cfg['domains']).get(domain)
    if entry is None:
        raise ValueError(f'no adopted calibration for {domain}' + (f' in study {study}' if study else ''))
    record = json.loads((repo / entry['record']).read_text())
    if digest(record) != entry['sha256']:
        raise ValueError('calibration record differs from the adopted one')
    if study and (record.get('rule') or {}).get('name') != entry.get('rule'):
        raise ValueError(f'the record for study {study} does not use the rule its adoption names')
    problems = record_problems(record)
    if problems:
        raise ValueError('calibration record: ' + '; '.join(problems))
    return record
