#!/usr/bin/env python3
"""B20_R43: the E1d DRAFT package and a same-operator rehearsal through the v5 path (GV3 path;
B20R41-OPEN-1). DEV, builder-run, fixture keys. Nothing is adopted or registered with any
custodian.

    b20r43_e1d_package.py OUT_DIR                     run from the repository
    (it re-runs itself as  b20r43_e1d_package.py OUT_DIR --rehearse  inside a throwaway copy)

**Why.** B20_R41 found E1's frozen candidate READY_FOR_REVIEW on DEV in a dense family: it beats
every registered baseline, including an exact MIP at four times its budget. B20_R42 wired the
pieces a custodian would need, opt-in:
  * registry-v2 baselines;
  * the exact-baseline policy per rule;
  * evaluation request v5 with the generated-rows reference and its custody.
This step does for E1d what B20_R24 did for E1 and E1b. It writes the package a reviewer would
sign off, and it runs the whole custody path once with fixture keys, so that the reviewer sees the
path work end to end before deciding. Everything below was fixed before running.

**1. Calibration record (in the repository).** B20_R41's Part A rows, rewritten as a
`genesis-dev-calibration-v1` record under the DRAFT rule `e1-hard-v3-draft`
(calibration.SELECTION_RULE_E1_HARD_V3_DRAFT).
  * The rows are copied, not re-measured.
  * calibration.record_problems must be [], and the selection must equal B20_R41's.
  * B20_R41's evidence is not rewritten. The record is a new file here.

**2. Rehearsal (in a throwaway copy).** The copy is `git archive HEAD`, so its code identity is this
commit's. In the copy only, `configs/dev_calibration.json` adopts the record as study `e1d`, which
stands in for the reviewer's adoption, and the record is placed in the copy's evidence. Then:
  * a fresh frozen DEV campaign (1 generation), with E1's frozen candidate descriptor frozen in it
    (`handoff/e1/candidate_descriptor.json`, unchanged);
  * fixture keys and an exposure manifest of every host the builder named;
  * the custodian's SELECT on 30 private hosts drawn from the `e1d` calibration, among five
    baselines under E1's profile (2 CPU s, 2048 MiB, 10 s wall, 1000 queries):
      - E1's three frozen time-matched DSL baselines;
      - `milp-highs-v1` at 0.5 s;
      - `milp-highs-v1` at 2.0 s;
  * the DRAFT decision record for E1d, a REHEARSAL-labelled frozen copy, and a v5 request whose
    task count is the B20_R41 power analysis's chosen total (240 = 80 per stratum).
    Its reference is `generated-rows-v1` with the B20_R37 package, 120 s, and B20_R41's route
    limits including `lp_rounding_seconds` 1.0;
  * a CONFIRM pool drawn from the calibration (seed 20264301), excluding every named host and the
    SELECT hosts;
  * register, evaluate, verify, the registration log check, and judge.recompute.
The keys, the custodian store and the copy are deleted afterwards. The hosts are kept in the
results, so that a real custodian excludes them.

**3. Package (in the repository).** `handoff/e1d/` holds:
  * the candidate descriptor and the five baselines;
  * a fresh frozen campaign export, with no selection recorded;
  * the DRAFT decision record;
  * B20_R41's pilot summary and power analysis;
  * the rehearsal summary and every host the builder named, as tasks, in files of at most 500 hosts
    (the exposure screener walks at most 10^6 JSON nodes per source, which one file of every dense
    host would exceed);
  * a package index.

**Development look (disclosed; evidence/e1d_package_b20r43/development_look_hosts.json).** A smoke run
of the rehearsal path ran in-process, with study `e1d` adopted by patching calibration.load for that
study only. It used 3 SELECT and 6 CONFIRM hosts and a 6-host power stub. Its 9 hosts are disclosed
and go into the addenda.
  * SELECT chose the MIP at 2.0 s.
  * The 6-host panel came out NOT_SUPPORTED (4/0/2, +9.2), and the judge agreed.
  * All 6 optima were certified by the LP over generated rows.
  * The package step wrote its files with no problems in the decision record.
  * It found one defect, now fixed: a single exposure file of every named host exceeded the
    screener's node limit.

**Reading.**
  * SUPPORTED with the judge agreeing means only this: the opt-in path works end to end on this
    family. The rehearsal licenses nothing. One operator plays every role, and the builder froze
    the record.
  * INVALID or NOT_SUPPORTED is recorded as it comes, with no re-run under the same seed.
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
from genesis import candidates_v2 as C2  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.kernel.analysis import plan_core  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402

TF = RD.TF
R41 = ROOT / 'evidence' / 'e1d_readiness_b20r41'
R37_PACKAGE = ROOT / 'evidence' / 'generator_v2_b20r37' / 'package.json'
RECORD_NAME = 'calibration_triangle_free_host_v1_e1_hard_v3_draft.json'
STUDY, CONFIRM_SEED, CAMPAIGN_SEED, PACKAGE_SEED, SELECT_TASKS = 'e1d', 20264301, 20264311, 20264321, 30
OPERATOR = 'BUILDER_REHEARSAL_NOT_INDEPENDENT'
E1_PROFILE = R11.PROFILE
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
    return {'route': 'generated-rows-v1', 'package_sha256': digest(json.loads(R37_PACKAGE.read_text())), 'seconds': 120,
            'separation_seconds': 15, 'max_rows': 50000, 'max_total': 80000, 'order': 'dense-first', 'enumerator': 'fast',
            'lp_rounding_seconds': 1.0}


def arms():
    d = ROOT / 'handoff' / 'e1'
    cand = json.loads((d / 'candidate_descriptor.json').read_text())
    base = dict(sorted(json.loads((d / 'time_matched_baselines.json').read_text()).items()))
    base['milp_highs_tm'] = C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': 0.5}, **E1_PROFILE)
    base['milp_highs_4x'] = C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': 2.0}, **E1_PROFILE)
    if C1.descriptor_problems(cand, domain=TF):
        raise RuntimeError('the frozen E1 candidate does not rebuild')
    from genesis import candidate_registry as CREG
    for n, desc in base.items():
        if CREG.descriptor_problems(desc, domain=TF) or desc['resource_profile'] != cand['resource_profile']:
            raise RuntimeError(f'baseline {n} does not rebuild under the candidate profile')
    return cand, base


# ------------------------------------------------------------------ 1. calibration record

def calibration_record():
    r41 = json.loads((R41 / 'calibration_record.json').read_text())
    hosts = json.loads((R41 / 'calibration_hosts.json').read_text())
    rows = [json.loads(l) for l in (R41 / 'calibration_rows.jsonl').read_text().splitlines() if l.strip()]
    rule = CAL.SELECTION_RULE_E1_HARD_V3_DRAFT
    if r41['rule'] != rule:
        raise RuntimeError('B20_R41 used another rule than the registered draft')
    settings = []
    for s in hosts['settings']:
        srows = [{'task_sha256': r['task_sha256'], 'edges': r['edges'], 'baselines': r['baselines'],
                  'baseline_cpu_ns': {n: a['cpu_ns'] for n, a in sorted(r['baseline_runs'].items())},
                  'reference': r['reference'], 'reference_seconds': r['reference_seconds']}
                 for r in rows if r['setting'] == s['index']]
        summary = CAL.summarize(srows, rule)
        settings.append({'index': s['index'], 'family': s['family'], 'params': s['params'], 'generator': s['generator'],
                         'rows': srows, 'summary': summary, 'ineligible_because': CAL.eligible(summary, rule)})
    record = {'schema': CAL.SCHEMA, 'domain': TF, 'derived_from': 'evidence/e1d_readiness_b20r41 (B20_R41 Part A)',
              'seed': r41['seed'], 'splits_used': ['DEV'], 'rule': rule,
              'limits': {'profile': E1_PROFILE, 'search_cpu_seconds': 0.5},
              'baselines': {'dsl_time_matched': ['exchange', 'low_cycle', 'multistart'],
                            'exact': ['milp-highs-v1 at 0.5 s', 'milp-highs-v1 at 2.0 s']},
              'reference_seconds': rule['measurement']['reference_seconds'], 'tasks_per_setting': r41['tasks_per_setting'],
              'grid': r41['grid'], 'settings': settings, 'selected': CAL.select(settings, rule),
              'task_sha256s': r41['task_sha256s'],
              'note': ('DEV material only (B20_R41 Part A rows, copied, not re-measured); DRAFT rule; '
                       'no study adopts this record')}
    problems = CAL.record_problems(record)
    if problems:
        raise RuntimeError(f'calibration record: {problems}')
    if record['selected'] != r41['selected']:
        raise RuntimeError('the record does not select what B20_R41 selected')
    return record


# ------------------------------------------------------------------ 2. rehearsal (in the copy)

def draft(cand, power, record, base):
    d = R11.draft_record()
    settings = ', '.join(f"{s['family']} {s['params']}" for s in record['selected'])
    ref = reference_spec()
    cal = (f"the {STUDY} study calibration (rule {record['rule']['name']}, record SHA-256 {digest(record)[:16]}, "
           f"settings {settings})")
    return DR.build(
        plan_core_dict=plan_core(R24.plan(TF)),
        power=power,
        exact_claim=('The frozen representation-and-repair candidate (descriptor ' + cand['descriptor_id'][:16] +
                     ', cut representation cross_2, 0.5 CPU s of search) scores more edges than the strongest of five '
                     'registered baselines (the three time-matched fixed DSL programs at 0.5 CPU s, and the exact MILP '
                     'milp-highs-v1 at 0.5 and at 2.0 CPU s), selected by the custodian on its private SELECT panel, '
                     'on a custodian-held CONFIRM panel of ' + TF + ' hosts drawn from ' + cal + ', with optima '
                     'certified by the generated-rows reference (' + ref['route'] + ', theory package SHA-256 ' +
                     ref['package_sha256'][:16] + '), by at least the minimum useful effect, under the registered '
                     'analysis.'),
        capability_changes=('Candidate: B18 W10 representation grammar (cross_2) with greedy repair, unchanged from E1. '
                            'Evaluator: registry-v2 exact baselines and the generated-rows reference over Lean-checked '
                            'rows (B20_R39/R42 wiring, evaluation request v5); every arm in the OCI sandbox through the '
                            'trusted runners.'),
        permissible_information=d['permissible_information'],
        baselines={'comparator': ('the strongest of the five registered baselines on the custodian SELECT panel '
                                  '(custodian.select_comparator under rule e1-hard-v3-draft)'),
                   'all_registered_baselines': sorted(base),
                   'exact_baseline_note': ('milp-highs-v1 is HiGHS through the pinned scipy, one core, best incumbent '
                                           'at its time limit; at 2.0 s it has four times the candidate search budget'),
                   'not_a_competitor': ('the generated-rows reference (LP over Lean-checked rows, rounding of its own '
                                        'LP, SAT/DRAT) is evaluator ground truth; it solves these hosts exactly in about '
                                        '20 s of wall time, which the claim must state')},
        total_budget={'profile': cand['resource_profile'], 'search_seconds_per_arm': {'candidate': 0.5,
                      'dsl_baselines': 0.5, 'milp_highs_tm': 0.5, 'milp_highs_4x': 2.0}, 'arms': 2,
                      'reference_seconds_per_task': ref['seconds'],
                      'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every DEV '
                         'panel named in the evidence and every host the builder generated (handoff/e1d/'
                         'exposure_hosts_all_part_*.json); a SELECT or CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' A comparator not selected by the custodian on its SELECT panel. '
                            f'A panel not drawn from the {STUDY} study calibration named in the claim. A reference other '
                            'than the route the request names.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for ' + TF + ' hosts from the ' + STUDY +
                            ' calibrated settings on that panel only, against the five registered baselines including '
                            'an exact MILP at four times the candidate budget. Not better-improver, transfer, novelty, '
                            'or any statement about other families or other exact methods.'),
        status='DRAFT')


def rehearse(out, log, *, power=None, select_tasks=SELECT_TASKS):
    """Runs inside the throwaway copy, where configs/dev_calibration.json adopts study 'e1d' (REHEARSAL).
    The keyword arguments exist for the disclosed development smoke run only; the run uses the defaults."""
    from genesis import custody_records as CRec
    from genesis.campaign import Campaign
    from genesis.cli import descriptor_request_bundle, export_replication, freeze_candidate_descriptor, \
        record_comparator_selection
    from genesis.custodian import evaluate, register, registration_log, select_comparator, verify
    from genesis.judge import recompute
    from genesis.models import Config
    record = CAL.load(TF, ROOT, study=STUDY)
    cand, base = arms()
    power = power or json.loads((R41 / 'power_analysis_centred.json').read_text())
    total = power['chosen']['total_tasks']
    excluded, scan, named = R24.exposure(log)
    work = out / 'work'
    if work.exists():
        shutil.rmtree(work)
    camp_root = work / 'campaign'
    Campaign.initialize(camp_root, Config(domain=TF, seed=CAMPAIGN_SEED, generations=1, tasks_per_panel=4,
                                          proposals_per_epoch=2, research_trials=8))
    with Campaign(camp_root) as camp:
        camp.run()
        cv = freeze_candidate_descriptor(camp, cand, origin='B20_R43 E1d candidate = the frozen E1 candidate (REHEARSAL)')
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
        path = descriptor_request_bundle(camp, total, analysis=p, claim_id='e1d-rehearsal-b20r43',
                                         statement='REHEARSAL: ' + d2['exact_claim'],
                                         scope=f'rehearsal panel of {total} {TF} hosts (same operator)',
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
    copy_root = Path('/tmp') / 'genesis-e1d-rehearsal-b20r43'
    if copy_root.exists():
        shutil.rmtree(copy_root)
    copy_root.mkdir()
    tar = subprocess.run(['git', '-C', str(ROOT), 'archive', 'HEAD'], check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', str(copy_root)], input=tar, check=True)
    rel = Path('evidence') / 'e1d_package_b20r43' / RECORD_NAME
    (copy_root / rel).parent.mkdir(parents=True, exist_ok=True)
    (copy_root / rel).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    cfg_path = copy_root / CAL.CONFIG
    cfg = json.loads(cfg_path.read_text())
    cfg.setdefault('studies', {})[STUDY] = {TF: {'record': str(rel), 'sha256': digest(record), 'rule': record['rule']['name'],
                                                'adopted_by': 'REHEARSAL in a throwaway copy (B20_R43); not an adoption'}}
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
    d = dest or ROOT / 'handoff' / 'e1d'
    d.mkdir(parents=True, exist_ok=True)
    cand, base = arms()
    work = out / 'package_work'
    if work.exists():
        shutil.rmtree(work)
    root = work / 'campaign'
    Campaign.initialize(root, Config(domain=TF, seed=PACKAGE_SEED, generations=1, tasks_per_panel=4, proposals_per_epoch=2,
                                     research_trials=8))
    with Campaign(root) as c:
        c.run()
        cv = freeze_candidate_descriptor(c, cand, origin='B20_R43 E1d package: the frozen E1 candidate')
        export_replication(root, root / 'exports' / 'campaign_export.zip', store=c.store)
    shutil.copy(root / 'exports' / 'campaign_export.zip', d / 'campaign_export.zip')
    shutil.rmtree(work)
    R11.dump(d / 'candidate_descriptor.json', cand)
    R11.dump(d / 'baselines.json', base)
    R11.dump(d / 'decision_record_DRAFT.json', rehearsal['decision_record_draft'])
    R11.dump(d / 'reference_route.json', reference_spec())
    for name in ('pilot_summary.json', 'power_analysis_centred.json'):
        shutil.copy(R41 / name, d / name.replace('.json', '_b20r41.json'))
    keep = {k: v for k, v in rehearsal.items() if k not in ('select_hosts', 'confirm_hosts', 'decision_record_draft')}
    R11.dump(d / 'rehearsal_summary_b20r43.json', keep)
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
    index = {'schema': 'genesis-handoff-package-index-v1', 'package': 'E1d (DRAFT)', 'domain': TF,
             'candidate_descriptor_id': cand['descriptor_id'], 'campaign_candidate_version': cv,
             'baselines': {n: b['descriptor_id'] for n, b in base.items()},
             'calibration': {'record': f'evidence/e1d_package_b20r43/{RECORD_NAME}', 'sha256': digest(record),
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
    R11.dump(out / 'summary.json', {'schema': 'genesis-b20r43-e1d-package-v1', 'calibration_record_sha256': digest(record),
                                    'rehearsal_outcome': rehearsal['receipt_payload']['outcome'],
                                    'judge_agrees': rehearsal['judge']['agrees'], 'package_index': index,
                                    'code_identity': code_identity(ROOT)['sha256'],
                                    'status': 'DRAFT package and same-operator rehearsal; licenses nothing'})
    log(f'done: rehearsal {rehearsal["receipt_payload"]["outcome"]}, judge agrees {rehearsal["judge"]["agrees"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
