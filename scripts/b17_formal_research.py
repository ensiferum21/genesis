#!/usr/bin/env python3
"""B17: the first theory package from the pinned Lean/Mathlib workspace (DEV material only).

  b17_formal_research.py OUT_DIR [--tasks N] [--certificates K]

1. Draw a fresh DEV panel from the adopted triangle-free calibration and certify each
   task's optimum with the evaluator reference (SAT/DRAT or exact search).
2. Run the theory loop (`genesis.formal_research.theory_package.run`): gadget search,
   generated concepts and conjectures, screening, checked disproofs, recipe search,
   sandboxed acceptance, the executable method, and Lean-checked bound certificates
   for the first K tasks.
3. Replay the package from its sources alone (`replay`) and record the report.

Nothing here is sealed or confirmatory. The method gives bounds, not optima. The
statements are elementary rediscoveries.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as CAL  # noqa: E402
from genesis.domains import ADAPTERS, Unsupported  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402

PANEL_SEED = 20261017


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--tasks', type=int, default=12)
    ap.add_argument('--certificates', type=int, default=2)
    a = ap.parse_args(argv)
    out = Path(a.out)
    record = CAL.load('triangle_free_host_v1', ROOT)
    tasks, _ = CAL.calibrated_panel(record, PANEL_SEED, a.tasks, 'DEV', excluded=set())
    CAL.require_dev(tasks)
    adapter = ADAPTERS['triangle_free_host_v1']
    method_tasks = []
    for t in tasks:
        ref = adapter.reference(t, seconds=120)
        method_tasks.append((t, None if isinstance(ref, Unsupported) else ref['value']))
    t0 = time.monotonic()
    package = TP.run(out / 'package', seed=0, certificate_tasks=tasks[:a.certificates], method_tasks=method_tasks,
                     log=lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True))
    report = TP.replay(json.loads((out / 'package' / 'package.json').read_text()))
    (out / 'replay.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    summary = {'package_sha256': package['package_sha256'],
               'statements': {s['id']: s['status'] for s in package['statements']},
               'method_evaluation': package['method_evaluation'],
               'certificates': [(c['task_id'], c['status'], c['bound'], c['uses_package_lemmas'])
                                for c in package['task_certificates']],
               'replay': report['verdict'], 'replay_differences': report['differences'],
               'costs': {k: v for k, v in package['costs'].items() if k not in ('attempts', 'acceptances')},
               'calibration_record_sha256': CAL.record_digest(record)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0 if report['verdict'] == 'REPLAYED' else 1


if __name__ == '__main__':
    sys.exit(main())
