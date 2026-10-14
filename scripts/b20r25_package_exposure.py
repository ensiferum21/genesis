#!/usr/bin/env python3
"""B20_R25: the handoff packages' exposure lists, split into sources of at most 400 hosts (preventive).

    PYTHONPATH=src python3 scripts/b20r25_package_exposure.py

The custodian's exposure screen (exposure.extract_hosts) refuses a JSON source with more than 1,000,000 values
("adjudicate externally"). The B20_R25 rehearsal's first attempt stopped there because its own host list was
not deduplicated (2,741 entries for 1,574 hosts). The packages' deduplicated list (handoff/*/exposure_hosts_all.json,
1,544 hosts, about 587,000 values) was accepted; this was checked after first assuming otherwise. At about 380
values per host the limit would be reached near 2,600 hosts, and the list grows with every DEV run, so both
packages now ship exposure_hosts_part_NN.json files of at most 400 hosts and an exposure_sources.json fragment to
paste into a manifest. The list is refreshed to every graph host now named under evidence/ and handoff/, the
regenerated E1 hosts and every calibration's hosts (B20_R25's pilot and rehearsal hosts included). Before writing,
it checks that exposure.build_registry accepts the parts and that they hold exactly the refreshed list, and it
records whether one file would still be accepted.
"""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, digest  # noqa: E402
from genesis.exposure import build_registry  # noqa: E402

import b20r24_repilots as RP  # noqa: E402

PER_PART = 400
PACKAGES = (ROOT / 'handoff' / 'e1', ROOT / 'handoff' / 'e1b')


def main():
    _, scan, named = RP.exposure(print)
    hosts = {}
    for t in named:
        d = t.model_dump(mode='json')
        hosts[(d['domain'], digest(d))] = d
    hosts = sorted(hosts.values(), key=lambda t: (t['domain'], t['task_id'], digest(t)))
    parts = [hosts[i:i + PER_PART] for i in range(0, len(hosts), PER_PART)]
    names = [f'exposure_hosts_part_{i:02d}.json' for i in range(len(parts))]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, part in zip(names, parts):
            (tmp / name).write_bytes(canonical(part))
        sources = [{'kind': 'json', 'path': n, 'label': f'builder-named hosts ({n})'} for n in names]
        index, record = build_registry({'schema': 'genesis-exposure-manifest-v1', 'sources': sources}, tmp, ROOT)
        (tmp / 'all.json').write_bytes(canonical(hosts))
        try:
            build_registry({'schema': 'genesis-exposure-manifest-v1',
                            'sources': [{'kind': 'json', 'path': 'all.json', 'label': 'one file'}]}, tmp, ROOT)
            single = 'accepted'
        except ValueError as exc:
            single = f'refused: {exc}'
    if sum(len(p) for p in parts) != len(hosts):
        raise RuntimeError('the parts do not hold the list')
    info = {'hosts': len(hosts), 'distinct_graphs': record['graphs'], 'parts': names, 'per_part_max': PER_PART,
            'scan': scan, 'one_file_screen': single, 'registry_root': record['root']}
    for pkg in PACKAGES:
        old = pkg / 'exposure_hosts_all.json'
        if old.exists():
            old.unlink()
        for f in pkg.glob('exposure_hosts_part_*.json'):
            f.unlink()
        for name, part in zip(names, parts):
            (pkg / name).write_bytes(canonical(part))
        (pkg / 'exposure_sources.json').write_text(json.dumps(
            {'note': ('add these entries to the custodian exposure manifest "sources"; paths are relative to the '
                      'manifest directory, so copy the part files next to it'), 'sources': sources},
            indent=1, sort_keys=True) + '\n')
        index_path = pkg / 'package_index.json'
        idx = json.loads(index_path.read_text())
        idx.pop('exposure_hosts_all', None)
        idx['exposure_hosts'] = info
        index_path.write_text(json.dumps(idx, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in info.items() if k != 'scan'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
