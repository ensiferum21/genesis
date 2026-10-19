#!/usr/bin/env python3
"""B20_R70: time-to-solution scaling of E1d's candidate against three domain heuristics (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r70_tts_scaling.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** E1d's evidence fixes the candidate's budget at 0.5 s for every host size and asks which comparator
budget catches it (B20_R63, R64, R66, R68). Benchmarking of quantum annealers (Rønnow et al., Science 2014) showed
that a fixed run time at every size can fake or hide a scaling advantage, and that speed comparisons must use
time-to-solution TTS99 = t · ceil(ln 0.01 / ln(1 − s)) at the *optimal* run time t for each size and instance,
read at quantiles of instance hardness. B20_R68 found a standard max-cut tabu search tying the candidate on the
calibrated settings and ahead at n60, at one budget. This study asks the scaling question properly, against three
domain heuristics: tabu search (B20_R67) and the two physics-inspired kinds of B20_R69, discrete simulated
bifurcation and τ-extremal optimization (docs/PHYSICS_INSPIRED_PLAN.md, idea 1).

**Design (fixed before running).**
  * **Hosts.** planted_cluster (p_in 0.8, p_out 0.06) at n = 40, 50 and 60, 8 fresh DEV hosts each (seed 20267001),
    drawn by `b20r64_e1d_scaling.generate_beyond_space` (equal to the adapter inside the family space; n50 and
    n60 lie beyond it and the 200-edge bound), excluding every identity `b20r24_repilots.exposure` excludes (all
    earlier hosts, B20_R68's included). Hosts are saved before anything runs and reloaded on resume.
  * **Arms**, all in runc under E1's profile (2 CPU s, 2048 MiB, 10 s wall, 1000 queries), each at every run time
    t in the ladder (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0) CPU s, REPS = 4 seeds per (host, arm, t):
      - `candidate`: E1's frozen kind and parameters (`represent-and-repair-v1`, `cross_2`, seed 0), with
        `cpu_seconds` = t (at t = 0.5 it is exactly the package's frozen descriptor, checked by id);
      - `tabu`: `maxcut-tabu-v1`; `dsb`: `ising-dsb-v1`; `eo`: `maxcut-eo-v1`, each with `cpu_seconds` = t.
    Each run's seed is derived from (study, task, arm, t, repetition); run order is host by host, arm by arm.
  * **Target per host.** After its 112 runs, B20_R41's generated-rows reference at 120 s, seeded with the best
    witness of all runs. The target is the certified optimum where it certifies, else the best value known (the
    reference's lower bound, at least every run's value); uncertified targets are flagged.
  * **TTS.** s(t) = successes / REPS (a success reaches the target; a failed run is not a success). TTS99(t) =
    t if s = 1, t · ceil(ln 0.01 / ln(1 − s)) if 0 < s < 1, infinite if s = 0. TTS* per (host, arm) is the minimum
    over the ladder (the optimal run time); a TTS* whose optimal t is the ladder's first rung with s = 1 is a
    *floor* (an upper bound; the optimum is not resolved there).
  * **Primary endpoint, per size and heuristic H.** r = log2(TTS*_H / TTS*_candidate) per host (both infinite: 0;
    only one infinite: ±10, the cap; finite values clipped to ±10). The median of r over the 8 hosts, with a
    bootstrap 90% percentile interval over hosts (4,000 resamples, seed 20267099). Verdict per (n, H):
      - CANDIDATE_FASTER: lower end > 1 (the heuristic needs more than twice the candidate's TTS);
      - HEURISTIC_FASTER: upper end < −1;
      - COMPARABLE: the whole interval inside (−1, 1);
      - UNRESOLVED: anything else.
  * **Overall verdict (at n60):** E1D_FASTER_THAN_ALL if CANDIDATE_FASTER against all three;
    E1D_SLOWER_THAN_SOME if HEURISTIC_FASTER against at least one; E1D_COMPARABLE if COMPARABLE against all;
    UNRESOLVED otherwise. Validity is checked first: INVALID_CPU_DELIVERY if any arm's median cgroup CPU at t = 0.5
    is below 0.45 s; INVALID_FAILURES if more than 1% of an arm's runs failed.
  * **Secondary, descriptive, never decisive:** per (n, arm) the median and 75th-percentile TTS* (Rønnow's
    "ratio of quantiles"), the optimal t, floors, solved hosts (TTS* finite); the scaling slope of log10 of the
    median TTS* against n where all three medians are finite; certified targets per size.

**Expectation, stated before running.** At n40 every arm solves every host at the ladder's floor or near it, so
COMPARABLE throughout, with floors. At n60 B20_R68 found the candidate optimal on 3 of 13 certified hosts at 0.5 s
against tabu's 7, and a disclosed development look (below) found dSB optimal on 3 of 3 hosts, so the builder
expects HEURISTIC_FASTER against tabu and dSB, the overall verdict E1D_SLOWER_THAN_SOME, and steeper TTS scaling
for the candidate than for the best heuristic.

**Development looks.** One, disclosed in the B20_R69 record: tabu, dSB and EO at 0.5 s, in process, on the first
three B20_R66 hosts (evidence hosts, none of this study's): tabu 263/279/266, dSB 264/280/267, EO 263/279/266, the
candidate 262/279/266. No host of this study's seed has been drawn, and no ladder run of any arm has been made.

**What it decides.** Nothing about packages, rules or comparators. It gives E1d's speed claim the form a speed
claim needs (scaling of TTS at optimal run times against the best-known methods) and informs the reviewer's
strong-baseline decision (review brief item 1).

**Status.** A DEV diagnostic. It licenses nothing.
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

TF = RD.TF
SEED, PER_N, NS, REF_S = 20267001, 8, (40, 50, 60), 120
P_IN, P_OUT = 0.8, 0.06
LADDER = (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0)
REPS = 4
BOOT, BOOT_SEED = 4000, 20267099
CAP = 10.0
PROFILE = R11.PROFILE
ARMS = ('candidate', 'tabu', 'dsb', 'eo')
HEURISTICS = ('tabu', 'dsb', 'eo')
V2_KIND = {'tabu': 'maxcut-tabu-v1', 'dsb': 'ising-dsb-v1', 'eo': 'maxcut-eo-v1'}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01


def arm_descriptors():
    """{(arm, t): (registry, descriptor)} for every arm and rung; the candidate at 0.5 s is the package's."""
    frozen = json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text())
    out = {}
    for t in LADDER:
        p = dict(frozen['parameters'], cpu_seconds=t)
        out[('candidate', t)] = ('v1', C1.build_descriptor(frozen['kind'], TF, p, **frozen['resource_profile']))
        for a, kind in V2_KIND.items():
            out[(a, t)] = ('v2', C2.build_descriptor(kind, TF, {'cpu_seconds': t}, **PROFILE))
    if out[('candidate', 0.5)][1]['descriptor_id'] != frozen['descriptor_id']:
        raise RuntimeError('the candidate at 0.5 s is not the frozen descriptor')
    profiles = {canonical(d['resource_profile']) for _, d in out.values()}
    if len(profiles) != 1:
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
    return int(digest({'study': 'b20r70', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


# ----------------------------------------------------------------------------------------------- analysis

def tts99(t, s):
    if s <= 0:
        return math.inf
    if s >= 1:
        return t
    return t * math.ceil(math.log(0.01) / math.log(1 - s))


def host_tts(row, arm):
    """(TTS*, optimal t, floor?) for one host and arm."""
    target = row['target']
    best = (math.inf, None)
    for t in LADDER:
        runs = row['runs'][arm][str(t)]
        s = sum(r['run'] == 'SUCCESS' and r['value'] >= target for r in runs) / len(runs)
        v = tts99(t, s)
        if v < best[0]:
            best = (v, t)
    floor = best[1] == LADDER[0] and best[0] == LADDER[0]
    return best[0], best[1], floor


def log_ratio(h, c):
    if math.isinf(h) and math.isinf(c):
        return 0.0
    if math.isinf(h):
        return CAP
    if math.isinf(c):
        return -CAP
    return max(-CAP, min(CAP, math.log2(h / c)))


def boot_median(xs):
    rng = random.Random(BOOT_SEED)
    sims = sorted(statistics.median(rng.choice(xs) for _ in xs) for _ in range(BOOT))
    return statistics.median(xs), [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def pair_verdict(ci):
    lo, hi = ci
    if lo > 1:
        return 'CANDIDATE_FASTER'
    if hi < -1:
        return 'HEURISTIC_FASTER'
    if -1 < lo and hi < 1:
        return 'COMPARABLE'
    return 'UNRESOLVED'


def quantile(xs, q):
    """The q-quantile (nearest rank, infinite values last)."""
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))]


def _num(x):
    return None if math.isinf(x) else round(x, 4)


def analyse(rows):
    by_n = {}
    for n in NS:
        rs = [r for r in rows if r['n'] == n]
        T = {a: [host_tts(r, a) for r in rs] for a in ARMS}
        per_h = {}
        for h in HEURISTICS:
            rr = [log_ratio(T[h][i][0], T['candidate'][i][0]) for i in range(len(rs))]
            med, ci = boot_median(rr)
            per_h[h] = {'median_log2_ratio': round(med, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                        'host_log2_ratios': [round(x, 4) for x in rr], 'verdict': pair_verdict(ci)}
        desc = {a: {'tts_median': _num(quantile([x[0] for x in T[a]], 0.5)),
                    'tts_q75': _num(quantile([x[0] for x in T[a]], 0.75)),
                    'solved': sum(not math.isinf(x[0]) for x in T[a]), 'floors': sum(x[2] for x in T[a]),
                    'optimal_t': [x[1] for x in T[a]]} for a in ARMS}
        by_n[str(n)] = {'hosts': len(rs), 'certified': sum(r['target_certified'] for r in rs),
                        'edges': [min(r['edges'] for r in rs), max(r['edges'] for r in rs)] if rs else None,
                        'per_heuristic': per_h, 'arms': desc}
    slopes = {}
    for a in ARMS:
        meds = [by_n[str(n)]['arms'][a]['tts_median'] for n in NS]
        if all(m is not None for m in meds):
            xs, ys = list(NS), [math.log10(m) for m in meds]
            mx, my = statistics.fmean(xs), statistics.fmean(ys)
            slopes[a] = round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs), 5)
        else:
            slopes[a] = None
    return by_n, slopes


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
    v = [by_n[str(NS[-1])]['per_heuristic'][h]['verdict'] for h in HEURISTICS]
    if all(x == 'CANDIDATE_FASTER' for x in v):
        return 'E1D_FASTER_THAN_ALL'
    if any(x == 'HEURISTIC_FASTER' for x in v):
        return 'E1D_SLOWER_THAN_SOME'
    if all(x == 'COMPARABLE' for x in v):
        return 'E1D_COMPARABLE'
    return 'UNRESOLVED'


# ----------------------------------------------------------------------------------------------- run

def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
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
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim')))
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
            ref, opt = R41.reference(task, [('best_run', best[0])], registry, REF_S)
            target = opt if opt is not None else max(ref['lower'], best[1])
            r = {'task_id': task.task_id, 'n': task.n, 'split': task.split, 'edges': len(task.edges),
                 'runs': runs, 'cpu_ns': cpu_ns, 'reference': ref, 'target': target,
                 'target_certified': opt is not None, 'best_run_value': best[1]}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            tts = {a: host_tts(r, a) for a in ARMS}
            log(f'n{task.n} {task.task_id[-4:]} ({len(task.edges)} edges) target {target}'
                f'{"" if opt is not None else " (uncertified)"}: '
                + ' '.join(f'{a} {tts[a][0]:.3g}@{tts[a][1]}' for a in ARMS) + f' ref {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    invalid, cpu_half, fail = validity(rows)
    by_n, slopes = analyse(rows)
    summary = {'schema': 'genesis-b20r70-tts-scaling-v1', 'verdict': overall(by_n, invalid),
               'n60_verdicts': {h: by_n[str(NS[-1])]['per_heuristic'][h]['verdict'] for h in HEURISTICS},
               'by_n': by_n, 'scaling_slope_log10_tts_per_vertex': slopes,
               'validity': {'cpu_s_median_at_0.5': {a: round(v, 3) for a, v in cpu_half.items()},
                            'failure_share': {a: round(v, 5) for a, v in fail.items()}},
               'descriptors': {f'{a}@{t}': d['descriptor_id'] for (a, t), (_, d) in D.items()},
               'ladder': list(LADDER), 'reps': REPS, 'seeds': {'hosts': SEED, 'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV diagnostic of TTS scaling; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {summary['verdict']}; n60 {summary['n60_verdicts']}; slopes {slopes}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
