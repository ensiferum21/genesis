#!/usr/bin/env python3
"""B20_R64: does E1d's advantage over HiGHS grow with host size? (DEV pilot, preregistered)

    taskset -c 1 python3 scripts/b20r64_e1d_scaling.py OUT_DIR      run (resumable) and analyse

**Why.** B20_R63 found that on E1d's settings (n38–40, about 160–200 edges) the 0.5 s candidate's advantage over
HiGHS ends between 8x and 16x its budget: HiGHS proves every optimum in about 6 CPU s. The advantage is speed. If
HiGHS's time to the optimum grows faster with host size than the candidate's quality falls, the crossover moves
out on larger hosts, and a stronger GV3 claim exists there. If the candidate degrades first, E1d is a small-host
result. Either answer matters for the reviewer's comparator decision (B20R41-OPEN-1).

**Scope, stated plainly.** The registered planted-cluster family space stops at n = 40
(`GraphHostAdapter.FAMILY_SPACE`), and hosts above 200 edges are outside the custody path's certificate bound
(`CERTIFICATE_MAX_EDGES`). For n = 50 and 60 this script draws hosts with `generate_beyond_space`, a DEV-only copy
of the adapter's `generate` loop (the same edge model `_edges`, seeding, task ids, exposure identities and
de-duplication) without the family-space check. Such hosts are outside every calibrated E1d setting. This is a DEV pilot; it
changes no rule, bound or package. Its primary endpoint needs no certified optimum: each arm's witness is
re-checked by the domain checker, and the comparison is of edge counts.

**Design (fixed before running).**
  * **Hosts.** planted_cluster with p_in 0.8, p_out 0.06 (the densest E1d setting at n40) at n = 40, 50 and 60.
    10 fresh DEV hosts per n, seed 20266401. They exclude every identity `b20r24_repilots.exposure` excludes.
    Saved before anything runs, reloaded on resume.
  * **Arms**, all in runc: E1's frozen candidate (0.5 CPU s of search, the E1d package's descriptor), and
    `milp-highs-v1` at 2, 8 and 32 s (4x, 16x, 64x), with B20_R63's descriptors.
  * **Reference.** B20_R41's generated-rows route at 120 s, seeded with the best arm witness; descriptive only
    (certified counts, gaps). It is called directly, as in B20_R41 and R63, so the 200-edge custody bound does
    not apply to it.
  * **Endpoint, per n and budget b.** d = candidate − highs_b per host (a failed run scores 0). Estimate: the
    mean; interval: bootstrap 90% percentile (4,000 resamples, seed 20266499).
  * **Verdict per (n, b):** B20_R63's rule: ADVANTAGE iff the lower end > 0.5; NO_MATERIAL_DIFFERENCE,
    MIP_AHEAD, UNRESOLVED; UNRESOLVED_FAILURES if any run of the candidate or that arm failed.
  * **Crossover per n:** the smallest b whose verdict is not ADVANTAGE; none means beyond 64x.
  * **Overall verdict**, comparing n = 60 with n = 40:
      - ADVANTAGE_GROWS: the crossover at n60 is later than at n40 (none counts as later than any budget);
      - ADVANTAGE_SHRINKS: earlier;
      - UNCHANGED: the same;
      - UNRESOLVED_FAILURES: if a failure decides either crossover.
  * **Descriptive:** host edges per n; certified counts; the best known value per host (the larger of the
    certified optimum and the best arm); each arm's gap to it; HiGHS non-monotonicity; the reference's time.

**Expectation, stated before running.** The builder expects ADVANTAGE_GROWS: on dense planted clusters the cut
representation should stay near-optimal, while an exact MILP's time should grow quickly with size. B20_R63 showed
that the builder's reading of HiGHS can be wrong, so this is a weak expectation.

**Development looks.** None: no host above n40 in this family has been run by any arm before this commit.

**Status.** A DEV pilot. It licenses nothing, and no package, rule or bound changes.
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

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r63_e1d_crossover as R63  # noqa: E402

TF = RD.TF
SEED, PER, REF_S = 20266401, 10, 120
NS = (40, 50, 60)
PARAMS = {'p_in': 0.8, 'p_out': 0.06}
BUDGETS = (2.0, 8.0, 32.0)
BOOT, BOOT_SEED = 4000, 20266499
MUE = R63.MUE


def arms():
    A = R63.arms()
    return {n: A[n] for n in ['candidate'] + [R63.arm_name(b) for b in BUDGETS]}


def generate_beyond_space(seed, count, split, params, excluded):
    """`GraphHostAdapter.generate` for planted_cluster without the family-space check (DEV only): the same
    seeding, edge model, task ids, exposure identities and de-duplication."""
    from genesis.domains import Unsupported
    A, family = ADAPTERS[TF], 'planted_cluster'
    rng = random.Random(digest({'seed': seed, 'family': family, 'params': params, 'domain': A.name}))
    seen, out, tries = set(excluded), [], 0
    tag = digest({'family': family, 'params': params})[:8]
    while len(out) < count and tries < count * 200:
        tries += 1
        edges = A._edges(rng, family, params)
        task = GraphTask(task_id=f'{split.lower()}-{family}-{tag}-{seed}-{len(out):04}', domain=A.name,
                         n=params['n'], edges=edges, family=f'{family}:{tag}', split=split)
        identity = A.exposure_identity(task)
        if isinstance(identity, Unsupported) or identity['canonical'] in seen:
            continue
        seen.add(identity['canonical'])
        out.append(task)
    if len(out) != count:
        raise RuntimeError(f'only {len(out)} of {count} distinct tasks')
    return out, seen


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, seen = [], set(excluded)
    space_n = ADAPTERS[TF].FAMILY_SPACE['planted_cluster']['n'][1]
    for i, n in enumerate(NS):
        if n <= space_n:
            ts, seen, _ = ADAPTERS[TF].generate(SEED + 7919 * i, PER, 'DEV', 'planted_cluster', dict(PARAMS, n=n),
                                                excluded=seen)
        else:
            ts, seen = generate_beyond_space(SEED + 7919 * i, PER, 'DEV', dict(PARAMS, n=n), seen)
        if RD.identities(ts) & set(excluded):
            raise RuntimeError('a host collides with an excluded identity')
        tasks += ts
    R11.dump(path, {'seed': SEED, 'ns': list(NS), 'params': PARAMS, 'per_n': PER,
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def boot(d):
    rng = random.Random(BOOT_SEED)
    est = statistics.fmean(d)
    sims = sorted(statistics.fmean(rng.choice(d) for _ in d) for _ in range(BOOT))
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def crossover(per):
    """The first budget whose verdict is not ADVANTAGE (None: beyond the grid), and whether a failure decided it."""
    for b in BUDGETS:
        v = per[R63.arm_name(b)]['verdict']
        if v != 'ADVANTAGE':
            return b, v == 'UNRESOLVED_FAILURES'
    return None, False


def _later(a, b):
    """Is crossover a later than crossover b? None is beyond every budget."""
    return (a is None and b is not None) or (a is not None and b is not None and a > b)


def overall(cross):
    (c40, f40), (c60, f60) = cross[NS[0]], cross[NS[-1]]
    if f40 or f60:
        return 'UNRESOLVED_FAILURES'
    if _later(c60, c40):
        return 'ADVANTAGE_GROWS'
    if _later(c40, c60):
        return 'ADVANTAGE_SHRINKS'
    return 'UNCHANGED'


def verdict(rows):
    names = ['candidate'] + [R63.arm_name(b) for b in BUDGETS]
    by_n, cross = {}, {}
    for n in NS:
        rs = [r for r in rows if r['n'] == n]
        cand_fail = sum(r['arms']['candidate']['run'] != 'SUCCESS' for r in rs)
        per = {}
        for b in BUDGETS:
            a = R63.arm_name(b)
            d = [r['arms']['candidate']['value'] - r['arms'][a]['value'] for r in rs]
            est, ci = boot(d)
            fails = sum(r['arms'][a]['run'] != 'SUCCESS' for r in rs)
            per[a] = {'budget_s': b, 'estimate': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                      'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)],
                      'failures': fails, 'cpu_s_median': round(statistics.median(r['arms'][a]['cpu_ns'] for r in rs) / 1e9, 3),
                      'verdict': R63.budget_verdict(ci, fails + cand_fail)}
        c, failed = crossover(per)
        cross[n] = (c, failed)
        best = [max([r['optimum'] or 0] + [r['arms'][x]['value'] for x in names]) for r in rs]
        by_n[str(n)] = {
            'hosts': len(rs), 'edges': [min(r['edges'] for r in rs), max(r['edges'] for r in rs)],
            'per_budget': per, 'crossover_budget_s': c, 'candidate_failures': cand_fail,
            'certified': sum(r['optimum'] is not None for r in rs),
            'mean_gap_to_best_known': {x: round(statistics.fmean(bk - r['arms'][x]['value'] for bk, r in zip(best, rs)), 4)
                                       for x in names},
            'at_best_known': {x: sum(r['arms'][x]['value'] == bk for bk, r in zip(best, rs)) for x in names},
            'non_monotone_highs': sum(any(r['arms'][R63.arm_name(b2)]['value'] < r['arms'][R63.arm_name(b1)]['value']
                                          for b1, b2 in zip(BUDGETS, BUDGETS[1:])) for r in rs),
            'reference_wall_s_median': round(statistics.median(r['reference']['wall_s'] for r in rs), 3)}
    return {'verdict': overall(cross), 'by_n': by_n, 'hosts': len(rows)}


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
            seed = int(digest({'study': 'b20r64', 'task': t.task_id})[:12], 16)
            res, offered = {}, []
            for name, (reg, desc) in A.items():
                res[name], sel = R41.run_arm(t, reg, desc, seed)
                offered.append((name, sel))
            ref, opt = R41.reference(t, offered, registry, REF_S)
            r = {'task_id': t.task_id, 'n': t.n, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'n{t.n} {t.task_id[-4:]} ({len(t.edges)} edges): candidate {res["candidate"]["value"]} highs '
                + ' '.join(str(res[R63.arm_name(b)]['value']) for b in BUDGETS)
                + f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.1f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    v = verdict(rows)
    summary = {'schema': 'genesis-b20r64-e1d-scaling-v1', **v,
               'descriptors': {n: d['descriptor_id'] for n, (_, d) in A.items()}, 'seed': SEED,
               'boot_seed': BOOT_SEED, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV pilot outside the calibrated settings and the 200-edge custody bound; licenses nothing'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {v['verdict']}; " + '; '.join(f"n{n}: crossover {x['crossover_budget_s']}" for n, x in v['by_n'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
