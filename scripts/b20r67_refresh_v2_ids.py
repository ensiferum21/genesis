#!/usr/bin/env python3
"""B20_R67: refresh the stored registry-v2 descriptors after the kind map moved out of the v2 core.

    PYTHONPATH=src python3 scripts/b20r67_refresh_v2_ids.py

B20_R67 moved registry v2's kind map from `candidates_v2.py` (a core file that every v2 identity hashes) to
`candidate_kinds/kinds.py` (in no identity), so that adding a kind no longer changes the other kinds' ids. The move
itself edits the core once, so every stored v2 descriptor's implementation identity, and hence its id, changes once.
This script rebuilds each stored v2 descriptor from its own kind, parameters and resource profile with the current
code, writes it back, and records old id -> new id. What a descriptor runs is unchanged: the kind module, the domain
files and the runner logic are the same; only the core file's digest changed.

Stored v2 descriptors: `handoff/e1d/baselines.json` (`milp_highs_4x`, `milp_highs_tm`). The mapping goes into
`handoff/e1d/package_index.json` (`v2_identity_refresh_b20r67`). Evidence files are never rewritten: record tests
of earlier evidence (B20_R41, R43, R63, R64, R66) compare the ids they recorded with `pre_r67_id` of the descriptor
this code builds, which accepts exactly that descriptor with the pre-R67 core digest and nothing else.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import candidates_v2 as C2  # noqa: E402
from genesis.common import digest  # noqa: E402

PKG = ROOT / 'handoff' / 'e1d'

# The v2 core file as of B20_R65's checkpoint (commit 4341806, `git show 4341806:src/genesis/candidates_v2.py`).
# Every v2 descriptor recorded before B20_R67 hashes this digest; nothing else in its identity changed.
PRE_R67_CORE = {'candidates_v2.py': '2f0d7341e01eb5b02aef45105b48601d3a865bd4617a841a0dd1097ffe0c41ed'}
PRE_R67_COMMIT = '4341806'


def pre_r67_id(desc):
    """The id a descriptor built by this code had before B20_R67: for v2, the same body with the pre-R67 core
    digest; any other descriptor is unchanged. Record tests of pre-R67 evidence compare against this, so a recorded
    id is accepted only if it names exactly the descriptor this code builds, apart from the one core edit."""
    if desc.get('schema') != C2.SCHEMA:
        return desc['descriptor_id']
    body = {k: desc[k] for k in C2.FIELDS - {'descriptor_id'}}
    body['implementation'] = dict(body['implementation'], **PRE_R67_CORE)
    return digest(body)


def pre_r67_ids(arms):
    """{name: pre-R67 id} for an `arms()` map {name: (registry, descriptor)}."""
    return {n: pre_r67_id(d) for n, (_, d) in arms.items()}


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + '\n')


def main():
    base = json.loads((PKG / 'baselines.json').read_text())
    index = json.loads((PKG / 'package_index.json').read_text())
    mapping = dict(index.get('v2_identity_refresh_b20r67', {}).get('old_to_new', {}))
    for name, d in sorted(base.items()):
        if d.get('schema') != C2.SCHEMA:
            continue
        new = C2.build_descriptor(d['kind'], d['domain'], d['parameters'], **d['resource_profile'])
        if {k: new[k] for k in ('kind', 'domain', 'parameters', 'resource_profile')} != \
                {k: d[k] for k in ('kind', 'domain', 'parameters', 'resource_profile')}:
            raise RuntimeError(f'{name}: the rebuilt descriptor differs in more than its identity')
        if new['descriptor_id'] != d['descriptor_id']:
            if pre_r67_id(new) != d['descriptor_id']:
                raise RuntimeError(f'{name}: the stored id is not this descriptor before B20_R67')
            mapping[d['descriptor_id']] = new['descriptor_id']
            changed = sorted(f for f in new['implementation'] if new['implementation'][f] != d['implementation'].get(f))
            print(f'{name}: {d["descriptor_id"][:16]} -> {new["descriptor_id"][:16]} (changed files: {changed})')
        base[name] = new
    if index.get('baselines'):
        index['baselines'] = {n: b['descriptor_id'] for n, b in base.items()}
    index['v2_identity_refresh_b20r67'] = {
        'why': ('B20_R67 moved the registry-v2 kind map out of candidates_v2.py (a core file in every v2 identity); '
                'the one-time core change re-identifies every stored v2 descriptor; what each runs is unchanged'),
        'old_to_new': mapping}
    dump(PKG / 'baselines.json', base)
    dump(PKG / 'package_index.json', index)
    return 0


if __name__ == '__main__':
    sys.exit(main())
