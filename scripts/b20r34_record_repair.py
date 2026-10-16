#!/usr/bin/env python3
"""B20_R34 record repair: list the graphs the rows were actually run on.

    b20r34_record_repair.py

**What happened.** A container restart stopped `b20r34_mip_hard_probe.py` after 48 of its 56 hosts,
and the run was resumed. On resume the script regenerates its hosts with the exposure exclusions.
By then its own first `hosts.json` was a named host file under evidence/, so its 56 first-run
hosts were excluded, and a different set of 56 graphs was drawn. Task ids depend only on seed and
index, so the new graphs carried the old ids. As a result:
  * the 48 completed rows were skipped by id;
  * the last 8 rows (setting 7) ran on the second set's graphs;
  * `hosts.json` was overwritten with the second set.
The rows and the summary's numbers are unaffected, since they are computed from the rows alone.
The host listing was wrong for 48 of the 56 rows. The same latent resume defect is in the
B20_R30, B20_R32 and B20_R33 scripts; none of those runs was resumed.

**What this does.** It:
  1. reconstructs the first-run hosts deterministically. The exclusions are the present exposure
     set minus the second set's identities, which must give the 1,988 identities the first run
     logged;
  2. checks that every one of the first 48 rows matches a first-run graph by task id and edge
     count, and every one of the last 8 matches a second-set graph. It refuses otherwise;
  3. moves the overwritten listing to `hosts_regenerated_on_resume.json`. Of its 56 graphs, only
     setting 7's 8 were run; the other 48 were generated and never run;
  4. writes `hosts.json` with the 56 graphs actually run;
  5. recomputes `summary.json` with the study's own `analyse` from the unchanged rows;
  6. writes `record_repair.json`.
No row is changed or re-run.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r34_mip_hard_probe as R34  # noqa: E402

OUT = ROOT / 'evidence' / 'mip_hard_probe_b20r34'
FIRST_RUN_EXCLUDED = 1988
COMPLETED_BEFORE_RESTART = 48


def main():
    regenerated_path = OUT / 'hosts_regenerated_on_resume.json'
    source = regenerated_path if regenerated_path.exists() else OUT / 'hosts.json'
    second = json.loads(source.read_text())
    h2 = [GraphTask.model_validate_json(canonical(t)) for t in second['tasks']]
    excluded, scan, _ = R24.exposure(lambda m: None)
    # the scan now also names the first-run listing if this repair already ran
    first_listing = OUT / 'hosts.json'
    named_first = set()
    if regenerated_path.exists():
        named_first = RD.identities([GraphTask.model_validate_json(canonical(t))
                                     for t in json.loads(first_listing.read_text())['tasks']])
    base = set(excluded) - RD.identities(h2) - named_first
    if len(base) != FIRST_RUN_EXCLUDED:
        raise RuntimeError(f'reconstructed exclusions {len(base)} != {FIRST_RUN_EXCLUDED} logged by the first run')
    seen, h1 = set(base), []
    for i, (family, params) in enumerate(R34.SETTINGS):
        tasks, seen, _ = ADAPTERS[R34.TF].generate(R34.SEED + 10 * i, R34.PER, 'DEV', family, params, excluded=seen)
        h1 += tasks
    rows = [json.loads(l) for l in (OUT / 'rows.jsonl').read_text().splitlines() if l.strip()]
    by1, by2 = {t.task_id: t for t in h1}, {t.task_id: t for t in h2}
    run_on = []
    for k, r in enumerate(rows):
        src = by1 if k < COMPLETED_BEFORE_RESTART else by2
        t = src.get(r['task_id'])
        if t is None or len(t.edges) != r['edges'] or t.n != r['n']:
            raise RuntimeError(f'row {k} ({r["task_id"]}) does not match its graph')
        run_on.append(t)
    if len({t.task_id for t in run_on}) != len(rows) or RD.identities(run_on[:COMPLETED_BEFORE_RESTART]) & RD.identities(h2):
        raise RuntimeError('the reconstructed listing is not consistent')
    if not regenerated_path.exists():
        regenerated_path.write_text((OUT / 'hosts.json').read_text())
    R11.dump(OUT / 'hosts.json', {'seed': R34.SEED, 'settings': [{'family': f, 'params': p} for f, p in R34.SETTINGS],
                                  'tasks': [t.model_dump(mode='json') for t in run_on],
                                  'note': ('B20_R34 record repair: the graphs the rows were run on. Rows 1-48 are the '
                                           'first run\'s hosts (reconstructed); rows 49-56 are setting 7 of the set '
                                           'drawn on resume (hosts_regenerated_on_resume.json).')})
    arms = R34.arms()
    s = R34.analyse(OUT, run_on, scan, arms)
    repair = {'schema': 'genesis-b20r34-record-repair-v1', 'completed_before_restart': COMPLETED_BEFORE_RESTART,
              'first_run_excluded_identities': len(base), 'rows_checked': len(rows),
              'hosts_sha256': digest([t.model_dump(mode='json') for t in run_on]),
              'regenerated_listing': regenerated_path.name, 'regenerated_run': len(rows) - COMPLETED_BEFORE_RESTART,
              'regenerated_never_run': len(h2) - (len(rows) - COMPLETED_BEFORE_RESTART),
              'verdict_after_repair': s['verdict']}
    R11.dump(OUT / 'record_repair.json', repair)
    print(json.dumps(repair, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
