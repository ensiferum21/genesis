#!/usr/bin/env python3
"""B20_R77: the system's new engine against CP-SAT and BURER2002, powered (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r77_engine_vs_sota.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** B20_R76's comparison with the state of the art was UNRESOLVED on 6 hosts per size. Two things were learned
from it. (1) Its statistic, the median over hosts of capped per-host log ratios, has almost no power when each
method fails on some hosts: those hosts give ±10 or ties at 0, and the median swings between them. (2) Every fast
arm stopped short of the optimum on the hardest host, because a search over cuts cannot reach an optimum that is not
a cut plus a completion (the diagnosis is in `hybrid_swap.py` and the B20_R77 record). The builder wrote a new kind,
`hybrid-swap-v1` (a portfolio of simulated bifurcation and one-flip descent, then (1,2)-swap iterated local search
on the problem itself). This study compares it with both tools on four times as many hosts, at the largest size.

**Design (fixed before running).**
  * **Hosts.** planted_cluster (p_in 0.8, p_out 0.06), 24 fresh DEV hosts at n63 (the task model's maximum), seed
    20267711, drawn by `b20r64_e1d_scaling.generate_beyond_space`, excluding every identity
    `b20r24_repilots.exposure` excludes (B20_R76's hosts, on which the engine was developed, included).
  * **Part A, anytime, all in runc under E1's profile** (2 CPU s, 2048 MiB, 10 s wall), run times t in
    (0.05, 0.1, 0.25, 0.5, 2.0) CPU s, REPS = 3 seeds per (host, arm, t):
      - `engine`: `hybrid-swap-v1` (new, B20_R77);
      - `system`: `represent-search-v1` {cross_2, descent} (B20_R76's system arm);
      - `dsb`: `ising-dsb-v1`; `tabu`: `maxcut-tabu-v1`; `candidate`: E1d's frozen kind and parameters;
      - `burer`: `mqlib-v1` {BURER2002}; `cpsat`: `cpsat-v1` (8 workers on the child's one core).
    HiGHS run anytime is dropped: in B20_R75 and B20_R76 it never reached the target within 2 s (0 of 24 hosts).
  * **Part B, on the pinned core:** CP-SAT with 60 s (B20_R76's exact child), whose claims of optimality are reported
    as claims; and the generated-rows reference (exact LP dual plus SAT/DRAT, 120 s), the checked route.
  * **Target per host.** The best value of any checked witness from Parts A and B, certified when the reference's
    checked upper bound equals it.
  * **TTS\*** per (host, arm): TTS99 = t ⌈ln 0.01 / ln(1 − s)⌉ at the best rung (s = the share of the 3 runs that
    reach the target), infinite if no rung reaches it (B20_R70).
  * **Primary endpoint (Rønnow et al. 2014, "speedup of quantiles").** For tool S in (burer, cpsat) and q in
    (0.5, 0.75): r(S, q) = log2(TTS*_S(q) / TTS*_engine(q)), TTS*(q) the nearest-rank q-quantile over the 24 hosts
    (infinite values last), capped at ±10 (both infinite: 0). 90% interval: bootstrap over hosts, paired (the same
    resampled hosts for both arms), 4,000 resamples, seed 20267799. Verdict per (S, q): ENGINE_FASTER (lower end
    > 1, i.e. more than twice as fast), SOTA_FASTER (upper end < −1), COMPARABLE (inside (−1, 1)), UNRESOLVED.
    Why this statistic and not B20_R76's: chosen after B20_R76, for reason (1) above; Rønnow et al. define both,
    and B20_R76's is kept as a secondary, so a disagreement between them is visible.
  * **Overall:** ENGINE_BEATS_SOTA if ENGINE_FASTER against both tools at both quantiles; SOTA_BEATS_ENGINE if
    SOTA_FASTER against either tool at either quantile; ENGINE_MATCHES_SOTA if COMPARABLE in all four; MIXED
    otherwise. Validity first: INVALID_CPU_DELIVERY if any arm's median cgroup CPU at t = 0.5 is below 0.45 s;
    INVALID_FAILURES if more than 1% of an arm's runs failed.
  * **Secondary, descriptive:** the same quantile ratios for system, dsb, tabu and candidate against both tools, and
    for the engine against system and dsb (did the new engine improve the system?); B20_R76's statistic (median
    over hosts of the per-host ratio, bootstrap over hosts, same seed) for every pair; per arm, hosts reached within
    2 s and the median and 75th-percentile TTS*; Part B claims, CP-SAT's values and the certified targets.

**Start-up.** Every arm's budget starts after its imports, except numpy's import in `ising-dsb-v1` and
`hybrid-swap-v1` (B20_R70's disclosed bias, against them). BURER2002 runs as a separate process for the remaining
budget (wall clock; the run is alone on a pinned core). CP-SAT's eight workers share the one core.

**Expectation, stated before running.** From B20_R76 (CP-SAT anytime reached no target within 2 s) and the
development looks: ENGINE_FASTER than CP-SAT at both quantiles; against BURER2002, ENGINE_FASTER at q = 0.75 (it
reached the target on 5 of 12 B20_R76 hosts, so its 75th percentile is likely infinite), unsure at q = 0.5, where
BURER2002 is fast on the hosts it solves. Overall the builder expects ENGINE_BEATS_SOTA or MIXED, MIXED slightly more
likely. The engine should also be faster than the system's B20_R76 engine and than dSB at q = 0.75.

**Development looks.** The engine was designed on B20_R76's 12 hosts only (evidence hosts, none of this study's),
disclosed in the record: the structure of CP-SAT's optimum on the hardest one, an edge-space annealing (worse),
(1,2)-swap ILS from dSB, the portfolio with descent, at 0.5 and 2 s. No host of this study's seed has been drawn.

**What it decides.** Nothing about packages, rules or comparators. **Status.** A DEV diagnostic; licenses nothing.
"""
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

from genesis import candidates as C1  # noqa: E402
from genesis import candidates_v2 as C2  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
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
SEED, PER_N, N, REF_S = 20267711, 24, 63, 120
P_IN, P_OUT = 0.8, 0.06
LADDER, REPS = R76.LADDER, 3
BOOT, BOOT_SEED, CAP = 4000, 20267799, 10.0
QS = (0.5, 0.75)
PROFILE = R11.PROFILE
ARMS = ('engine', 'system', 'dsb', 'tabu', 'candidate', 'burer', 'cpsat')
SOTAS = ('burer', 'cpsat')
SECONDARY = ('system', 'dsb', 'tabu', 'candidate')
IMPROVEMENT = ('system', 'dsb')
V2 = {'engine': ('hybrid-swap-v1', {}),
      'system': ('represent-search-v1', {'representation': 'cross_2', 'move': 'descent'}),
      'dsb': ('ising-dsb-v1', {}), 'tabu': ('maxcut-tabu-v1', {}), 'burer': ('mqlib-v1', {'heuristic': 'BURER2002'}),
      'cpsat': ('cpsat-v1', {})}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01
assert LADDER == (0.05, 0.1, 0.25, 0.5, 2.0)


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
    tasks, _ = R64.generate_beyond_space(SEED, PER_N, 'DEV', {'n': N, 'p_in': P_IN, 'p_out': P_OUT}, set(excluded))
    if len(tasks) != PER_N or RD.identities(tasks) & set(excluded):
        raise RuntimeError('host drawing failed or collides with an excluded identity')
    R11.dump(path, {'seed': SEED, 'per_n': PER_N, 'n': N, 'params': {'p_in': P_IN, 'p_out': P_OUT},
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def run_seed(task_id, arm, t, k):
    return int(digest({'study': 'b20r77', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


# ----------------------------------------------------------------------------------------------- analysis

def tts_star(rows, arm):
    return [R76.host_tts(r, arm)[0] for r in rows]


def quantile_ratio(ts, tx, q):
    return R70.log_ratio(R70.quantile(ts, q), R70.quantile(tx, q))


def boot(stat, k, seed=BOOT_SEED):
    """The statistic on the hosts and its paired bootstrap 90% interval (hosts resampled with replacement)."""
    rng = random.Random(seed)
    sims = sorted(stat([rng.randrange(k) for _ in range(k)]) for _ in range(BOOT))
    return stat(list(range(k))), [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def verdict(ci):
    lo, hi = ci
    if lo > 1:
        return 'ENGINE_FASTER'
    if hi < -1:
        return 'SOTA_FASTER'
    if -1 < lo and hi < 1:
        return 'COMPARABLE'
    return 'UNRESOLVED'


def _pair(T, s, x):
    out = {}
    for q in QS:
        est, ci = boot(lambda ix, q=q: quantile_ratio([T[s][i] for i in ix], [T[x][i] for i in ix], q), len(T[s]))
        out[f'q{q}'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                        'verdict': verdict(ci)}
    per_host = [R70.log_ratio(a, b) for a, b in zip(T[s], T[x])]
    est, ci = boot(lambda ix: statistics.median(per_host[i] for i in ix), len(per_host))
    out['b20r76_per_host_median'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                                     'verdict': verdict(ci), 'host_log2_ratios': [round(v, 4) for v in per_host]}
    return out


def analyse(rows):
    T = {a: tts_star(rows, a) for a in ARMS}
    primary = {S: _pair(T, S, 'engine') for S in SOTAS}
    secondary = {S: {x: _pair(T, S, x) for x in SECONDARY} for S in SOTAS}
    improvement = {x: _pair(T, x, 'engine') for x in IMPROVEMENT}
    arms = {a: {'reached_within_2s': sum(not math.isinf(v) for v in T[a]),
                'tts_median': R70._num(R70.quantile(T[a], 0.5)), 'tts_q75': R70._num(R70.quantile(T[a], 0.75)),
                'success_share_at_2s': round(statistics.mean(
                    sum(x['run'] == 'SUCCESS' and x['value'] >= r['target'] for x in r['runs'][a]['2.0']) / REPS
                    for r in rows), 4) if rows else None}
            for a in ARMS}
    e = [r['exact']['cpsat'] for r in rows]
    exact = {'cpsat_60s': {'claims_optimal': sum(x['claims_optimal'] for x in e),
                           'reaches_target': sum(x['value'] == r['target'] for x, r in zip(e, rows)),
                           'timeouts': sum(x['status'] == 'TIMEOUT' for x in e),
                           'short_of_target': sorted(r['target'] - x['value'] for x, r in zip(e, rows))},
             'generated_rows_reference': {'certified': sum(r['target_certified'] for r in rows),
                                          'wall_s_median': round(statistics.median(r['reference']['wall_s'] for r in rows), 3)
                                          if rows else None}}
    return {'hosts': len(rows), 'edges': [min(r['edges'] for r in rows), max(r['edges'] for r in rows)] if rows else None,
            'certified': sum(r['target_certified'] for r in rows), 'primary': primary, 'secondary': secondary,
            'improvement': improvement, 'arms': arms, 'exact': exact}


def validity(rows):
    cpu = {a: statistics.median(r['cpu_ns'][a]['0.5'] for r in rows) / 1e9 for a in ARMS}
    runs = {a: [x for r in rows for t in LADDER for x in r['runs'][a][str(t)]] for a in ARMS}
    fail = {a: sum(x['run'] != 'SUCCESS' for x in runs[a]) / len(runs[a]) for a in ARMS}
    if any(cpu[a] < MIN_CPU_AT_HALF for a in ARMS):
        return 'INVALID_CPU_DELIVERY', cpu, fail
    if any(fail[a] > MAX_FAIL_SHARE for a in ARMS):
        return 'INVALID_FAILURES', cpu, fail
    return None, cpu, fail


def overall(analysis, invalid):
    if invalid:
        return invalid
    v = [analysis['primary'][S][f'q{q}']['verdict'] for S in SOTAS for q in QS]
    if all(x == 'ENGINE_FASTER' for x in v):
        return 'ENGINE_BEATS_SOTA'
    if any(x == 'SOTA_FASTER' for x in v):
        return 'SOTA_BEATS_ENGINE'
    if all(x == 'COMPARABLE' for x in v):
        return 'ENGINE_MATCHES_SOTA'
    return 'MIXED'


# ----------------------------------------------------------------------------------------------- run

def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='b20r77-'))          # outside the evidence tree and its exposure walk
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
            ex['cpsat'], sel = R76.exact(task, 'cpsat', tmp)
            if sel is not None and ex['cpsat']['value'] > best[1]:
                best = (sel, ex['cpsat']['value'])
            ref, opt = R41.reference(task, [('best', best[0])], registry, REF_S)
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
                + f' | cpsat-60s {ex["cpsat"]["value"]}{"*" if ex["cpsat"]["claims_optimal"] else ""}'
                + f' | ref {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    invalid, cpu_half, fail = validity(rows)
    a = analyse(rows)
    summary = {'schema': 'genesis-b20r77-engine-vs-sota-v1', 'verdict': overall(a, invalid),
               'primary_verdicts': {S: {f'q{q}': a['primary'][S][f'q{q}']['verdict'] for q in QS} for S in SOTAS},
               **a,
               'validity': {'cpu_s_median_at_0.5': {k: round(v, 3) for k, v in cpu_half.items()},
                            'failure_share': {k: round(v, 5) for k, v in fail.items()}},
               'descriptors': {f'{x}@{t}': d['descriptor_id'] for (x, t), (_, d) in D.items()},
               'mqlib': {'binary': MQ.BINARY, 'sha256': MQ.binary_digest(), 'source': MQ.SOURCE},
               'ortools': {'dir': K.SOTA_DIR, 'sha256': K.tree_digest(), 'packages': K.SOTA_PACKAGES,
                           'wheels': K.WHEELS, 'workers': K.WORKERS},
               'ladder': list(LADDER), 'reps': REPS, 'quantiles': list(QS), 'seeds': {'hosts': SEED, 'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV comparison with state-of-the-art tools; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {summary['verdict']}; primary {summary['primary_verdicts']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
