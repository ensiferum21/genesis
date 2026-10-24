#!/usr/bin/env python3
"""B20_R127: does an engine the system writes itself beat the engines humans designed? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r127_self_invented_engine.py OUT_DIR     run ALONE (resumable after the search)

**Why.** Daniel, 24 Oct 2026: the system should invent improvements to itself, better than we do. B20_R125 turned the
max-cut engine into an interpreter of search programs over physics operators; B20_R126 gave the system an inventor
that writes such programs under the feedback contract. This study lets it invent an engine from scratch and holds the
result against the human-designed engines, last of all on Gset.

**Design (fixed before running; amended at 09:55 on 24 Oct 2026, before any run, at Daniel's request "use this to
adapt and make it even better": per-class engines, three compounding generations, Gset at 60 s; the first design is
in the commit `70a590d`).**
  * **Graphs** (fresh, generated as Gset's families were, B20_R105's settings without the 3,000-vertex tori; Gset's
    identities excluded; seeds from SEED): per class (random, planar, toroidal), split A (the inventor's training
    data) 4 graphs, B and C (the judge's two confirmation splits) 4 each, D (held out) 5; the settings in rotation.
  * **Reference:** on every graph, the builder's hybrid REX (`mcx2` DEFAULT) at 1 s, one fixed seed. An engine's
    score on a split is the mean over its graphs of its cut divided by that reference (above 1: better than REX).
  * **The invention, per class, in three generations:** `selfimprove.search` with the ORIGINAL process (the feedback
    contract version 2's search), MAX_EVALS = 160 split evaluations per generation (each split evaluation runs the
    engine on the split's 4 graphs at 1 s; seeds from the evaluation count). Generation 1 starts from random engines;
    generations 2 and 3 start from the previous generation's engine and three of its mutations (the system's own
    work, never a human design), then random engines. A generation's engine is the judge's incumbent.
    **Second amendment (09:51, before any run; Daniel: "we can learn from failures too"):** from generation 2 on, the
    inventor also gets a library of macros learned (`selfimprove.learn_macros`, 6 macros) from the 20 best distinct
    engines by mean training score over all earlier generations of the class, its own successes; failures are what
    the judge rejected and the scores it saw, and steer the library.
    **Third amendment (09:58, before any run; Daniel: "different types of thinking"):** analogy across classes. From
    generation 2 on, the start also includes the previous generation's engines of the two other classes (ideas found
    on one kind of graph tried on another). The language gained D (pair descent, Ma and Hao 2017) and L (path
    relinking, Shylo, Glover and Sergienko) after a literature check; their templates are in TEMPLATES. The class's
    engine (SYSTEM) is generation 3's. The pinned binary is run directly during the search (no sandbox, for speed);
    every judged run below goes through `candidates_maxcut` in the runc sandbox.
  * **Human-designed engines (the comparators):**
      - BLS: breakout local search's published setting (`mcx-v1` DEFAULT);
      - MCX: `mcx-v1` with B20_R105's configuration for the graph's class and budget (the builder-configured engine
        that led every published heuristic on Gset, B20_R106);
      - REX: the builder's physics hybrid (`mcx2-v1` DEFAULT).
  * **Held-out test (D):** SYSTEM, MCX, REX and BLS at 1 s and at 10 s, and the generation-1 and generation-2
    engines at 1 s; one seed per (graph, engine, budget).
  * **Gset test:** SYSTEM, MCX, REX and BLS at 10 s on G1-G54, and SYSTEM at 60 s; one seed each; classes by
    B20_R105's classifier.
  * **Test 1 (primary):** on Gset at 10 s, SYSTEM against MCX: sign test on per-instance values (ties dropped,
    two-sided, alpha 0.05): SYSTEM_BETTER / SYSTEM_WORSE / NOT_DISTINGUISHABLE. **Verdict:**
    INVENTED_BETTER_THAN_HUMAN_DESIGN if SYSTEM_BETTER, NOT_SHOWN otherwise.
  * **Secondary** (the same test, reported):
      - SYSTEM against REX and BLS on Gset at 10 s; against each of the three on D at 1 s and 10 s;
      - compounding: generation 3 against generation 1 on D at 1 s: COMPOUNDS / REGRESSES / NOT_DISTINGUISHABLE;
      - SYSTEM at 60 s against B20_R110's 60 s values (MCX, another seed), the instances at their best known value,
        and RECORD_CANDIDATE for any value above it (kept, checked against the literature, never claimed here);
      - whether an engine's program equals one of the human designs written in the same language (TEMPLATES), and
        each generation's claimed and released scores.
  * **Validity:** median metered CPU at least 0.9 of each budget; at most 1% failed runs.

**Development looks (disclosed).** B20_R125's tests; one look at REX, BLS and MCX at 1 s on six graphs of another seed
(REX about BLS, below MCX on planar graphs). No search was run.

**Expectation, stated before running.** The inventor finds engines with larger perturbations and some population
moves that beat REX on their own data; on Gset at 10 s SYSTEM is NOT_DISTINGUISHABLE from MCX (the builder-configured
engine already matches the best known values on many instances at 10 s). Generations do not compound measurably
(NOT_DISTINGUISHABLE). At 60 s, no record candidate. NOT_SHOWN.
**Cost.** Search about 96 min; held-out about 12 min; Gset about 90 min: about 3.3 h, in two slices.
**Status.** DEV; licenses nothing.
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

STUDY = 'b20r127'
SEED = 20351271
SPLITS = {'A': 4, 'B': 4, 'C': 4, 'D': 5}            # graphs per class
SEARCH_BUDGET, MAX_EVALS, GENERATIONS = 1.0, 160, 3
CLASSES = ('random', 'planar', 'toroidal')
BUDGETS = (1.0, 10.0)
ALPHA = 0.05
ENGINES = ('SYSTEM', 'MCX', 'REX', 'BLS')
LONG = 60.0
TEMPLATES = {'BLS-like': 'b1', 'PT': 'B100 X', 'PT+ICM': 'B100 X I', 'REX': 'B100 X I S2000 C',
             'Houdayer restart': 'B1 S2000 H', 'renormalisation restart': 'B1 S2000 C', 'MACUT restart': 'B1 S2000 M',
             'MOH-like (pair descent)': 'b1 D', 'GES-PR-like (path relinking)': 'B100 S2000 L'}
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def settings():
    import b20r105_mcx_configure as R105M
    return {cls: [s for s in R105M.SETTINGS[cls] if s != 'plus'] for cls in ('random', 'planar', 'toroidal')}


def graphs(excluded):
    """{class: {split: [task]}} of fresh generated graphs."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out, k = set(excluded), {}, 0
    st = settings()
    for cls in CLASSES:
        out[cls] = {}
        for split, per in SPLITS.items():
            out[cls][split] = []
            for i in range(per):
                fam, params = st[cls][(i + k) % len(st[cls])]
                ts, seen, _ = A.generate(SEED + 100 * k + i, 1, 'DEV', fam, params, excluded=seen)
                out[cls][split].append(ts[0])
            k += 1
    return out


def sign(a, b):
    from scipy.stats import binomtest
    w = sum(x > y for x, y in zip(a, b))
    lo = sum(x < y for x, y in zip(a, b))
    p = float(binomtest(w, w + lo, 0.5).pvalue) if w + lo else 1.0
    return {'wins': w, 'losses': lo, 'ties': len(a) - w - lo, 'p': p,
            'label': 'NOT_DISTINGUISHABLE' if p >= ALPHA else ('SYSTEM_BETTER' if w > lo else 'SYSTEM_WORSE')}


def template_of(cfg):
    return [name for name, prog in TEMPLATES.items() if cfg['prog'] == prog]


def analyse(held, gens, gset_rows, best, r110):
    """held: {budget: {graph: {engine: value}}}; gens: {graph: {'G1', 'G2', 'G3': value at 1 s}};
    gset_rows: [{instance, values: {engine: value at 10 s}, long: SYSTEM at 60 s}]; r110: {instance: 60 s value}."""
    out = {'gset': {}, 'held_out': {}}
    gs = [r for r in gset_rows if all(r['values'][e] is not None for e in ENGINES)]
    for other in ('MCX', 'REX', 'BLS'):
        out['gset'][other] = sign([r['values']['SYSTEM'] for r in gs], [r['values'][other] for r in gs])
    for b, rows in held.items():
        gl = [g for g in rows if all(rows[g][e] is not None for e in ENGINES)]
        out['held_out'][b] = {o: sign([rows[g]['SYSTEM'] for g in gl], [rows[g][o] for g in gl])
                              for o in ('MCX', 'REX', 'BLS')}
    gg = [g for g in gens if all(gens[g][x] is not None for x in ('G1', 'G3'))]
    c = sign([gens[g]['G3'] for g in gg], [gens[g]['G1'] for g in gg])
    c['label'] = {'SYSTEM_BETTER': 'COMPOUNDS', 'SYSTEM_WORSE': 'REGRESSES'}.get(c['label'], c['label'])
    out['compounding'] = c
    out['gset_reach_best_known'] = {e: sum(r['values'][e] >= best[r['instance']] for r in gs) for e in ENGINES}
    out['gset_mean_fraction'] = {e: statistics.mean(r['values'][e] / best[r['instance']] for r in gs) for e in ENGINES}
    lg = [r for r in gset_rows if r['long'] is not None]
    out['long'] = {'vs_r110': sign([r['long'] for r in lg], [r110[r['instance']] for r in lg]),
                   'reach_best_known': sum(r['long'] >= best[r['instance']] for r in lg),
                   'reached': [r['instance'] for r in lg if r['long'] >= best[r['instance']]],
                   'mean_fraction': statistics.mean(r['long'] / best[r['instance']] for r in lg) if lg else None}
    out['record_candidates'] = (
        [{'instance': r['instance'], 'engine': e, 'budget': 10.0, 'value': r['values'][e], 'best_known': best[r['instance']]}
         for r in gs for e in ENGINES if r['values'][e] > best[r['instance']]] +
        [{'instance': r['instance'], 'engine': 'SYSTEM', 'budget': LONG, 'value': r['long'],
          'best_known': best[r['instance']]} for r in lg if r['long'] > best[r['instance']]])
    t1 = out['gset']['MCX']
    out['test1'] = t1
    out['verdict'] = 'INVENTED_BETTER_THAN_HUMAN_DESIGN' if t1['label'] == 'SYSTEM_BETTER' else 'NOT_SHOWN'
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'self_invented_engine_b20r127').resolve():
        raise SystemExit('the registered output is evidence/self_invented_engine_b20r127')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r105_mcx_configure as R105M
    import b20r116_gset_attempt as R116
    from genesis import candidates_maxcut as CM
    from genesis import gset as GS
    from genesis.autonomy import selfimprove as SI
    from genesis.candidate_kinds import mcx as K1
    from genesis.candidate_kinds import mcx2 as K2
    from genesis.domains import adapter
    from genesis.models_maxcut import MaxCutCandidateView
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    c105 = R116.checked(R116.R105)
    log(f'{STUDY}; pinned to CPU {cpu}')
    A = adapter('maxcut_v1')
    ex = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    G = graphs(ex)
    log('graphs: ' + ', '.join(f'{c} {sum(len(v) for v in G[c].values())}' for c in CLASSES))

    def direct(cfg, kind, task, budget, seed):
        K = K2 if kind == 'mcx2' else K1
        return K.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg},
                       budget, seed)['value']

    # ---- references and the invention, per class and generation (each generation saved when done)
    spath = out / 'search.json'
    search = json.loads(spath.read_text()) if spath.exists() else {'references': {}, 'generations': {}}
    ref = search['references']
    for cls in CLASSES:
        for t in G[cls]['A'] + G[cls]['B'] + G[cls]['C']:
            if t.task_id not in ref:
                ref[t.task_id] = direct(K2.DEFAULT, 'mcx2', t, SEARCH_BUDGET, 1)
    tpath = out / 'trace.jsonl'

    def top_engines(cls, k):
        """The k best distinct engines of the class's earlier generations by mean training (A) score."""
        scores = {}
        if tpath.exists():
            for line in tpath.read_text().splitlines():
                if line.strip():
                    x = json.loads(line)
                    if x['gen'].startswith(cls + '|') and x['split'] == 'A':
                        scores.setdefault(x['engine'], []).append(x['value'])
        ranked = sorted(scores, key=lambda e: (-statistics.mean(scores[e]), e))
        return [json.loads(e) for e in ranked[:k]]
    for gen in range(1, GENERATIONS + 1):
        for cls in CLASSES:
            gk = f'{cls}|{gen}'
            if gk in search['generations']:
                continue
            if time.monotonic() - t0 > SLICE_S:
                spath.write_text(json.dumps(search, indent=1, sort_keys=True) + '\n')
                log(f'time slice used ({SLICE_S} s): paused before {gk}')
                return PAUSED
            counter, trace = [0], []

            def evaluate(cfg, split):
                counter[0] += 1
                seed = int(digest({'study': STUDY, 'gen': gk, 'eval': counter[0]})[:12], 16)
                v = statistics.mean(direct(cfg, 'mcx2', t, SEARCH_BUDGET, seed + i) / ref[t.task_id]
                                    for i, t in enumerate(G[cls][split]))
                trace.append({'gen': gk, 'n': counter[0], 'split': split, 'value': v, 'engine': SI.key(cfg)})
                return v
            ops = SI.engine_ops()
            if gen > 1:
                prev = search['generations'][f'{cls}|{gen - 1}']['engine']
                srng = random.Random(f'{STUDY}|{gk}')
                lib = SI.learn_macros(top_engines(cls, 20), 6)
                search.setdefault('libraries', {})[gk] = lib
                others = [search['generations'][f'{c}|{gen - 1}']['engine'] for c in CLASSES if c != cls]
                ops = SI.seeded_ops(SI.engine_ops(library=lib),
                                    [prev] + [SI.mutate(prev, srng) for _ in range(3)] + others)
            winner, rep = SI.search(SI.ORIGINAL, ops, evaluate, MAX_EVALS,
                                    int(digest({'study': STUDY, 'gen': gk})[:12], 16))
            search['generations'][gk] = {'engine': winner, 'report': rep}
            spath.write_text(json.dumps(search, indent=1, sort_keys=True) + '\n')
            with tpath.open('a') as f:
                f.write(''.join(json.dumps(x, sort_keys=True) + '\n' for x in trace))
            log(f"{gk}: engine {json.dumps(winner, sort_keys=True)}; judge {rep['judge']}")
    eng = {cls: search['generations'][f'{cls}|{GENERATIONS}']['engine'] for cls in CLASSES}

    # ---- judged runs (resumable), in the runc sandbox
    path = out / 'runs.jsonl'
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r['key']] = r
    desc = {}

    def arm(engine, cls, budget):
        if engine == 'SYSTEM':
            return 'mcx2-v1', eng[cls]
        if engine in ('G1', 'G2'):
            return 'mcx2-v1', search['generations'][f'{cls}|{engine[1]}']['engine']
        if engine == 'REX':
            return 'mcx2-v1', K2.DEFAULT
        if engine == 'BLS':
            return 'mcx-v1', K1.DEFAULT
        return 'mcx-v1', c105['chosen'][cls][f'{budget:g}']

    def value(task, cls, engine, budget, part):
        key = f'{part}|{task.task_id}|{engine}|{budget:g}'
        if key not in cache:
            if time.monotonic() - t0 > SLICE_S:
                raise Paused
            kind, cfg = arm(engine, cls, budget)
            dk = (kind, json.dumps(cfg, sort_keys=True), budget)
            if dk not in desc:
                desc[dk] = CM.build_descriptor(kind, {'cpu_seconds': budget, 'config': cfg}, cpu_seconds=budget,
                                               wall_seconds=int(3 * budget) + 60)
            d = desc[dk]
            seed = int(digest({'study': STUDY, 'task': task.task_id, 'engine': engine, 'budget': budget})[:12], 16)
            r = CM.run(task, d, seed=seed, expected_id=d['descriptor_id'], isolation='runc')
            ok = r.get('status') == 'SUCCESS'
            cache[key] = {'key': key, 'task': task.task_id, 'engine': engine, 'budget': budget, 'part': part,
                          'status': r.get('status'), 'cpu_ns': r.get('cpu_ns'), 'descriptor': d['descriptor_id'],
                          'value': r['result']['value'] if ok else None, 'side': r['result']['side'] if ok else None}
            with path.open('a') as f:
                f.write(json.dumps(cache[key], sort_keys=True) + '\n')
        return cache[key]['value']
    try:
        held, gens = {}, {}
        for b in BUDGETS:
            held[f'{b:g}'] = {}
            for cls in CLASSES:
                for t in G[cls]['D']:
                    held[f'{b:g}'][t.task_id] = {e: value(t, cls, e, b, 'D') for e in ENGINES}
            log(f'held-out at {b:g} s done')
        for cls in CLASSES:
            for t in G[cls]['D']:
                gens[t.task_id] = {'G1': value(t, cls, 'G1', 1.0, 'D'), 'G2': value(t, cls, 'G2', 1.0, 'D'),
                                   'G3': held['1'][t.task_id]['SYSTEM']}
        best = GS.best_known()
        r110 = {r['instance']: r['value'] for r in R116._rows(R116.R110 / 'rows.jsonl')}
        gset_rows = []
        for t in GS.tasks():
            cls = R105M.classify(c105['classifier'], R105M.features(t))
            g = t.task_id.split('-')[1]
            vals = {e: value(t, cls, e, 10.0, 'G') for e in ENGINES}
            gset_rows.append({'instance': g, 'class': cls, 'values': vals, 'long': None})
            log(f"{g} [{cls}] best known {best[g]}: " + ', '.join(f'{e} {vals[e]}' for e in ENGINES))
        for row, t in zip(gset_rows, GS.tasks()):
            row['long'] = value(t, row['class'], 'SYSTEM', LONG, 'L')
            log(f"{row['instance']} SYSTEM at 60 s: {row['long']} (best known {best[row['instance']]}, B20_R110 "
                f"{r110[row['instance']]})")
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    res = analyse(held, gens, gset_rows, best, r110)
    cpus = {}
    fails = 0
    for r in cache.values():
        if r['status'] != 'SUCCESS':
            fails += 1
        elif r['cpu_ns']:
            cpus.setdefault(f"{r['budget']:g}", []).append(r['cpu_ns'] / 1e9 / r['budget'])
    med = {b: statistics.median(v) for b, v in cpus.items()}
    valid = all(m >= 0.9 for m in med.values()) and fails <= 0.01 * max(1, len(cache))
    summary = dict(res, study=STUDY, schema='genesis-b20r127-self-invented-engine-v1', valid=valid, cpu_median=med,
                   failed_runs=fails, engines=eng,
                   engines_are_templates={c: template_of(e) for c, e in eng.items()},
                   generations={k: {'engine': v['engine'], 'judge': v['report']['judge'],
                                    'reported': v['report']['reported']} for k, v in search['generations'].items()},
                   libraries=search.get('libraries', {}),
                   held_out_values=held, generation_values=gens, gset_rows=gset_rows,
                   code_identity=code_identity(ROOT)['sha256'],
                   status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; test 1 {res['test1']['label']} ({res['test1']['wins']}-{res['test1']['losses']}); verdict "
        f"{res['verdict']}; compounding {res['compounding']['label']}; Gset at best known (10 s): "
        f"{res['gset_reach_best_known']}; SYSTEM at 60 s: {res['long']['reach_best_known']}; record candidates "
        f"{len(res['record_candidates'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
