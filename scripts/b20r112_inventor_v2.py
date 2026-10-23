#!/usr/bin/env python3
"""B20_R112: can the improved inventor pass the invention test? A fresh search under contract v2 (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r112_inventor_v2.py OUT_DIR     run ALONE after B20_R111 (resumable), then analyse

**Why.** B20_R111 judges the programs the system already found. Those searches ran without a feedback contract, on
small hosts. They could not tell progress from noise (B20_R103: their reported gains are inflated by up to 6.6
sigma_e). The improving process has since been improved: contract v2 (B20_R107) keeps the judge honest and keeps its
power. This study lets the system search again, with the contract, on the large hosts where B20_R111 judges. It
holds the result to the same invention test, so it asks whether improving the improver changes the answer.

**Design (fixed before B20_R111 finished).**
  * **Search hosts:** 12 fresh DEV hosts of `triangle_free_large_v1`, 3 in each of B20_R111's cells (seeds from
    HOST_SEED; every recorded large-domain identity excluded, B20_R111's included). Split by cell into A (the worker's
    training data), B and C (the judge's two confirmation splits), 4 hosts each.
  * **Values:** a program's value on a host is its edge set's size after 0.5 CPU s (in-process interpreter, a fresh
    seed per evaluation), divided by the host's reference: `tfxw` at 2 s in B20_R95's configuration, computed once.
    An evaluation of a split is the mean over its 4 hosts.
  * **The search:** `feedback.steady_state_search` (`invention.solver_search`'s algorithm) over the real solver
    language (B20_R103's operators: random programs, mutation, crossover over the licensed representations).
    `contract=True, calibrate='BC'`; MAX_EVALS = 400 split evaluations, each split counting 1. The reported program is
    the judge's incumbent: the start program if nothing was released.
  * **The invention test, as B20_R111:** the reported program runs at 2 s on B20_R111's 24 held-out hosts (fresh
    seeds, in-process). Sign test against B20_R111's recorded prior-art champion values on the same hosts (ties
    dropped, two-sided, alpha 0.05): BEATS_PRIOR_ART / BEHIND_PRIOR_ART / NOT_DISTINGUISHABLE. If it beats prior art,
    its core is found by B20_R111's deletion search on B20_R111's tuning hosts and labelled with B20_R111's rule.
  * **Verdict:** INVENTION_DEMONSTRATED (BEATS_PRIOR_ART with a NOVEL_CORE), BETTER_BUT_KNOWN, or NOT_DEMONSTRATED.
    Also reported: releases, evaluations used, whether the search stopped, the program and its signature. The study
    refuses to start unless B20_R111 finished validly.

**Development looks (disclosed).** None: the search was never run on the large domain before this design was fixed.

**Expectation, stated before running.** NOT_DEMONSTRATED. The contract releases one to three improvements and stops
early. The program found is an annealing or plateau-search variant within B20_R111's library, NOT_DISTINGUISHABLE from
or BEHIND the prior-art champion. The language, not the search, is the limit (B20_R99: no recognizable local
structure where the strongest search stops).
**Cost.** References 12 x 2 s; search up to 400 x 4 x 0.5 s plus judging, about 20-30 min; the test 24 x 2 s.
**Status.** DEV; licenses nothing.
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

STUDY = 'b20r112'
HOST_SEED = 20291201
EVAL_BUDGET, TEST_BUDGET = 0.5, 2.0
MAX_EVALS = 400
ALPHA = 0.05
R111 = ROOT / 'evidence' / 'invention_test_b20r111'


def splits(tasks, n_cells):
    """Hosts in qet's order (cell-interleaved): the first of each cell to A, the second to B, the third to C."""
    return {'A': tasks[:n_cells], 'B': tasks[n_cells:2 * n_cells], 'C': tasks[2 * n_cells:3 * n_cells]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'inventor_v2_b20r112').resolve():
        raise SystemExit('the registered output is evidence/inventor_v2_b20r112')
    s111 = R111 / 'summary.json'
    if not s111.exists() or not json.loads(s111.read_text())['valid']:
        raise SystemExit('B20_R111 must have finished validly')
    r111 = json.loads(s111.read_text())
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r99_headroom as R99
    import b20r103_zero_signal as R103
    import b20r111_invention_test as M111
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
    from genesis.invention import representations as R
    from genesis.invention import solver_library as SL
    from genesis.invention import solver_programs as SP
    from genesis.models_large import LargeGraphTask
    from genesis.common import canonical
    from genesis.candidate_kinds import solver_program as KP
    licensed = KP.licensed_reps('triangle_free_host_v1')
    tasks = qet.hosts({'study': STUDY, 'cells': [list(c) for c in M111.CELLS], 'per_cell': 3, 'host_seed': HOST_SEED},
                      out, ROOT, log)
    sp = splits(tasks, len(M111.CELLS))
    reps = {r['id']: r for r in R.proposals()}
    tfx = R99.tfxw_descriptors()
    ref_path = out / 'references.json'
    refs = json.loads(ref_path.read_text()) if ref_path.exists() else {}
    for t in tasks:
        if t.task_id not in refs:
            sel, _, _ = R99.state(t, 'tfxw', 2.0, None, tfx)
            refs[t.task_id] = len(sel)
            ref_path.write_text(json.dumps(refs, indent=1, sort_keys=True) + '\n')
    log(f'references (tfxw at 2 s): {refs}')
    trace = []
    counter = [0]

    def run(prog, task, budget, seed):
        E = [tuple(e) for e in task.edges]
        f = SL.run if 'library' in prog else SP.run
        S = {R99.key(*e) for e in f(prog, reps[prog['rep']], task.n, E, budget, seed)}
        if not S <= {R99.key(*e) for e in E} or not R99.is_triangle_free(S, task.n):
            raise RuntimeError(f'invalid edge set on {task.task_id}')
        return len(S)

    def evaluate(prog, split):
        counter[0] += 1
        seed = int(digest({'study': STUDY, 'eval': counter[0]})[:12], 16)
        v = statistics.mean(run(prog, t, EVAL_BUDGET, seed + i) / refs[t.task_id] for i, t in enumerate(sp[split]))
        trace.append({'n': counter[0], 'split': split, 'value': v, 'program': digest(prog)})
        return v
    winner, rep = FB.steady_state_search(R103.language_ops(), evaluate, MAX_EVALS,
                                         int(digest({'study': STUDY})[:12], 16), contract=True, calibrate='BC')
    (out / 'trace.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in trace))
    log(f"search: releases {rep['judge']['releases']}, submissions {rep['judge']['submissions']}, evaluations "
        f"{rep['evaluations']}, stopped {rep['judge']['stopped']}; program {json.dumps(winner)}")
    held = [LargeGraphTask.model_validate_json(canonical(t))
            for t in json.loads((R111 / 'hosts.json').read_text())['tasks']][M111.TUNE_PER_CELL * len(M111.CELLS):]
    champ = r111['champion']
    mine, theirs = [], []
    for t in held:
        seed = int(digest({'study': STUDY, 'test': t.task_id})[:12], 16)
        mine.append(run(winner, t, TEST_BUDGET, seed))
        theirs.append(r111['held_out'][champ][t.task_id])
    test = M111.sign(mine, theirs, ALPHA)
    core = None
    if test['label'] == 'BEATS_PRIOR_ART':
        tune_hosts = [LargeGraphTask.model_validate_json(canonical(t))
                      for t in json.loads((R111 / 'hosts.json').read_text())['tasks']][:M111.TUNE_PER_CELL * len(M111.CELLS)]
        prog = winner
        full = statistics.mean(run(prog, t, TEST_BUDGET, 1) for t in tune_hosts)
        while True:
            trials = []
            for k, p in enumerate(M111.deletions(prog)):
                if (SL.problems(p, licensed) if 'library' in p else SP.problems(p, licensed)):
                    continue
                trials.append((statistics.mean(run(p, t, TEST_BUDGET, 1) for t in tune_hosts), k, p))
            ok = [x for x in trials if x[0] >= full - M111.DELTA]
            if not ok:
                break
            _, _, prog = max(ok, key=lambda x: (x[0], -x[1]))
        label, known = M111.core_label(M111.signature(prog))
        core = {'core': prog, 'label': label, 'known_as': known}
    verdict = M111.verdict({'inventor_v2': test}, {'inventor_v2': core} if core else {})
    summary = {'study': STUDY, 'schema': 'genesis-b20r112-inventor-v2-v1', 'verdict': verdict, 'test': test,
               'core': core, 'program': winner, 'signature': repr(M111.signature(winner)),
               'known_as_template': M111.core_label(M111.signature(winner))[1],
               'search': {k: (v if k != 'judge' else {kk: float(vv) if kk in ('tau', 'start') else vv for kk, vv in v.items()})
                          for k, v in rep.items() if k in ('generations', 'evaluations', 'distinct_programs', 'judge')},
               'reported': float(rep['reported']), 'held_out_values': dict(zip([t.task_id for t in held], mine)),
               'champion': champ, 'references': refs, 'code_identity': code_identity(ROOT)['sha256'],
               'valid': True, 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"verdict {verdict}; test {test['label']} {test['wins']}-{test['losses']}; held-out mean "
        f"{statistics.mean(mine):.1f} vs champion {statistics.mean(theirs):.1f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
