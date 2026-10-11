#!/usr/bin/env python3
"""The only sanctioned way to change toolchain/PINS.json (roadmap W04).

  revise_pins.py --reason TEXT [--set TOOL.FIELD=VALUE ...] [--known-answers KA.json]
                 [--build-record BR.json] [--init]

Appends a hash-chained entry to PINS_HISTORY.jsonl recording the old and new
values. A change to any tool's binary, binary hash or commit is refused unless
the known-answer results (toolchain/known_answers.py --json) passed and ran
exactly the new binaries. Retired binary hashes stop being verifier anchors.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import deployment as D  # noqa: E402
from genesis.common import atomic_write  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--reason', required=True)
    ap.add_argument('--set', action='append', default=[], metavar='TOOL.FIELD=VALUE')
    ap.add_argument('--known-answers', type=Path)
    ap.add_argument('--build-record', type=Path)
    ap.add_argument('--init', action='store_true', help='start the history from the current PINS.json')
    a = ap.parse_args(argv)
    pins = json.loads(D.PINS_PATH.read_text())
    now = datetime.now(timezone.utc).isoformat()
    if a.init:
        if D.HISTORY_PATH.exists():
            raise SystemExit('history already exists')
        raw, _ = D.history_entry([], pins, reason=a.reason, recorded_at=now)
        atomic_write(D.HISTORY_PATH, raw + b'\n')
        print(json.dumps({'initialized': str(D.HISTORY_PATH)}))
        return 0
    entries = D.read_history()
    problems = D.check_pins_history(pins, entries, check_recipe=False)   # a recipe change is what this may record
    if problems:
        raise SystemExit('pin history is not consistent; refusing to revise: ' + '; '.join(problems))
    new = json.loads(json.dumps(pins))
    for item in a.set:
        key, _, value = item.partition('=')
        tool, _, field = key.partition('.')
        if not tool or not field or not _:
            raise SystemExit(f'bad --set {item!r}')
        # Strings by default (hashes made of digits must stay strings); JSON only when quoted or structured.
        parsed = json.loads(value) if value[:1] in ('"', '[', '{') or value in ('true', 'false', 'null') else value
        new.setdefault(tool, {})[field] = parsed
    ka = json.loads(a.known_answers.read_text()) if a.known_answers else None
    br = json.loads(a.build_record.read_text()) if a.build_record else None
    raw, entry = D.history_entry(entries, new, reason=a.reason, known_answers=ka, build_record=br, recorded_at=now)
    trial = entries + [(raw, entry)]
    problems = D.check_pins_history(new, trial)
    if problems:
        raise SystemExit('revision refused: ' + '; '.join(problems))
    atomic_write(D.HISTORY_PATH, D.HISTORY_PATH.read_bytes() + raw + b'\n', overwrite=True)
    atomic_write(D.PINS_PATH, (json.dumps(new, indent=1, sort_keys=True) + '\n').encode(), overwrite=True)
    print(json.dumps({'seq': entry['seq'], 'changes': entry['changes'], 'retired_anchors': entry['retired_anchors']},
                     indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
