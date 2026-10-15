#!/usr/bin/env python3
"""B20_R28: exposure addenda for the frozen E1 and E1b handoff packages.

    b20r28_exposure_addendum.py

`handoff/e1/exposure_hosts_all.json` and `handoff/e1b/exposure_hosts_all.json` (B20_R24) list
every host the builder had named or generated: 1,544 hosts. B20_R26–R28 then named new DEV hosts,
some of them in an e1-v2 setting (erdos n30 p0.3) and all of the B20_R28 hosts in the e1b settings.
A custodian must exclude them as well.

The packages are frozen DRAFTs, so their files are not edited. This script writes, next to each
package, `exposure_hosts_addendum_b20r28.json`: every graph host named in any JSON or JSONL file
under evidence/ and handoff/ (`b20r23_e1b_readiness.named_hosts`) that is not already in the
package's `exposure_hosts_all.json` (compared by exposure identity), as tasks, sorted by task id.
A custodian lists both files in its exposure manifest.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r23_e1b_readiness as RD  # noqa: E402


def main():
    named, scan = RD.named_hosts()
    out = {}
    for pkg in ('handoff/e1', 'handoff/e1b'):
        have = [GraphTask.model_validate_json(canonical(t))
                for t in json.loads((ROOT / pkg / 'exposure_hosts_all.json').read_text())]
        known = RD.identities(have)
        add = sorted((t for t in named if not (RD.identities([t]) & known)), key=lambda t: t.task_id)
        path = ROOT / pkg / 'exposure_hosts_addendum_b20r28.json'
        path.write_bytes(canonical([t.model_dump(mode='json') for t in add]))
        out[pkg] = {'package_hosts': len(have), 'addendum_hosts': len(add),
                    'by_domain': {d: sum(t.domain == d for t in add) for d in sorted({t.domain for t in add})}}
    print(json.dumps({'scan': {k: scan[k] for k in ('files_scanned', 'distinct_hosts')}, 'packages': out}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
