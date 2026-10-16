#!/usr/bin/env python3
"""B20_R41: E1d readiness (DEV). A DRAFT dense family, compared against an exact MIP and scored by
the generated-rows reference (GV3 path; B20R33-OPEN-1, B20R35-OPEN-1, B20R40-OPEN-1).

    taskset -c 0 python3 scripts/b20r41_e1d_readiness.py OUT_DIR      run (resumable) and analyse

**Why.** Three earlier results lead here:
  * On the decided family, an exact MIP is always optimal, so E1 cannot be "beyond strong
    baselines" there (B20_R33).
  * In a dense planted regime, E1's frozen candidate reached the certified optimum on 19/20 hosts,
    while HiGHS at four times its budget reached it on none (B20_R38).
  * That regime is certifiable only by the generated-rows reference (B20_R35/R37). The custody for
    that reference (B20_R39) and an exact-MIP baseline kind (B20_R40) are built, but not wired.
This study does on DEV for that regime what B20_R24 did for E1: a versioned family rule, a
calibration, and a re-pilot with power. The rule is a DRAFT. The study adopts nothing and changes
no package. It produces the evidence a reviewer would need to decide. Everything below was fixed
before running.

**Draft rule `e1-hard-v3-draft`.** It takes e1-hard-v2's thresholds and changes three things.
  1. **Baselines.** E1's three frozen time-matched DSL programs, at E1's 0.5 CPU s. Plus the exact
     MILP `milp-highs-v1` (registry v2), at 0.5 CPU s and at 2.0 CPU s (four times E1's budget).
     All run in runc. The strongest baseline on a host is the maximum over all five. So the
     ceiling rate and the headroom are measured against an exact MIP given four times the budget.
  2. **Reference.** The generated-rows route: generated_certify.certify_with_rows with B20_R37's v2
     registry and limits (R37.V2), 60 s, with `lp_rounding_seconds=1.0` (new in this commit).
     - Its seed is the evaluator's own seed witness, as in generated_certify.reference: the better
       of the DSL rounds=8 solve and the LP greedy. It is also offered the best baseline witness.
     - After its LP step it rounds the LP's own edge values with construct.lp_greedy for 1 CPU s.
       It keeps the result if larger. Then comes the SAT/DRAT step, unchanged.
     - It never takes candidate input.
  3. **Median reference time ≤ 30 s, not 15 s.** The route's separation step is capped at 15 s by
     the fixed R37.V2 config. e1-hard-v2's 15 s limit was set for obstruction.certify, whose LP
     step takes under a second. With this route, 15 s cannot be met whenever separation reaches
     its cap. The draft allows the separation cap again for LP and SAT, which is half the 60 s
     budget. B20_R38's wall times with an optimal seed informed this choice: median 20.7 s, max
     27.4 s on planted n40 (0.8, 0.06).
  Unchanged from e1-hard-v2:
    * certified fraction ≥ 0.9;
    * ceiling rate in [0, 0.25];
    * mean headroom ≥ 0.02;
    * mean gap ≥ 1.0 edge;
    * at most 4 settings, ordered by the ceiling rate closest to 0, then the faster reference.

**Part A — calibration (candidate-blind: only the baselines and the reference run).**
  * 8 DEV hosts per setting, generator seed 20264101 + 1000 i.
  * The dense grid:
      planted_cluster n36 (0.8, 0.08), n38 (0.8, 0.07), n40 (0.8, 0.06), n40 (0.7, 0.06),
      n40 (0.9, 0.05); erdos n28 p0.45, n30 p0.42, n32 p0.38.
  * Excludes every identity that b20r24_repilots.exposure excludes.
  * The hosts are saved before anything runs, and reloaded on resume (B20R34-OPEN-1).
  * Summary, eligibility and selection use calibration.summarize / eligible / select under the
    draft rule.

**Part B — re-pilot, only if a setting is selected.**
  * 30 fresh DEV hosts, split round-robin over the selected settings, seed 20264151 + 7919 i.
    They exclude Part A's hosts too.
  * Arms, all in runc:
      - E1's frozen candidate (`handoff/e1/candidate_descriptor.json`);
      - its three frozen time-matched baselines (`handoff/e1/time_matched_baselines.json`);
      - `milp-highs-v1` at 0.5 s and at 2.0 s.
  * Reference: the same route with the best witness of any arm, at 120 s, as B20_R24 does.
  * Analysis: b20r24_repilots.analyse with the comparator set made explicit, here all five
    baselines.
      - The comparator is the strongest baseline by pilot total, and may be the MIP at 4× budget.
      - Then: the 75% certification gate per stratum, the B19 DRAFT plan core, a dry run, and the
        centred power model.
      - Verdicts: UNSETTLED_REFERENCE / EFFECT_BELOW_MUE / COST_RULE_FAILS / UNDERPOWERED /
        READY_FOR_REVIEW.
  * Descriptive: candidate − each baseline (mean, W/T/L) and the optimum hits per arm.

**Development looks (disclosed; evidence/e1d_readiness_b20r41/development_looks.json).**
  1. **Smoke run of this script.** A tiny grid with other seeds: planted_cluster n14 (0.8, 0.2) and
     erdos n12 p0.5, 2 hosts each, then 4 pilot hosts, with the thresholds relaxed so that Part B
     runs. These 8 new DEV hosts are disclosed in development_look_hosts.json and the addenda.
     The pipeline ran end to end and resumed from its saved hosts.
  2. **Two already-exposed B20_R38 hosts, every baseline arm plus the reference** (no new hosts).
     - No arm was killed. The MIP took 0.9 cgroup CPU s at its 0.5 s budget and about 2 s at its
       2.0 s budget.
     - On the planted host the evaluator's seed was 111 against an optimum of 122. The route
       reached 122 only by a SAT climb, at 53 s wall with both cores busy.
  3. **Six already-exposed B20_R38 hosts, rounding the route's LP edge values** (no new hosts).
     - On all 4 planted hosts the generated-rows LP was integral: 0 fractional edges, and rounding
       gave the optimum.
     - On 1 of 2 erdos hosts it was integral; on the other it was fractional and rounding gave
       114 against 118.
     This look is why `lp_rounding_seconds` exists. It is candidate-blind, and it was fixed at
     1.0 s before this run.
  The 30 s time limit (change 3) was set before looks 2 and 3, from B20_R38's recorded times.

**Status.** A DEV readiness study under a DRAFT rule. It licenses no claim. A real E1d run would
need all of the following:
  * a reviewer to adopt the rule, the generated-rows reference and the registry v2 wiring;
  * a statistician;
  * an independent custodian.
"""
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C1  # noqa: E402
from genesis import candidates_v2 as C2  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_certify as GC  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402
from genesis.kernel.analysis import analyze  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402

TF = RD.TF
GRID = [('planted_cluster', {'n': 36, 'p_in': 0.8, 'p_out': 0.08}), ('planted_cluster', {'n': 38, 'p_in': 0.8, 'p_out': 0.07}),
        ('planted_cluster', {'n': 40, 'p_in': 0.8, 'p_out': 0.06}), ('planted_cluster', {'n': 40, 'p_in': 0.7, 'p_out': 0.06}),
        ('planted_cluster', {'n': 40, 'p_in': 0.9, 'p_out': 0.05}),
        ('erdos', {'n': 28, 'p': 0.45}), ('erdos', {'n': 30, 'p': 0.42}), ('erdos', {'n': 32, 'p': 0.38})]
CAL_SEED, PER, PILOT_SEED, PILOT_N = 20264101, 8, 20264151, 30
CAL_REF_S, PILOT_REF_S, ROUNDING_S = 60, 120, 1.0
E1_BUDGET = 0.5
MIP_PROFILE = {'cpu_seconds': 3, 'memory_mib': 2048, 'wall_seconds': 15, 'queries': 1000}
BASELINES = ('exchange_tm', 'low_cycle_tm', 'multistart_tm', 'milp_highs_tm', 'milp_highs_4x')
RULE = dict(CAL.SELECTION_RULE_E1_HARD_V2, name='e1-hard-v3-draft', reference_seconds_median_max=30.0,
            measurement={'baselines': "E1's frozen dsl-time-matched-v1 programs at 0.5 s + milp-highs-v1 (registry v2) "
                                      'at 0.5 s and 2.0 s; strongest = per-host maximum of the five',
                         'search_cpu_seconds': E1_BUDGET, 'isolation': 'runc',
                         'reference': 'generated_certify.certify_with_rows with the B20_R37 v2 registry and R37.V2, '
                                      "seeded by the evaluator's seed witness and the best baseline witness",
                         'reference_seconds': CAL_REF_S},
            status='DRAFT (builder); not adopted; not in calibration.RULES')
PACKAGE = ROOT / 'evidence' / 'generator_v2_b20r37' / 'package.json'


def arms():
    d = ROOT / 'handoff' / 'e1'
    out = {'candidate': ('v1', json.loads((d / 'candidate_descriptor.json').read_text()))}
    out.update({n: ('v1', desc) for n, desc in sorted(json.loads((d / 'time_matched_baselines.json').read_text()).items())})
    out['milp_highs_tm'] = ('v2', C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': E1_BUDGET}, **MIP_PROFILE))
    out['milp_highs_4x'] = ('v2', C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': 4 * E1_BUDGET}, **MIP_PROFILE))
    for name, (reg, desc) in out.items():
        problems = (C1 if reg == 'v1' else C2).descriptor_problems(desc)
        if problems:
            raise RuntimeError(f'{name} does not rebuild: {problems}')
    if set(out) != {'candidate', *BASELINES}:
        raise RuntimeError(f'unexpected arms {sorted(out)}')
    return out


def run_arm(task, reg, desc, seed):
    r = (C1 if reg == 'v1' else C2).run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
    ok = r['status'] == 'SUCCESS'
    return ({'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED', 'status': r['status'],
             'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0, 'isolation': r.get('isolation')},
            [tuple(e) for e in r['result']['selected']] if ok else None)


def evaluator_seed(task):
    """generated_certify.reference's seed witness: the better of the DSL rounds=8 solve and the LP greedy."""
    from genesis.discovery.construct import Budget, lp_greedy
    from genesis.dsl import solve
    from genesis.models import SolverProgram
    start = tuple(map(tuple, solve(task, SolverProgram(rounds=8), 100000, 0)['selected']))
    lp = tuple(map(tuple, lp_greedy(task, Budget(1.0), 0)['witness']))
    return list(max((start, lp), key=len))


def reference(task, offered, registry, seconds):
    """The route, seeded by the evaluator's seed and the offered witnesses (never the candidate's in Part A)."""
    t0 = time.monotonic()
    own = evaluator_seed(task)
    seed, source = own, 'evaluator'
    for name, w in offered:
        if w is not None and len(w) > len(seed):
            seed, source = w, name
    rec = GC.certify_with_rows(task, seed, registry, seconds=seconds, lp_rounding_seconds=ROUNDING_S, **R37.V2)
    lp = next((s for s in rec['steps'] if s['step'] == 'lp-dual-rows'), {})
    rd = next((s for s in rec['steps'] if s['step'] == 'lp-rounding'), {})
    sat = next((s for s in rec['steps'] if s['step'] == 'sat-drat'), {'calls': []})
    out = {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'seeded_from': source,
           'seed_value': len(seed), 'evaluator_seed_value': len(own), 'lp_bound': lp.get('bound'),
           'lp_rows': lp.get('rows'), 'lp_wall_s': lp.get('wall_s'), 'rounded_value': rd.get('value'),
           'lp_fractional_edges': rd.get('fractional_edges'), 'sat_calls': len(sat['calls']),
           'route_wall_s': rec['wall_s'], 'wall_s': round(time.monotonic() - t0, 3)}
    return out, (rec['lower'] if rec['lower'] == rec['upper'] else None)


def host_seed(tag, task):
    return int(digest({'study': 'b20r41', 'part': tag, 'task': task.task_id})[:12], 16)


# ---------------------------------------------------------------- Part A

def calibration_hosts(out, log, excluded, scan):
    path = out / 'calibration_hosts.json'
    if path.exists():
        d = json.loads(path.read_text())
        log(f'calibration hosts reloaded from {path.name}')
        return [(s['index'], s['generator'], [GraphTask.model_validate_json(canonical(t)) for t in s['tasks']])
                for s in d['settings']], d['exposure_scan']
    seen, settings = set(excluded), []
    for i, (family, params) in enumerate(GRID):
        tasks, seen, gen = ADAPTERS[TF].generate(CAL_SEED + 1000 * i, PER, 'DEV', family, params, excluded=seen)
        if RD.identities(tasks) & set(excluded):
            raise RuntimeError('a calibration host collides with an excluded identity')
        settings.append((i, gen, tasks))
    R11.dump(path, {'seed': CAL_SEED, 'exposure_scan': scan,
                    'settings': [{'index': i, 'family': GRID[i][0], 'params': GRID[i][1], 'generator': gen,
                                  'tasks': [t.model_dump(mode='json') for t in ts]} for i, gen, ts in settings]})
    return settings, scan


def part_a(out, log, all_arms, registry, settings):
    path = out / 'calibration_rows.jsonl'
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    done = {r['task_id'] for r in rows}
    with path.open('a') as fh:
        for i, _, tasks in settings:
            for t in tasks:
                if t.task_id in done:
                    continue
                seed = host_seed('A', t)
                values, offered, detail = {}, [], {}
                for n in BASELINES:
                    a, sel = run_arm(t, *all_arms[n], seed)
                    values[n] = a['value'] if a['run'] == 'SUCCESS' else None
                    detail[n] = a
                    offered.append((n, sel))
                ref, opt = reference(t, offered, registry, CAL_REF_S)
                r = {'task_id': t.task_id, 'task_sha256': digest(t.model_dump(mode='json')), 'setting': i,
                     'stratum': t.family, 'edges': len(t.edges), 'baselines': values, 'baseline_runs': detail,
                     'reference_seconds': ref['wall_s'], 'ref': ref,
                     'reference': ({'status': 'FINITE_CERTIFIED', 'value': opt, 'method': ref['method']} if opt is not None
                                   else {'status': 'UNSUPPORTED', 'reason': f'bounds {ref["lower"]}..{ref["upper"]}'})}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                rows.append(r)
                log(f'A{i} {t.task_id[-4:]}: ' + json.dumps(values) + f' opt {opt} [{ref["lower"]}..{ref["upper"]}] '
                    f'{ref["method"]} {ref["wall_s"]:.1f}s')
    summaries = []
    for i, gen, tasks in settings:
        srows = [r for r in rows if r['setting'] == i]
        if [r['task_sha256'] for r in srows] != [digest(t.model_dump(mode='json')) for t in tasks]:
            raise RuntimeError(f'setting {i}: rows do not match the saved hosts')
        summary = CAL.summarize(srows, RULE)
        summaries.append({'index': i, 'family': GRID[i][0], 'params': GRID[i][1], 'generator': gen, 'summary': summary,
                          'ineligible_because': CAL.eligible(summary, RULE),
                          'mip_4x_at_optimum': sum(r['baselines']['milp_highs_4x'] == r['reference'].get('value')
                                                   for r in srows if r['reference']['status'] == 'FINITE_CERTIFIED'),
                          'best_dsl_at_optimum': sum(max(r['baselines'][n] or 0 for n in BASELINES[:3]) ==
                                                     r['reference'].get('value') for r in srows
                                                     if r['reference']['status'] == 'FINITE_CERTIFIED')})
    record = {'schema': 'genesis-b20r41-calibration-draft-v1', 'rule': RULE, 'seed': CAL_SEED, 'tasks_per_setting': PER,
              'grid': [{'family': f, 'params': p} for f, p in GRID], 'settings': summaries,
              'selected': CAL.select(summaries, RULE), 'task_sha256s': [r['task_sha256'] for r in rows],
              'note': 'DEV material only; DRAFT rule; not adopted; candidate-blind'}
    R11.dump(out / 'calibration_record.json', record)
    for s in summaries:
        log(f'A{s["index"]} {s["family"]} {s["params"]}: ' + json.dumps(s['summary']) + f' -> {s["ineligible_because"]}')
    log(f'Part A selected {record["selected"]}')
    return record


# ---------------------------------------------------------------- Part B

def pilot_hosts(out, record, excluded):
    path = out / 'pilot_hosts.json'
    if path.exists():
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    chosen = record['selected']
    per = [PILOT_N // len(chosen) + (1 if i < PILOT_N % len(chosen) else 0) for i in range(len(chosen))]
    tasks, seen = [], set(excluded)
    for i, (s, k) in enumerate(zip(chosen, per)):
        ts, seen, _ = ADAPTERS[TF].generate(PILOT_SEED + 7919 * i, k, 'DEV', s['family'], s['params'], excluded=seen)
        if RD.identities(ts) & set(excluded):
            raise RuntimeError('a pilot host collides with an excluded identity')
        tasks += ts
    R11.dump(path, {'seed': PILOT_SEED, 'per_setting': per, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def analyse(rows, names, comparators):
    """b20r24_repilots.analyse with the comparator set given explicitly (here: every baseline)."""
    totals = {n: sum(r['arms'][n]['value'] for r in rows) for n in names}
    comparator = max(comparators, key=lambda n: (totals[n], n))
    strata = sorted({r['stratum'] for r in rows})
    certified = {s: [sum(r['optimum'] is not None for r in rows if r['stratum'] == s),
                     sum(r['stratum'] == s for r in rows)] for s in strata}
    cpu = {n: sum(r['arms'][n]['cpu_ns'] for r in rows) for n in names}
    ratio = cpu['candidate'] / cpu[comparator] if cpu[comparator] else None
    p = R24.plan(TF)
    mue, max_ratio = p['minimum_useful_effect'], p['cost']['max_ratio']
    out = {'hosts': len(rows), 'certified_by_stratum': certified, 'comparator_set': list(comparators),
           'comparator': comparator, 'totals': totals, 'cpu_ns_by_arm': cpu,
           'cpu_ratio_candidate_to_comparator': round(ratio, 4) if ratio else None,
           'failures': {n: sum(r['arms'][n]['run'] == 'FAILED' for r in rows) for n in names}}
    if any(c < math.ceil(0.75 * n) for c, n in certified.values()):
        return dict(out, verdict='UNSETTLED_REFERENCE'), None
    scored = [r for r in rows if r['optimum'] is not None]
    prow = [{'task_id': r['task_id'], 'stratum': r['stratum'], 'status': 'SCORED', 'split': r['split'],
             'optimum': r['optimum'],
             'candidate': {k: r['arms']['candidate'][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: r['arms'][comparator][k] for k in ('value', 'run', 'cpu_ns')}} for r in scored]
    result = analyze(prow, p)
    power = required_sample(prow, p, sims=1000, min_tasks_per_stratum=10, headroom='centred')
    chosen = (power.get('chosen') or {}).get('tasks_per_stratum')
    diffs = [r['candidate']['value'] - r['baseline']['value'] for r in prow]
    mean = statistics.fmean(diffs)
    verdict = ('EFFECT_BELOW_MUE' if mean < mue else 'COST_RULE_FAILS' if ratio is None or ratio > max_ratio else
               'UNDERPOWERED' if not chosen else 'READY_FOR_REVIEW')
    by = {}
    for r in prow:
        by.setdefault(r['stratum'], []).append(r['candidate']['value'] - r['baseline']['value'])

    def contrast(b):
        d = [r['arms']['candidate']['value'] - r['arms'][b]['value'] for r in scored]
        return {'mean': round(statistics.fmean(d), 4), 'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d),
                                                                             sum(x < 0 for x in d)]}
    out.update({
        'scored': len(prow), 'mean_difference': round(mean, 4),
        'stratum_mean_differences': {s: round(statistics.fmean(v), 4) for s, v in sorted(by.items())},
        'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
        'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in scored) for n in names},
        'mean_gap_to_optimum': {n: round(statistics.fmean(r['optimum'] - r['arms'][n]['value'] for r in scored), 4)
                                for n in names},
        'candidate_minus_each_baseline': {b: contrast(b) for b in comparators},
        'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value', 'checks',
                                                           'cost_ratio')},
        'power_centred': {k: power.get(k) for k in ('status', 'chosen', 'power_at_minimum_useful_effect',
                                                     'false_positive_rate_at_zero_effect', 'pilot_strata', 'table')},
        'approximation_agreement': approximation_check(prow, p, chosen, sims=40, headroom='centred') if chosen else None,
        'verdict': verdict})
    return out, power


def part_b(out, log, all_arms, registry, record, excluded):
    tasks = pilot_hosts(out, record, excluded)
    path = out / 'pilot_rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            seed = host_seed('B', t)
            res, offered = {}, []
            for n, (reg, desc) in all_arms.items():
                res[n], sel = run_arm(t, reg, desc, seed)
                offered.append((n, sel))
            ref, opt = reference(t, offered, registry, PILOT_REF_S)
            r = {'task_id': t.task_id, 'stratum': t.family, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'B {t.task_id[-4:]}: ' + json.dumps({k: a['value'] for k, a in res.items()}) +
                f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.1f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    analysis, power = analyse(rows, ['candidate', *BASELINES], list(BASELINES))
    R11.dump(out / 'pilot_summary.json', analysis)
    if power is not None:
        R11.dump(out / 'power_analysis_centred.json', power)
    log(f'Part B: {analysis["verdict"]}; comparator {analysis["comparator"]}; mean {analysis.get("mean_difference")}; '
        f'cpu ratio {analysis["cpu_ratio_candidate_to_comparator"]}')
    return analysis


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}; pid {os.getpid()}')
    from genesis.verification.tools import tool
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim')))   # fail fast
    all_arms = arms()
    registry = R37.registry_v2(json.loads(PACKAGE.read_text()))
    excluded, scan, _ = R24.exposure(log)
    settings, scan = calibration_hosts(out, log, excluded, scan)
    record = part_a(out, log, all_arms, registry, settings)
    cal_ids = RD.identities([t for _, _, ts in settings for t in ts])
    b = part_b(out, log, all_arms, registry, record, set(excluded) | cal_ids) if record['selected'] else None
    verdict = b['verdict'] if b else 'NO_ELIGIBLE_SETTING'
    R11.dump(out / 'summary.json', {'schema': 'genesis-b20r41-e1d-readiness-v1', 'rule': RULE['name'],
                                    'selected': record['selected'], 'pilot': b, 'verdict': verdict,
                                    'descriptors': {n: d['descriptor_id'] for n, (_, d) in all_arms.items()},
                                    'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
                                    'status': 'DEV readiness under a DRAFT rule; licenses no claim; adopts nothing'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
