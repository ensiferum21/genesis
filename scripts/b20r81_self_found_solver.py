#!/usr/bin/env python3
"""B20_R81: the solver the system found itself, against the builder's engine, random search and the state of the art
(DEV, preregistered before B20_R79 and B20_R80 have run)

    taskset -c 0 python3 scripts/b20r81_self_found_solver.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** Daniel asked that the system find its solver itself rather than be handed it. B20_R79 searches the solver
language of B20_R78 for a program; B20_R80 draws random programs for the same budget as a control. This study fixes,
before either has run, how the two frozen programs are judged: on fresh hosts, against the engine the builder
assembled (B20_R77's `hybrid-swap-v1`), simulated bifurcation, the system's B20_R76 engine, BURER2002 and CP-SAT.

**Design (fixed before running).**
  * **Programs:** `found` = `evidence/program_search_b20r79/discovered_program.json`, `random` =
    `evidence/random_program_control_b20r80/random_program.json`, both run by `solver-program-v1`; their SHA-256 are
    recorded. The study refuses to run unless both exist and are in the language.
  * **Hosts.** planted_cluster (p_in 0.8, p_out 0.06), 24 fresh DEV hosts at n63, seed 20268101, excluding every
    identity `b20r24_repilots.exposure` excludes (B20_R79's training hosts included).
  * **Part A, anytime, in runc under E1's profile**, run times (0.05, 0.1, 0.25, 0.5, 2.0) CPU s, 3 seeds each, arms
    found, random, engine (`hybrid-swap-v1`), dsb (`ising-dsb-v1`), system (`represent-search-v1` cross_2 descent),
    burer (`mqlib-v1` BURER2002), cpsat (`cpsat-v1`, 8 workers on one core).
  * **Part B:** CP-SAT 60 s (B20_R76's exact child) and the checked generated-rows reference (120 s).
  * **Target, TTS*, the quantile ratio and its paired bootstrap:** as B20_R77 (seed 20268199), with
    r(a, b, q) = log2(TTS*_b(q) / TTS*_a(q)), positive when a is faster; verdict per q: A_FASTER (lower end > 1),
    B_FASTER (upper end < −1), COMPARABLE (inside (−1, 1)), UNRESOLVED.
  * **Three preregistered questions, each with its own label (q = 0.5 and 0.75):**
      1. **GV4, the headline: does the system's own solver match the builder's?** found against engine:
         SELF_FOUND_BEATS_BUILDER (found faster at both q), BUILDER_BEATS_SELF_FOUND (engine faster at either),
         SELF_FOUND_MATCHES_BUILDER (comparable at both), UNRESOLVED otherwise.
      2. **Does the search do the work?** found against random: SEARCH_HELPS (found faster at one q or both, random
         faster at neither), SEARCH_HURTS (the reverse), NO_DIFFERENCE (comparable at both), UNRESOLVED.
      3. **Against the state of the art:** found against BURER2002 and CP-SAT, B20_R77's rule: SELF_FOUND_BEATS_SOTA
         (faster than both at both q), SOTA_BEATS_SELF_FOUND (either tool faster at either q), SELF_FOUND_MATCHES_SOTA
         (comparable in all four), MIXED.
    Validity first, as B20_R77: INVALID_CPU_DELIVERY (median CPU at t = 0.5 below 0.45 s), INVALID_FAILURES (> 1%).
  * **Secondary:** B20_R77's question again on these hosts (engine against both tools, its rule: a replication);
    found against the system's B20_R76 engine and against dSB; B20_R76's per-host statistic for every pair; per arm,
    hosts reached within 2 s and TTS* quantiles; Part B.

**Expectation, stated before B20_R79 has run.** The builder expects the found program to beat the system's B20_R76
engine, to beat random search (SEARCH_HELPS), and to lose to the builder's engine (BUILDER_BEATS_SELF_FOUND), since
it has no simulated bifurcation and the swap structure must be found; against the state of the art, faster than
CP-SAT, unsure against BURER2002, so MIXED more likely than SELF_FOUND_BEATS_SOTA. The engine should replicate
B20_R77 (ENGINE_BEATS_SOTA), though its narrow margin at q = 0.5 against BURER2002 may not hold.

**What it decides.** Nothing about packages, rules or comparators. **Status.** A DEV diagnostic; licenses nothing.
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
SEED, PER_N, N, REF_S = 20268101, 24, 63, 120
P_IN, P_OUT = 0.8, 0.06
LADDER, REPS = R76.LADDER, 3
BOOT, BOOT_SEED = 4000, 20268199
QS = (0.5, 0.75)
PROFILE = R11.PROFILE
FOUND = ROOT / 'evidence' / 'program_search_b20r79' / 'discovered_program.json'
RANDOM = ROOT / 'evidence' / 'random_program_control_b20r80' / 'random_program.json'
ARMS = ('found', 'random', 'engine', 'dsb', 'system', 'burer', 'cpsat')
SOTAS = ('burer', 'cpsat')
V2_FIXED = {'engine': ('hybrid-swap-v1', {}), 'dsb': ('ising-dsb-v1', {}),
            'system': ('represent-search-v1', {'representation': 'cross_2', 'move': 'descent'}),
            'burer': ('mqlib-v1', {'heuristic': 'BURER2002'}), 'cpsat': ('cpsat-v1', {})}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01
assert LADDER == (0.05, 0.1, 0.25, 0.5, 2.0)


def programs():
    """The two frozen programs and the SHA-256 of their files; refuses if either is missing or invalid."""
    out = {}
    for arm, path in (('found', FOUND), ('random', RANDOM)):
        if not path.exists():
            raise SystemExit(f'{path.relative_to(ROOT)} is missing: run B20_R79 and B20_R80 first')
        prog = json.loads(path.read_text())['program']
        bad = SP.problems(prog, KP.licensed_reps(TF))
        if bad:
            raise SystemExit(f'{arm} program is not in the language: {bad}')
        out[arm] = (prog, hashlib.sha256(path.read_bytes()).hexdigest())
    return out


def arm_descriptors(progs):
    out = {}
    for t in LADDER:
        for a in ('found', 'random'):
            out[(a, t)] = ('v2', C2.build_descriptor('solver-program-v1', TF,
                                                     {'program': progs[a][0], 'cpu_seconds': t}, **PROFILE))
        for a, (kind, extra) in V2_FIXED.items():
            out[(a, t)] = ('v2', C2.build_descriptor(kind, TF, dict(extra, cpu_seconds=t), **PROFILE))
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
    return int(digest({'study': 'b20r81', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


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
    """a against b: log2(TTS*_b(q) / TTS*_a(q)) at each q, and B20_R76's per-host median."""
    out = {}
    for q in QS:
        est, ci = boot(lambda ix, q=q: R70.log_ratio(R70.quantile([T[b][i] for i in ix], q),
                                                    R70.quantile([T[a][i] for i in ix], q)), len(T[a]))
        out[f'q{q}'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                        'verdict': verdict(ci)}
    per_host = [R70.log_ratio(y, x) for x, y in zip(T[a], T[b])]
    est, ci = boot(lambda ix: statistics.median(per_host[i] for i in ix), len(per_host))
    out['b20r76_per_host_median'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                                     'verdict': verdict(ci), 'host_log2_ratios': [round(v, 4) for v in per_host]}
    return out


def label_vs_builder(p):
    v = [p[f'q{q}']['verdict'] for q in QS]
    if all(x == 'A_FASTER' for x in v):
        return 'SELF_FOUND_BEATS_BUILDER'
    if any(x == 'B_FASTER' for x in v):
        return 'BUILDER_BEATS_SELF_FOUND'
    if all(x == 'COMPARABLE' for x in v):
        return 'SELF_FOUND_MATCHES_BUILDER'
    return 'UNRESOLVED'


def label_vs_random(p):
    v = [p[f'q{q}']['verdict'] for q in QS]
    if 'A_FASTER' in v and 'B_FASTER' not in v:
        return 'SEARCH_HELPS'
    if 'B_FASTER' in v and 'A_FASTER' not in v:
        return 'SEARCH_HURTS'
    if all(x == 'COMPARABLE' for x in v):
        return 'NO_DIFFERENCE'
    return 'UNRESOLVED'


def label_vs_sota(ps, prefix):
    v = [ps[S][f'q{q}']['verdict'] for S in SOTAS for q in QS]
    if all(x == 'A_FASTER' for x in v):
        return f'{prefix}_BEATS_SOTA'
    if any(x == 'B_FASTER' for x in v):
        return f'SOTA_BEATS_{prefix}'
    if all(x == 'COMPARABLE' for x in v):
        return f'{prefix}_MATCHES_SOTA'
    return 'MIXED'


def analyse(rows):
    T = {a: [R76.host_tts(r, a)[0] for r in rows] for a in ARMS}
    q1 = pair(T, 'found', 'engine')
    q2 = pair(T, 'found', 'random')
    q3 = {S: pair(T, 'found', S) for S in SOTAS}
    rep77 = {S: pair(T, 'engine', S) for S in SOTAS}
    e = [r['exact']['cpsat'] for r in rows]
    return {
        'hosts': len(rows), 'edges': [min(r['edges'] for r in rows), max(r['edges'] for r in rows)] if rows else None,
        'certified': sum(r['target_certified'] for r in rows),
        'labels': {'gv4_found_vs_builder': label_vs_builder(q1), 'found_vs_random': label_vs_random(q2),
                   'found_vs_sota': label_vs_sota(q3, 'SELF_FOUND'), 'b20r77_replication': label_vs_sota(rep77, 'ENGINE')},
        'found_vs_engine': q1, 'found_vs_random': q2, 'found_vs_sota': q3, 'engine_vs_sota': rep77,
        'found_vs_system': pair(T, 'found', 'system'), 'found_vs_dsb': pair(T, 'found', 'dsb'),
        'arms': {a: {'reached_within_2s': sum(not math.isinf(v) for v in T[a]),
                     'tts_median': R70._num(R70.quantile(T[a], 0.5)), 'tts_q75': R70._num(R70.quantile(T[a], 0.75))}
                 for a in ARMS},
        'exact': {'cpsat_60s': {'claims_optimal': sum(x['claims_optimal'] for x in e),
                                'reaches_target': sum(x['value'] == r['target'] for x, r in zip(e, rows))},
                  'generated_rows_reference': {'certified': sum(r['target_certified'] for r in rows)}}}


def validity(rows):
    cpu = {a: statistics.median(r['cpu_ns'][a]['0.5'] for r in rows) / 1e9 for a in ARMS}
    runs = {a: [x for r in rows for t in LADDER for x in r['runs'][a][str(t)]] for a in ARMS}
    fail = {a: sum(x['run'] != 'SUCCESS' for x in runs[a]) / len(runs[a]) for a in ARMS}
    if any(cpu[a] < MIN_CPU_AT_HALF for a in ARMS):
        return 'INVALID_CPU_DELIVERY', cpu, fail
    if any(fail[a] > MAX_FAIL_SHARE for a in ARMS):
        return 'INVALID_FAILURES', cpu, fail
    return None, cpu, fail


# ----------------------------------------------------------------------------------------------- run

def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    progs = programs()
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='b20r81-'))
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    for a in ('found', 'random'):
        log(f'{a} program sha256 {progs[a][1][:16]}: {json.dumps(progs[a][0], sort_keys=True)}')
    from genesis.verification.tools import tool
    from genesis.candidate_kinds import cpsat as K, mqlib as MQ
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim'))
        + f'; MQLib sha256 {MQ.binary_digest()[:16]}; OR-Tools tree sha256 {K.tree_digest()[:16]} workers {K.WORKERS}')
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
            certified = ref['upper'] == target
            r = {'task_id': task.task_id, 'n': task.n, 'split': task.split, 'edges': len(task.edges), 'runs': runs,
                 'cpu_ns': cpu_ns, 'exact': ex, 'reference': ref, 'target': target, 'target_certified': certified,
                 'best_witness_value': best[1]}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            tts = {a: R76.host_tts(r, a) for a in ARMS}
            log(f'{task.task_id[-4:]} ({len(task.edges)} edges) target {target}'
                f'{"" if certified else " (uncertified)"}: ' + ' '.join(f'{a} {tts[a][0]:.3g}' for a in ARMS)
                + f' | cpsat-60s {ex["cpsat"]["value"]} | ref {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    invalid, cpu_half, fail = validity(rows)
    a = analyse(rows)
    labels = {k: (invalid or v) for k, v in a['labels'].items()}
    summary = {'schema': 'genesis-b20r81-self-found-solver-v1', 'labels': labels, **{k: v for k, v in a.items() if k != 'labels'},
               'validity': {'cpu_s_median_at_0.5': {k: round(v, 3) for k, v in cpu_half.items()},
                            'failure_share': {k: round(v, 5) for k, v in fail.items()}},
               'programs': {k: {'program': v[0], 'file_sha256': v[1]} for k, v in progs.items()},
               'descriptors': {f'{x}@{t}': d['descriptor_id'] for (x, t), (_, d) in D.items()},
               'mqlib': {'sha256': MQ.binary_digest()}, 'ortools': {'sha256': K.tree_digest(), 'workers': K.WORKERS},
               'ladder': list(LADDER), 'reps': REPS, 'quantiles': list(QS), 'seeds': {'hosts': SEED, 'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV comparison; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f'labels {labels}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
