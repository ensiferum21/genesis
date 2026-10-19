#!/usr/bin/env python3
"""B20_R80: random programs as a control for the system's program search (DEV, preregistered before B20_R79's result)

    taskset -c 0 python3 scripts/b20r80_random_program_control.py OUT_DIR     run ALONE, after B20_R79

**Why.** If B20_R79's search finds a good solver, is that the search's doing, or would drawing random programs from
the same language, for the same CPU time, with the same final choice, do as well? Random search is the standard
control for searches over configurations and programs (Bergstra and Bengio, JMLR 2012). B20_R81 tests both frozen
programs on fresh hosts.

**Design (fixed before B20_R79 has run).**
  * **Training hosts:** exactly B20_R79's 16 (read from `evidence/program_search_b20r79/hosts.json`).
  * **Sampling:** `solver_programs.random_program` with seed 20268001, duplicates skipped, each new program
    evaluated as in the search (`solver_search.evaluate`, 0.25 CPU s per host, round 0), for 6,000 CPU s.
  * **Final choice:** identical to the search's: the 4 best by mean (ties: smaller program, then the canonical
    text), each run at 0.25 and 1.0 s with 2 fresh seeds on every training host; the highest mean is frozen.
  * **Outputs:** `random_program.json` (the program and its `solver-program-v1` descriptor), every evaluation
    (`history.jsonl`), the summary.

**Expectation, stated before running.** The best random program will be weaker than B20_R79's on the training hosts;
in B20_R78's development look three random programs reached 0, 3 and 0 of 24 targets, though thousands of draws can
find good ones. **Status.** DEV; licenses nothing.
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

from genesis import candidates_v2 as C2  # noqa: E402
from genesis.candidate_kinds import solver_program as KP  # noqa: E402
from genesis.common import canonical, code_identity  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.invention import solver_programs as SP  # noqa: E402
from genesis.invention import solver_search as SS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

TF = RD.TF
SEED, SEARCH_S = 20268001, 6000.0
TRAINING = ROOT / 'evidence' / 'program_search_b20r79' / 'hosts.json'


def random_search(hosts, reps, rep_by_id, seconds, seed, log=print, history=None):
    """Draw random programs until the CPU time is spent; the same final choice as `solver_search.search`."""
    rng = random.Random(seed)
    t_end = time.process_time() + seconds
    seen = {}
    while time.process_time() < t_end:
        p = SP.random_program(rng, reps)
        key = json.dumps(p, sort_keys=True)
        if key in seen:
            continue
        e = seen[key] = SS.Entry(p)
        mean, vals = SS.evaluate(p, rep_by_id, hosts, SS.BUDGET, 0)
        e.scores.append(mean)
        if history is not None:
            history.append({'program': p, 'round': 0, 'mean': round(mean, 4), 'values': vals,
                            'cpu_s': round(time.process_time() - (t_end - seconds), 2)})
        if len(seen) % 100 == 0:
            b = min(seen.values(), key=SS.Entry.rank)
            log(f'{len(seen)} programs, best {b.fitness:.2f} (size {b.size}) {b.key}')
    ranked = sorted(seen.values(), key=SS.Entry.rank)
    finals = []
    for e in ranked[:SS.FINALISTS]:
        vals = [SS.evaluate(e.program, rep_by_id, hosts, b, 1000 + s)[0] for b in SS.FINAL_BUDGETS
                for s in range(SS.FINAL_SEEDS)]
        finals.append((statistics.mean(vals), e))
        log(f'finalist {statistics.mean(vals):.2f} (sample fitness {e.fitness:.2f}, size {e.size}) {e.key}')
    best = max(finals, key=lambda x: (x[0], -x[1].size, x[1].key))[1]
    return best.program, {'programs': len(seen),
                          'finalists': [{'program': e.program, 'final_mean': round(m, 4),
                                         'sample_fitness': round(e.fitness, 4), 'size': e.size} for m, e in finals]}


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'random_program.json').exists():
        raise SystemExit('already run; not resumable (one CPU-time-budgeted run)')
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads(TRAINING.read_text())['tasks']]
    log(f'{len(tasks)} training hosts from {TRAINING.relative_to(ROOT)}')
    reps = KP.licensed_reps(TF)
    rep_by_id = {r['id']: r for r in R.proposals()}
    history = []
    c0 = time.process_time()
    program, report = random_search(tasks, reps, rep_by_id, SEARCH_S, SEED, log=log, history=history)
    cpu_used = time.process_time() - c0
    with (out / 'history.jsonl').open('w') as fh:
        for h in history:
            fh.write(json.dumps(h, sort_keys=True) + '\n')
    desc = C2.build_descriptor('solver-program-v1', TF, {'program': program, 'cpu_seconds': 0.5}, **R11.PROFILE)
    summary = {'schema': 'genesis-b20r80-random-program-control-v1', 'program': program,
               'anatomy': SS.anatomy(program), 'size': SP.size(program), 'descriptor_at_0.5s': desc, **report,
               'sample_fitness_mean': round(statistics.mean(h['mean'] for h in history), 4),
               'cpu_s': round(cpu_used, 1), 'seed': SEED, 'training_hosts': str(TRAINING.relative_to(ROOT)),
               'training_host_ids': [t.task_id for t in tasks], 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV control for the program search; tested in B20_R81; licenses nothing'}
    R11.dump(out / 'control_summary.json', summary)
    R11.dump(out / 'random_program.json', {'program': program, 'descriptor_at_0.5s': desc,
                                           'anatomy': summary['anatomy']})
    log(f'frozen random-search program (size {summary["size"]}): {json.dumps(program, sort_keys=True)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
