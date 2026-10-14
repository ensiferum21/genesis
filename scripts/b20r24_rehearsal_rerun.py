#!/usr/bin/env python3
"""B20_R24: the E1 and E1b same-operator rehearsals again, after the evaluator's reference was repaired.

    b20r24_rehearsal_rerun.py OUT_DIR

What happened first (evidence/repilots_b20r24, kept): both re-pilots were READY_FOR_REVIEW, and both
rehearsals were INVALID under the preregistered plan, because the custodian could not certify the optimum
of 4 of 30 (E1) and 2 of 30 (E1b) CONFIRM hosts and the plan allows at most 5% unsupported. The cause is
in the evaluator, not in the plan: the graph adapter's SAT-only reference stops at the first SAT call that
returns UNKNOWN within 60 s (it gave up after 62-70 s on each). The joint LP/SAT certification closes 5 of
the 6 hosts within 120 s (3 by the exact LP dual in 4-10 s, 2 by SAT/DRAT in 158-233 s, the last call
overrunning while drat-trim checked) and leaves one at bounds 100..101 (evidence/repilots_b20r24/
diagnosis_unsupported.log).
Repair (B20_R24, before this run): a v4 evaluation now asks a graph adapter for the joint reference
(domains.GraphHostAdapter.reference(joint=True): exact LP dual, then SAT/DRAT on the remaining gap with the
whole 600 s budget, certificate bundle v2 kept in the evaluation evidence). The plan, its unsupported limit
(5%), the decision records and every other rule are unchanged.

Fixed before running (this file is committed before it runs): the rehearsal procedure of
scripts/b20r24_repilots.py, unchanged, for E1 (study e1-v2) and E1b (study e1b, triangle-free), with the
power analyses of evidence/repilots_b20r24; a new campaign seed 20262971 and new CONFIRM seeds 20262961 + 10 k;
the custodian draws a new SELECT panel. Every host named so far, including both earlier rehearsals' SELECT
and CONFIRM hosts, is excluded. The outcomes are reported as they come; an INVALID or NOT_SUPPORTED rehearsal
is kept. REHEARSAL by the same operator with fixture keys: it licenses nothing.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r11_e1_readiness as R11  # noqa: E402
import b20r24_repilots as RP  # noqa: E402
from genesis.common import code_identity  # noqa: E402

FIRST = ROOT / 'evidence' / 'repilots_b20r24'
RP.REHEARSAL_SEED, RP.CAMPAIGN_SEED = 20262961, 20262971


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    first = json.loads((FIRST / 'summary.json').read_text())
    excluded, scan, named = RP.exposure(log)
    results = {}
    for key, study, domain, _ in RP.PILOTS:
        if first['pilots'][key]['verdict'] != 'READY_FOR_REVIEW':
            results[key] = f'not run: pilot verdict {first["pilots"][key]["verdict"]}'
            continue
        power = json.loads((FIRST / f'power_analysis_centred_{key}.json').read_text())
        results[key], used = RP.rehearsal(out, log, key, study, domain, power, excluded, named)
        excluded = set(excluded) | used
    summary = {'schema': 'genesis-b20r24-rehearsal-rerun-v1', 'rehearsals': results, 'exposure_scan': scan,
               'first_rehearsals': first['rehearsals'], 'seeds': {'confirm': RP.REHEARSAL_SEED, 'campaign': RP.CAMPAIGN_SEED},
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'same-operator rehearsal with fixture keys; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    log(f'rehearsals {json.dumps(results)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
