#!/usr/bin/env python3
"""Execution helper for the frozen b20r_e3_fresh.py Lean phase: run one shard of it.

    b20r_e3_lean_shard.py OUT_DIR SHARD COUNT

Uses the frozen script's own selection (``lean_selection``) and replay call
(``custody.replay_target`` with the same trust context and names); processes the selected
records whose position modulo COUNT equals SHARD, skipping those already replayed. It
changes no rule of the study, only how many processes share the work.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r_e3_fresh as E  # noqa: E402


def main(argv=None):
    out, shard, count = (argv or sys.argv[1:])[0], int((argv or sys.argv[1:])[1]), int((argv or sys.argv[1:])[2])
    out = Path(out)
    objects = E.C.ObjectStore(out / 'objects')
    tc = {'checker_identity': E.C.checker_identity()['identity']}
    done = out / 'lean'
    done.mkdir(exist_ok=True)
    sel = E.lean_selection(out)
    t0 = time.monotonic()
    for i, (f, rid) in enumerate(sel):
        if i % count != shard or (done / f'{rid}.json').exists():
            continue
        d = json.loads(f.read_text())
        rec = next(r for r in d['targets'] if r['record_id'] == rid)
        res = E.C.replay_target(rec, d['manifest'], objects, task_statement=rec['statement'], trust_context=tc,
                                name=f'e3r{rid[:12]}')
        E.dump(done / f'{rid}.json', dict(res, run=str(f.relative_to(out))))
        print(f'[{time.monotonic() - t0:7.1f}s] shard {shard}: {i + 1}/{len(sel)} {f.parent.name}/{f.stem}: '
              f'{res["status"]}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
