#!/usr/bin/env python3
"""B20_R24: regenerate the E1 (v3) and E1b (v2) handoff packages on the e1-hard-v2 family. DRAFT; nothing
is registered with any custodian.

    b20r24_packages.py WORK_DIR

For each study (E1: study 'e1-v2'; E1b: study 'e1b', triangle-free only, because no C4 setting is eligible):
  * the candidate and the time-matched baselines (and, for E1b, the registered ablation and placebo) as
    descriptors built by this commit's reviewed code;
  * a fresh frozen DEV campaign (1 generation) with the candidate frozen in it, and its export;
  * the DRAFT decision record the re-pilot built (evidence/repilots_b20r24), which names the e1-hard-v2
    study calibration and the re-pilot's centred power analysis, and the problems a frozen copy would have;
  * the re-pilot summary and power analysis, and the rehearsal re-run summary (outcome, judge, SELECT);
  * every host the builder named or generated, as tasks (exposure_hosts_all.json): the evidence walk, the
    regenerated E1 hosts, both calibrations' hosts, the pilots and both rounds of rehearsals.
Files of earlier package versions that this one does not replace are kept (E1: the B19 and B20_R12 files).
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
from genesis.kernel import replay_contracts as RC  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as RP  # noqa: E402

PILOT, RERUN = ROOT / 'evidence' / 'repilots_b20r24', ROOT / 'evidence' / 'rehearsal_rerun_b20r24'
TF = RD.TF
PACKAGES = {'e1': ('e1-v2', ROOT / 'handoff' / 'e1', 20263001), 'e1b_tf': ('e1b', ROOT / 'handoff' / 'e1b', 20263011)}
E1_KEEP = ('README.md', 'b19_pilot_rows.json', 'b19_power_analysis.json', 'b19_power_analysis_b16_model.json',
           'b19_summary.json', 'decision_record_DRAFT.json', 'decision_record_DRAFT_v2.json',
           'pilot_summary_b20r12.json', 'power_analysis_centred_b20r12.json', 'exposure_hosts_to_exclude.json')


def campaign(work, key, domain, cand, seed, log):
    from genesis.campaign import Campaign
    from genesis.cli import export_replication, freeze_candidate_descriptor
    from genesis.models import Config
    root = work / f'campaign_{key}'
    if root.exists():
        shutil.rmtree(root)
    t0 = time.monotonic()
    Campaign.initialize(root, Config(domain=domain, seed=seed, generations=1, tasks_per_panel=4, proposals_per_epoch=2,
                                     research_trials=8))
    with Campaign(root) as c:
        c.run()
        cv = freeze_candidate_descriptor(c, cand, origin=f'B20_R24 {key} candidate (re-pilot evidence/repilots_b20r24)')
        export_replication(root, root / 'exports' / 'campaign_export.zip', store=c.store)
    log(f'{key}: campaign frozen and exported in {time.monotonic() - t0:.0f} s')
    return root / 'exports' / 'campaign_export.zip', cv


def main(argv=None):
    work = Path((argv or sys.argv[1:])[0]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)  # noqa: E731
    pilot, rerun = json.loads((PILOT / 'summary.json').read_text()), json.loads((RERUN / 'summary.json').read_text())
    _, scan, named = RP.exposure(log)
    everything = {}
    for t in named:
        everything[(t.domain, digest(t.model_dump(mode='json')))] = t.model_dump(mode='json')
    for ts in json.loads((PILOT / 'pilot_hosts.json').read_text()).values():
        for t in ts:
            everything[(t['domain'], digest(t))] = t
    for d in (PILOT, RERUN):
        for f in sorted(d.glob('rehearsal_*.json')):
            if f.name.startswith('rehearsal_receipt'):
                continue
            r = json.loads(f.read_text())
            for t in r.get('select_hosts', []) + r.get('confirm_hosts', []):
                everything[(t['domain'], digest(t))] = t
    hosts_all = sorted(everything.values(), key=lambda t: (t['domain'], t['task_id']))
    for key, (study, pkg, seed) in PACKAGES.items():
        domain = pilot['pilots'][key]['domain']
        cand, tm, _ = RP.arms(key, domain)
        if key == 'e1':
            for f in pkg.glob('*'):
                if f.name not in E1_KEEP:
                    f.unlink()
        else:
            if pkg.exists():
                shutil.rmtree(pkg)
            pkg.mkdir(parents=True)
            iv = {}
            for kind, init in (('ablation', 'random_greedy'), ('placebo', 'lp_shuffled_greedy')):
                d = C.build_descriptor('construct-pipeline-v1', domain, dict(RD.CANDIDATE, init=init), **RD.PROFILE)
                why, path = RC.intervention_problems(kind, cand, d)
                if why or path != ('init',):
                    raise RuntimeError(f'{kind}: {why}')
                iv[kind] = d
            R11.dump(pkg / 'interventions.json', iv)
        draft = json.loads((PILOT / f'decision_record_DRAFT_{key}.json').read_text())
        if cand['descriptor_id'][:16] not in draft['exact_claim']:
            raise RuntimeError(f'{key}: the DRAFT names another candidate descriptor')
        frozen_copy, _ = DR.freeze(draft)
        export, cv = campaign(work, key, domain, cand, seed, log)
        record = CAL.load(domain, ROOT, study=study)
        rr = json.loads((RERUN / f'rehearsal_{key}.json').read_text())
        R11.dump(pkg / 'candidate_descriptor.json', cand)
        R11.dump(pkg / 'time_matched_baselines.json', tm)
        R11.dump(pkg / ('decision_record_DRAFT_v3.json' if key == 'e1' else 'decision_record_DRAFT.json'), draft)
        shutil.copy(PILOT / f'power_analysis_centred_{key}.json', pkg / 'power_analysis_centred_b20r24.json')
        R11.dump(pkg / 'pilot_summary_b20r24.json', pilot['pilots'][key])
        R11.dump(pkg / 'rehearsal_summary_b20r24.json', {
            'label': rr['label'], 'first_rehearsal': pilot['rehearsals'][key], 'rerun': rerun['rehearsals'][key],
            'receipt_payload': rr['receipt_payload'], 'judge': rr['judge'], 'fairness': rr['fairness'],
            'comparator_selection': rr['comparator_selection']})
        shutil.copy(export, pkg / 'campaign_export.zip')
        (pkg / 'exposure_hosts_all.json').write_bytes(canonical(hosts_all))
        R11.dump(pkg / 'package_index.json', {
            'schema': 'genesis-gv3-package-v1', 'study': study, 'domain': domain,
            'status': 'DRAFT; not registered; licenses nothing',
            'candidate_descriptor_id': cand['descriptor_id'], 'campaign_candidate_version': cv,
            'baselines': {n: d['descriptor_id'] for n, d in tm.items()},
            'calibration': {'record': json.loads((ROOT / CAL.CONFIG).read_text())['studies'][study][domain]['record'],
                            'sha256': digest(record), 'rule': record['rule']['name'], 'selected': record['selected']},
            'decision_record_draft_sha256': digest(draft),
            'problems_of_a_frozen_copy': DR.problems(frozen_copy, require_frozen=True),
            'pilot_verdict': pilot['pilots'][key]['verdict'], 'rehearsals': {'first': pilot['rehearsals'][key],
                                                                             'rerun': rerun['rehearsals'][key]},
            'exposure_hosts_all': {'hosts': len(hosts_all), 'scan': scan},
            'code_identity': code_identity(ROOT)['sha256']})
        log(f'{key}: package {pkg.relative_to(ROOT)} written ({len(hosts_all)} exposure hosts)')
    shutil.rmtree(work)
    return 0


if __name__ == '__main__':
    sys.exit(main())
