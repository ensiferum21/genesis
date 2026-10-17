#!/usr/bin/env python3
"""B20_R59: internal replication of B20_R57 (sum-free rows on hosts hard for the conventional route; DEV).

    taskset -c 0 python3 scripts/b20r59_sf_replication.py OUT_DIR      run (resumable) and analyse

**Why.** B20_R57 found CERTIFICATION_UTILITY (22 vs 14 of 40, p 0.0039) and BOUND_UTILITY for B20_R55's transferred
rows. One study is one draw. This repeats it unchanged on fresh hosts before anything rests on it.

**Protocol.** B20_R57's script, imported and run unchanged except for its seeds: fresh candidate seeds 20265901 and
20265911 (B20_R57: 20265701, 20265711) and bootstrap seed 20265999. The screen (route a alone, 20 s), the 40 included
hosts, both routes (60 s), both verdict rules and every threshold are B20_R57's.

**Verdict (fixed here before running).** REPLICATED iff the primary verdict is CERTIFICATION_UTILITY again;
NOT_REPLICATED otherwise (DEFECT_FOUND passes through). The secondary bound verdict is reported. Same operator and
machine: an internal replication only; roadmap E6 needs an independent operator.

**Development looks.** None on these seeds. Run pinned to one core.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r57_sf_hard_certification as R57  # noqa: E402

SEEDS = (20265901, 20265911)
BOOT_SEED = 20265999


def replication_verdict(summary):
    v = summary['verdict']
    return {'replication': 'REPLICATED' if v == 'CERTIFICATION_UTILITY' else
            ('DEFECT_FOUND' if v == 'DEFECT_FOUND' else 'NOT_REPLICATED'),
            'primary': v, 'bound': summary['bound']['verdict'], 'original': 'B20_R57'}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    R57.SEEDS, R57.BOOT_SEED = SEEDS, BOOT_SEED
    R57.main([str(out)])
    s = json.loads((out / 'summary.json').read_text())
    r = replication_verdict(s)
    (out / 'replication.json').write_text(json.dumps(r, indent=1, sort_keys=True) + '\n')
    print(f'replication {r}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
