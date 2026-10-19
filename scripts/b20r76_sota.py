#!/usr/bin/env python3
"""B20_R76: E1d's candidate and the system's best engine against CP-SAT and BURER2002 (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r76_sota.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** B20_R75 was to compare the system with the most advanced tools available and came out
INVALID_CPU_DELIVERY: the BURER2002 kind passed seeds MQLib rejects and returned empty answers. The kind is fixed,
and Google OR-Tools CP-SAT (gold in the fixed, free and parallel categories of the MiniZinc Challenge 2025) is now
available, from the official wheel Daniel supplied (B20R74-OPEN-1 partly resolved). This study repeats B20_R75's
design on fresh hosts with both state-of-the-art tools: BURER2002, the best single max-cut heuristic of 37 in
Dunning, Gupta and Silberholz (2018), and CP-SAT, the leading general-purpose exact solver.

**Design (fixed before running).**
  * **Hosts.** planted_cluster (p_in 0.8, p_out 0.06), 6 fresh DEV hosts at n60 and 6 at n63 (the task model's
    maximum), seed 20267601, drawn by `b20r64_e1d_scaling.generate_beyond_space`, excluding every identity
    `b20r24_repilots.exposure` excludes (B20_R75's hosts included).
  * **Part A, anytime, all in runc under E1's profile** (2 CPU s, 2048 MiB, 10 s wall), at each run time t in
    (0.05, 0.1, 0.25, 0.5, 2.0) CPU s, REPS = 3 seeds per (host, arm, t):
      - `candidate`: E1d's frozen kind and parameters with `cpu_seconds` = t;
      - `system`: `represent-search-v1` {cross_2, descent} (the frozen rule with the faster repair, B20_R72);
      - `dsb`: `ising-dsb-v1`; `tabu`: `maxcut-tabu-v1`;
      - `burer`: `mqlib-v1` {BURER2002}, fixed (seeds modulo 65,536; failures fail the run);
      - `cpsat`: `cpsat-v1`, CP-SAT with its 8-worker portfolio on the child's single core;
      - `highs`: `milp-highs-v1`.
  * **Part B, exact, on the pinned core** (descriptive): CP-SAT (8 workers on the one core) and HiGHS, each in a
    child process with a 60 s limit, whose claims of optimality are reported as claims; and the system's own
    certification route, B20_R41's generated-rows reference (exact LP dual plus SAT/DRAT, 120 s), the only route
    with a checked certificate.
  * **Target per host.** The best value of any witness from Parts A and B (each re-checked by the domain checker),
    certified when the reference's checked upper bound equals it.
  * **Primary endpoints** (as B20_R70): per size and state-of-the-art tool S in (burer, cpsat), r = log2(TTS*_S /
    TTS*_x) per host for x in (candidate, system), TTS* at the optimal run time, infinite where never reached
    (±10 caps); the median over hosts with a bootstrap 90% interval (4,000 resamples, seed 20267699). Verdict per
    (n, S, x): X_FASTER (lower end > 1), SOTA_FASTER (upper end < −1), COMPARABLE (inside (−1, 1)), UNRESOLVED.
  * **Overall (at n63, for x = system):** SYSTEM_BEATS_SOTA if X_FASTER against both tools; SOTA_BEATS_SYSTEM if
    SOTA_FASTER against at least one; SYSTEM_MATCHES_SOTA if COMPARABLE against both; UNRESOLVED otherwise.
    Validity first: INVALID_CPU_DELIVERY if any Part A arm's median cgroup CPU at t = 0.5 is below 0.45 s;
    INVALID_FAILURES if more than 1% of an arm's runs failed (a kind that fails now fails loudly).
  * **Secondary, descriptive:** the same ratios for dSB, tabu and HiGHS; median and 75th-percentile TTS* per arm;
    Part B claim rates and times; certified targets.

**Start-up.** Every arm's budget starts after its imports, except `ising-dsb-v1`'s numpy import (B20_R70's disclosed
bias). BURER2002 runs as a separate process for the remaining budget (MQLib's -r, wall clock; the run is alone on a
pinned core). CP-SAT's eight workers share the one core, so its CPU equals its budget.

**Expectation, stated before running.** B20_R75's valid arms and the disclosed looks below suggest that neither
tool is fast at these budgets on these hosts: CP-SAT's portfolio reached 245 and 266 edges in 2 s on two B20_R66
hosts whose optima are 264 and 279–280, and BURER2002 reached 261, 279 and 266 on three. The builder expects the
system's engine to be X_FASTER than both, so SYSTEM_BEATS_SOTA, with simulated bifurcation faster still; and CP-SAT,
given 60 s, to claim optimality on few n63 hosts.

**Development looks.** On B20_R66 hosts only (evidence hosts, none of this study's), all disclosed in the B20_R76
record: CP-SAT with 1 and 8 workers at 0.1–2 s on three hosts and the worker comparison on two; the fixed BURER2002
at 0.5 s on three. No host of this study's seed has been drawn.

**What it decides.** Nothing about packages, rules or comparators. It answers B20_R75's question with the kinds
fixed and CP-SAT added.

**Status.** A DEV diagnostic. It licenses nothing.
"""
import json
import math
from pathlib import Path
import random
import resource
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import candidates as C1  # noqa: E402
from genesis import candidates_v2 as C2  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402
import b20r70_tts_scaling as R70  # noqa: E402

TF = RD.TF
SEED, PER_N, NS, REF_S, EXACT_S = 20267601, 6, (60, 63), 120, 60
P_IN, P_OUT = 0.8, 0.06
LADDER = (0.05, 0.1, 0.25, 0.5, 2.0)
REPS = 3
BOOT, BOOT_SEED, CAP = 4000, 20267699, 10.0
PROFILE = R11.PROFILE
ARMS = ('candidate', 'system', 'dsb', 'tabu', 'burer', 'cpsat', 'highs')
SOTAS = ('burer', 'cpsat')
PRIMARY = ('candidate', 'system')
SECONDARY = ('dsb', 'tabu', 'highs')
V2 = {'system': ('represent-search-v1', {'representation': 'cross_2', 'move': 'descent'}),
      'dsb': ('ising-dsb-v1', {}), 'tabu': ('maxcut-tabu-v1', {}), 'burer': ('mqlib-v1', {'heuristic': 'BURER2002'}),
      'cpsat': ('cpsat-v1', {}), 'highs': ('milp-highs-v1', {})}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01
EXACT = ('cpsat', 'highs')


def arm_descriptors():
    frozen = json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text())
    out = {}
    for t in LADDER:
        p = dict(frozen['parameters'], cpu_seconds=t)
        out[('candidate', t)] = ('v1', C1.build_descriptor(frozen['kind'], TF, p, **frozen['resource_profile']))
        for a, (kind, extra) in V2.items():
            out[(a, t)] = ('v2', C2.build_descriptor(kind, TF, dict(extra, cpu_seconds=t), **PROFILE))
    if out[('candidate', 0.5)][1]['descriptor_id'] != frozen['descriptor_id']:
        raise RuntimeError('the candidate at 0.5 s is not the frozen descriptor')
    if len({canonical(d['resource_profile']) for _, d in out.values()}) != 1:
        raise RuntimeError('the arms do not share one resource profile')
    for k, (reg, d) in out.items():
        if (C1 if reg == 'v1' else C2).descriptor_problems(d, domain=TF):
            raise RuntimeError(f'{k} does not rebuild')
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, seen = [], set(excluded)
    for i, n in enumerate(NS):
        ts, seen = R64.generate_beyond_space(SEED + 7919 * i, PER_N, 'DEV', {'n': n, 'p_in': P_IN, 'p_out': P_OUT}, seen)
        tasks += ts
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a host collides with an excluded identity')
    R11.dump(path, {'seed': SEED, 'per_n': PER_N, 'ns': list(NS), 'params': {'p_in': P_IN, 'p_out': P_OUT},
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def run_seed(task_id, arm, t, k):
    return int(digest({'study': 'b20r76', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


# ----------------------------------------------------------------------------------------------- Part B

def _exact_child(solver, path):
    """Child entry: solve one host exactly; print {'value', 'selected', 'claims_optimal'}."""
    task = GraphTask.model_validate_json(Path(path).read_text())
    E = [tuple(e) for e in task.edges]
    adj = {}
    for u, v in E:
        adj.setdefault(u, set()).add(v); adj.setdefault(v, set()).add(u)
    T = [(u, v, w) for u, v in E for w in sorted(adj[u] & adj[v]) if w > v]
    if solver == 'cpsat':
        from genesis.candidate_kinds import cpsat as K
        sys.path.insert(0, K.SOTA_DIR)
        from ortools.sat.python import cp_model
        m = cp_model.CpModel()
        x = {e: m.NewBoolVar(f'x{e[0]}_{e[1]}') for e in E}
        for u, v, w in T:
            m.Add(x[(u, v)] + x[(v, w)] + x[(u, w)] <= 2)
        m.Maximize(sum(x.values()))
        s = cp_model.CpSolver()
        s.parameters.num_workers = K.WORKERS
        s.parameters.max_time_in_seconds = EXACT_S
        st = s.Solve(m)
        sel = [list(e) for e in E if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) and s.Value(x[e])]
        out = {'value': len(sel), 'selected': sel, 'claims_optimal': st == cp_model.OPTIMAL}
    elif solver == 'highs':
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import lil_matrix
        ix = {e: i for i, e in enumerate(E)}
        A = lil_matrix((max(1, len(T)), len(E)))
        for j, (u, v, z) in enumerate(T):
            for e in ((u, v), (v, z), (u, z)):
                A[j, ix[e]] = 1
        res = milp(-np.ones(len(E)), constraints=LinearConstraint(A.tocsr(), -np.inf, 2),
                   integrality=np.ones(len(E)), bounds=Bounds(0, 1), options={'time_limit': EXACT_S})
        sel = [list(E[i]) for i in range(len(E)) if res.x is not None and res.x[i] > 0.5]
        out = {'value': len(sel), 'selected': sel, 'claims_optimal': bool(res.status == 0)}
    else:
        raise SystemExit(f'unknown solver {solver}')
    sys.stdout.write(json.dumps(out))


def exact(task, solver, tmp):
    """Run one exact solver in a child pinned to this core; value, claim, CPU and wall time, checked witness."""
    path = tmp / f'{task.task_id}.json'
    path.write_bytes(canonical(task.model_dump(mode='json')))
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--exact', solver, str(path)],
                           capture_output=True, text=True, timeout=EXACT_S + 5,
                           env={'PYTHONPATH': str(ROOT / 'src'), 'PATH': '/usr/bin:/bin', 'PYTHONHASHSEED': '0',
                                'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
        timed_out = False
    except subprocess.TimeoutExpired:
        p, timed_out = None, True
    wall = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
    if timed_out or p.returncode != 0:
        return {'status': 'TIMEOUT' if timed_out else 'ERROR', 'value': 0, 'claims_optimal': False,
                'cpu_s': round(cpu, 3), 'wall_s': round(wall, 3),
                'stderr_tail': None if timed_out else p.stderr[-300:]}, None
    out = json.loads(p.stdout)
    sel = [tuple(e) for e in out['selected']]
    chk = check_witness(task, sel)
    ok = isinstance(chk, dict) and chk.get('value') == out['value']
    return {'status': 'SUCCESS' if ok else 'BAD_WITNESS', 'value': out['value'] if ok else 0,
            'claims_optimal': bool(out['claims_optimal']) and ok, 'cpu_s': round(cpu, 3),
            'wall_s': round(wall, 3)}, (sel if ok else None)


# ----------------------------------------------------------------------------------------------- analysis

def host_tts(row, arm):
    target = row['target']
    best = (math.inf, None)
    for t in LADDER:
        runs = row['runs'][arm][str(t)]
        s = sum(r['run'] == 'SUCCESS' and r['value'] >= target for r in runs) / len(runs)
        v = R70.tts99(t, s)
        if v < best[0]:
            best = (v, t)
    return best[0], best[1], best[1] == LADDER[0] and best[0] == LADDER[0]


def pair_verdict(ci):
    lo, hi = ci
    if lo > 1:
        return 'X_FASTER'
    if hi < -1:
        return 'SOTA_FASTER'
    if -1 < lo and hi < 1:
        return 'COMPARABLE'
    return 'UNRESOLVED'


def boot_median(xs):
    rng = random.Random(BOOT_SEED)
    sims = sorted(statistics.median(rng.choice(xs) for _ in xs) for _ in range(BOOT))
    return statistics.median(xs), [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def analyse(rows):
    by_n = {}
    for n in NS:
        rs = [r for r in rows if r['n'] == n]
        T = {a: [host_tts(r, a) for r in rs] for a in ARMS}
        vs = {}
        for S in SOTAS:
            vs[S] = {}
            for x in PRIMARY + SECONDARY:
                rr = [R70.log_ratio(T[S][i][0], T[x][i][0]) for i in range(len(rs))]
                med, ci = boot_median(rr)
                vs[S][x] = {'median_log2_ratio_sota_over_x': round(med, 4),
                            'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                            'host_log2_ratios': [round(v, 4) for v in rr], 'verdict': pair_verdict(ci)}
        arms = {a: {'tts_median': R70._num(R70.quantile([x[0] for x in T[a]], 0.5)),
                    'tts_q75': R70._num(R70.quantile([x[0] for x in T[a]], 0.75)),
                    'solved': sum(not math.isinf(x[0]) for x in T[a]), 'floors': sum(x[2] for x in T[a]),
                    'optimal_t': [x[1] for x in T[a]]} for a in ARMS}
        exact_ = {}
        for s in EXACT:
            e = [r['exact'][s] for r in rs]
            claimed = [x for x in e if x['claims_optimal']]
            exact_[s] = {'claims_optimal': len(claimed), 'reaches_target': sum(x['value'] == r['target'] for x, r in zip(e, rs)),
                         'cpu_s_median_when_claimed': round(statistics.median(x['cpu_s'] for x in claimed), 3) if claimed else None,
                         'timeouts': sum(x['status'] == 'TIMEOUT' for x in e)}
        ref = [r['reference'] for r in rs]
        exact_['generated_rows_reference'] = {'certified': sum(r['target_certified'] for r in rs),
                                              'wall_s_median': round(statistics.median(x['wall_s'] for x in ref), 3)}
        by_n[str(n)] = {'hosts': len(rs), 'edges': [min(r['edges'] for r in rs), max(r['edges'] for r in rs)] if rs else None,
                        'certified': sum(r['target_certified'] for r in rs), 'versus_sota': vs, 'arms': arms,
                        'exact': exact_}
    return by_n


def validity(rows):
    cpu = {a: statistics.median(r['cpu_ns'][a]['0.5'] for r in rows) / 1e9 for a in ARMS}
    runs = {a: [x for r in rows for t in LADDER for x in r['runs'][a][str(t)]] for a in ARMS}
    fail = {a: sum(x['run'] != 'SUCCESS' for x in runs[a]) / len(runs[a]) for a in ARMS}
    if any(cpu[a] < MIN_CPU_AT_HALF for a in ARMS):
        return 'INVALID_CPU_DELIVERY', cpu, fail
    if any(fail[a] > MAX_FAIL_SHARE for a in ARMS):
        return 'INVALID_FAILURES', cpu, fail
    return None, cpu, fail


def overall(by_n, invalid):
    if invalid:
        return invalid
    v = [by_n[str(NS[-1])]['versus_sota'][S]['system']['verdict'] for S in SOTAS]
    if all(x == 'X_FASTER' for x in v):
        return 'SYSTEM_BEATS_SOTA'
    if any(x == 'SOTA_FASTER' for x in v):
        return 'SOTA_BEATS_SYSTEM'
    if all(x == 'COMPARABLE' for x in v):
        return 'SYSTEM_MATCHES_SOTA'
    return 'UNRESOLVED'


# ----------------------------------------------------------------------------------------------- run

def main(argv=None):
    argv = argv or sys.argv[1:]
    if argv and argv[0] == '--exact':
        _exact_child(argv[1], argv[2])
        return 0
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='b20r76-'))          # outside the evidence tree and its exposure walk
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    from genesis.verification.tools import tool
    from genesis.candidate_kinds import cpsat as K, mqlib as MQ
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim'))
        + f'; MQLib {MQ.BINARY} sha256 {MQ.binary_digest()[:16]} (commit {MQ.SOURCE["commit"][:7]})'
        + f'; OR-Tools tree {K.SOTA_DIR} sha256 {K.tree_digest()[:16]} {K.SOTA_PACKAGES} workers {K.WORKERS}')
    D = arm_descriptors()
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
            for s in EXACT:
                ex[s], sel = exact(task, s, tmp)
                if sel is not None and ex[s]['value'] > best[1]:
                    best = (sel, ex[s]['value'])
            ref, opt = R41.reference(task, [('best', best[0])], registry, REF_S)
            target = max(best[1], ref['lower'])
            certified = ref['upper'] == target
            r = {'task_id': task.task_id, 'n': task.n, 'split': task.split, 'edges': len(task.edges), 'runs': runs,
                 'cpu_ns': cpu_ns, 'exact': ex, 'reference': ref, 'target': target, 'target_certified': certified,
                 'best_witness_value': best[1]}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            tts = {a: host_tts(r, a) for a in ARMS}
            log(f'n{task.n} {task.task_id[-4:]} ({len(task.edges)} edges) target {target}'
                f'{"" if certified else " (uncertified)"}: ' + ' '.join(f'{a} {tts[a][0]:.3g}' for a in ARMS)
                + ' | exact ' + ' '.join(f'{s} {ex[s]["value"]}{"*" if ex[s]["claims_optimal"] else ""}'
                                         f'@{ex[s]["cpu_s"]:.1f}s' for s in ex) + f' | ref {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    invalid, cpu_half, fail = validity(rows)
    by_n = analyse(rows)
    summary = {'schema': 'genesis-b20r76-sota-v1', 'verdict': overall(by_n, invalid),
               'largest_n_versus_sota': {S: {x: by_n[str(NS[-1])]['versus_sota'][S][x]['verdict'] for x in PRIMARY + SECONDARY}
                                         for S in SOTAS},
               'by_n': by_n,
               'validity': {'cpu_s_median_at_0.5': {a: round(v, 3) for a, v in cpu_half.items()},
                            'failure_share': {a: round(v, 5) for a, v in fail.items()}},
               'descriptors': {f'{a}@{t}': d['descriptor_id'] for (a, t), (_, d) in D.items()},
               'mqlib': {'binary': MQ.BINARY, 'sha256': MQ.binary_digest(), 'source': MQ.SOURCE},
               'ortools': {'dir': K.SOTA_DIR, 'sha256': K.tree_digest(), 'packages': K.SOTA_PACKAGES,
                           'wheels': K.WHEELS, 'workers': K.WORKERS},
               'ladder': list(LADDER), 'reps': REPS, 'seeds': {'hosts': SEED, 'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV comparison with state-of-the-art tools; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {summary['verdict']}; n63 vs state of the art {summary['largest_n_versus_sota']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
