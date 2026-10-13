#!/usr/bin/env python3
"""B20_R12: DEV calibration of E1's host family under the separately versioned rule e1-hard-v1.

    b20r12_e1_calibration.py OUT_DIR [--adopt]

The user's decision (13 Oct 2026): E1's family is chosen by a second, versioned rule
(calibration.SELECTION_RULE_E1_HARD), not by the frozen domain rule, which by design excludes
families where the fixed baselines rarely reach the optimum. The domain rule and the domain
adoption are unchanged. The new rule never reads a candidate; a reviewer must sign it off.

Fixed before running (this file is committed before it runs):
  rule       calibration.SELECTION_RULE_E1_HARD ('e1-hard-v1'): certified fraction >= 0.9, fixed-baseline
             ceiling rate in [0, 0.25], mean headroom >= 0.02, median evaluator time <= 15 s; order by
             ceiling rate closest to 0, then faster evaluator, then grid order; at most 4 settings
  grid       the union of every triangle-free setting measured before, not a choice among them: the
             round-2 domain grid (6 settings, in its order) followed by the B20_RX4 cells not already
             in it (erdos n in 26..38 x p in .25/.30/.35, in RX4 order) -> 17 settings
  measure    calibration.calibrate unchanged: 8 fresh DEV hosts per setting, the three fixed DSL
             baselines under the calibration limits, the domain reference with 30 s per host
  seed       20261901 (generation seed + 1000 i per setting, as calibrate always does)
  adoption   with --adopt, and only if the record passes record_problems and selects >= 1 setting,
             configs/dev_calibration.json gains studies.e1.triangle_free_host_v1 (record path, SHA-256,
             rule name). If nothing is selected the result is NO_ELIGIBLE_SETTING: reported, nothing is
             relaxed, E1 stays where it is.

Disclosure: before fixing this grid the builder had seen DEV candidate results on some of these
settings (B20_R14 optimum-gap probe; B20_RX4, whose n30 p0.35 effect was chosen by candidate effect
and is unusable for E1). That knowledge motivated the user's decision to recalibrate; it does not
enter the rule, which reads only the fixed baselines and the evaluator.

A DEV calibration: every host measured is exposed and is excluded from E1's later panels.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as CAL  # noqa: E402
from genesis.common import digest  # noqa: E402

DOMAIN = 'triangle_free_host_v1'
SEED = 20261901
STUDY = 'e1'
RECORD = 'evidence/dev_calibration_e1_b20r12/calibration_triangle_free_host_v1_e1.json'
RX4_CELLS = [(n, p) for n in (26, 30, 34, 38) for p in (0.25, 0.30, 0.35)]


def grid():
    rec = json.loads((ROOT / json.loads((ROOT / CAL.CONFIG).read_text())['domains'][DOMAIN]['record']).read_text())
    out = [(g['family'], g['params']) for g in rec['grid']]
    for n, p in RX4_CELLS:
        if ('erdos', {'n': n, 'p': p}) not in out:
            out.append(('erdos', {'n': n, 'p': p}))
    return out


def adopt(record):
    cfg_path = ROOT / CAL.CONFIG
    cfg = json.loads(cfg_path.read_text())
    cfg.setdefault('studies', {}).setdefault(STUDY, {})[DOMAIN] = {
        'record': RECORD, 'sha256': digest(record), 'rule': record['rule']['name'], 'selected': record['selected'],
        'note': ('B20_R12: E1 only, under the separately versioned rule e1-hard-v1 (the user, 13 Oct 2026); '
                 'the domain adoption above is unchanged; needs reviewer sign-off of the rule')}
    cfg_path.write_text(json.dumps(cfg, indent=1, sort_keys=True) + '\n')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    adopt_flag = '--adopt' in argv
    out = Path([a for a in argv if not a.startswith('--')][0])
    out.mkdir(parents=True, exist_ok=True)
    g = grid()
    assert len(g) == 17, g
    t0 = time.monotonic()

    def progress(s):
        print(f'[{time.monotonic() - t0:7.1f}s] {s["index"]:2d} {s["family"]} {s["params"]} {s["summary"]} '
              f'-> {s["ineligible_because"] or "ELIGIBLE"}', flush=True)

    record = CAL.calibrate(DOMAIN, g, seed=SEED, rule=CAL.SELECTION_RULE_E1_HARD, progress=progress)
    problems = CAL.record_problems(record)
    path = ROOT / RECORD if out.resolve() == (ROOT / RECORD).parent.resolve() else out / Path(RECORD).name
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    summary = {'schema': 'genesis-b20r12-e1-calibration-summary-v1', 'record': str(path.relative_to(ROOT))
               if path.is_relative_to(ROOT) else str(path), 'record_sha256': digest(record),
               'rule': record['rule']['name'], 'problems': problems, 'selected': record['selected'],
               'verdict': 'SELECTED' if record['selected'] and not problems else
               ('INVALID_RECORD' if problems else 'NO_ELIGIBLE_SETTING'),
               'settings': [{'index': s['index'], 'family': s['family'], 'params': s['params'], **s['summary'],
                             'ineligible_because': s['ineligible_because']} for s in record['settings']],
               'seconds': round(time.monotonic() - t0, 1)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print('verdict', summary['verdict'], 'selected', record['selected'], 'problems', problems, flush=True)
    if adopt_flag and summary['verdict'] == 'SELECTED':
        if path.resolve() != (ROOT / RECORD).resolve():
            raise SystemExit('--adopt needs OUT_DIR = ' + str(Path(RECORD).parent))
        adopt(record)
        CAL.load(DOMAIN, ROOT, study=STUDY)          # re-checked exactly as later users will
        print('adopted under studies.e1', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
