#!/usr/bin/env python3
"""B20_R72: do physics move rules improve every representation the system invented? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r72_represent_moves.py OUT_DIR      run (resumable) and analyse; run it ALONE

**Why.** The system turns each representation it invents (B18's typed decoders, Lean-checked sound) into a solver
with one engine: zero-temperature descent over encodings, then greedy repair. On n60 hosts that engine stops short
(B20_R66: optimal on 4 of 10 certified hosts; B20_R68: 3 of 13, behind a textbook tabu search). If a move rule from
statistical physics improves the engine for *every* sound representation, that is an improvement to the system's
own machinery, which any future invention inherits, rather than a fix for one problem
(docs/PHYSICS_INSPIRED_PLAN.md, idea 3). B20_R71 built `represent-search-v1`, the engine with a closed choice of
move rule: `descent` (the frozen rule), `eo` (τ-extremal optimization) and `anneal` (simulated annealing).

**Design (fixed before running).**
  * **Hosts.** 20 fresh DEV planted_cluster hosts, n60 (p_in 0.8, p_out 0.06), seed 20267201, drawn by
    `b20r64_e1d_scaling.generate_beyond_space`, excluding every identity `b20r24_repilots.exposure` excludes
    (B20_R70's hosts included). Saved before anything runs.
  * **Representations:** the sound triangle-free proposals that differ: `cross_2`, `adjacent_3`, `ordered_2`
    (`adjacent_2` decodes exactly as `cross_2` and is left out).
  * **Arms**, all in runc under E1's profile, 0.5 CPU s each, one run per host:
      - for each representation r and move m in (descent, eo, anneal): `represent-search-v1` {r, m};
      - context: E1's frozen candidate (v1 descriptor of the E1d package); `maxcut-tabu-v1`; `ising-dsb-v1`.
  * **Reference.** B20_R41's generated-rows route at 120 s, seeded with the best witness; descriptive.
  * **Primary endpoints.** For each r and each physics move m in (eo, anneal): d = value(r, m) − value(r, descent)
    per host; mean with a bootstrap 90% percentile interval (4,000 resamples, seed 20267299). Verdict per (r, m),
    MUE 0.5: IMPROVES (lower end > 0.5), WORSENS (upper end < −0.5), NO_MATERIAL_DIFFERENCE (inside (−0.5, 0.5)),
    UNRESOLVED otherwise; any failed run of either arm makes it UNRESOLVED_FAILURES.
  * **Overall:** IMPROVES_EVERY_REPRESENTATION if some move m IMPROVES for all three representations (the summary
    names it); IMPROVES_SOME if any (r, m) IMPROVES; NO_GENERAL_IMPROVEMENT otherwise. Validity first:
    INVALID_CPU_DELIVERY if any arm's median cgroup CPU is below 0.45 s.
  * **Secondary, descriptive, never decisive:** value(cross_2, descent) − frozen candidate (the same rule with this
    kind's faster repair); the best physics arm − tabu and − dSB; optimum hits on certified hosts; mean gap to the
    proven upper bound per arm.

**Expectation, stated before running.** Annealing improves every representation (the builder's guess: +1 to +2
edges at n60), EO less consistently, so IMPROVES_EVERY_REPRESENTATION with `anneal`; cross_2 under annealing near
tabu search and dSB. The builder has no data on any `represent-search-v1` arm beyond unit tests.

**Development looks.** None: `represent-search-v1` has run only on its unit-test hosts (K10, two random
fixtures, and one planted n30 host of seed 20267101).

**What it decides.** Nothing about packages, rules or comparators. A positive result would be a component
improvement for the system's invention engine, to be adopted (or not) as a new reviewed kind.

**Status.** A DEV diagnostic. It licenses nothing.
"""
import json
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
SEED, HOSTS, REF_S = 20267201, 20, 120
PARAMS = {'n': 60, 'p_in': 0.8, 'p_out': 0.06}
BOOT, BOOT_SEED, MUE = 4000, 20267299, 0.5
PROFILE = R11.PROFILE
BUDGET = 0.5
REPS_ = ('cross_2', 'adjacent_3', 'ordered_2')
MOVES = ('descent', 'eo', 'anneal')
PHYSICS = ('eo', 'anneal')
MIN_CPU = 0.45


def arm_name(r, m):
    return f'{r}/{m}'


def arms():
    out = {'candidate': ('v1', json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text()))}
    for r in REPS_:
        for m in MOVES:
            out[arm_name(r, m)] = ('v2', C2.build_descriptor('represent-search-v1', TF, {'representation': r, 'move': m,
                                                                                       'cpu_seconds': BUDGET}, **PROFILE))
    out['tabu'] = ('v2', C2.build_descriptor('maxcut-tabu-v1', TF, {'cpu_seconds': BUDGET}, **PROFILE))
    out['dsb'] = ('v2', C2.build_descriptor('ising-dsb-v1', TF, {'cpu_seconds': BUDGET}, **PROFILE))
    for name, (reg, d) in out.items():
        if (C1 if reg == 'v1' else C2).descriptor_problems(d, domain=TF):
            raise RuntimeError(f'{name} does not rebuild')
    if len({canonical(d['resource_profile']) for _, d in out.values()}) != 1:
        raise RuntimeError('the arms do not share one resource profile')
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, _ = R64.generate_beyond_space(SEED, HOSTS, 'DEV', PARAMS, set(excluded))
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a host collides with an excluded identity')
    R11.dump(path, {'seed': SEED, 'params': PARAMS, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def boot(d):
    rng = random.Random(BOOT_SEED)
    sims = sorted(statistics.fmean(rng.choice(d) for _ in d) for _ in range(BOOT))
    return statistics.fmean(d), [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def verdict(ci, failures):
    lo, hi = ci
    if failures:
        return 'UNRESOLVED_FAILURES'
    if lo > MUE:
        return 'IMPROVES'
    if hi < -MUE:
        return 'WORSENS'
    if -MUE < lo and hi < MUE:
        return 'NO_MATERIAL_DIFFERENCE'
    return 'UNRESOLVED'


def contrast(rows, a, b):
    d = [r['arms'][a]['value'] - r['arms'][b]['value'] for r in rows]
    est, ci = boot(d)
    return {'estimate': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
            'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)]}, ci


def analyse(rows, names):
    fails = {n: sum(r['arms'][n]['run'] != 'SUCCESS' for r in rows) for n in names}
    cpu = {n: statistics.median(r['arms'][n]['cpu_ns'] for r in rows) / 1e9 for n in names}
    primary = {}
    for r_ in REPS_:
        for m in PHYSICS:
            a, b = arm_name(r_, m), arm_name(r_, 'descent')
            c, ci = contrast(rows, a, b)
            c['verdict'] = verdict(ci, fails[a] + fails[b])
            primary[f'{a} - {b}'] = c
    if any(v < MIN_CPU for v in cpu.values()):
        overall, best_move = 'INVALID_CPU_DELIVERY', None
    else:
        every = [m for m in PHYSICS if all(primary[f'{arm_name(r_, m)} - {arm_name(r_, "descent")}']['verdict']
                                           == 'IMPROVES' for r_ in REPS_)]
        if every:
            overall, best_move = 'IMPROVES_EVERY_REPRESENTATION', every
        elif any(p['verdict'] == 'IMPROVES' for p in primary.values()):
            overall, best_move = 'IMPROVES_SOME', None
        else:
            overall, best_move = 'NO_GENERAL_IMPROVEMENT', None
    physics_arms = [arm_name(r_, m) for r_ in REPS_ for m in PHYSICS]
    best_phys = max(physics_arms, key=lambda a: statistics.fmean(r['arms'][a]['value'] for r in rows))
    cert = [r for r in rows if r['optimum'] is not None]
    secondary = {
        'cross_2/descent - candidate': contrast(rows, arm_name('cross_2', 'descent'), 'candidate')[0],
        'best_physics_arm': best_phys,
        'best_physics - tabu': contrast(rows, best_phys, 'tabu')[0],
        'best_physics - dsb': contrast(rows, best_phys, 'dsb')[0],
        'certified': len(cert),
        'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in cert) for n in names},
        'mean_gap_to_upper_bound': {n: round(statistics.fmean(r['reference']['upper'] - r['arms'][n]['value']
                                                              for r in rows), 4) for n in names},
        'mean_value': {n: round(statistics.fmean(r['arms'][n]['value'] for r in rows), 4) for n in names}}
    return {'verdict': overall, 'improving_moves': best_move, 'primary': primary, 'secondary': secondary,
            'failures': fails, 'cpu_s_median': {n: round(v, 3) for n, v in cpu.items()}, 'hosts': len(rows)}


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
    A = arms()
    registry = R37.registry_v2(json.loads(R41.PACKAGE.read_text()))
    excluded, scan, _ = R24.exposure(log)
    tasks = hosts(out, log, excluded)
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            seed = int(digest({'study': 'b20r72', 'task': t.task_id})[:12], 16)
            res, offered = {}, []
            for name, (reg, desc) in A.items():
                res[name], sel = R41.run_arm(t, reg, desc, seed)
                offered.append((name, sel))
            ref, opt = R41.reference(t, offered, registry, REF_S)
            r = {'task_id': t.task_id, 'n': t.n, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id[-4:]} ({len(t.edges)} edges): ' + ' '.join(f'{n} {res[n]["value"]}' for n in A)
                + f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.0f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    a = analyse(rows, list(A))
    summary = {'schema': 'genesis-b20r72-represent-moves-v1', **a,
               'descriptors': {n: d['descriptor_id'] for n, (_, d) in A.items()},
               'seeds': {'hosts': SEED, 'boot': BOOT_SEED}, 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV diagnostic of move rules in the representation engine; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {a['verdict']} {a['improving_moves']}; "
        + '; '.join(f"{k}: {v['estimate']} {v['interval_90']} {v['verdict']}" for k, v in a['primary'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
