#!/usr/bin/env python3
"""B20_R30: certification at the calibration's budget and at the evaluator's, on the e1b family (DEV).

    b20r30_certification_budget.py OUT_DIR            run (resumable) and summarise
    b20r30_certification_budget.py OUT_DIR --summary  summarise existing rows only

B20R24-OPEN-2 is a design point for a reviewer, and two limits bear on it:
  * `e1-hard-v2` admits a setting when at least 90% of its calibration hosts are certified within
    60 s (obstruction.certify, seeded with the best time-matched baseline);
  * the analysis plan tolerates at most 5% unsupported CONFIRM tasks under the evaluator's
    reference: GraphHostAdapter.reference(joint=True) at 600 s.
The calibration measured 8 hosts per setting. This step measures both limits on the same fresh
hosts, so a reviewer can see whether they agree on this family. It changes neither limit.

Everything below is fixed before running.

Hosts: 90 fresh DEV hosts, drawn round-robin from the adopted e1b calibration's three selected
settings (calibration.calibrated_panel), generator seed 20263001. They exclude every exposure
identity b20r24_repilots.exposure excludes: every graph host named under evidence/ and handoff/
(B20_R26–R28 included), the regenerated E1 hosts, and the calibration hosts.

Per host:
  calibration  calibration.measure_time_matched([host], e1-hard-v2 measurement): the three fixed
               baselines as dsl-time-matched-v1 (2.0 CPU s, runc), then obstruction.certify seeded
               with the best of them, 60 s. Certified iff lower == upper.
  evaluator    domains.ADAPTERS['triangle_free_host_v1'].reference(host, joint=True, seconds=600):
               the custodian's v4 reference. Certified iff FINITE_CERTIFIED. Wall time recorded.
Where both certify, the values must agree; a disagreement is reported as a defect.

Summary per setting and pooled: the certified fraction at 60 s (calibration) and at 600 s
(evaluator); hosts certified only at 600 s; the evaluator's wall-time median, 90th percentile
and maximum; and the one-sided 95% Clopper–Pearson upper bound of the evaluator's unsupported
rate.

Verdict on the pooled evaluator unsupported rate u (fixed here):
  LIMITS_CONSISTENT     the 95% upper bound of u ≤ 0.05
  LIMITS_INCONCLUSIVE   u ≤ 0.05, but its 95% upper bound > 0.05
  LIMITS_INCONSISTENT   u > 0.05
A DEV measurement. It licenses no claim, and the decision stays with the reviewer.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis.common import code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402

TF = RD.TF
STUDY, HOSTS, SEED = 'e1b', 90, 20263001
EVALUATOR_SECONDS = 600
LIMIT = 0.05


def clopper_pearson_upper(k, n, alpha=0.05):
    """One-sided (1 - alpha) upper bound of a binomial rate, by bisection on the exact tail."""
    from math import comb
    if k >= n:
        return 1.0
    tail = lambda p: sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))   # P(X <= k)
    lo, hi = k / n, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if tail(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def hosts(log):
    excluded, scan, _ = R24.exposure(log)
    record = CAL.load(TF, ROOT, study=STUDY)
    tasks, _ = CAL.calibrated_panel(record, SEED, HOSTS, 'DEV', excluded=excluded)
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    return tasks, scan, record


def run(out, tasks, log):
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        done = {json.loads(l)['task_id'] for l in rows_path.read_text().splitlines() if l.strip()}
    measurement = CAL.SELECTION_RULE_E1_HARD_V2['measurement']
    t0 = time.monotonic()
    with rows_path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            cal = CAL.measure_time_matched([t], measurement, seed=SEED)[0]
            start = time.monotonic()
            ref = ADAPTERS[TF].reference(t, joint=True, seconds=EVALUATOR_SECONDS)
            wall = round(time.monotonic() - start, 3)
            r = {'task_id': t.task_id, 'stratum': t.family, 'edges': len(t.edges),
                 'calibration': {'status': cal['reference']['status'], 'value': cal['reference'].get('value'),
                                 'seconds': cal['reference_seconds'], 'baselines': cal['baselines']},
                 'evaluator': {'status': ref['status'], 'value': ref.get('value'), 'method': ref.get('method'),
                               'reason': ref.get('reason'), 'wall_s': wall}}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id}: calibration {r["calibration"]["status"]} {r["calibration"]["value"]} '
                f'({r["calibration"]["seconds"]:.1f}s); evaluator {ref["status"]} {ref.get("value")} ({wall:.1f}s) '
                f'[{time.monotonic() - t0:.0f}s]')


def summarise_rows(rows):
    n = len(rows)
    cal = sum(r['calibration']['status'] == 'FINITE_CERTIFIED' for r in rows)
    ev = sum(r['evaluator']['status'] == 'FINITE_CERTIFIED' for r in rows)
    only600 = sum(r['evaluator']['status'] == 'FINITE_CERTIFIED' and r['calibration']['status'] != 'FINITE_CERTIFIED'
                  for r in rows)
    walls = sorted(r['evaluator']['wall_s'] for r in rows)
    disagree = [r['task_id'] for r in rows if r['calibration']['status'] == r['evaluator']['status'] == 'FINITE_CERTIFIED'
                and r['calibration']['value'] != r['evaluator']['value']]
    return {'hosts': n, 'certified_60s_calibration': cal, 'certified_600s_evaluator': ev,
            'certified_fraction_60s': round(cal / n, 4) if n else None,
            'certified_fraction_600s': round(ev / n, 4) if n else None,
            'certified_only_at_600s': only600, 'evaluator_unsupported': n - ev,
            'evaluator_wall_s': {'median': round(statistics.median(walls), 2) if walls else None,
                                 'p90': walls[int(0.9 * (n - 1))] if walls else None, 'max': walls[-1] if walls else None},
            'value_disagreements': disagree}


def analyse(out, tasks, scan, record):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    want = {t.task_id for t in tasks}
    if {r['task_id'] for r in rows} != want:
        raise RuntimeError(f'{len(want - {r["task_id"] for r in rows})} hosts not yet run')
    pooled = summarise_rows(rows)
    u = pooled['evaluator_unsupported'] / pooled['hosts']
    bound = clopper_pearson_upper(pooled['evaluator_unsupported'], pooled['hosts'])
    verdict = ('LIMITS_CONSISTENT' if bound <= LIMIT else 'LIMITS_INCONCLUSIVE' if u <= LIMIT else
               'LIMITS_INCONSISTENT')
    summary = {'schema': 'genesis-b20r30-certification-budget-v1', 'study': STUDY, 'domain': TF, 'seed': SEED,
               'calibration': {'record_sha256': digest(record), 'rule': record['rule']['name'],
                               'selected': record['selected']},
               'limits': {'calibration': 'certified_fraction_min 0.9 at 60 s (e1-hard-v2)',
                          'plan': 'at most 5% unsupported CONFIRM tasks at the evaluator\'s 600 s'},
               'pooled': pooled, 'by_stratum': {s: summarise_rows([r for r in rows if r['stratum'] == s])
                                                 for s in sorted({r['stratum'] for r in rows})},
               'evaluator_unsupported_rate': round(u, 4), 'evaluator_unsupported_upper95': round(bound, 4),
               'verdict': verdict, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV measurement for a reviewer (B20R24-OPEN-2); licenses no claim; changes no limit'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    tasks, scan, record = hosts(log)
    R11.dump(out / 'hosts.json', {'study': STUDY, 'seed': SEED, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    if '--summary' not in argv:
        run(out, tasks, log)
    s = analyse(out, tasks, scan, record)
    log(f'verdict {s["verdict"]}: pooled {s["pooled"]}; unsupported upper95 {s["evaluator_unsupported_upper95"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
