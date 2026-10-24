#!/usr/bin/env python3
"""B20_R128: can the system improve its own process of invention? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r128_improve_the_improver.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** Daniel, 24 Oct 2026: "... and the process itself to be improved." B20_R127 tests one level: the system's
inventor writes an engine. Here the system searches over the inventor itself: its population, children per
generation, leaders, tournament, crossover rate and the weight of each kind of mutation (a PROCESS,
`autonomy.selfimprove`), judged by what each process produces.

**Design (fixed before running).**
  * **A process's yield.** One inner search with that process (`selfimprove.search`, the feedback contract version
    2, starting from random engines) with INNER_EVALS = 120 split evaluations, each running the engine on 6 graphs at
    0.5 s (splits A, B, C of a graph set; scores relative to the builder's hybrid REX at 0.5 s); then the engine it
    returns is run on the set's 12 held-out graphs (D) at 0.5 s. The yield is its mean score on D (above 1: better
    than REX, the human design).
  * **Graph sets** (fresh, generated as in B20_R127, Gset's identities excluded; seeds from SEED): one set for the
    meta-search, one more for each repetition of the final test; a set is 2 + 2 + 2 graphs per class for A, B and C and
    4 per class for D (classes random, planar, toroidal).
  * **The meta-search** (on the meta set): generation 0 is ORIGINAL plus 5 random processes; then 2 generations,
    each of 4 children (mutation or crossover, at even odds, of the two best processes so far). Each process is
    evaluated once (its own inner-search seed). EVOLVED is the process with the highest yield.
  * **Final test (8 repetitions, each on a fresh graph set):** in each, ORIGINAL and EVOLVED each run one inner search
    (the same graphs, independent seeds), and their engines' yields are compared. Test (primary): paired Wilcoxon
    signed-rank of the yields over the 8 repetitions (two-sided, alpha 0.05, at least 6 non-zero differences):
    PROCESS_IMPROVED / PROCESS_WORSE / NO_DIFFERENCE. **Verdict:** SELF_IMPROVEMENT_SHOWN if PROCESS_IMPROVED,
    NOT_SHOWN otherwise.
  * **Also reported:** each process's yields; how many of each process's engines beat REX on held-out graphs (yield
    above 1), and their mean; the meta-search's trajectory (best yield by generation).
  * **Validity:** every engine valid (`mcx2.check_config`); every run returned a checked cut.

**Development looks (disclosed).** B20_R126's tests (a toy evaluation, no engine run); one look at REX, BLS and MCX
at 1 s on six graphs (B20_R127's disclosure). No inner search was run before this study.

**Expectation, stated before running.** The meta-search finds a process with a higher yield on its own graph set
(selection on noise alone would do that), and on fresh sets NO_DIFFERENCE: one inner search's yield is noisy and 8
repetitions are few. The engines of both processes beat REX on held-out graphs at 0.5 s in most repetitions (REX is
untuned), by about 0.1-0.5%. NOT_SHOWN.
**Cost.** About 6.5 min per inner search plus scoring: meta-search 14 searches, final test 16: about 3.3 h, in two or
three slices. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r128'
SEED = 20361281
PER_CLASS = {'A': 2, 'B': 2, 'C': 2, 'D': 4}
BUDGET, INNER_EVALS = 0.5, 120
GEN0_RANDOM, GENERATIONS, CHILDREN = 5, 2, 4
REPETITIONS = 8
ALPHA = 0.05
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def graph_set(index, excluded):
    """(split -> [(class, task)], seen) for graph set `index` (0: the meta-search's; 1..: the repetitions')."""
    import b20r127_self_invented_engine as R127
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out, k = set(excluded), {}, 0
    for split, per in PER_CLASS.items():
        out[split] = []
        for cls, st in R127.settings().items():
            for i in range(per):
                fam, params = st[(i + k) % len(st)]
                ts, seen, _ = A.generate(SEED + 10000 * index + 100 * k + i, 1, 'DEV', fam, params, excluded=seen)
                out[split].append((cls, ts[0]))
            k += 1
    return out, seen


def wilcoxon(a, b):
    from scipy.stats import wilcoxon as W
    diffs = [x - y for x, y in zip(a, b)]
    d = [x for x in diffs if x != 0]
    md = statistics.mean(diffs) if diffs else 0.0
    if len(d) < 6:
        return {'label': 'NO_DIFFERENCE', 'p': 1.0, 'nonzero': len(d), 'mean_difference': md}
    p = float(W(d, zero_method='wilcox', alternative='two-sided').pvalue)
    return {'label': 'NO_DIFFERENCE' if p >= ALPHA else ('PROCESS_IMPROVED' if md > 0 else 'PROCESS_WORSE'),
            'p': p, 'nonzero': len(d), 'mean_difference': md}


def analyse(meta, final):
    """meta: [{'gen', 'process', 'yield'}]; final: [{'rep', 'ORIGINAL': yield, 'EVOLVED': yield}]."""
    evolved = max(meta, key=lambda r: (r['yield'], -r['index']))
    test = wilcoxon([r['EVOLVED'] for r in final], [r['ORIGINAL'] for r in final])
    traj = {}
    for r in meta:
        traj[r['gen']] = max(traj.get(r['gen'], float('-inf')), r['yield'])
    return {'evolved': evolved, 'test': test,
            'verdict': 'SELF_IMPROVEMENT_SHOWN' if test['label'] == 'PROCESS_IMPROVED' else 'NOT_SHOWN',
            'beats_rex': {p: sum(r[p] > 1 for r in final) for p in ('ORIGINAL', 'EVOLVED')},
            'mean_yield': {p: statistics.mean(r[p] for r in final) for p in ('ORIGINAL', 'EVOLVED')},
            'meta_best_by_generation': {str(g): traj[g] for g in sorted(traj)}}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'improve_the_improver_b20r128').resolve():
        raise SystemExit('the registered output is evidence/improve_the_improver_b20r128')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis import gset as GS
    from genesis.autonomy import selfimprove as SI
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
    log(f'{STUDY}; pinned to CPU {cpu}')
    A = adapter('maxcut_v1')
    seen = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    sets = {}
    for i in range(REPETITIONS + 1):
        sets[i], seen = graph_set(i, seen)

    def run(cfg, task, seed):
        r = K2.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': BUDGET, 'config': cfg},
                     BUDGET, seed)
        return r['value']
    rpath = out / 'references.json'
    refs = json.loads(rpath.read_text()) if rpath.exists() else {}

    def ref(task):
        """REX at the budget, one fixed seed, computed once per graph and kept (so a resumed run uses the same)."""
        if task.task_id not in refs:
            refs[task.task_id] = run(K2.DEFAULT, task, 1)
            rpath.write_text(json.dumps(refs, indent=1, sort_keys=True) + '\n')
        return refs[task.task_id]

    path = out / 'yields.jsonl'
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[r['key']] = r

    def yield_of(process, set_index, tag):
        key = f'{tag}|{set_index}|{SI.key(process)}'
        if key in done:
            return done[key]
        if time.monotonic() - t0 > SLICE_S:
            raise Paused
        G = sets[set_index]
        counter = [0]
        base = int(digest({'study': STUDY, 'key': key})[:12], 16)

        def evaluate(cfg, split):
            counter[0] += 1
            return statistics.mean(run(cfg, t, base + 1000 * counter[0] + i) / ref(t) for i, (_, t) in enumerate(G[split]))
        eng, rep = SI.search(process, SI.engine_ops(process['weights']), evaluate, INNER_EVALS, base)
        if K2.check_config(eng) is not None:
            raise RuntimeError('an invalid engine')
        y = statistics.mean(run(eng, t, base + 7 + i) / ref(t) for i, (_, t) in enumerate(G['D']))
        row = {'key': key, 'tag': tag, 'set': set_index, 'process': process, 'engine': eng, 'yield': y,
               'judge': rep['judge'], 'evaluations': rep['evaluations']}
        done[key] = row
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f"{tag} set {set_index}: yield {y:.5f}; engine {eng['prog']!r} levels {eng['levels']}; "
            f"releases {rep['judge']['releases']}")
        return row
    try:
        rng = random.Random(SEED)
        meta = []
        gen0 = [SI.ORIGINAL] + [SI.random_process(rng) for _ in range(GEN0_RANDOM)]
        for p in gen0:
            meta.append({'gen': 0, 'index': len(meta), 'process': p, 'yield': yield_of(p, 0, f'meta{len(meta)}')['yield']})
        for g in range(1, GENERATIONS + 1):
            top = sorted(meta, key=lambda r: (-r['yield'], r['index']))[:2]
            for _ in range(CHILDREN):
                p = (SI.mutate_process(top[0]['process'], rng) if rng.random() < 0.5
                     else SI.crossover_process(top[0]['process'], top[1]['process'], rng))
                meta.append({'gen': g, 'index': len(meta), 'process': p,
                             'yield': yield_of(p, 0, f'meta{len(meta)}')['yield']})
        evolved = max(meta, key=lambda r: (r['yield'], -r['index']))['process']
        log(f'EVOLVED: {json.dumps(evolved, sort_keys=True)}')
        final = []
        for rep_i in range(1, REPETITIONS + 1):
            final.append({'rep': rep_i, 'ORIGINAL': yield_of(SI.ORIGINAL, rep_i, 'final-ORIGINAL')['yield'],
                          'EVOLVED': yield_of(evolved, rep_i, 'final-EVOLVED')['yield']})
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(done)} searches')
        return PAUSED
    res = analyse(meta, final)
    summary = dict(res, study=STUDY, schema='genesis-b20r128-improve-the-improver-v1', valid=True, meta=meta,
                   final=final, code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"test {res['test']['label']} (p {res['test']['p']:.3g}); verdict {res['verdict']}; mean yields "
        f"{res['mean_yield']}; engines beating REX {res['beats_rex']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
