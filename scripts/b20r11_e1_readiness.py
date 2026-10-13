#!/usr/bin/env python3
"""B20_R11: E1 readiness through the custodian's own runner (GV3 path; B19-OPEN-3 repaired in B20_R5).

    b20r11_e1_readiness.py OUT_DIR

The B19 E1 candidate is the represent-and-repair solver with the cut representation cross_2.
Its DEV pilot gave +1.27 edges per task over `low_cycle`. In that pilot the candidate's CPU was
measured in-process and the baselines' CPU in the DSL worker, and the custodian could not run
the candidate at all.

Since B20_R5 the custodian runs both arms through `candidates.run(isolation='runc')`:
  * the same OCI sandbox for every arm;
  * one resource profile for every arm;
  * the same cgroup CPU meter for every arm.
This script measures E1 on that path and prepares the package an independent custodian needs.

Part A: DEV pilot under the custodian's runner (rules fixed here, before running).
  * Tasks: 30 fresh DEV hosts from the adopted triangle-free calibration, seed 20261113. The
    B19 pilot hosts (seed 20261026, 60 tasks) are excluded.
  * Candidate: represent-and-repair, cross_2, 0.5 CPU s inside the solver (as in B19).
  * Baselines: the three fixed DSL programs. One shared profile for all arms: 2 CPU s,
    1000 queries, 2048 MiB, 10 s wall (the calibration limits).
  * Reference optimum: the domain adapter, 30 s per task. Tasks without a certified reference
    are reported and excluded.
  * Rows: the candidate against the strongest baseline by total value, scored with the B19
    DRAFT plan (dry run; DEV).
  * Readiness verdict (fixed here):
      READY_FOR_REVIEW   mean difference >= the plan's minimum useful effect AND the
                         candidate/baseline CPU ratio <= the plan's max_ratio;
      COST_RULE_FAILS    the effect is reached but the CPU ratio exceeds max_ratio;
      EFFECT_BELOW_MUE   otherwise.

Part B: the E1 package (handoff/e1/), prepared and NOT registered with any real custodian.
  * A real frozen triangle-free campaign with the candidate descriptor frozen in it.
  * The v4 request needs a decision record frozen by a reviewer (the power model is B19-OPEN-4).
    The package therefore ships the DRAFT and the exact commands, and no request.
  * A REHEARSAL by the same operator, with fixture keys and a builder-frozen copy of the
    record: register, evaluate and judge on 25 freshly generated hosts. It shows that the
    package executes; it is not independent, not a CONFIRM result, and licenses nothing. Its
    hosts go into the package's exposure manifest so a real custodian excludes them.
"""
import base64
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import bytes_hash, canonical, code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS, Unsupported  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.kernel.analysis import analyze  # noqa: E402

DOMAIN = 'triangle_free_host_v1'
B19_SEED, B19_TASKS = 20261026, 60
PILOT_SEED, PILOT_TASKS = 20261113, 30
REHEARSAL_SEED, REHEARSAL_TASKS = 20261127, 25
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}
CANDIDATE_PARAMS = {'representation': 'cross_2', 'cpu_seconds': 0.5, 'seed': 0}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + '\n')


def descriptors():
    cand = C.build_descriptor('represent-and-repair-v1', DOMAIN, CANDIDATE_PARAMS, **PROFILE)
    dsl = {n: C.build_descriptor('dsl-program-v1', DOMAIN, {'program': p.model_dump(mode='json')}, **PROFILE)
           for n, p in sorted(baseline_programs().items())}
    return cand, dsl


def draft_record():
    return json.loads((ROOT / 'evidence/readiness_b19/e1/decision_record_DRAFT.json').read_text())


def part_a(out, log):
    record = CAL.load(DOMAIN, ROOT)
    _, b19_seen = CAL.calibrated_panel(record, B19_SEED, B19_TASKS, 'DEV')
    tasks, _ = CAL.calibrated_panel(record, PILOT_SEED, PILOT_TASKS, 'DEV', excluded=b19_seen)
    cand, dsl = descriptors()
    arms = {'candidate': cand, **dsl}
    runs, optima = {}, {}
    for t in tasks:
        ref = ADAPTERS[DOMAIN].reference(t, seconds=30)
        optima[t.task_id] = None if isinstance(ref, Unsupported) else ref['value']
        seed = int(digest({'seed': PILOT_SEED, 'task': t.task_id})[:12], 16)
        for name, desc in arms.items():
            r = C.run(t, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
            ok = r['status'] == 'SUCCESS'
            runs[(t.task_id, name)] = {'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED',
                                       'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else 0,
                                       'status': r['status']}
        log(f'{t.task_id}: optimum {optima[t.task_id]}, ' +
            ', '.join(f'{n} {runs[(t.task_id, n)]["value"]}' for n in arms))
    totals = {n: sum(runs[(t.task_id, n)]['value'] for t in tasks) for n in dsl}
    strongest = max(totals, key=lambda n: (totals[n], n))
    rows = [{'task_id': t.task_id, 'stratum': t.family, 'status': 'SCORED', 'split': t.split,
             'optimum': optima[t.task_id],
             'candidate': {k: runs[(t.task_id, 'candidate')][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: runs[(t.task_id, strongest)][k] for k in ('value', 'run', 'cpu_ns')}}
            for t in tasks if optima[t.task_id] is not None]
    draft = draft_record()
    plan = dict(draft['analysis_plan_core'], decision_record_sha256='0' * 64)
    result = analyze(rows, plan)
    diffs = [r['candidate']['value'] - r['baseline']['value'] for r in rows]
    cpu = {n: sum(runs[(t.task_id, n)]['cpu_ns'] for t in tasks) for n in arms}
    ratio = cpu['candidate'] / cpu[strongest] if cpu[strongest] else None
    mean = sum(diffs) / len(diffs)
    mue, max_ratio = plan['minimum_useful_effect'], plan['cost']['max_ratio']
    verdict = ('READY_FOR_REVIEW' if mean >= mue and ratio is not None and ratio <= max_ratio else
               'COST_RULE_FAILS' if mean >= mue else 'EFFECT_BELOW_MUE')
    summary = {'tasks': len(tasks), 'scored': len(rows), 'strongest_baseline': strongest, 'baseline_totals': totals,
               'candidate_total': sum(r['candidate']['value'] for r in rows),
               'mean_difference': round(mean, 4),
               'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
               'candidate_optimum_hits': sum(r['candidate']['value'] == r['optimum'] for r in rows),
               'baseline_optimum_hits': sum(r['baseline']['value'] == r['optimum'] for r in rows),
               'cpu_ns_by_arm': cpu, 'cpu_ratio_candidate_to_strongest': round(ratio, 4) if ratio else None,
               'plan_minimum_useful_effect': mue, 'plan_max_cost_ratio': max_ratio,
               'draft_plan_dry_run': {k: result.get(k) for k in ('decision', 'estimate', 'interval', 'p_value',
                                                                  'checks', 'cost_ratio')},
               'failures': {n: sum(runs[(t.task_id, n)]['run'] == 'FAILED' for t in tasks) for n in arms},
               'verdict': verdict, 'descriptors': {n: d['descriptor_id'] for n, d in arms.items()},
               'profile': PROFILE, 'candidate_parameters': CANDIDATE_PARAMS,
               'status': 'DEV pilot under the custodian runner; no sealed task; no claim'}
    dump(out / 'pilot_rows.json', rows)
    dump(out / 'pilot_summary.json', summary)
    log(f'pilot: mean {mean:+.3f} vs {strongest}, W/T/L {summary["wins_ties_losses"]}, cpu ratio {summary["cpu_ratio_candidate_to_strongest"]}, '
        f'DRAFT dry run {result.get("decision")} -> {verdict}')
    return summary, b19_seen, tasks


def keyfile(directory, name):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    k = Ed25519PrivateKey.generate()
    path = Path(directory) / f'{name}.pem'
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    path.chmod(0o600)
    return path, base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                              serialization.PublicFormat.Raw)).decode()


def part_b(out, log, excluded):
    from genesis.campaign import Campaign
    from genesis.cli import descriptor_request_bundle, freeze_candidate_descriptor
    from genesis.models import Config
    pkg = out / 'package'
    camp_root = pkg / 'campaign'
    if camp_root.exists():
        shutil.rmtree(camp_root)
    cfg = Config(domain=DOMAIN, seed=20261120, generations=1, tasks_per_panel=4, proposals_per_epoch=2,
                 research_trials=8)
    t0 = time.monotonic()
    Campaign.initialize(camp_root, cfg)
    with Campaign(camp_root) as camp:
        camp.run()
    log(f'campaign frozen in {time.monotonic() - t0:.0f} s')
    cand, _ = descriptors()
    draft = draft_record()
    with Campaign(camp_root) as camp:
        cv = freeze_candidate_descriptor(camp, cand, origin=('B18 W10 representation grammar (cross_2) with greedy '
                                                             'repair; B19 E1 candidate (evidence/readiness_b19/e1)'))
        strongest = camp.store.state('summary')['generations'][-1]['baseline']
        # REHEARSAL ONLY: a builder-frozen copy of the B19 DRAFT. The real record must be frozen by the
        # reviewer who accepts or rejects the power model (B19-OPEN-4).
        rehearsal = copy.deepcopy(draft)
        rehearsal['exact_claim'] = 'REHEARSAL (same operator, fixture keys, not a reviewed decision): ' + draft['exact_claim']
        frozen, h = DR.freeze(rehearsal)
        plan = dict(draft['analysis_plan_core'], decision_record_sha256=h)
        path = descriptor_request_bundle(camp, REHEARSAL_TASKS, analysis=plan, claim_id='e1-rehearsal-b20r11',
                                         statement='REHEARSAL: ' + draft['exact_claim'],
                                         scope='rehearsal panel of 25 triangle_free_host_v1 hosts (same operator)')
        request = json.loads(path.read_text())
        export = camp_root / 'exports' / 'campaign_export.zip'
    log(f'candidate frozen ({cv[:12]}); campaign strongest baseline {strongest}; rehearsal request {digest(request)[:12]}')
    # The rehearsal custodian (same operator, fixture keys).
    from genesis.custodian import evaluate, register, registration_log, verify
    from genesis import custody_records as CR
    from genesis.judge import recompute
    reh = out / 'rehearsal'
    if reh.exists():
        shutil.rmtree(reh)
    reh.mkdir(parents=True)
    reh.chmod(0o700)
    prereg, cust = keyfile(reh, 'prereg_FIXTURE'), keyfile(reh, 'custodian_FIXTURE')
    manifest = reh / 'exposure_manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
    manifest.chmod(0o600)
    record = CAL.load(DOMAIN, ROOT)
    tasks, _ = CAL.calibrated_panel(record, REHEARSAL_SEED, REHEARSAL_TASKS, 'CONFIRM', excluded=excluded)
    pool = reh / 'rehearsal_pool.json'
    pool.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
    t0 = time.monotonic()
    anchor = register(reh, request, prereg[0], 'BUILDER_REHEARSAL_NOT_INDEPENDENT', exposure_manifest=manifest,
                      campaign_export=export, pool=pool, decision_record=frozen)
    receipt = evaluate(reh, digest(request), pool, cust[0], 'BUILDER_REHEARSAL_NOT_INDEPENDENT')
    p = verify(receipt, cust[1])
    log_env = registration_log(reh, cust[0])
    lg, problems = CR.check_log(log_env, cust[1], verify)
    judged = recompute(reh / 'evaluations' / digest(request), request, receipt, registration_log_entries=lg['entries'])
    log(f'rehearsal: {p["outcome"]} (W/L/T {p["wins"]}/{p["losses"]}/{p["ties"]}), judge agrees {judged["agrees"]}, '
        f'{time.monotonic() - t0:.0f} s')
    rehearsal_out = {'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: not independent, not a CONFIRM result, licenses nothing',
                     'request_sha256': digest(request), 'receipt_payload': p, 'anchor_payload': anchor['payload'],
                     'judge': {k: judged.get(k) for k in ('agrees', 'problems', 'witnesses_rechecked', 'recomputed_outcome')},
                     'resource_account': judged.get('resource_account'), 'fairness': judged.get('fairness'),
                     'log_problems': problems, 'panel_tasks': [t.task_id for t in tasks]}
    dump(out / 'rehearsal_summary.json', rehearsal_out)
    # Package contents: everything a reviewer and an independent custodian need, nothing private.
    shutil.copy(export, pkg / 'campaign_export.zip')
    dump(pkg / 'candidate_descriptor.json', cand)
    dump(pkg / 'decision_record_DRAFT.json', draft)
    for name in ('power_analysis.json', 'power_analysis_b16_model.json', 'pilot_rows.json', 'summary.json'):
        shutil.copy(ROOT / 'evidence/readiness_b19/e1' / name, pkg / f'b19_{name}')
    dump(pkg / 'exposure_hosts_to_exclude.json', {
        'note': 'every DEV and rehearsal host the builder generated for E1; a real custodian adds them to its exposure '
                'manifest (with every DEV panel named in B16-B20 evidence)',
        'b19_pilot': {'seed': B19_SEED, 'tasks': B19_TASKS}, 'b20r11_pilot': {'seed': PILOT_SEED, 'tasks': PILOT_TASKS},
        'b20r11_rehearsal': [t.model_dump(mode='json') for t in tasks]})
    shutil.rmtree(camp_root)
    return {'campaign_strongest_baseline': strongest, 'candidate_version': cv, 'rehearsal_outcome': p['outcome'],
            'judge_agrees': judged['agrees']}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    summary, b19_seen, pilot = part_a(out, log)
    excluded = set(b19_seen)
    record = CAL.load(DOMAIN, ROOT)
    _, pilot_seen = CAL.calibrated_panel(record, PILOT_SEED, PILOT_TASKS, 'DEV', excluded=b19_seen)
    excluded |= set(pilot_seen)
    b = part_b(out, log, excluded)
    dump(out / 'readiness.json', {'pilot': summary, 'package': b, 'code_identity': code_identity(ROOT)['sha256']})
    return 0


if __name__ == '__main__':
    sys.exit(main())
