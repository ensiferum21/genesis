#!/usr/bin/env python3
"""B20_R115: does a richer language let the system invent? A search in language v2, held to the invention test
(DEV, preregistered)

    taskset -c 0 python3 scripts/b20r115_language_v2.py OUT_DIR     run ALONE (resumable after the search), then analyse

**Why.** B20_R111 and B20_R112: nothing the system found in B20_R78's language beats annealing-then-descent written
in the same language, and the differences between its programs are about 0.1%. B20_R99 says the best states differ
globally. On max-cut, population moves on whole groups of variables were part of what leads Gset. Language v2
(`invention.solver_programs_v2`) adds three such primitives for the triangle-free problem: an elite pool, keeping
what the elites agree on, and Houdayer's cluster exchange on edge sets. This study lets the system search in it, then
holds the result to the invention test. Two prior-art templates that use the new primitives in the textbook way
(memetic algorithms with consensus or cluster recombination) are added to the library, so the new primitives alone
cannot pass the novelty rule.

**Design (fixed before running).**
  * **Hosts:** 36 fresh DEV hosts of `triangle_free_large_v1`, 9 per cell in B20_R111's four cells (seeds from
    HOST_SEED; every recorded large-domain identity excluded). Per cell: 1 for the search (A), 2 for tuning, 6 held
    out (24 in all).
  * **The search (open protocol; the held-out test is the judge):** `feedback.steady_state_search` over language v2
    (random programs, mutation and crossover of `solver_programs_v2`, the licensed representations), MAX_EVALS = 800.
    An evaluation is the mean over the 4 search hosts of the edge-set size after 0.5 CPU s divided by tfxw's value at
    2 s on that host (computed once). The candidate is the search's final choice (B20_R79's rule: the best of 4
    finalists by 4 fresh evaluations).
  * **Prior art (written before any run):** B20_R111's eight templates (68 variants) and two more (16 variants):
      - T9, a memetic algorithm with consensus recombination: init, descent, sweep, offer to the pool, `agree`,
        sweep;
      - T10, the same with `cluster` recombination.
    Each has a variant for every licensed representation and the sweeps' acceptance (sideways or improve). Tuning as
    in B20_R111: every variant on the 8 tuning hosts at 2 s; each template keeps its best variant; the champion is
    the tuned template with the lowest mean gap.
  * **Held out:** the 10 tuned templates, the candidate, and as references the builder's tfxw and hybrid-swap-v1, on
    the 24 held-out hosts at 2 s (in-process programs; one seed per host and arm).
  * **Test 1:** sign test of the candidate against the champion over the 24 hosts (ties dropped, two-sided, alpha
    0.05): BEATS_PRIOR_ART / BEHIND_PRIOR_ART / NOT_DISTINGUISHABLE.
  * **Test 2 (only if it beats prior art):** B20_R111's deletion search on the tuning hosts (DELTA = 0.1 edges), then
    the core's signature (pool statements as steps) against the ten templates': KNOWN_CORE if it equals one or uses
    only the statement kinds one template has, NOVEL_CORE otherwise. A NOVEL_CORE goes to a literature review before
    anything is claimed.
  * **Verdict:** INVENTION_DEMONSTRATED / BETTER_BUT_KNOWN / NOT_DEMONSTRATED. Also reported: whether the candidate
    uses the pool primitives, T9's and T10's standing against T4, the search's claimed gain and the candidate's
    held-out standing, and the distance to the builder's tfxw.
  * **Validity:** median CPU at least 0.9 of the budget per arm; no invalid edge set.

**Development looks (disclosed).** One 0.5 s run of T9, T10 and T4 on one development host (seed 777222): 1136, 1137
and 1149 edges. Language v2's random generation, mutation and crossover were checked for validity on 200 programs.

**Expectation, stated before running.** NOT_DEMONSTRATED. T4 remains the champion; T9 and T10 trail it at 2 s. The
search finds a program that uses a pool primitive, NOT_DISTINGUISHABLE from T4. The new primitives may need longer
budgets or a different problem to matter.
**Cost.** References 4 x 2 s; search 800 x 4 x 0.5 s, about 27 min; tuning 84 x 8 x 2 s, about 22 min; held out 13 x
24 x 2 s, about 10 min: about 60 min, more if a deletion search runs. **Status.** DEV; licenses nothing.
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
import b20r111_invention_test as M111  # noqa: E402

STUDY = 'b20r115'
HOST_SEED = 20301151
PER_CELL = 9                      # 1 search host, 2 tuning hosts, 6 held out, per cell
EVAL_BUDGET, BUDGET = 0.5, 2.0
MAX_EVALS = 800
ALPHA = 0.05
SLICE_S, PAUSED = 6600, 3


def _memetic(name, recombine):
    return [(f'{name}|{rep}|{acc}', {'rep': rep, 'body': [['init'], ['descent'], ['sweep', 'drop', acc], ['elite'],
                                                          [recombine], ['sweep', 'drop', acc]]})
            for rep in M111.REPS for acc in ('sideways', 'improve')]


LIBRARY = dict(M111.LIBRARY, T9=_memetic('T9', 'agree'), T10=_memetic('T10', 'cluster'))


def signature(program):
    """B20_R111's signature, with the pool statements as steps."""
    def block(b):
        out = []
        for s in b:
            op = s[0]
            if op in ('init', 'descent', 'best', 'elite', 'agree', 'cluster'):
                out.append((op,))
            elif op in ('relabel', 'edges', 'sweep'):
                out.append((op, s[1], s[2]))
            elif op == 'repeat':
                out.append((op, block(s[2])))
            elif op == 'loop':
                out.append((op, block(s[1])))
            elif op == 'split':
                out.append((op, block(s[2]), block(s[3])))
            else:
                raise ValueError(f'unknown statement {op!r}')
        return tuple(out)
    return block(program['body'])


TEMPLATE_SIGNATURES = {t: signature(vs[0][1]) for t, vs in LIBRARY.items()}


def core_label(sig):
    known = [t for t, s in TEMPLATE_SIGNATURES.items() if s == sig or M111.kinds(sig) <= M111.kinds(s)]
    return ('KNOWN_CORE' if known else 'NOVEL_CORE'), known


def tune(values, hosts):
    best_on = {h: max(values[a][h] for a in values) for h in hosts}
    score = {a: statistics.mean((best_on[h] - values[a][h]) / best_on[h] for h in hosts) for a in values}
    tuned = {t: min([n for n, _ in vs], key=lambda n: (score[n], [m for m, _ in vs].index(n))) for t, vs in LIBRARY.items()}
    champion = min(LIBRARY, key=lambda t: (score[tuned[t]], list(LIBRARY).index(t)))
    return tuned, champion, score


def uses_pool(program):
    return any(s[0] in ('elite', 'agree', 'cluster') for s in _flat(program['body']))


def _flat(block):
    for s in block:
        yield s
        if s[0] == 'repeat':
            yield from _flat(s[2])
        elif s[0] == 'loop':
            yield from _flat(s[1])
        elif s[0] == 'split':
            yield from _flat(s[2])
            yield from _flat(s[3])


class Paused(Exception):
    pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'language_v2_b20r115').resolve():
        raise SystemExit('the registered output is evidence/language_v2_b20r115')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r99_headroom as R99
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    from genesis.autonomy import feedback as FB
    from genesis.autonomy import qet
    from genesis.candidate_kinds import solver_program as KP
    from genesis.invention import representations as R
    from genesis.invention import solver_programs_v2 as V2
    licensed = KP.licensed_reps('triangle_free_host_v1')
    for vs in LIBRARY.values():
        for name, prog in vs:
            if V2.problems(prog, licensed):
                raise SystemExit(f'{name} is not in language v2')
    tasks = qet.hosts({'study': STUDY, 'cells': [list(c) for c in M111.CELLS], 'per_cell': PER_CELL,
                       'host_seed': HOST_SEED}, out, ROOT, log)
    nc = len(M111.CELLS)
    search_hosts, tune_hosts, held = tasks[:nc], tasks[nc:3 * nc], tasks[3 * nc:]
    reps = {r['id']: r for r in R.proposals()}
    tfx = R99.tfxw_descriptors()

    def run(prog, task, budget, seed):
        E = [tuple(e) for e in task.edges]
        c0 = time.process_time()
        S = {R99.key(*e) for e in V2.run(prog, reps[prog['rep']], task.n, E, budget, seed)}
        cpu_s = time.process_time() - c0
        if not S <= {R99.key(*e) for e in E} or not R99.is_triangle_free(S, task.n):
            raise RuntimeError(f'invalid edge set on {task.task_id}')
        return len(S), cpu_s

    # ---- the search (first; not resumable mid-way, about 27 min)
    spath = out / 'search.json'
    if spath.exists():
        search = json.loads(spath.read_text())
    else:
        refs = {t.task_id: len(R99.state(t, 'tfxw', 2.0, None, tfx)[0]) for t in search_hosts}
        counter, trace = [0], []

        def evaluate(prog, split):
            counter[0] += 1
            seed = int(digest({'study': STUDY, 'eval': counter[0]})[:12], 16)
            v = statistics.mean(run(prog, t, EVAL_BUDGET, seed + i)[0] / refs[t.task_id]
                                for i, t in enumerate(search_hosts))
            trace.append({'n': counter[0], 'value': v, 'program': digest(prog)})
            return v
        ops = {'random': lambda rng: V2.random_program(rng, licensed), 'mutate': lambda p, rng: V2.mutate(p, rng, licensed),
               'crossover': lambda a, b, rng: V2.crossover(a, b, rng, licensed), 'size': V2.size}
        winner, rep = FB.steady_state_search(ops, evaluate, MAX_EVALS, int(digest({'study': STUDY})[:12], 16))
        first = trace[0]['value'] if trace else None
        search = {'program': winner, 'reported': float(rep['reported']), 'first_score': first,
                  'generations': rep['generations'], 'evaluations': rep['evaluations'],
                  'distinct_programs': rep['distinct_programs'], 'references': refs}
        spath.write_text(json.dumps(search, indent=1, sort_keys=True) + '\n')
        (out / 'trace.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in trace))
    cand = search['program']
    log(f"search: {search['evaluations']} evaluations, reported {search['reported']:.4f}; program {json.dumps(cand)}")

    # ---- tuning and the held-out test (resumable)
    path = out / 'runs.jsonl'
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r['key']] = r

    def value(task, arm, prog):
        key = f'{task.task_id}|{arm}'
        if key not in cache:
            if time.monotonic() - t0 > SLICE_S:
                raise Paused
            seed = int(digest({'study': STUDY, 'task': task.task_id, 'arm': arm})[:12], 16)
            if arm in ('tfxw', 'hybrid'):
                sel, cpu_s, how = R99.state(task, arm, BUDGET, None, tfx)
                S = {R99.key(*e) for e in sel}
                if not R99.is_triangle_free(S, task.n):
                    raise RuntimeError(f'{arm}: invalid edge set')
                v = len(S)
            else:
                v, cpu_s = run(prog, task, BUDGET, seed)
            cache[key] = {'key': key, 'task': task.task_id, 'arm': arm, 'value': v, 'cpu_s': round(cpu_s, 3)}
            with path.open('a') as f:
                f.write(json.dumps(cache[key], sort_keys=True) + '\n')
        return cache[key]['value']

    variants = {n: p for vs in LIBRARY.values() for n, p in vs}
    try:
        values = {n: {t.task_id: value(t, n, p) for t in tune_hosts} for n, p in variants.items()}
        tuned, champion, score = tune(values, [t.task_id for t in tune_hosts])
        log(f'tuned: {tuned}; champion {champion}')
        hv = {t: {h.task_id: value(h, tuned[t], variants[tuned[t]]) for h in held} for t in LIBRARY}
        hv['candidate'] = {h.task_id: value(h, 'candidate', cand) for h in held}
        for ref in ('tfxw', 'hybrid'):
            hv[ref] = {h.task_id: value(h, ref, None) for h in held}
        hs = [h.task_id for h in held]
        test = M111.sign([hv['candidate'][h] for h in hs], [hv[champion][h] for h in hs], ALPHA)
        log(f"test 1: {test['label']} {test['wins']}-{test['losses']}")
        core = None
        if test['label'] == 'BEATS_PRIOR_ART':
            prog = cand
            full = statistics.mean(value(t, 'candidate', cand) for t in tune_hosts)
            while True:
                trials = []
                for k, p in enumerate(M111.deletions(prog)):
                    if V2.problems(p, licensed):
                        continue
                    trials.append((statistics.mean(value(t, f'core-{digest(p)[:12]}', p) for t in tune_hosts), k, p))
                ok = [x for x in trials if x[0] >= full - M111.DELTA]
                if not ok:
                    break
                _, _, prog = max(ok, key=lambda x: (x[0], -x[1]))
            label, known = core_label(signature(prog))
            core = {'core': prog, 'label': label, 'known_as': known}
            log(f'core: {label} {known}')
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    verdict = M111.verdict({'candidate': test}, {'candidate': core} if core else {})
    t9 = M111.sign([hv['T9'][h] for h in hs], [hv['T4'][h] for h in hs], ALPHA)
    t10 = M111.sign([hv['T10'][h] for h in hs], [hv['T4'][h] for h in hs], ALPHA)
    cpu_by = {}
    for r in cache.values():
        cpu_by.setdefault(r['arm'].split('|')[0].split('-')[0], []).append(r['cpu_s'] / BUDGET)
    med = {a: statistics.median(v) for a, v in sorted(cpu_by.items())}
    valid = all(m >= 0.9 for m in med.values())
    means = {a: statistics.mean(v.values()) for a, v in hv.items()}
    summary = {'study': STUDY, 'schema': 'genesis-b20r115-language-v2-v1', 'verdict': verdict, 'test1': test,
               'core': core, 'candidate': cand, 'candidate_signature': repr(signature(cand)),
               'candidate_known_as': core_label(signature(cand))[1], 'candidate_uses_pool': uses_pool(cand),
               'search': search, 'tuned': tuned, 'champion': champion, 'tuning_scores': score,
               't9_vs_t4': t9, 't10_vs_t4': t10, 'held_out': hv, 'held_out_means': means, 'valid': valid,
               'cpu_median_by_arm': med, 'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'valid {valid}; verdict {verdict}; candidate uses pool: {uses_pool(cand)}; held-out means ' +
        ', '.join(f'{a} {m:.1f}' for a, m in sorted(means.items(), key=lambda x: -x[1])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
