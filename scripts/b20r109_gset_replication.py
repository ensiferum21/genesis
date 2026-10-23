#!/usr/bin/env python3
"""B20_R109: does B20_R106's lead survive new seeds? A replication on Gset at 10 s (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r109_gset_replication.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** B20_R106 found Genesis's configured max-cut engine ahead of BURER2002, dSB and the virtual best of twelve
published heuristics on Gset G1-G54 (MCX_LEADS), with one seed per run, as B20_R102. One seed per instance confounds
the engine's level with its luck on that instance. This study reruns the three main arms at 10 s with two fresh seeds
each, so that every arm has three runs per instance (B20_R102's or B20_R106's seed plus these two), and compares the
arms on their per-instance means.

**Design (fixed before running).**
  * **Instances:** G1-G54, pinned.
  * **Arms at 10 s,** through `candidates_maxcut` in the runc sandbox, one core:
      - mcx chosen: B20_R105's configuration for the instance's class (B20_R105's classifier; as in B20_R106);
      - BURER2002 (`mqlib-maxcut-v1`);
      - dSB (`dsb-maxcut-v1`).
    Two new seeds per (instance, arm), from this study's name, the instance, the arm and the replicate. The descriptors
    are rebuilt from the same parameters; their ids may differ from B20_R102/R106's because later engineering changed
    the kinds' files (B20_R108 widened `mcx.WIDE`); the binaries are the pinned ones.
  * **Per instance and arm:** the mean of the three values (the earlier study's run and the two new ones).
  * **Tests** (sign tests over the 54 instances on the per-instance means, ties dropped, two-sided, alpha 0.05 / 3):
    mcx vs BURER2002, mcx vs dSB, and, on the new runs alone, mcx's *worst* of its two new runs vs the *best* of
    BURER2002's and dSB's four new runs (a stringent check: the engine's bad luck against the tools' good luck).
  * **Labels:** each AHEAD / BEHIND / COMPARABLE. **Headline:** REPLICATED if mcx is AHEAD of both tools on the means;
    NOT_REPLICATED if it is not AHEAD of either; PARTLY otherwise. Also: per-arm mean fraction of the best known value
    (all three runs), the number of instances where any mcx run reaches it, and values above it (RECORD_CANDIDATE,
    never claimed). Validity: median metered CPU at least 0.9 of the budget, at most 1% failed runs.

**Expectation, stated before running.** REPLICATED; the stringent check AHEAD or COMPARABLE; no RECORD_CANDIDATE.
**Cost.** 54 x 3 arms x 2 seeds x 10 s plus overhead: about 60 min. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r109'
BUDGET, REPLICATES = 10.0, 2
ARMS = ('mcx', 'burer', 'dsb')
R102 = ROOT / 'evidence' / 'gset_standing_b20r102'
R105 = ROOT / 'evidence' / 'mcx_configure_b20r105'
R106 = ROOT / 'evidence' / 'mcx_gset_b20r106'
ALPHA = 0.05 / 3
SLICE_S, PAUSED = 6600, 3


def run_seed(task_id, arm, rep):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'rep': rep})[:12], 16)


def sign(xs, ys, alpha=ALPHA):
    from scipy.stats import binomtest
    wins = sum(x > y for x, y in zip(xs, ys))
    losses = sum(x < y for x, y in zip(xs, ys))
    p = float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else 1.0
    return {'wins': wins, 'losses': losses, 'ties': len(xs) - wins - losses, 'p': p,
            'label': 'COMPARABLE' if p >= alpha else ('AHEAD' if wins > losses else 'BEHIND')}


def analyse(rows, best):
    """rows: [{'instance', 'family', 'earlier': {arm: value}, 'new': {arm: [v, v]}}]."""
    mean = {a: [statistics.mean([r['earlier'][a]] + r['new'][a]) for r in rows] for a in ARMS}
    tests = {'mcx vs burer': sign(mean['mcx'], mean['burer']), 'mcx vs dsb': sign(mean['mcx'], mean['dsb']),
             'mcx worst new vs tools best new': sign([min(r['new']['mcx']) for r in rows],
                                                     [max(r['new']['burer'] + r['new']['dsb']) for r in rows])}
    lead = [tests['mcx vs burer']['label'], tests['mcx vs dsb']['label']]
    headline = ('REPLICATED' if lead == ['AHEAD', 'AHEAD'] else
                'NOT_REPLICATED' if 'AHEAD' not in lead else 'PARTLY')
    per_arm = {}
    for a in ARMS:
        fs = [v / best[r['instance']] for r in rows for v in [r['earlier'][a]] + r['new'][a]]
        per_arm[a] = {'mean_fraction': statistics.mean(fs),
                      'instances_reaching_best_known': sum(any(v >= best[r['instance']] for v in [r['earlier'][a]] + r['new'][a])
                                                           for r in rows)}
    cands = [{'instance': r['instance'], 'arm': a, 'value': v, 'best_known': best[r['instance']]}
             for r in rows for a in ARMS for v in r['new'][a] if v > best[r['instance']]]
    return {'tests': tests, 'headline': headline, 'per_arm': per_arm, 'record_candidates': cands}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'gset_replication_b20r109').resolve():
        raise SystemExit('the registered output is evidence/gset_replication_b20r109')
    configs = json.loads((R105 / 'configs.json').read_text())
    if digest(configs) != json.loads((R105 / 'summary.json').read_text())['configs_sha256']:
        raise SystemExit('configs.json is not the one B20_R105 recorded')
    earlier102 = {r['instance']: r for r in map(json.loads, (R102 / 'rows.jsonl').read_text().splitlines()) if r}
    earlier106 = {r['instance']: r for r in map(json.loads, (R106 / 'rows.jsonl').read_text().splitlines()) if r}
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
    log(f'{STUDY}; pinned to CPU {cpu}')
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    best = GS.best_known()
    path = out / 'rows.jsonl'
    done = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    desc = {}

    def descriptor(kind, params):
        key = json.dumps([kind, params], sort_keys=True)
        if key not in desc:
            desc[key] = CM.build_descriptor(kind, params, cpu_seconds=BUDGET, wall_seconds=max(60, int(3 * BUDGET) + 60))
        return desc[key]
    for t in GS.tasks()[len(done):]:
        if time.monotonic() - t0 > SLICE_S:
            log(f'time slice used ({SLICE_S} s): paused after {len(done)} instances')
            return PAUSED
        g = t.task_id.split('-')[1]
        cls = R105M.classify(configs['classifier'], R105M.features(t))
        params = {'mcx': ('mcx-v1', {'cpu_seconds': BUDGET, 'config': configs['chosen'][cls]['10']}),
                  'burer': ('mqlib-maxcut-v1', {'heuristic': 'BURER2002', 'cpu_seconds': BUDGET}),
                  'dsb': ('dsb-maxcut-v1', {'cpu_seconds': BUDGET})}
        row = {'instance': g, 'task_id': t.task_id, 'family': t.family.split('-')[1], 'class': cls,
               'earlier': {'mcx': earlier106[g]['runs']['chosen@10']['value'], 'burer': earlier102[g]['runs']['burer']['10']['value'],
                           'dsb': earlier102[g]['runs']['dsb']['10']['value']},
               'new': {}, 'runs': []}
        for a in ARMS:
            d = descriptor(*params[a])
            vals = []
            for rep in range(REPLICATES):
                r = CM.run(t, d, seed=run_seed(t.task_id, a, rep), expected_id=d['descriptor_id'], isolation='runc')
                ok = r.get('status') == 'SUCCESS'
                vals.append(r['result']['value'] if ok else None)
                row['runs'].append({'arm': a, 'rep': rep, 'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'),
                                    'value': vals[-1], 'descriptor': d['descriptor_id'],
                                    'side': r['result']['side'] if ok else None})
            row['new'][a] = vals
        done.append(row)
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f"{g} [{cls}] best known {best[g]}: mcx {row['earlier']['mcx']}/{row['new']['mcx']} burer "
            f"{row['earlier']['burer']}/{row['new']['burer']} dsb {row['earlier']['dsb']}/{row['new']['dsb']}")
    ok_rows = [r for r in done if all(v is not None for a in ARMS for v in r['new'][a])]
    res = analyse(ok_rows, best)
    cpus = [x['cpu_ns'] / 1e9 / BUDGET for r in done for x in r['runs'] if x['status'] == 'SUCCESS' and x['cpu_ns']]
    fails = sum(x['status'] != 'SUCCESS' for r in done for x in r['runs'])
    valid = statistics.median(cpus) >= 0.9 and fails <= 0.01 * sum(len(r['runs']) for r in done)
    summary = dict(res, study=STUDY, schema='genesis-b20r109-replication-v1', valid=valid, cpu_median=statistics.median(cpus),
                   failed_runs=fails, instances=len(ok_rows), configs_sha256=digest(configs),
                   best_known_sha256=digest(json.loads((GS.DATA / 'best_known.json').read_text())),
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; {res['headline']}; " + '; '.join(f"{k} {v['label']} {v['wins']}-{v['losses']}"
                                                         for k, v in res['tests'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
