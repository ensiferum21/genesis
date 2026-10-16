#!/usr/bin/env python3
"""Further exposure addenda for the frozen E1 and E1b handoff packages (B20_R31 on; B20_R28 wrote
the first with `b20r28_exposure_addendum.py`).

    exposure_addendum.py LABEL          e.g. b20r31

The packages are frozen DRAFTs, so their files are not edited. For each package this writes
`exposure_hosts_addendum_<LABEL>.json` next to it. The file lists every graph host named in any
JSON or JSONL file under evidence/ and handoff/ (`b20r23_e1b_readiness.named_hosts`) that is in
neither of these, compared by exposure identity:
  * the package's `exposure_hosts_all.json`;
  * an earlier addendum of the package (`exposure_hosts_addendum_*.json` with another label).
Hosts are written as tasks, sorted by task id. Rerunning with the same label rewrites only that
label's file and gives the same content. A custodian lists every exposure file of the package.
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r23_e1b_readiness as RD  # noqa: E402

PACKAGES = ('handoff/e1', 'handoff/e1b')


def load(path):
    return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())]


def addendum(label, named):
    out = {}
    for pkg in PACKAGES:
        d = ROOT / pkg
        target = d / f'exposure_hosts_addendum_{label}.json'
        sources = [d / 'exposure_hosts_all.json'] + sorted(p for p in d.glob('exposure_hosts_addendum_*.json')
                                                           if p != target)
        known = set()
        for p in sources:
            known |= RD.identities(load(p))
        add = sorted((t for t in named if not (RD.identities([t]) & known)), key=lambda t: t.task_id)
        out[pkg] = (target, add, [p.name for p in sources])
    return out


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1 or not re.fullmatch(r'b20r\d+', argv[0]):
        raise SystemExit('usage: exposure_addendum.py b20r<N>')
    named, scan = RD.named_hosts()
    report = {}
    for pkg, (target, add, sources) in addendum(argv[0], named).items():
        target.write_bytes(canonical([t.model_dump(mode='json') for t in add]))
        report[pkg] = {'file': target.name, 'addendum_hosts': len(add), 'compared_with': sources,
                       'by_family': {f: sum(t.family == f for t in add) for f in sorted({t.family for t in add})}}
    print(json.dumps({'scan': {k: scan[k] for k in ('files_scanned', 'distinct_hosts')}, 'packages': report}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
