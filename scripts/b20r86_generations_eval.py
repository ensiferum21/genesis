#!/usr/bin/env python3
"""B20_R86: do the system's generations compound? (GV5, DEV, preregistered before B20_R79 has finished)

    taskset -c 0 python3 scripts/b20r86_generations_eval.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** GV5: gains across three generations, each judged against the one before on a fresh panel, with causal
evidence. Generation 1 is B20_R79's program (search from random programs); generation 2 is B20_R83's (the same
search with generation 1 callable); generation 3 is B20_R85's (generations 1 and 2 callable); the control is B20_R84's
(generation 2's search, hosts and budget, no library).

**Design (fixed before running).**
  * **Programs:** gen1 = `evidence/program_search_b20r79/discovered_program.json` (`solver-program-v1`); gen2, gen3,
    control = `evidence/{generation2_b20r83, generation3_b20r85, generation2_control_b20r84}/program.json`
    (`solver-library-v1`); SHA-256 recorded; the study refuses to run without all four.
  * **Hosts.** 24 fresh DEV planted-cluster hosts (p_in 0.8, p_out 0.06) at n63, seed 20268601, excluding every
    identity `b20r24_repilots.exposure` excludes (every generation's training hosts included).
  * **Part A,** in runc under E1's profile, run times (0.05, 0.1, 0.25, 0.5, 2.0) CPU s, 3 seeds each, arms gen1,
    gen2, gen3, control, and engine (B20_R77's builder-made `hybrid-swap-v1`, as a reference). **Part B:** CP-SAT
    60 s and the checked reference (120 s), for the targets.
  * **Statistic:** B20_R77's/B20_R81's quantile ratio, r(a, b, q) = log2(TTS*_b(q) / TTS*_a(q)), paired bootstrap
    90% (4,000, seed 20268699), q in (0.5, 0.75); per q: A_FASTER (lower end > 1), B_FASTER (upper end < −1),
    COMPARABLE (inside (−1, 1)), UNRESOLVED.
  * **Labels.** For a pair (later, earlier): IMPROVES (later faster at one q or both, earlier faster at neither),
    WORSENS (the reverse), NO_DIFFERENCE (comparable at both), UNRESOLVED.
      - transition 1→2: (gen2, gen1); transition 2→3: (gen3, gen2);
      - the library's effect: (gen2, control): LIBRARY_HELPS / LIBRARY_HURTS / NO_DIFFERENCE / UNRESOLVED;
      - **headline:** COMPOUNDS if both transitions IMPROVE and LIBRARY_HELPS; PARTIAL if at least one transition
        IMPROVES and none WORSENS; NO_COMPOUNDING otherwise.
    Validity first, as before (CPU at t = 0.5 at least 0.45 s; at most 1% failed runs).
  * **Secondary:** gen3 against gen1; every generation and the control against the engine; B20_R76's per-host
    statistic; hosts reached within 2 s and TTS* quantiles per arm; Part B.

**Expectation, stated before B20_R79 has finished.** Generation 2 improves on generation 1 only if generation 1
leaves room (if generation 1 already reaches most targets at the shortest run times, nothing can show); generation
3 adds little; so PARTIAL or NO_COMPOUNDING, PARTIAL slightly more likely. **Status.** DEV; licenses nothing.
"""
import hashlib
import json
import math
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
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.invention import solver_library as SL  # noqa: E402
from genesis.invention import solver_programs as SP  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402
import b20r70_tts_scaling as R70  # noqa: E402
import b20r76_sota as R76  # noqa: E402

TF = RD.TF
SEED, PER_N, N, REF_S = 20268601, 24, 63, 120
P_IN, P_OUT = 0.8, 0.06
LADDER, REPS = R76.LADDER, 3
BOOT, BOOT_SEED = 4000, 20268699
QS = (0.5, 0.75)
PROFILE = R11.PROFILE
EV = ROOT / 'evidence'
SOURCES = {'gen1': EV / 'program_search_b20r79' / 'discovered_program.json',
           'gen2': EV / 'generation2_b20r83' / 'program.json',
           'gen3': EV / 'generation3_b20r85' / 'program.json',
           'control': EV / 'generation2_control_b20r84' / 'program.json'}
ARMS = ('gen1', 'gen2', 'gen3', 'control', 'engine')
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01
assert LADDER == (0.05, 0.1, 0.25, 0.5, 2.0)


def programs():
    reps = KP.licensed_reps(TF)
    out = {}
    for arm, path in SOURCES.items():
        if not path.exists():
            raise SystemExit(f'{path.relative_to(ROOT)} is missing: run B20_R79 and B20_R83-R85 first')
        prog = json.loads(path.read_text())['program']
        bad = SP.problems(prog, reps) if arm == 'gen1' else SL.problems(prog, reps)
        if bad:
            raise SystemExit(f'{arm} program is not in its language: {bad}')
        out[arm] = (prog, hashlib.sha256(path.read_bytes()).hexdigest())
    return out


def arm_descriptors(progs):
    out = {}
    for t in LADDER:
        out[('gen1', t)] = ('v2', C2.build_descriptor('solver-program-v1', TF,
                                                      {'program': progs['gen1'][0], 'cpu_seconds': t}, **PROFILE))
        for a in ('gen2', 'gen3', 'control'):
            out[(a, t)] = ('v2', C2.build_descriptor('solver-library-v1', TF,
                                                     {'program': progs[a][0], 'cpu_seconds': t}, **PROFILE))
        out[('engine', t)] = ('v2', C2.build_descriptor('hybrid-swap-v1', TF, {'cpu_seconds': t}, **PROFILE))
    if len({canonical(d['resource_profile']) for _, d in out.values()}) != 1:
        raise RuntimeError('the arms do not share one resource profile')
    for k, (_, d) in out.items():
        if C2.descriptor_problems(d, domain=TF):
            raise RuntimeError(f'{k} does not rebuild')
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, _ = R64.generate_beyond_space(SEED, PER_N, 'DEV', {'n': N, 'p_in': P_IN, 'p_out': P_OUT}, set(excluded))
    if len(tasks) != PER_N or RD.identities(tasks) & set(excluded):
        raise RuntimeError('host drawing failed or collides with an excluded identity')
    R11.dump(path, {'seed': SEED, 'per_n': PER_N, 'n': N, 'params': {'p_in': P_IN, 'p_out': P_OUT},
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def run_seed(task_id, arm, t, k):
    return int(digest({'study': 'b20r86', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


# ----------------------------------------------------------------------------------------------- analysis

def boot(stat, k):
    rng = random.Random(BOOT_SEED)
    sims = sorted(stat([rng.randrange(k) for _ in range(k)]) for _ in range(BOOT))
    return stat(list(range(k))), [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def verdict(ci):
    lo, hi = ci
    if lo > 1:
        return 'A_FASTER'
    if hi < -1:
        return 'B_FASTER'
    if -1 < lo and hi < 1:
        return 'COMPARABLE'
    return 'UNRESOLVED'


def pair(T, a, b):
    out = {}
    for q in QS:
        est, ci = boot(lambda ix, q=q: R70.log_ratio(R70.quantile([T[b][i] for i in ix], q),
                                                    R70.quantile([T[a][i] for i in ix], q)), len(T[a]))
        out[f'q{q}'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                        'verdict': verdict(ci)}
    per_host = [R70.log_ratio(y, x) for x, y in zip(T[a], T[b])]
    est, ci = boot(lambda ix: statistics.median(per_host[i] for i in ix), len(per_host))
    out['b20r76_per_host_median'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                                     'verdict': verdict(ci)}
    return out


def change(p, up='IMPROVES', down='WORSENS'):
    v = [p[f'q{q}']['verdict'] for q in QS]
    if 'A_FASTER' in v and 'B_FASTER' not in v:
        return up
    if 'B_FASTER' in v and 'A_FASTER' not in v:
        return down
    if all(x == 'COMPARABLE' for x in v):
        return 'NO_DIFFERENCE'
    return 'UNRESOLVED'


def headline(t12, t23, lib):
    if t12 == 'IMPROVES' and t23 == 'IMPROVES' and lib == 'LIBRARY_HELPS':
        return 'COMPOUNDS'
    if 'IMPROVES' in (t12, t23) and 'WORSENS' not in (t12, t23):
        return 'PARTIAL'
    return 'NO_COMPOUNDING'


def analyse(rows):
    T = {a: [R76.host_tts(r, a)[0] for r in rows] for a in ARMS}
    p12, p23, plib = pair(T, 'gen2', 'gen1'), pair(T, 'gen3', 'gen2'), pair(T, 'gen2', 'control')
    t12, t23 = change(p12), change(p23)
    lib = change(plib, 'LIBRARY_HELPS', 'LIBRARY_HURTS')
    e = [r['exact']['cpsat'] for r in rows]
    return {'hosts': len(rows), 'certified': sum(r['target_certified'] for r in rows),
            'edges': [min(r['edges'] for r in rows), max(r['edges'] for r in rows)] if rows else None,
            'labels': {'transition_1_2': t12, 'transition_2_3': t23, 'library_effect': lib,
                       'headline': headline(t12, t23, lib)},
            'gen2_vs_gen1': p12, 'gen3_vs_gen2': p23, 'gen2_vs_control': plib, 'gen3_vs_gen1': pair(T, 'gen3', 'gen1'),
            'vs_engine': {a: pair(T, a, 'engine') for a in ('gen1', 'gen2', 'gen3', 'control')},
            'arms': {a: {'reached_within_2s': sum(not math.isinf(v) for v in T[a]),
                         'tts_median': R70._num(R70.quantile(T[a], 0.5)), 'tts_q75': R70._num(R70.quantile(T[a], 0.75))}
                     for a in ARMS},
            'exact': {'cpsat_60s_reaches_target': sum(x['value'] == r['target'] for x, r in zip(e, rows))}}


def validity(rows):
    cpu = {a: statistics.median(r['cpu_ns'][a]['0.5'] for r in rows) / 1e9 for a in ARMS}
    runs = {a: [x for r in rows for t in LADDER for x in r['runs'][a][str(t)]] for a in ARMS}
    fail = {a: sum(x['run'] != 'SUCCESS' for x in runs[a]) / len(runs[a]) for a in ARMS}
    if any(cpu[a] < MIN_CPU_AT_HALF for a in ARMS):
        return 'INVALID_CPU_DELIVERY', cpu, fail
    if any(fail[a] > MAX_FAIL_SHARE for a in ARMS):
        return 'INVALID_FAILURES', cpu, fail
    return None, cpu, fail


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    progs = programs()
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='b20r86-'))
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    for a, (p, h) in progs.items():
        log(f'{a} sha256 {h[:16]}: {json.dumps(p["body"])} rep {p["rep"]}')
    from genesis.verification.tools import tool
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim')))
    D = arm_descriptors(progs)
    registry = R37.registry_v2(json.loads(R41.PACKAGE.read_text()))
    excluded, scan, _ = R24.exposure(log)
    tasks = hosts(out, log, excluded)
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for task in tasks:
            if task.task_id in done:
                continue
            runs, cpu_ns, best = {a: {} for a in ARMS}, {a: {} for a in ARMS}, (None, -1)
            for a in ARMS:
                for t in LADDER:
                    reg, desc = D[(a, t)]
                    rs = []
                    for k in range(REPS):
                        res, sel = R41.run_arm(task, reg, desc, run_seed(task.task_id, a, t, k))
                        rs.append({'value': res['value'], 'run': res['run'], 'cpu_ns': res['cpu_ns'],
                                   'isolation': res['isolation']})
                        if sel is not None and res['value'] > best[1]:
                            best = (sel, res['value'])
                    runs[a][str(t)] = rs
                    cpu_ns[a][str(t)] = int(statistics.median(x['cpu_ns'] for x in rs))
            ex = {}
            ex['cpsat'], sel = R76.exact(task, 'cpsat', tmp)
            if sel is not None and ex['cpsat']['value'] > best[1]:
                best = (sel, ex['cpsat']['value'])
            ref, _ = R41.reference(task, [('best', best[0])], registry, REF_S)
            target = max(best[1], ref['lower'])
            r = {'task_id': task.task_id, 'n': task.n, 'split': task.split, 'edges': len(task.edges), 'runs': runs,
                 'cpu_ns': cpu_ns, 'exact': ex, 'reference': ref, 'target': target,
                 'target_certified': ref['upper'] == target, 'best_witness_value': best[1]}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            tts = {a: R76.host_tts(r, a) for a in ARMS}
            log(f'{task.task_id[-4:]} ({len(task.edges)} edges) target {target}'
                f'{"" if r["target_certified"] else " (uncertified)"}: ' + ' '.join(f'{a} {tts[a][0]:.3g}' for a in ARMS))
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    invalid, cpu_half, fail = validity(rows)
    a = analyse(rows)
    labels = {k: (invalid or v) for k, v in a['labels'].items()}
    summary = {'schema': 'genesis-b20r86-generations-v1', 'labels': labels, **{k: v for k, v in a.items() if k != 'labels'},
               'validity': {'cpu_s_median_at_0.5': {k: round(v, 3) for k, v in cpu_half.items()},
                            'failure_share': {k: round(v, 5) for k, v in fail.items()}},
               'programs': {k: {'program': v[0], 'file_sha256': v[1]} for k, v in progs.items()},
               'descriptors': {f'{x}@{t}': d['descriptor_id'] for (x, t), (_, d) in D.items()},
               'ladder': list(LADDER), 'reps': REPS, 'quantiles': list(QS), 'seeds': {'hosts': SEED, 'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV test of compounding generations; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    log(f'labels {labels}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
