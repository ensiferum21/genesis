#!/usr/bin/env python3
"""B20_R90: the system's configured engine against the strongest anytime MaxSAT solvers (DEV, preregistered before
B20_R89 has run)

    taskset -c 0 python3 scripts/b20r90_beat_the_champions.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** Daniel asked for a solver that beats "the best of the best, extremely tuned over years". B20_R87 built the
strongest anytime MaxSAT solvers from source; B20_R88 built `tfx-v1`; B20_R89 lets the system choose its
configuration. This study fixes, before that choice exists, how the frozen configuration is judged.

**Design (fixed before running).**
  * **Engine:** `tfx` = `tfx-v1` with `evidence/configure_tfx_b20r89/config.json`'s configuration (refuses to run
    without it, or if it is not valid); its SHA-256 is recorded.
  * **Champions** (`maxsat-anytime-v1`, B20_R87's pinned builds, published configurations, the seed picks an
    isomorphic copy): `deepdist` (ECAI 2025), `spb` (SPB-MaxSAT-c-FPS, MSE 2024 winner), `nuwls` (NuWLS-c-IBR, MSE 2024
    podium), `tt` (TT-Open-WBO-Inc 2024, IntelSAT), `aperture` (SOFT 2026). **VBS:** per host, the best (lowest)
    TTS* of the five: the virtual best solver, an oracle no single solver and no selector can beat.
  * **References:** `engine` (`hybrid-swap-v1`, B20_R77), `burer` (`mqlib-v1` BURER2002), `mq1`–`mq3`
    (`mqlib-heuristic-v1` MERZ2004, FESTA2002GVNSPR, FESTA2002GVNS: B20_R88's best three MQLib heuristics other than
    BURER2002; MQVBS = per-host best of burer and mq1–mq3), `cpsat` (`cpsat-v1`, 8 workers on one core).
  * **Hosts.** Family P (primary): planted_cluster (p_in 0.8, p_out 0.06), 24 fresh DEV hosts at n63, seed 20269001.
    Family D (secondary, a denser structure on which `tfx` was never developed): G(63, 0.5) (planted_cluster with
    p_in = p_out = 0.5), 12 fresh DEV hosts, seed 20269002. Both exclude every identity `b20r24_repilots.exposure`
    excludes (B20_R89's training hosts included).
  * **Part A, anytime, in runc under E1's profile:** run times (0.05, 0.1, 0.25, 0.5, 2.0) CPU s, 3 seeds each.
    Family P: all arms. Family D: tfx and the five champions.
  * **Part C, long budget, in runc (profile: 12 CPU s, 30 s wall):** tfx and the five champions at 10 s, one seed,
    both families: given five times the longest ladder time, does any champion find more?
  * **Part B:** CP-SAT 60 s (B20_R76's exact child) on every host; on family P also the checked generated-rows
    reference (120 s). **Target** = the best checked value of any run (Parts A, B, C) or the reference's lower bound;
    certified when the reference's upper bound equals it.
  * **TTS*, the quantile ratio and its paired bootstrap:** as B20_R77 (4,000 resamples, seed 20269099):
    r(a, b, q) = log2(TTS*_b(q) / TTS*_a(q)), capped at ±10, positive when a is faster; verdict per q: A_FASTER (90%
    interval above 1, i.e. more than twice as fast), B_FASTER (below −1), COMPARABLE (inside (−1, 1)), UNRESOLVED.
  * **Preregistered labels (q = 0.5 and 0.75):**
      1. **`champions_P`, the headline:** tfx against each champion on family P: TFX_BEATS_EVERY_CHAMPION (A_FASTER
         in all ten), A_CHAMPION_BEATS_TFX (any B_FASTER), TFX_MATCHES_CHAMPIONS (all COMPARABLE), MIXED otherwise.
      2. **`vbs_P`:** tfx against the champions' VBS on family P: TFX_BEATS_VBS (A_FASTER at both q), VBS_BEATS_TFX
         (B_FASTER at either), TFX_MATCHES_VBS (COMPARABLE at both), UNRESOLVED otherwise.
      3. **`champions_D`** and 4. **`vbs_D`:** the same on family D.
      5. **`long_budget`:** NO_CHAMPION_FINDS_MORE if on no host of either family any champion's 10 s value exceeds
         the best value tfx found within 2 s (Part A); otherwise CHAMPIONS_FIND_MORE (with the count).
    Validity first: INVALID_CPU_DELIVERY (some Part A arm's median CPU at t = 0.5 below 0.45 s), INVALID_FAILURES (some
    arm's failed share above 1% in Part A or C).
  * **Secondary:** tfx against MQVBS, engine, burer and cpsat; B20_R77's question again (engine against burer and
    cpsat); every pair's per-host median (B20_R76's statistic); per arm, hosts reached within 2 s, TTS* quantiles and
    Part C values; Part B.

**Expectation, stated before B20_R89 has run.** From B20_R88's looks: tfx faster than every champion at q = 0.5 on
family P; at q = 0.75 DeepDist is the closest and may be COMPARABLE or UNRESOLVED, so champions_P MIXED is about as
likely as TFX_BEATS_EVERY_CHAMPION; vbs_P likely MIXED-like (UNRESOLVED). Family D is open (never developed on).
long_budget: NO_CHAMPION_FINDS_MORE (the problems saturate within 2 s for the strongest solvers).

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
from genesis.candidate_kinds import maxsat as MS, tfx as T  # noqa: E402
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
FAMILIES = {'P': {'seed': 20269001, 'count': 24, 'params': {'n': 63, 'p_in': 0.8, 'p_out': 0.06}},
            'D': {'seed': 20269002, 'count': 12, 'params': {'n': 63, 'p_in': 0.5, 'p_out': 0.5}}}
LADDER, REPS, LONG_T, REF_S = R76.LADDER, 3, 10.0, 120
BOOT, BOOT_SEED = 4000, 20269099
QS = (0.5, 0.75)
PROFILE = R11.PROFILE
LONG_PROFILE = {'cpu_seconds': 12, 'memory_mib': 2048, 'wall_seconds': 30, 'queries': 1000}
CONFIG = ROOT / 'evidence' / 'configure_tfx_b20r89' / 'config.json'
CHAMPIONS = ('deepdist', 'spb', 'nuwls', 'tt', 'aperture')
MQ = ('burer', 'mq1', 'mq2', 'mq3')
ARMS = {'P': ('tfx',) + CHAMPIONS + ('engine',) + MQ + ('cpsat',), 'D': ('tfx',) + CHAMPIONS}
LONG_ARMS = ('tfx',) + CHAMPIONS
FIXED = {'deepdist': ('maxsat-anytime-v1', {'solver': 'deepdist'}),
         'spb': ('maxsat-anytime-v1', {'solver': 'spb-maxsat-c-fps'}),
         'nuwls': ('maxsat-anytime-v1', {'solver': 'nuwls-c-ibr'}),
         'tt': ('maxsat-anytime-v1', {'solver': 'tt-open-wbo-inc'}),
         'aperture': ('maxsat-anytime-v1', {'solver': 'aperture'}),
         'engine': ('hybrid-swap-v1', {}),
         'burer': ('mqlib-v1', {'heuristic': 'BURER2002'}),
         'mq1': ('mqlib-heuristic-v1', {'heuristic': 'MERZ2004'}),
         'mq2': ('mqlib-heuristic-v1', {'heuristic': 'FESTA2002GVNSPR'}),
         'mq3': ('mqlib-heuristic-v1', {'heuristic': 'FESTA2002GVNS'}),
         'cpsat': ('cpsat-v1', {})}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01
assert LADDER == (0.05, 0.1, 0.25, 0.5, 2.0)


def frozen_config():
    if not CONFIG.exists():
        raise SystemExit(f'{CONFIG.relative_to(ROOT)} is missing: run B20_R89 first')
    cfg = json.loads(CONFIG.read_text())['config']
    if T.check_config(cfg):
        raise SystemExit(f'the frozen configuration is not valid: {T.check_config(cfg)}')
    return cfg, hashlib.sha256(CONFIG.read_bytes()).hexdigest()


def descriptor(arm, t, cfg, profile):
    if arm == 'tfx':
        return C2.build_descriptor('tfx-v1', TF, {'cpu_seconds': t, 'config': cfg}, **profile)
    kind, extra = FIXED[arm]
    return C2.build_descriptor(kind, TF, dict(extra, cpu_seconds=t), **profile)


def arm_descriptors(cfg):
    out = {(a, t): ('v2', descriptor(a, t, cfg, PROFILE)) for a in ARMS['P'] for t in LADDER}
    out.update({(a, LONG_T): ('v2', descriptor(a, LONG_T, cfg, LONG_PROFILE)) for a in LONG_ARMS})
    for profile, keys in ((PROFILE, [k for k in out if k[1] != LONG_T]), (LONG_PROFILE, [k for k in out if k[1] == LONG_T])):
        if {canonical(out[k][1]['resource_profile']) for k in keys} != {canonical(out[keys[0]][1]['resource_profile'])}:
            raise RuntimeError('arms of one part do not share one resource profile')
    for k, (_, d) in out.items():
        if C2.descriptor_problems(d, domain=TF):
            raise RuntimeError(f'{k} does not rebuild')
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        d = json.loads(path.read_text())
        return {f: [GraphTask.model_validate_json(canonical(t)) for t in d['families'][f]['tasks']] for f in FAMILIES}
    seen, fams = set(excluded), {}
    for f, spec in FAMILIES.items():
        tasks, seen = R64.generate_beyond_space(spec['seed'], spec['count'], 'DEV', spec['params'], seen)
        if len(tasks) != spec['count'] or RD.identities(tasks) & set(excluded):
            raise RuntimeError('host drawing failed or collides with an excluded identity')
        fams[f] = tasks
    R11.dump(path, {'families': {f: dict(FAMILIES[f], tasks=[t.model_dump(mode='json') for t in fams[f]])
                                 for f in FAMILIES}})
    return fams


def run_seed(task_id, arm, t, k):
    return int(digest({'study': 'b20r90', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


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


def pair(T_, a, b):
    """a against b: log2(TTS*_b(q) / TTS*_a(q)) at each q, and B20_R76's per-host median."""
    out = {}
    for q in QS:
        est, ci = boot(lambda ix, q=q: R70.log_ratio(R70.quantile([T_[b][i] for i in ix], q),
                                                    R70.quantile([T_[a][i] for i in ix], q)), len(T_[a]))
        out[f'q{q}'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                        'verdict': verdict(ci)}
    per_host = [R70.log_ratio(y, x) for x, y in zip(T_[a], T_[b])]
    est, ci = boot(lambda ix: statistics.median(per_host[i] for i in ix), len(per_host))
    out['b20r76_per_host_median'] = {'log2_ratio': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                                     'verdict': verdict(ci), 'host_log2_ratios': [round(v, 4) for v in per_host]}
    return out


def label_champions(ps):
    v = [ps[c][f'q{q}']['verdict'] for c in CHAMPIONS for q in QS]
    if all(x == 'A_FASTER' for x in v):
        return 'TFX_BEATS_EVERY_CHAMPION'
    if any(x == 'B_FASTER' for x in v):
        return 'A_CHAMPION_BEATS_TFX'
    if all(x == 'COMPARABLE' for x in v):
        return 'TFX_MATCHES_CHAMPIONS'
    return 'MIXED'


def label_vbs(p):
    v = [p[f'q{q}']['verdict'] for q in QS]
    if all(x == 'A_FASTER' for x in v):
        return 'TFX_BEATS_VBS'
    if any(x == 'B_FASTER' for x in v):
        return 'VBS_BEATS_TFX'
    if all(x == 'COMPARABLE' for x in v):
        return 'TFX_MATCHES_VBS'
    return 'UNRESOLVED'


def tts_table(rows, arms):
    T_ = {a: [R76.host_tts(r, a)[0] for r in rows] for a in arms}
    T_['vbs'] = [min(T_[c][i] for c in CHAMPIONS) for i in range(len(rows))]
    if set(MQ) <= set(arms):
        T_['mqvbs'] = [min(T_[c][i] for c in MQ) for i in range(len(rows))]
    return T_


def long_budget(rows):
    """Hosts where some champion's 10 s value exceeds the best tfx value within 2 s."""
    out = []
    for r in rows:
        tfx_best = max((x['value'] for t in LADDER for x in r['runs']['tfx'][str(t)] if x['run'] == 'SUCCESS'),
                       default=-1)
        champ = {c: r['long'][c]['value'] for c in CHAMPIONS if r['long'][c]['run'] == 'SUCCESS'}
        better = {c: v for c, v in champ.items() if v > tfx_best}
        if better:
            out.append({'task_id': r['task_id'], 'tfx_best_2s': tfx_best, 'champions_10s': better})
    return out


def analyse_family(rows, f):
    arms = ARMS[f]
    T_ = tts_table(rows, arms)
    champs = {c: pair(T_, 'tfx', c) for c in CHAMPIONS}
    vbs = pair(T_, 'tfx', 'vbs')
    out = {'hosts': len(rows), 'edges': [min(r['edges'] for r in rows), max(r['edges'] for r in rows)] if rows else None,
           'certified': sum(r['target_certified'] for r in rows),
           'labels': {f'champions_{f}': label_champions(champs), f'vbs_{f}': label_vbs(vbs)},
           'tfx_vs_champions': champs, 'tfx_vs_vbs': vbs,
           'arms': {a: {'reached_within_2s': sum(not math.isinf(v) for v in T_[a]),
                        'tts_median': R70._num(R70.quantile(T_[a], 0.5)), 'tts_q75': R70._num(R70.quantile(T_[a], 0.75))}
                    for a in T_},
           'long_budget': {a: {'reaches_target': sum(r['long'][a]['run'] == 'SUCCESS' and r['long'][a]['value'] >= r['target']
                                                     for r in rows)} for a in LONG_ARMS},
           'long_budget_hosts_where_a_champion_finds_more': long_budget(rows),
           'exact': {'cpsat_60s': {'claims_optimal': sum(r['exact']['cpsat']['claims_optimal'] for r in rows),
                                   'reaches_target': sum(r['exact']['cpsat']['value'] == r['target'] for r in rows)}}}
    if f == 'P':
        out['secondary'] = {'tfx_vs_mqvbs': pair(T_, 'tfx', 'mqvbs'), 'tfx_vs_engine': pair(T_, 'tfx', 'engine'),
                            'tfx_vs_burer': pair(T_, 'tfx', 'burer'), 'tfx_vs_cpsat': pair(T_, 'tfx', 'cpsat'),
                            'engine_vs_burer': pair(T_, 'engine', 'burer'), 'engine_vs_cpsat': pair(T_, 'engine', 'cpsat')}
    return out


def analyse(rows_by_family):
    fam = {f: analyse_family(rows_by_family[f], f) for f in FAMILIES}
    labels = {k: v for f in FAMILIES for k, v in fam[f]['labels'].items()}
    more = sum(len(fam[f]['long_budget_hosts_where_a_champion_finds_more']) for f in FAMILIES)
    labels['long_budget'] = 'NO_CHAMPION_FINDS_MORE' if more == 0 else f'CHAMPIONS_FIND_MORE ({more} hosts)'
    return labels, fam


def validity(rows_by_family):
    cpu, fail = {}, {}
    for f, rows in rows_by_family.items():
        for a in ARMS[f]:
            cpu[f'{f}:{a}'] = statistics.median(r['cpu_ns'][a]['0.5'] for r in rows) / 1e9
            runs = [x for r in rows for t in LADDER for x in r['runs'][a][str(t)]]
            if a in LONG_ARMS:
                runs += [r['long'][a] for r in rows]
            fail[f'{f}:{a}'] = sum(x['run'] != 'SUCCESS' for x in runs) / len(runs)
    if any(v < MIN_CPU_AT_HALF for v in cpu.values()):
        return 'INVALID_CPU_DELIVERY', cpu, fail
    if any(v > MAX_FAIL_SHARE for v in fail.values()):
        return 'INVALID_FAILURES', cpu, fail
    return None, cpu, fail


# ----------------------------------------------------------------------------------------------- run

def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    cfg, cfg_sha = frozen_config()
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='b20r90-'))
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}; tfx config sha256 {cfg_sha[:16]}: {json.dumps(cfg, sort_keys=True)}')
    from genesis.verification.tools import tool
    from genesis.candidate_kinds import cpsat as K, mqlib as MQL
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim'))
        + f'; MQLib {MQL.binary_digest()[:16]}; OR-Tools {K.tree_digest()[:16]}; tfx {T.binary_digest()[:16]}; '
        + ', '.join(f'{k} {MS.binary_digest(v["binary"])[:16]}' for k, v in MS.SOLVERS.items()))
    D = arm_descriptors(cfg)
    registry = R37.registry_v2(json.loads(R41.PACKAGE.read_text()))
    excluded, scan, _ = R24.exposure(log)
    fams = hosts(out, log, excluded)
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for f in FAMILIES:
            for task in fams[f]:
                if task.task_id in done:
                    continue
                runs, cpu_ns, best, long = {a: {} for a in ARMS[f]}, {a: {} for a in ARMS[f]}, (None, -1), {}
                for a in ARMS[f]:
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
                for a in LONG_ARMS:
                    reg, desc = D[(a, LONG_T)]
                    res, sel = R41.run_arm(task, reg, desc, run_seed(task.task_id, a, LONG_T, 0))
                    long[a] = {'value': res['value'], 'run': res['run'], 'cpu_ns': res['cpu_ns']}
                    if sel is not None and res['value'] > best[1]:
                        best = (sel, res['value'])
                ex = {}
                ex['cpsat'], sel = R76.exact(task, 'cpsat', tmp)
                if sel is not None and ex['cpsat']['value'] > best[1]:
                    best = (sel, ex['cpsat']['value'])
                if f == 'P':
                    ref, _ = R41.reference(task, [('best', best[0])], registry, REF_S)
                else:
                    ref = {'lower': best[1], 'upper': None, 'wall_s': 0.0, 'method': 'not run (family D)'}
                target = max(best[1], ref['lower'])
                certified = ref['upper'] == target
                r = {'task_id': task.task_id, 'family': f, 'n': task.n, 'split': task.split, 'edges': len(task.edges),
                     'runs': runs, 'cpu_ns': cpu_ns, 'long': long, 'exact': ex, 'reference': ref, 'target': target,
                     'target_certified': certified, 'best_witness_value': best[1]}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                tts = {a: R76.host_tts(r, a) for a in ARMS[f]}
                log(f'{f} {task.task_id[-4:]} ({len(task.edges)} edges) target {target}'
                    f'{"" if certified else " (uncertified)"}: ' + ' '.join(f'{a} {tts[a][0]:.3g}' for a in ARMS[f])
                    + ' | 10s ' + ' '.join(f'{a} {long[a]["value"]}' for a in LONG_ARMS)
                    + f' | cpsat-60s {ex["cpsat"]["value"]} | ref {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    by = {f: [r for r in rows if r['family'] == f] for f in FAMILIES}
    invalid, cpu_half, fail = validity(by)
    labels, fam = analyse(by)
    labels = {k: (invalid or v) for k, v in labels.items()}
    summary = {'schema': 'genesis-b20r90-beat-the-champions-v1', 'labels': labels, 'families': fam,
               'validity': {'cpu_s_median_at_0.5': {k: round(v, 3) for k, v in cpu_half.items()},
                            'failure_share': {k: round(v, 5) for k, v in fail.items()}},
               'tfx': {'config': cfg, 'config_file_sha256': cfg_sha, 'binary_sha256': T.binary_digest()},
               'champions': {k: MS.binary_digest(v['binary']) for k, v in MS.SOLVERS.items()},
               'descriptors': {f'{x}@{t}': d['descriptor_id'] for (x, t), (_, d) in D.items()},
               'mqlib': {'sha256': MQL.binary_digest()}, 'ortools': {'sha256': K.tree_digest(), 'workers': K.WORKERS},
               'ladder': list(LADDER), 'reps': REPS, 'long_seconds': LONG_T, 'quantiles': list(QS),
               'seeds': {f: FAMILIES[f]['seed'] for f in FAMILIES} | {'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV comparison; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f'labels {labels}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
