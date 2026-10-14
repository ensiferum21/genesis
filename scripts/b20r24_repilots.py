#!/usr/bin/env python3
"""B20_R24: E1 and E1b re-pilots on the e1-hard-v2 family, and a same-operator rehearsal where ready.

    b20r24_repilots.py OUT_DIR             run (pilot rows are resumable) and write the results
    b20r24_repilots.py OUT_DIR --summary   summarise existing pilot rows only (no rehearsal)

The user's decision (14 Oct 2026): a versioned rule e1-hard-v2 picks the settings for both E1 and E1b
(scripts/b20r24_e1_hard_v2_calibration.py), then both are re-piloted on fresh hosts. This script was
written and committed before the calibration produced any result.

Fixed before running.

Studies and arms (all through candidates.run(isolation='runc'); one profile per study; failures score 0):
  E1   study 'e1-v2', triangle_free_host_v1. Candidate: represent-and-repair-v1 cross_2, 0.5 CPU s (the
       B19/B20_R12 candidate). Baselines: the three fixed DSL programs as dsl-time-matched-v1, 0.5 CPU s.
       Profile {cpu 2 s, 2048 MiB, wall 10 s, 1000 queries} (B20_R11/R12).
  E1b  study 'e1b', each domain with an adopted calibration. Candidate: construct-pipeline-v1
       {init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0, seed 0}. Baselines: the three
       time-matched programs, 2.0 CPU s. Diagnostic on triangle-free hosts only: cross_2 at 2.0 CPU s.
       Profile {cpu 4 s, 2048 MiB, wall 20 s, 1000 queries} (B20_R23).
  A study or domain without an adopted calibration is NOT_RUN (no eligible setting); nothing is relaxed.

Hosts: 30 fresh DEV hosts per study and domain, drawn round-robin from the adopted calibration's selected
settings (calibration.calibrated_panel), seeds E1 20262901, E1b triangle-free 20262911, E1b C4 20262921.
Each excludes the exposure identities of every graph host named under evidence/ and handoff/, the
regenerated E1 hosts (b20r12_e1_redo.exposure), the e1-hard-v1 and e1-hard-v2 calibration hosts
(regenerated and checked against their records' digests), and the hosts of the pilots drawn before it.
Per-host seed digest({'pilot': 'b20r24', 'study': study, 'task': id})[:12].

Reference: obstruction.certify seeded with the best arm witness, 120 s per host; an optimum only if
lower == upper. A study/domain is scored only if every stratum has at least 75% of its hosts certified
(rounded up); otherwise UNSETTLED_REFERENCE.

Comparator: the strongest time-matched baseline by total over the pilot hosts.
Analysis: the B19 DRAFT plan core (MUE 0.5, design effect 1.0, alpha 0.05, Holm over 3, strata = family
setting, max cost ratio 3.0), with the multiplicity family_id naming the domain; a dry run; power:
required_sample(..., sims=1000, min_tasks_per_stratum=10, headroom='centred').
Verdict per study and domain:
  UNSETTLED_REFERENCE  a stratum with fewer than 75% certified hosts
  EFFECT_BELOW_MUE     mean difference (strata pooled) < 0.5
  COST_RULE_FAILS      cgroup CPU ratio candidate / comparator > 3.0
  UNDERPOWERED         the centred model chooses no size in its grid
  READY_FOR_REVIEW     otherwise

Rehearsal (only for a study/domain whose verdict is READY_FOR_REVIEW): as in B20_R12 Part B, by the same
operator with fixture keys, labelled REHEARSAL, licensing nothing. A real frozen DEV campaign (1
generation) with the candidate frozen; the custodian's select_comparator(study=...) on 30 private SELECT
hosts drawn from the study calibration; the selection recorded in the campaign; a builder-frozen copy of
the DRAFT decision record; the v4 request for the power-chosen panel size; register, evaluate on a
CONFIRM pool drawn from the study calibration (seed 20262931 + 10 k, excluding every host above and the
SELECT hosts), judge.recompute, and the registration log checked. Keys, the custodian store and the
campaign are deleted afterwards; the hosts are kept in the results so a real custodian excludes them.
"""
import copy
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.kernel.analysis import analyze, plan_core  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r12_e1_redo as R12  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402

TF, C4 = RD.TF, RD.C4
PILOT_TASKS, SELECT_TASKS, CERTIFY_S = 30, 30, 120
E1_PROFILE, E1B_PROFILE = R11.PROFILE, RD.PROFILE
PILOTS = [  # (key, study, domain, seed)
    ('e1', 'e1-v2', TF, 20262901),
    ('e1b_tf', 'e1b', TF, 20262911),
    ('e1b_c4', 'e1b', C4, 20262921),
]
REHEARSAL_SEED, CAMPAIGN_SEED = 20262931, 20262941


def arms(key, domain):
    if key == 'e1':
        cand = C.build_descriptor('represent-and-repair-v1', domain, {'representation': 'cross_2', 'cpu_seconds': 0.5,
                                                                       'seed': 0}, **E1_PROFILE)
        search, profile = 0.5, E1_PROFILE
    else:
        cand = C.build_descriptor('construct-pipeline-v1', domain, RD.CANDIDATE, **E1B_PROFILE)
        search, profile = RD.SEARCH_S, E1B_PROFILE
    tm = {f'{n}_tm': C.build_descriptor('dsl-time-matched-v1', domain, {'program': p.model_dump(mode='json'),
                                                                        'cpu_seconds': search}, **profile)
          for n, p in sorted(baseline_programs().items())}
    diag = {}
    if key == 'e1b_tf':
        diag['cross_2_diag'] = C.build_descriptor('represent-and-repair-v1', domain,
                                                  {'representation': 'cross_2', 'cpu_seconds': search, 'seed': 0},
                                                  **profile)
    return cand, tm, diag


# ------------------------------------------------------------------ exposure

def calibration_tasks(record):
    a, seen, out = ADAPTERS[record['domain']], set(), []
    for i, g in enumerate(record['grid']):
        tasks, seen, _ = a.generate(record['seed'] + 1000 * i, record['tasks_per_setting'], 'DEV', g['family'],
                                    g['params'], excluded=seen)
        out += tasks
    if [digest(t.model_dump(mode='json')) for t in out] != record['task_sha256s']:
        raise RuntimeError(f'the {record["rule"].get("name")} calibration hosts do not regenerate to their digests')
    return out


def exposure(log):
    named, scan = RD.named_hosts()
    e1_excluded, e1_named = R12.exposure(CAL.load(TF, ROOT, study='e1'))
    cal = calibration_tasks(CAL.load(TF, ROOT, study='e1'))
    cfg = json.loads((ROOT / CAL.CONFIG).read_text())
    for study in ('e1-v2', 'e1b'):
        for domain in cfg.get('studies', {}).get(study, {}):
            cal += calibration_tasks(CAL.load(domain, ROOT, study=study))
    excluded = RD.identities(named) | set(e1_excluded) | RD.identities(cal)
    scan.update(e1_named_hosts=len(e1_named), calibration_hosts=len(cal), excluded_identities=len(excluded))
    log(f'exposure: {len(excluded)} identities ({scan["distinct_hosts"]} named hosts, {len(e1_named)} E1 hosts, '
        f'{len(cal)} calibration hosts)')
    return excluded, scan, named + e1_named + cal


# ------------------------------------------------------------------ pilots

def run_host(key, task, all_arms):
    seed = int(digest({'pilot': 'b20r24', 'study': key, 'task': task.task_id})[:12], 16)
    res, best = {}, None
    for name, desc in all_arms.items():
        r = C.run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
        ok = r['status'] == 'SUCCESS'
        res[name] = {'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED',
                     'status': r['status'], 'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0,
                     'meter': r.get('meter'), 'isolation': r.get('isolation')}
        if ok and (best is None or r['result']['value'] > best[0]):
            best = (r['result']['value'], [tuple(e) for e in r['result']['selected']], name)
    from genesis.discovery import obstruction as O
    rec = O.certify(task, best[1] if best else [], seconds=CERTIFY_S)
    cert = {'seeded_from': best and best[2], 'seed_value': best and best[0], 'lower': rec['lower'],
            'upper': rec['upper'], 'upper_method': rec['upper_evidence']['method'], 'status': rec['status'],
            'wall_s': rec['wall_s']}
    return {'pilot': key, 'task_id': task.task_id, 'stratum': task.family, 'split': task.split, 'arms': res,
            'certify': cert, 'optimum': rec['lower'] if rec['lower'] == rec['upper'] else None}


def plan(domain):
    p = dict(R11.draft_record()['analysis_plan_core'], decision_record_sha256='0' * 64)
    p['multiplicity'] = dict(p['multiplicity'], family_id=f'sealed_evaluation:{domain}')
    return p


def analyse(key, domain, rows, names):
    tm = [n for n in names if n.endswith('_tm')]
    totals = {n: sum(r['arms'][n]['value'] for r in rows) for n in names}
    comparator = max(tm, key=lambda n: (totals[n], n))
    strata = sorted({r['stratum'] for r in rows})
    certified = {s: [sum(r['optimum'] is not None for r in rows if r['stratum'] == s),
                     sum(r['stratum'] == s for r in rows)] for s in strata}
    cpu = {n: sum(r['arms'][n]['cpu_ns'] for r in rows) for n in names}
    ratio = cpu['candidate'] / cpu[comparator] if cpu[comparator] else None
    p = plan(domain)
    mue, max_ratio = p['minimum_useful_effect'], p['cost']['max_ratio']
    out = {'hosts': len(rows), 'certified_by_stratum': certified, 'comparator': comparator, 'totals': totals,
           'cpu_ns_by_arm': cpu, 'cpu_ratio_candidate_to_comparator': round(ratio, 4) if ratio else None,
           'failures': {n: sum(r['arms'][n]['run'] == 'FAILED' for r in rows) for n in names}}
    if any(c < math.ceil(0.75 * n) for c, n in certified.values()):
        return dict(out, verdict='UNSETTLED_REFERENCE'), None, None
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
        'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in scored) for n in names},
        'mean_gap_to_optimum': {n: round(statistics.fmean(r['optimum'] - r['arms'][n]['value'] for r in scored), 4)
                                for n in names},
        'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value', 'checks',
                                                           'cost_ratio')},
        'power_centred': {k: power.get(k) for k in ('status', 'chosen', 'power_at_minimum_useful_effect',
                                                     'false_positive_rate_at_zero_effect', 'pilot_strata', 'table')},
        'approximation_agreement': approximation_check(prow, p, chosen, sims=40, headroom='centred') if chosen else None,
        'verdict': verdict})
    if 'cross_2_diag' in names:
        d2 = [r['arms']['candidate']['value'] - r['arms']['cross_2_diag']['value'] for r in scored]
        out['diagnostic_candidate_minus_cross_2'] = {'mean': round(statistics.fmean(d2), 4), 'wins_ties_losses':
                                                     [sum(d > 0 for d in d2), sum(d == 0 for d in d2), sum(d < 0 for d in d2)]}
    return out, prow, power


def pilots(out, log, excluded):
    rows_path = out / 'rows.jsonl'
    done = {}
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r['pilot'], r['task_id'])] = r
    cfg = json.loads((ROOT / CAL.CONFIG).read_text()).get('studies', {})
    results, hosts, t0 = {}, {}, time.monotonic()
    for key, study, domain, seed in PILOTS:
        if domain not in cfg.get(study, {}):
            results[key] = {'study': study, 'domain': domain, 'verdict': 'NOT_RUN',
                            'reason': f'no adopted calibration for {domain} in study {study} (no eligible setting)'}
            log(f'{key}: NOT_RUN')
            continue
        record = CAL.load(domain, ROOT, study=study)
        tasks, _ = CAL.calibrated_panel(record, seed, PILOT_TASKS, 'DEV', excluded=excluded)
        excluded = set(excluded) | RD.identities(tasks)
        hosts[key] = [t.model_dump(mode='json') for t in tasks]
        cand, tm, diag = arms(key, domain)
        all_arms = {'candidate': cand, **tm, **diag}
        rows = []
        with rows_path.open('a') as fh:
            for t in tasks:
                r = done.get((key, t.task_id))
                if r is None:
                    r = run_host(key, t, all_arms)
                    fh.write(json.dumps(r, sort_keys=True) + '\n')
                    fh.flush()
                    log(f'{key} {t.task_id}: opt {r["optimum"]} (L{r["certify"]["lower"]}/U{r["certify"]["upper"]} '
                        f'{r["certify"]["wall_s"]:.0f}s) ' + ', '.join(f'{n} {a["value"]}' for n, a in r['arms'].items())
                        + f' [{time.monotonic() - t0:.0f}s]')
                rows.append(r)
        s, prow, power = analyse(key, domain, rows, list(all_arms))
        s.update(study=study, domain=domain, calibration={'record_sha256': digest(record), 'rule': record['rule']['name'],
                                                           'selected': record['selected']},
                 descriptors={n: d['descriptor_id'] for n, d in all_arms.items()}, seed=seed)
        results[key] = s
        if prow is not None:
            R11.dump(out / f'pilot_rows_{key}.json', prow)
            R11.dump(out / f'power_analysis_centred_{key}.json', power)
        log(f'{key}: {s["verdict"]}; comparator {s["comparator"]}; certified {s["certified_by_stratum"]}; mean '
            f'{s.get("mean_difference")} {s.get("stratum_mean_differences")}; W/T/L {s.get("wins_ties_losses")}; cpu '
            f'{s["cpu_ratio_candidate_to_comparator"]}; power {(s.get("power_centred") or {}).get("status")} '
            f'{(s.get("power_centred") or {}).get("chosen")}; dry run {(s.get("draft_plan_dry_run") or {}).get("decision")}')
    R11.dump(out / 'pilot_hosts.json', hosts)
    return results, excluded, hosts


# ------------------------------------------------------------------ rehearsal

def draft(key, study, domain, cand, power, record):
    d = R11.draft_record()
    settings = ', '.join(f"{s['family']} {s['params']}" for s in record['selected'])
    cal = f"the {study} study calibration (rule {record['rule']['name']}, record SHA-256 {digest(record)[:16]}, settings {settings})"
    if key == 'e1':
        what = ('The frozen representation-and-repair candidate (descriptor ' + cand['descriptor_id'][:16] + ', cut '
                'representation cross_2, 0.5 CPU s of search) scores more edges than the strongest time-matched fixed '
                'DSL baseline (0.5 CPU s of restarts)')
        changes = ('Candidate: B18 W10 representation grammar (cross_2) with greedy repair. The custodian runs every arm '
                   'in the OCI sandbox through the trusted runner; no change to trusted checking.')
        search = 0.5
    else:
        what = ('The frozen construction-pipeline candidate (descriptor ' + cand['descriptor_id'][:16] + ': '
                'construct-pipeline-v1, LP-ordered greedy with LP-perturbed restarts, 2.0 CPU s of search) scores more '
                'edges than the strongest time-matched fixed DSL baseline (2.0 CPU s of restarts)')
        changes = ('Candidate: builder-written LP-guided construction (discovery/construct.py, B20_RX3) as the data-only '
                   'kind construct-pipeline-v1 (B20_R23). The custodian runs every arm in the OCI sandbox through the '
                   'trusted runner; no change to trusted checking.')
        search = RD.SEARCH_S
    return DR.build(
        plan_core_dict=plan_core(plan(domain)), power=power,
        exact_claim=(what + ', selected by the custodian on its private SELECT panel, on a custodian-held CONFIRM '
                     'panel of ' + domain + ' hosts drawn from ' + cal + ', by at least the minimum useful effect, '
                     'under the registered analysis.'),
        capability_changes=changes, permissible_information=d['permissible_information'],
        baselines={'comparator': (f'the strongest time-matched fixed DSL baseline (dsl-time-matched-v1, {search} CPU s '
                                  'of restarts) on the custodian SELECT panel (custodian.select_comparator)'),
                   'all_fixed_baselines': sorted(f'{n} (time-matched)' for n in baseline_programs()),
                   'not_a_competitor': 'the SAT/DRAT or LP reference optimum is evaluator ground truth'},
        total_budget={'profile': cand['resource_profile'], 'search_seconds_per_arm': search, 'arms': 2,
                      'reference_seconds_per_task': CERTIFY_S,
                      'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every DEV '
                         'panel named in the evidence and every host the builder generated (B20_R24 results); a '
                         'SELECT or CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' A comparator not selected by the custodian on its SELECT panel. '
                            f'A panel not drawn from the {study} study calibration named in the claim.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for ' + domain + ' hosts from the ' + study +
                            ' calibrated settings on that panel only, against time-matched fixed DSL baselines. Not '
                            'better-improver, transfer, novelty, or any statement about other families.'),
        status='DRAFT')


def rehearsal(out, log, key, study, domain, power, excluded, named):
    from genesis import custody_records as CR
    from genesis.campaign import Campaign
    from genesis.cli import (descriptor_request_bundle, export_replication, freeze_candidate_descriptor,
                             record_comparator_selection)
    from genesis.custodian import evaluate, register, registration_log, select_comparator, verify
    from genesis.judge import recompute
    from genesis.models import Config
    record = CAL.load(domain, ROOT, study=study)
    cand, tm, _ = arms(key, domain)
    work = out / 'work' / key
    if work.exists():
        shutil.rmtree(work)
    camp_root = work / 'campaign'
    Campaign.initialize(camp_root, Config(domain=domain, seed=CAMPAIGN_SEED, generations=1, tasks_per_panel=4,
                                          proposals_per_epoch=2, research_trials=8))
    with Campaign(camp_root) as camp:
        camp.run()
        cv = freeze_candidate_descriptor(camp, cand, origin=f'B20_R24 {key} re-pilot candidate (REHEARSAL)')
        export_replication(camp_root, camp_root / 'exports' / 'campaign_export.zip', store=camp.store)
    reh = work / 'rehearsal'
    reh.mkdir(parents=True)
    reh.chmod(0o700)
    prereg, cust = R11.keyfile(reh, 'prereg_FIXTURE'), R11.keyfile(reh, 'custodian_FIXTURE')
    hosts_file = reh / 'builder_named_hosts.json'
    hosts_file.write_bytes(canonical([t.model_dump(mode='json') for t in named]))
    hosts_file.chmod(0o600)
    manifest = reh / 'exposure_manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': [
        {'kind': 'json', 'path': hosts_file.name, 'label': 'every host the builder named or generated'}]}))
    manifest.chmod(0o600)
    t0 = time.monotonic()
    sel = select_comparator(reh, camp_root / 'exports' / 'campaign_export.zip', tm, cust[0],
                            'BUILDER_REHEARSAL_NOT_INDEPENDENT', exposure_manifest=manifest, task_count=SELECT_TASKS,
                            study=study)
    sp = verify(sel, cust[1])
    select_tasks = json.loads((reh / 'comparator_selections' / f'{digest(sel)}.json').read_text())['tasks']
    log(f'{key}: SELECT panel {sp["totals"]} -> comparator {sp["selected"]} ({time.monotonic() - t0:.0f} s)')
    with Campaign(camp_root) as camp:
        record_comparator_selection(camp, sel)
    d2 = draft(key, study, domain, cand, power, record)
    total = power['chosen']['total_tasks']
    with Campaign(camp_root) as camp:
        reh_rec = copy.deepcopy(d2)
        reh_rec['exact_claim'] = 'REHEARSAL (same operator, fixture keys, not a reviewed decision): ' + d2['exact_claim']
        frozen, h = DR.freeze(reh_rec)
        p = dict(d2['analysis_plan_core'], decision_record_sha256=h)
        path = descriptor_request_bundle(camp, total, analysis=p, claim_id=f'{key}-rehearsal-b20r24',
                                         statement='REHEARSAL: ' + d2['exact_claim'],
                                         scope=f'rehearsal panel of {total} {domain} hosts (same operator)')
        request = json.loads(path.read_text())
    select_ids = RD.identities([GraphTask.model_validate_json(canonical(t)) for t in select_tasks])
    seed = REHEARSAL_SEED + 10 * [k for k, *_ in PILOTS].index(key)
    tasks, _ = CAL.calibrated_panel(record, seed, total, 'CONFIRM', excluded=set(excluded) | select_ids)
    pool = reh / 'rehearsal_pool.json'
    pool.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
    t0 = time.monotonic()
    anchor = register(reh, request, prereg[0], 'BUILDER_REHEARSAL_NOT_INDEPENDENT', exposure_manifest=manifest,
                      campaign_export=camp_root / 'exports' / 'campaign_export.zip', pool=pool, decision_record=frozen)
    receipt = evaluate(reh, digest(request), pool, cust[0], 'BUILDER_REHEARSAL_NOT_INDEPENDENT')
    rp = verify(receipt, cust[1])
    lg, problems = CR.check_log(registration_log(reh, cust[0]), cust[1], verify)
    judged = recompute(reh / 'evaluations' / digest(request), request, receipt, registration_log_entries=lg['entries'])
    log(f'{key}: rehearsal {rp["outcome"]} (W/L/T {rp["wins"]}/{rp["losses"]}/{rp["ties"]}), estimate '
        f'{rp["analysis_result"].get("estimate")}, cost ratio {rp["analysis_result"].get("cost_ratio")}, judge agrees '
        f'{judged["agrees"]} ({time.monotonic() - t0:.0f} s)')
    summary = {'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: not independent, not a CONFIRM result, licenses nothing',
               'campaign_candidate_version': cv, 'comparator_selection': sp, 'request_sha256': digest(request),
               'decision_record_draft': d2, 'decision_record_rehearsal_sha256': h, 'receipt_payload': rp,
               'anchor_payload': anchor['payload'],
               'judge': {k: judged.get(k) for k in ('agrees', 'problems', 'witnesses_rechecked', 'recomputed_outcome')},
               'resource_account': judged.get('resource_account'), 'fairness': judged.get('fairness'),
               'log_problems': problems, 'select_hosts': select_tasks,
               'confirm_hosts': [t.model_dump(mode='json') for t in tasks]}
    R11.dump(out / f'rehearsal_{key}.json', summary)
    R11.dump(out / f'rehearsal_receipt_{key}.json', receipt)
    shutil.copy(camp_root / 'exports' / 'campaign_export.zip', out / f'campaign_export_{key}.zip')
    R11.dump(out / f'decision_record_DRAFT_{key}.json', d2)
    shutil.rmtree(work)
    return {'outcome': rp['outcome'], 'judge_agrees': judged['agrees'], 'panel_size': total,
            'comparator': sp['selected']}, select_ids | RD.identities(tasks)


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    excluded, scan, named = exposure(log)
    results, excluded, hosts = pilots(out, log, excluded)
    rehearsals = {}
    if '--summary' not in argv:
        named = list(named) + [GraphTask.model_validate_json(canonical(t)) for ts in hosts.values() for t in ts]
        for key, study, domain, _ in PILOTS:
            if results[key]['verdict'] != 'READY_FOR_REVIEW':
                rehearsals[key] = f'not run: verdict {results[key]["verdict"]}'
                continue
            power = json.loads((out / f'power_analysis_centred_{key}.json').read_text())
            rehearsals[key], used = rehearsal(out, log, key, study, domain, power, excluded, named)
            excluded = set(excluded) | used
    summary = {'schema': 'genesis-b20r24-repilots-v1', 'pilots': results, 'rehearsals': rehearsals,
               'exposure_scan': scan, 'certify_seconds': CERTIFY_S, 'pilot_tasks': PILOT_TASKS,
               'verdicts': {k: r['verdict'] for k, r in results.items()},
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV re-pilots and same-operator rehearsals; no sealed task; licenses no claim'}
    R11.dump(out / 'summary.json', summary)
    log(f'verdicts {summary["verdicts"]}; rehearsals {json.dumps(rehearsals)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
