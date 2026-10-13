#!/usr/bin/env python3
"""B20_R14 design probe (DEV): is the B20_R13 solver portfolio already at the optimum?

    b20r14_optimum_gap_probe.py OUT_DIR [--seconds 60]

B20_R13 found no headroom in choosing among solver configurations (NO_HEADROOM in all 7
settings). This probe asks the follow-up design question for GV4 in graph construction: on the
same held-out hosts, how far is the portfolio's per-host best (BEST_OF, from the R13 rows) from
the certified optimum? If the portfolio already sits at the optimum, no research process can do
better on these families, and a GV4 study needs harder ones. If a gap remains, it is
capability headroom (new methods), not selection headroom.

Method (fixed here, before running): for every held-out host of every R13 setting, re-run the
setting's ORACLE-chosen configuration once with the R13 seed (0.5 CPU s) to get a witness, then
``obstruction.certify(task, witness, seconds=SECONDS)``: an exact LP dual bound, then SAT/DRAT on
the remaining gap (SAT models can also raise the lower bound). Per host: the checked upper bound
U (LP_DUAL_EXACT, SAT_DRAT or HOST_EDGE_COUNT), the best checked lower bound L, the R13 BEST_OF B.

Verdict per setting (fixed here; MUE = 0.5 edges per host as in E1 and R13):
  UNSETTLED_BOUNDS   fewer than 12 of the 16 hosts end with U == L (certified optimum)
  ROOM_TO_OPTIMUM    otherwise, if mean over certified hosts of (optimum - B) >= MUE
  AT_CEILING         otherwise
A design diagnostic, not a study: it licenses no claim. Hosts are the R13 hosts (already exposed).
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

R13 = ROOT / 'evidence' / 'graph_headroom_b20r13'
MUE, MIN_CERTIFIED = 0.5, 12


def main(argv=None):
    import b20r13_graph_headroom_pilot as P13
    args = argv or sys.argv[1:]
    out = Path(args[0])
    seconds = float(args[args.index('--seconds') + 1]) if '--seconds' in args else 60.0
    out.mkdir(parents=True, exist_ok=True)
    hosts = json.loads((R13 / 'hosts.json').read_text())
    rows = [json.loads(line) for line in (R13 / 'rows.jsonl').read_text().splitlines()]
    summary13 = json.loads((R13 / 'summary.json').read_text())
    value = {(r['setting'], r['config'], r['task_id']): r['value'] for r in rows}
    done = {}
    rows_path = out / 'rows.jsonl'
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            done[(r['setting'], r['task_id'])] = r
    t0 = time.monotonic()
    with rows_path.open('a') as fh:
        for sid, domain, family, params in P13.SETTINGS:
            configs = {n: spec for n, _, spec in P13.configurations(domain)}
            chosen = summary13['settings'][sid]['chosen']['ORACLE']
            for raw in hosts[sid]['held_out']:
                task = GraphTask.model_validate_json(canonical(raw))
                if (sid, task.task_id) in done:
                    continue
                seed = int(P13.digest({'pilot': 'b20r13', 'task': task.task_id})[:12], 16)
                best_of = max(value[(sid, n, task.task_id)] for n in configs)
                witness = _witness(task, configs[chosen], seed, P13)
                rerun = len(witness)
                rec = O.certify(task, witness, seconds=seconds)
                r = {'setting': sid, 'task_id': task.task_id, 'n': task.n, 'm': len(task.edges), 'config': chosen,
                     'rerun_value': rerun, 'best_of_r13': best_of,
                     'lower': rec['lower'], 'upper': rec['upper'], 'upper_method': rec['upper_evidence']['method'],
                     'status': rec['status'], 'wall_s': rec['wall_s']}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                done[(sid, task.task_id)] = r
                print(f'[{time.monotonic() - t0:7.1f}s] {sid} {task.task_id}: B={best_of} L={rec["lower"]} '
                      f'U={rec["upper"]} ({r["upper_method"]}) {rec["status"]}', flush=True)
    summary = {'schema': 'genesis-b20r14-optimum-gap-v1', 'seconds': seconds, 'mue': MUE,
               'min_certified': MIN_CERTIFIED, 'settings': {}}
    for sid, domain, family, params in P13.SETTINGS:
        rs = [r for (s, _), r in done.items() if s == sid]
        cert = [r for r in rs if r['lower'] == r['upper']]
        gaps = [r['upper'] - r['best_of_r13'] for r in cert]
        open_gaps = [r['upper'] - r['lower'] for r in rs if r['lower'] < r['upper']]
        if len(cert) < MIN_CERTIFIED:
            verdict = 'UNSETTLED_BOUNDS'
        else:
            verdict = 'ROOM_TO_OPTIMUM' if statistics.mean(gaps) >= MUE else 'AT_CEILING'
        summary['settings'][sid] = {
            'domain': domain, 'family': family, 'params': params, 'hosts': len(rs), 'certified_optimum': len(cert),
            'mean_optimum_minus_best_of': round(statistics.mean(gaps), 3) if gaps else None,
            'hosts_best_of_at_optimum': sum(1 for g in gaps if g == 0),
            'max_optimum_minus_best_of': max(gaps) if gaps else None,
            'open_gaps': open_gaps, 'upper_methods': sorted({r['upper_method'] for r in rs}), 'verdict': verdict}
    summary['verdicts'] = {k: v['verdict'] for k, v in summary['settings'].items()}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print('verdicts', summary['verdicts'], flush=True)
    return 0


def _witness(task, spec, seed, P13):
    """The witness of one R13 configuration run (same code path as P13.run_config)."""
    import time as _t
    from genesis.dsl import solve
    from genesis.models import SolverProgram
    if 'representation' in spec:
        from genesis.invention import representations as R
        rep = next(r for r in R.proposals() if r['id'] == spec['representation'])
        return R.represent_and_repair(task.n, task.edges, rep, R.tf_add_ok, cpu_seconds=P13.SEARCH_S, seed=seed)['witness']
    program = SolverProgram.model_validate_json(canonical(spec['program']))
    start, best, k = _t.process_time_ns(), None, 0
    while best is None or _t.process_time_ns() - start < int(P13.SEARCH_S * 1e9):
        o = solve(task, program, P13.QUERIES, (seed + 1_000_003 * k) % (1 << 62))
        if best is None or o['value'] > best['value']:
            best = o
        k += 1
    return best['selected']


if __name__ == '__main__':
    sys.exit(main())
