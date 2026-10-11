"""Preregistered analysis v2 (roadmap W07, §12.1).

A plan is frozen in the evaluation request before any sealed outcome exists. The
analysis is a pure, deterministic function of the per-task raw rows and the plan, so
the custodian, a judge and any later verifier recompute the identical result.

Design (one primary endpoint, one analysis point):
  unit        one sealed task; candidate and baseline are paired on it
  difference  candidate edges - baseline edges (a failed or timed-out run scores 0 and
              stays charged; failures are never dropped)
  strata      task families (outcomes within a family share structure)
  estimand    mean over families of the family mean difference (each family weighs equally)
  test        one-sided stratified sign-flip permutation test of H0: no superiority
              (task differences are exchangeable in sign under H0; tasks are generated
              independently given their family). Exact when there are <= 18 non-zero
              differences, else 20 000 deterministic Monte Carlo flips with the +1 correction.
  interval    stratified bootstrap percentile interval (resample tasks within families)
  multiplicity Holm across the registered hypothesis family (the custodian's registration
              log supplies the other p-values; unknown or outstanding ones count as 1)
  stopping    a single analysis; a second analysis of the same evaluation is INVALID
  decision    SUPPORTED iff Holm rejects H0 AND the interval's lower end is > 0 AND the
              estimate reaches the minimum useful effect AND the cost and regression
              criteria hold. Otherwise NOT_SUPPORTED (with reasons), or INVALID when the
              evidence is incomplete, inconsistent or too much of it is unsupported.

The minimum useful effect is a usefulness threshold, not the design effect: a study
powered at an effect equal to the threshold has at most about 50% power, so plans name
a larger `design_effect` for the power analysis (genesis.power).
"""
from collections import defaultdict
from itertools import product
import math
import random

from ..common import digest

PLAN_SCHEMA = 'genesis-analysis-plan-v2'
RESULT_SCHEMA = 'genesis-analysis-result-v2'
EXACT_LIMIT = 18
MC_DRAWS = 20000
PLAN_FIELDS = frozenset({
    'schema', 'primary', 'estimand', 'strata', 'minimum_useful_effect', 'design_effect', 'alpha',
    'power_target', 'test', 'interval', 'multiplicity', 'stopping', 'failures', 'unsupported',
    'max_unsupported_fraction', 'cost', 'regression', 'sensitivity', 'decision_rule',
    'decision_record_sha256'})
SENSITIVITY = ('task-sign-test', 'leave-one-stratum-out', 'failures-excluded', 'stratum-level-sign-flip')
OUTCOMES = ('SUPPORTED', 'NOT_SUPPORTED', 'INVALID')


def _num(x, lo=None, hi=None):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and \
        (lo is None or x >= lo) and (hi is None or x <= hi)


def plan_core(plan):
    """The plan without its decision-record reference: the decision record embeds this core,
    and the plan then names the record by hash (no circularity)."""
    return {k: v for k, v in plan.items() if k != 'decision_record_sha256'}


def check_plan(plan):
    """Problems with a v2 plan (empty list = acceptable for preregistration)."""
    if not isinstance(plan, dict) or plan.get('schema') != PLAN_SCHEMA:
        return ['not a v2 analysis plan']
    if set(plan) != PLAN_FIELDS:
        return [f'plan fields differ: missing {sorted(PLAN_FIELDS - set(plan))}, extra {sorted(set(plan) - PLAN_FIELDS)}']
    out = []
    fixed = {'primary': 'paired-edge-difference', 'estimand': 'mean-of-stratum-means', 'strata': 'family',
             'test': 'stratified-sign-flip', 'stopping': {'rule': 'single-analysis'}, 'failures': 'score-zero',
             'decision_rule': 'superiority-with-minimum-useful-effect'}
    for k, v in fixed.items():
        if plan[k] != v:
            out.append(f'{k} must be {v!r}')
    if not _num(plan['minimum_useful_effect'], 0) or plan['minimum_useful_effect'] <= 0:
        out.append('minimum_useful_effect must be a positive number of edges per task')
    if not _num(plan['design_effect'], 0) or not plan['design_effect'] > plan.get('minimum_useful_effect', 0):
        out.append('design_effect must exceed the minimum useful effect (power at the threshold is <= ~50%)')
    if not _num(plan['alpha'], 0) or not 0 < plan['alpha'] <= 0.1:
        out.append('alpha must be in (0, 0.1]')
    if not _num(plan['power_target']) or not 0.5 <= plan['power_target'] < 1:
        out.append('power_target must be in [0.5, 1)')
    iv = plan['interval']
    if not isinstance(iv, dict) or iv.get('method') != 'stratified-bootstrap-percentile' or \
            not _num(iv.get('level')) or not 0.5 < iv['level'] < 1 or type(iv.get('resamples')) is not int or \
            not 1000 <= iv['resamples'] <= 100000:
        out.append('interval must be a stratified bootstrap with level in (0.5, 1) and 1000..100000 resamples')
    elif abs(iv['level'] - (1 - 2 * plan['alpha'])) > 1e-9:
        out.append('interval level must be 1 - 2*alpha (its lower end is the one-sided bound)')
    m = plan['multiplicity']
    if not isinstance(m, dict) or m.get('method') != 'holm' or not isinstance(m.get('family_id'), str) or \
            not m.get('family_id') or type(m.get('family_size')) is not int or not 1 <= m['family_size'] <= 1000:
        out.append('multiplicity must be holm with a family_id and a family_size >= 1')
    if plan['unsupported'] not in ('exclude-and-report', 'invalidate-if-any'):
        out.append('unsupported policy')
    if not _num(plan['max_unsupported_fraction'], 0, 0.5):
        out.append('max_unsupported_fraction must be in [0, 0.5]')
    c = plan['cost']
    if not isinstance(c, dict) or c.get('measure') != 'cpu_ns' or not (c.get('max_ratio') is None or _num(c['max_ratio'], 0)):
        out.append("cost must be {'measure': 'cpu_ns', 'max_ratio': number | None}")
    r = plan['regression']
    if not isinstance(r, dict) or not (r.get('max_stratum_loss') is None or _num(r['max_stratum_loss'], 0)):
        out.append("regression must be {'max_stratum_loss': number >= 0 | None}")
    if not isinstance(plan['sensitivity'], list) or set(plan['sensitivity']) != set(SENSITIVITY):
        out.append(f'sensitivity analyses must be exactly {list(SENSITIVITY)}')
    h = plan['decision_record_sha256']
    if not (isinstance(h, str) and len(h) == 64 and all(ch in '0123456789abcdef' for ch in h)):
        out.append('decision_record_sha256 must name the published pre-freeze decision record')
    return out


def _r(x):
    return None if x is None else round(float(x), 10)


def _rng(plan, label):
    return random.Random(int(digest({'plan': plan, 'purpose': label})[:16], 16))


def _row_problems(rows):
    out = []
    ids = [r.get('task_id') for r in rows]
    if len(ids) != len(set(ids)):
        out.append('duplicate task rows')
    for r in rows:
        if r.get('status') not in ('SCORED', 'UNSUPPORTED') or not isinstance(r.get('stratum'), str):
            out.append(f"malformed row for {r.get('task_id')!r}")
        elif r['status'] == 'SCORED':
            for arm in ('candidate', 'baseline'):
                a = r.get(arm)
                if not isinstance(a, dict) or type(a.get('value')) is not int or a['value'] < 0 or \
                        a.get('run') not in ('SUCCESS', 'FAILED') or type(a.get('cpu_ns')) is not int:
                    out.append(f"malformed {arm} result for {r.get('task_id')!r}")
    return out


def _strata(diffs):
    by = defaultdict(list)
    for s, d in diffs:
        by[s].append(d)
    return dict(sorted(by.items()))


def _stat(by):
    return sum(sum(v) / len(v) for v in by.values()) / len(by)


def stratified_sign_flip_p(by, plan, label='primary'):
    """One-sided p-value for T = mean of stratum means under random sign flips."""
    observed = _stat(by)
    cells = [(s, i, d) for s, v in by.items() for i, d in enumerate(v) if d != 0]
    sizes = {s: len(v) for s, v in by.items()}
    k = len(by)

    def t_of(signs):
        tot = defaultdict(float)
        for (s, _, d), sign in zip(cells, signs):
            tot[s] += sign * d
        return sum(tot[s] / sizes[s] for s in sizes) / k
    eps = 1e-12
    if len(cells) <= EXACT_LIMIT:
        hits = sum(t_of(signs) >= observed - eps for signs in product((1, -1), repeat=len(cells)))
        return hits / 2 ** len(cells), 'exact'
    rng = _rng(plan, label)
    hits = sum(t_of([rng.choice((1, -1)) for _ in cells]) >= observed - eps for _ in range(MC_DRAWS))
    return (hits + 1) / (MC_DRAWS + 1), f'monte-carlo-{MC_DRAWS}'


def bootstrap_interval(by, plan):
    rng = _rng(plan, 'interval')
    level, b = plan['interval']['level'], plan['interval']['resamples']
    stats = []
    for _ in range(b):
        res = {s: [v[rng.randrange(len(v))] for _ in v] for s, v in by.items()}
        stats.append(_stat(res))
    stats.sort()
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    return stats[int(math.floor(lo_q * (b - 1)))], stats[int(math.ceil(hi_q * (b - 1)))]


def holm(own_p, others, family_size, alpha):
    """Holm step-down for this hypothesis given the other family members' p-values.
    Members not yet known (family_size larger than the known set) count as p = 1.
    Returns (rejected, threshold at this hypothesis' rank)."""
    ps = sorted([own_p] + list(others) + [1.0] * max(0, family_size - 1 - len(others)))
    m = len(ps)
    own_rank = ps.index(own_p)
    for j, p in enumerate(ps[:own_rank + 1]):
        if p > alpha / (m - j):
            return False, alpha / (m - own_rank)
    return True, alpha / (m - own_rank)


def _sign_test(w, l):
    n = w + l
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(w, n + 1)) / 2 ** n


def analyze(rows, plan, *, family_p_values=(), analysis_count=1):
    """Deterministic analysis of per-task raw rows under a v2 plan."""
    problems = check_plan(plan)
    if problems:
        return {'schema': RESULT_SCHEMA, 'decision': 'INVALID', 'reasons': ['plan: ' + p for p in problems]}
    reasons = _row_problems(rows)
    if analysis_count != 1:
        reasons.append('the plan allows a single analysis of an evaluation')
    unsupported = sorted(r['task_id'] for r in rows if r.get('status') == 'UNSUPPORTED')
    scored = [r for r in rows if r.get('status') == 'SCORED']
    frac = len(unsupported) / len(rows) if rows else 1.0
    if plan['unsupported'] == 'invalidate-if-any' and unsupported:
        reasons.append('unsupported tasks present and the plan invalidates on any')
    if frac > plan['max_unsupported_fraction']:
        reasons.append(f'{len(unsupported)} of {len(rows)} tasks unsupported (more than the plan allows)')
    if not scored:
        reasons.append('no scored tasks')
    base = {'schema': RESULT_SCHEMA, 'plan_sha256': digest(plan), 'tasks': len(rows), 'scored': len(scored),
            'unsupported': unsupported}
    if reasons:
        return {**base, 'decision': 'INVALID', 'reasons': reasons}
    diffs = [(r['stratum'], r['candidate']['value'] - r['baseline']['value']) for r in scored]
    by = _strata(diffs)
    estimate = _stat(by)
    p, method = stratified_sign_flip_p(by, plan)
    rejected, threshold = holm(p, family_p_values, plan['multiplicity']['family_size'], plan['alpha'])
    lo, hi = bootstrap_interval(by, plan)
    wins = sum(d > 0 for _, d in diffs); losses = sum(d < 0 for _, d in diffs)
    failures = {arm: sum(r[arm]['run'] == 'FAILED' for r in scored) for arm in ('candidate', 'baseline')}
    cost = {arm: sum(r[arm]['cpu_ns'] for r in scored) for arm in ('candidate', 'baseline')}
    ratio = cost['candidate'] / cost['baseline'] if cost['baseline'] else None
    cost_ok = plan['cost']['max_ratio'] is None or (ratio is not None and ratio <= plan['cost']['max_ratio'])
    stratum_means = {s: sum(v) / len(v) for s, v in by.items()}
    worst = min(stratum_means.values())
    regression_ok = plan['regression']['max_stratum_loss'] is None or worst >= -plan['regression']['max_stratum_loss']
    # Sensitivity analyses (reported, never decisive).
    loo = {s: _stat({k: v for k, v in by.items() if k != s}) for s in by} if len(by) > 1 else {}
    kept = [(r['stratum'], r['candidate']['value'] - r['baseline']['value']) for r in scored
            if r['candidate']['run'] == 'SUCCESS' and r['baseline']['run'] == 'SUCCESS']
    level_p = stratified_sign_flip_p({s: [sum(v) / len(v)] for s, v in by.items()}, plan, 'stratum-level')[0]
    sensitivity = {
        'task-sign-test': _r(_sign_test(wins, losses)),
        'leave-one-stratum-out': {s: _r(v) for s, v in loo.items()},
        'failures-excluded': _r(_stat(_strata(kept))) if kept else None,
        'stratum-level-sign-flip': _r(level_p),
    }
    checks = {'holm_rejects_no_superiority': rejected, 'interval_lower_above_zero': lo > 0,
              'estimate_reaches_minimum_useful_effect': estimate >= plan['minimum_useful_effect'],
              'cost_within_bound': cost_ok, 'no_stratum_regression': regression_ok}
    decision = 'SUPPORTED' if all(checks.values()) else 'NOT_SUPPORTED'
    return {**base, 'decision': decision, 'checks': checks,
            'reasons': [k for k, v in checks.items() if not v],
            'estimate': _r(estimate), 'interval': [_r(lo), _r(hi)], 'interval_level': plan['interval']['level'],
            'p_value': _r(p), 'p_method': method, 'holm_threshold': _r(threshold),
            'family_p_values': [_r(x) for x in sorted(family_p_values)], 'strata': len(by),
            'stratum_means': {s: _r(v) for s, v in stratum_means.items()},
            'wins': wins, 'losses': losses, 'ties': len(diffs) - wins - losses, 'failures': failures,
            'cost_cpu_ns': cost, 'cost_ratio': _r(ratio), 'sensitivity': sensitivity}


def decision_from_result(result, plan):
    """Re-derive the decision from a recorded result's own fields (kernel-side consistency)."""
    if not isinstance(result, dict) or result.get('schema') != RESULT_SCHEMA:
        return 'INVALID'
    if result.get('decision') == 'INVALID':
        return 'INVALID'
    try:
        checks = {'holm_rejects_no_superiority': result['checks']['holm_rejects_no_superiority'],
                  'interval_lower_above_zero': result['interval'][0] > 0,
                  'estimate_reaches_minimum_useful_effect': result['estimate'] >= plan['minimum_useful_effect'],
                  'cost_within_bound': plan['cost']['max_ratio'] is None or (
                      result['cost_ratio'] is not None and result['cost_ratio'] <= plan['cost']['max_ratio']),
                  'no_stratum_regression': plan['regression']['max_stratum_loss'] is None or
                  min(result['stratum_means'].values()) >= -plan['regression']['max_stratum_loss']}
        if checks != result['checks'] or result['plan_sha256'] != digest(plan):
            return 'INVALID'
        if result['p_value'] > result['holm_threshold'] and checks['holm_rejects_no_superiority']:
            return 'INVALID'
    except (KeyError, TypeError, ValueError, IndexError):
        return 'INVALID'
    return 'SUPPORTED' if all(checks.values()) else 'NOT_SUPPORTED'
