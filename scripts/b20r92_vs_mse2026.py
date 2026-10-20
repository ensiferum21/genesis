#!/usr/bin/env python3
"""B20_R92: the system's engine against the MaxSAT Evaluation 2026 and 2024 anytime champions, with a finer ladder
and an ablation of its nature- and physics-inspired operators (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r92_vs_mse2026.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** B20_R90 found `tfx` (B20_R89's configuration) more than twice as fast as every 2024 champion and their
virtual best, but with three gaps Daniel asked about: the 2026 Evaluation's entrants were missing; tfx sat at the
ladder's floor (0.05 s) on 33 of 36 hosts, so its margin was unmeasured; and it was not known which of the operators
the system chose (from physics: simulated bifurcation, parallel tempering; from biology: crossover; path relinking
and restarts) matter. This study addresses all three, on fresh hosts.

**Design (fixed before running).**
  * **Engine:** `tfx` = `tfx-v1` with `evidence/configure_tfx_b20r89/config.json` (unchanged since B20_R89).
  * **Champions** (each with its Evaluation configuration; seeds pick isomorphic copies): the eight ranked 2026
    unweighted anytime entrants, built from their submitted sources (`maxsat-anytime-2026-v1`, B20_R91), in the
    2026 ranking's order at 60 s: `pasmaxsat` (PASMaxSAT-c, 1st at 60 s and 1707 s), `sgat` (SGAT-NuWLS-c),
    `aperture_gbg`, `nuwls26ub` (NuWLS-c-2026-UB), `aperture_kbg` (1st at 300 s), `aperture_ibi`, `deepdistc`
    (DeepDist-c), `nuwls26` (NuWLS-c-2026); and B20_R90's five (`maxsat-anytime-v1`): `deepdist`, `spb`, `nuwls`,
    `tt`, `aperture` (hermax's). **VBS:** per host, the lowest TTS* of all thirteen.
  * **Ablations of tfx** (family P only; each changes one thing in the frozen configuration): `no_dsb` (warm starts
    by descent only: ws 2), `no_pt` (no parallel tempering: acc 0, keeping its pw 0.05), `no_cross` (cross 0),
    `no_relink_restart` (relink 0, restart 0), and `first_design` (`tfx-v1`'s DEFAULT: what the configuration
    race replaced).
  * **Hosts.** P: planted_cluster (0.8, 0.06), 24 fresh n63 DEV hosts, seed 20269201. D: G(63, 0.5), 12 fresh,
    seed 20269202. Both exclude every identity `b20r24_repilots.exposure` excludes (all earlier studies' hosts).
  * **Part A, in runc under E1's profile:** the ladder (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 2.0) CPU s, 3 seeds.
    It reaches 10× below B20_R90's floor. A run below 0.5 s that ends without an assignment (some champions are
    still reading, preprocessing or in a first stage that prints nothing) counts as unsuccessful, not as a failure:
    a toy smoke run on dev-only hosts showed SGAT-NuWLS-c and Aperture printing nothing at 0.05 s on some runs.
  * **Part C, long budget, in runc (12 CPU s, 30 s wall):** tfx, the 2026 top five (PASMaxSAT-c, SGAT-NuWLS-c,
    Aperture-GBG, NuWLS-c-2026-UB, Aperture-KBG), DeepDist and SPB-MaxSAT-c-FPS at 10 s, one seed, both families.
  * **Part B:** CP-SAT 60 s on every host; on P also the checked generated-rows reference (120 s). Target = the best
    checked value of any run or the reference's lower bound; certified when its upper bound equals it.
  * **Statistic:** as B20_R90 (TTS*, Rønnow's quantile ratio at q 0.5 and 0.75, paired bootstrap, 4,000 resamples,
    seed 20269299, ±10 caps; A_FASTER = 90% interval above 1, i.e. more than twice as fast).
  * **Preregistered labels:**
      1. `champions_P`, `champions_D`: tfx against each of the thirteen: TFX_BEATS_EVERY_CHAMPION (A_FASTER in all
         26), A_CHAMPION_BEATS_TFX (any B_FASTER), TFX_MATCHES_CHAMPIONS (all COMPARABLE), MIXED.
      2. `vbs_P`, `vbs_D`: against the thirteen's VBS: TFX_BEATS_VBS, VBS_BEATS_TFX, TFX_MATCHES_VBS, UNRESOLVED.
      3. `champions2026_P`, `champions2026_D`: the same as 1 against the eight 2026 entrants only.
      4. `long_budget`: NO_CHAMPION_FINDS_MORE if on no host any Part C champion's 10 s value exceeds tfx's best
         value within 2 s; else CHAMPIONS_FIND_MORE (count).
      5. **Ablations** (P): for each, tfx against the ablated engine: HELPS (tfx A_FASTER at one or both q, never
         B_FASTER), HURTS (the reverse), NO_MEASURABLE_EFFECT (COMPARABLE at both), UNRESOLVED; and the margin
         itself: `margin_P` / `margin_D` = the log2 ratio against the VBS at q 0.5 and 0.75 with intervals (reported,
         no label).
    Validity first: INVALID_CPU_DELIVERY (some arm's median CPU at t = 0.5 below 0.45 s), INVALID_FAILURES (some
    arm's failed share above 1% over Part A runs at 0.5 s and 2 s, and Part C).

**Expectation, stated before running.** All four champion labels and both VBS labels as in B20_R90 (tfx more than
twice as fast), with the finer ladder now measuring a margin of roughly 10× against the VBS on P (B20_R90: at least
5×); DeepDist and PASMaxSAT-c the closest (in a development look on B20_R76's hosts, PASMaxSAT-c reached 262–264 of a
265 target at 0.01–0.05 s, DeepDist 258–265). **Revised after the toy smoke run (disclosed in the B20_R91
record), before preregistration:** on its one planted dev host Aperture-KBG and NuWLS-c-2026 reached the target in
0.06 s (TTS*) against tfx's 0.02 s, so the 2026 entrants are much faster than the 2024 ones; against the VBS the margin
may be under 2× at q 0.5, making vbs_P UNRESOLVED or COMPARABLE about as likely as TFX_BEATS_VBS, and champions_P
MIXED likelier than in B20_R90. long_budget NO_CHAMPION_FINDS_MORE. Ablations: each operator's effect is
smaller than the 2× the statistic resolves, so NO_MEASURABLE_EFFECT or UNRESOLVED for most; `first_design` the most
likely to show (HELPS), since the race eliminated it early.

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
from genesis.candidate_kinds import maxsat as MS, maxsat2026 as M26, tfx as T  # noqa: E402
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
FAMILIES = {'P': {'seed': 20269201, 'count': 24, 'params': {'n': 63, 'p_in': 0.8, 'p_out': 0.06}},
            'D': {'seed': 20269202, 'count': 12, 'params': {'n': 63, 'p_in': 0.5, 'p_out': 0.5}}}
LADDER = (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 2.0)
SHORT = 0.5                        # below this, a run without an assignment is unsuccessful, not failed
REPS, LONG_T, REF_S = 3, 10.0, 120
BOOT, BOOT_SEED = 4000, 20269299
QS = (0.5, 0.75)
PROFILE = R11.PROFILE
LONG_PROFILE = {'cpu_seconds': 12, 'memory_mib': 2048, 'wall_seconds': 30, 'queries': 1000}
CONFIG = ROOT / 'evidence' / 'configure_tfx_b20r89' / 'config.json'
CH2026 = ('pasmaxsat', 'sgat', 'aperture_gbg', 'nuwls26ub', 'aperture_kbg', 'aperture_ibi', 'deepdistc', 'nuwls26')
CH2024 = ('deepdist', 'spb', 'nuwls', 'tt', 'aperture')
CHAMPIONS = CH2026 + CH2024
ABLATIONS = {'no_dsb': {'ws': 2}, 'no_pt': {'acc': 0}, 'no_cross': {'cross': 0},
             'no_relink_restart': {'relink': 0, 'restart': 0}, 'first_design': None}
ARMS = {'P': ('tfx',) + tuple(ABLATIONS) + CHAMPIONS, 'D': ('tfx',) + CHAMPIONS}
LONG_ARMS = ('tfx',) + CH2026[:5] + ('deepdist', 'spb')
FIXED = {'pasmaxsat': ('maxsat-anytime-2026-v1', {'solver': 'pasmaxsat-c'}),
         'sgat': ('maxsat-anytime-2026-v1', {'solver': 'sgat-nuwls-c'}),
         'aperture_gbg': ('maxsat-anytime-2026-v1', {'solver': 'aperture-gbg'}),
         'nuwls26ub': ('maxsat-anytime-2026-v1', {'solver': 'nuwls-c-2026-ub'}),
         'aperture_kbg': ('maxsat-anytime-2026-v1', {'solver': 'aperture-kbg'}),
         'aperture_ibi': ('maxsat-anytime-2026-v1', {'solver': 'aperture-ibi'}),
         'nuwls26': ('maxsat-anytime-2026-v1', {'solver': 'nuwls-c-2026'}),
         'deepdistc': ('maxsat-anytime-2026-v1', {'solver': 'deepdist-c'}),
         'deepdist': ('maxsat-anytime-v1', {'solver': 'deepdist'}),
         'spb': ('maxsat-anytime-v1', {'solver': 'spb-maxsat-c-fps'}),
         'nuwls': ('maxsat-anytime-v1', {'solver': 'nuwls-c-ibr'}),
         'tt': ('maxsat-anytime-v1', {'solver': 'tt-open-wbo-inc'}),
         'aperture': ('maxsat-anytime-v1', {'solver': 'aperture'})}
MIN_CPU_AT_HALF, MAX_FAIL_SHARE = 0.45, 0.01


def frozen_config():
    if not CONFIG.exists():
        raise SystemExit(f'{CONFIG.relative_to(ROOT)} is missing')
    cfg = json.loads(CONFIG.read_text())['config']
    if T.check_config(cfg):
        raise SystemExit(f'the frozen configuration is not valid: {T.check_config(cfg)}')
    return cfg, hashlib.sha256(CONFIG.read_bytes()).hexdigest()


def tfx_config(arm, cfg):
    if arm == 'tfx':
        return dict(cfg)
    change = ABLATIONS[arm]
    out = dict(T.DEFAULT) if change is None else dict(cfg, **change)
    if T.check_config(out):
        raise RuntimeError(f'{arm}: {T.check_config(out)}')
    return out


def descriptor(arm, t, cfg, profile):
    if arm == 'tfx' or arm in ABLATIONS:
        return C2.build_descriptor('tfx-v1', TF, {'cpu_seconds': t, 'config': tfx_config(arm, cfg)}, **profile)
    kind, extra = FIXED[arm]
    return C2.build_descriptor(kind, TF, dict(extra, cpu_seconds=t), **profile)


def arm_descriptors(cfg):
    out = {(a, t): ('v2', descriptor(a, t, cfg, PROFILE)) for a in ARMS['P'] for t in LADDER}
    out.update({(a, LONG_T): ('v2', descriptor(a, LONG_T, cfg, LONG_PROFILE)) for a in LONG_ARMS})
    for keys in ([k for k in out if k[1] != LONG_T], [k for k in out if k[1] == LONG_T]):
        if len({canonical(out[k][1]['resource_profile']) for k in keys}) != 1:
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
    return int(digest({'study': 'b20r92', 'task': task_id, 'arm': arm, 't': t, 'rep': k})[:12], 16)


# ----------------------------------------------------------------------------------------------- analysis

def host_tts(row, arm):
    """TTS* over this study's ladder: the best, over run times, of TTS99 = t * ceil(ln 0.01 / ln(1 - s))."""
    best = math.inf
    for t in LADDER:
        runs = row['runs'][arm][str(t)]
        s = sum(r['run'] == 'SUCCESS' and r['value'] >= row['target'] for r in runs) / len(runs)
        best = min(best, R70.tts99(t, s))
    return best


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


def label_champions(ps, names):
    v = [ps[c][f'q{q}']['verdict'] for c in names for q in QS]
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


def label_ablation(p):
    v = [p[f'q{q}']['verdict'] for q in QS]
    if 'A_FASTER' in v and 'B_FASTER' not in v:
        return 'HELPS'
    if 'B_FASTER' in v and 'A_FASTER' not in v:
        return 'HURTS'
    if all(x == 'COMPARABLE' for x in v):
        return 'NO_MEASURABLE_EFFECT'
    return 'UNRESOLVED'


def tts_table(rows, arms):
    T_ = {a: [host_tts(r, a) for r in rows] for a in arms}
    T_['vbs'] = [min(T_[c][i] for c in CHAMPIONS) for i in range(len(rows))]
    return T_


def long_budget(rows):
    out = []
    for r in rows:
        tfx_best = max((x['value'] for t in LADDER for x in r['runs']['tfx'][str(t)] if x['run'] == 'SUCCESS'),
                       default=-1)
        better = {c: r['long'][c]['value'] for c in LONG_ARMS if c != 'tfx' and r['long'][c]['run'] == 'SUCCESS'
                  and r['long'][c]['value'] > tfx_best}
        if better:
            out.append({'task_id': r['task_id'], 'tfx_best_2s': tfx_best, 'champions_10s': better})
    return out


def analyse_family(rows, f):
    T_ = tts_table(rows, ARMS[f])
    champs = {c: pair(T_, 'tfx', c) for c in CHAMPIONS}
    vbs = pair(T_, 'tfx', 'vbs')
    out = {'hosts': len(rows), 'edges': [min(r['edges'] for r in rows), max(r['edges'] for r in rows)] if rows else None,
           'certified': sum(r['target_certified'] for r in rows),
           'labels': {f'champions_{f}': label_champions(champs, CHAMPIONS), f'vbs_{f}': label_vbs(vbs),
                      f'champions2026_{f}': label_champions(champs, CH2026)},
           'margin_vs_vbs': {f'q{q}': vbs[f'q{q}'] for q in QS},
           'tfx_vs_champions': champs, 'tfx_vs_vbs': vbs,
           'arms': {a: {'reached_within_2s': sum(not math.isinf(v) for v in T_[a]),
                        'tts_median': R70._num(R70.quantile(T_[a], 0.5)), 'tts_q75': R70._num(R70.quantile(T_[a], 0.75)),
                        'at_floor': sum(v == LADDER[0] for v in T_[a])} for a in T_},
           'long_budget': {a: {'reaches_target': sum(r['long'][a]['run'] == 'SUCCESS' and r['long'][a]['value'] >= r['target']
                                                     for r in rows)} for a in LONG_ARMS},
           'long_budget_hosts_where_a_champion_finds_more': long_budget(rows),
           'exact': {'cpsat_60s': {'claims_optimal': sum(r['exact']['cpsat']['claims_optimal'] for r in rows),
                                   'reaches_target': sum(r['exact']['cpsat']['value'] == r['target'] for r in rows)}}}
    if f == 'P':
        abl = {a: pair(T_, 'tfx', a) for a in ABLATIONS}
        out['ablations'] = abl
        out['labels'].update({f'ablation_{a}': label_ablation(p) for a, p in abl.items()})
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
            runs = [x for r in rows for t in LADDER if t >= SHORT for x in r['runs'][a][str(t)]]
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
    tmp = Path(tempfile.mkdtemp(prefix='b20r92-'))
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}; tfx config sha256 {cfg_sha[:16]}')
    from genesis.verification.tools import tool
    from genesis.candidate_kinds import cpsat as K
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim'))
        + f'; OR-Tools {K.tree_digest()[:16]}; tfx {T.binary_digest()[:16]}; '
        + ', '.join(f'{k} {MS.binary_digest(v["binary"])[:12]}' for k, v in MS.SOLVERS.items()) + '; '
        + ', '.join(f'{k} {M26.digest(v["binary"])[:12]}' for k, v in M26.SOLVERS.items()))
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
                                       'status': res['status']})
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
                tts = {a: host_tts(r, a) for a in ARMS[f]}
                log(f'{f} {task.task_id[-4:]} ({len(task.edges)} edges) target {target}'
                    f'{"" if certified else " (uncertified)"}: ' + ' '.join(f'{a} {tts[a]:.3g}' for a in ARMS[f])
                    + ' | 10s ' + ' '.join(f'{a} {long[a]["value"]}' for a in LONG_ARMS)
                    + f' | cpsat-60s {ex["cpsat"]["value"]} | ref {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    by = {f: [r for r in rows if r['family'] == f] for f in FAMILIES}
    invalid, cpu_half, fail = validity(by)
    labels, fam = analyse(by)
    labels = {k: (invalid or v) for k, v in labels.items()}
    summary = {'schema': 'genesis-b20r92-vs-mse2026-v1', 'labels': labels, 'families': fam,
               'validity': {'cpu_s_median_at_0.5': {k: round(v, 3) for k, v in cpu_half.items()},
                            'failure_share_at_or_above_0.5_and_long': {k: round(v, 5) for k, v in fail.items()}},
               'tfx': {'config': cfg, 'config_file_sha256': cfg_sha, 'binary_sha256': T.binary_digest(),
                       'ablations': {a: tfx_config(a, cfg) for a in ABLATIONS}},
               'champions': {**{k: MS.binary_digest(v['binary']) for k, v in MS.SOLVERS.items()},
                             **{k: M26.digest(v['binary']) for k, v in M26.SOLVERS.items()}},
               'descriptors': {f'{x}@{t}': d['descriptor_id'] for (x, t), (_, d) in D.items()},
               'ladder': list(LADDER), 'reps': REPS, 'long_seconds': LONG_T, 'quantiles': list(QS),
               'seeds': {f: FAMILIES[f]['seed'] for f in FAMILIES} | {'boot': BOOT_SEED},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV comparison; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f'labels {labels}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
