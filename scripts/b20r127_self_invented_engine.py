#!/usr/bin/env python3
"""B20_R127: does an engine the system writes itself beat the engines humans designed? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r127_self_invented_engine.py OUT_DIR     run ALONE (resumable after the search)

**Why.** Daniel, 24 Oct 2026: the system should invent improvements to itself, better than we do. B20_R125 turned the
max-cut engine into an interpreter of search programs over physics operators; B20_R126 gave the system an inventor
that writes such programs under the feedback contract. This study lets it invent an engine from scratch and holds the
result against the human-designed engines, last of all on Gset.

**Design (fixed before running).**
  * **Graphs** (fresh, generated as Gset's families were, B20_R105's settings without the 3,000-vertex tori; Gset's
    identities excluded; seeds from SEED): split A (the inventor's training data) 6 graphs, B and C (the judge's two
    confirmation splits) 6 each, D (held out) 15; two (A, B, C) or five (D) per class (random, planar, toroidal),
    the settings in rotation.
  * **Reference:** on every graph, the builder's hybrid REX (`mcx2` DEFAULT) at 1 s, one fixed seed. An engine's
    score on a split is the mean over its graphs of its cut divided by that reference (above 1: better than REX).
  * **The invention:** `selfimprove.search` with the ORIGINAL process (B20_R126; the feedback contract version 2's
    search), starting from random engines, MAX_EVALS = 300 split evaluations (each split evaluation runs the engine on
    the split's 6 graphs at 1 s, seeds from the evaluation count). The engine is the judge's incumbent (its released
    engine, or the starting one if nothing was released). The pinned binary is run directly during the search (no
    sandbox, for speed); every judged run below goes through `candidates_maxcut` in the runc sandbox.
  * **Human-designed engines (the comparators):**
      - BLS: breakout local search's published setting (`mcx-v1` DEFAULT);
      - MCX: `mcx-v1` with B20_R105's configuration for the graph's class and budget (the builder-configured engine
        that led every published heuristic on Gset, B20_R106);
      - REX: the builder's physics hybrid (`mcx2-v1` DEFAULT).
  * **Held-out test (D):** the four engines at 1 s and at 10 s, one seed per (graph, engine, budget).
  * **Gset test:** the four engines at 10 s on G1-G54, one seed each, classes by B20_R105's classifier.
  * **Test 1 (primary):** on Gset at 10 s, the invented engine against MCX: sign test on per-instance values (ties
    dropped, two-sided, alpha 0.05): SYSTEM_BETTER / SYSTEM_WORSE / NOT_DISTINGUISHABLE. **Verdict:**
    INVENTED_BETTER_THAN_HUMAN_DESIGN if SYSTEM_BETTER, NOT_SHOWN otherwise.
  * **Secondary** (same test, reported): the invented engine against REX and BLS on Gset; against each of the three
    on D at 1 s and 10 s. Also: whether the invented program equals one of the human designs written in the same
    language (TEMPLATES), the search's claimed and released scores, and the instances at their best known value.
  * **Validity:** median metered CPU at least 0.9 of the budget; at most 1% failed runs.

**Development looks (disclosed).** B20_R125's tests; one look at REX, BLS and MCX at 1 s on six graphs of another seed
(REX about BLS, below MCX on planar graphs). No search was run.

**Expectation, stated before running.** The inventor finds an engine with larger perturbations and some population
moves that beats REX on its own data; on Gset at 10 s it is NOT_DISTINGUISHABLE from MCX (the builder-configured
engine already matches the best known values on many instances at 10 s), behind it on planar graphs. NOT_SHOWN.
**Cost.** Search about 35 min; held-out about 12 min; Gset about 40 min. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r127'
SEED = 20351271
SPLITS = {'A': 2, 'B': 2, 'C': 2, 'D': 5}            # graphs per class
SEARCH_BUDGET, MAX_EVALS = 1.0, 300
BUDGETS = (1.0, 10.0)
ALPHA = 0.05
ENGINES = ('SYSTEM', 'MCX', 'REX', 'BLS')
TEMPLATES = {'BLS-like': 'b1', 'PT': 'B100 X', 'PT+ICM': 'B100 X I', 'REX': 'B100 X I S2000 C',
             'Houdayer restart': 'B1 S2000 H', 'renormalisation restart': 'B1 S2000 C', 'MACUT restart': 'B1 S2000 M'}
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def settings():
    import b20r105_mcx_configure as R105M
    return {cls: [s for s in R105M.SETTINGS[cls] if s != 'plus'] for cls in ('random', 'planar', 'toroidal')}


def graphs(excluded):
    """{split: [task]} of fresh generated graphs, classes in a fixed order."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out, k = set(excluded), {}, 0
    for split, per in SPLITS.items():
        out[split] = []
        for cls, st in settings().items():
            for i in range(per):
                fam, params = st[(i + k) % len(st)]
                ts, seen, _ = A.generate(SEED + 100 * k + i, 1, 'DEV', fam, params, excluded=seen)
                out[split].append((cls, ts[0]))
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


def analyse(held, gset_rows, best):
    """held: {budget: {graph: {engine: value}}}; gset_rows: [{instance, values: {engine: value}}]."""
    out = {'gset': {}, 'held_out': {}}
    gs = [r for r in gset_rows if all(r['values'][e] is not None for e in ENGINES)]
    for other in ('MCX', 'REX', 'BLS'):
        out['gset'][other] = sign([r['values']['SYSTEM'] for r in gs], [r['values'][other] for r in gs])
    for b, rows in held.items():
        gl = [g for g in rows if all(rows[g][e] is not None for e in ENGINES)]
        out['held_out'][b] = {o: sign([rows[g]['SYSTEM'] for g in gl], [rows[g][o] for g in gl])
                              for o in ('MCX', 'REX', 'BLS')}
    out['gset_reach_best_known'] = {e: sum(r['values'][e] >= best[r['instance']] for r in gs) for e in ENGINES}
    out['gset_mean_fraction'] = {e: statistics.mean(r['values'][e] / best[r['instance']] for r in gs) for e in ENGINES}
    out['record_candidates'] = [{'instance': r['instance'], 'engine': e, 'value': r['values'][e],
                                 'best_known': best[r['instance']]}
                                for r in gs for e in ENGINES if r['values'][e] > best[r['instance']]]
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
    log('graphs: ' + ', '.join(f'{s} {len(v)}' for s, v in G.items()))

    def direct(cfg, kind, task, budget, seed):
        K = K2 if kind == 'mcx2' else K1
        return K.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg},
                       budget, seed)['value']

    # ---- references and the invention (first; not resumable mid-way)
    spath = out / 'search.json'
    if spath.exists():
        search = json.loads(spath.read_text())
    else:
        ref = {t.task_id: direct(K2.DEFAULT, 'mcx2', t, SEARCH_BUDGET, 1) for s in 'ABC' for _, t in G[s]}
        counter, trace = [0], []

        def evaluate(cfg, split):
            counter[0] += 1
            seed = int(digest({'study': STUDY, 'eval': counter[0]})[:12], 16)
            v = statistics.mean(direct(cfg, 'mcx2', t, SEARCH_BUDGET, seed + i) / ref[t.task_id]
                                for i, (_, t) in enumerate(G[split]))
            trace.append({'n': counter[0], 'split': split, 'value': v, 'engine': SI.key(cfg)})
            return v
        winner, rep = SI.search(SI.ORIGINAL, SI.engine_ops(), evaluate, MAX_EVALS, int(digest({'study': STUDY})[:12], 16))
        search = {'engine': winner, 'report': rep, 'references': ref}
        spath.write_text(json.dumps(search, indent=1, sort_keys=True) + '\n')
        (out / 'trace.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in trace))
    eng = search['engine']
    log(f"invented engine: {json.dumps(eng, sort_keys=True)}; judge {search['report']['judge']}")

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
            return 'mcx2-v1', eng
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
        held = {}
        for b in BUDGETS:
            held[f'{b:g}'] = {}
            for cls, t in G['D']:
                held[f'{b:g}'][t.task_id] = {e: value(t, cls, e, b, 'D') for e in ENGINES}
            log(f'held-out at {b:g} s done')
        best = GS.best_known()
        gset_rows = []
        for t in GS.tasks():
            cls = R105M.classify(c105['classifier'], R105M.features(t))
            g = t.task_id.split('-')[1]
            vals = {e: value(t, cls, e, 10.0, 'G') for e in ENGINES}
            gset_rows.append({'instance': g, 'class': cls, 'values': vals})
            log(f"{g} [{cls}] best known {best[g]}: " + ', '.join(f'{e} {vals[e]}' for e in ENGINES))
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    res = analyse(held, gset_rows, best)
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
                   failed_runs=fails, engine=eng, engine_is_template=template_of(eng), search=search['report'],
                   held_out_values=held, gset_rows=gset_rows, code_identity=code_identity(ROOT)['sha256'],
                   status='DEV; licenses nothing; no record claim')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; test 1 {res['test1']['label']} ({res['test1']['wins']}-{res['test1']['losses']}); verdict "
        f"{res['verdict']}; Gset at best known: {res['gset_reach_best_known']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
