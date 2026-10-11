#!/usr/bin/env python3
"""Proof-term sizes for the B18 recovery arms, by re-acceptance of each arm package.

The run's first extraction read theorem values with `ConstantInfo.value?`. That treats
theorems as opaque and returned no value, so every size came out as 0. The fix reads them
with `allowOpaque := true`. This script re-accepts each arm package from its sources and
records the size of every fresh-statement proof term. It also corrects `comparison.json`
in place and notes the correction there.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.formal_research import checker as C  # noqa: E402


def main(evidence):
    evidence = Path(evidence)
    comp_path = evidence / 'recovery' / 'comparison.json'
    comp = json.loads(comp_path.read_text())
    sizes_out = {}
    for arm in comp['arms']:
        pkg = json.loads((evidence / 'recovery' / f'arm_{arm}' / 'package.json').read_text())
        mods = [{k: m[k] for k in ('name', 'source', 'trusted')} for m in pkg['modules']]
        r = C.accept(mods, pkg['bindings'])
        if r['status'] != 'CHECKED':
            raise SystemExit(f'arm {arm} did not re-accept: {r.get("reason")}')
        sizes = {d['name']: d['value_nodes'] for d in r['declarations'] if d['name'].endswith('.proof')}
        st = {s['id']: s for s in pkg['statements']}
        per = {}
        for sid, row in comp['arms'][arm]['per_statement'].items():
            const = st[sid].get('proof_const')
            row['proof_nodes'] = sizes.get(const) if const else None
            per[sid] = row['proof_nodes']
        comp['arms'][arm]['proof_nodes_fresh'] = sum(v for sid, v in per.items()
                                                     if v and comp['arms'][arm]['per_statement'][sid]['status'] == 'CHECKED')
        sizes_out[arm] = per
        print(arm, comp['arms'][arm]['proof_nodes_fresh'], per)
    comp['corrections'] = [{'field': 'proof_nodes', 'reason': 'theorem values were read as opaque (0 nodes); '
                            'recomputed by re-acceptance with allowOpaque := true (scripts/b18_proof_sizes.py)'}]
    comp_path.write_text(json.dumps(comp, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    (evidence / 'recovery' / 'proof_sizes.json').write_text(json.dumps(sizes_out, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
