#!/usr/bin/env python3
"""B20_R113: does renormalisation close the planar gap? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r113_planar_renorm.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** At 60 s Genesis's engine reaches the best known values on every Gset torus. Its remaining gap is on the
planar graphs, most of all the larger ±1 ones (B20_R110: G39-G42 at 0.992-0.999). In B20_R108, maturation chose for
planar graphs at 10 s a configuration with the renormalisation restart and the largest perturbation offered (L0 =
0.2). That configuration won all five decided held-out planar graphs, too few for the preregistered test. This study
decides the lead on enough graphs, then, only if it holds, takes it to Gset's planar instances.

**Design (fixed before running).**
  * **Configurations:**
      - INCUMBENT: B20_R105's planar configuration at 10 s (Houdayer cluster exchange);
      - RENORM: B20_R108's planar configuration at 10 s (renormalisation, L0 = 0.2).
    Both are read as recorded, each file checked against its study's SHA-256.
  * **Part A (generated planar graphs):** 40 fresh graphs rotating through B20_R105's planar settings (`planar2` and
    `planar2_pm1` at n = 800, 2000 and 1000, density 0.99). Seeds are from SEED; the identities of Gset and of all of
    B20_R105's and B20_R108's graphs are excluded. Both configurations at 10 s, one seed per (graph, arm), through
    `candidates_maxcut` in the runc sandbox, one core. The test is a Wilcoxon signed-rank test on per-graph gaps
    (zeros dropped, two-sided, alpha 0.05): RENORM_BETTER / RENORM_WORSE / NO_DIFFERENCE.
  * **Part B (Gset planar instances; only if Part A is RENORM_BETTER):** RENORM at 60 s on the 20 planar instances
    (G14-G21, G35-G42, G51-G54), one seed each, against B20_R110's 60 s values (INCUMBENT, another seed): a sign
    test (ties dropped, two-sided, alpha 0.05), the instances reaching the best known value, and RECORD_CANDIDATE for
    any value above it (kept, never claimed).
  * **Validity:** median metered CPU at least 0.9 of each budget; at most 1% failed runs.

**Development looks (disclosed).** B20_R108's held-out planar graphs (5-0 for RENORM at 10 s, 3 ties) are the lead
itself; no other look.

**Expectation, stated before running.** NO_DIFFERENCE slightly more likely than RENORM_BETTER: a 5-0 lead on 8 graphs
often shrinks. If RENORM_BETTER, Part B gains on the larger planar ±1 instances but sets no record.
**Cost.** Part A 40 x 2 x 10 s, about 15 min; Part B 20 x 60 s, about 21 min. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r113'
SEED = 20301131
N_GRAPHS = 40
SHORT, LONG = 10.0, 60.0
ALPHA = 0.05
EV = ROOT / 'evidence'
R105, R108, R110 = EV / 'mcx_configure_b20r105', EV / 'mcx_maturation_b20r108', EV / 'gset_long_b20r110'
PLANAR_GSET = tuple(range(14, 22)) + tuple(range(35, 43)) + tuple(range(51, 55))
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def configs():
    out = {}
    for name, d in (('INCUMBENT', R105), ('RENORM', R108)):
        c = json.loads((d / 'configs.json').read_text())
        s = json.loads((d / 'summary.json').read_text())
        if digest(c) != s['configs_sha256'] or not s['valid']:
            raise SystemExit(f'{d.name}: configs.json is not the recorded one, or the study is not valid')
        out[name] = c['chosen']['planar']['10']
    return out


def graphs(excluded):
    import b20r105_mcx_configure as R105M
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out = set(excluded), []
    settings = R105M.SETTINGS['planar']
    for i in range(N_GRAPHS):
        fam, params = settings[i % len(settings)]
        ts, seen, _ = A.generate(SEED + i, 1, 'DEV', fam, params, excluded=seen)
        out.append(ts[0])
    return out


def part_a_label(values):
    """values: {graph: {'INCUMBENT': v, 'RENORM': v}} -> the Wilcoxon label."""
    import b20r105_mcx_configure as R105M
    gp = R105M.gaps(values)
    gs = sorted(gp)
    w, p = R105M.compare([gp[g]['RENORM'] for g in gs], [gp[g]['INCUMBENT'] for g in gs], ALPHA)
    return {'label': {'A': 'RENORM_BETTER', 'B': 'RENORM_WORSE', None: 'NO_DIFFERENCE'}[w], 'p': p,
            'wins': sum(values[g]['RENORM'] > values[g]['INCUMBENT'] for g in gs),
            'losses': sum(values[g]['RENORM'] < values[g]['INCUMBENT'] for g in gs),
            'mean_gap_renorm': statistics.mean(gp[g]['RENORM'] for g in gs),
            'mean_gap_incumbent': statistics.mean(gp[g]['INCUMBENT'] for g in gs)}


def part_b_summary(rows, best):
    from scipy.stats import binomtest
    wins = sum(r['value'] > r['incumbent_60'] for r in rows)
    losses = sum(r['value'] < r['incumbent_60'] for r in rows)
    p = float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else 1.0
    return {'wins': wins, 'losses': losses, 'ties': len(rows) - wins - losses, 'p': p,
            'label': 'NO_DIFFERENCE' if p >= ALPHA else ('RENORM_BETTER' if wins > losses else 'RENORM_WORSE'),
            'mean_fraction': statistics.mean(r['value'] / best[r['instance']] for r in rows),
            'mean_fraction_incumbent': statistics.mean(r['incumbent_60'] / best[r['instance']] for r in rows),
            'reach_best_known': sum(r['value'] >= best[r['instance']] for r in rows),
            'record_candidates': [{'instance': r['instance'], 'value': r['value'], 'best_known': best[r['instance']]}
                                  for r in rows if r['value'] > best[r['instance']]]}


def run_seed(task_id, arm, budget):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (EV / 'planar_renorm_b20r113').resolve():
        raise SystemExit('the registered output is evidence/planar_renorm_b20r113')
    cfg = configs()
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r105_mcx_configure as R105M
    import b20r108_mcx_maturation as R108M
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}; INCUMBENT {cfg["INCUMBENT"]}; RENORM {cfg["RENORM"]}')
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ex = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    ex |= {A.exposure_identity(t)['canonical'] for ts in R105M.pools(set(ex)).values() for t in ts}
    ex |= {A.exposure_identity(t)['canonical'] for ts in R108M.pools(set(ex)).values() for t in ts}
    G = graphs(ex)
    log(f'{len(G)} planar graphs; {len(ex)} identities excluded')
    path = out / 'runs.jsonl'
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r['key']] = r
    desc = {}

    def value(task, arm, b, part):
        key = f'{part}|{task.task_id}|{arm}|{b:g}'
        if key not in cache:
            if time.monotonic() - t0 > SLICE_S:
                raise Paused
            if (arm, b) not in desc:
                desc[(arm, b)] = CM.build_descriptor('mcx-v1', {'cpu_seconds': b, 'config': cfg[arm]}, cpu_seconds=b,
                                                     wall_seconds=int(3 * b) + 60)
            d = desc[(arm, b)]
            r = CM.run(task, d, seed=run_seed(task.task_id, arm, b), expected_id=d['descriptor_id'], isolation='runc')
            ok = r.get('status') == 'SUCCESS'
            cache[key] = {'key': key, 'part': part, 'task': task.task_id, 'arm': arm, 'budget': b,
                          'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'), 'descriptor': d['descriptor_id'],
                          'value': r['result']['value'] if ok else None, 'side': r['result']['side'] if ok else None}
            with path.open('a') as f:
                f.write(json.dumps(cache[key], sort_keys=True) + '\n')
        return cache[key]['value']
    try:
        va = {}
        for t in G:
            va[t.task_id] = {a: value(t, a, SHORT, 'A') for a in ('INCUMBENT', 'RENORM')}
            log(f'A {t.task_id}: {va[t.task_id]}')
        part_a = part_a_label(va)
        log(f'part A: {part_a["label"]} ({part_a["wins"]}-{part_a["losses"]}, p {part_a["p"]:.3g})')
        part_b = None
        if part_a['label'] == 'RENORM_BETTER':
            best = GS.best_known()
            r110 = {r['instance']: r['value'] for r in map(json.loads, (R110 / 'rows.jsonl').read_text().splitlines()) if r}
            rows = []
            for t in GS.tasks(list(PLANAR_GSET)):
                g = t.task_id.split('-')[1]
                rows.append({'instance': g, 'value': value(t, 'RENORM', LONG, 'B'), 'incumbent_60': r110[g]})
                log(f'B {g} best known {best[g]}: RENORM 60 s {rows[-1]["value"]} (INCUMBENT 60 s {r110[g]})')
            part_b = part_b_summary(rows, best)
            part_b['rows'] = rows
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    cpu_by, fails = {}, 0
    for r in cache.values():
        if r['status'] != 'SUCCESS':
            fails += 1
        elif r['cpu_ns']:
            cpu_by.setdefault(f"{r['budget']:g}", []).append(r['cpu_ns'] / 1e9 / r['budget'])
    med = {b: statistics.median(v) for b, v in cpu_by.items()}
    valid = all(m >= 0.9 for m in med.values()) and fails <= 0.01 * max(1, len(cache))
    summary = {'study': STUDY, 'schema': 'genesis-b20r113-planar-renorm-v1', 'configs': cfg, 'part_a': part_a,
               'part_a_values': va, 'part_b': part_b, 'valid': valid, 'cpu_median': med, 'failed_runs': fails,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing; no record claim'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'valid {valid}; part A {part_a["label"]}; part B ' +
        (f'{part_b["label"]} {part_b["wins"]}-{part_b["losses"]}, reaching {part_b["reach_best_known"]}, record candidates '
         f'{len(part_b["record_candidates"])}' if part_b else 'not run'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
