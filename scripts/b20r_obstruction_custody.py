#!/usr/bin/env python3
"""B20_R1 Repair D: a custody-complete re-run of the B19 joint certification (DEV).

    b20r_obstruction_custody.py OUT_DIR [--budget 60]

The B19 obstruction evaluation (evidence/discovery_b19/obstruction/evaluation.json) kept
bounds and verdict summaries but not the final witnesses or the exact LP certificates
(finding B20-REVIEW-04). That record is history and is not modified. This script is a NEW
execution on the same DEV task specification (HARD settings and HARD_SEED of
scripts/b19_discovery.py, the same represent-and-repair witness method and budget). It
runs only the joint arm, because the finding concerns its custody; the B19 reference arm
is not re-run. Every bound is written as a certificate bundle v2 with its objects BEFORE
the summary row, and afterwards every bundle is replayed in a separate process with the
producers disabled (scipy blocked, SAT solver refused). Outcomes can differ from B19
(time-based witness search); differences are reported, not reconciled.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.verification import certificates as CB  # noqa: E402
from genesis.verification.lp_dual import checker_identity  # noqa: E402

HARD_SEED = 20261021
HARD = [(30, 0.3), (36, 0.25), (40, 0.2)]

REPLAY_CHILD = r'''
import json, sys
sys.modules['scipy'] = None
from pathlib import Path
from genesis.verification import certificates as CB
d = Path(sys.argv[1]); out = []
with CB.checker_only():
    for b in sorted((d / 'bundles').glob('*.json')):
        bundle = json.loads(b.read_bytes())
        def get(h):
            data = (d / 'objects' / h).read_bytes()
            if CB._sha(data) != h:
                raise ValueError('object corruption')
            return data
        r = CB.replay(bundle, get)
        out.append({'bundle': b.stem, 'task_sha256': bundle['problem']['task_sha256'], 'recorded': bundle['status'],
                    'replayed': r['status'], 'problems': r['problems']})
print(json.dumps(out))
'''


def seed_of(*parts):
    return int(digest({'p': parts})[:8], 16)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--budget', type=float, default=60.0)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    rep = next(r for r in R.proposals() if r['id'] == 'cross_2')
    adapter = ADAPTERS['triangle_free_host_v1']
    old = json.loads((ROOT / 'evidence' / 'discovery_b19' / 'obstruction' / 'evaluation.json').read_text())
    old_by_task = {r['task_id']: r['joint'] for r in old['rows']}
    rows = []
    for n, p in HARD:
        tasks, _, _ = adapter.generate(HARD_SEED, 4, 'DEV', 'erdos', {'n': n, 'p': p})
        for t in tasks:
            t1 = time.monotonic()
            rr = R.represent_and_repair(t.n, t.edges, rep, R.tf_add_ok, cpu_seconds=1.0, seed=seed_of('ob', t.task_id))
            joint = O.certify(t, rr['witness'], seconds=a.budget - (time.monotonic() - t1))
            h = CB.persist_dir(out, joint['bundle'], joint['objects'])           # custody before any summary
            prev = old_by_task.get(t.task_id, {})
            rows.append({'task_id': t.task_id, 'n': n, 'p': p, 'edges': len(t.edges), 'bundle_sha256': h,
                         'status': joint['status'], 'lower': joint['lower'], 'upper': joint['upper'],
                         'gap': joint['gap'], 'upper_method': joint['bundle']['upper']['method'],
                         'wall_s': round(time.monotonic() - t1, 2),
                         'b19_recorded': {k: prev.get(k) for k in ('status', 'lower', 'upper', 'upper_method')}})
            log(f'{t.task_id}: {joint["status"]} {joint["lower"]}..{joint["upper"]} via '
                f'{joint["bundle"]["upper"]["method"]} (B19 recorded {prev.get("status")} '
                f'{prev.get("lower")}..{prev.get("upper")})')
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    child = subprocess.run([sys.executable, '-c', REPLAY_CHILD, str(out)], capture_output=True, text=True, env=env,
                           timeout=3600)
    if child.returncode != 0:
        raise SystemExit('replay child failed: ' + child.stderr[-2000:])
    replays = json.loads(child.stdout)
    by_bundle = {r['bundle']: r for r in replays}
    for r in rows:
        r['replay'] = by_bundle[r['bundle_sha256']]['replayed']
        r['replay_problems'] = by_bundle[r['bundle_sha256']]['problems']
    summary = {'tasks': len(rows), 'budget_wall_s': a.budget,
               'optimality_checked': sum(r['status'] == 'OPTIMALITY_CHECKED' for r in rows),
               'by_method': {m: sum(r['upper_method'] == m for r in rows) for m in sorted({r['upper_method'] for r in rows})},
               'replayed_as_recorded': sum((r['replay'] == 'OPTIMALITY_CHECKED') == (r['status'] == 'OPTIMALITY_CHECKED')
                                           and r['replay'] in ('OPTIMALITY_CHECKED', 'BOUNDS_CHECKED')
                                           and not r['replay_problems'] for r in rows),
               'b19_recorded_optimality_checked': sum(r['b19_recorded']['status'] == 'OPTIMALITY_CHECKED' for r in rows),
               'differences_from_b19': [r['task_id'] for r in rows
                                        if (r['status'], r['lower'], r['upper']) != (r['b19_recorded']['status'],
                                                                                      r['b19_recorded']['lower'],
                                                                                      r['b19_recorded']['upper'])],
               'lp_checker': checker_identity(), 'code_identity': code_identity(ROOT)['sha256'],
               'wall_s': round(time.monotonic() - t0, 1),
               'scope': 'DEV; joint arm only; new execution; the B19 record is unchanged history'}
    (out / 'evaluation.json').write_text(json.dumps({'split': 'DEV', 'seed': HARD_SEED, 'rows': rows,
                                                     'summary': summary}, indent=1, sort_keys=True) + '\n')
    log(json.dumps(summary))
    return 0 if summary['replayed_as_recorded'] == summary['tasks'] else 1


if __name__ == '__main__':
    sys.exit(main())
