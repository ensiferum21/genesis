#!/usr/bin/env python3
"""B20_R50: E1b's C4 arm, made scorable by the transferred rows. A DRAFT C4 rule whose reference is the
tree route, a candidate-blind calibration, and a readiness and causal re-pilot (DEV; GV3 path in the C4
domain).

    taskset -c 0 python3 scripts/b20r50_e1b_c4_readiness.py OUT_DIR      run (resumable) and analyse

**Why.** E1b, the LP-guided construct-pipeline-v1 candidate, has no study on C4.
  * Under e1-hard-v2, no C4 setting was eligible (B20_R24): the small settings sit at the time-matched
    ceiling, and the one with headroom, erdos n30 p0.2 (E1b's C3), failed the certification limit
    (6/8 certified within 60 s) and the evaluator-speed limit (median 24 s).
  * B20_R23's C4 causal pilot was UNSETTLED_REFERENCE.
  * B20_R48 found a certification route that meets the limit on that setting and on erdos n36 p0.17:
    branch and bound over the rows the system invented and transferred to C4, with exact tree
    certificates (38 vs 26 of 40, p 0.00024).
This step does on DEV for C4 what B20_R41 did for E1d. It is a DRAFT. It adopts nothing and changes no
package. Everything below is fixed before running.

**Draft rule `e1-hard-v2-c4tree-draft`.** e1-hard-v2 (calibration.SELECTION_RULE_E1_HARD_V2), with one
change: **the reference.**
  * It is `generated_bnb_c4.certify_with_tree` with B20_R46's registry, B20_R47's limits and 1 CPU s of
    LP rounding, 60 s per host.
  * Its seed is the evaluator's own seed witness, or the best baseline witness if that is larger.
  * A host counts as certified only if the tree checker (`verification.lp_dual_tree_c4`) accepts the
    certificate with lower == upper.
  * The reference time is the route's wall time plus the exact check.
Everything else is unchanged:
  * time-matched DSL baselines at 2.0 CPU s in runc;
  * certified fraction ≥ 0.9;
  * ceiling rate in [0, 0.25];
  * relative headroom ≥ 0.02;
  * mean gap ≥ 1.0 edge;
  * median reference time ≤ 15 s;
  * at most 4 settings.

**Part A: calibration.** It is candidate-blind: only the three baselines and the reference run.
  * **Grid.** It is fixed here, and is the settings where certification, not the ceiling, was the
    binding question:
    - erdos n30 p0.2 (E1b's C3, the only e1-hard-v2 C4 setting with headroom);
    - erdos n36 p0.17 (B20_R47/R48);
    - erdos n32 p0.2;
    - erdos n40 p0.15.
    The 13 small settings of the C4 domain grid are not re-measured. Under e1-hard-v2 they were all
    certified within the limit and all failed on the ceiling and headroom, which the reference does not
    change.
  * **Hosts.** 8 DEV hosts per setting, seed 20265001 + 1000 i. They exclude every identity that
    b20r24_repilots.exposure excludes, and are saved with the exposure scan before running.
  * **Descriptive (no part of the rule).** An exact C4 MIP, HiGHS over the 4-cycle rows in-process as
    b20r33's `mip`, at 2.0 s and at 8.0 s (four times the budget), and its optimum hits.

**Part B: re-pilot**, only if a setting is selected.
  * **Hosts.** 30 fresh DEV hosts, round-robin over the selected settings, seed 20265051 + 7919 i. They
    exclude Part A's hosts too.
  * **Arms.** All in runc with the E1b profile {cpu 4 s, 2048 MiB, wall 20 s, 1000 queries}, seed
    digest({'study': 'b20r50', 'part': 'B', 'task': id})[:12]:
    - the candidate: construct-pipeline-v1 {init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0,
      seed 0}, for c4_host_v2, as B20_R23 built it;
    - the three time-matched DSL baselines;
    - the registered ablation (init random_greedy) and placebo (init lp_shuffled_greedy), each checked
      with replay_contracts.intervention_problems.
    - Descriptive: the C4 MIP at 2.0 s and 8.0 s.
  * **Reference.** The same route at 120 s, seeded with the best witness of any arm, as B20_R24 does.
  * **Analysis.** As B20_R41's `analyse`: the 75% certification gate per stratum, the B19 DRAFT plan
    core with family `sealed_evaluation:c4_host_v2`, a dry run, and the centred power model. Three
    contrasts:
    - readiness: the candidate against the strongest DSL baseline by pilot total;
    - causal: the candidate against the ablation, and against the placebo.
    Verdicts per contrast: UNSETTLED_REFERENCE / EFFECT_BELOW_MUE / COST_RULE_FAILS / UNDERPOWERED /
    READY_FOR_REVIEW.
  * **Descriptive.** The candidate against each MIP budget (mean, W/T/L), and the optimum hits per arm.

**Development looks (disclosed).**
  * Earlier results on these settings: B20_R23/R24 on erdos n30 p0.2, and B20_R47/R48 on erdos n36 p0.17.
    The builder has seen E1b's DEV results on C3 (B20_R23).
  * A smoke run of this script on 4 calibration and 4 pilot hosts (seeds 999501 and 999551; 2 per setting
    for the first two settings; reference at 15 s; the rule's limits relaxed so that Part B ran). Every
    reference certified, in 2.6–3.7 s.
    - On the 4 pilot hosts, the candidate was 1.0 above the best DSL baseline and 1.0 below the optimum.
    - The C4 MIP at 2.0 s was optimal on all 4.
    The expected descriptive result is that an exact MIP dominates E1b on C4 too, as on triangle-free
    (B20R33-OPEN-1). The rule's comparators are the DSL baselines, so the readiness verdict does not
    depend on this.

A DEV readiness study. It licenses no claim and adopts no rule. A causal level still needs signed
custodian evaluations.
"""
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_bnb_c4 as GB  # noqa: E402
from genesis.discovery.construct import Budget  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.kernel.analysis import analyze  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402
from genesis.verification import lp_dual_tree_c4 as VT  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_causal_readiness as R23C  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r47_c4_certification as R47  # noqa: E402

C4 = RD.C4
GRID = [('erdos', {'n': 30, 'p': 0.2}), ('erdos', {'n': 36, 'p': 0.17}), ('erdos', {'n': 32, 'p': 0.2}),
        ('erdos', {'n': 40, 'p': 0.15})]
PER, CAL_SEED = 8, 20265001
PILOT_N, PILOT_SEED = 30, 20265051
CAL_REF_S, PILOT_REF_S = 60, 120
SEARCH_S = RD.SEARCH_S
MIP_BUDGETS = {'mip_tm': SEARCH_S, 'mip_4x': 4 * SEARCH_S}
DSL = ('exchange_tm', 'low_cycle_tm', 'multistart_tm')
CAUSAL = ('ablation', 'placebo')
ROUTE = dict(R47.ROUTE)
RULE = dict(CAL.SELECTION_RULE_E1_HARD_V2, name='e1-hard-v2-c4tree-draft',
            measurement=dict(CAL.SELECTION_RULE_E1_HARD_V2['measurement'],
                             reference='generated_bnb_c4.certify_with_tree with the B20_R46 registry and B20_R47 limits, '
                                       'seeded with the better of the evaluator seed and the best baseline witness; '
                                       'certified iff the exact tree check accepts with lower == upper',
                             reference_seconds=CAL_REF_S),
            note='DRAFT (B20_R50): e1-hard-v2 with the tree route as reference; not adopted by any study')


def arms():
    """{name: descriptor}: the candidate, the three DSL baselines and the two registered interventions."""
    base = RD.arms(C4)
    causal = R23C.arms(C4)
    out = {'candidate': base['candidate'], **{n: base[n] for n in DSL}, **{k: causal[k] for k in CAUSAL}}
    if causal['candidate']['descriptor_id'] != base['candidate']['descriptor_id']:
        raise RuntimeError('the causal arms do not intervene on the readiness candidate')
    for name, desc in out.items():
        problems = C.descriptor_problems(desc)
        if problems:
            raise RuntimeError(f'{name} does not rebuild: {problems}')
    return out


def run_arm(task, desc, seed):
    r = C.run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
    ok = r['status'] == 'SUCCESS'
    return ({'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED', 'status': r['status'],
             'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0, 'isolation': r.get('isolation')},
            [tuple(e) for e in r['result']['selected']] if ok else None)


def mip(task, seconds):
    """HiGHS over the 4-cycle rows (x(C) <= 3), in process, as b20r33's mip for triangles. Descriptive only."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    from genesis.discovery.obstruction import four_cycles
    b = Budget(seconds)
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    cyc = four_cycles(task)
    A = lil_matrix((max(1, len(cyc)), len(E)))
    for j, es in enumerate(cyc):
        for e in es:
            A[j, idx[tuple(e)]] = 1
    res = milp(-np.ones(len(E)), constraints=LinearConstraint(A.tocsr(), -np.inf, 3), integrality=np.ones(len(E)),
               bounds=Bounds(0, 1), options={'time_limit': max(0.05, seconds - b.used())})
    cpu = b.used()
    sel = [E[i] for i in range(len(E)) if res.x is not None and res.x[i] > 0.5]
    value = check_witness(task, sel)['value'] if res.x is not None else 0
    over = cpu > R33.OVERRUN * seconds
    return ({'value': 0 if over else value, 'raw_value': value, 'cpu_s': round(cpu, 3), 'status': int(res.status),
             'overrun': over, 'proved_optimal': int(res.status) == 0, 'run': 'SUCCESS', 'cpu_ns': int(cpu * 1e9)},
            sel if value and not over else None)


def reference(task, offered, registry, seconds):
    """The tree route, seeded by the better of the evaluator's seed and the offered witnesses, then checked."""
    t0 = time.monotonic()
    own = R41.evaluator_seed(task)
    seed, source = own, 'evaluator'
    for name, w in offered:
        if w is not None and len(w) > len(seed):
            seed, source = w, name
    rec = GB.certify_with_tree(task, seed, registry, seconds=seconds, **ROUTE)
    v = VT.check_certificate(task, rec['certificate'], registry) if rec['certificate'] is not None else {'verdict': 'NONE'}
    ok = v['verdict'] == 'VALID' and v.get('bound') == rec['upper']
    out = {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'seeded_from': source,
           'seed_value': len(seed), 'evaluator_seed_value': len(own), 'nodes': rec['nodes'], 'check': v['verdict'],
           'route_wall_s': rec['wall_s'], 'wall_s': round(time.monotonic() - t0, 3)}
    return out, (rec['lower'] if ok and rec['lower'] == rec['upper'] else None)


def host_seed(tag, task):
    return int(digest({'study': 'b20r50', 'part': tag, 'task': task.task_id})[:12], 16)


def calibration_hosts(out, log, excluded, scan):
    path = out / 'calibration_hosts.json'
    if path.exists():
        saved = json.loads(path.read_text())
        log('resume: calibration hosts and the exposure scan reloaded')
        return ([(s['index'], s['generator'], [GraphTask.model_validate_json(canonical(t)) for t in s['tasks']])
                 for s in saved['settings']], saved['exposure_scan'])
    seen, settings = set(excluded), []
    for i, (family, params) in enumerate(GRID):
        tasks, seen, gen = ADAPTERS[C4].generate(CAL_SEED + 1000 * i, PER, 'DEV', family, params, excluded=seen)
        settings.append((i, gen, tasks))
    if RD.identities([t for _, _, ts in settings for t in ts]) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    R11.dump(path, {'exposure_scan': scan, 'settings': [{'index': i, 'generator': g, 'tasks': [t.model_dump(mode='json') for t in ts]}
                                                        for i, g, ts in settings]})
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
                for n in DSL:
                    a, sel = run_arm(t, all_arms[n], seed)
                    values[n] = a['value'] if a['run'] == 'SUCCESS' else None
                    detail[n] = a
                    offered.append((n, sel))
                ref, opt = reference(t, offered, registry, CAL_REF_S)
                mips = {n: mip(t, s)[0] for n, s in MIP_BUDGETS.items()}
                r = {'task_id': t.task_id, 'task_sha256': digest(t.model_dump(mode='json')), 'setting': i,
                     'stratum': t.family, 'edges': len(t.edges), 'baselines': values, 'baseline_runs': detail,
                     'mip': mips, 'reference_seconds': ref['wall_s'], 'ref': ref,
                     'reference': ({'status': 'FINITE_CERTIFIED', 'value': opt, 'method': ref['method']} if opt is not None
                                   else {'status': 'UNSUPPORTED', 'reason': f'bounds {ref["lower"]}..{ref["upper"]}'})}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                rows.append(r)
                log(f'A{i} {t.task_id[-4:]}: ' + json.dumps(values) + f' mip {mips["mip_tm"]["value"]}/{mips["mip_4x"]["value"]}'
                    f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["method"]} {ref["wall_s"]:.1f}s')
    summaries = []
    for i, gen, tasks in settings:
        srows = [r for r in rows if r['setting'] == i]
        if [r['task_sha256'] for r in srows] != [digest(t.model_dump(mode='json')) for t in tasks]:
            raise RuntimeError(f'setting {i}: rows do not match the saved hosts')
        summary = CAL.summarize(srows, RULE)
        cert = [r for r in srows if r['reference']['status'] == 'FINITE_CERTIFIED']
        summaries.append({'index': i, 'family': GRID[i][0], 'params': GRID[i][1], 'generator': gen, 'summary': summary,
                          'ineligible_because': CAL.eligible(summary, RULE),
                          'mip_at_optimum': {n: sum(r['mip'][n]['value'] == r['reference']['value'] for r in cert)
                                             for n in MIP_BUDGETS},
                          'best_dsl_at_optimum': sum(max(r['baselines'][n] or 0 for n in DSL) == r['reference']['value']
                                                     for r in cert)})
    record = {'schema': 'genesis-b20r50-calibration-draft-v1', 'rule': RULE, 'seed': CAL_SEED, 'tasks_per_setting': PER,
              'grid': [{'family': f, 'params': p} for f, p in GRID], 'settings': summaries,
              'selected': CAL.select(summaries, RULE), 'task_sha256s': [r['task_sha256'] for r in rows],
              'note': 'DEV material only; DRAFT rule; not adopted; candidate-blind'}
    R11.dump(out / 'calibration_record.json', record)
    for s in summaries:
        log(f'A{s["index"]} {s["family"]} {s["params"]}: ' + json.dumps(s['summary']) + f' -> {s["ineligible_because"]}')
    log(f'Part A selected {record["selected"]}')
    return record


def pilot_hosts(out, record, excluded):
    path = out / 'pilot_hosts.json'
    if path.exists():
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    chosen = record['selected']
    per = [PILOT_N // len(chosen) + (1 if i < PILOT_N % len(chosen) else 0) for i in range(len(chosen))]
    tasks, seen = [], set(excluded)
    for i, (s, k) in enumerate(zip(chosen, per)):
        ts, seen, _ = ADAPTERS[C4].generate(PILOT_SEED + 7919 * i, k, 'DEV', s['family'], s['params'], excluded=seen)
        tasks += ts
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a pilot host collides with an excluded host')
    R11.dump(path, {'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def analyse(rows, names, comparators):
    """b20r41.analyse for c4_host_v2 (plan family sealed_evaluation:c4_host_v2)."""
    totals = {n: sum(r['arms'][n]['value'] for r in rows) for n in names}
    comparator = max(comparators, key=lambda n: (totals[n], n))
    strata = sorted({r['stratum'] for r in rows})
    certified = {s: [sum(r['optimum'] is not None for r in rows if r['stratum'] == s),
                     sum(r['stratum'] == s for r in rows)] for s in strata}
    cpu = {n: sum(r['arms'][n]['cpu_ns'] for r in rows) for n in names}
    ratio = cpu['candidate'] / cpu[comparator] if cpu[comparator] else None
    p = R24.plan(C4)
    mue, max_ratio = p['minimum_useful_effect'], p['cost']['max_ratio']
    out = {'hosts': len(rows), 'certified_by_stratum': certified, 'comparator_set': list(comparators),
           'comparator': comparator, 'totals': totals, 'cpu_ratio_candidate_to_comparator': round(ratio, 4) if ratio else None,
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
    out.update({
        'scored': len(prow), 'mean_difference': round(mean, 4),
        'stratum_mean_differences': {s: round(statistics.fmean(v), 4) for s, v in sorted(by.items())},
        'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
        'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value', 'checks', 'cost_ratio')},
        'power_centred': {k: power.get(k) for k in ('status', 'chosen', 'power_at_minimum_useful_effect',
                                                     'false_positive_rate_at_zero_effect', 'pilot_strata', 'table')},
        'approximation_agreement': approximation_check(prow, p, chosen, sims=40, headroom='centred') if chosen else None,
        'verdict': verdict})
    return out, power


def descriptive(rows, names):
    scored = [r for r in rows if r['optimum'] is not None]

    def contrast(b):
        d = [r['arms']['candidate']['value'] - r['arms'][b]['value'] for r in scored]
        return {'mean': round(statistics.fmean(d), 4) if d else None,
                'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)]}
    return {'scored': len(scored),
            'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in scored) for n in names},
            'mean_gap_to_optimum': {n: round(statistics.fmean(r['optimum'] - r['arms'][n]['value'] for r in scored), 4)
                                    if scored else None for n in names},
            'candidate_minus': {b: contrast(b) for b in names if b != 'candidate'}}


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
            for n, desc in all_arms.items():
                res[n], sel = run_arm(t, desc, seed)
                offered.append((n, sel))
            for n, s in MIP_BUDGETS.items():
                res[n], sel = mip(t, s)
                offered.append((n, sel))
            ref, opt = reference(t, offered, registry, PILOT_REF_S)
            r = {'task_id': t.task_id, 'stratum': t.family, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'B {t.task_id[-4:]}: ' + json.dumps({k: a['value'] for k, a in res.items()}) +
                f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.1f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every pilot host has been run')
    names = ['candidate', *DSL, *CAUSAL, *MIP_BUDGETS]
    contrasts, powers = {}, {}
    contrasts['readiness'], powers['readiness'] = analyse(rows, names, list(DSL))
    for k in CAUSAL:
        contrasts[k], powers[k] = analyse(rows, names, [k])
    out_ = {'contrasts': contrasts, 'descriptive': descriptive(rows, names)}
    R11.dump(out / 'pilot_summary.json', out_)
    for k, pw in powers.items():
        if pw is not None:
            R11.dump(out / f'power_analysis_centred_{k}.json', pw)
    for k, a in contrasts.items():
        log(f'Part B {k}: {a["verdict"]}; comparator {a["comparator"]}; mean {a.get("mean_difference")}; '
            f'cpu ratio {a["cpu_ratio_candidate_to_comparator"]}')
    return out_


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
    log(f'pinned to CPU {cpu}')
    from genesis.verification.tools import tool
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim')))
    all_arms = arms()
    registry = R47.registry()
    log(f'arms {sorted(all_arms)}; registry {len(registry["patterns"])} patterns from {registry["package_sha256"][:16]}')
    excluded, scan, _ = R24.exposure(log)
    settings, scan = calibration_hosts(out, log, excluded, scan)
    record = part_a(out, log, all_arms, registry, settings)
    cal_ids = RD.identities([t for _, _, ts in settings for t in ts])
    b = part_b(out, log, all_arms, registry, record, set(excluded) | cal_ids) if record['selected'] else None
    verdicts = {k: a['verdict'] for k, a in b['contrasts'].items()} if b else {'all': 'NO_ELIGIBLE_SETTING'}
    R11.dump(out / 'summary.json', {'schema': 'genesis-b20r50-e1b-c4-readiness-v1', 'rule': RULE['name'],
                                    'selected': record['selected'], 'pilot': b, 'verdicts': verdicts,
                                    'descriptors': {n: d['descriptor_id'] for n, d in all_arms.items()},
                                    'registry_package_sha256': registry['package_sha256'],
                                    'checker_identity': VT.checker_identity(), 'exposure_scan': scan,
                                    'code_identity': code_identity(ROOT)['sha256'],
                                    'status': 'DEV readiness; DRAFT rule; licenses nothing'})
    log(f'verdicts {verdicts}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
