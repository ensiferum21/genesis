#!/usr/bin/env python3
"""B20_R24: DEV calibration of the E1 and E1b host families under the versioned rule e1-hard-v2.

    b20r24_e1_hard_v2_calibration.py OUT_DIR --domain DOMAIN   calibrate one domain (the two run in parallel)
    b20r24_e1_hard_v2_calibration.py OUT_DIR --adopt           check both records and adopt the studies

The user's decision (14 Oct 2026): "New rule e1-hard-v2: a versioned rule that adds a candidate-independent
headroom bound and certification limit; a calibration picks settings for both E1 and E1b, then both are
re-piloted on fresh hosts." It answers B20R12-OPEN-1 (E1 UNDERPOWERED on the e1-hard-v1 family) and
B20R23-OPEN-1 (no study calibration for E1b).

Fixed before running (this file is committed before it runs):
  rule       calibration.SELECTION_RULE_E1_HARD_V2 ('e1-hard-v2'), unchanged from e1-hard-v1 except:
             * baselines measured as the studies run them: the three fixed DSL programs as dsl-time-matched-v1
               with 2.0 CPU s of restarts (the larger study budget; E1's baselines get 0.5 s), in the OCI
               sandbox under one profile {cpu 4 s, 2048 MiB, wall 20 s, 1000 queries};
             * reference: obstruction.certify seeded with the best baseline witness, 60 s per host; a host
               not certified within it counts as uncertified (certified fraction >= 0.9 as before);
             * headroom bound in edges: mean (certified optimum - best time-matched baseline) >= 1.0, the
               analysis plan's design effect.
             Still: ceiling rate in [0, 0.25] (target 0), relative headroom >= 0.02, median evaluator time
             <= 15 s, order by ceiling rate closest to 0, then faster evaluator, then grid order, at most 4.
  grids      the union of every setting measured before, not a choice among them:
             triangle_free_host_v1: the e1-hard-v1 grid (17 settings, in its order), then the B20_R13/R14
               settings not in it, in their order: erdos n40 p0.2, planted_cluster n30 p_in 0.6 p_out 0.2,
               erdos n40 p0.35 -> 20 settings (C1 erdos n30 p0.3 is in the v1 grid; C2 is n40 p0.2);
             c4_host_v2: the domain grid (13 settings, in its order), then erdos n30 p0.2 (B20_R13 S7,
               E1b C3) -> 14 settings (B20_R13 S6, erdos n20 p0.25, is in the domain grid).
  measure    calibration.calibrate with the rule: 8 fresh DEV hosts per setting, generation seed
             20262701 (triangle-free) or 20262801 (C4), + 1000 i per setting.
  adoption   with --adopt, for each domain whose record passes record_problems and selects >= 1 setting:
             configs/dev_calibration.json studies 'e1-v2' (triangle-free only: E1's candidate is
             triangle-free only) and 'e1b' (both domains) name the record, its SHA-256 and the rule. The
             study 'e1' (e1-hard-v1, B20_R12) is kept unchanged for reproducibility. A domain that selects
             nothing is NO_ELIGIBLE_SETTING: reported, nothing relaxed, no adoption.

Disclosure: the builder has seen DEV candidate results on some of these settings (B20_R12, R14, RX3/RX3b,
the E1b pilots of B20_R23). The rule reads only the fixed baselines and the evaluator, never a candidate,
and the grid is every setting measured before. Every host measured is DEV and is exposed; the re-pilots
and any CONFIRM panel exclude them.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as CAL  # noqa: E402
from genesis.common import digest  # noqa: E402

TF, C4 = 'triangle_free_host_v1', 'c4_host_v2'
SEEDS = {TF: 20262701, C4: 20262801}
TASKS_PER_SETTING = 8
RULE = CAL.SELECTION_RULE_E1_HARD_V2
STUDIES = {'e1-v2': (TF,), 'e1b': (TF, C4)}
NOTE = ('B20_R24: under the versioned rule e1-hard-v2 (the user, 14 Oct 2026); needs reviewer sign-off of the '
        'rule; the domain adoption and study e1 (e1-hard-v1) are unchanged')


def grid(domain):
    cfg = json.loads((ROOT / CAL.CONFIG).read_text())
    if domain == TF:
        v1 = json.loads((ROOT / cfg['studies']['e1'][TF]['record']).read_text())
        out = [(g['family'], g['params']) for g in v1['grid']]
        later = [('erdos', {'n': 40, 'p': 0.2}), ('planted_cluster', {'n': 30, 'p_in': 0.6, 'p_out': 0.2}),
                 ('erdos', {'n': 40, 'p': 0.35})]
    else:
        dom = json.loads((ROOT / cfg['domains'][C4]['record']).read_text())
        out = [(g['family'], g['params']) for g in dom['grid']]
        later = [('erdos', {'n': 20, 'p': 0.25}), ('erdos', {'n': 30, 'p': 0.2})]
    for g in later:
        if g not in out:
            out.append(g)
    return out


def record_path(out, domain):
    return out / f'calibration_{domain}_e1_hard_v2.json'


def calibrate(out, domain):
    t0 = time.monotonic()
    log = (out / f'run_{domain}.log').open('a')

    def progress(s):
        x = s['summary']
        line = (f'[{time.monotonic() - t0:7.1f}s] {domain} #{s["index"]} {s["family"]} {s["params"]}: certified '
                f'{x["certified_fraction"]}, ceiling {x["ceiling_rate"]}, gap {x.get("mean_gap_edges")} edges, '
                f'headroom {x["mean_headroom"]}, ref median {x["reference_seconds_median"]} s, edges {x["mean_edges"]}'
                f' -> {s["ineligible_because"] or "ELIGIBLE"}')
        print(line, flush=True)
        log.write(line + '\n')
        log.flush()
    g = grid(domain)
    rec = CAL.calibrate(domain, g, seed=SEEDS[domain], tasks_per_setting=TASKS_PER_SETTING, rule=RULE,
                        progress=progress)
    record_path(out, domain).write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
    line = f'{domain}: {len(g)} settings; selected {rec["selected"]}; problems {CAL.record_problems(rec)}'
    print(line, flush=True)
    log.write(line + '\n')


def adopt(out):
    cfg_path = ROOT / CAL.CONFIG
    cfg = json.loads(cfg_path.read_text())
    summary = {'schema': 'genesis-b20r24-calibration-v1', 'rule': RULE, 'domains': {}}
    for domain in (TF, C4):
        rec = json.loads(record_path(out, domain).read_text())
        problems = CAL.record_problems(rec)
        verdict = ('INVALID_RECORD' if problems else 'NO_ELIGIBLE_SETTING' if not rec['selected'] else 'SELECTED')
        summary['domains'][domain] = {
            'record': str(record_path(out, domain).relative_to(ROOT)), 'sha256': digest(rec), 'problems': problems,
            'verdict': verdict, 'selected': rec['selected'],
            'settings': [{'index': s['index'], 'family': s['family'], 'params': s['params'], 'summary': s['summary'],
                          'ineligible_because': s['ineligible_because']} for s in rec['settings']]}
        if verdict != 'SELECTED':
            continue
        for study, domains in STUDIES.items():
            if domain in domains:
                cfg.setdefault('studies', {}).setdefault(study, {})[domain] = {
                    'record': str(record_path(out, domain).relative_to(ROOT)), 'sha256': digest(rec),
                    'rule': RULE['name'], 'selected': rec['selected'], 'note': NOTE}
    cfg_path.write_text(json.dumps(cfg, indent=1, sort_keys=True) + '\n')
    for study, domains in STUDIES.items():
        for domain in domains:
            if summary['domains'][domain]['verdict'] == 'SELECTED':
                CAL.load(domain, ROOT, study=study)            # the adoption loads and re-checks
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({d: (x['verdict'], x['selected']) for d, x in summary['domains'].items()}))


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if '--adopt' in argv:
        adopt(out)
    else:
        calibrate(out, argv[argv.index('--domain') + 1])
    return 0


if __name__ == '__main__':
    sys.exit(main())
