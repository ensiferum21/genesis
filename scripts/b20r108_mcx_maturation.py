#!/usr/bin/env python3
"""B20_R108: affinity maturation: the system mutates and reselects its max-cut configurations (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r108_mcx_maturation.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** B20_R105 chose a configuration of `mcx-v1` per graph class by clonal selection: successive halving over
DEFAULT and 31 random draws. Every class chose the largest perturbation offered (L0 = 0.05), and two classes the
longest tenure and largest pool: the optimum may lie outside the space. A germinal centre does not only select: it
mutates the selected clones (somatic hypermutation) and selects again (affinity maturation). Here the space is widened
(B20_R108 engineering, `mcx.WIDE`: L0 up to 0.2, tenure divisors down to 2, pools up to 32; B20_R105's draw space
`mcx.SPACE` is unchanged) and B20_R105's choices are matured.

**Design (fixed before running).**
  * **Graphs.** B20_R105's three classes and settings with fresh draws (seeds from SEED), excluding the identities of
    every Gset graph and of all 96 of B20_R105's graphs; the weight-1 tori on ten new shapes, each of a size used by
    neither (the exposure identity cannot tell regular graphs of one size apart). 32 per class: 16 for the 1 s race,
    8 for the 10 s race, 8 held out.
  * **Mutants.** For each class, the incumbent is B20_R105's chosen configuration at that budget
    (`evidence/mcx_configure_b20r105/configs.json`, read as recorded). A mutant changes one or two keys (equally
    likely) of the incumbent to other values of WIDE; mutants are distinct.
  * **1 s race, per class:** the 1 s incumbent and 31 mutants, successive halving as B20_R105 (all 32 on 4 graphs, the
    best 10 on 4 more, the best 3 on 8 more; ties: the incumbent first, then the order drawn).
  * **10 s race, per class:** the 10 s incumbent, 4 mutants of it, and the 1 s race's final three (8 or fewer distinct),
    on 4 graphs at 10 s; the best 2 on 4 more.
  * **Held out** (8 per class): the incumbent and the matured configuration, at 1 s and at 10 s.
  * **Labels, per budget** (Wilcoxon signed-rank on per-graph gaps over 24 held-out graphs, two-sided, zeros dropped,
    alpha 0.025): MATURED_BETTER / MATURED_WORSE / NO_DIFFERENCE; INCUMBENT_KEPT in a class whose race the incumbent
    won (its held-out runs are then identical). Validity: median metered CPU at least 0.9 of each budget, at most 1%
    failed runs.
  * **Output.** `configs.json` in B20_R105's format (its classifier, the matured configurations).

**Development looks (disclosed).** None: the widened values were never run before this design was fixed.

**Expectation, stated before running.** Maturation changes the configuration in at least two classes, moving to
L0 = 0.1 or 0.2 in at least one. MATURED_BETTER at 1 s is possible but not likely to reach significance (B20_R105's
choices already leave a mean gap of 0.003% at 1 s); NO_DIFFERENCE at 10 s.
**Cost.** About 45 minutes. **Status.** DEV; licenses nothing; Gset is not touched.
"""
import json
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
import b20r105_mcx_configure as R105  # noqa: E402

STUDY = 'b20r108'
SEED = 20281081      # graph seeds SEED + 1000 k + i stay clear of B20_R105's (2027xxxx)
SHORT, LONG = R105.SHORT, R105.LONG
PER_CLASS, MUTANTS_1S, MUTANTS_10S = 32, 31, 4
ROUNDS_1S = R105.ROUNDS_1S
ROUNDS_10S = ((4, 8), (4, 2))
PLUS_SHAPES = ((29, 101), (26, 115), (33, 91), (34, 89), (41, 73), (38, 79), (47, 63), (49, 61), (51, 59), (53, 57))
INCUMBENTS = ROOT / 'evidence' / 'mcx_configure_b20r105' / 'configs.json'
CLASSES = R105.CLASSES
ALPHA = 0.025
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def setting(cls, i):
    s = R105.SETTINGS[cls][i % len(R105.SETTINGS[cls])]
    if s == 'plus':
        r, c = PLUS_SHAPES[i // len(R105.SETTINGS[cls])]
        return 'torus2d', {'rows': r, 'cols': c}
    return s


def pools(excluded):
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out = set(excluded), {}
    for k, cls in enumerate(CLASSES):
        out[cls] = []
        for i in range(PER_CLASS):
            fam, params = setting(cls, i)
            ts, seen, _ = A.generate(SEED + 1000 * k + i, 1, 'DEV', fam, params, excluded=seen)
            out[cls].append(ts[0])
    return out


def mutants(incumbent, count, tag):
    """`count` distinct configurations, each the incumbent with one or two keys changed to other values of WIDE."""
    from genesis.candidate_kinds import mcx as K
    rng = random.Random(digest({'study': STUDY, 'seed': SEED, 'tag': tag}))
    keys, out = {json.dumps(incumbent, sort_keys=True)}, []
    while len(out) < count:
        m = dict(incumbent)
        for k in rng.sample(sorted(K.WIDE), rng.choice((1, 2))):
            m[k] = rng.choice([v for v in K.WIDE[k] if v != incumbent[k]])
        s = json.dumps(m, sort_keys=True)
        if s not in keys:
            keys.add(s)
            out.append(m)
    return out


def labels(held, kept):
    """held: {graph: {'incumbent@b', 'matured@b'}}; kept: {budget: [classes whose incumbent won]}."""
    out = {}
    for b in ('1', '10'):
        gp = R105.gaps({g: {a: by[a] for a in (f'incumbent@{b}', f'matured@{b}')} for g, by in held.items()})
        gs = sorted(gp)
        w, p = R105.compare([gp[g][f'matured@{b}'] for g in gs], [gp[g][f'incumbent@{b}'] for g in gs], ALPHA)
        out[f'maturation@{b}'] = {
            'label': {'A': 'MATURED_BETTER', 'B': 'MATURED_WORSE', None: 'NO_DIFFERENCE'}[w], 'p': p,
            'incumbent_kept_in': kept[b], 'wins': sum(held[g][f'matured@{b}'] > held[g][f'incumbent@{b}'] for g in gs),
            'losses': sum(held[g][f'matured@{b}'] < held[g][f'incumbent@{b}'] for g in gs),
            'mean_gap_matured': statistics.mean(gp[g][f'matured@{b}'] for g in gs),
            'mean_gap_incumbent': statistics.mean(gp[g][f'incumbent@{b}'] for g in gs)}
        if len(kept[b]) == len(CLASSES):
            out[f'maturation@{b}']['label'] = 'INCUMBENT_KEPT'
    return out


def run_seed(task_id, arm, budget):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'mcx_maturation_b20r108').resolve():
        raise SystemExit('the registered output is evidence/mcx_maturation_b20r108')
    inc = json.loads(INCUMBENTS.read_text())
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
    log(f'{STUDY}; pinned to CPU {cpu}; incumbents {digest(inc)[:12]}')
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    from genesis.domains import adapter
    from genesis.candidate_kinds import mcx as K
    A = adapter('maxcut_v1')
    excluded = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    excluded |= {A.exposure_identity(t)['canonical'] for ts in R105.pools(set(excluded)).values() for t in ts}
    P = pools(excluded)
    log(f'graphs: {sum(len(v) for v in P.values())}; {len(excluded)} identities excluded (Gset and B20_R105)')
    path = out / 'runs.jsonl'
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r['key']] = r
    desc = {}

    def value(task, cfg, b):
        arm = 'mcx:' + digest(cfg)[:12]
        key = f'{task.task_id}|{arm}|{b:g}'
        if key not in cache:
            if time.monotonic() - t0 > SLICE_S:
                raise Paused
            if (arm, b) not in desc:
                desc[(arm, b)] = CM.build_descriptor('mcx-v1', {'cpu_seconds': b, 'config': cfg}, cpu_seconds=b,
                                                     wall_seconds=max(60, int(3 * b) + 60))
            d = desc[(arm, b)]
            r = CM.run(task, d, seed=run_seed(task.task_id, arm, b), expected_id=d['descriptor_id'], isolation='runc')
            ok = r.get('status') == 'SUCCESS'
            cache[key] = {'key': key, 'task': task.task_id, 'arm': arm, 'budget': b, 'descriptor': d['descriptor_id'],
                          'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'),
                          'value': r['result']['value'] if ok else None}
            with path.open('a') as f:
                f.write(json.dumps(cache[key], sort_keys=True) + '\n')
        return cache[key]['value']

    matured, history, kept = {}, {}, {'1': [], '10': []}
    try:
        for cls in CLASSES:
            g = P[cls]
            tasks = {t.task_id: t for t in g}
            i1, i10 = inc['chosen'][cls]['1'], inc['chosen'][cls]['10']
            c1 = [i1] + mutants(i1, MUTANTS_1S, f'{cls}@1')
            by = {'mcx:' + digest(c)[:12]: c for c in c1}
            arms1 = list(by)
            w1, h1 = R105.race(lambda a, tid: value(tasks[tid], by[a], SHORT), arms1, ROUNDS_1S,
                               [t.task_id for t in g[:16]])
            c10 = [i10] + mutants(i10, MUTANTS_10S, f'{cls}@10')
            by.update({'mcx:' + digest(c)[:12]: c for c in c10})
            arms10 = []
            for a in ['mcx:' + digest(c)[:12] for c in c10] + h1[-1]['ranked'][:3]:
                if a not in arms10:
                    arms10.append(a)
            w10, h10 = R105.race(lambda a, tid: value(tasks[tid], by[a], LONG), arms10, ROUNDS_10S,
                                 [t.task_id for t in g[16:24]])
            matured[cls] = {'1': by[w1], '10': by[w10]}
            history[cls] = {'1s': h1, '10s': h10}
            for b, w, i in (('1', w1, i1), ('10', w10, i10)):
                if by[w] == i:
                    kept[b].append(cls)
            log(f'{cls}: matured@1 {by[w1]} ({"kept" if by[w1] == i1 else "changed"}); matured@10 {by[w10]} '
                f'({"kept" if by[w10] == i10 else "changed"})')
        held = {}
        for cls in CLASSES:
            for t in P[cls][24:]:
                row = {}
                for b in (SHORT, LONG):
                    row[f'incumbent@{b:g}'] = value(t, inc['chosen'][cls][f'{b:g}'], b)
                    row[f'matured@{b:g}'] = value(t, matured[cls][f'{b:g}'], b)
                held[t.task_id] = row
                log(f'held {t.task_id}: {row}')
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    lab = labels(held, kept)
    ok, med, fails = R105.validity(cache)
    configs = dict(inc, schema='genesis-b20r108-mcx-configs-v1', chosen=matured, matured_from=digest(inc),
                   binary_sha256=K.BINARY_SHA256)
    (out / 'configs.json').write_text(json.dumps(configs, indent=1, sort_keys=True) + '\n')
    summary = {'study': STUDY, 'schema': 'genesis-b20r108-summary-v1', 'labels': lab, 'valid': ok, 'cpu_median': med,
               'failed_runs': fails, 'runs': len(cache), 'history': history, 'held_out': held, 'kept': kept,
               'incumbents_sha256': digest(inc), 'configs_sha256': digest(configs),
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'valid {ok}; ' + '; '.join(f'{k} {v["label"]} (p {v["p"]:.3g}, {v["wins"]}-{v["losses"]})' for k, v in lab.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
