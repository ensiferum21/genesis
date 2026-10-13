#!/usr/bin/env python3
"""B20_RX4 DEV calibration: a harder host family for E1 (the user's decision of 13 Oct 2026).

    b20rx4_e1_family_calibration.py OUT_DIR

E1 compares the represent-and-repair candidate (cross_2, 0.5 CPU s) with time-matched conventional
baselines (0.5 CPU s of restarts) on triangle-free hosts. On its current family (erdos n22 p0.35)
the candidate is already optimal on most hosts and the DRAFT design effect of 1.0 edge per task
cannot be powered (lost B20_R12 run; B20_R14: that family is at the ceiling). The user chose to
recalibrate E1 on a harder family. This script calibrates on DEV only; the E1 redo (B20_R12, which
needs the canonical B20_R11 code) must then run a fresh pilot and power analysis on new hosts.

Fixed before running:
  grid      triangle-free erdos n in (26, 30, 34, 38) x p in (0.25, 0.30, 0.35); 12 DEV hosts per cell,
            generator seed 20261501 + 10 i (cell i in grid order); every E1 host the builder named is
            excluded (b20r13_graph_headroom_pilot.e1_exposure)
  arms      candidate cross_2 (represent-and-repair, 0.5 CPU s); baselines multistart_tm, low_cycle_tm,
            exchange_tm (0.5 CPU s each, the R13/B20_R12 time-matched semantics); one run each, seed from
            the task identity
  optimum   obstruction.certify(candidate witness, 30 s): exact LP dual bound then SAT/DRAT
  per cell  comparator = the baseline with the highest mean in that cell; effect = candidate - comparator
            per host; room = certified optimum - candidate
  eligible  mean effect >= 1.0 (the DRAFT design effect), certified optimum on >= 9 of 12 hosts, and
            the candidate below the optimum on >= 6 of the certified hosts (room left)
  choice    the eligible cell with the smallest n (cheapest hosts), then the largest mean effect / SD
            of the effect; no eligible cell -> NO_ELIGIBLE_FAMILY (reported; nothing is relaxed)
A DEV calibration; it licenses no claim, and its hosts are exposed (written to OUT_DIR).
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r13_graph_headroom_pilot as P13  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402

TF = P13.TF
GRID = [(n, p) for n in (26, 30, 34, 38) for p in (0.25, 0.30, 0.35)]
HOSTS, CERT_S = 12, 30
DESIGN_EFFECT, MIN_CERTIFIED, MIN_ROOM = 1.0, 9, 6
CANDIDATE = 'cross_2'
BASELINES = ('multistart_tm', 'low_cycle_tm', 'exchange_tm')


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    specs = {n: s for n, _, s in P13.configurations(TF)}
    excluded = P13.e1_exposure()
    rows_path = out / 'rows.jsonl'
    done = {}
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            done[r['task_id']] = r
    hosts_rec = {}
    t0 = time.monotonic()
    with rows_path.open('a') as fh:
        for i, (n, p) in enumerate(GRID):
            tasks, seen, gen = ADAPTERS[TF].generate(20261501 + 10 * i, HOSTS, 'DEV', 'erdos', {'n': n, 'p': p},
                                                     excluded=excluded)
            excluded = set(excluded) | set(seen)
            hosts_rec[f'n{n}_p{p}'] = {'tasks': [t.model_dump(mode='json') for t in tasks], 'generator': gen}
            for t in tasks:
                if t.task_id in done:
                    continue
                seed = int(digest({'calibration': 'b20rx4', 'task': t.task_id})[:12], 16)
                vals = {}
                for arm in (CANDIDATE,) + BASELINES:
                    vals[arm] = P13.run_config(t, specs[arm], seed)['value']
                from genesis.invention import representations as R
                rep = next(r for r in R.proposals() if r['id'] == CANDIDATE)
                w = R.represent_and_repair(t.n, t.edges, rep, R.tf_add_ok, cpu_seconds=P13.SEARCH_S, seed=seed)['witness']
                rec = O.certify(t, w, seconds=CERT_S)
                r = {'cell': f'n{n}_p{p}', 'n': n, 'p': p, 'task_id': t.task_id, 'm': len(t.edges), 'values': vals,
                     'lower': rec['lower'], 'upper': rec['upper'], 'upper_method': rec['upper_evidence']['method'],
                     'status': rec['status']}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                done[t.task_id] = r
                print(f'[{time.monotonic() - t0:7.1f}s] n{n} p{p} {t.task_id[-4:]}: {vals} L={rec["lower"]} '
                      f'U={rec["upper"]}', flush=True)
    (out / 'hosts.json').write_text(json.dumps(hosts_rec, indent=1, sort_keys=True) + '\n')
    cells = {}
    for n, p in GRID:
        key = f'n{n}_p{p}'
        rs = [r for r in done.values() if r['cell'] == key]
        comp = max(BASELINES, key=lambda b: (statistics.mean(r['values'][b] for r in rs), b))
        eff = [r['values'][CANDIDATE] - r['values'][comp] for r in rs]
        cert = [r for r in rs if r['lower'] == r['upper']]
        room = [r['upper'] - r['values'][CANDIDATE] for r in cert]
        sd = statistics.stdev(eff) if len(eff) > 1 else None
        eligible = (statistics.mean(eff) >= DESIGN_EFFECT and len(cert) >= MIN_CERTIFIED
                    and sum(1 for x in room if x > 0) >= MIN_ROOM)
        cells[key] = {'n': n, 'p': p, 'hosts': len(rs), 'comparator': comp, 'mean_effect': round(statistics.mean(eff), 3),
                      'sd_effect': round(sd, 3) if sd is not None else None,
                      'wins_ties_losses': [sum(e > 0 for e in eff), sum(e == 0 for e in eff), sum(e < 0 for e in eff)],
                      'certified': len(cert), 'candidate_below_optimum': sum(1 for x in room if x > 0),
                      'mean_room': round(statistics.mean(room), 3) if room else None,
                      'baseline_means': {b: round(statistics.mean(r['values'][b] for r in rs), 3) for b in BASELINES},
                      'candidate_mean': round(statistics.mean(r['values'][CANDIDATE] for r in rs), 3),
                      'eligible': eligible}
    elig = [k for k, c in cells.items() if c['eligible']]
    choice = min(elig, key=lambda k: (cells[k]['n'], -(cells[k]['mean_effect'] / (cells[k]['sd_effect'] or 1e9)))) \
        if elig else None
    summary = {'schema': 'genesis-b20rx4-e1-calibration-v1', 'cells': cells, 'eligible': elig,
               'choice': choice or 'NO_ELIGIBLE_FAMILY',
               'rule': {'design_effect': DESIGN_EFFECT, 'min_certified': MIN_CERTIFIED, 'min_room': MIN_ROOM,
                        'hosts_per_cell': HOSTS, 'certify_seconds': CERT_S}}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print('choice', summary['choice'], 'eligible', elig, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
