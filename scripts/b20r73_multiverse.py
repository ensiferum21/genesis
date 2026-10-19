#!/usr/bin/env python3
"""B20_R73: how robust are E1d's DEV verdicts to reasonable analysis choices? A multiverse analysis (preregistered)

    python3 scripts/b20r73_multiverse.py OUT_DIR      analysis only: reads committed rows, runs no solver

**Why.** Each E1d DEV study fixed one analysis before running: the mean difference, a 90% percentile bootstrap,
MUE 0.5, stratified where the hosts have strata. Those choices are reasonable but not unique, and the statistician's
review (B19-OPEN-4) is still pending. Multiverse analysis (Steegen et al. 2016) and many-analysts studies
(Silberzahn et al. 2018) show that conclusions can hinge on such choices; the honest report states how many
reasonable analyses agree (docs/PHYSICS_INSPIRED_PLAN.md, idea 5). This batch re-reads the saved rows of
B20_R63, R64, R66 and R68 under a grid of alternative analyses. It changes no verdict: the preregistered verdicts
stand, and this reports their robustness.

**The contrasts** (candidate − comparator per host, from each study's `rows.jsonl`; failed runs score 0 as in the
studies): B20_R63, HiGHS at 2, 4, 8, 16, 32 s (30 hosts, 3 strata); B20_R64, HiGHS at 2, 8, 32 s for each of n40,
n50, n60 (10 hosts each); B20_R66, HiGHS at 32 and 60 s (20 hosts); B20_R68, tabu at 0.5 s, Part A (30 hosts, 3
strata) and Part B (20 hosts). 18 contrasts.

**The universe of analyses** (fixed before running): MUE in {0.25, 0.5, 1.0}; interval level in {90%, 95%};
estimator and interval in {mean with percentile bootstrap, mean with Student t, median with percentile bootstrap};
stratification in {as preregistered, pooled}; bootstrap seed in {the study's own, 20267301, 20267302, 20267303}
(4,000 resamples). The t interval needs no seed. Each analysis maps the interval to the studies' common rule:
AHEAD (lower end > MUE), NO_MATERIAL_DIFFERENCE (inside (−MUE, MUE)), BEHIND (upper end < −MUE), UNRESOLVED;
a contrast with failures is FAILURES in every analysis. 108 analyses per stratified contrast, 54 per unstratified
one (pooling changes nothing there, so it is not double-counted).

**Study-level verdicts** are recomputed in every analysis with each study's own combination rule: B20_R63's
crossover budget (the first HiGHS budget that is not AHEAD), B20_R64's overall verdict (`b20r64_e1d_scaling.overall`
over the per-n crossovers), B20_R66's overall verdict (`b20r66_e1d_n60.overall`), B20_R68's overall verdict (from
Part A). The analysis grid for a study-level verdict is the product grid without the bootstrap seed varying across
its contrasts (one seed per analysis).

**Robustness label** per contrast and per study-level verdict: ROBUST if at least 90% of analyses agree with the
preregistered verdict, MIXED if 50–90%, FRAGILE below 50%. For every non-robust item the report names the
analysis choices under which it changes.

**Expectation, stated before running.** The large effects (B20_R63 at 2–4 s, B20_R64 and R66 at n60, B20_R68 Part
A's tie) are ROBUST. Borderline ones change with MUE: B20_R63 at 8 s (+0.43 [0.03, 0.90]) and B20_R68 Part B
(−1.15 [−1.65, −0.70]) become UNRESOLVED at MUE 1.0; the study-level verdicts of B20_R63 (crossover at 8 s), R66
and R68 remain ROBUST or MIXED, none FRAGILE.

**Development looks.** All four studies' verdicts are known (that is the point); no alternative analysis has been
computed on any of them.

**Status.** An analysis of committed DEV evidence. It changes no verdict and licenses nothing.
"""
import itertools
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r63_e1d_crossover as R63  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402
import b20r66_e1d_n60 as R66  # noqa: E402
import b20r68_e1d_domain_heuristic as R68  # noqa: E402

EV = ROOT / 'evidence'
BOOT = 4000
MUES = (0.25, 0.5, 1.0)
LEVELS = (0.90, 0.95)
METHODS = ('boot-mean', 't-mean', 'boot-median')
STRATS = ('preregistered', 'pooled')
EXTRA_SEEDS = (20267301, 20267302, 20267303)
NORMAL = {'ADVANTAGE': 'AHEAD', 'CANDIDATE_AHEAD': 'AHEAD', 'NO_MATERIAL_DIFFERENCE': 'NO_MATERIAL_DIFFERENCE',
          'MIP_AHEAD': 'BEHIND', 'HEURISTIC_AHEAD': 'BEHIND', 'UNRESOLVED': 'UNRESOLVED',
          'UNRESOLVED_FAILURES': 'FAILURES'}
BACK = {'AHEAD': 'ADVANTAGE', 'NO_MATERIAL_DIFFERENCE': 'NO_MATERIAL_DIFFERENCE', 'BEHIND': 'MIP_AHEAD',
        'UNRESOLVED': 'UNRESOLVED', 'FAILURES': 'UNRESOLVED_FAILURES'}


def _rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _diffs(rows, comp, strata):
    by = {}
    fails = 0
    for r in rows:
        a, b = r['arms']['candidate'], r['arms'][comp]
        fails += (a['run'] != 'SUCCESS') + (b['run'] != 'SUCCESS')
        by.setdefault(r['stratum'] if strata else 'all', []).append(a['value'] - b['value'])
    return by, fails


def contrasts():
    """[{'id', 'study', 'by', 'failures', 'prereg', 'seed'}] for the 18 contrasts."""
    out = []
    s63 = json.loads((EV / 'e1d_crossover_b20r63' / 'summary.json').read_text())
    rows = _rows(EV / 'e1d_crossover_b20r63' / 'rows.jsonl')
    for b in R63.BUDGETS:
        a = R63.arm_name(b)
        by, f = _diffs(rows, a, True)
        out.append({'id': f'B20_R63 {a}', 'study': 'B20_R63', 'arm': a, 'by': by, 'failures': f,
                    'prereg': NORMAL[s63['per_budget'][a]['verdict']], 'seed': R63.BOOT_SEED})
    s64 = json.loads((EV / 'e1d_scaling_b20r64' / 'summary.json').read_text())
    rows = _rows(EV / 'e1d_scaling_b20r64' / 'rows.jsonl')
    for n in R64.NS:
        for b in R64.BUDGETS:
            a = R63.arm_name(b)
            by, f = _diffs([r for r in rows if r['n'] == n], a, False)
            out.append({'id': f'B20_R64 n{n} {a}', 'study': 'B20_R64', 'n': n, 'arm': a, 'by': by, 'failures': f,
                        'prereg': NORMAL[s64['by_n'][str(n)]['per_budget'][a]['verdict']], 'seed': R64.BOOT_SEED})
    s66 = json.loads((EV / 'e1d_n60_b20r66' / 'summary.json').read_text())
    rows = _rows(EV / 'e1d_n60_b20r66' / 'rows.jsonl')
    for b in R66.BUDGETS:
        a = R63.arm_name(b)
        by, f = _diffs(rows, a, False)
        out.append({'id': f'B20_R66 {a}', 'study': 'B20_R66', 'arm': a, 'by': by, 'failures': f,
                    'prereg': NORMAL[s66['per_budget'][a]['verdict']], 'seed': R66.BOOT_SEED})
    s68 = json.loads((EV / 'e1d_domain_heuristic_b20r68' / 'summary.json').read_text())
    rows = _rows(EV / 'e1d_domain_heuristic_b20r68' / 'rows.jsonl')
    for part in ('A', 'B'):
        by, f = _diffs([r for r in rows if r['part'] == part], R68.PRIMARY, True)
        out.append({'id': f'B20_R68 Part {part}', 'study': 'B20_R68', 'part': part, 'by': by, 'failures': f,
                    'prereg': NORMAL[s68['parts'][part]['primary_candidate_minus_tabu_0.5s']['verdict']],
                    'seed': R68.BOOT_SEED})
    return out


def _t_quantile(p, df):
    from scipy.stats import t
    return float(t.ppf(p, df))


def interval(by, method, level, seed):
    """The estimate's (lower, upper) interval for one analysis; strata weighted equally, as in the studies."""
    strata = sorted(by)
    agg = statistics.fmean if method in ('boot-mean', 't-mean') else statistics.median
    alpha = (1 - level) / 2
    if method == 't-mean':
        est = statistics.fmean(statistics.fmean(by[s]) for s in strata)
        var = sum((statistics.variance(by[s]) if len(by[s]) > 1 else 0.0) / len(by[s]) for s in strata) / len(strata) ** 2
        df = sum(len(by[s]) - 1 for s in strata)
        half = _t_quantile(1 - alpha, df) * var ** 0.5
        return est - half, est + half
    rng = random.Random(seed)
    sims = sorted(statistics.fmean(agg([rng.choice(by[s]) for _ in by[s]]) for s in strata) for _ in range(BOOT))
    return sims[int(alpha * BOOT)], sims[int((1 - alpha) * BOOT) - 1]


def rule(ci, mue, failures):
    lo, hi = ci
    if failures:
        return 'FAILURES'
    if lo > mue:
        return 'AHEAD'
    if -mue < lo and hi < mue:
        return 'NO_MATERIAL_DIFFERENCE'
    if hi < -mue:
        return 'BEHIND'
    return 'UNRESOLVED'


_CACHE = {}


def cached_interval(c, strat, level, method, seed):
    key = (c['id'], strat, level, method, seed)
    if key not in _CACHE:
        by = c['by'] if strat == 'preregistered' else {'all': [x for v in c['by'].values() for x in v]}
        _CACHE[key] = interval(by, method, level, seed)
    return _CACHE[key]


def analyses(c):
    """[(choices, verdict)] for one contrast over its universe."""
    out = []
    stratified = len(c['by']) > 1
    for strat in (STRATS if stratified else STRATS[:1]):
        for level in LEVELS:
            for method in METHODS:
                seeds = (None,) if method == 't-mean' else (c['seed'],) + EXTRA_SEEDS
                for seed in seeds:
                    ci = cached_interval(c, strat, level, method, seed)
                    for mue in MUES:
                        out.append(({'strat': strat, 'level': level, 'method': method, 'seed': seed, 'mue': mue},
                                    rule(ci, mue, c['failures'])))
    return out


def label(share):
    return 'ROBUST' if share >= 0.9 else 'MIXED' if share >= 0.5 else 'FRAGILE'


def flips(results, prereg):
    """Which single choice values make the verdict differ most often: {dimension: {value: agreement share}}."""
    dims = {}
    for choices, v in results:
        for k, val in choices.items():
            dims.setdefault(k, {}).setdefault(str(val), []).append(v == prereg)
    return {k: {val: round(sum(x) / len(x), 3) for val, x in vals.items()} for k, vals in dims.items()
            if len(vals) > 1}


def study_levels(cs):
    """Study-level verdicts in every analysis (one seed per analysis across a study's contrasts)."""
    out = {}
    by_study = {}
    for c in cs:
        by_study.setdefault(c['study'], []).append(c)
    grid = [dict(zip(('strat', 'level', 'method', 'k', 'mue'), x))
            for x in itertools.product(STRATS, LEVELS, METHODS, range(1 + len(EXTRA_SEEDS)), MUES)
            if not (x[2] == 't-mean' and x[3] > 0)]
    for study, group in by_study.items():
        res = []
        for g in grid:
            per = {}
            for c in group:
                strat = g['strat'] if len(c['by']) > 1 else 'preregistered'
                seed = None if g['method'] == 't-mean' else ((c['seed'],) + EXTRA_SEEDS)[g['k']]
                per[c['id']] = rule(cached_interval(c, strat, g['level'], g['method'], seed), g['mue'], c['failures'])
            res.append((g, _combine(study, group, per)))
        out[study] = res
    return out


def _combine(study, group, per):
    if study == 'B20_R63':
        for c in group:
            if per[c['id']] != 'AHEAD':
                return f"crossover {R63.BUDGETS[[x['id'] for x in group].index(c['id'])]}"
        return 'no crossover'
    if study == 'B20_R64':
        cross = {}
        for n in R64.NS:
            vs = [(c, per[c['id']]) for c in group if c['n'] == n]
            first = next((R64.BUDGETS[i] for i, (_, v) in enumerate(vs) if v != 'AHEAD'), None)
            cross[n] = (first, any(v == 'FAILURES' for _, v in vs))
        return R64.overall(cross)
    if study == 'B20_R66':
        p = {c['arm']: {'verdict': BACK[per[c['id']]]} for c in group}
        return R66.overall(p, True)
    if study == 'B20_R68':
        a = next(per[c['id']] for c in group if c['part'] == 'A')
        return R68.OVERALL.get({'AHEAD': 'CANDIDATE_AHEAD', 'BEHIND': 'HEURISTIC_AHEAD'}.get(a, a), 'UNRESOLVED')
    raise ValueError(study)


def preregistered_study_verdicts():
    s63 = json.loads((EV / 'e1d_crossover_b20r63' / 'summary.json').read_text())
    s64 = json.loads((EV / 'e1d_scaling_b20r64' / 'summary.json').read_text())
    s66 = json.loads((EV / 'e1d_n60_b20r66' / 'summary.json').read_text())
    s68 = json.loads((EV / 'e1d_domain_heuristic_b20r68' / 'summary.json').read_text())
    b = s63['crossover_budget_s']
    return {'B20_R63': f'crossover {b}' if b is not None else 'no crossover', 'B20_R64': s64['verdict'],
            'B20_R66': s66['verdict'], 'B20_R68': s68['verdict']}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    cs = contrasts()
    per_contrast = {}
    for c in cs:
        res = analyses(c)
        share = sum(v == c['prereg'] for _, v in res) / len(res)
        dist = {}
        for _, v in res:
            dist[v] = dist.get(v, 0) + 1
        per_contrast[c['id']] = {'preregistered': c['prereg'], 'analyses': len(res), 'agreement': round(share, 4),
                                 'label': label(share), 'verdicts': dict(sorted(dist.items())),
                                 'by_choice': flips(res, c['prereg'])}
    pre = preregistered_study_verdicts()
    levels = {}
    for study, res in study_levels(cs).items():
        share = sum(v == pre[study] for _, v in res) / len(res)
        dist = {}
        for _, v in res:
            dist[v] = dist.get(v, 0) + 1
        levels[study] = {'preregistered': pre[study], 'analyses': len(res), 'agreement': round(share, 4),
                         'label': label(share), 'verdicts': dict(sorted(dist.items())),
                         'by_choice': flips([({k: v for k, v in g.items() if k != 'k'}, x) for g, x in res], pre[study])}
    counts = {lab: sum(x['label'] == lab for x in per_contrast.values()) for lab in ('ROBUST', 'MIXED', 'FRAGILE')}
    summary = {'schema': 'genesis-b20r73-multiverse-v1', 'contrast_labels': counts, 'contrasts': per_contrast,
               'study_level': levels,
               'universe': {'mue': list(MUES), 'levels': list(LEVELS), 'methods': list(METHODS),
                            'stratification': list(STRATS), 'extra_seeds': list(EXTRA_SEEDS), 'boot': BOOT},
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'robustness of committed DEV verdicts; changes no verdict; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    for k, v in per_contrast.items():
        print(f"{k:28} {v['preregistered']:24} {v['label']:8} {v['agreement']:.3f} {v['verdicts']}")
    for k, v in levels.items():
        print(f"{k:28} {v['preregistered']:36} {v['label']:8} {v['agreement']:.3f} {v['verdicts']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
