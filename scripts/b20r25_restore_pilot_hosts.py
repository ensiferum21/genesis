#!/usr/bin/env python3
"""B20_R25 fix-up: restore the causal re-pilot's host list after the resumed run overwrote it.

    PYTHONPATH=src python3 scripts/b20r25_restore_pilot_hosts.py

What went wrong. scripts/b20r25_e1b_causal.py ran twice (the first run stopped in Part B). Its first run wrote
evidence/e1b_causal_b20r25/pilot_hosts.json, inside the tree its exposure walk scans. On the second run the walk
therefore excluded the pilot's own 30 hosts, the generator drew 30 other graphs under the same index-based
task ids, the resumable loop matched the stored rows by task id (so no host was re-run and the analysis used
the first run's rows unchanged), and pilot_hosts.json was overwritten with the 30 unscored graphs.

This script regenerates the hosts the rows belong to: the same seed and count, excluding the exposure set the
first run used (the same walk without evidence/e1b_causal_b20r25; 1,544 identities, as its log says). It then
checks every regenerated host against its row: the task id, the stratum, and the certified optimum
(obstruction.certify, 120 s, unseeded) must match. Only if all 30 match does it write pilot_hosts.json (and
keeps the overwritten file as pilot_hosts_second_run_unscored.json). A fix-up of a record, not a study.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402

import b20r12_e1_redo as R12  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as RP  # noqa: E402
import b20r25_e1b_causal as E  # noqa: E402

OUT = ROOT / 'evidence' / 'e1b_causal_b20r25'


def first_run_exclusion():
    original = RD.ROOT
    skip = OUT.resolve()
    real_rglob = Path.rglob

    def rglob(self, pattern):
        return (p for p in real_rglob(self, pattern) if skip not in p.resolve().parents)
    Path.rglob = rglob
    try:
        named, _ = RD.named_hosts()
    finally:
        Path.rglob = real_rglob
    assert RD.ROOT == original
    e1_excluded, _ = R12.exposure(CAL.load(E.TF, ROOT, study='e1'))
    cal = RP.calibration_tasks(CAL.load(E.TF, ROOT, study='e1'))
    cfg = json.loads((ROOT / CAL.CONFIG).read_text())
    for study in ('e1-v2', 'e1b'):
        for domain in cfg.get('studies', {}).get(study, {}):
            cal += RP.calibration_tasks(CAL.load(domain, ROOT, study=study))
    return RD.identities(named) | set(e1_excluded) | RD.identities(cal)


def main():
    excluded = first_run_exclusion()
    print(f'first-run exclusion: {len(excluded)} identities', flush=True)
    record = CAL.load(E.TF, ROOT, study=E.STUDY)
    tasks, _ = CAL.calibrated_panel(record, E.PILOT_SEED, E.PILOT_TASKS, 'DEV', excluded=excluded)
    rows = {json.loads(line)['task_id']: json.loads(line) for line in (OUT / 'rows.jsonl').read_text().splitlines()
            if line.strip()}
    problems = []
    for t in tasks:
        r = rows.get(t.task_id)
        if r is None or r['stratum'] != t.family:
            problems.append(f'{t.task_id}: no row with this id and stratum')
            continue
        rec = O.certify(t, [], seconds=E.CERTIFY_S)
        opt = rec['lower'] if rec['lower'] == rec['upper'] else None
        ok = opt is not None and opt == r['optimum']
        print(f'{t.task_id}: regenerated optimum {opt} (L{rec["lower"]}/U{rec["upper"]}), row optimum {r["optimum"]}'
              f' -> {"MATCH" if ok else "MISMATCH"}', flush=True)
        if not ok:
            problems.append(f'{t.task_id}: optimum {opt} differs from the row ({r["optimum"]})')
    if len(excluded) != 1544:
        problems.append(f'the first-run exclusion has {len(excluded)} identities, not 1,544')
    if problems:
        print('NOT RESTORED:', problems)
        return 1
    current = OUT / 'pilot_hosts.json'
    if current.exists():
        current.rename(OUT / 'pilot_hosts_second_run_unscored.json')
    current.write_text(json.dumps([t.model_dump(mode='json') for t in tasks], indent=1, sort_keys=True) + '\n')
    print('RESTORED: all 30 hosts match their rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
