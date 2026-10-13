#!/usr/bin/env python3
"""B20_R12 (redo on the canonical line): E1 under the user's decisions of 13 Oct 2026.

    b20r12_e1_redo.py OUT_DIR

The first B20_R12 run was lost with its workspace; its code was recovered and is reused here.
Decisions (the user, 13 Oct 2026, recorded before this script ran):
  * cost: conventional baselines get the candidate's search budget (dsl-time-matched-v1: the fixed
    program is restarted until 0.5 CPU s of search are spent). The plan's cost rule (max_ratio 3.0)
    is unchanged;
  * comparator: the DRAFT's rule, "the strongest fixed baseline on the SELECT panel", executed by the
    custodian (custodian.select_comparator) over the time-matched baselines;
  * power: the centred-headroom model (B19), n >= 10 per stratum; needs an independent statistician;
  * family: E1's hosts come from the study calibration 'e1' made under the separately versioned rule
    e1-hard-v1 (scripts/b20r12_e1_calibration.py), not from the domain adoption, which is unchanged.

Part A: DEV re-pilot (rules fixed here, before running):
  * 30 fresh DEV hosts from the E1 study calibration, seed 20261921, excluding every E1 host the
    builder can name (b20r13 e1_exposure: B19 pilot, B20_R11 pilot and rehearsal, the lost B20_R12
    pilot; regenerated as tasks and checked against those identities), every triangle-free host
    recorded in the B20_R13, RX3, RX3b, RX4 and RX5 evidence, and the E1 calibration's own DEV hosts
    (regenerated and checked against the record's digests);
  * arms through candidates.run(isolation='runc'), one profile (2 CPU s, 1000 queries, 2048 MiB,
    10 s wall): the candidate (cross_2, 0.5 s search), the three time-matched baselines (0.5 s
    search each) and, as a diagnostic only, the three plain baselines;
  * reference optimum: the domain adapter, 30 s per host; hosts without one are reported, not scored;
  * comparator for the pilot: the strongest time-matched baseline by total on these hosts;
  * analysis: the B19 DRAFT plan unchanged (MUE 0.5, design effect 1.0, alpha 0.05, Holm over 3,
    strata = family setting) as a dry run; power: centred model from these rows (>= 10 per stratum,
    1000 simulations);
  * verdict:
      READY_FOR_REVIEW   mean >= MUE, CPU ratio <= max_ratio, and the power model CHOSE a size;
      UNDERPOWERED       mean >= MUE and ratio within bound, but no size reaches the power target;
      COST_RULE_FAILS    mean >= MUE but the ratio exceeds max_ratio;
      EFFECT_BELOW_MUE   otherwise.
    The mean is over all scored hosts (strata pooled), as in B20_R11; the plan's own estimand is
    reported beside it.

Part B: handoff/e1 regenerated (v2; B20_R11's files replaced, B19 files kept) with an amended DRAFT
naming the E1 calibration (status DRAFT, not frozen), and a same-operator REHEARSAL with fixture
keys: custodian SELECT comparator on 30 private hosts -> selection recorded in the campaign. Only if
Part A says READY_FOR_REVIEW: v4 request (builder-frozen copy labelled REHEARSAL) -> register ->
evaluate on the power-chosen panel -> judge. Otherwise the DRAFT cannot pass the decision-record
check (no chosen size) and the rehearsal stops after SELECT; this is reported, nothing is relaxed.
The rehearsal custodian's exposure manifest lists every host named above. Nothing here licenses
a claim.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS, Unsupported  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.kernel.analysis import analyze, plan_core  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402

DOMAIN = R11.DOMAIN
STUDY = 'e1'
PILOT_SEED, PILOT_TASKS = 20261921, 30
SELECT_TASKS, REHEARSAL_SEED, CAMPAIGN_SEED = 30, 20261931, 20261941
PROFILE = R11.PROFILE
SEARCH_S = 0.5
NAMED_EVIDENCE = ('graph_headroom_b20r13', 'capability_pilot_b20rx3', 'capability_replication_b20rx3b',
                  'e1_family_calibration_b20rx4', 'proposal_pilot_b20rx5')
KEEP_IN_PACKAGE = ('README.md', 'decision_record_DRAFT.json', 'b19_power_analysis.json',
                   'b19_power_analysis_b16_model.json', 'b19_pilot_rows.json', 'b19_summary.json')


def arms():
    cand, plain = R11.descriptors()
    tm = {f'{n}_tm': C.build_descriptor('dsl-time-matched-v1', DOMAIN, {'program': p.model_dump(mode='json'),
                                                                        'cpu_seconds': SEARCH_S}, **PROFILE)
          for n, p in sorted(baseline_programs().items())}
    return cand, tm, plain


# ------------------------------------------------------------------ exposure

def _walk(o, acc):
    if isinstance(o, dict):
        if {'task_id', 'domain', 'n', 'edges'} <= set(o):
            acc.append(o)
            return
        for v in o.values():
            _walk(v, acc)
    elif isinstance(o, list):
        for v in o:
            _walk(v, acc)


def evidence_hosts():
    """Every triangle-free host task recorded in the named DEV evidence (all exposed)."""
    acc = []
    for d in NAMED_EVIDENCE:
        for f in sorted((ROOT / 'evidence' / d).iterdir()):
            if f.suffix == '.json':
                _walk(json.loads(f.read_text()), acc)
            elif f.suffix == '.jsonl':
                for line in f.read_text().splitlines():
                    _walk(json.loads(line), acc)
    out = {}
    for t in acc:
        if t['domain'] == DOMAIN:
            out[t['task_id']] = GraphTask.model_validate_json(canonical(t))
    return list(out.values())


def calibration_hosts(record):
    """The E1 calibration's DEV hosts, regenerated exactly as calibrate drew them and checked
    against the digests the record keeps."""
    a, seen, out = ADAPTERS[DOMAIN], set(), []
    for i, s in enumerate(record['settings']):
        tasks, seen, _ = a.generate(record['seed'] + 1000 * i, record['tasks_per_setting'], 'DEV', s['family'],
                                    s['params'], excluded=seen)
        out += tasks
    if [digest(t.model_dump(mode='json')) for t in out] != record['task_sha256s']:
        raise RuntimeError('the E1 calibration hosts do not regenerate to the recorded digests')
    return out


def identities(tasks):
    a, out = ADAPTERS[DOMAIN], set()
    for t in tasks:
        ident = a.exposure_identity(t)
        if isinstance(ident, dict):
            out.add(ident['canonical'])
    return out


def prior_e1_hosts():
    """The earlier E1 hosts as tasks (b20r13 e1_exposure keeps only their identities): the B19 pilot,
    the B20_R11 pilot and rehearsal, and the lost B20_R12 pilot (deterministic from its seed)."""
    import b20r13_graph_headroom_pilot as P13
    domain_record = CAL.load(DOMAIN, ROOT)
    b19, seen = CAL.calibrated_panel(domain_record, P13.B19_SEED, P13.B19_TASKS, 'DEV')
    r11, seen = CAL.calibrated_panel(domain_record, P13.R11_PILOT_SEED, P13.R11_PILOT_TASKS, 'DEV', excluded=seen)
    reh = [GraphTask.model_validate_json(canonical(t)) for t in
           json.loads((ROOT / 'handoff/e1/exposure_hosts_to_exclude.json').read_text())['b20r11_rehearsal']]
    seen = set(seen) | identities(reh)
    r12, _ = CAL.calibrated_panel(domain_record, P13.R12_PILOT_SEED, P13.R12_PILOT_TASKS, 'DEV', excluded=seen)
    return b19 + r11 + reh + r12


def exposure(record):
    import b20r13_graph_headroom_pilot as P13
    named = prior_e1_hosts() + evidence_hosts() + calibration_hosts(record)
    excluded = identities(named)
    if not set(P13.e1_exposure()) <= excluded:
        raise RuntimeError('the prior E1 hosts do not regenerate to the identities b20r13 excludes')
    return excluded, named


# ------------------------------------------------------------------ part A

def part_a(out, log, record, excluded):
    tasks, _ = CAL.calibrated_panel(record, PILOT_SEED, PILOT_TASKS, 'DEV', excluded=excluded)
    cand, tm, plain = arms()
    all_arms = {'candidate': cand, **tm, **plain}
    runs, optima = {}, {}
    for t in tasks:
        ref = ADAPTERS[DOMAIN].reference(t, seconds=30)
        optima[t.task_id] = None if isinstance(ref, Unsupported) else ref['value']
        seed = int(digest({'seed': PILOT_SEED, 'task': t.task_id})[:12], 16)
        for name, desc in all_arms.items():
            r = C.run(t, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
            ok = r['status'] == 'SUCCESS'
            runs[(t.task_id, name)] = {'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED',
                                       'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0,
                                       'status': r['status']}
        log(f'{t.task_id}: optimum {optima[t.task_id]}, ' + ', '.join(f'{n} {runs[(t.task_id, n)]["value"]}'
                                                                     for n in all_arms))
    totals = {n: sum(runs[(t.task_id, n)]['value'] for t in tasks) for n in all_arms}
    comparator = max(tm, key=lambda n: (totals[n], n))
    rows = [{'task_id': t.task_id, 'stratum': t.family, 'status': 'SCORED', 'split': t.split,
             'optimum': optima[t.task_id],
             'candidate': {k: runs[(t.task_id, 'candidate')][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: runs[(t.task_id, comparator)][k] for k in ('value', 'run', 'cpu_ns')}}
            for t in tasks if optima[t.task_id] is not None]
    plan = dict(R11.draft_record()['analysis_plan_core'], decision_record_sha256='0' * 64)
    result = analyze(rows, plan)
    power = required_sample(rows, plan, sims=1000, min_tasks_per_stratum=10, headroom='centred')
    chosen = (power.get('chosen') or {}).get('tasks_per_stratum')
    agreement = approximation_check(rows, plan, chosen, sims=40, headroom='centred') if chosen else None
    diffs = [r['candidate']['value'] - r['baseline']['value'] for r in rows]
    mean = sum(diffs) / len(diffs)
    cpu = {n: sum(runs[(t.task_id, n)]['cpu_ns'] for t in tasks) for n in all_arms}
    ratio = cpu['candidate'] / cpu[comparator] if cpu[comparator] else None
    mue, max_ratio = plan['minimum_useful_effect'], plan['cost']['max_ratio']
    if mean < mue:
        verdict = 'EFFECT_BELOW_MUE'
    elif ratio is None or ratio > max_ratio:
        verdict = 'COST_RULE_FAILS'
    elif not chosen:
        verdict = 'UNDERPOWERED'
    else:
        verdict = 'READY_FOR_REVIEW'
    strata = {}
    for r in rows:
        strata.setdefault(r['stratum'], []).append(r['candidate']['value'] - r['baseline']['value'])
    summary = {'tasks': len(tasks), 'scored': len(rows), 'unsupported_reference': len(tasks) - len(rows),
               'comparator': comparator, 'totals': totals, 'mean_difference': round(mean, 4),
               'stratum_mean_differences': {s: round(sum(v) / len(v), 4) for s, v in sorted(strata.items())},
               'stratum_tasks': {s: len(v) for s, v in sorted(strata.items())},
               'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
               'optimum_hits': {n: sum(runs[(t.task_id, n)]['value'] == optima[t.task_id] for t in tasks
                                       if optima[t.task_id] is not None) for n in all_arms},
               'failures': {n: sum(runs[(t.task_id, n)]['run'] == 'FAILED' for t in tasks) for n in all_arms},
               'cpu_ns_by_arm': cpu, 'cpu_ratio_candidate_to_comparator': round(ratio, 4) if ratio else None,
               'plan_minimum_useful_effect': mue, 'plan_max_cost_ratio': max_ratio,
               'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value',
                                                                  'checks', 'cost_ratio')},
               'power_centred': {k: power.get(k) for k in ('status', 'chosen', 'power_at_minimum_useful_effect',
                                                            'false_positive_rate_at_zero_effect')},
               'approximation_agreement': agreement, 'verdict': verdict,
               'calibration': {'study': STUDY, 'record_sha256': digest(record), 'rule': record['rule']['name'],
                               'selected': record['selected']},
               'descriptors': {n: d['descriptor_id'] for n, d in all_arms.items()}, 'profile': PROFILE,
               'search_seconds': SEARCH_S, 'pilot_seed': PILOT_SEED,
               'status': 'DEV re-pilot under the decided design; no sealed task; no claim'}
    R11.dump(out / 'pilot_rows.json', rows)
    R11.dump(out / 'pilot_summary.json', summary)
    R11.dump(out / 'power_analysis_centred.json', power)
    log(f'pilot: mean {mean:+.3f} vs {comparator}, W/T/L {summary["wins_ties_losses"]}, cpu ratio '
        f'{summary["cpu_ratio_candidate_to_comparator"]}, power {power.get("status")} n={chosen}, '
        f'DRAFT dry run {result.get("decision")} -> {verdict}')
    return summary, power, tasks


# ------------------------------------------------------------------ part B

def amended_draft(power, record):
    d = R11.draft_record()
    plan = dict(d['analysis_plan_core'])
    ident = R11.descriptors()[0]['descriptor_id']
    cal = (f"the E1 study calibration (rule e1-hard-v1, record SHA-256 {digest(record)[:16]}, settings "
           + ', '.join(f"{s['family']} {s['params']}" for s in record['selected']) + ')')
    return DR.build(
        plan_core_dict=plan_core(dict(plan, decision_record_sha256='0' * 64)), power=power,
        exact_claim=('The frozen representation-and-repair candidate (descriptor ' + ident[:16] + ', cut representation '
                     'cross_2, 0.5 CPU s of search) scores more edges than the strongest time-matched fixed DSL baseline '
                     '(0.5 CPU s of restarts), selected by the custodian on its private SELECT panel, on a custodian-held '
                     'CONFIRM panel of triangle_free_host_v1 hosts drawn from ' + cal + ', by at least the minimum '
                     'useful effect, under the registered analysis.'),
        capability_changes=('Candidate: B18 W10 representation grammar (cross_2) with greedy repair. The custodian runs '
                            'every arm in the OCI sandbox through the trusted runner (B20_R5); no change to trusted '
                            'checking.'),
        permissible_information=d['permissible_information'],
        baselines={'comparator': ('the strongest time-matched fixed DSL baseline (dsl-time-matched-v1, 0.5 CPU s of '
                                  'restarts) on the custodian SELECT panel (custodian.select_comparator)'),
                   'all_fixed_baselines': sorted(f'{n} (time-matched)' for n in baseline_programs()),
                   'not_a_competitor': 'the SAT/DRAT or LP reference optimum is evaluator ground truth'},
        total_budget={'profile': PROFILE, 'search_seconds_per_arm': SEARCH_S, 'arms': 2,
                      'reference_seconds_per_task': 600, 'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'discovery_cost': 'B18 W10 representation search, recorded in evidence/invention_b18',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every DEV '
                         'panel named in B16-B20 evidence and every host in handoff/e1/exposure_hosts_all.json; '
                         'a SELECT or CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' A comparator not selected by the custodian on its SELECT panel. '
                            'A panel not drawn from the E1 study calibration named in the claim.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for triangle_free_host_v1 hosts from the E1 '
                            'calibrated settings on that panel only, against time-matched fixed baselines. Not '
                            'better-improver, transfer, novelty, or any statement about the domain-adopted family.'),
        status='DRAFT')


def part_b(out, log, record, excluded, power, ready, named_tasks, pilot_tasks):
    from genesis.campaign import Campaign
    from genesis.cli import (descriptor_request_bundle, export_replication, freeze_candidate_descriptor,
                             record_comparator_selection)
    from genesis.models import Config
    from genesis.custodian import evaluate, register, registration_log, select_comparator, verify
    from genesis import custody_records as CR
    from genesis.judge import recompute
    pkg = ROOT / 'handoff' / 'e1'
    work = out / 'work'
    if work.exists():
        shutil.rmtree(work)
    camp_root = work / 'campaign'
    cfg = Config(domain=DOMAIN, seed=CAMPAIGN_SEED, generations=1, tasks_per_panel=4, proposals_per_epoch=2,
                 research_trials=8)
    t0 = time.monotonic()
    Campaign.initialize(camp_root, cfg)
    with Campaign(camp_root) as camp:
        camp.run()
    log(f'campaign frozen in {time.monotonic() - t0:.0f} s')
    cand, tm, _ = arms()
    reh = work / 'rehearsal'
    reh.mkdir(parents=True)
    reh.chmod(0o700)
    prereg, cust = R11.keyfile(reh, 'prereg_FIXTURE'), R11.keyfile(reh, 'custodian_FIXTURE')
    hosts_file = reh / 'builder_named_hosts.json'
    hosts_file.write_bytes(canonical([t.model_dump(mode='json') for t in named_tasks]))
    hosts_file.chmod(0o600)
    manifest = reh / 'exposure_manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1',
                                    'sources': [{'kind': 'json', 'path': hosts_file.name,
                                                 'label': 'builder-named E1 and DEV hosts'}]}))
    manifest.chmod(0o600)
    draft2 = amended_draft(power, record)
    with Campaign(camp_root) as camp:
        cv = freeze_candidate_descriptor(camp, cand, origin=('B18 W10 representation grammar (cross_2) with greedy repair; '
                                                             'B19 E1 candidate (evidence/readiness_b19/e1)'))
        export_replication(camp_root, camp_root / 'exports' / 'campaign_export.zip', store=camp.store)
    t0 = time.monotonic()
    sel = select_comparator(reh, camp_root / 'exports' / 'campaign_export.zip', tm, cust[0],
                            'BUILDER_REHEARSAL_NOT_INDEPENDENT', exposure_manifest=manifest, task_count=SELECT_TASKS,
                            study=STUDY)
    sp = verify(sel, cust[1])
    select_tasks = json.loads((reh / 'comparator_selections' / f'{digest(sel)}.json').read_text())['tasks']
    log(f'SELECT panel: {sp["totals"]} -> comparator {sp["selected"]} ({time.monotonic() - t0:.0f} s)')
    with Campaign(camp_root) as camp:
        record_comparator_selection(camp, sel)
    rehearsal_tasks, outcome = [], {'comparator': sp['selected'], 'select_totals': sp['totals']}
    if ready:
        total = power['chosen']['total_tasks']
        with Campaign(camp_root) as camp:
            rehearsal = copy.deepcopy(draft2)
            rehearsal['exact_claim'] = 'REHEARSAL (same operator, fixture keys, not a reviewed decision): ' + draft2['exact_claim']
            frozen, h = DR.freeze(rehearsal)
            plan = dict(draft2['analysis_plan_core'], decision_record_sha256=h)
            path = descriptor_request_bundle(camp, total, analysis=plan, claim_id='e1-rehearsal-b20r12',
                                             statement='REHEARSAL: ' + draft2['exact_claim'],
                                             scope=f'rehearsal panel of {total} triangle_free_host_v1 hosts (same operator)')
            request = json.loads(path.read_text())
        export = camp_root / 'exports' / 'campaign_export.zip'
        select_ids = identities([GraphTask.model_validate_json(canonical(t)) for t in select_tasks])
        tasks, _ = CAL.calibrated_panel(record, REHEARSAL_SEED, total, 'CONFIRM', excluded=set(excluded) | select_ids)
        rehearsal_tasks = [t.model_dump(mode='json') for t in tasks]
        pool = reh / 'rehearsal_pool.json'
        pool.write_bytes(canonical(rehearsal_tasks))
        t0 = time.monotonic()
        anchor = register(reh, request, prereg[0], 'BUILDER_REHEARSAL_NOT_INDEPENDENT', exposure_manifest=manifest,
                          campaign_export=export, pool=pool, decision_record=frozen)
        receipt = evaluate(reh, digest(request), pool, cust[0], 'BUILDER_REHEARSAL_NOT_INDEPENDENT')
        p = verify(receipt, cust[1])
        lg, problems = CR.check_log(registration_log(reh, cust[0]), cust[1], verify)
        judged = recompute(reh / 'evaluations' / digest(request), request, receipt, registration_log_entries=lg['entries'])
        log(f'rehearsal: {p["outcome"]} (W/L/T {p["wins"]}/{p["losses"]}/{p["ties"]}), estimate '
            f'{p["analysis_result"].get("estimate")}, cost ratio {p["analysis_result"].get("cost_ratio")}, judge agrees '
            f'{judged["agrees"]} ({time.monotonic() - t0:.0f} s)')
        R11.dump(out / 'rehearsal_summary.json', {
            'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: not independent, not a CONFIRM result, licenses nothing',
            'comparator_selection': sp, 'request_sha256': digest(request), 'receipt_payload': p,
            'anchor_payload': anchor['payload'],
            'judge': {k: judged.get(k) for k in ('agrees', 'problems', 'witnesses_rechecked', 'recomputed_outcome')},
            'resource_account': judged.get('resource_account'), 'fairness': judged.get('fairness'),
            'log_problems': problems, 'panel_tasks': [t.task_id for t in tasks]})
        R11.dump(out / 'rehearsal_receipt.json', receipt)
        outcome.update({'rehearsal_outcome': p['outcome'], 'panel_size': total, 'judge_agrees': judged['agrees']})
    else:
        outcome['rehearsal'] = ('stopped after SELECT: the pilot verdict is not READY_FOR_REVIEW, so the DRAFT has no '
                                'chosen sample size and cannot pass the decision-record check')
        outcome['decision_record_problems'] = DR.problems(DR.freeze(draft2)[0], require_frozen=True)
        R11.dump(out / 'rehearsal_summary.json', {
            'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: not independent, licenses nothing',
            'comparator_selection': sp, **outcome})
        log(outcome['rehearsal'])
    # Regenerate the package (no private material; keys and the custodian store stay in OUT_DIR/work, removed).
    prior = json.loads((pkg / 'exposure_hosts_to_exclude.json').read_text())
    for f in pkg.glob('*'):
        if f.name not in KEEP_IN_PACKAGE:
            f.unlink()
    shutil.copy(camp_root / 'exports' / 'campaign_export.zip', pkg / 'campaign_export.zip')
    R11.dump(pkg / 'candidate_descriptor.json', cand)
    R11.dump(pkg / 'time_matched_baselines.json', tm)
    R11.dump(pkg / 'decision_record_DRAFT_v2.json', draft2)
    R11.dump(pkg / 'power_analysis_centred_b20r12.json', power)
    R11.dump(pkg / 'pilot_summary_b20r12.json', json.loads((out / 'pilot_summary.json').read_text()))
    R11.dump(pkg / 'exposure_hosts_to_exclude.json', {
        'note': ('every E1 host the builder generated, by seed or as tasks; a real custodian adds them, '
                 'exposure_hosts_all.json and every DEV panel named in B16-B20 evidence to its exposure manifest'),
        'b19_pilot': prior['b19_pilot'], 'b20r11_pilot': prior['b20r11_pilot'],
        'b20r11_rehearsal': prior['b20r11_rehearsal'],
        'b20r12_lost_run': {'pilot': {'seed': 20261204, 'tasks': 30, 'calibration': 'domain adoption'},
                            'select_rehearsal': 'drawn from os.urandom in the lost run; cannot be named'},
        'e1_calibration': {'record': 'evidence/dev_calibration_e1_b20r12/calibration_triangle_free_host_v1_e1.json',
                           'seed': record['seed'], 'tasks_per_setting': record['tasks_per_setting']},
        'named_dev_evidence': list(NAMED_EVIDENCE),
        'b20r12_pilot': {'seed': PILOT_SEED, 'tasks': PILOT_TASKS, 'calibration': f'study {STUDY}'},
        'b20r12_select_rehearsal': select_tasks,
        'b20r12_rehearsal': rehearsal_tasks})
    everything = {t.task_id: t.model_dump(mode='json') for t in named_tasks}
    for t in pilot_tasks:
        everything[t.task_id] = t.model_dump(mode='json')
    for t in select_tasks + rehearsal_tasks:
        everything[t['task_id']] = t
    (pkg / 'exposure_hosts_all.json').write_bytes(canonical(sorted(everything.values(), key=lambda t: t['task_id'])))
    shutil.rmtree(work)
    return {'campaign_candidate_version': cv, 'hosts_named_in_package': len(everything), **outcome}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    record = CAL.load(DOMAIN, ROOT, study=STUDY)
    excluded, named = exposure(record)
    log(f'E1 study calibration {digest(record)[:12]} ({record["rule"]["name"]}) selected {record["selected"]}; '
        f'{len(excluded)} host identities excluded')
    summary, power, pilot = part_a(out, log, record, excluded)
    excluded = set(excluded) | identities(pilot)
    b = part_b(out, log, record, excluded, power, summary['verdict'] == 'READY_FOR_REVIEW', named, pilot)
    R11.dump(out / 'readiness.json', {'pilot': summary, 'package': b, 'code_identity': code_identity(ROOT)['sha256']})
    log('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
