#!/usr/bin/env python3
"""B20_R116: a five-minute attempt on every Gset instance whose best known value Genesis has not reached (DEV,
preregistered)

    taskset -c 0 python3 scripts/b20r116_gset_attempt.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** Genesis's engine reaches the 2012-13 best known values on 27 of the 54 Gset instances at 60 s (B20_R110),
on more over all its recorded runs, and exceeds none. The papers that set those values ran for minutes. This study
gives each remaining instance five minutes on one core, with the best configuration Genesis has by its own
preregistered evidence, and records how many it reaches. Any value above a best known value is a RECORD_CANDIDATE: the
witness is kept and checked against the literature after 2013 before anything is said. It is never claimed here.

**Design (fixed before B20_R113 finished).**
  * **Instances:** every Gset instance (G1-G54) with no recorded Genesis run at or above its best known value. The
    recorded runs are B20_R106's mcx runs, B20_R109's mcx runs, B20_R110's, and B20_R113's Part B if it ran. The list
    is computed from those files at the start and recorded.
  * **Configuration per instance:** its class by B20_R105's classifier.
      - Random and toroidal classes: B20_R105's 10 s configuration.
      - Planar class: B20_R108's 10 s planar configuration (renormalisation) if B20_R113's Part A is RENORM_BETTER,
        otherwise B20_R105's. Each file is checked against its study's recorded SHA-256.
  * **Run:** `mcx-v1` at 300 s, one seed per instance from the study and the instance, through `candidates_maxcut` in
    the runc sandbox, one core.
  * **Measures:** the instances reaching their best known value; each instance's gap to it; the gain over the best
    earlier Genesis value; RECORD_CANDIDATE for any value above it. Descriptive, no hypothesis test. Validity: median
    metered CPU at least 0.9 of the budget, at most 1% failed runs.

**Expectation, stated before running.** About a third of the remaining instances reach their best known value (most
of the random ones one or two below, few of the larger planar ±1 ones); no RECORD_CANDIDATE.
**Development look (disclosed).** The list was computed once while writing, before B20_R113's Part B finished: 21
instances (G14, G15, G19, G22, G24-G26, G29-G31, G35-G39, G41, G42, G51-G54). No run was made.
**Cost.** About 300 s per remaining instance (21 or fewer): up to about 1.8 h, in one or two slices.
**Status.** DEV; licenses nothing; no record claim.
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

STUDY = 'b20r116'
BUDGET = 300.0
EV = ROOT / 'evidence'
R105, R106, R108 = EV / 'mcx_configure_b20r105', EV / 'mcx_gset_b20r106', EV / 'mcx_maturation_b20r108'
R109, R110, R113 = EV / 'gset_replication_b20r109', EV / 'gset_long_b20r110', EV / 'planar_renorm_b20r113'
SLICE_S, PAUSED = 6600, 3


def _rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def best_earlier():
    """{instance: the best value of any recorded Genesis mcx run}."""
    out = {}

    def offer(g, v):
        if v is not None:
            out[g] = max(out.get(g, v), v)
    for r in _rows(R106 / 'rows.jsonl'):
        for arm in ('chosen@1', 'chosen@10', 'default@1', 'default@10'):
            offer(r['instance'], r['runs'][arm]['value'])
    for r in _rows(R109 / 'rows.jsonl'):
        for v in r['new']['mcx']:
            offer(r['instance'], v)
    for r in _rows(R110 / 'rows.jsonl'):
        offer(r['instance'], r['value'])
    s113 = R113 / 'summary.json'
    if s113.exists():
        s = json.loads(s113.read_text())
        for r in (s.get('part_b') or {}).get('rows', []):
            offer(r['instance'], r['value'])
    return out


def checked(d):
    c = json.loads((d / 'configs.json').read_text())
    s = json.loads((d / 'summary.json').read_text())
    if digest(c) != s['configs_sha256'] or not s['valid']:
        raise SystemExit(f'{d.name}: configs.json is not the recorded one, or the study is not valid')
    return c


def configurations():
    """{class: configuration at 10 s} by the preregistered rule."""
    c105 = checked(R105)
    out = {cls: c105['chosen'][cls]['10'] for cls in ('random', 'toroidal', 'planar')}
    s113 = R113 / 'summary.json'
    if s113.exists() and json.loads(s113.read_text())['part_a']['label'] == 'RENORM_BETTER':
        out['planar'] = checked(R108)['chosen']['planar']['10']
    return out, c105['classifier']


def analyse(rows, best):
    return {'instances': len(rows), 'reach_best_known': sum(r['value'] >= best[r['instance']] for r in rows),
            'reached': [r['instance'] for r in rows if r['value'] >= best[r['instance']]],
            'gains_over_earlier': sum(r['value'] > r['earlier'] for r in rows),
            'gaps': {r['instance']: best[r['instance']] - r['value'] for r in rows},
            'mean_fraction': statistics.mean(r['value'] / best[r['instance']] for r in rows) if rows else None,
            'record_candidates': [{'instance': r['instance'], 'value': r['value'], 'best_known': best[r['instance']]}
                                  for r in rows if r['value'] > best[r['instance']]]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (EV / 'gset_attempt_b20r116').resolve():
        raise SystemExit('the registered output is evidence/gset_attempt_b20r116')
    cfgs, classifier = configurations()
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
    plan_path = out / 'plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    else:
        earlier = best_earlier()
        todo = [g for g in (f'G{k}' for k in range(1, 55)) if earlier.get(g, 0) < best[g]]
        plan = {'instances': todo, 'earlier': {g: earlier.get(g) for g in todo}, 'configurations': cfgs}
        plan_path.write_text(json.dumps(plan, indent=1, sort_keys=True) + '\n')
    log(f'{STUDY}; pinned to CPU {cpu}; {len(plan["instances"])} instances: {plan["instances"]}')
    path = out / 'rows.jsonl'
    done = {r['instance']: r for r in _rows(path)} if path.exists() else {}
    desc = {}
    for t in GS.tasks([int(g[1:]) for g in plan['instances']]):
        g = t.task_id.split('-')[1]
        if g in done:
            continue
        if time.monotonic() - t0 > SLICE_S:
            log(f'time slice used ({SLICE_S} s): paused after {len(done)} instances')
            return PAUSED
        cls = R105M.classify(classifier, R105M.features(t))
        cfg = plan['configurations'][cls]
        key = json.dumps(cfg, sort_keys=True)
        if key not in desc:
            desc[key] = CM.build_descriptor('mcx-v1', {'cpu_seconds': BUDGET, 'config': cfg}, cpu_seconds=BUDGET,
                                            wall_seconds=int(2 * BUDGET) + 120)
        d = desc[key]
        r = CM.run(t, d, seed=int(digest({'study': STUDY, 'task': t.task_id})[:12], 16), expected_id=d['descriptor_id'],
                   isolation='runc')
        ok = r.get('status') == 'SUCCESS'
        row = {'instance': g, 'class': cls, 'config': cfg, 'value': r['result']['value'] if ok else None,
               'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'), 'descriptor': d['descriptor_id'],
               'side': r['result']['side'] if ok else None, 'earlier': plan['earlier'][g]}
        done[g] = row
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f"{g} [{cls}] best known {best[g]}: 300 s {row['value']} (best earlier {row['earlier']})")
    rows = [done[g] for g in plan['instances'] if done.get(g, {}).get('value') is not None]
    res = analyse(rows, best)
    cpus = [r['cpu_ns'] / 1e9 / BUDGET for r in rows if r['cpu_ns']]
    fails = len(plan['instances']) - len(rows)
    valid = bool(cpus) and statistics.median(cpus) >= 0.9 and fails <= 0.01 * max(1, len(plan['instances']))
    summary = dict(res, study=STUDY, schema='genesis-b20r116-gset-attempt-v1', valid=valid,
                   cpu_median=statistics.median(cpus) if cpus else None, failed_runs=fails, plan=plan,
                   best_known_sha256=digest(json.loads((GS.DATA / 'best_known.json').read_text())),
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; reached {res['reach_best_known']} of {res['instances']}; record candidates "
        f"{len(res['record_candidates'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
