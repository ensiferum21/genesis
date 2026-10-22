#!/usr/bin/env python3
"""B20_R98: why do DeepDist-c and NuWLS-c-2026 end near half the best value on large hosts? A harness check (the
adaptation cell's work order after B20_R97; DEV diagnostic, preregistered)

    taskset -c 0 python3 scripts/b20r98_harness_check.py OUT_DIR      run ALONE (resumable per run), then analyse

**Why.** In B20_R97, DeepDist-c (7th in the MaxSAT Evaluation 2026 unweighted anytime ranking) and NuWLS-c-2026 (8th)
ended at 40-63% of the best known value on hosts with 128 and 256 vertices, and DeepDist-c barely moved when given its
home budget (60 s: NO_RESPONSE). Tuned solvers that rank well in the Evaluation should not collapse like that, so
until the harness is ruled out, B20_R97's margins over these two solvers are not evidence about them. Our kinds differ
from the Evaluation's conditions in four ways: the instance arrives on a pipe (`/proc/self/fd/0`), not as a file; the
run is inside the runc sandbox with a 2 GiB address-space limit (the Evaluation gives 32 GB); the run is ended by
SIGTERM at the budget (the Evaluation uses runsolver, and DeepDist-c also sets its own alarm from the timeout hint);
and the model is read from the solver's last "v" line by `maxsat.parse_model`.

**Design (fixed before running).**
  * **Hosts.** The first host of each of B20_R97's four cells (planted and G(n, 0.5), n = 128 and 256), exposed;
    this is a check of the harness on the instances where the behaviour was seen, not a comparison.
  * **Solvers.** deepdist-c and nuwls-c-2026 (the two that collapsed), with deepdist (2024) and nuwls-c-2026-ub (the
    UB variant of the same 2026 code, which did not collapse) as controls.
  * **Conditions** (budget 10 s unless stated; the instance is `maxsat2026.wcnf2022`'s / `maxsat.wcnf`'s seeded copy
    with the seed B20_R97 used on that host for that solver, so C0 reproduces B20_R97's run):
      - C0 `kind`: the registered kind in runc through `candidates_large` (B20_R97's descriptor, re-identified by this
        batch's repin: the run refuses unless `b20r98_repin.pre_r98_id` of it is B20_R97's recorded id), as in B20_R97;
      - C1 `pipe`: the kind's own command line, pipe input and SIGTERM at the budget, run directly (no sandbox, no
        memory limit), with the solver's whole output kept;
      - C2 `file`: as C1 but the instance is a file named on the command line;
      - C3 `file_grace`: as C2, but the solver is left to stop itself (the 2026 entrants get the timeout hint; the run
        is ended only at the budget + 5 s);
      - C4 `file_60`: as C2 with a 60 s budget (and hint), the Evaluation's shortest budget.
    One run per (host, solver, condition): 4 x 4 x 5 = 80 runs, about 22 minutes.
  * **Measures.** The value of the parsed model (re-checked against every hard clause); for C1-C4 also the solver's
    own claims: the last "o" line (its cost, the number of falsified soft clauses, so its claimed value is m - o), the
    number of "v" lines and their format (0/1 string or literals), and whether the output ends cleanly.
  * **Labels (per solver).**
      - PARSE_MISMATCH if in any C1-C4 run the solver's last "o" line claims a value larger than the parsed model's
        (the harness reads a worse model than the solver reports);
      - SANDBOX_EFFECT if C1's value exceeds C0's by at least 5% of the host's best known value (B20_R97) on at
        least 3 of the 4 hosts;
      - INPUT_EFFECT, likewise C2 over C1; STOP_EFFECT, C3 over C2; BUDGET_EFFECT, C4 over C2;
      - NO_HARNESS_EFFECT if none of these holds. A solver can carry several labels.
    **Headline:** HARNESS_DEFECT if either collapsing solver carries PARSE_MISMATCH, SANDBOX_EFFECT, INPUT_EFFECT or
    STOP_EFFECT (conditions under our control that the Evaluation does not impose); NOT_THE_HARNESS if both carry
    only NO_HARNESS_EFFECT or BUDGET_EFFECT; then the collapse is these solvers' behaviour on these instances and
    B20_R97's margins over them stand. The controls must show NO_HARNESS_EFFECT; if a control shows an effect,
    the headline is reported with that caveat.
  * **If HARNESS_DEFECT:** the kind is repaired in an engineering batch (a new kind version; the defect recorded) and
    B20_R97's comparison with these two solvers is re-run (B20_R98b). Nothing is repaired in this script.

**Expectation, stated before running.** Unknown; slightly more likely NOT_THE_HARNESS, because the same harness
serves the other 11 champions well (DeepDist 2024 within 0-10 edges of the best at n = 128) and both collapsing
solvers emitted valid models; the most likely harness cause, if any, is the output (PARSE_MISMATCH) or the
address-space limit (SANDBOX_EFFECT). **Status.** A DEV diagnostic; licenses nothing; changes no package, rule or
comparator.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402

STUDY = 'b20r98'
R97 = ROOT / 'evidence' / 'qet_large_b20r97'
SOLVERS = ('deepdist-c', 'nuwls-c-2026', 'deepdist', 'nuwls-c-2026-ub')
COLLAPSING, CONTROLS = ('deepdist-c', 'nuwls-c-2026'), ('deepdist', 'nuwls-c-2026-ub')
R97_ARM = {'deepdist-c': 'deepdistc', 'nuwls-c-2026': 'nuwls26', 'deepdist': 'deepdist', 'nuwls-c-2026-ub': 'nuwls26ub'}
CONDITIONS = ('kind', 'pipe', 'file', 'file_grace', 'file_60')
BUDGET, LONG, GRACE, EFFECT = 10.0, 60.0, 5.0, 0.05


def log_to(out):
    t0 = time.time()

    def log(msg):
        line = f'[{time.time() - t0:8.1f}s] {msg}'
        print(line, flush=True)
        with open(out / 'run.log', 'a') as f:
            f.write(line + '\n')
    return log


def hosts():
    """The first host of each B20_R97 cell, with that host's B20_R97 row."""
    from genesis.models_large import LargeGraphTask
    tasks = [LargeGraphTask.model_validate_json(canonical(t)) for t in json.loads((R97 / 'hosts.json').read_text())['tasks']]
    rows = {json.loads(l)['task_id']: json.loads(l) for l in (R97 / 'rows.jsonl').read_text().splitlines() if l.strip()}
    out, seen = [], set()
    for t in tasks:
        cell = (t.family.split(':')[0], t.n)
        if cell not in seen and t.task_id in rows:
            seen.add(cell)
            out.append((t, rows[t.task_id]))
    return out


def r97_design():
    import importlib.util
    spec = importlib.util.spec_from_file_location('b20r97', ROOT / 'scripts' / 'b20r97_qet_large.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.DESIGN


def descriptor(solver, budget):
    from genesis import candidates_large as CL
    from genesis.candidate_kinds import maxsat_large as ML
    return CL.build_descriptor('maxsat-anytime-large-v1', {'solver': solver, 'cpu_seconds': budget},
                               cpu_seconds=budget + ML.ENCODING_ALLOWANCE_S, wall_seconds=max(60, int(3 * budget) + 60))


def claims(out, m):
    """The solver's own report: last 'o' cost, its claimed value, the 'v' lines' count and format, the tail."""
    os_ = [l.split()[1] for l in out.splitlines() if l.startswith('o ') and len(l.split()) > 1]
    vs = [l for l in out.splitlines() if l.startswith('v ')]
    last_o = int(os_[-1]) if os_ and os_[-1].lstrip('-').isdigit() else None
    fmt = None
    if vs:
        body = vs[-1][2:].strip()
        fmt = 'bits' if body and set(body) <= {'0', '1'} and ' ' not in body else 'literals'
    return {'o_lines': len(os_), 'last_o': last_o, 'claimed_value': None if last_o is None else m - last_o,
            'v_lines': len(vs), 'v_format': fmt, 's_line': next((l for l in out.splitlines()[::-1] if l.startswith('s ')), None),
            'tail': out[-200:]}


def direct(task, solver, seed, condition):
    """One direct run (no sandbox): the kind's encoding and command, varied as the condition says."""
    from genesis.candidate_kinds import maxsat as MS, maxsat2026 as M26, maxsat_large as ML
    E = [tuple(e) for e in task.edges]
    era, s = ML.SOLVERS[solver]
    text, order = (MS.wcnf if era == '2024' else M26.wcnf2022)(E, seed)
    budget = LONG if condition == 'file_60' else BUDGET
    with tempfile.TemporaryDirectory(prefix='b20r98-') as d:
        if condition == 'pipe':
            inst = '/proc/self/fd/0'
        else:
            inst = str(Path(d) / 'instance.wcnf')
            Path(inst).write_text(text)
        if era == '2024':
            argv = [s['binary'], inst, *s['args']]
        else:
            argv = [s['binary'], *[a.format(instance=inst, seconds=M26.hint(budget)) for a in s['args']]]
        limit = budget + (GRACE if condition == 'file_grace' else 0.0)
        t0 = time.time()
        p = subprocess.Popen(argv, stdin=subprocess.PIPE if condition == 'pipe' else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=d)
        stopped = 'self'
        try:
            out, err = p.communicate(input=text if condition == 'pipe' else None, timeout=limit)
        except subprocess.TimeoutExpired:
            stopped = 'sigterm'
            p.send_signal(signal.SIGTERM)
            try:
                out, err = p.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                stopped = 'kill'
                p.kill()
                out, err = p.communicate()
        wall = time.time() - t0
    true = MS.parse_model(out, len(E))
    value, valid = None, None
    if true is not None:
        chosen = sorted(E[order[k - 1]] for k in true if 1 <= k <= len(E))
        nb = {}
        for u, v in chosen:
            nb[u] = nb.get(u, 0) | 1 << v
            nb[v] = nb.get(v, 0) | 1 << u
        valid = not any(nb[u] & nb[v] for u, v in chosen)
        value = len(chosen) if valid else None
    return dict(claims(out, len(E)), value=value, valid=valid, stopped=stopped, returncode=p.returncode,
                wall_s=round(wall, 2), stderr_tail=err[-200:])


def labels(runs, best):
    """{solver: [labels]} from {(task_id, solver, condition): run} and {task_id: best known value}."""
    out = {}
    for s in SOLVERS:
        mine = {(t, c): r for (t, s2, c), r in runs.items() if s2 == s}
        ls = []
        if any(r.get('claimed_value') is not None and r.get('value') is not None and r['claimed_value'] > r['value']
               for (t, c), r in mine.items() if c != 'kind'):
            ls.append('PARSE_MISMATCH')
        for lab, hi, lo in (('SANDBOX_EFFECT', 'pipe', 'kind'), ('INPUT_EFFECT', 'file', 'pipe'),
                            ('STOP_EFFECT', 'file_grace', 'file'), ('BUDGET_EFFECT', 'file_60', 'file')):
            wins = sum(1 for t in best if (mine.get((t, hi), {}).get('value') or 0) - (mine.get((t, lo), {}).get('value') or 0)
                       >= EFFECT * best[t])
            if wins >= 3:
                ls.append(lab)
        out[s] = ls or ['NO_HARNESS_EFFECT']
    return out


def headline(labs):
    harness = {'PARSE_MISMATCH', 'SANDBOX_EFFECT', 'INPUT_EFFECT', 'STOP_EFFECT'}
    h = 'HARNESS_DEFECT' if any(set(labs[s]) & harness for s in COLLAPSING) else 'NOT_THE_HARNESS'
    caveat = [s for s in CONTROLS if labs[s] != ['NO_HARNESS_EFFECT']]
    return h, caveat


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'harness_check_b20r98').resolve():
        raise SystemExit('the registered output is evidence/harness_check_b20r98')
    out.mkdir(parents=True, exist_ok=True)
    log = log_to(out)
    import b20r33_strong_baseline_audit as R33
    R33.pinned_core()
    log(f'{STUDY}; pinned to CPU {sorted(os.sched_getaffinity(0))}')
    from genesis import candidates_large as CL
    from genesis.autonomy import qet
    design = r97_design()
    H = hosts()
    D = {s: descriptor(s, BUDGET) for s in SOLVERS}
    for s in SOLVERS:                   # B20_R97's own descriptors: C0 reproduces its runs
        if R97_ARM[s] in {a for a, _ in design['champions']}:
            want = json.loads((R97 / 'summary.json').read_text()).get('descriptors', {}).get(f'{R97_ARM[s]}@10')
            import b20r98_repin as R98       # this batch's repin changed the kinds' identity, not what they run
            if want is not None and want != R98.pre_r98_id(D[s]):
                raise SystemExit(f'{s}: not B20_R97\'s descriptor ({R98.pre_r98_id(D[s])[:16]} != {want[:16]})')
    path = out / 'runs.jsonl'
    done = {}
    if path.exists():
        for l in path.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                done[(r['task_id'], r['solver'], r['condition'])] = r
    for task, row in H:
        for s in SOLVERS:
            seed = qet.run_seed(design, task.task_id, R97_ARM[s], BUDGET)
            for c in CONDITIONS:
                if (task.task_id, s, c) in done:
                    continue
                if c == 'kind':
                    r = CL.run(task, D[s], seed=seed, expected_id=D[s]['descriptor_id'], isolation='runc')
                    rec = {'value': r['result']['value'] if r.get('status') == 'SUCCESS' else None,
                           'status': r.get('status'), 'cpu_ns': r.get('cpu_ns')}
                else:
                    rec = direct(task, s, seed, c)
                rec.update(task_id=task.task_id, solver=s, condition=c, seed=seed,
                           r97_value=row['runs'].get(R97_ARM[s], {}).get('10', {}).get('value'))
                with open(path, 'a') as f:
                    f.write(json.dumps(rec, sort_keys=True) + '\n')
                done[(task.task_id, s, c)] = rec
                log(f'{task.task_id[-14:]} {s:16s} {c:10s} value {rec.get("value")} '
                    f'(claimed {rec.get("claimed_value")}, v {rec.get("v_lines")} {rec.get("v_format")}, '
                    f'stopped {rec.get("stopped")}; B20_R97 {rec["r97_value"]})')
    best = {t.task_id: row['best_value'] for t, row in H}
    labs = labels(done, best)
    h, caveat = headline(labs)
    summary = {'study': STUDY, 'schema': 'genesis-b20r98-harness-check-v1', 'headline': h, 'control_caveat': caveat,
               'labels': labs, 'best_known': best, 'hosts': [t.task_id for t, _ in H],
               'descriptors': {s: d['descriptor_id'] for s, d in D.items()},
               'status': 'DEV diagnostic; licenses nothing; no package changed',
               'code_identity': code_identity(ROOT)['sha256']}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'headline {h}; labels {labs}; control caveat {caveat}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
