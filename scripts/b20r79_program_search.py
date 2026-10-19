#!/usr/bin/env python3
"""B20_R79: the system searches for its own solver (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r79_program_search.py OUT_DIR      run ALONE (CPU-time budgets)

**Why.** B20_R77's engine beat CP-SAT and BURER2002, but the builder assembled it (simulated bifurcation, a
portfolio, (1,2)-swaps). Daniel asked that the system find such a solver itself. B20_R78 gave it the parts: a closed
language of low-level steps (relabel a vertex, descent, drop or force an edge, sweeps, acceptance rules, repeat,
loop, split, return to the best) over the system's own licensed representations, and a program search. No
simulated bifurcation, swap move, portfolio or hand-written program is given to the search.

**Design (fixed before running).**
  * **Training hosts.** planted_cluster (p_in 0.8, p_out 0.06), 16 fresh DEV hosts at n63, seed 20267901, drawn by
    `b20r64_e1d_scaling.generate_beyond_space`, excluding every identity `b20r24_repilots.exposure` excludes (all
    earlier studies' hosts, B20_R77's included). The search sees only these.
  * **Search.** `invention.solver_search.search` with its fixed constants (population 16 random programs; 8 children
    per generation by mutation or crossover of tournament winners; the 2 leaders re-evaluated each generation;
    fitness = mean best size over the 16 hosts at 0.25 CPU s, in process, one run per host), seed 20267902, for
    6,000 CPU s; then 4 finalists each run at 0.25 and 1.0 s with 2 fresh seeds on every training host, and the
    highest mean is frozen (ties: smaller program).
  * **Outputs.** The frozen program and its `solver-program-v1` descriptor (`discovered_program.json`); every
    evaluation (`history.jsonl`); the search report; the program's anatomy.
  * **Rediscovery question (descriptive):** does the frozen program use a swap-like step (drop with improve or
    sideways acceptance), a kick (force), a cut search (descent or relabel), restarts, phases (split)?

**Expectation, stated before running.** In a two-minute development look (4 B20_R76 hosts, 0.1 s fitness) the search
found "relabel 100 random vertices with annealing acceptance, then descent", an iterated local search over cuts,
from random programs. The builder expects a program of that kind, better than the system's B20_R76 engine (descent
restarts), and puts the chance that it also uses a swap-like edge step at about one in three.

**What it decides.** Nothing; it produces the program that B20_R80 will test on fresh hosts. **Status.** DEV.
"""
import json
from pathlib import Path
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
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402

TF = RD.TF
SEED, SEARCH_SEED, PER_N, N, SEARCH_S = 20267901, 20267902, 16, 63, 6000.0
P_IN, P_OUT = 0.8, 0.06


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, _ = R64.generate_beyond_space(SEED, PER_N, 'DEV', {'n': N, 'p_in': P_IN, 'p_out': P_OUT}, set(excluded))
    if len(tasks) != PER_N or RD.identities(tasks) & set(excluded):
        raise RuntimeError('host drawing failed or collides with an excluded identity')
    R11.dump(path, {'seed': SEED, 'per_n': PER_N, 'n': N, 'params': {'p_in': P_IN, 'p_out': P_OUT},
                    'role': 'training hosts of the program search; never evaluation hosts',
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'discovered_program.json').exists():
        raise SystemExit('already run; the search is not resumable (it is one CPU-time-budgeted run)')
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    reps = KP.licensed_reps(TF)
    rep_by_id = {r['id']: r for r in R.proposals()}
    log(f'licensed representations {sorted(reps)}')
    excluded, scan, _ = R24.exposure(log)
    tasks = hosts(out, log, excluded)
    history = []
    c0 = time.process_time()
    program, report = SS.search(tasks, reps, rep_by_id, SEARCH_S, SEARCH_SEED, log=log, history=history)
    cpu_used = time.process_time() - c0
    with (out / 'history.jsonl').open('w') as fh:
        for h in history:
            fh.write(json.dumps(h, sort_keys=True) + '\n')
    if SP.problems(program, reps):
        raise RuntimeError('the search returned a program outside the language')
    desc = C2.build_descriptor('solver-program-v1', TF, {'program': program, 'cpu_seconds': 0.5}, **R11.PROFILE)
    first = [h['mean'] for h in history[:SS.POP]]
    summary = {'schema': 'genesis-b20r79-program-search-v1', 'program': program, 'anatomy': SS.anatomy(program),
               'size': SP.size(program), 'descriptor_at_0.5s': desc,
               'search': {k: report[k] for k in ('generations', 'evaluations', 'distinct_programs')},
               'finalists': report['finalists'], 'population': report['population'],
               'initial_population_mean_fitness': round(sum(first) / len(first), 4),
               'initial_population_best_fitness': max(first),
               'cpu_s': round(cpu_used, 1), 'constants': {
                   'POP': SS.POP, 'CHILDREN': SS.CHILDREN, 'LEADERS': SS.LEADERS, 'TOURNAMENT': SS.TOURNAMENT,
                   'P_CROSS': SS.P_CROSS, 'BUDGET': SS.BUDGET, 'FINALISTS': SS.FINALISTS,
                   'FINAL_BUDGETS': list(SS.FINAL_BUDGETS), 'FINAL_SEEDS': SS.FINAL_SEEDS, 'SEARCH_S': SEARCH_S},
               'seeds': {'hosts': SEED, 'search': SEARCH_SEED}, 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV program search; the frozen program is tested on fresh hosts in B20_R80; licenses nothing'}
    R11.dump(out / 'search_summary.json', summary)
    R11.dump(out / 'discovered_program.json', {'program': program, 'descriptor_at_0.5s': desc,
                                               'anatomy': summary['anatomy']})
    log(f'frozen program (size {summary["size"]}): {json.dumps(program, sort_keys=True)}')
    log(f'anatomy {summary["anatomy"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
