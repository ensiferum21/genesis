#!/usr/bin/env python3
"""B20_R25: E1b's causal follow-ups on the e1b family: a DEV re-pilot, then (where ready) a same-operator
rehearsal of the whole causal path through the custodian, the judge and the evidence kernel.

    b20r25_e1b_causal.py OUT_DIR             run (pilot rows are resumable) and write the results
    b20r25_e1b_causal.py OUT_DIR --summary   summarise existing pilot rows only (no rehearsal)

Why. The B20_R23 causal pilot (ablation +1.42, placebo +2.53, both READY_FOR_REVIEW) ran on builder-chosen
settings. B20_R24 fixed E1b's family by the user's decision (study e1b, rule e1-hard-v2, triangle-free), so
the follow-ups need a re-pilot there before any request (handoff/e1b/README.md). And no causal level has yet
been rehearsed end to end on a real study: B20_R15 tested the contracts on fixtures only.

Fixed before running (this file is committed before it runs).

Part A, DEV re-pilot.
  Hosts: 30 fresh DEV hosts from the e1b study calibration (round robin over its 3 settings), seed 20263101,
  excluding every host named under evidence/ and handoff/, the regenerated E1 hosts, and both calibrations'
  hosts (b20r24_repilots.exposure). Per-host seed digest({'pilot': 'b20r25', 'task': id})[:12].
  Arms, through candidates.run(isolation='runc') under the E1b profile {cpu 4 s, 2048 MiB, wall 20 s,
  1000 queries}: the E1b candidate (construct-pipeline-v1, lp_greedy, 2.0 CPU s), its registered ablation
  (init random_greedy) and its registered placebo (init lp_shuffled_greedy), each checked with
  replay_contracts.intervention_problems before any run. A failed run scores 0.
  Reference: obstruction.certify seeded with the best arm witness, 120 s per host; scored only if every
  stratum has at least 75% of its hosts certified (else UNSETTLED_REFERENCE).
  Analysis per contrast k in (ablation, placebo): the B19 DRAFT plan core with the multiplicity family_id
  'k:triangle_free_host_v1' (the family the follow-up registers in); a dry run; power
  required_sample(..., sims=1000, min_tasks_per_stratum=10, headroom='centred').
  Verdict per contrast: UNSETTLED_REFERENCE / EFFECT_BELOW_MUE (mean < 0.5) / COST_RULE_FAILS (CPU ratio
  candidate / intervened > 3.0) / UNDERPOWERED (no size chosen) / READY_FOR_REVIEW.

Part B, same-operator rehearsal (only if at least one contrast is READY_FOR_REVIEW; fixture keys; licenses
nothing). In one fresh frozen DEV campaign (seed 20263111) with the E1b candidate frozen:
  1. the custodian's select_comparator(study='e1b') on 30 private hosts; the selection recorded;
  2. the main sealed evaluation: the B20_R24 E1b DRAFT (handoff/e1b/decision_record_DRAFT.json), a
     builder-frozen REHEARSAL copy, the v4 request for its power-chosen size (30), register, evaluate on a
     CONFIRM pool from the e1b calibration (seed 20263121), judge.recompute;
  3. for each READY contrast, in the order ablation, placebo: a DRAFT built from Part A's power analysis,
     a builder-frozen REHEARSAL copy, cli.followup_request with the registered intervention as the
     baseline arm, register (the custodian re-checks the intervention), evaluate on a fresh CONFIRM pool
     (seed 20263131 + 10 j), judge.recompute;
  4. the evidence kernel over the campaign store with a FIXTURE role registry pinning the rehearsal's
     prereg and custodian keys: every anchor and receipt recorded (record_signed), one claim bound to all
     the requests (receipts.binding_from_requests), then promote(utility, CONFIRMED_SAME_DOMAIN),
     promote(causality, ABLATION_SUPPORTED) and, if a placebo ran, promote(causality, PLACEBO_CONTROLLED).
     Every level reached and every rejection (with its reasons) is reported as it comes. Promotions under a
     FIXTURE registry are rehearsal levels only.
  Every SELECT and CONFIRM pool excludes all hosts above and every earlier pool. Keys and the custodian
  store are deleted afterwards; hosts, receipts, requests and kernel results are kept.
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
from genesis.kernel import replay_contracts as RC  # noqa: E402
from genesis.kernel.analysis import analyze, plan_core  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as RP  # noqa: E402

TF, STUDY = RD.TF, 'e1b'
PILOT_SEED, PILOT_TASKS, CERTIFY_S = 20263101, 30, 120
CAMPAIGN_SEED, MAIN_SEED, FOLLOW_SEED, SELECT_TASKS = 20263111, 20263121, 20263131, 30
CONTRASTS = (('ablation', 'random_greedy'), ('placebo', 'lp_shuffled_greedy'))
CLAIM_ID = 'e1b-causal-rehearsal-b20r25'
HOSTS_PER_SOURCE = 400


def arms():
    cand = C.build_descriptor('construct-pipeline-v1', TF, RD.CANDIDATE, **RD.PROFILE)
    out = {'candidate': cand}
    for kind, init in CONTRASTS:
        d = C.build_descriptor('construct-pipeline-v1', TF, dict(RD.CANDIDATE, init=init), **RD.PROFILE)
        why, path = RC.intervention_problems(kind, cand, d)
        if why or path != ('init',):
            raise RuntimeError(f'{kind} is not the registered intervention: {why}')
        out[kind] = d
    return out


def plan(kind):
    p = dict(R11.draft_record()['analysis_plan_core'], decision_record_sha256='0' * 64)
    p['multiplicity'] = dict(p['multiplicity'], family_id=f'{kind}:{TF}')
    return p


# ------------------------------------------------------------------ part A

def run_host(task, all_arms):
    seed = int(digest({'pilot': 'b20r25', 'task': task.task_id})[:12], 16)
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
    return {'task_id': task.task_id, 'stratum': task.family, 'split': task.split, 'arms': res, 'certify': cert,
            'optimum': rec['lower'] if rec['lower'] == rec['upper'] else None}


def contrast(kind, rows):
    strata = sorted({r['stratum'] for r in rows})
    certified = {s: [sum(r['optimum'] is not None for r in rows if r['stratum'] == s),
                     sum(r['stratum'] == s for r in rows)] for s in strata}
    cpu = {n: sum(r['arms'][n]['cpu_ns'] for r in rows) for n in ('candidate', kind)}
    ratio = cpu['candidate'] / cpu[kind] if cpu[kind] else None
    p = plan(kind)
    mue, max_ratio = p['minimum_useful_effect'], p['cost']['max_ratio']
    out = {'certified_by_stratum': certified, 'cpu_ns': cpu,
           'cpu_ratio_candidate_to_intervened': round(ratio, 4) if ratio else None,
           'failures': {n: sum(r['arms'][n]['run'] == 'FAILED' for r in rows) for n in ('candidate', kind)}}
    if any(c < math.ceil(0.75 * n) for c, n in certified.values()):
        return dict(out, verdict='UNSETTLED_REFERENCE'), None, None
    scored = [r for r in rows if r['optimum'] is not None]
    prow = [{'task_id': r['task_id'], 'stratum': r['stratum'], 'status': 'SCORED', 'split': r['split'],
             'optimum': r['optimum'],
             'candidate': {k: r['arms']['candidate'][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: r['arms'][kind][k] for k in ('value', 'run', 'cpu_ns')}} for r in scored]
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
    out.update({'scored': len(prow), 'mean_difference': round(mean, 4),
                'stratum_mean_differences': {s: round(statistics.fmean(v), 4) for s, v in sorted(by.items())},
                'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
                'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value',
                                                                   'checks', 'cost_ratio')},
                'power_centred': {k: power.get(k) for k in ('status', 'chosen', 'power_at_minimum_useful_effect',
                                                             'false_positive_rate_at_zero_effect', 'pilot_strata',
                                                             'table')},
                'approximation_agreement': (approximation_check(prow, p, chosen, sims=40, headroom='centred')
                                            if chosen else None),
                'verdict': verdict})
    return out, prow, power


def part_a(out, log, excluded):
    record = CAL.load(TF, ROOT, study=STUDY)
    tasks, _ = CAL.calibrated_panel(record, PILOT_SEED, PILOT_TASKS, 'DEV', excluded=excluded)
    rows_path, done = out / 'rows.jsonl', {}
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[r['task_id']] = r
    all_arms, rows, t0 = arms(), [], time.monotonic()
    with rows_path.open('a') as fh:
        for t in tasks:
            r = done.get(t.task_id)
            if r is None:
                r = run_host(t, all_arms)
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                log(f'{t.task_id}: opt {r["optimum"]} (L{r["certify"]["lower"]}/U{r["certify"]["upper"]} '
                    f'{r["certify"]["wall_s"]:.0f}s) ' + ', '.join(f'{n} {a["value"]}' for n, a in r['arms'].items())
                    + f' [{time.monotonic() - t0:.0f}s]')
            rows.append(r)
    results = {'hosts': len(rows), 'calibration': {'record_sha256': digest(record), 'selected': record['selected']},
               'descriptors': {n: d['descriptor_id'] for n, d in all_arms.items()}, 'contrasts': {}}
    scored = [r for r in rows if r['optimum'] is not None]
    results['optimum_hits'] = {n: sum(r['arms'][n]['value'] == r['optimum'] for r in scored) for n in all_arms}
    if scored:
        results['placebo_minus_ablation_mean'] = round(statistics.fmean(
            r['arms']['placebo']['value'] - r['arms']['ablation']['value'] for r in scored), 4)
    for kind, _ in CONTRASTS:
        s, prow, power = contrast(kind, rows)
        results['contrasts'][kind] = s
        if prow is not None:
            R11.dump(out / f'pilot_rows_{kind}.json', prow)
            R11.dump(out / f'power_analysis_centred_{kind}.json', power)
        log(f'{kind}: {s["verdict"]}; mean {s.get("mean_difference")} {s.get("stratum_mean_differences")}; W/T/L '
            f'{s.get("wins_ties_losses")}; cpu {s["cpu_ratio_candidate_to_intervened"]}; power '
            f'{(s.get("power_centred") or {}).get("status")} {(s.get("power_centred") or {}).get("chosen")}; dry run '
            f'{(s.get("draft_plan_dry_run") or {}).get("decision")}')
    R11.dump(out / 'pilot_hosts.json', [t.model_dump(mode='json') for t in tasks])
    return results, tasks


# ------------------------------------------------------------------ part B

def followup_draft(kind, cand, interv, power, record):
    d = R11.draft_record()
    settings = ', '.join(f"{s['family']} {s['params']}" for s in record['selected'])
    what = {'ablation': 'removing its LP guidance (the registered ablation: init random_greedy, the same budget)',
            'placebo': ('replacing its LP guidance by the registered placebo (init lp_shuffled_greedy: the same LP '
                        'solve and restarts with the LP values permuted among the edges)')}[kind]
    return DR.build(
        plan_core_dict=plan_core(plan(kind)), power=power,
        exact_claim=('The frozen construction-pipeline candidate (descriptor ' + cand['descriptor_id'][:16] + ') scores '
                     'more edges than the same candidate after ' + what + ' (descriptor ' + interv['descriptor_id'][:16] +
                     '), on a custodian-held CONFIRM panel of triangle_free_host_v1 hosts drawn from the e1b study '
                     'calibration (rule e1-hard-v2, record SHA-256 ' + digest(record)[:16] + ', settings ' + settings +
                     '), by at least the minimum useful effect, under the registered analysis.'),
        capability_changes='None: a causal follow-up of the E1b claim; the arms differ in one registered component.',
        permissible_information=d['permissible_information'],
        baselines={'comparator': f'the registered {kind} of the frozen candidate (replay_contracts.INTERVENTIONS)',
                   'meaning': RC.INTERVENTIONS[('construct-pipeline-v1', ('init',))]['meaning']},
        total_budget={'profile': cand['resource_profile'], 'search_seconds_per_arm': RD.SEARCH_S, 'arms': 2,
                      'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; every host the builder named or generated; a CONFIRM '
                         'panel is retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' An intervened arm that is not the registered intervention of '
                            'the frozen candidate.'),
        allowed_conclusion=(f'If SUPPORTED: on that panel only, the LP guidance contributes at least the minimum useful '
                            f'effect ({kind}). Not a statement about other components, families or domains.'),
        status='DRAFT')


def part_b(out, log, excluded, named, pilot):
    from genesis import custody_records as CR
    from genesis.campaign import Campaign
    from genesis.cli import (descriptor_request_bundle, export_replication, followup_request,
                             freeze_candidate_descriptor, record_comparator_selection)
    from genesis.custodian import evaluate, register, registration_log, select_comparator, verify
    from genesis.judge import recompute
    from genesis.kernel import receipts as R
    from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
    from genesis.models import Config
    record = CAL.load(TF, ROOT, study=STUDY)
    all_arms = arms()
    cand = all_arms['candidate']
    tm = RP.arms('e1b_tf', TF)[1]
    work = out / 'work'
    if work.exists():
        shutil.rmtree(work)
    camp_root = work / 'campaign'
    Campaign.initialize(camp_root, Config(domain=TF, seed=CAMPAIGN_SEED, generations=1, tasks_per_panel=4,
                                          proposals_per_epoch=2, research_trials=8))
    with Campaign(camp_root) as camp:
        camp.run()
        cv = freeze_candidate_descriptor(camp, cand, origin='B20_R25 E1b causal rehearsal (handoff/e1b)')
        export_replication(camp_root, camp_root / 'exports' / 'campaign_export.zip', store=camp.store)
    reh = work / 'custodian'
    reh.mkdir(parents=True)
    reh.chmod(0o700)
    keys = {n: R11.keyfile(reh, f'{n}_FIXTURE') for n in ('prereg', 'custodian', 'auditor', 'release', 'replicator',
                                                         'priority_reviewer')}
    # The custodian screens each JSON source up to 1,000,000 values and refuses larger ones ("adjudicate
    # externally"); the first run of this script stopped there with all named hosts in one file. The same
    # hosts are now split across several sources (fix after the crash, before any Part B result; rules unchanged).
    named = [t.model_dump(mode='json') for t in named]
    sources = []
    for i in range(0, len(named), HOSTS_PER_SOURCE):
        f = reh / f'builder_named_hosts_{i // HOSTS_PER_SOURCE:02d}.json'
        f.write_bytes(canonical(named[i:i + HOSTS_PER_SOURCE]))
        f.chmod(0o600)
        sources.append({'kind': 'json', 'path': f.name, 'label': f'builder-named hosts, part {i // HOSTS_PER_SOURCE}'})
    manifest = reh / 'exposure_manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': sources}))
    manifest.chmod(0o600)
    op = 'BUILDER_REHEARSAL_NOT_INDEPENDENT'
    export = camp_root / 'exports' / 'campaign_export.zip'
    t0 = time.monotonic()
    sel = select_comparator(reh, export, tm, keys['custodian'][0], op, exposure_manifest=manifest,
                            task_count=SELECT_TASKS, study=STUDY)
    sp = verify(sel, keys['custodian'][1])
    select_tasks = json.loads((reh / 'comparator_selections' / f'{digest(sel)}.json').read_text())['tasks']
    excluded = set(excluded) | RD.identities([GraphTask.model_validate_json(canonical(t)) for t in select_tasks])
    log(f'SELECT panel {sp["totals"]} -> comparator {sp["selected"]} ({time.monotonic() - t0:.0f} s)')
    with Campaign(camp_root) as camp:
        record_comparator_selection(camp, sel)
    main_draft = json.loads((ROOT / 'handoff' / 'e1b' / 'decision_record_DRAFT.json').read_text())
    main_power = json.loads((ROOT / 'handoff' / 'e1b' / 'power_analysis_centred_b20r24.json').read_text())
    evaluations, results = [], {'comparator_selection': sp, 'select_hosts': select_tasks, 'evaluations': {}}

    def sealed(kind, request, frozen, total, seed):
        nonlocal excluded
        tasks, _ = CAL.calibrated_panel(record, seed, total, 'CONFIRM', excluded=excluded)
        excluded = set(excluded) | RD.identities(tasks)
        pool = reh / f'pool_{kind}.json'
        pool.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
        t1 = time.monotonic()
        anchor = register(reh, request, keys['prereg'][0], op, exposure_manifest=manifest, campaign_export=export,
                          pool=pool, decision_record=frozen)
        receipt = evaluate(reh, digest(request), pool, keys['custodian'][0], op)
        p = verify(receipt, keys['custodian'][1])
        lg, problems = CR.check_log(registration_log(reh, keys['custodian'][0]), keys['custodian'][1], verify)
        judged = recompute(reh / 'evaluations' / digest(request), request, receipt, registration_log_entries=lg['entries'])
        a = p['analysis_result']
        log(f'{kind}: {p["outcome"]} (W/L/T {p["wins"]}/{p["losses"]}/{p["ties"]}; scored {a.get("scored")}/'
            f'{a.get("tasks")}), estimate {a.get("estimate")} {a.get("interval")}, cost ratio {a.get("cost_ratio")}, '
            f'judge agrees {judged["agrees"]} ({time.monotonic() - t1:.0f} s)')
        results['evaluations'][kind] = {
            'request_sha256': digest(request), 'decision_record_rehearsal_sha256': digest(frozen),
            'receipt_payload': p, 'anchor_payload': anchor['payload'],
            'judge': {k: judged.get(k) for k in ('agrees', 'problems', 'witnesses_rechecked', 'recomputed_outcome')},
            'fairness': judged.get('fairness'), 'log_problems': problems,
            'confirm_hosts': [t.model_dump(mode='json') for t in tasks]}
        R11.dump(out / f'request_{kind}.json', request)
        R11.dump(out / f'receipt_{kind}.json', receipt)
        evaluations.append((request, anchor, receipt))

    # 2. the main sealed evaluation
    reh_main = copy.deepcopy(main_draft)
    reh_main['exact_claim'] = 'REHEARSAL (same operator, fixture keys, not a reviewed decision): ' + main_draft['exact_claim']
    frozen_main, h_main = DR.freeze(reh_main)
    total_main = main_power['chosen']['total_tasks']
    statement = 'REHEARSAL: ' + main_draft['exact_claim']
    scope = f'rehearsal panels of {TF} hosts from the e1b calibration (same operator)'
    with Campaign(camp_root) as camp:
        path = descriptor_request_bundle(camp, total_main, analysis=dict(main_draft['analysis_plan_core'],
                                                                         decision_record_sha256=h_main),
                                         claim_id=CLAIM_ID, statement=statement, scope=scope)
        main_request = json.loads(path.read_text())
    sealed('sealed_evaluation', main_request, frozen_main, total_main, MAIN_SEED)
    # 3. the follow-ups that are ready
    for j, (kind, _) in enumerate(CONTRASTS):
        if pilot['contrasts'][kind]['verdict'] != 'READY_FOR_REVIEW':
            results['evaluations'][kind] = f'not run: pilot verdict {pilot["contrasts"][kind]["verdict"]}'
            continue
        power = json.loads((out / f'power_analysis_centred_{kind}.json').read_text())
        draft = followup_draft(kind, cand, all_arms[kind], power, record)
        reh_k = copy.deepcopy(draft)
        reh_k['exact_claim'] = 'REHEARSAL (same operator, fixture keys, not a reviewed decision): ' + draft['exact_claim']
        frozen_k, h_k = DR.freeze(reh_k)
        with Campaign(camp_root) as camp:
            req = followup_request(camp, kind, analysis=dict(plan_core(plan(kind)), decision_record_sha256=h_k),
                                   task_count=power['chosen']['total_tasks'], baseline=all_arms[kind])
        R11.dump(out / f'decision_record_DRAFT_{kind}.json', draft)
        sealed(kind, req, frozen_k, power['chosen']['total_tasks'], FOLLOW_SEED + 10 * j)
    # 4. the evidence kernel
    registry = {'pins': {'custodian_key': keys['custodian'][1], 'prereg_key': keys['prereg'][1],
                         'auditor_key': keys['auditor'][1], 'release_key': keys['release'][1],
                         'replicator_key': keys['replicator'][1],
                         'priority_reviewer_key': keys['priority_reviewer'][1],
                         'release_authority_id': 'REHEARSAL_FIXTURE_BOARD'}}
    kernel = {'registry': 'FIXTURE (rehearsal keys; not the externally pinned trust root)', 'promotions': []}
    with Campaign(camp_root) as camp:
        k = EvidenceKernel.with_fixture_registry(camp.store, registry)
        nodes = []
        for request, anchor, receipt in evaluations:
            src = request['source_hash']
            a = k.record_signed('preregistration_anchor', anchor, route='genesis.custodian.evaluate', source_hash=src)
            nodes.append(k.record_signed(request['evidence_kind'], receipt, parents=[a],
                                         route='genesis.custodian.evaluate', source_hash=src))
        binding = R.binding_from_requests([r for r, _, _ in evaluations])
        k.create_claim(CLAIM_ID, statement, scope, nodes, binding=binding)
        steps = [('utility', 'CONFIRMED_SAME_DOMAIN'), ('causality', 'ABLATION_SUPPORTED')]
        if any(r['evidence_kind'] == 'placebo' for r, _, _ in evaluations):
            steps.append(('causality', 'PLACEBO_CONTROLLED'))
        for axis, level in steps:
            try:
                k.promote(CLAIM_ID, axis, level)
                kernel['promotions'].append({'axis': axis, 'level': level, 'result': 'PROMOTED'})
            except PromotionRejected as exc:
                kernel['promotions'].append({'axis': axis, 'level': level, 'result': 'REJECTED',
                                             'reasons': exc.args[0]})
            log(f'kernel: {axis} {level}: {kernel["promotions"][-1]["result"]}'
                + (f' {kernel["promotions"][-1].get("reasons")}' if kernel['promotions'][-1]['result'] == 'REJECTED'
                   else ''))
        kernel['levels'] = k.levels(CLAIM_ID)
        kernel['binding'] = binding
        kernel['nodes'] = nodes
    log(f'kernel levels {kernel["levels"]}')
    results['kernel'] = kernel
    results['campaign_candidate_version'] = cv
    shutil.copy(export, out / 'campaign_export.zip')
    shutil.rmtree(work)
    return results


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
    excluded, scan, named = RP.exposure(log)
    pilot, tasks = part_a(out, log, excluded)
    excluded = set(excluded) | RD.identities(tasks)
    rehearsal = 'not run: --summary'
    if '--summary' not in argv:
        ready = [k for k, _ in CONTRASTS if pilot['contrasts'][k]['verdict'] == 'READY_FOR_REVIEW']
        if ready:
            rehearsal = part_b(out, log, excluded, list(named) + list(tasks), pilot)
            R11.dump(out / 'rehearsal.json', {'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: licenses nothing',
                                              **rehearsal})
            rehearsal = {'evaluations': {k: (v['receipt_payload']['outcome'] if isinstance(v, dict) else v)
                                         for k, v in rehearsal['evaluations'].items()},
                         'kernel_levels': rehearsal['kernel']['levels'],
                         'promotions': [(p['axis'], p['level'], p['result']) for p in rehearsal['kernel']['promotions']]}
        else:
            rehearsal = 'not run: no contrast READY_FOR_REVIEW'
    summary = {'schema': 'genesis-b20r25-e1b-causal-v1', 'pilot': pilot, 'rehearsal': rehearsal,
               'verdicts': {k: v['verdict'] for k, v in pilot['contrasts'].items()}, 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV re-pilot and a same-operator rehearsal with fixture keys; licenses no claim'}
    R11.dump(out / 'summary.json', summary)
    log(f'verdicts {summary["verdicts"]}; rehearsal {json.dumps(rehearsal)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
