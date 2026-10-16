#!/usr/bin/env python3
"""B20_R45: a same-operator rehearsal of the E1d ablation evaluation through the v5 path (GV3 path,
causal control; B20R41-OPEN-1, B20R44-OPEN-1). DEV, builder-run, fixture keys. Nothing is adopted or
registered with any custodian.

    taskset -c 0 python3 scripts/b20r45_e1d_ablation_rehearsal.py OUT_DIR

**Why.** B20_R44 found the registered ablation of E1's discovered representation (`cross_2` →
`ordered_2`) READY_FOR_REVIEW, with power chosen at 15 per stratum (45 hosts). A causal level
(ABLATION_SUPPORTED) is licensed only by a *custodian-signed* evaluation of evidence kind `ablation`.
The custodian re-checks the intervention's provenance (replay_contracts.intervention_problems), and
the kernel replays it from the arms the receipt commits to. This step runs that path once with
fixture keys, so that a reviewer sees it work before deciding. Everything below was fixed before
running.

**Steps (in this repository; no adoption is needed, because SELECT does not take part in an
ablation):**
  1. A fresh frozen DEV campaign (1 generation), with E1's frozen candidate frozen in it.
  2. The campaign's sealed_evaluation request for E1d, frozen as v5 with the B20_R43 reference route
     and analysis plan. It is never registered here. It fixes the claim that the ablation follows
     up.
  3. A DRAFT decision record for the ablation claim, in the custodian's ablation family
     (`ablation:triangle_free_host_v1`), with a REHEARSAL-labelled frozen copy. Its power analysis is
     B20_R44's centred model recomputed from B20_R44's rows for this plan. A power analysis is bound
     to its plan core, and the family is part of the core; a design test caught that before the run.
     - The claim: the frozen candidate scores more edges than its registered ablation on a
       custodian-held CONFIRM panel, by at least the minimum useful effect.
  4. cli.followup_request(campaign, 'ablation', ...). This gives a v5 ablation request whose
     baseline is the registered ablation, with the task count the recomputed power analysis chooses.
  5. A CONFIRM pool of that size drawn from the B20_R43 calibration record, seed 20264501. It excludes
     every identity b20r24_repilots.exposure excludes, which covers all B20_R41/R43/R44 hosts.
  6. Fixture keys, and an exposure manifest of every named host in files of at most 500. Then
     register (the custodian re-checks the intervention), evaluate, verify, the registration-log
     check, and judge.recompute.

**Reading.** SUPPORTED with the judge agreeing means the causal path works end to end. The rehearsal
licenses nothing: one operator plays every role, and the transform awaits review (B20R44-OPEN-1).
INVALID or NOT_SUPPORTED is recorded as it comes, with no re-run.
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
from genesis import decision_record as DR  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.kernel.analysis import plan_core  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r43_e1d_package as R43  # noqa: E402
import b20r44_e1d_ablation as R44  # noqa: E402

TF = RD.TF
CONFIRM_SEED, CAMPAIGN_SEED = 20264501, 20264511
OPERATOR = 'BUILDER_REHEARSAL_NOT_INDEPENDENT'
E1D_DRAFT = ROOT / 'handoff' / 'e1d' / 'decision_record_DRAFT.json'
R44_DIR = ROOT / 'evidence' / 'e1d_ablation_b20r44'


def ablation_plan():
    """B20_R24's plan core with the hypothesis family the custodian assigns to ablations (custody_records)."""
    p = R24.plan(TF)
    p['multiplicity'] = dict(p['multiplicity'], family_id=f'ablation:{TF}')
    return p


def ablation_power():
    """B20_R44's centred power analysis, recomputed from its pilot rows for the ablation plan: the power
    analysis is bound to the plan core, and the custodian's ablation family changes the core."""
    from genesis.power import required_sample
    rows = [json.loads(l) for l in (R44_DIR / 'rows.jsonl').read_text().splitlines() if l.strip()]
    prow = [{'task_id': r['task_id'], 'stratum': r['stratum'], 'status': 'SCORED', 'split': r['split'],
             'optimum': r['optimum'],
             'candidate': {k: r['arms']['candidate'][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: r['arms']['ablation'][k] for k in ('value', 'run', 'cpu_ns')}}
            for r in rows if r['optimum'] is not None]
    return required_sample(prow, ablation_plan(), sims=1000, min_tasks_per_stratum=10, headroom='centred')


def ablation_draft(cand, abl, power, record):
    d = R11.draft_record()
    settings = ', '.join(f"{s['family']} {s['params']}" for s in record['selected'])
    ref = R43.reference_spec()
    cal = (f"the e1d study calibration (rule {record['rule']['name']}, record SHA-256 {digest(record)[:16]}, "
           f"settings {settings})")
    return DR.build(
        plan_core_dict=plan_core(ablation_plan()), power=power,
        exact_claim=('The frozen representation-and-repair candidate (descriptor ' + cand['descriptor_id'][:16] +
                     ', cut representation cross_2, 0.5 CPU s of search) scores more edges than its registered ablation '
                     '(descriptor ' + abl['descriptor_id'][:16] + ': the same candidate with the discovered cross_2 '
                     'decoder replaced by the Lean-checked strictly weaker ordered_2 decoder, kernel replay_contracts '
                     'INTERVENTIONS) on a custodian-held CONFIRM panel of ' + TF + ' hosts drawn from ' + cal +
                     ', with optima certified by the generated-rows reference (' + ref['route'] + '), by at least the '
                     'minimum useful effect, under the registered analysis.'),
        capability_changes=('None beyond E1d: the comparison isolates one registered component (the decoder of the '
                            'discovered representation) of the frozen candidate.'),
        permissible_information=d['permissible_information'],
        baselines={'comparator': 'the registered ablation of the candidate (replay_contracts.intervention_problems)',
                   'not_a_competitor': 'the generated-rows reference is evaluator ground truth'},
        total_budget={'profile': cand['resource_profile'], 'search_seconds_per_arm': 0.5, 'arms': 2,
                      'reference_seconds_per_task': ref['seconds'],
                      'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every DEV '
                         'panel named in the evidence and every host the builder generated; a CONFIRM panel is '
                         'retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' A baseline that is not the registered ablation of the frozen '
                            'candidate. A panel not drawn from the e1d study calibration named in the claim.'),
        allowed_conclusion=('If SUPPORTED: on that panel only, the discovered representation\'s decoder is causally '
                            'responsible for an effect of at least the minimum useful effect (ABLATION_SUPPORTED at most; '
                            'no placebo exists for this component). Not novelty, transfer or improver claims.'),
        status='DRAFT')


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0]).resolve()
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
    from genesis import custody_records as CRec
    from genesis.campaign import Campaign
    from genesis.cli import descriptor_request_bundle, export_replication, freeze_candidate_descriptor, followup_request
    from genesis.custodian import evaluate, register, registration_log, verify
    from genesis.judge import recompute
    from genesis.models import Config
    from genesis.store import Store
    record = json.loads(R44.RECORD.read_text())
    if CAL.record_problems(record):
        raise RuntimeError('the calibration record does not check')
    A = R44.arms()
    cand, abl = A['candidate'], A['ablation']
    power = ablation_power()
    if power.get('status') != 'CHOSEN':
        raise RuntimeError(f'the recomputed power analysis chooses no size: {power.get("status")}')
    total = power['chosen']['total_tasks']
    R11.dump(out / 'power_analysis_centred_ablation_plan.json', power)
    log(f'power recomputed for the ablation plan: {power["chosen"]}')
    excluded, scan, named = R24.exposure(log)
    work = out / 'work'
    if work.exists():
        shutil.rmtree(work)
    camp_root = work / 'campaign'
    Campaign.initialize(camp_root, Config(domain=TF, seed=CAMPAIGN_SEED, generations=1, tasks_per_panel=4,
                                          proposals_per_epoch=2, research_trials=8))
    with Campaign(camp_root) as camp:
        camp.run()
        cv = freeze_candidate_descriptor(camp, cand, origin='B20_R45 E1d candidate = the frozen E1 candidate (REHEARSAL)')
        export_replication(camp_root, camp_root / 'exports' / 'campaign_export.zip', store=camp.store)
    e1d = json.loads(E1D_DRAFT.read_text())
    _, h_main = DR.freeze(dict(e1d, exact_claim='REHEARSAL (same operator, fixture keys, not a reviewed decision): '
                                               + e1d['exact_claim']))
    p_main = dict(e1d['analysis_plan_core'], decision_record_sha256=h_main)
    d_abl = ablation_draft(cand, abl, power, record)
    frozen_abl, h_abl = DR.freeze(dict(d_abl, exact_claim='REHEARSAL (same operator, fixture keys, not a reviewed '
                                                          'decision): ' + d_abl['exact_claim']))
    p_abl = dict(d_abl['analysis_plan_core'], decision_record_sha256=h_abl)
    with Campaign(camp_root) as camp:
        descriptor_request_bundle(camp, 240, analysis=p_main, claim_id='e1d-rehearsal-b20r45',
                                  statement='REHEARSAL: ' + e1d['exact_claim'],
                                  scope=f'rehearsal panel of 240 {TF} hosts (same operator)',
                                  reference=R43.reference_spec())
        request = followup_request(camp, 'ablation', analysis=p_abl, task_count=total, baseline=abl)
    log(f'v5 ablation request frozen ({request["schema"]}, {total} hosts); baseline {abl["descriptor_id"][:16]}')
    tasks, _ = CAL.calibrated_panel(record, CONFIRM_SEED, total, 'CONFIRM', excluded=set(excluded))
    reh = work / 'rehearsal'
    reh.mkdir(parents=True)
    reh.chmod(0o700)
    prereg, cust = R11.keyfile(reh, 'prereg_FIXTURE'), R11.keyfile(reh, 'custodian_FIXTURE')
    files = R43.host_chunks(reh, 'builder_named_hosts', list(named))
    for name in files:
        (reh / name).chmod(0o600)
    manifest = reh / 'exposure_manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': [
        {'kind': 'json', 'path': name, 'label': f'every host the builder named or generated ({name})'}
        for name in files]}))
    manifest.chmod(0o600)
    pool = reh / 'rehearsal_pool.json'
    pool.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
    t1 = time.monotonic()
    anchor = register(reh, request, prereg[0], OPERATOR, exposure_manifest=manifest,
                      campaign_export=camp_root / 'exports' / 'campaign_export.zip', pool=pool, decision_record=frozen_abl)
    log('registered (the custodian re-checked the intervention); evaluating')
    receipt = evaluate(reh, digest(request), pool, cust[0], OPERATOR)
    rp = verify(receipt, cust[1])
    lg, problems = CRec.check_log(registration_log(reh, cust[0]), cust[1], verify)
    judged = recompute(reh / 'evaluations' / digest(request), request, receipt, registration_log_entries=lg['entries'])
    log(f'rehearsal {rp["outcome"]} (W/L/T {rp["wins"]}/{rp["losses"]}/{rp["ties"]}), estimate '
        f'{rp["analysis_result"].get("estimate")}, cost ratio {rp["analysis_result"].get("cost_ratio")}, judge agrees '
        f'{judged["agrees"]} ({time.monotonic() - t1:.0f} s)')
    refs = {'methods': {}, 'unsupported': 0, 'wall_s': []}
    with Store(reh / 'evaluations' / digest(request)) as s:
        for _, req_h, rec_h in s.db.execute('SELECT status,request,receipt FROM attempts'):
            a, r = s.get(req_h), s.get(rec_h)
            if a.get('kind') == 'exact-check':
                if r['status'] == 'UNSUPPORTED':
                    refs['unsupported'] += 1
                else:
                    refs['methods'][r['result']['method']] = refs['methods'].get(r['result']['method'], 0) + 1
                refs['wall_s'].append(round(r['wall_ns'] / 1e9, 3))
    summary = {'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: not independent, not a CONFIRM result, licenses nothing',
               'code_identity': code_identity(ROOT)['sha256'], 'campaign_candidate_version': cv,
               'request_sha256': digest(request), 'request_schema': request['schema'],
               'evidence_kind': request['evidence_kind'], 'reference': request['reference'],
               'arms': {n: d['descriptor_id'] for n, d in request['arms'].items()},
               'decision_record_draft': d_abl, 'decision_record_rehearsal_sha256': h_abl,
               'receipt_payload': rp, 'anchor_payload': anchor['payload'], 'reference_methods': refs,
               'judge': {k: judged.get(k) for k in ('agrees', 'problems', 'witnesses_rechecked', 'recomputed_outcome')},
               'resource_account': judged.get('resource_account'), 'fairness': judged.get('fairness'),
               'log_problems': problems, 'confirm_hosts': [t.model_dump(mode='json') for t in tasks],
               'exposure_scan': scan, 'status': 'same-operator rehearsal; the transform awaits review (B20R44-OPEN-1)'}
    R11.dump(out / 'rehearsal_summary.json', summary)
    R11.dump(out / 'rehearsal_receipt.json', receipt)
    R11.dump(out / 'decision_record_ablation_DRAFT.json', d_abl)
    shutil.rmtree(work)
    log(f'done: {rp["outcome"]}, judge agrees {judged["agrees"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
