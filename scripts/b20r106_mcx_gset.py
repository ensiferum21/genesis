#!/usr/bin/env python3
"""B20_R106: Genesis's max-cut engine against the published heuristics on Gset, once (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r106_mcx_gset.py OUT_DIR     run ALONE after B20_R102 and B20_R105, then analyse

**Why.** `docs/OPEN_RECORDS_PLAN.md`: the open-record track asks whether a Genesis method beats the strongest pinned
tools on a public benchmark, at equal budgets on one core. B20_R102 measured those tools on Gset; B20_R105 let the
system configure `mcx-v1` on generated graphs only. This study applies that configuration to Gset, once, with no
change after seeing Gset.

**Design (fixed before B20_R102, B20_R105 or this study ran).**
  * **Instances.** G1-G54, pinned (`gset.tasks()`), in order.
  * **Arms** (`mcx-v1` through `candidates_maxcut` in the runc sandbox, one core, one seed per (instance, arm,
    budget) from the study, instance, arm and budget, as B20_R102):
      - chosen@1 and chosen@10: each instance is placed in a class by B20_R105's classifier (its two order
        parameters), and run with B20_R105's configuration for that class and budget;
      - default@1 and default@10: `mcx-v1`'s DEFAULT, breakout local search's published setting in this engine
        (our implementation, not the authors' code).
    B20_R105's `configs.json` is read as recorded (its SHA-256 is recorded here); the study refuses to start
    unless B20_R105's and B20_R102's summaries exist and are valid.
  * **Comparators** (B20_R102's recorded runs, one seed each): BURER2002 at 1 s and 10 s, dSB at 1 s and 10 s, and
    the virtual best at 10 s (the best of B20_R102's twelve arms at 10 s per instance: twelve times mcx's compute).
  * **Tests** (sign tests over the 54 instances, ties dropped, two-sided, alpha 0.05 / 7 for the seven): chosen vs
    BURER2002 at 1 s and at 10 s; chosen vs dSB at 1 s and at 10 s; chosen@10 vs the virtual best at 10 s; chosen vs
    default at 1 s and at 10 s. Each is AHEAD, BEHIND or COMPARABLE.
  * **Headline.** MCX_LEADS if chosen is AHEAD of BURER2002 at both budgets; MCX_BEHIND if it is BEHIND at either;
    otherwise MCX_COMPARABLE. Also: mean fraction of the best known value per arm and family, and the number of
    instances reaching it; the classifier's agreement with Gset's own family labels (reported, not used).
  * **Record rule** (as B20_R102). A run above an instance's best known value (`data/gset/best_known.json`, which
    since B20_R104 holds the BLS paper's Table 2) is labelled RECORD_CANDIDATE and never claimed: later papers may
    report higher values, and a candidate is first checked against the literature after 2013.
  * **Validity.** Median metered CPU at least 0.9 of each budget; at most 1% failed runs.

**Development look (disclosed).** On 22 Oct 2026, while writing mcx, the builder ran an earlier draft of it (the
cluster-exchange restart, no renormalisation, no BLS rules; in-process, 2 s, one seed) on G1, G11, G14, G22, G32, G43
and G48: above BURER2002 at 2 s on G11, G14 and G22, below it on G1 (11615 vs 11623), 1402 on G32 and 6660 on G43
(below and equal to the best known values of the BLS paper, which the table holds since B20_R104). Nothing in
B20_R104-R105 used Gset afterwards: mcx was developed and configured on generated graphs only.

**Expectation, stated before running.** Chosen AHEAD of BURER2002 at 1 s and COMPARABLE at 10 s, so MCX_COMPARABLE;
chosen AHEAD of dSB at both budgets; chosen@10 BEHIND or COMPARABLE to the virtual best at 10 s (twelve heuristics,
twelve times the compute); chosen vs default COMPARABLE at both budgets. No RECORD_CANDIDATE (the table holds the BLS
paper's values, reached by runs of up to 200,000 n iterations).
**Cost.** 54 x 2 x 11 s plus overhead: about 25 min. **Status.** DEV; licenses nothing; no record claim.
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

STUDY = 'b20r106'
SHORT, LONG = 1.0, 10.0
R102 = ROOT / 'evidence' / 'gset_standing_b20r102'
R105 = ROOT / 'evidence' / 'mcx_configure_b20r105'
TESTS = (('chosen@1', 'burer@1'), ('chosen@10', 'burer@10'), ('chosen@1', 'dsb@1'), ('chosen@10', 'dsb@10'),
         ('chosen@10', 'vbs@10'), ('chosen@1', 'default@1'), ('chosen@10', 'default@10'))
ALPHA = 0.05 / len(TESTS)


def comparators(r102_row):
    """B20_R102's recorded values for one instance: burer@1/10, dsb@1/10 and the virtual best at 10 s."""
    runs = r102_row['runs']
    ten = [x['value'] for byb in runs.values() for b, x in byb.items() if b == '10' and x['value'] is not None]
    return {'burer@1': runs['burer']['1']['value'], 'burer@10': runs['burer']['10']['value'],
            'dsb@1': runs['dsb']['1']['value'], 'dsb@10': runs['dsb']['10']['value'],
            'vbs@10': max(ten) if ten else None}


def sign_test(rows, a, b, alpha=ALPHA):
    from scipy.stats import binomtest
    wins = sum(r[a] is not None and (r[b] is None or r[a] > r[b]) for r in rows)
    losses = sum(r[b] is not None and (r[a] is None or r[a] < r[b]) for r in rows)
    p = float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else 1.0
    label = 'COMPARABLE' if p >= alpha else ('AHEAD' if wins > losses else 'BEHIND')
    return {'wins': wins, 'losses': losses, 'ties': len(rows) - wins - losses, 'p': p, 'label': label}


def analyse(rows, best):
    """rows: [{'instance', 'family', 'class', arm: value, ...}]."""
    tests = {f'{a} vs {b}': sign_test(rows, a, b) for a, b in TESTS}
    lead = [tests[f'chosen@{x} vs burer@{x}']['label'] for x in ('1', '10')]
    headline = ('MCX_LEADS' if lead == ['AHEAD', 'AHEAD'] else 'MCX_BEHIND' if 'BEHIND' in lead else 'MCX_COMPARABLE')
    arms = ('chosen@1', 'chosen@10', 'default@1', 'default@10', 'burer@1', 'burer@10', 'dsb@1', 'dsb@10', 'vbs@10')
    per_arm, cands = {}, []
    for a in arms:
        fs, by_f, hit = [], {}, 0
        for r in rows:
            v = r[a]
            if v is None:
                continue
            f = v / best[r['instance']]
            fs.append(f)
            by_f.setdefault(r['family'], []).append(f)
            hit += v >= best[r['instance']]
            if v > best[r['instance']] and a.split('@')[0] in ('chosen', 'default'):
                cands.append({'instance': r['instance'], 'arm': a, 'value': v, 'best_known': best[r['instance']]})
        per_arm[a] = {'mean_fraction': statistics.mean(fs) if fs else None, 'reach_best_known': hit,
                      'by_family': {k: statistics.mean(v) for k, v in sorted(by_f.items())}}
    agree = statistics.mean(r['family'] == r['class'] for r in rows) if rows else None
    return {'tests': tests, 'headline': headline, 'per_arm': per_arm, 'record_candidates': cands,
            'classifier_agrees_with_gset_family': agree}


def run_seed(task_id, arm, budget):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def inputs():
    """B20_R105's configs and B20_R102's rows, refused unless both studies finished validly."""
    s105, s102 = R105 / 'summary.json', R102 / 'summary.json'
    if not (s105.exists() and s102.exists()):
        raise SystemExit('B20_R102 and B20_R105 must have finished (their summary.json files)')
    if not (json.loads(s105.read_text())['valid'] and json.loads(s102.read_text())['valid']):
        raise SystemExit('B20_R102 and B20_R105 must be valid')
    configs = json.loads((R105 / 'configs.json').read_text())
    if digest(configs) != json.loads(s105.read_text())['configs_sha256']:
        raise SystemExit('configs.json is not the one B20_R105 recorded')
    rows = {r['instance']: r for r in map(json.loads, (R102 / 'rows.jsonl').read_text().splitlines()) if r}
    return configs, rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'mcx_gset_b20r106').resolve():
        raise SystemExit('the registered output is evidence/mcx_gset_b20r106')
    configs, r102 = inputs()
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
    log(f'{STUDY}; pinned to CPU {cpu}; B20_R105 configs {digest(configs)[:12]}')
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    from genesis.candidate_kinds import mcx as K
    if configs['binary_sha256'] != K.BINARY_SHA256:
        raise SystemExit('mcx-v1 is not the build B20_R105 configured')
    best = GS.best_known()
    path = out / 'rows.jsonl'
    done = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    desc = {}
    for t in GS.tasks()[len(done):]:
        g = t.task_id.split('-')[1]
        cls = R105M.classify(configs['classifier'], R105M.features(t))
        row = {'instance': g, 'task_id': t.task_id, 'family': t.family.split('-')[1], 'class': cls, 'runs': {}}
        for b in (SHORT, LONG):
            for name, cfg in (('chosen', configs['chosen'][cls][f'{b:g}']), ('default', K.DEFAULT)):
                key = (json.dumps(cfg, sort_keys=True), b)
                if key not in desc:
                    desc[key] = CM.build_descriptor('mcx-v1', {'cpu_seconds': b, 'config': cfg}, cpu_seconds=b,
                                                    wall_seconds=max(60, int(3 * b) + 60))
                d = desc[key]
                r = CM.run(t, d, seed=run_seed(t.task_id, name, b), expected_id=d['descriptor_id'], isolation='runc')
                ok = r.get('status') == 'SUCCESS'
                row['runs'][f'{name}@{b:g}'] = {'value': r['result']['value'] if ok else None, 'status': r.get('status'),
                                                'cpu_ns': r.get('cpu_ns'), 'descriptor': d['descriptor_id'],
                                                'side': r['result']['side'] if ok else None}
        row.update(comparators(r102[g]))
        done.append(row)
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f"{g} [{cls}] best known {best[g]}: chosen {row['runs']['chosen@1']['value']}/{row['runs']['chosen@10']['value']}"
            f" default {row['runs']['default@1']['value']}/{row['runs']['default@10']['value']} burer {row['burer@1']}/"
            f"{row['burer@10']} vbs10 {row['vbs@10']}")
    flat = [dict({k: v for k, v in r.items() if k != 'runs'}, **{a: x['value'] for a, x in r['runs'].items()})
            for r in done]
    res = analyse(flat, best)
    cpu_med, fails, total = {}, 0, 0
    for r in done:
        for a, x in r['runs'].items():
            total += 1
            if x['status'] != 'SUCCESS':
                fails += 1
            elif x['cpu_ns']:
                b = a.split('@')[1]
                cpu_med.setdefault(b, []).append(x['cpu_ns'] / 1e9 / float(b))
    med = {b: statistics.median(v) for b, v in cpu_med.items()}
    ok = all(m >= 0.9 for m in med.values()) and fails <= 0.01 * max(1, total)
    summary = dict(res, study=STUDY, schema='genesis-b20r106-mcx-gset-v1', valid=ok, cpu_median=med, failed_runs=fails,
                   configs_sha256=digest(configs), best_known_sha256=digest(json.loads((GS.DATA / 'best_known.json').read_text())),
                   gset_archive_sha256=GS.manifest()['archive_sha256'], code_identity=code_identity(ROOT)['sha256'],
                   status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {ok}; {res['headline']}; " + '; '.join(f"{k} {v['label']} {v['wins']}-{v['losses']}"
                                                      for k, v in res['tests'].items())
        + f"; record candidates {len(res['record_candidates'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
