#!/usr/bin/env python3
"""B20_R63: how much CPU does an exact MILP solver need to match E1d's 0.5 s candidate? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r63_e1d_crossover.py OUT_DIR      run (resumable) and analyse

**Why.** E1d's claim is "a 0.5 s solver beats an exact MILP at 2 s" (HiGHS at four times the candidate's budget;
B20_R41, R43). Which MIP budget a GV3 comparison must beat is a reviewer decision (B20_R38 record; B20R41-OPEN-1),
and the GV4 fallback draft rests on E1d (Part A). The reviewer needs to know whether the advantage is a
knife-edge at 4x or holds at much larger budgets. Nothing so far has run HiGHS above 2 s on these settings.

**Design (fixed before running).**
  * **Hosts.** 30 fresh DEV hosts, round-robin over the three settings that the B20_R43 calibration record selects
    (rule `e1-hard-v3-draft`): planted_cluster n38 (0.8, 0.07), n40 (0.8, 0.06), n40 (0.7, 0.06). Seed 20266301.
    They exclude every identity `b20r24_repilots.exposure` excludes, which includes every host of B20_R41, R43,
    R44 and R45. The hosts are saved before anything runs and reloaded on resume.
  * **Arms**, all in runc, each on the same host:
      - `candidate`: E1's frozen descriptor (`handoff/e1/candidate_descriptor.json`, 0.5 CPU s of search);
      - `highs_<b>s`: `milp-highs-v1` (registry v2; HiGHS pinned to one core) with `cpu_seconds` b, for
        b in 2, 4, 8, 16 and 32 s, that is 4x, 8x, 16x, 32x and 64x the candidate's budget. The 2 s arm is the E1d
        package's `milp_highs_4x` descriptor itself (checked by id), under E1's profile (2 CPU s, 10 s wall, 2048
        MiB). The others use that profile scaled: `cpu_seconds` b (the sandbox allows b + 1), wall max(10, 5b) s.
  * **Reference.** B20_R41's generated-rows route at 120 s, seeded with the best arm witness. It is used only for
    the descriptive optimum statements; the primary endpoint does not need it.
  * **Primary endpoint, per budget b.** d_b = candidate edges − highs_b edges per host, a failed run scoring 0 (the
    registered convention). Estimate: the mean of the three stratum means. Interval: a stratified bootstrap 90%
    percentile interval (4,000 resamples, seed 20266399).
  * **Verdict per budget** (MUE 0.5, the registered minimum useful effect):
      - ADVANTAGE: the interval's lower end > 0.5;
      - NO_MATERIAL_DIFFERENCE: the whole interval inside (−0.5, 0.5);
      - MIP_AHEAD: the interval's upper end < −0.5;
      - UNRESOLVED: anything else;
      - UNRESOLVED_FAILURES: any run of that HiGHS arm, or of the candidate, failed (it would be scored 0 and could
        manufacture an advantage).
  * **Overall verdict.** The crossover budget is the smallest b whose verdict is not ADVANTAGE.
    ADVANTAGE_THROUGH_64X if there is none; otherwise CROSSOVER_AT_<b>S.
  * **Descriptive, never decisive:** certified hosts per stratum; optimum hits per arm on certified hosts; mean gap
    to the optimum per arm; HiGHS arms whose value falls as the budget rises (time-limit non-monotonicity); the
    reference's wall time.

**Expectation, stated before running.** HiGHS at 2 s reached the optimum on 6 of 30 B20_R41 hosts, while the
generated-rows reference certifies these optima in about 20 s of wall time. The weakness looks like HiGHS's
relaxation, not its search speed, so the builder expects ADVANTAGE at least through 8 s (16x). Beyond that the
builder has no data.

**Development looks.** None: no HiGHS arm above 2 s has been run on any host of these settings before this
commit. The B20_R43 calibration record and the E1d descriptors are read, not re-run.

**Status.** A DEV diagnostic for the reviewer's comparator decision. It licenses nothing, and changes no package,
rule or comparator.
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
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r44_e1d_ablation as R44  # noqa: E402

TF = RD.TF
SEED, N, REF_S = 20266301, 30, 120
BUDGETS = (2.0, 4.0, 8.0, 16.0, 32.0)
BOOT, BOOT_SEED = 4000, 20266399
MUE = 0.5
RECORD = R44.RECORD


def arm_name(b):
    return f'highs_{int(b)}s'


def mip_profile(b):
    """E1's profile (R11.PROFILE: 2 CPU s, 10 s wall) scaled to a b-second HiGHS run; equal to it at b = 2."""
    return {'cpu_seconds': int(b), 'memory_mib': 2048, 'wall_seconds': max(10, int(5 * b)), 'queries': 1000}


def arms():
    cand = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
    out = {'candidate': ('v1', cand)}
    for b in BUDGETS:
        out[arm_name(b)] = ('v2', C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': b}, **mip_profile(b)))
    for name, (reg, desc) in out.items():
        problems = (C1 if reg == 'v1' else C2).descriptor_problems(desc, domain=TF)
        if problems:
            raise RuntimeError(f'{name} does not rebuild: {problems}')
    package = json.loads((ROOT / 'handoff' / 'e1d' / 'baselines.json').read_text())['milp_highs_4x']
    if out['highs_2s'][1]['descriptor_id'] != package['descriptor_id']:
        raise RuntimeError("highs_2s is not the E1d package's milp_highs_4x descriptor")
    if cand['descriptor_id'] != json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text())['descriptor_id']:
        raise RuntimeError("the candidate is not the E1d package's")
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    record = json.loads(RECORD.read_text())
    chosen = record['selected']
    per = [N // len(chosen) + (1 if i < N % len(chosen) else 0) for i in range(len(chosen))]
    tasks, seen = [], set(excluded)
    for i, (s, k) in enumerate(zip(chosen, per)):
        ts, seen, _ = ADAPTERS[TF].generate(SEED + 7919 * i, k, 'DEV', s['family'], s['params'], excluded=seen)
        if RD.identities(ts) & set(excluded):
            raise RuntimeError('a host collides with an excluded identity')
        tasks += ts
    R11.dump(path, {'seed': SEED, 'per_setting': per, 'record_sha256': digest(record),
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def boot(by):
    rng = random.Random(BOOT_SEED)
    strata = sorted(by)
    est = statistics.fmean(statistics.fmean(by[s]) for s in strata)
    sims = sorted(statistics.fmean(statistics.fmean(rng.choice(by[s]) for _ in by[s]) for s in strata)
                  for _ in range(BOOT))
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def budget_verdict(ci, failures):
    lo, hi = ci
    if failures:
        return 'UNRESOLVED_FAILURES'
    if lo > MUE:
        return 'ADVANTAGE'
    if -MUE < lo and hi < MUE:
        return 'NO_MATERIAL_DIFFERENCE'
    if hi < -MUE:
        return 'MIP_AHEAD'
    return 'UNRESOLVED'


def overall(per_budget):
    for b in BUDGETS:
        if per_budget[arm_name(b)]['verdict'] != 'ADVANTAGE':
            return f'CROSSOVER_AT_{int(b)}S', b
    return 'ADVANTAGE_THROUGH_64X', None


def verdict(rows):
    cand_fail = sum(r['arms']['candidate']['run'] != 'SUCCESS' for r in rows)
    per = {}
    for b in BUDGETS:
        a = arm_name(b)
        by = {}
        for r in rows:
            by.setdefault(r['stratum'], []).append(r['arms']['candidate']['value'] - r['arms'][a]['value'])
        est, ci = boot(by)
        fails = sum(r['arms'][a]['run'] != 'SUCCESS' for r in rows)
        d = [x for v in by.values() for x in v]
        per[a] = {'budget_s': b, 'ratio_to_candidate': b / R41.E1_BUDGET, 'estimate': round(est, 4),
                  'interval_90': [round(ci[0], 4), round(ci[1], 4)], 'failures': fails,
                  'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)],
                  'stratum_means': {s: round(statistics.fmean(v), 4) for s, v in sorted(by.items())},
                  'cpu_s_median': round(statistics.median(r['arms'][a]['cpu_ns'] for r in rows) / 1e9, 3),
                  'verdict': budget_verdict(ci, fails + cand_fail)}
    name, cross = overall(per)
    cert = [r for r in rows if r['optimum'] is not None]
    names = ['candidate'] + [arm_name(b) for b in BUDGETS]
    strata = sorted({r['stratum'] for r in rows})
    descriptive = {
        'certified_by_stratum': {s: [sum(r['optimum'] is not None for r in rows if r['stratum'] == s),
                                     sum(r['stratum'] == s for r in rows)] for s in strata},
        'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in cert) for n in names},
        'mean_gap_to_optimum': {n: round(statistics.fmean(r['optimum'] - r['arms'][n]['value'] for r in cert), 4)
                                if cert else None for n in names},
        'exceeds_optimum': {n: sum(r['arms'][n]['value'] > r['optimum'] for r in cert) for n in names},
        'non_monotone_highs': sum(any(r['arms'][arm_name(b2)]['value'] < r['arms'][arm_name(b1)]['value']
                                      for b1, b2 in zip(BUDGETS, BUDGETS[1:])) for r in rows),
        'reference_wall_s_median': round(statistics.median(r['reference']['wall_s'] for r in rows), 3),
    }
    return {'verdict': name, 'crossover_budget_s': cross, 'per_budget': per, 'candidate_failures': cand_fail,
            'hosts': len(rows), 'certified': len(cert), 'descriptive': descriptive}


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
            seed = int(digest({'study': 'b20r63', 'task': t.task_id})[:12], 16)
            res, offered = {}, []
            for n, (reg, desc) in A.items():
                res[n], sel = R41.run_arm(t, reg, desc, seed)
                offered.append((n, sel))
            ref, opt = R41.reference(t, offered, registry, REF_S)
            r = {'task_id': t.task_id, 'stratum': t.family, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id[-4:]}: candidate {res["candidate"]["value"]} highs '
                + ' '.join(str(res[arm_name(b)]['value']) for b in BUDGETS)
                + f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.1f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    v = verdict(rows)
    summary = {'schema': 'genesis-b20r63-e1d-crossover-v1', **v,
               'descriptors': {n: d['descriptor_id'] for n, (_, d) in A.items()}, 'seed': SEED,
               'boot_seed': BOOT_SEED, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV diagnostic for the comparator decision; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {v['verdict']}; " + '; '.join(f"{a} {p['estimate']} {p['interval_90']} {p['verdict']}"
                                                  for a, p in v['per_budget'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
