#!/usr/bin/env python3
"""Print the W07 resource account of an evidence store (a DEV campaign or an evaluation).

  resource_account.py STORE_DIR [--human-seconds N --declared-by NAME] [--fairness]

The store is opened read-only in effect: nothing is written. Human time is never measured
by the machine; it appears only as a declaration naming who declared it.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.resources import account, arm_fairness  # noqa: E402
from genesis.store import Store  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('store')
    ap.add_argument('--human-seconds', type=float)
    ap.add_argument('--declared-by')
    ap.add_argument('--fairness', action='store_true', help='also check arm pairing (evaluation stores)')
    args = ap.parse_args(argv)
    with Store(Path(args.store)) as s:
        out = {'account': account(s, declared_human_seconds=args.human_seconds, declared_by=args.declared_by)}
        if args.fairness:
            out['fairness'] = arm_fairness(s)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 1 if out.get('fairness', {}).get('problems') else 0


if __name__ == '__main__':
    sys.exit(main())
