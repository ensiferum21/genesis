#!/usr/bin/env python3
"""B20_R66: does E1d's lead at n60 replicate on fresh hosts, and does it survive HiGHS at 120x? (DEV, preregistered)

    python3 scripts/b20r66_e1d_n60.py OUT_DIR      run (resumable) and analyse; run it ALONE on the machine

**Why.** B20_R64 (a DEV pilot, 10 hosts per size) found that the 0.5 s candidate's lead over HiGHS grows with host
size: at n60 it led HiGHS at 32 s (64x) by +17.6 [8.1, 28.8], 10/0/0. That is the strongest GV3 signal so far, from
10 hosts. As with B20_R57 → R59, a positive pilot gets an internal replication on fresh hosts before anyone leans
on it. This study also raises HiGHS to `milp-highs-v1`'s ceiling, 60 s (120x), to locate the crossover at n60.

**Scope.** As in B20_R64: n60 planted hosts lie beyond the registered family space and the 200-edge certificate
bound; they are drawn by `b20r64_e1d_scaling.generate_beyond_space`. A DEV study; no claim, rule or bound changes.

**Design (fixed before running).**
  * **Hosts.** 20 fresh DEV hosts, planted_cluster n60 (p_in 0.8, p_out 0.06), seed 20266601, excluding every
    identity `b20r24_repilots.exposure` excludes (which covers all of B20_R64's hosts).
  * **Arms**, in runc: E1's frozen candidate (0.5 CPU s); HiGHS at 32 s (B20_R63/R64's descriptor) and at 60 s
    (the same profile scaled: `cpu_seconds` 60, wall 300 s).
  * **Reference.** B20_R41's generated-rows route at 120 s, seeded with the best arm witness; descriptive.
  * **Endpoint per budget.** candidate − HiGHS per host (a failed run scores 0); mean, bootstrap 90% percentile
    interval (4,000 resamples, seed 20266699). Per-budget verdicts by B20_R63's rule (ADVANTAGE iff the lower end
    > 0.5).
  * **Validity (B20_R64's lesson, part of the design).** For each HiGHS arm, the median ratio of its cgroup CPU to
    its budget, over hosts where it ran to its limit (value below the best known), must be at least 0.9. If not,
    the verdict is INVALID_CPU_DELIVERY and nothing else is read.
  * **Overall verdict.**
      - NOT_REPLICATED: the 32 s verdict is not ADVANTAGE;
      - REPLICATED_CROSSOVER_BY_120X: ADVANTAGE at 32 s but not at 60 s;
      - REPLICATED_ADVANTAGE_THROUGH_120X: ADVANTAGE at both.
  * **Descriptive:** certified hosts; each arm's gap to the reference's proven upper bound; HiGHS non-monotonicity
    (60 s below 32 s); the reference's time.

**Expectation, stated before running.** In B20_R64 at n60 HiGHS's gap to the bound fell from 48 at 8 s to 18 at
32 s. A similar fall from 32 s to 60 s leaves it above the candidate's gap of about one edge, so the builder expects
REPLICATED_ADVANTAGE_THROUGH_120X, but with a smaller lead at 60 s.

**Development looks.** None: no host of this seed has been run, and no HiGHS arm above 32 s has run on n60 hosts.

**Status.** A DEV replication. It licenses nothing.
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

from genesis import candidates_v2 as C2  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r63_e1d_crossover as R63  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402

TF = RD.TF
SEED, HOSTS, N, REF_S = 20266601, 20, 60, 120
PARAMS = {'n': N, 'p_in': 0.8, 'p_out': 0.06}
BUDGETS = (32.0, 60.0)
BOOT, BOOT_SEED = 4000, 20266699
MUE = R63.MUE
MIN_DELIVERY = 0.9


def arms():
    A = R63.arms()
    out = {'candidate': A['candidate'], 'highs_32s': A['highs_32s']}
    d = C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': 60.0}, **R63.mip_profile(60.0))
    if C2.descriptor_problems(d, domain=TF):
        raise RuntimeError('highs_60s does not rebuild')
    out['highs_60s'] = ('v2', d)
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
    est = statistics.fmean(d)
    sims = sorted(statistics.fmean(rng.choice(d) for _ in d) for _ in range(BOOT))
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def best_known(r):
    return max([r['optimum'] or 0, r['reference']['lower']] + [a['value'] for a in r['arms'].values()])


def delivery(rows):
    """{arm: (hosts that ran to the limit, median CPU/budget)} for the HiGHS arms."""
    out = {}
    for b in BUDGETS:
        a = R63.arm_name(b)
        ratios = [r['arms'][a]['cpu_ns'] / 1e9 / b for r in rows if r['arms'][a]['value'] < best_known(r)]
        out[a] = (len(ratios), round(statistics.median(ratios), 4) if ratios else None)
    return out


def overall(per, valid):
    if not valid:
        return 'INVALID_CPU_DELIVERY'
    v32, v60 = per['highs_32s']['verdict'], per['highs_60s']['verdict']
    if v32 != 'ADVANTAGE':
        return 'NOT_REPLICATED'
    return 'REPLICATED_ADVANTAGE_THROUGH_120X' if v60 == 'ADVANTAGE' else 'REPLICATED_CROSSOVER_BY_120X'


def verdict(rows):
    cand_fail = sum(r['arms']['candidate']['run'] != 'SUCCESS' for r in rows)
    per = {}
    for b in BUDGETS:
        a = R63.arm_name(b)
        d = [r['arms']['candidate']['value'] - r['arms'][a]['value'] for r in rows]
        est, ci = boot(d)
        fails = sum(r['arms'][a]['run'] != 'SUCCESS' for r in rows)
        per[a] = {'budget_s': b, 'ratio_to_candidate': b / R41.E1_BUDGET, 'estimate': round(est, 4),
                  'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                  'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)],
                  'failures': fails, 'verdict': R63.budget_verdict(ci, fails + cand_fail)}
    dl = delivery(rows)
    valid = all(m is None or m >= MIN_DELIVERY for _, m in dl.values())
    names = ['candidate'] + [R63.arm_name(b) for b in BUDGETS]
    descriptive = {
        'certified': sum(r['optimum'] is not None for r in rows),
        'edges': [min(r['edges'] for r in rows), max(r['edges'] for r in rows)],
        'gap_to_upper_bound': {x: {'mean': round(statistics.fmean(r['reference']['upper'] - r['arms'][x]['value']
                                                                  for r in rows), 4),
                                   'max': max(r['reference']['upper'] - r['arms'][x]['value'] for r in rows)}
                               for x in names},
        'highs_60s_below_32s': sum(r['arms']['highs_60s']['value'] < r['arms']['highs_32s']['value'] for r in rows),
        'reference_wall_s_median': round(statistics.median(r['reference']['wall_s'] for r in rows), 3)}
    return {'verdict': overall(per, valid), 'per_budget': per, 'cpu_delivery': dl, 'valid': valid,
            'candidate_failures': cand_fail, 'hosts': len(rows), 'descriptive': descriptive}


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
            seed = int(digest({'study': 'b20r66', 'task': t.task_id})[:12], 16)
            res, offered = {}, []
            for name, (reg, desc) in A.items():
                res[name], sel = R41.run_arm(t, reg, desc, seed)
                offered.append((name, sel))
            ref, opt = R41.reference(t, offered, registry, REF_S)
            r = {'task_id': t.task_id, 'n': t.n, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id[-4:]} ({len(t.edges)} edges): candidate {res["candidate"]["value"]} highs '
                f'{res["highs_32s"]["value"]} {res["highs_60s"]["value"]} [{ref["lower"]}..{ref["upper"]}] '
                f'{ref["wall_s"]:.1f}s; cpu 32s {res["highs_32s"]["cpu_ns"] / 1e9:.1f} 60s {res["highs_60s"]["cpu_ns"] / 1e9:.1f}')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    v = verdict(rows)
    summary = {'schema': 'genesis-b20r66-e1d-n60-v1', **v,
               'descriptors': {n: d['descriptor_id'] for n, (_, d) in A.items()}, 'seed': SEED,
               'boot_seed': BOOT_SEED, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV replication outside the calibrated settings and the 200-edge custody bound; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {v['verdict']}; " + '; '.join(f"{a} {p['estimate']} {p['interval_90']} {p['verdict']}"
                                                  for a, p in v['per_budget'].items()) + f"; delivery {v['cpu_delivery']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
