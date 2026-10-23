#!/usr/bin/env python3
"""B20_R110: what six times the budget buys on Gset: the engine at 60 s against the best known values (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r110_gset_long.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** At 10 s Genesis's configured engine reaches the 2012-13 best known values on 24 of the 54 Gset instances
(B20_R106). The papers that set them ran for minutes per instance. This study measures how far a longer run on one
core closes the remaining gap, instance by instance. It is the first step of any record attempt, and a value above the
table would be flagged for checking, never claimed.

**Design (fixed before B20_R108 and B20_R109 finished).**
  * **Instances:** G1-G54, pinned.
  * **Configuration:** each instance's class by B20_R105's classifier. The 10 s configuration for that class is taken
    from B20_R108's `configs.json` if B20_R108's 10 s label is MATURED_BETTER, otherwise from B20_R105's. The rule is
    fixed here; the study refuses to start unless the chosen file is the one its study recorded.
  * **Arm:** `mcx-v1` at 60 s, one seed per instance from the study and the instance, through `candidates_maxcut` in
    the runc sandbox, one core.
  * **Measures:** fraction of the best known value overall and per family; instances reaching it; RECORD_CANDIDATE
    for any value above it (the witness kept; never claimed).
  * **Test:** sign test over the 54 instances of the 60 s value against B20_R106's chosen@10 value (ties dropped,
    two-sided, alpha 0.05): LONGER_HELPS / NO_DIFFERENCE / LONGER_HURTS. The 10 s run used a different seed, and the
    configuration may differ if B20_R108 matured it; both are stated with the result. Validity: median metered CPU at
    least 0.9 of the budget, at most 1% failed runs.

**Expectation, stated before running.** LONGER_HELPS; the best known value reached on 30-36 instances; the planar
instances still furthest below; no RECORD_CANDIDATE.
**Cost.** 54 x 60 s plus overhead: about 60 min. **Status.** DEV; licenses nothing; no record claim.
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

STUDY = 'b20r110'
BUDGET = 60.0
R105 = ROOT / 'evidence' / 'mcx_configure_b20r105'
R106 = ROOT / 'evidence' / 'mcx_gset_b20r106'
R108 = ROOT / 'evidence' / 'mcx_maturation_b20r108'
SLICE_S, PAUSED = 6600, 3


def run_seed(task_id):
    return int(digest({'study': STUDY, 'task': task_id})[:12], 16)


def choose_configs(r105_dir=R105, r108_dir=R108):
    """B20_R108's configurations if its 10 s label is MATURED_BETTER, else B20_R105's; each checked against its study."""
    s108 = r108_dir / 'summary.json'
    if s108.exists() and json.loads(s108.read_text())['labels']['maturation@10']['label'] == 'MATURED_BETTER':
        src, summary = r108_dir, json.loads(s108.read_text())
    else:
        src, summary = r105_dir, json.loads((r105_dir / 'summary.json').read_text())
    configs = json.loads((src / 'configs.json').read_text())
    if digest(configs) != summary['configs_sha256'] or not summary['valid']:
        raise SystemExit(f'{src.name}: configs.json is not the one its study recorded, or the study is not valid')
    return src.name, configs


def analyse(rows, best):
    """rows: [{'instance', 'family', 'value', 'ten'}]."""
    from scipy.stats import binomtest
    fs, by_f = [], {}
    for r in rows:
        f = r['value'] / best[r['instance']]
        fs.append(f)
        by_f.setdefault(r['family'], []).append(f)
    wins = sum(r['value'] > r['ten'] for r in rows)
    losses = sum(r['value'] < r['ten'] for r in rows)
    p = float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else 1.0
    label = 'NO_DIFFERENCE' if p >= 0.05 else ('LONGER_HELPS' if wins > losses else 'LONGER_HURTS')
    return {'mean_fraction': statistics.mean(fs), 'by_family': {k: statistics.mean(v) for k, v in sorted(by_f.items())},
            'reach_best_known': sum(r['value'] >= best[r['instance']] for r in rows),
            'reached': [r['instance'] for r in rows if r['value'] >= best[r['instance']]],
            'record_candidates': [{'instance': r['instance'], 'value': r['value'], 'best_known': best[r['instance']]}
                                  for r in rows if r['value'] > best[r['instance']]],
            'vs_10s': {'wins': wins, 'losses': losses, 'ties': len(rows) - wins - losses, 'p': p, 'label': label}}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'gset_long_b20r110').resolve():
        raise SystemExit('the registered output is evidence/gset_long_b20r110')
    source, configs = choose_configs()
    classifier = json.loads((R105 / 'configs.json').read_text())['classifier']
    ten = {r['instance']: r['runs']['chosen@10']['value']
           for r in map(json.loads, (R106 / 'rows.jsonl').read_text().splitlines()) if r}
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
    log(f'{STUDY}; pinned to CPU {cpu}; configurations from {source} ({digest(configs)[:12]})')
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    best = GS.best_known()
    path = out / 'rows.jsonl'
    done = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    desc = {}
    for t in GS.tasks()[len(done):]:
        if time.monotonic() - t0 > SLICE_S:
            log(f'time slice used ({SLICE_S} s): paused after {len(done)} instances')
            return PAUSED
        g = t.task_id.split('-')[1]
        cls = R105M.classify(classifier, R105M.features(t))
        cfg = configs['chosen'][cls]['10']
        key = json.dumps(cfg, sort_keys=True)
        if key not in desc:
            desc[key] = CM.build_descriptor('mcx-v1', {'cpu_seconds': BUDGET, 'config': cfg}, cpu_seconds=BUDGET,
                                            wall_seconds=int(3 * BUDGET) + 60)
        d = desc[key]
        r = CM.run(t, d, seed=run_seed(t.task_id), expected_id=d['descriptor_id'], isolation='runc')
        ok = r.get('status') == 'SUCCESS'
        row = {'instance': g, 'task_id': t.task_id, 'family': t.family.split('-')[1], 'class': cls, 'config': cfg,
               'value': r['result']['value'] if ok else None, 'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'),
               'descriptor': d['descriptor_id'], 'side': r['result']['side'] if ok else None, 'ten': ten[g]}
        done.append(row)
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f"{g} [{cls}] best known {best[g]}: 60 s {row['value']} (10 s {ten[g]})")
    ok_rows = [r for r in done if r['value'] is not None]
    res = analyse(ok_rows, best)
    cpus = [r['cpu_ns'] / 1e9 / BUDGET for r in ok_rows if r['cpu_ns']]
    fails = len(done) - len(ok_rows)
    valid = bool(cpus) and statistics.median(cpus) >= 0.9 and fails <= 0.01 * len(done)
    summary = dict(res, study=STUDY, schema='genesis-b20r110-gset-long-v1', valid=valid, cpu_median=statistics.median(cpus),
                   failed_runs=fails, configs_from=source, configs_sha256=digest(configs),
                   best_known_sha256=digest(json.loads((GS.DATA / 'best_known.json').read_text())),
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; mean fraction {res['mean_fraction']:.5f}; reaching {res['reach_best_known']}; vs 10 s "
        f"{res['vs_10s']['label']} {res['vs_10s']['wins']}-{res['vs_10s']['losses']}; record candidates "
        f"{len(res['record_candidates'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
