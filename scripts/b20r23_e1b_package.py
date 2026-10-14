#!/usr/bin/env python3
"""B20_R23: build the E1b handoff package (handoff/e1b/). DRAFT; nothing is registered.

    b20r23_e1b_package.py WORK_DIR

E1b is the better-solver claim of the construct-pipeline-v1 candidate (LP-ordered greedy with
LP-perturbed restarts, 2.0 CPU s) against the strongest time-matched fixed DSL baseline. Its DEV
readiness pilot (evidence/e1b_readiness_b20r23) is READY_FOR_REVIEW on triangle_free_host_v1 and on
c4_host_v2. This script prepares, per domain, what a reviewer and an independent custodian need:

  * the candidate, the three time-matched baselines, and the registered ablation and placebo, as
    descriptors built by the reviewed code of this commit;
  * a real frozen campaign (1 generation, DEV) with the candidate descriptor frozen in it, and its
    replication export;
  * a DRAFT decision record (not frozen) built from the B19 DRAFT plan (the multiplicity family_id
    names the domain, as in the pilot) and the pilot's centred power analysis, plus the problems a
    frozen copy would still have (decision_record.problems with require_frozen=True on a copy);
  * the exposure list: every graph host named in evidence/ and handoff/ (both E1b pilots included)
    and the regenerated E1 exposure set, as tasks;
  * the state of the custodian's SELECT step: it draws from a study calibration ('e1b'), which does not
    exist until a family rule is decided; calibration.load(..., study='e1b') is attempted and its
    refusal recorded.
No rehearsal is run: without a study calibration the SELECT step cannot draw a panel, and nothing is
relaxed to make it.
"""
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
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.kernel import replay_contracts as RC  # noqa: E402
from genesis.kernel.analysis import plan_core  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r12_e1_redo as R12  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402

PKG = ROOT / 'handoff' / 'e1b'
READY = ROOT / 'evidence' / 'e1b_readiness_b20r23'
CAUSAL = ROOT / 'evidence' / 'e1b_causal_readiness_b20r23'
TF, C4 = RD.TF, RD.C4
CAMPAIGN_SEED = {TF: 20262601, C4: 20262611}


def descriptors(domain):
    cand = C.build_descriptor('construct-pipeline-v1', domain, RD.CANDIDATE, **RD.PROFILE)
    tm = {f'{n}_tm': C.build_descriptor('dsl-time-matched-v1', domain, {'program': p.model_dump(mode='json'),
                                                                        'cpu_seconds': RD.SEARCH_S}, **RD.PROFILE)
          for n, p in sorted(baseline_programs().items())}
    iv = {}
    for kind, init in (('ablation', 'random_greedy'), ('placebo', 'lp_shuffled_greedy')):
        d = C.build_descriptor('construct-pipeline-v1', domain, dict(RD.CANDIDATE, init=init), **RD.PROFILE)
        why, path = RC.intervention_problems(kind, cand, d)
        if why or path != ('init',):
            raise RuntimeError(f'{kind}: {why}')
        iv[kind] = d
    return cand, tm, iv


def plan(domain):
    p = dict(R11.draft_record()['analysis_plan_core'], decision_record_sha256='0' * 64)
    p['multiplicity'] = dict(p['multiplicity'], family_id=f'sealed_evaluation:{domain}')
    return p


def draft(domain, cand, power):
    d = R11.draft_record()
    settings = ', '.join(f'{f} n{p["n"]} p{p["p"]}' for _, dom, f, p in RD.SETTINGS if dom == domain)
    return DR.build(
        plan_core_dict=plan_core(plan(domain)), power=power,
        exact_claim=('The frozen construction-pipeline candidate (descriptor ' + cand['descriptor_id'][:16] + ': '
                     'construct-pipeline-v1, LP-ordered greedy with LP-perturbed restarts, 2.0 CPU s of search) scores '
                     'more edges than the strongest time-matched fixed DSL baseline (2.0 CPU s of restarts), selected '
                     'by the custodian on its private SELECT panel, on a custodian-held CONFIRM panel of ' + domain +
                     ' hosts drawn from the E1b study calibration (rule NOT YET DECIDED; pilot settings ' + settings +
                     '), by at least the minimum useful effect, under the registered analysis.'),
        capability_changes=('Candidate: builder-written LP-guided construction (discovery/construct.py, B20_RX3) run as '
                            'the data-only candidate kind construct-pipeline-v1 (B20_R23). The custodian runs every arm '
                            'in the OCI sandbox through the trusted runner; no change to trusted checking.'),
        permissible_information=d['permissible_information'],
        baselines={'comparator': ('the strongest time-matched fixed DSL baseline (dsl-time-matched-v1, 2.0 CPU s of '
                                  'restarts) on the custodian SELECT panel (custodian.select_comparator)'),
                   'all_fixed_baselines': sorted(f'{n} (time-matched)' for n in baseline_programs()),
                   'registered_interventions': RC.INTERVENTIONS[('construct-pipeline-v1', ('init',))]['meaning'],
                   'not_a_competitor': 'the SAT/DRAT or LP reference optimum is evaluator ground truth'},
        total_budget={'profile': RD.PROFILE, 'search_seconds_per_arm': RD.SEARCH_S, 'arms': 2,
                      'reference_seconds_per_task': RD.CERTIFY_S,
                      'equal_accounting': 'one sandbox, one profile, cgroup CPU per arm',
                      'discovery_cost': 'B20_RX3 and RX3b capability pilots, recorded in their evidence',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every DEV '
                         'panel named in the evidence and every host in handoff/e1b/exposure_hosts_all.json; a SELECT '
                         'or CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=d['raw_evidence_custody'], roles=d['roles'],
        rejection_criteria=(d['rejection_criteria'] + ' A comparator not selected by the custodian on its SELECT panel. '
                            'A panel not drawn from the E1b study calibration named in the claim. A candidate '
                            'descriptor other than the frozen one.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for ' + domain + ' hosts from the E1b '
                            'calibrated settings on that panel only, against time-matched fixed DSL baselines. The '
                            'candidate is a builder-written method, so not better-improver (GV4), not research '
                            'ability, transfer, novelty, or any statement about other families.'),
        status='DRAFT')


def campaign(work, domain, cand, log):
    from genesis.campaign import Campaign
    from genesis.cli import export_replication, freeze_candidate_descriptor
    from genesis.models import Config
    root = work / f'campaign_{domain}'
    if root.exists():
        shutil.rmtree(root)
    cfg = Config(domain=domain, seed=CAMPAIGN_SEED[domain], generations=1, tasks_per_panel=4, proposals_per_epoch=2,
                 research_trials=8)
    t0 = time.monotonic()
    Campaign.initialize(root, cfg)
    with Campaign(root) as c:
        c.run()
        cv = freeze_candidate_descriptor(c, cand, origin=('B20_RX3 LP-guided construction (discovery/construct.py) as '
                                                          'construct-pipeline-v1 (B20_R23); E1b readiness pilot '
                                                          'evidence/e1b_readiness_b20r23'))
        export_replication(root, root / 'exports' / 'campaign_export.zip', store=c.store)
    log(f'{domain}: campaign frozen and exported in {time.monotonic() - t0:.0f} s')
    return root / 'exports' / 'campaign_export.zip', cv


def main(argv=None):
    work = Path((argv or sys.argv[1:])[0])
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)  # noqa: E731
    ready = json.loads((READY / 'summary.json').read_text())
    if PKG.exists():
        shutil.rmtree(PKG)
    PKG.mkdir(parents=True)
    index = {'schema': 'genesis-e1b-package-v1', 'status': 'DRAFT; not registered; licenses nothing', 'domains': {}}
    for domain in (TF, C4):
        if ready['verdicts'][domain] != 'READY_FOR_REVIEW':
            index['domains'][domain] = {'skipped': f'readiness verdict {ready["verdicts"][domain]}'}
            continue
        cand, tm, iv = descriptors(domain)
        power = json.loads((READY / f'power_analysis_centred_{domain}.json').read_text())
        if power['plan_core_sha256'] != digest(plan_core(plan(domain))):
            raise RuntimeError('the pilot power analysis was made for another plan')
        rec = draft(domain, cand, power)
        frozen_copy, _ = DR.freeze(rec)
        export, cv = campaign(work, domain, cand, log)
        try:
            CAL.load(domain, ROOT, study='e1b')
            select = 'a study calibration e1b exists'
        except ValueError as exc:
            select = f'BLOCKED: {exc}'
        R11.dump(PKG / f'candidate_descriptor_{domain}.json', cand)
        R11.dump(PKG / f'time_matched_baselines_{domain}.json', tm)
        R11.dump(PKG / f'interventions_{domain}.json', iv)
        R11.dump(PKG / f'decision_record_DRAFT_{domain}.json', rec)
        R11.dump(PKG / f'power_analysis_centred_{domain}.json', power)
        shutil.copy(export, PKG / f'campaign_export_{domain}.zip')
        index['domains'][domain] = {
            'candidate_descriptor_id': cand['descriptor_id'], 'campaign_candidate_version': cv,
            'baselines': {n: d['descriptor_id'] for n, d in tm.items()},
            'interventions': {k: d['descriptor_id'] for k, d in iv.items()},
            'readiness_pilot_descriptor_id': ready['descriptors'][domain]['candidate'],
            'decision_record_draft_sha256': digest(rec),
            'problems_of_a_frozen_copy': DR.problems(frozen_copy, require_frozen=True),
            'select_step': select, 'power_chosen': power['chosen']}
        log(f'{domain}: package written; SELECT step: {select}')
    named, scan = RD.named_hosts()
    _, e1_named = R12.exposure(CAL.load(TF, ROOT, study='e1'))
    everything = {}
    for t in [*named, *e1_named]:
        everything[(t.domain, digest(t.model_dump(mode='json')))] = t.model_dump(mode='json')
    (PKG / 'exposure_hosts_all.json').write_bytes(canonical(sorted(everything.values(),
                                                                   key=lambda t: (t['domain'], t['task_id']))))
    index['exposure_hosts_all'] = {'hosts': len(everything), 'scan': scan, 'e1_regenerated': len(e1_named)}
    index['readiness_pilot'] = {'summary_sha256': digest(ready), 'verdicts': ready['verdicts']}
    if (CAUSAL / 'summary.json').exists():
        causal = json.loads((CAUSAL / 'summary.json').read_text())
        index['causal_readiness_pilot'] = {'summary_sha256': digest(causal), 'verdicts': causal['verdicts']}
    index['code_identity'] = code_identity(ROOT)['sha256']
    R11.dump(PKG / 'package_index.json', index)
    shutil.rmtree(work)
    log(f'done: {json.dumps({d: x.get("select_step", x.get("skipped")) for d, x in index["domains"].items()})}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
