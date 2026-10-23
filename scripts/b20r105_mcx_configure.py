#!/usr/bin/env python3
"""B20_R105: the system configures its max-cut engine on generated graphs, never on Gset (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r105_mcx_configure.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** Published max-cut heuristics were tuned by their authors on the benchmark they report. Genesis's engine,
`mcx-v1` (B20_R104), has a configuration space of 5,184 settings (perturbation strength, directed-move floor, tabu
tenure, elite pool, restart period; restart operator: none, a cluster exchange, a renormalisation step or MACUT's
multi-parent crossover; perturbation rules, including breakout local search's own). Its DEFAULT is breakout local
search's published setting (Benlic and Hao 2013; our implementation in this engine), so "chosen vs DEFAULT" asks
whether the system's choice beats the published method as adapted. Here the system chooses its configuration, by two
of the organism plan's mechanisms
(`docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md`), on data it may use: graphs generated as Gset's were, never Gset.
B20_R106 then applies the result to Gset, once.
  * **Order parameters choose the method.** Each graph is placed in a structural class (random, toroidal, planar) by
    two order parameters of its degree sequence (the coefficient of variation and the log of the largest degree over
    the mean), with nearest centroids learned from the training graphs. One configuration per class and budget.
  * **Germinal-centre selection.** Candidate configurations compete for evaluations as B cells compete for antigen:
    successive halving, each round on fresh graphs, the weaker ones dropped.

**Design (fixed before running).**
  * **Graphs.** Three classes, each a rotation through Gset's generator settings with fresh draws (`maxcut_v1`
    generated families; the identities of all 54 Gset graphs excluded, and no repeats):
      - random: erdos and erdos_pm1 (n = 800, p = 0.06), erdos and erdos_pm1 (2000, 0.01), erdos (1000, 0.02);
      - toroidal: torus2d_pm1 100 x 8 and 100 x 20, and torus2d (weights 1) on ten shapes of 2,880-3,150 vertices
        that are not Gset's (G48-G50 are 50 x 60, 30 x 100 and 25 x 120), some with an odd side (frustrated);
      - planar: planar2 and planar2_pm1 (800, 0.99), planar2 and planar2_pm1 (2000, 0.99), planar2 (1000, 0.99).
    32 graphs per class: 16 for the 1 s race, 8 for the 10 s race, 8 held out.
  * **Runs.** `mcx-v1` through `candidates_maxcut` in the runc sandbox, one core, one seed per (graph, arm, budget)
    from the study, graph, arm and budget. A run's score on a graph is its gap below the best value that the runs
    being compared reached on that graph, (best - value) / best; a configuration's score is its mean gap.
  * **1 s race, per class.** DEFAULT and 31 distinct configurations drawn from SPACE. Round 1: all 32 on 4 graphs;
    the best 10 on 4 more; the best 3 on 8 more; the lowest mean gap over the 16 graphs wins (ties: DEFAULT first,
    then the order drawn).
  * **10 s race, per class.** The 1 s race's final three and DEFAULT, on 4 fresh graphs at 10 s; the best 2 on 4 more;
    the lowest mean gap over the 8 wins.
  * **Held out** (8 graphs per class, 24 in all): DEFAULT (breakout local search's setting) and the class's chosen
    configuration at 1 s and at 10 s, and `mqlib-maxcut-v1` BURER2002 at 1 s and 10 s (the best single heuristic of
    Dunning et al. 2018).
  * **Labels, per budget** (Wilcoxon signed-rank test of the per-graph gaps over the 24 held-out graphs, two-sided,
    zeros dropped, alpha 0.025 for the two budgets): chosen vs DEFAULT, TUNED_BETTER / TUNED_WORSE / NO_DIFFERENCE;
    chosen vs BURER2002, MCX_AHEAD / MCX_BEHIND / COMPARABLE. The classifier's accuracy on the held-out graphs.
    Validity: median metered CPU at least 0.9 of each budget, at most 1% failed runs.
  * **Output.** `configs.json` (the classifier and the chosen configuration per class and budget): B20_R106's input.

**Development looks (disclosed).** On 23 Oct 2026 the builder ran mcx in-process (one seed) on six generated graphs
(dev seeds 777001-777006; erdos 800/0.06, erdos_pm1 2000/0.01, torus2d_pm1 100 x 20, torus2d 25 x 119, planar2
800/0.99, planar2_pm1 2000/0.99), never on Gset. At 1 s, DEFAULT (BLS's setting) was ahead of BURER2002 on four
graphs, tied on one and behind on planar2 (3045 vs 3047); against the builder's earlier perturbation (pert 0) BLS's
rules were ahead on three, tied on two and behind on one; restarts every 2,000 local optima hurt (on these graphs
that is a restart every ~0.01 s), so the restart periods were widened to 2,000-200,000 before this design was fixed.
At 10 s, DEFAULT was ahead of BURER2002 on three (torus2d_pm1 1368 vs 1348, planar2_pm1 2430 vs 2411, erdos 11717 vs
11714), tied on one and behind on two (erdos_pm1 3394 vs 3396, planar2 3045 vs 3047); restarts every 20,000 local
optima did not help.

**Expectation, stated before running.** The races keep DEFAULT or a near variant in most classes (BLS's
setting is strong at these budgets); chosen vs DEFAULT NO_DIFFERENCE at both budgets; MCX_AHEAD of BURER2002 at 1 s,
COMPARABLE at 10 s; the classifier places every held-out graph in its class.
**Cost.** Per class: 192 runs at 1 s, 24 at 10 s, plus held-out 8 x 33 s; about 45 min in all. **Status.** DEV;
licenses nothing.
"""
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r105'
SEED = 20271051
SHORT, LONG = 1.0, 10.0
PER_CLASS, CANDIDATES = 32, 32
ROUNDS_1S = ((4, 32), (4, 10), (8, 3))          # (new graphs, configurations entering the round)
ROUNDS_10S = ((4, 4), (4, 2))
ALPHA = 0.025
PLUS_SHAPES = ((40, 75), (24, 125), (20, 150), (48, 60), (36, 84), (42, 70), (28, 108), (32, 96), (45, 64), (35, 90),
               (27, 112), (44, 66))
SETTINGS = {
    'random': (('erdos', {'n': 800, 'p': 0.06}), ('erdos_pm1', {'n': 800, 'p': 0.06}),
               ('erdos', {'n': 2000, 'p': 0.01}), ('erdos_pm1', {'n': 2000, 'p': 0.01}),
               ('erdos', {'n': 1000, 'p': 0.02})),
    'toroidal': (('torus2d_pm1', {'rows': 100, 'cols': 8}), ('torus2d_pm1', {'rows': 100, 'cols': 20}), 'plus'),
    'planar': (('planar2', {'n': 800, 'density': 0.99}), ('planar2_pm1', {'n': 800, 'density': 0.99}),
               ('planar2', {'n': 2000, 'density': 0.99}), ('planar2_pm1', {'n': 2000, 'density': 0.99}),
               ('planar2', {'n': 1000, 'density': 0.99})),
}
CLASSES = tuple(SETTINGS)
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def setting(cls, i):
    """The family and parameters of graph i of a class."""
    s = SETTINGS[cls][i % len(SETTINGS[cls])]
    if s == 'plus':
        r, c = PLUS_SHAPES[i // len(SETTINGS[cls])]
        return 'torus2d', {'rows': r, 'cols': c}
    return s


def pools(excluded):
    """{class: [32 MaxCutTask]}: fresh draws, no repeats, none of Gset's identities."""
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


def features(task):
    """Two order parameters of the degree sequence: its coefficient of variation and log(max degree / mean)."""
    deg = [0] * task.n
    for u, v, _ in task.edges:
        deg[u] += 1
        deg[v] += 1
    mean = statistics.mean(deg)
    return (statistics.pstdev(deg) / mean, math.log(max(deg) / mean))


def fit_classifier(labelled):
    """Nearest centroid on standardised features; labelled: [(features, class)]."""
    xs = [f for f, _ in labelled]
    mu = [statistics.mean(c) for c in zip(*xs)]
    sd = [statistics.pstdev(c) or 1.0 for c in zip(*xs)]
    z = lambda f: [(a - m) / s for a, m, s in zip(f, mu, sd)]
    cent = {}
    for cls in sorted({c for _, c in labelled}):
        pts = [z(f) for f, c in labelled if c == cls]
        cent[cls] = [statistics.mean(c) for c in zip(*pts)]
    return {'mean': mu, 'sd': sd, 'centroids': cent}


def classify(model, f):
    z = [(a - m) / s for a, m, s in zip(f, model['mean'], model['sd'])]
    return min(model['centroids'], key=lambda c: (sum((a - b) ** 2 for a, b in zip(z, model['centroids'][c])), c))


def draw_configs(cls):
    from genesis.candidate_kinds import mcx as K
    rng = random.Random(digest({'study': STUDY, 'seed': SEED, 'class': cls}))
    out, keys = [dict(K.DEFAULT)], {json.dumps(K.DEFAULT, sort_keys=True)}
    while len(out) < CANDIDATES:
        c = {k: rng.choice(v) for k, v in K.SPACE.items()}
        if json.dumps(c, sort_keys=True) not in keys:
            keys.add(json.dumps(c, sort_keys=True))
            out.append(c)
    return out


def gaps(values):
    """{graph: {arm: value}} -> {graph: {arm: gap below the graph's best}}."""
    out = {}
    for g, by in values.items():
        best = max(v for v in by.values() if v is not None)
        out[g] = {a: (best - v) / best if v is not None and best > 0 else (1.0 if v is None else 0.0)
                  for a, v in by.items()}
    return out


def rank(values, arms, graphs, order):
    """Arms ordered by mean gap over the graphs (ties: their place in `order`, DEFAULT first)."""
    gp = gaps({g: values[g] for g in graphs})
    score = {a: statistics.mean(gp[g][a] for g in graphs) for a in arms}
    return sorted(arms, key=lambda a: (score[a], order.index(a))), score


def race(values_of, arms, rounds, graphs):
    """Successive halving. values_of(arm, graph) runs (or replays) one run; returns (winner, history)."""
    alive, used, hist, order = list(arms), [], [], list(arms)
    for (new, entering) in rounds:
        alive = alive[:entering]
        g_new = graphs[len(used):len(used) + new]
        used += g_new
        vals = {g: {a: values_of(a, g) for a in alive} for g in used}
        alive, score = rank(vals, alive, used, order)
        hist.append({'graphs': list(used), 'ranked': list(alive), 'score': {a: score[a] for a in alive}})
    return alive[0], hist


def compare(a_gaps, b_gaps, alpha=ALPHA):
    """Wilcoxon signed-rank on paired gaps (lower is better): 'A', 'B' or None (no difference), and the p-value."""
    from scipy.stats import wilcoxon
    d = [x - y for x, y in zip(a_gaps, b_gaps) if x != y]
    if len(d) < 6:
        return None, 1.0
    p = float(wilcoxon(d, zero_method='wilcox', alternative='two-sided').pvalue)
    if p >= alpha:
        return None, p
    return ('A' if statistics.mean(d) < 0 else 'B'), p


def labels(held):
    """held: {graph: {arm: value}} with arms 'default@b', 'chosen@b', 'burer@b' for b in 1, 10."""
    out = {}
    for b in ('1', '10'):
        gp = gaps({g: {a: by[a] for a in (f'default@{b}', f'chosen@{b}', f'burer@{b}')} for g, by in held.items()})
        gs = sorted(gp)
        w, p = compare([gp[g][f'chosen@{b}'] for g in gs], [gp[g][f'default@{b}'] for g in gs])
        out[f'tuning@{b}'] = {'label': {'A': 'TUNED_BETTER', 'B': 'TUNED_WORSE', None: 'NO_DIFFERENCE'}[w], 'p': p,
                              'mean_gap_chosen': statistics.mean(gp[g][f'chosen@{b}'] for g in gs),
                              'mean_gap_default': statistics.mean(gp[g][f'default@{b}'] for g in gs)}
        w, p = compare([gp[g][f'chosen@{b}'] for g in gs], [gp[g][f'burer@{b}'] for g in gs])
        wins = sum(held[g][f'chosen@{b}'] > held[g][f'burer@{b}'] for g in gs)
        losses = sum(held[g][f'chosen@{b}'] < held[g][f'burer@{b}'] for g in gs)
        out[f'vs_burer@{b}'] = {'label': {'A': 'MCX_AHEAD', 'B': 'MCX_BEHIND', None: 'COMPARABLE'}[w], 'p': p,
                                'wins': wins, 'losses': losses, 'ties': len(gs) - wins - losses,
                                'mean_gap_burer': statistics.mean(gp[g][f'burer@{b}'] for g in gs)}
    return out


def run_seed(task_id, arm, budget):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def validity(cache):
    cpu, fails = {}, 0
    for x in cache.values():
        if x['status'] != 'SUCCESS':
            fails += 1
        elif x['cpu_ns']:
            cpu.setdefault(x['budget'], []).append(x['cpu_ns'] / 1e9 / x['budget'])
    med = {f'{b:g}': statistics.median(v) for b, v in cpu.items()}
    return all(m >= 0.9 for m in med.values()) and fails <= 0.01 * max(1, len(cache)), med, fails


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'mcx_configure_b20r105').resolve():
        raise SystemExit('the registered output is evidence/mcx_configure_b20r105')
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
    from genesis.domains import adapter
    from genesis.candidate_kinds import mcx as K
    A = adapter('maxcut_v1')
    gset_ids = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    P = pools(gset_ids)
    log('graphs: ' + ', '.join(f'{c} {len(v)}' for c, v in P.items()) + f'; {len(gset_ids)} Gset identities excluded')
    path = out / 'runs.jsonl'
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r['key']] = r
    desc = {}

    def descriptor(arm_key, kind, params, b):
        k = (arm_key, b)
        if k not in desc:
            desc[k] = CM.build_descriptor(kind, params, cpu_seconds=b, wall_seconds=max(60, int(3 * b) + 60))
        return desc[k]

    def value(task, arm_key, kind, params, b):
        key = f'{task.task_id}|{arm_key}|{b:g}'
        if key not in cache:
            if time.monotonic() - t0 > SLICE_S:
                raise Paused
            d = descriptor(arm_key, kind, params, b)
            r = CM.run(task, d, seed=run_seed(task.task_id, arm_key, b), expected_id=d['descriptor_id'], isolation='runc')
            ok = r.get('status') == 'SUCCESS'
            cache[key] = {'key': key, 'task': task.task_id, 'arm': arm_key, 'budget': b, 'descriptor': d['descriptor_id'],
                          'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'),
                          'value': r['result']['value'] if ok else None}
            with path.open('a') as f:
                f.write(json.dumps(cache[key], sort_keys=True) + '\n')
        return cache[key]['value']

    def mcx(cfg):
        return 'mcx:' + digest(cfg)[:12], 'mcx-v1', cfg

    chosen, history = {}, {}
    try:
        for cls in CLASSES:
            g = P[cls]
            cfgs = draw_configs(cls)
            arms = [mcx(c)[0] for c in cfgs]
            by = {mcx(c)[0]: c for c in cfgs}
            tasks = {t.task_id: t for t in g}

            def at(b):
                return lambda a, tid: value(tasks[tid], a, 'mcx-v1', {'cpu_seconds': b, 'config': by[a]}, b)
            w1, h1 = race(at(SHORT), arms, ROUNDS_1S, [t.task_id for t in g[:16]])
            finals = h1[-1]['ranked'][:3]
            entrants = finals + ([arms[0]] if arms[0] not in finals else [])
            w10, h10 = race(at(LONG), entrants, ROUNDS_10S, [t.task_id for t in g[16:24]])
            chosen[cls] = {'1': by[w1], '10': by[w10]}
            history[cls] = {'1s': h1, '10s': h10}
            log(f'{cls}: chosen@1 {by[w1]} (default {"won" if w1 == arms[0] else "lost"}); chosen@10 {by[w10]}')
        held = {}
        for cls in CLASSES:
            for t in P[cls][24:]:
                row = {}
                for b in (SHORT, LONG):
                    for name, cfg in (('default', K.DEFAULT), ('chosen', chosen[cls][f'{b:g}'])):
                        a, kind, c = mcx(cfg)
                        row[f'{name}@{b:g}'] = value(t, a, kind, {'cpu_seconds': b, 'config': c}, b)
                    row[f'burer@{b:g}'] = value(t, 'burer', 'mqlib-maxcut-v1',
                                                {'heuristic': 'BURER2002', 'cpu_seconds': b}, b)
                held[t.task_id] = row
                log(f'held {t.task_id}: {row}')
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    train = [(features(t), cls) for cls in CLASSES for t in P[cls][:24]]
    model = fit_classifier(train)
    acc = statistics.mean(classify(model, features(t)) == cls for cls in CLASSES for t in P[cls][24:])
    lab = labels(held)
    ok, med, fails = validity(cache)
    configs = {'schema': 'genesis-b20r105-mcx-configs-v1', 'classifier': model, 'features': 'degree cv, log(max/mean)',
               'chosen': chosen, 'default': K.DEFAULT, 'kind': 'mcx-v1', 'binary_sha256': K.BINARY_SHA256}
    (out / 'configs.json').write_text(json.dumps(configs, indent=1, sort_keys=True) + '\n')
    summary = {'study': STUDY, 'schema': 'genesis-b20r105-summary-v1', 'labels': lab, 'classifier_accuracy': acc,
               'valid': ok, 'cpu_median': med, 'failed_runs': fails, 'runs': len(cache), 'history': history,
               'held_out': held, 'configs_sha256': digest(configs), 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'valid {ok}; classifier accuracy {acc:.3f}; ' + '; '.join(f'{k} {v["label"]} (p {v["p"]:.3g})'
                                                                     for k, v in lab.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
