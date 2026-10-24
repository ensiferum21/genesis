#!/usr/bin/env python3
"""B20_R123: three more five-minute seeds on each Gset instance still below its best known value (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r123_gset_seeds.py OUT_DIR     run ALONE (resumable per run), then analyse

**Why.** After B20_R116, Genesis's engine matches the 2012-13 best known values on 40 of the 54 Gset instances and
exceeds none. Of the 14 left, 11 are one unit short. On the 2,000-vertex planar instances, one 300 s run was not
reliably better than one 60 s run: one seed per instance and budget cannot separate time from luck. This study gives
each remaining instance three more independent 300 s runs with the same configurations, which tells how many of the
14 more seeds close and how wide the spread of a single 300 s run is. Any value above a best known value is a
RECORD_CANDIDATE: the witness is kept and checked against the literature after 2013 before anything is said. It is
never claimed here.

**Design (fixed before running).**
  * **Instances:** every Gset instance (G1-G54) with no recorded Genesis run at or above its best known value. The
    recorded runs are those of B20_R106, R109, R110, R113 (Part B) and R116. The list is computed from those files at
    the start and recorded.
  * **Configuration per instance:** B20_R116's recorded configuration for its class (by B20_R105's classifier), read
    from B20_R116's plan and checked against its summary.
  * **Runs:** `mcx-v1` at 300 s, three seeds per instance (k = 0, 1, 2; each seed from the study, the instance and k,
    distinct from B20_R116's), through `candidates_maxcut` in the runc sandbox, one core.
  * **Measures:**
      - instances reaching the best known value in at least one of the three runs, and in how many;
      - per instance, the spread of the four 300 s values (these three and B20_R116's) and their mean gap to the
        best known value;
      - RECORD_CANDIDATE for any value above it.
    Descriptive, no hypothesis test.
  * **Validity:** median metered CPU at least 0.9 of the budget, at most 1% failed runs.

**Development look (disclosed).** The list was computed once while writing: 14 instances (G14, G15, G22, G24, G26,
G31, G35, G36, G38, G41, G42, G51, G53, G54). No run was made.

**Expectation, stated before running.** About a third of the 14 reach their best known value in at least one of three
runs, more of the one-short instances than of G36, G38 and G42. The spread of single 300 s runs on the 2,000-vertex
planar instances is about 10. No RECORD_CANDIDATE.
**Cost.** 14 x 3 x about 305 s, about 3.6 h, in two slices. **Status.** DEV; licenses nothing; no record claim.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
import b20r116_gset_attempt as R116  # noqa: E402

STUDY = 'b20r123'
BUDGET = 300.0
SEEDS = 3
R116_DIR = ROOT / 'evidence' / 'gset_attempt_b20r116'
SLICE_S, PAUSED = 6600, 3


def best_earlier():
    """{instance: best recorded Genesis value}, B20_R116's rule plus B20_R116's own runs."""
    out = R116.best_earlier()
    for r in R116._rows(R116_DIR / 'rows.jsonl'):
        if r['value'] is not None:
            out[r['instance']] = max(out.get(r['instance'], r['value']), r['value'])
    return out


def configurations():
    s = json.loads((R116_DIR / 'summary.json').read_text())
    plan = json.loads((R116_DIR / 'plan.json').read_text())
    if not s['valid'] or s['plan'] != plan:
        raise SystemExit('B20_R116 is not valid, or its plan is not the recorded one')
    return plan['configurations']


def run_seed(task_id, k):
    return int(digest({'study': STUDY, 'task': task_id, 'k': k})[:12], 16)


def analyse(rows, best, r116):
    """rows: one per (instance, k) with a value; r116: {instance: B20_R116's value}."""
    by = {}
    for r in rows:
        by.setdefault(r['instance'], []).append(r['value'])
    out = {}
    for g, vs in by.items():
        allv = vs + ([r116[g]] if r116.get(g) is not None else [])
        out[g] = {'values': vs, 'reached_runs': sum(v >= best[g] for v in vs), 'best': max(vs),
                  'spread_300s': max(allv) - min(allv), 'mean_gap_300s': statistics.mean(best[g] - v for v in allv)}
    return {'per_instance': out, 'instances': len(out),
            'reach_best_known': sum(o['reached_runs'] > 0 for o in out.values()),
            'reached': sorted((g for g, o in out.items() if o['reached_runs'] > 0), key=lambda g: int(g[1:])),
            'record_candidates': [{'instance': r['instance'], 'k': r['k'], 'value': r['value'],
                                   'best_known': best[r['instance']]} for r in rows if r['value'] > best[r['instance']]]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'gset_seeds_b20r123').resolve():
        raise SystemExit('the registered output is evidence/gset_seeds_b20r123')
    cfgs = configurations()
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r105_mcx_configure as R105M
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    best = GS.best_known()
    classifier = R116.checked(R116.R105)['classifier']
    plan_path = out / 'plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    else:
        earlier = best_earlier()
        todo = [g for g in (f'G{k}' for k in range(1, 55)) if earlier.get(g, 0) < best[g]]
        plan = {'instances': todo, 'earlier': {g: earlier.get(g) for g in todo}, 'configurations': cfgs}
        plan_path.write_text(json.dumps(plan, indent=1, sort_keys=True) + '\n')
    log(f'{STUDY}; pinned to CPU {cpu}; {len(plan["instances"])} instances x {SEEDS} seeds: {plan["instances"]}')
    path = out / 'rows.jsonl'
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r['instance'], r['k'])] = r
    desc = {}
    for t in GS.tasks([int(g[1:]) for g in plan['instances']]):
        g = t.task_id.split('-')[1]
        cls = R105M.classify(classifier, R105M.features(t))
        cfg = plan['configurations'][cls]
        for k in range(SEEDS):
            if (g, k) in done:
                continue
            if time.monotonic() - t0 > SLICE_S:
                log(f'time slice used ({SLICE_S} s): paused after {len(done)} runs')
                return PAUSED
            key = json.dumps(cfg, sort_keys=True)
            if key not in desc:
                desc[key] = CM.build_descriptor('mcx-v1', {'cpu_seconds': BUDGET, 'config': cfg}, cpu_seconds=BUDGET,
                                                wall_seconds=int(2 * BUDGET) + 120)
            d = desc[key]
            r = CM.run(t, d, seed=run_seed(t.task_id, k), expected_id=d['descriptor_id'], isolation='runc')
            ok = r.get('status') == 'SUCCESS'
            row = {'instance': g, 'k': k, 'class': cls, 'config': cfg, 'value': r['result']['value'] if ok else None,
                   'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'), 'descriptor': d['descriptor_id'],
                   'side': r['result']['side'] if ok else None}
            done[(g, k)] = row
            with path.open('a') as f:
                f.write(json.dumps(row, sort_keys=True) + '\n')
            log(f"{g} [{cls}] seed {k} best known {best[g]}: 300 s {row['value']}")
    rows = [r for r in done.values() if r['value'] is not None]
    r116 = {r['instance']: r['value'] for r in R116._rows(R116_DIR / 'rows.jsonl')}
    res = analyse(rows, best, r116)
    cpus = [r['cpu_ns'] / 1e9 / BUDGET for r in rows if r['cpu_ns']]
    fails = len(done) - len(rows)
    valid = bool(cpus) and statistics.median(cpus) >= 0.9 and fails <= 0.01 * max(1, len(done))
    summary = dict(res, study=STUDY, schema='genesis-b20r123-gset-seeds-v1', valid=valid, plan=plan,
                   cpu_median=statistics.median(cpus) if cpus else None, failed_runs=fails,
                   best_known_sha256=digest(json.loads((GS.DATA / 'best_known.json').read_text())),
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; reached {res['reach_best_known']} of {res['instances']} ({res['reached']}); record "
        f"candidates {len(res['record_candidates'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
