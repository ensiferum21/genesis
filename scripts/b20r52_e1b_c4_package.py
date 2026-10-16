#!/usr/bin/env python3
"""B20_R52: the E1b-C4 DRAFT package and a same-operator rehearsal through the v5 path with the C4 tree reference
(GV3 path in C4; B20R50-OPEN-1, B20R48-OPEN-1). DEV, builder-run, fixture keys. Nothing is adopted or registered
with any custodian.

    b20r52_e1b_c4_package.py OUT_DIR                     run from the repository
    (it re-runs itself as  b20r52_e1b_c4_package.py OUT_DIR --rehearse  inside a throwaway copy)

**Why.** B20_R50 made E1b's C4 arm scorable:
  * a DRAFT rule (`e1-hard-v2-c4tree-draft`) whose reference is the tree route over the transferred rows;
  * two calibrated C4 settings;
  * READY_FOR_REVIEW in readiness and both causal contrasts.
B20_R51 wired that reference into the custodian path, opt-in, with custody. This step does for E1b's C4 arm
what B20_R43 did for E1d. It writes the package a reviewer would sign off, and runs the whole custody path
once with fixture keys. Everything below is fixed before running.

**1. Calibration record (in the repository).** B20_R50's Part A rows, rewritten as a
`genesis-dev-calibration-v1` record under the DRAFT rule (calibration.SELECTION_RULE_E1_HARD_V2_C4TREE_DRAFT).
  * The rows are copied, not re-measured.
  * calibration.record_problems must be [], and the selection must equal B20_R50's.
  * B20_R50's evidence is not rewritten. The record is a new file here.

**2. Rehearsal (in a throwaway copy).** The copy is `git archive HEAD`, so its code identity is this
commit's. In the copy only, `configs/dev_calibration.json` adopts the record as study `e1b-c4`, which stands
in for the reviewer's adoption. Then:
  * a fresh frozen DEV campaign on c4_host_v2 (1 generation), with E1b's C4 candidate frozen in it. The
    candidate is construct-pipeline-v1 with E1b's frozen parameters, built for c4_host_v2 as B20_R23 and
    R50 built it;
  * fixture keys and an exposure manifest of every host the builder named;
  * the custodian's SELECT on 30 private hosts drawn from the `e1b-c4` calibration, among E1b's three
    time-matched DSL baselines under the E1b profile;
  * the DRAFT decision record for E1b-C4, a REHEARSAL-labelled frozen copy, and a v5 request whose task
    count is B20_R50's power choice for readiness (20 = 10 per stratum). Its reference is
    `generated-rows-tree-c4-v1` with B20_R46's package, **600 s** (the evaluator's measure in B20_R30 and
    the plan's unsupported limit, B20R24-OPEN-2), and B20_R47's limits with `lp_rounding_seconds` 1.0;
  * a CONFIRM pool drawn from the calibration (seed 20265201), excluding every named host and the SELECT
    hosts;
  * register, evaluate, verify, the registration log check, and judge.recompute.
The keys, the custodian store and the copy are deleted afterwards. The hosts are kept in the results, so
that a real custodian excludes them.

**3. Package (in the repository).** `handoff/e1b_c4/` holds:
  * the candidate descriptor and the three baselines;
  * a fresh frozen campaign export, with no selection recorded;
  * the DRAFT decision record;
  * B20_R50's pilot summary and power analyses;
  * the rehearsal summary and every host the builder named, in files of at most 500 hosts;
  * a package index.

**Reading.**
  * SUPPORTED with the judge agreeing means only that the opt-in C4 path works end to end on this family.
    The rehearsal licenses nothing. One operator plays every role, and the builder froze the record.
  * A SUPPORTED claim would be scoped to the DSL baselines. On these settings an exact C4 MIP is optimal
    within 2 s and dominates E1b (B20_R50; B20R33-OPEN-1).
  * INVALID or NOT_SUPPORTED is recorded as it comes, with no re-run under the same seed.

**Development look (disclosed; evidence/e1b_c4_package_b20r52/development_look_hosts.json).** A smoke run of
this path ran in process, with study `e1b-c4` adopted by patching calibration.load for that study only. It
used 3 SELECT hosts, a 6-host power stub, and the reference at **120 s**, as B20_R43 used.
  * SELECT chose low_cycle_tm.
  * The 6-host panel came out **INVALID**: one reference was UNSUPPORTED at 120 s. The candidate was 4/1/0,
    and the judge agreed.
  * The cause: on two of the 6 hosts, which are denser than their settings' means, the tree route needed
    105 s and over 120 s. The seed made no difference: the evaluator's seed and the candidate's witness
    gave identical searches.
  * At 600 s the open host was certified in 221 s (3,429 nodes).
  * In B20_R50's pilot every reference took about 4 s, because it was seeded with the best arm witness,
    including the exact MIP's optimal one.
  * Hence the reference budget here is 600 s. The package step wrote its files with no problems in the
    decision record.
These 9 hosts are disclosed and go into the addenda.
"""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis import candidates as C1  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.kernel.analysis import plan_core  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402

C4 = RD.C4
R50 = ROOT / 'evidence' / 'e1b_c4_readiness_b20r50'
C4_PACKAGE = ROOT / 'evidence' / 'c4_generator_b20r46' / 'package.json'
RECORD_NAME = 'calibration_c4_host_v2_e1_hard_v2_c4tree_draft.json'
STUDY, CONFIRM_SEED, CAMPAIGN_SEED, PACKAGE_SEED, SELECT_TASKS = 'e1b-c4', 20265201, 20265211, 20265221, 30
OPERATOR = 'BUILDER_REHEARSAL_NOT_INDEPENDENT'
E1B_PROFILE = RD.PROFILE
CHUNK = 500     # hosts per exposure file: exposure.extract_hosts screens at most 10^6 JSON nodes per source


def host_chunks(directory, prefix, tasks):
    """Write `tasks` as JSON files of at most CHUNK hosts (dense hosts exceed the screener's node limit in one
    file); returns the file names."""
    names = []
    for i in range(0, len(tasks), CHUNK):
        name = f'{prefix}_part_{i // CHUNK + 1:02d}.json'
        (Path(directory) / name).write_bytes(canonical([t.model_dump(mode='json') for t in tasks[i:i + CHUNK]]))
        names.append(name)
    return names


def reference_spec():
    return {'route': 'generated-rows-tree-c4-v1', 'package_sha256': digest(json.loads(C4_PACKAGE.read_text())), 'seconds': 600,
            'separation_seconds': 15, 'max_rows': 50000, 'max_total': 80000, 'order': 'dense-first', 'enumerator': 'fast',
            'lp_rounding_seconds': 1.0}


def arms():
    """E1b's C4 candidate and its three time-matched DSL baselines (B20_R23/R50), under the E1b profile."""
    a = RD.arms(C4)
    cand = a.pop('candidate')
    base = dict(sorted(a.items()))
    if C1.descriptor_problems(cand, domain=C4):
        raise RuntimeError('the E1b C4 candidate does not rebuild')
    import b20r50_e1b_c4_readiness as M
    if cand['descriptor_id'] != M.arms()['candidate']['descriptor_id']:
        raise RuntimeError('the candidate is not the one B20_R50 measured')
    from genesis import candidate_registry as CREG
    for n, desc in base.items():
        if CREG.descriptor_problems(desc, domain=C4) or desc['resource_profile'] != cand['resource_profile']:
            raise RuntimeError(f'baseline {n} does not rebuild under the candidate profile')
    return cand, base


# ------------------------------------------------------------------ 1. calibration record

def calibration_record():
    r50 = json.loads((R50 / 'calibration_record.json').read_text())
    hosts = json.loads((R50 / 'calibration_hosts.json').read_text())
    rows = [json.loads(l) for l in (R50 / 'calibration_rows.jsonl').read_text().splitlines() if l.strip()]
    rule = CAL.SELECTION_RULE_E1_HARD_V2_C4TREE_DRAFT
    if r50['rule'] != rule:
        raise RuntimeError('B20_R50 used another rule than the registered draft')
    settings = []
    for s in hosts['settings']:
        g = r50['grid'][s['index']]
        srows = [{'task_sha256': r['task_sha256'], 'edges': r['edges'], 'baselines': r['baselines'],
                  'baseline_cpu_ns': {n: a['cpu_ns'] for n, a in sorted(r['baseline_runs'].items())},
                  'reference': r['reference'], 'reference_seconds': r['reference_seconds']}
                 for r in rows if r['setting'] == s['index']]
        summary = CAL.summarize(srows, rule)
        settings.append({'index': s['index'], 'family': g['family'], 'params': g['params'], 'generator': s['generator'],
                         'rows': srows, 'summary': summary, 'ineligible_because': CAL.eligible(summary, rule)})
    record = {'schema': CAL.SCHEMA, 'domain': C4, 'derived_from': 'evidence/e1b_c4_readiness_b20r50 (B20_R50 Part A)',
              'seed': r50['seed'], 'splits_used': ['DEV'], 'rule': rule,
              'limits': {'profile': E1B_PROFILE, 'search_cpu_seconds': RD.SEARCH_S},
              'baselines': {'dsl_time_matched': ['exchange', 'low_cycle', 'multistart']},
              'reference_seconds': rule['measurement']['reference_seconds'], 'tasks_per_setting': r50['tasks_per_setting'],
              'grid': r50['grid'], 'settings': settings, 'selected': CAL.select(settings, rule),
              'task_sha256s': r50['task_sha256s'],
              'note': ('DEV material only (B20_R50 Part A rows, copied, not re-measured); DRAFT rule; '
                       'no study adopts this record')}
    problems = CAL.record_problems(record)
    if problems:
        raise RuntimeError(f'calibration record: {problems}')
    if [(x['family'], x['params']) for x in record['selected']] != [(x['family'], x['params']) for x in r50['selected']]:
        raise RuntimeError('the record does not select what B20_R50 selected')
    return record


# ------------------------------------------------------------------ 2. rehearsal (in the copy)

def draft(cand, power, record, base):
    from genesis.dsl import baseline_programs
    from genesis.kernel import replay_contracts as RC
    d = R11.draft_record()
    settings = ', '.join(f"{s['family']} {s['params']}" for s in record['selected'])
    ref = reference_spec()
    cal = (f"the {STUDY} study calibration (rule {record['rule']['name']}, record SHA-256 {digest(record)[:16]}, "
           f"settings {settings})")
    return DR.build(
        plan_core_dict=plan_core(R24.plan(C4)),
        power=power,
        exact_claim=('The construction-pipeline candidate (descriptor ' + cand['descriptor_id'][:16] + ': '
                     'construct-pipeline-v1 with E1b\'s frozen parameters, LP-ordered greedy with LP-perturbed restarts, '
                     '2.0 CPU s of search) scores more edges than the strongest time-matched fixed DSL baseline (2.0 CPU s '
                     'of restarts), selected by the custodian on its private SELECT panel, on a custodian-held CONFIRM '
                     'panel of ' + C4 + ' hosts drawn from ' + cal + ', with optima certified by the C4 tree reference '
                     '(' + ref['route'] + ', theory package SHA-256 ' + ref['package_sha256'][:16] + '), by at least the '
                     'minimum useful effect, under the registered analysis.'),
        capability_changes=('Candidate: builder-written LP-guided construction (discovery/construct.py, B20_RX3) run as '
                            'the data-only candidate kind construct-pipeline-v1 (B20_R23), unchanged. Evaluator: the C4 '
                            'tree reference over Lean-checked transferred rows (B20_R46-R51 wiring, evaluation request v5); '
                            'every arm in the OCI sandbox through the trusted runner.'),
        permissible_information=d['permissible_information'],
        baselines={'comparator': ('the strongest time-matched fixed DSL baseline (dsl-time-matched-v1, 2.0 CPU s of '
                                  'restarts) on the custodian SELECT panel (custodian.select_comparator)'),
                   'all_fixed_baselines': sorted(f'{n} (time-matched)' for n in baseline_programs()),
                   'registered_interventions': RC.INTERVENTIONS[('construct-pipeline-v1', ('init',))]['meaning'],
                   'strong_baseline_note': ('an exact C4 MIP (HiGHS over the 4-cycle rows) is optimal within 2 s on '
                                            'these settings and dominates the candidate (B20_R50, descriptive); it is '
                                            'not a registered comparator, so the claim is scoped to the DSL baselines'),
                   'not_a_competitor': ('the C4 tree reference (branch and bound over Lean-checked rows with exact '
                                        'LP-dual leaves) is evaluator ground truth')},
        total_budget={'profile': cand['resource_profile'], 'search_seconds_per_arm': RD.SEARCH_S, 'arms': 2,
                      'reference_seconds_per_task': ref['seconds'],
                      'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every DEV '
                         'panel named in the evidence and every host the builder generated (handoff/e1b_c4/'
                         'exposure_hosts_all_part_*.json); a SELECT or CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' A comparator not selected by the custodian on its SELECT panel. '
                            f'A panel not drawn from the {STUDY} study calibration named in the claim. A reference other '
                            'than the route the request names.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for ' + C4 + ' hosts from the ' + STUDY +
                            ' calibrated settings on that panel only, against time-matched fixed DSL baselines. Not '
                            'beyond an exact MIP, not better-improver (GV4), transfer, novelty, or any statement about '
                            'other families.'),
        status='DRAFT')


def rehearse(out, log, *, power=None, select_tasks=SELECT_TASKS):
    """Runs inside the throwaway copy, where configs/dev_calibration.json adopts study 'e1b-c4' (REHEARSAL).
    The keyword arguments exist for the disclosed development smoke run only; the run uses the defaults."""
    from genesis import custody_records as CRec
    from genesis.campaign import Campaign
    from genesis.cli import descriptor_request_bundle, export_replication, freeze_candidate_descriptor, \
        record_comparator_selection
    from genesis.custodian import evaluate, register, registration_log, select_comparator, verify
    from genesis.judge import recompute
    from genesis.models import Config
    record = CAL.load(C4, ROOT, study=STUDY)
    cand, base = arms()
    power = power or json.loads((R50 / 'power_analysis_centred_readiness.json').read_text())
    total = power['chosen']['total_tasks']
    excluded, scan, named = R24.exposure(log)
    work = out / 'work'
    if work.exists():
        shutil.rmtree(work)
    camp_root = work / 'campaign'
    Campaign.initialize(camp_root, Config(domain=C4, seed=CAMPAIGN_SEED, generations=1, tasks_per_panel=4,
                                          proposals_per_epoch=2, research_trials=8))
    with Campaign(camp_root) as camp:
        camp.run()
        cv = freeze_candidate_descriptor(camp, cand, origin='B20_R52 E1b-C4 candidate (REHEARSAL)')
        export_replication(camp_root, camp_root / 'exports' / 'campaign_export.zip', store=camp.store)
    reh = work / 'rehearsal'
    reh.mkdir(parents=True)
    reh.chmod(0o700)
    prereg, cust = R11.keyfile(reh, 'prereg_FIXTURE'), R11.keyfile(reh, 'custodian_FIXTURE')
    files = host_chunks(reh, 'builder_named_hosts', list(named))
    for name in files:
        (reh / name).chmod(0o600)
    manifest = reh / 'exposure_manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': [
        {'kind': 'json', 'path': name, 'label': f'every host the builder named or generated ({name})'}
        for name in files]}))
    manifest.chmod(0o600)
    t0 = time.monotonic()
    sel = select_comparator(reh, camp_root / 'exports' / 'campaign_export.zip', base, cust[0], OPERATOR,
                            exposure_manifest=manifest, task_count=select_tasks, study=STUDY)
    sp = verify(sel, cust[1])
    select_tasks = json.loads((reh / 'comparator_selections' / f'{digest(sel)}.json').read_text())['tasks']
    log(f'SELECT panel totals {sp["totals"]} -> comparator {sp["selected"]} ({time.monotonic() - t0:.0f} s)')
    with Campaign(camp_root) as camp:
        record_comparator_selection(camp, sel)
    d2 = draft(cand, power, record, base)
    with Campaign(camp_root) as camp:
        reh_rec = copy.deepcopy(d2)
        reh_rec['exact_claim'] = 'REHEARSAL (same operator, fixture keys, not a reviewed decision): ' + d2['exact_claim']
        frozen, h = DR.freeze(reh_rec)
        p = dict(d2['analysis_plan_core'], decision_record_sha256=h)
        path = descriptor_request_bundle(camp, total, analysis=p, claim_id='e1b-c4-rehearsal-b20r52',
                                         statement='REHEARSAL: ' + d2['exact_claim'],
                                         scope=f'rehearsal panel of {total} {C4} hosts (same operator)',
                                         reference=reference_spec())
        request = json.loads(path.read_text())
    select_ids = RD.identities([GraphTask.model_validate_json(canonical(t)) for t in select_tasks])
    tasks, _ = CAL.calibrated_panel(record, CONFIRM_SEED, total, 'CONFIRM', excluded=set(excluded) | select_ids)
    pool = reh / 'rehearsal_pool.json'
    pool.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
    t0 = time.monotonic()
    anchor = register(reh, request, prereg[0], OPERATOR, exposure_manifest=manifest,
                      campaign_export=camp_root / 'exports' / 'campaign_export.zip', pool=pool, decision_record=frozen)
    log(f'registered the v5 request ({total} hosts); evaluating')
    receipt = evaluate(reh, digest(request), pool, cust[0], OPERATOR)
    rp = verify(receipt, cust[1])
    lg, problems = CRec.check_log(registration_log(reh, cust[0]), cust[1], verify)
    judged = recompute(reh / 'evaluations' / digest(request), request, receipt, registration_log_entries=lg['entries'])
    log(f'rehearsal {rp["outcome"]} (W/L/T {rp["wins"]}/{rp["losses"]}/{rp["ties"]}), estimate '
        f'{rp["analysis_result"].get("estimate")}, cost ratio {rp["analysis_result"].get("cost_ratio")}, judge agrees '
        f'{judged["agrees"]} ({time.monotonic() - t0:.0f} s)')
    from genesis.store import Store
    refs = {'methods': {}, 'unsupported': 0, 'wall_s': []}
    with Store(reh / 'evaluations' / digest(request)) as s:
        for _, req_h, rec_h in s.db.execute('SELECT status,request,receipt FROM attempts'):
            a, r = s.get(req_h), s.get(rec_h)
            if a.get('kind') == 'exact-check':
                if r['status'] == 'UNSUPPORTED':
                    refs['unsupported'] += 1
                else:
                    m = r['result']['method']
                    refs['methods'][m] = refs['methods'].get(m, 0) + 1
                refs['wall_s'].append(round(r['wall_ns'] / 1e9, 3))
    summary = {'label': 'REHEARSAL_SAME_OPERATOR_FIXTURE_KEYS: not independent, not a CONFIRM result, licenses nothing',
               'adoption_in_the_copy': {'study': STUDY, 'rule': record['rule']['name'], 'record_sha256': digest(record),
                                        'note': 'configs/dev_calibration.json of a throwaway copy only'},
               'code_identity': code_identity(ROOT)['sha256'], 'campaign_candidate_version': cv,
               'comparator_selection': sp, 'request_sha256': digest(request), 'request_schema': request['schema'],
               'reference': request['reference'], 'decision_record_draft': d2, 'decision_record_rehearsal_sha256': h,
               'receipt_payload': rp, 'anchor_payload': anchor['payload'], 'reference_methods': refs,
               'judge': {k: judged.get(k) for k in ('agrees', 'problems', 'witnesses_rechecked', 'recomputed_outcome')},
               'resource_account': judged.get('resource_account'), 'fairness': judged.get('fairness'),
               'log_problems': problems, 'select_hosts': select_tasks,
               'confirm_hosts': [t.model_dump(mode='json') for t in tasks], 'exposure_scan': scan}
    R11.dump(out / 'rehearsal_summary.json', summary)
    R11.dump(out / 'rehearsal_receipt.json', receipt)
    R11.dump(out / 'decision_record_DRAFT.json', d2)
    shutil.rmtree(work)
    return summary


def make_copy(out, record, log):
    copy_root = Path('/tmp') / 'genesis-e1b-c4-rehearsal-b20r52'
    if copy_root.exists():
        shutil.rmtree(copy_root)
    copy_root.mkdir()
    tar = subprocess.run(['git', '-C', str(ROOT), 'archive', 'HEAD'], check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', str(copy_root)], input=tar, check=True)
    rel = Path('evidence') / 'e1b_c4_package_b20r52' / RECORD_NAME
    (copy_root / rel).parent.mkdir(parents=True, exist_ok=True)
    (copy_root / rel).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    cfg_path = copy_root / CAL.CONFIG
    cfg = json.loads(cfg_path.read_text())
    cfg.setdefault('studies', {})[STUDY] = {C4: {'record': str(rel), 'sha256': digest(record), 'rule': record['rule']['name'],
                                                'adopted_by': 'REHEARSAL in a throwaway copy (B20_R52); not an adoption'}}
    cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + '\n')
    if code_identity(copy_root)['sha256'] != code_identity(ROOT)['sha256']:
        raise RuntimeError('the copy does not have this commit\'s code identity (is the work tree clean?)')
    log(f'throwaway copy at {copy_root}; study {STUDY} adopted there only')
    return copy_root


# ------------------------------------------------------------------ 3. package (in the repository)

def package(out, record, rehearsal, log, dest=None):
    from genesis.campaign import Campaign
    from genesis.cli import export_replication, freeze_candidate_descriptor
    from genesis.models import Config
    d = dest or ROOT / 'handoff' / 'e1b_c4'
    d.mkdir(parents=True, exist_ok=True)
    cand, base = arms()
    work = out / 'package_work'
    if work.exists():
        shutil.rmtree(work)
    root = work / 'campaign'
    Campaign.initialize(root, Config(domain=C4, seed=PACKAGE_SEED, generations=1, tasks_per_panel=4, proposals_per_epoch=2,
                                     research_trials=8))
    with Campaign(root) as c:
        c.run()
        cv = freeze_candidate_descriptor(c, cand, origin='B20_R52 E1b-C4 package: E1b\'s frozen parameters for c4_host_v2')
        export_replication(root, root / 'exports' / 'campaign_export.zip', store=c.store)
    shutil.copy(root / 'exports' / 'campaign_export.zip', d / 'campaign_export.zip')
    shutil.rmtree(work)
    R11.dump(d / 'candidate_descriptor.json', cand)
    R11.dump(d / 'baselines.json', base)
    R11.dump(d / 'decision_record_DRAFT.json', rehearsal['decision_record_draft'])
    R11.dump(d / 'reference_route.json', reference_spec())
    for name in ('pilot_summary.json', 'power_analysis_centred_readiness.json', 'power_analysis_centred_ablation.json',
                 'power_analysis_centred_placebo.json'):
        shutil.copy(R50 / name, d / name.replace('.json', '_b20r50.json'))
    keep = {k: v for k, v in rehearsal.items() if k not in ('select_hosts', 'confirm_hosts', 'decision_record_draft')}
    R11.dump(d / 'rehearsal_summary_b20r52.json', keep)
    named, scan = RD.named_hosts()
    extra = [GraphTask.model_validate_json(canonical(t)) for t in rehearsal['select_hosts'] + rehearsal['confirm_hosts']]
    allh, seen = [], set()
    for t in list(named) + extra:
        i = next(iter(RD.identities([t])))
        if i not in seen:
            seen.add(i)
            allh.append(t)
    for old in d.glob('exposure_hosts_all*.json'):
        old.unlink()
    parts = host_chunks(d, 'exposure_hosts_all', sorted(allh, key=lambda t: (t.domain, t.task_id)))
    frozen, _ = DR.freeze(rehearsal['decision_record_draft'])
    index = {'schema': 'genesis-handoff-package-index-v1', 'package': 'E1b-C4 (DRAFT)', 'domain': C4,
             'candidate_descriptor_id': cand['descriptor_id'], 'campaign_candidate_version': cv,
             'baselines': {n: b['descriptor_id'] for n, b in base.items()},
             'calibration': {'record': f'evidence/e1b_c4_package_b20r52/{RECORD_NAME}', 'sha256': digest(record),
                             'rule': record['rule']['name'], 'selected': record['selected'],
                             'adopted': False},
             'reference_route': reference_spec(), 'decision_record_draft_sha256': digest(rehearsal['decision_record_draft']),
             'decision_record_problems_if_frozen': DR.problems(frozen),
             'exposure_hosts_all': {'hosts': len(allh), 'files': parts, 'scan': scan},
             'rehearsal': {'outcome': rehearsal['receipt_payload']['outcome'], 'judge_agrees': rehearsal['judge']['agrees'],
                           'comparator': rehearsal['comparator_selection']['selected'],
                           'request_sha256': rehearsal['request_sha256']},
             'code_identity': code_identity(ROOT)['sha256'], 'status': 'DRAFT; not registered with any custodian'}
    R11.dump(d / 'package_index.json', index)
    log(f'package written: {len(allh)} exposure hosts; decision record problems if frozen: '
        f'{index["decision_record_problems_if_frozen"]}')
    return index


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
    if '--rehearse' in argv:
        log(f'rehearsal in the copy {ROOT} (pid {os.getpid()})')
        rehearse(out, log)
        return 0
    from genesis.verification.tools import tool
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim')))
    record = calibration_record()
    R11.dump(out / RECORD_NAME, record)
    log(f'calibration record {digest(record)[:16]}: selected {[s["index"] for s in record["selected"]]}')
    summary_path = out / 'rehearsal_summary.json'
    if not summary_path.exists():
        copy_root = make_copy(out, record, log)
        env = dict(os.environ, PYTHONPATH=str(copy_root / 'src'))
        rc = subprocess.run([sys.executable, str(copy_root / 'scripts' / Path(__file__).name), str(out), '--rehearse'],
                            cwd=str(copy_root), env=env).returncode
        shutil.rmtree(copy_root)
        if rc != 0:
            raise RuntimeError(f'the rehearsal failed with exit code {rc}')
    rehearsal = json.loads(summary_path.read_text())
    index = package(out, record, rehearsal, log)
    R11.dump(out / 'summary.json', {'schema': 'genesis-b20r52-e1b-c4-package-v1', 'calibration_record_sha256': digest(record),
                                    'rehearsal_outcome': rehearsal['receipt_payload']['outcome'],
                                    'judge_agrees': rehearsal['judge']['agrees'], 'package_index': index,
                                    'code_identity': code_identity(ROOT)['sha256'],
                                    'status': 'DRAFT package and same-operator rehearsal; licenses nothing'})
    log(f'done: rehearsal {rehearsal["receipt_payload"]["outcome"]}, judge agrees {rehearsal["judge"]["agrees"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
