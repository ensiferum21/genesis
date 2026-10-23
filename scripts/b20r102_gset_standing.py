#!/usr/bin/env python3
"""B20_R102: where the pinned tools stand against Gset's published records (the open-record track's calibration;
DEV, preregistered)

    taskset -c 0 python3 scripts/b20r102_gset_standing.py OUT_DIR     run ALONE (resumable; pauses before the
                                                                      background limit), then analyse

**Why.** `docs/OPEN_RECORDS_PLAN.md`: every Genesis result so far is on hosts generated for its own studies. Gset
(G1-G54) has published best-known values. Before any Genesis method is judged there, the target must be measured:
how far below the records the strongest pinned tools end at equal, short budgets on one core, family by family. A
Genesis method later has to beat these numbers, not the records alone.

**Design (fixed before running).**
  * **Instances.** G1-G54, pinned (`gset.tasks()`: the archive and every member by SHA-256), in order.
  * **Arms** (all through `candidates_maxcut` in the runc sandbox, one core):
      - `mqlib-maxcut-v1` BURER2002 (the best single heuristic in Dunning et al. 2018) at 1 s and 10 s;
      - `dsb-maxcut-v1` (discrete simulated bifurcation, the physics arm) at 1 s and 10 s;
      - MQLib's other ten max-cut heuristics at 10 s (for the per-instance virtual best, VBS).
    One seed per (instance, arm, budget), from the study, instance, arm and budget.
  * **Measures.** For each run, the fraction f = value / best known (`data/gset/best_known.json`). Per arm and
    budget: mean f overall and per family (random, toroidal, planar), and the number of instances reaching the best
    known value. The VBS at 10 s over the twelve arms. Validity: median metered CPU at least 0.9 of each budget, and
    at most 1% failed runs.
  * **Record rule.** A run above an instance's best known value is labelled RECORD_CANDIDATE. It is never a record
    claim: the witness is kept, and the value has to be checked against the paper that set the record (the table's
    policy). No hypothesis is tested; the study is a calibration.

**Development look (disclosed).** While building the domain, BURER2002 and dSB ran in-process at 2 s on G1, G11, G14,
G22, G32, G43 and G48 (22 Oct 2026). Both ended at 98.6-100% of the best known; the toroidal ±1 instances (G11, G32)
were the furthest below.

**Expectation, stated before running.** BURER2002 at 10 s will be within 0.5% of the best known value on the random
and planar instances, and 1% below on the toroidal ±1 ones. dSB at 10 s will be close to BURER2002 on the random ones
and behind on the planar ones. The VBS will reach the best known value on fewer than half of the instances. There will
be no RECORD_CANDIDATE. **Cost.** About 54 x (2 x 11 + 10 x 10) s plus overhead: about 2 h, in up to two slices.
**Status.** DEV; licenses nothing.
"""
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r102'
SHORT, LONG = 1.0, 10.0
OTHERS = ('DESOUSA2013', 'DUARTE2005', 'FESTA2002G', 'FESTA2002GPR', 'FESTA2002GVNS', 'FESTA2002GVNSPR',
          'FESTA2002VNS', 'FESTA2002VNSPR', 'LAGUNA2009CE', 'LAGUNA2009HCE')
SLICE_S, PAUSED = 6600, 3


def arms():
    """{(arm, budget): descriptor}."""
    from genesis import candidates_maxcut as CM
    D = {}
    for b in (SHORT, LONG):
        D[('burer', b)] = CM.build_descriptor('mqlib-maxcut-v1', {'heuristic': 'BURER2002', 'cpu_seconds': b},
                                              cpu_seconds=b, wall_seconds=max(60, int(3 * b) + 60))
        D[('dsb', b)] = CM.build_descriptor('dsb-maxcut-v1', {'cpu_seconds': b}, cpu_seconds=b,
                                            wall_seconds=max(60, int(3 * b) + 60))
    for h in OTHERS:
        D[(h.lower(), LONG)] = CM.build_descriptor('mqlib-maxcut-v1', {'heuristic': h, 'cpu_seconds': LONG},
                                                   cpu_seconds=LONG, wall_seconds=90)
    return D


def run_seed(task_id, arm, budget):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def family(task):
    return task.family.split('-')[1]


def analyse(rows, best):
    out = {'per_arm': {}, 'record_candidates': [], 'vbs10': {}}
    keys = sorted({(a, b) for r in rows for a, byb in r['runs'].items() for b in byb})
    for a, b in keys:
        fs, by_f, hit = [], {}, 0
        for r in rows:
            x = r['runs'].get(a, {}).get(b)
            if not x or x['value'] is None:
                continue
            f = x['value'] / best[r['instance']]
            fs.append(f)
            by_f.setdefault(r['family'], []).append(f)
            hit += x['value'] >= best[r['instance']]
            if x['value'] > best[r['instance']]:
                out['record_candidates'].append({'instance': r['instance'], 'arm': a, 'budget': b, 'value': x['value'],
                                                 'best_known': best[r['instance']]})
        out['per_arm'][f'{a}@{b}'] = {'instances': len(fs), 'mean_fraction': statistics.mean(fs) if fs else None,
                                      'by_family': {k: statistics.mean(v) for k, v in sorted(by_f.items())},
                                      'reach_best_known': hit}
    vb = []
    for r in rows:
        vals = [x['value'] for a, byb in r['runs'].items() for b, x in byb.items() if b == f'{LONG:g}' and x['value'] is not None]
        if vals:
            vb.append((r['family'], max(vals) / best[r['instance']], max(vals) >= best[r['instance']]))
    out['vbs10'] = {'mean_fraction': statistics.mean(f for _, f, _ in vb) if vb else None,
                    'by_family': {k: statistics.mean(f for g, f, _ in vb if g == k) for k in sorted({g for g, _, _ in vb})},
                    'reach_best_known': sum(h for _, _, h in vb)}
    return out


def validity(rows):
    cpu = {}
    fails = total = 0
    for r in rows:
        for a, byb in r['runs'].items():
            for b, x in byb.items():
                total += 1
                if x['status'] != 'SUCCESS':
                    fails += 1
                elif x['cpu_ns']:
                    cpu.setdefault(b, []).append(x['cpu_ns'] / 1e9 / float(b))
    med = {b: statistics.median(v) for b, v in cpu.items()}
    ok = all(m >= 0.9 for m in med.values()) and fails <= 0.01 * max(1, total)
    return ok, med, fails


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'gset_standing_b20r102').resolve():
        raise SystemExit('the registered output is evidence/gset_standing_b20r102')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    D = arms()
    best = GS.best_known()
    tasks = GS.tasks()
    path = out / 'rows.jsonl'
    done = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    for t in tasks[len(done):]:
        if time.monotonic() - t0 > SLICE_S:
            log(f'time slice used ({SLICE_S} s): paused after {len(done)} instances')
            return PAUSED
        g = t.task_id.split('-')[1]
        row = {'instance': g, 'task_id': t.task_id, 'family': family(t), 'n': t.n, 'edges': len(t.edges), 'runs': {}}
        for (a, b), d in D.items():
            r = CM.run(t, d, seed=run_seed(t.task_id, a, b), expected_id=d['descriptor_id'], isolation='runc')
            ok = r.get('status') == 'SUCCESS'
            row['runs'].setdefault(a, {})[f'{b:g}'] = {'value': r['result']['value'] if ok else None,
                                                      'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'),
                                                      'side': r['result']['side'] if ok else None}
        done.append(row)
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f"{g} ({t.n}, {len(t.edges)}) best known {best[g]}: burer {row['runs']['burer']['1']['value']}/"
            f"{row['runs']['burer']['10']['value']} dsb {row['runs']['dsb']['1']['value']}/{row['runs']['dsb']['10']['value']} "
            f"vbs10 {max(x['value'] or 0 for byb in row['runs'].values() for b, x in byb.items() if b == '10')}")
    res = analyse(done, best)
    ok, med, fails = validity(done)
    summary = dict(res, study=STUDY, schema='genesis-b20r102-gset-standing-v1', valid=ok, cpu_median=med,
                   failed_runs=fails, descriptors={f'{a}@{b:g}': d['descriptor_id'] for (a, b), d in D.items()},
                   best_known_sha256=digest(json.loads((GS.DATA / 'best_known.json').read_text())),
                   gset_archive_sha256=GS.manifest()['archive_sha256'], code_identity=code_identity(ROOT)['sha256'],
                   status='DEV calibration; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {ok}; burer@10 {res['per_arm']['burer@10']['mean_fraction']:.5f}; dsb@10 "
        f"{res['per_arm']['dsb@10']['mean_fraction']:.5f}; vbs10 {res['vbs10']['mean_fraction']:.5f}; record candidates "
        f"{len(res['record_candidates'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
