#!/usr/bin/env python3
"""B20_R6 design pilot (DEV): search for an equational family with selection headroom (B20R3-OPEN-1).

    b20r6_family_search.py OUT_DIR VARIANT [VARIANT ...]
    b20r6_family_search.py OUT_DIR --summary

A design diagnostic, not a study. It licenses no claim and chooses nothing by itself. It asks
whether, on a family not yet tried, *any* selection from the research pool could beat the fixed
smallest-first policy under the calibrated cap. The method is the B20_R3 pilot's round 1
(``b20r3_headroom_pilot.pilot``, unchanged): EXHAUST, FIXED@CAP (cap = 0.25 x exhaust CPU),
EMPTY and ORACLE (dependency closure of the lemmas EXHAUST target proofs used; optimistic, built
from the targets) on 12 targets per range, 1 s per target, 8 premises.

Families tried, fixed before running (chosen because the B20_R3 pilot explained why the old ones
had no room: Huntington's key lemma is its smallest equation, Sheffer barely uses libraries, the
others sit at floor or ceiling):

  * ba_robbins: Boolean algebra in Robbins' basis (commutativity, associativity, Robbins'
    equation). Every Robbins algebra is Boolean (McCune 1997), so the two-element algebra
    decides truth exactly; but proving even small identities from these axioms is hard for E,
    so small pool equations are often unprovable at 1 s and smallest-first spends its cap on
    failures. Ranges as Huntington's, plus larger targets (``:t6``).
  * bool_ring: Boolean rings (with zero and negation). Commutativity of multiplication is a
    classic consequence that needs characteristic 2 first; there are many small, cheap and
    irrelevant zero/negation identities for smallest-first to spend its cap on.

Verdict per variant, fixed here before running (12 targets per range):
  SELECTION_HEADROOM   some range has ORACLE - FIXED@CAP >= 2, EXHAUST - EMPTY >= 2, EMPTY <= 10,
                       and ORACLE's own research cost <= the cap (achievable under the same cap);
  HEADROOM_OVER_CAP    the same, except ORACLE costs more than the cap;
  NO_HEADROOM          otherwise.
Every target and pool statement is written to OUT_DIR, so later studies count it as exposed.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r3_headroom_pilot as H  # noqa: E402

VARIANTS = {
    'ba_robbins': {'pool_max': 5, 'max_term': 5, 'grid': [(5, 8), (6, 9), (7, 10)]},
    'ba_robbins:t6': {'pool_max': 5, 'max_term': 6, 'grid': [(9, 12), (10, 12)]},
    'bool_ring': {'pool_max': 4, 'max_term': 4, 'grid': [(5, 8), (6, 8)]},
    'bool_ring:t5': {'pool_max': 4, 'max_term': 5, 'grid': [(7, 10), (8, 10)]},
}


def verdict(d):
    best = 'NO_HEADROOM'
    for r in d['ranges']:
        sel, lib = r['oracle'] - r['fixed_cap'], r['exhaust'] - r['empty']
        if sel >= 2 and lib >= 2 and r['empty'] <= 10:
            if r['oracle_cost_s'] <= d['cap_s']:
                return 'SELECTION_HEADROOM'
            best = 'HEADROOM_OVER_CAP'
    return best


def summarize(out, log):
    rows = {}
    for f in sorted(out.glob('*.json')):
        if f.name == 'summary.json':
            continue
        d = json.loads(f.read_text())
        rows[d['variant']] = {'verdict': verdict(d), 'cap_s': d['cap_s'], 'pool': len(d['pool']),
                              'exhaust_library': len(d['exhaust']['library']),
                              'fixed_cap_library': len(d['fixed_cap']['library']),
                              'ranges': [{k: r[k] for k in ('range', 'empty', 'fixed_cap', 'exhaust', 'oracle',
                                                            'oracle_cost_s')} for r in d['ranges']]}
    H.dump(out / 'summary.json', {'variants': rows, 'status': 'DESIGN_PILOT_DEV',
                                  'rule': 'see the script docstring (fixed before running)'})
    for v, r in rows.items():
        log(f'{v}: {r["verdict"]}  ' + '; '.join(f'{x["range"]}: E{x["empty"]} F{x["fixed_cap"]} X{x["exhaust"]} '
                                                    f'O{x["oracle"]} ({x["oracle_cost_s"]}s/{r["cap_s"]}s)'
                                                    for x in r['ranges']))


def main(argv=None):
    a = argv or sys.argv[1:]
    out = Path(a[0])
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    if '--summary' in a:
        summarize(out, log)
        return 0
    H.PILOT.update(VARIANTS)
    for v in a[1:]:
        if v not in VARIANTS:
            raise SystemExit(f'unknown variant {v}; fixed set: {sorted(VARIANTS)}')
        H.pilot(v, out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
