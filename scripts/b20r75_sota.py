#!/usr/bin/env python3
"""B20_R75: E1d's candidate and the system's best engine against state-of-the-art tools (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r75_sota.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** A speed or quality claim must hold against the best *known* methods (Rønnow et al. 2014; Dunning et al.
2018). B20_R68 and R70 compared E1d's candidate with domain heuristics; Daniel asked (19 Oct 2026) for the most
advanced tools as well. The best single max-cut heuristic in the largest independent comparison (37 heuristics,
3,296 instances, identical termination criteria; Dunning, Gupta and Silberholz 2018) is BURER2002, the rank-two
relaxation heuristic of Burer, Monteiro and Zhang; B20_R74 built it from MQLib at a pinned commit (`mqlib-v1`).
B20_R70's fastest method was discrete simulated bifurcation. Google OR-Tools CP-SAT (gold in the MiniZinc
Challenge 2025) and the MaxSAT solver RC2 were also planned, but PyPI was not reachable from this workspace (the
egress proxy refused it); they are left for a follow-up if their wheels are supplied, and this study does not
claim to cover them. This study puts the system against BURER2002, dSB, tabu search and HiGHS at n60 and at n63, the
largest size the domain's task model accepts, on two questions: how fast does each method reach the best known value (Part A), and how fast can an
exact method prove it optimal (Part B)?

**Design (fixed before running).**
  * **Hosts.** planted_cluster (p_in 0.8, p_out 0.06), 6 fresh DEV hosts at n60 and 6 at n63 (seed 20267501), drawn
    by `b20r64_e1d_scaling.generate_beyond_space`, excluding every identity `b20r24_repilots.exposure` excludes.
  * **Part A, anytime, all in runc under E1's profile** (2 CPU s, 2048 MiB, 10 s wall), at each run time t in
    (0.05, 0.1, 0.25, 0.5, 2.0) CPU s, REPS = 3 seeds per (host, arm, t):
      - `candidate`: E1d's frozen kind and parameters with `cpu_seconds` = t;
      - `system`: the system's best engine, `represent-search-v1` {cross_2, descent} (B20_R72: the frozen rule with
        the faster repair);
      - `dsb`: `ising-dsb-v1`; `tabu`: `maxcut-tabu-v1`;
      - `burer`: `mqlib-v1` {BURER2002} (B20_R74), the best single max-cut heuristic of Dunning et al.;
      - `highs`: `milp-highs-v1` (E1d's exact comparator).
  * **Part B, exact, on the pinned core** (descriptive): HiGHS (scipy milp) in a child process with a 60 s limit,
    whose claim of optimality is reported as a claim; and the system's own certification route, B20_R41's
    generated-rows reference (exact LP dual plus SAT/DRAT with CaDiCaL and drat-trim, 120 s), the only route with
    a checked certificate. Each records value, whether it claims or certifies optimality, and its time.
  * **Target per host.** The best value of any witness from Parts A and B (every witness is re-checked by the domain
    checker), certified when the reference's checked upper bound equals it.
  * **Primary endpoint** (as B20_R70): per size, r = log2(TTS*_burer / TTS*_x) per host for x in (candidate,
    system), TTS* at the optimal run time, infinite where never reached (±10 caps); the median over hosts with a
    bootstrap 90% interval (4,000 resamples, seed 20267599). Verdict per (n, x): X_FASTER (lower end > 1),
    SOTA_FASTER (upper end < −1), COMPARABLE (inside (−1, 1)), UNRESOLVED.
  * **Overall (at the largest size, n63):** SYSTEM_BEATS_SOTA if `system` is X_FASTER than BURER2002; SOTA_BEATS_SYSTEM if
    SOTA_FASTER;
    SYSTEM_MATCHES_SOTA if COMPARABLE; else UNRESOLVED. Validity first: INVALID_CPU_DELIVERY if any Part A arm's
    median cgroup CPU at t = 0.5 is below 0.45 s; INVALID_FAILURES if more than 1% of an arm's runs failed.
  * **Secondary, descriptive:** the same ratio for dSB, tabu and HiGHS against BURER2002; median and 75th-percentile
    TTS* per arm; Part B proof rates and times; certified targets.

**Start-up.** Every arm's budget starts after its imports, except `ising-dsb-v1`, whose numpy import counts against
its budget (B20_R70's disclosed bias, kept so that the kind is unchanged). BURER2002 runs as a separate process
for the remaining budget (MQLib's -r, a wall-clock limit; the run is alone on a pinned core).

**Expectation, stated before running.** BURER2002 optimizes the cut, not the repaired subgraph, and returns one
best cut per run, so the builder expects it to be no faster than dSB, and comparable with or slower than the
system's engine: overall SYSTEM_MATCHES_SOTA or UNRESOLVED at n63. HiGHS proves few n63 hosts within 60 s; the
generated-rows reference certifies fewer hosts at n63 than at n60.

**Amendment, before any arm ran (disclosed).** As first committed (`fc8f950`) the design named n80. The domain's task
model caps hosts at 63 vertices (`models.GraphTask.n <= 63`, part of every identity), so the first run stopped while
drawing the n80 hosts: no host was saved and no arm ran (its log is kept in `run1_stopped/`). The larger size is now
n63, the largest the model accepts; nothing else changed.

**Development looks.** One, disclosed in the B20_R74 record: BURER2002 at 0.1 and 0.5 s in process on the first
three B20_R66 hosts gave 261, 279, 266 (dSB in B20_R69's look: 264, 280, 267). No host of this study's seed has
been drawn.

**What it decides.** Nothing about packages, rules or comparators. It answers how the system and its best
discovery fare against the most advanced tools available, for the reviewer's strong-baseline decision.

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
SEED, PER_N, NS, REF_S, EXACT_S = 20267501, 6, (60, 63), 120, 60
P_IN, P_OUT = 0.8, 0.06
LADDER = (0.05, 0.1, 0.25, 0.5, 2.0)
REPS = 3
BOOT, BOOT_SEED, CAP = 4000, 20267599, 10.0
PROFILE = R11.PROFILE
ARMS = ('candidate', 'system', 'dsb', 'tabu', 'burer', 'highs')
SOTA = 'burer'
PRIMARY = ('candidate', 'system')
SECONDARY = ('dsb', 'tabu', 'highs')
V2 = {'system': ('represent-search-v1', {'representation': 'cross_2', 'move': 'descent'}),
      'dsb': ('ising-dsb-v1', {}), 'tabu': ('maxcut-tabu-v1', {}), 'burer': ('mqlib-v1', {'heuristic': 'BURER2002'}),
      'highs': ('milp-highs-v1', {})}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01
EXACT = ('highs',)


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
    return int(digest({'study': 'b20r75', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


# ----------------------------------------------------------------------------------------------- Part B

def _exact_child(solver, path):
    """Child entry: solve one host exactly; print {'value', 'selected', 'claims_optimal'}."""
    task = GraphTask.model_validate_json(Path(path).read_text())
    E = [tuple(e) for e in task.edges]
    adj = {}
    for u, v in E:
        adj.setdefault(u, set()).add(v); adj.setdefault(v, set()).add(u)
    T = [(u, v, w) for u, v in E for w in sorted(adj[u] & adj[v]) if w > v]
    if solver == 'highs':
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
        for x in PRIMARY + SECONDARY:
            rr = [R70.log_ratio(T[SOTA][i][0], T[x][i][0]) for i in range(len(rs))]
            med, ci = boot_median(rr)
            vs[x] = {'median_log2_ratio_sota_over_x': round(med, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
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


OVERALL = {'X_FASTER': 'SYSTEM_BEATS_SOTA', 'SOTA_FASTER': 'SOTA_BEATS_SYSTEM', 'COMPARABLE': 'SYSTEM_MATCHES_SOTA'}


def overall(by_n, invalid):
    if invalid:
        return invalid
    return OVERALL.get(by_n[str(NS[-1])]['versus_sota']['system']['verdict'], 'UNRESOLVED')


# ----------------------------------------------------------------------------------------------- run

def main(argv=None):
    argv = argv or sys.argv[1:]
    if argv and argv[0] == '--exact':
        _exact_child(argv[1], argv[2])
        return 0
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='b20r75-'))          # outside the evidence tree and its exposure walk
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
    from genesis.candidate_kinds import mqlib as MQ
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim'))
        + f'; MQLib {MQ.BINARY} sha256 {MQ.binary_digest()[:16]} (commit {MQ.SOURCE["commit"][:7]})')
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
    summary = {'schema': 'genesis-b20r75-sota-v1', 'verdict': overall(by_n, invalid),
               'largest_n_versus_sota': {x: by_n[str(NS[-1])]['versus_sota'][x]['verdict'] for x in PRIMARY + SECONDARY},
               'by_n': by_n,
               'validity': {'cpu_s_median_at_0.5': {a: round(v, 3) for a, v in cpu_half.items()},
                            'failure_share': {a: round(v, 5) for a, v in fail.items()}},
               'descriptors': {f'{a}@{t}': d['descriptor_id'] for (a, t), (_, d) in D.items()},
               'mqlib': {'binary': MQ.BINARY, 'sha256': MQ.binary_digest(), 'source': MQ.SOURCE},
               'ladder': list(LADDER), 'reps': REPS, 'seeds': {'hosts': SEED, 'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV comparison with state-of-the-art tools; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {summary['verdict']}; n63 vs BURER2002 {summary['largest_n_versus_sota']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
