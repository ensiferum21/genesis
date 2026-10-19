#!/usr/bin/env python3
"""B20_R83, B20_R84, B20_R85: generations of the system's program search, each able to call the previous
generations' discoveries (GV5, DEV, preregistered before B20_R79 has finished)

    taskset -c 0 python3 scripts/b20r83_generation_search.py b20r83 OUT_DIR    generation 2 (library: generation 1)
    taskset -c 0 python3 scripts/b20r83_generation_search.py b20r84 OUT_DIR    its control (no library, same hosts)
    taskset -c 0 python3 scripts/b20r83_generation_search.py b20r85 OUT_DIR    generation 3 (library: 1 and 2)
    each ALONE and pinned, in this order (each needs the previous one's frozen program)

**Why.** GV5 asks for gains across generations: three executable generations, each judged against the one before on
fresh panels, with causal evidence. Generation 1 is B20_R79's search from random programs. A later generation
searches the same language plus a library: the bodies of the earlier generations' frozen programs, callable as
`["macro", I]` (B20_R82, library learning). The control repeats generation 2's search with the same budget on the
same training hosts and no library, so that a difference between them is the library's. B20_R86 judges all of them.

**Design (fixed before running).** Each study: 16 fresh DEV planted-cluster hosts (p_in 0.8, p_out 0.06) at n63
drawn excluding every identity `b20r24_repilots.exposure` excludes (all earlier studies' hosts, B20_R79's training
hosts included), except B20_R84, which uses B20_R83's hosts; `invention.library_search.search` with B20_R78's
constants (population 16 from random programs, 8 children per generation, 2 leaders re-evaluated, fitness at
0.25 CPU s, 4 finalists at 0.25 and 1.0 s with 2 seeds) for 6,000 CPU s:

| study | role | hosts (seed) | library | search seed |
|---|---|---|---|---|
| b20r83 | generation 2 | 20268301 | [generation 1] | 20268302 |
| b20r84 | control for generation 2 | B20_R83's | [] | 20268402 |
| b20r85 | generation 3 | 20268501 | [generation 1, generation 2] | 20268502 |

Generation 1's entry is B20_R79's frozen body; generation 2's is B20_R83's (which may call entry 0). Outputs: the
frozen program with its library and its `solver-library-v1` descriptor (`program.json`), every evaluation
(`history.jsonl`), the summary.

**Expectation, stated before B20_R79 has finished.** Generation 2 will use the macro and do at least as well as
generation 1 on its training hosts; the control will do about as well as generation 1 (it is generation 1's search
again); generation 3 will add little. **Status.** DEV; licenses nothing.
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
from genesis.invention import library_search as LS  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.invention import solver_library as SL  # noqa: E402
from genesis.invention import solver_search as SS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402

TF = RD.TF
N, PER_N, SEARCH_S, P_IN, P_OUT = 63, 16, 6000.0, 0.8, 0.06
EV = ROOT / 'evidence'
GEN1 = EV / 'program_search_b20r79' / 'discovered_program.json'
GEN2 = EV / 'generation2_b20r83' / 'program.json'
STUDIES = {
    'b20r83': {'role': 'generation 2', 'host_seed': 20268301, 'hosts_from': None, 'library': (GEN1,),
               'search_seed': 20268302, 'out': EV / 'generation2_b20r83'},
    'b20r84': {'role': 'control for generation 2 (no library)', 'host_seed': None,
               'hosts_from': EV / 'generation2_b20r83' / 'hosts.json', 'library': (), 'search_seed': 20268402,
               'out': EV / 'generation2_control_b20r84'},
    'b20r85': {'role': 'generation 3', 'host_seed': 20268501, 'hosts_from': None, 'library': (GEN1, GEN2),
               'search_seed': 20268502, 'out': EV / 'generation3_b20r85'},
}


def library_for(study):
    lib = []
    for path in STUDIES[study]['library']:
        if not path.exists():
            raise SystemExit(f'{path.relative_to(ROOT)} is missing: run the earlier generation first')
        lib.append(SL.as_library_entry(json.loads(path.read_text())['program']))
    return lib


def hosts(study, out, log, excluded):
    cfg = STUDIES[study]
    path = out / 'hosts.json'
    if cfg['hosts_from'] is not None:
        if not cfg['hosts_from'].exists():
            raise SystemExit(f'{cfg["hosts_from"].relative_to(ROOT)} is missing: run B20_R83 first')
        data = json.loads(cfg['hosts_from'].read_text())
        R11.dump(path, dict(data, role=f'{cfg["role"]}: the hosts of {cfg["hosts_from"].relative_to(ROOT)}'))
        return [GraphTask.model_validate_json(canonical(t)) for t in data['tasks']]
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, _ = R64.generate_beyond_space(cfg['host_seed'], PER_N, 'DEV', {'n': N, 'p_in': P_IN, 'p_out': P_OUT},
                                         set(excluded))
    if len(tasks) != PER_N or RD.identities(tasks) & set(excluded):
        raise RuntimeError('host drawing failed or collides with an excluded identity')
    R11.dump(path, {'seed': cfg['host_seed'], 'per_n': PER_N, 'n': N, 'params': {'p_in': P_IN, 'p_out': P_OUT},
                    'role': f'{cfg["role"]}: training hosts of the program search; never evaluation hosts',
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def main(argv=None):
    argv = argv or sys.argv[1:]
    study, out = argv[0], Path(argv[1])
    if study not in STUDIES:
        raise SystemExit(f'study must be one of {sorted(STUDIES)}')
    cfg = STUDIES[study]
    if out.resolve() != cfg['out'].resolve():
        raise SystemExit(f'{study} writes to {cfg["out"].relative_to(ROOT)} (later studies read it there)')
    library = library_for(study)
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'program.json').exists():
        raise SystemExit('already run; not resumable (one CPU-time-budgeted run)')
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{study} ({cfg["role"]}); pinned to CPU {cpu}; library of {len(library)}: {json.dumps(library)}')
    reps = KP.licensed_reps(TF)
    rep_by_id = {r['id']: r for r in R.proposals()}
    excluded, scan, _ = R24.exposure(log)
    tasks = hosts(study, out, log, excluded)
    history = []
    c0 = time.process_time()
    program, report = LS.search(tasks, reps, rep_by_id, library, SEARCH_S, cfg['search_seed'], log=log,
                                history=history)
    cpu_used = time.process_time() - c0
    with (out / 'history.jsonl').open('w') as fh:
        for h in history:
            fh.write(json.dumps(h, sort_keys=True) + '\n')
    if SL.problems(program, reps):
        raise RuntimeError('the search returned a program outside the language')
    desc = C2.build_descriptor('solver-library-v1', TF, {'program': program, 'cpu_seconds': 0.5}, **R11.PROFILE)
    uses = sorted({s[1] for b, _ in SL._blocks(program) for s in b if s[0] == 'macro'})
    summary = {'schema': 'genesis-b20r83-generation-search-v1', 'study': study, 'role': cfg['role'],
               'program': program, 'size': SL.size(program), 'macros_used': uses,
               'descriptor_at_0.5s': desc, 'search': report, 'cpu_s': round(cpu_used, 1),
               'seeds': {'hosts': cfg['host_seed'], 'search': cfg['search_seed']},
               'library_sources': [str(p.relative_to(ROOT)) for p in cfg['library']],
               'constants': {'POP': SS.POP, 'CHILDREN': SS.CHILDREN, 'BUDGET': SS.BUDGET, 'SEARCH_S': SEARCH_S},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV generation of the program search; judged in B20_R86; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    R11.dump(out / 'program.json', {'program': program, 'descriptor_at_0.5s': desc, 'macros_used': uses})
    log(f'frozen program (size {summary["size"]}, macros used {uses}): {json.dumps(program["body"])} '
        f'rep {program["rep"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
