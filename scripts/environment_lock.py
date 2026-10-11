#!/usr/bin/env python3
"""Write or check requirements.lock and environment/lock_fingerprints.json (W04, R-04).

  environment_lock.py --write   regenerate from the installed environment
  environment_lock.py --check   exit 1 unless the running environment equals the lock
"""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import deployment as D  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', action='store_true')
    g.add_argument('--check', action='store_true')
    a = p.parse_args(argv)
    if a.write:
        text, fps = D.render_lock()
        D.LOCK_PATH.write_text(text)
        D.FINGERPRINTS_PATH.parent.mkdir(exist_ok=True)
        D.FINGERPRINTS_PATH.write_text(json.dumps(fps, indent=1, sort_keys=True) + '\n')
        print(f'wrote {D.LOCK_PATH} and {D.FINGERPRINTS_PATH}')
        return 0
    result = D.check_lock()
    print(json.dumps(result, indent=1))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
