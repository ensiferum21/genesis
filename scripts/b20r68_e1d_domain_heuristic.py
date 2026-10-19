#!/usr/bin/env python3
"""B20_R68: is E1d's candidate beyond a standard max-cut heuristic? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r68_e1d_domain_heuristic.py OUT_DIR    run (resumable) and analyse; run it ALONE

**Why.** E1d's claim is that E1's frozen candidate (0.5 CPU s) beats the strongest of five registered baselines, the
strongest being the exact MILP HiGHS at four times its budget (B20_R41, R43; the GV4 fallback's Part A). A review of
the B20_R65 handover found that the candidate is itself the simplest classical method for this problem: with the
`cross_2` decoder, `represent_and_repair` is one-flip local search for a maximum cut from random two-colourings,
followed by a greedy triangle-free completion. On dense hosts the largest triangle-free subgraph is close to a
maximum cut. None of the five baselines is a max-cut heuristic, so "beyond strong baselines" has only been measured
against a generic exact solver and fixed DSL programs. The reviewer's strong-baseline decision (review brief item 1)
needs the comparison with a standard method of the field. B20_R67 added one: `maxcut-tabu-v1`, tabu search over
one-vertex flips with the same completion.

**Design (fixed before running).**
  * **Part A, the calibrated E1d settings.** 30 fresh DEV hosts, round-robin over the three planted settings the
    B20_R43 calibration record selects (as B20_R63), seed 20266801.
  * **Part B, larger hosts beyond the family space** (as B20_R64/R66): 20 fresh DEV hosts, planted_cluster n60
    (p_in 0.8, p_out 0.06), drawn by `b20r64_e1d_scaling.generate_beyond_space`, seed 20266811.
  * Both exclude every identity `b20r24_repilots.exposure` excludes (all earlier hosts, B20_R66's included), and
    Part B also excludes Part A's hosts. The hosts are saved before anything runs and reloaded on resume.
  * **Arms**, all in runc under E1's profile (2 CPU s, 2048 MiB, 10 s wall, 1000 queries), on the same host:
      - `candidate`: E1's frozen descriptor (`handoff/e1d/candidate_descriptor.json`), 0.5 CPU s of search;
      - `tabu_0.5s`: `maxcut-tabu-v1` with `cpu_seconds` 0.5, the time-matched domain heuristic;
      - `tabu_2s`: `maxcut-tabu-v1` with `cpu_seconds` 2.0, at the budget E1d's comparator gets;
      - `highs_2s`: the E1d package's `milp_highs_4x` descriptor (HiGHS at 2 s), checked by id.
  * **Reference.** B20_R41's generated-rows route at 120 s, seeded with the evaluator's seed and the best arm
    witness (`b20r41_e1d_readiness.reference`). Descriptive; the primary endpoint does not need it.
  * **Primary endpoint.** d = candidate − tabu_0.5s edges per host (a failed run scores 0). Part A: the mean of the
    three stratum means with a stratified bootstrap 90% percentile interval; Part B: the mean with a bootstrap 90%
    percentile interval. 4,000 resamples, seed 20266899.
  * **Verdict per part** (B20_R63's rule, MUE 0.5):
      - CANDIDATE_AHEAD: the interval's lower end > 0.5;
      - NO_MATERIAL_DIFFERENCE: the whole interval inside (−0.5, 0.5);
      - HEURISTIC_AHEAD: the interval's upper end < −0.5;
      - UNRESOLVED: anything else;
      - UNRESOLVED_FAILURES: any run of `candidate` or `tabu_0.5s` failed;
      - INVALID_CPU_DELIVERY (B20_R64's lesson, checked first): the median cgroup CPU of `candidate` or of
        `tabu_0.5s` over the part's hosts is below 0.9 × 0.5 s. Both search until their budget is spent, so a lower
        figure means the machine did not deliver the budget, and nothing else in that part is read.
  * **Overall verdict** (from Part A, the calibrated settings): E1D_BEYOND_DOMAIN_HEURISTIC, E1D_MATCHES_DOMAIN_HEURISTIC,
    DOMAIN_HEURISTIC_AHEAD, INVALID_CPU_DELIVERY or UNRESOLVED, for CANDIDATE_AHEAD, NO_MATERIAL_DIFFERENCE,
    HEURISTIC_AHEAD, INVALID_CPU_DELIVERY or anything else. Part B's verdict is reported beside it.
  * **Secondary, descriptive, never decisive:** candidate − tabu_2s; tabu_0.5s − highs_2s (does the standard heuristic
    also beat E1d's comparator?); per arm, optimum hits on certified hosts (Part A) and the mean gap to the reference's
    proven upper bound (Part B); failures; median cgroup CPU per arm.

**Expectation, stated before running.** In Part A the candidate is at the certified optimum on 29–30 of 30 hosts
(B20_R41, R63), so the heuristic can at most tie it there: NO_MATERIAL_DIFFERENCE, overall
E1D_MATCHES_DOMAIN_HEURISTIC, with tabu_0.5s also far above highs_2s. Part B is open. B20_R66 found the candidate
1.65 edges below a proven upper bound on average at n60, and optimal on only 4 of 10 certified hosts, so there is
room above it; tabu search is the stronger max-cut search, and the builder leans to HEURISTIC_AHEAD or UNRESOLVED
there, without data on the heuristic.

**What it decides.** Nothing about packages, rules or comparators. It informs the reviewer's strong-baseline
decision and the wording of E1d's claim: if the domain heuristic matches the candidate, E1d's result is "a standard
max-cut method beats a generic exact MILP at up to 8x its budget", and the discovery is the representation search
rediscovering the max-cut reduction.

**Development looks.** None: `maxcut-tabu-v1` has run only on its unit-test hosts (K10, a bipartite host, and one
planted n30 host of seed 20266701), and no host of these seeds has been drawn.

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
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402
import b20r44_e1d_ablation as R44  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402

TF = RD.TF
SEED_A, N_A, SEED_B, N_B, REF_S = 20266801, 30, 20266811, 20, 120
PARAMS_B = {'n': 60, 'p_in': 0.8, 'p_out': 0.06}
BOOT, BOOT_SEED, MUE = 4000, 20266899, 0.5
PROFILE = R11.PROFILE
PRIMARY = 'tabu_0.5s'
SEARCH_S, MIN_DELIVERY = 0.5, 0.9


def arms():
    cand = json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text())
    highs = json.loads((ROOT / 'handoff' / 'e1d' / 'baselines.json').read_text())['milp_highs_4x']
    out = {'candidate': ('v1', cand),
           'tabu_0.5s': ('v2', C2.build_descriptor('maxcut-tabu-v1', TF, {'cpu_seconds': 0.5}, **PROFILE)),
           'tabu_2s': ('v2', C2.build_descriptor('maxcut-tabu-v1', TF, {'cpu_seconds': 2.0}, **PROFILE)),
           'highs_2s': ('v2', highs)}
    for name, (reg, desc) in out.items():
        problems = (C1 if reg == 'v1' else C2).descriptor_problems(desc, domain=TF)
        if problems:
            raise RuntimeError(f'{name} does not rebuild: {problems}')
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        d = json.loads(path.read_text())
        return {p: [GraphTask.model_validate_json(canonical(t)) for t in d[p]] for p in ('A', 'B')}
    record = json.loads(R44.RECORD.read_text())
    chosen = record['selected']
    per = [N_A // len(chosen) + (1 if i < N_A % len(chosen) else 0) for i in range(len(chosen))]
    a, seen = [], set(excluded)
    for i, (s, k) in enumerate(zip(chosen, per)):
        ts, seen, _ = ADAPTERS[TF].generate(SEED_A + 7919 * i, k, 'DEV', s['family'], s['params'], excluded=seen)
        a += ts
    b, seen = R64.generate_beyond_space(SEED_B, N_B, 'DEV', PARAMS_B, seen)
    if RD.identities(a + b) & set(excluded):
        raise RuntimeError('a host collides with an excluded identity')
    R11.dump(path, {'seeds': {'A': SEED_A, 'B': SEED_B}, 'per_setting_A': per, 'record_sha256': digest(record),
                    'params_B': PARAMS_B, 'A': [t.model_dump(mode='json') for t in a],
                    'B': [t.model_dump(mode='json') for t in b]})
    return {'A': a, 'B': b}


def boot(by):
    rng = random.Random(BOOT_SEED)
    strata = sorted(by)
    est = statistics.fmean(statistics.fmean(by[s]) for s in strata)
    sims = sorted(statistics.fmean(statistics.fmean(rng.choice(by[s]) for _ in by[s]) for s in strata)
                  for _ in range(BOOT))
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def part_verdict(ci, failures, delivered=True):
    lo, hi = ci
    if not delivered:
        return 'INVALID_CPU_DELIVERY'
    if failures:
        return 'UNRESOLVED_FAILURES'
    if lo > MUE:
        return 'CANDIDATE_AHEAD'
    if -MUE < lo and hi < MUE:
        return 'NO_MATERIAL_DIFFERENCE'
    if hi < -MUE:
        return 'HEURISTIC_AHEAD'
    return 'UNRESOLVED'


OVERALL = {'CANDIDATE_AHEAD': 'E1D_BEYOND_DOMAIN_HEURISTIC', 'NO_MATERIAL_DIFFERENCE': 'E1D_MATCHES_DOMAIN_HEURISTIC',
           'HEURISTIC_AHEAD': 'DOMAIN_HEURISTIC_AHEAD', 'INVALID_CPU_DELIVERY': 'INVALID_CPU_DELIVERY'}


def contrast(rows, a, b):
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['arms'][a]['value'] - r['arms'][b]['value'])
    est, ci = boot(by)
    d = [x for v in by.values() for x in v]
    return {'estimate': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
            'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)],
            'stratum_means': {s: round(statistics.fmean(v), 4) for s, v in sorted(by.items())}}, ci


def analyse_part(rows, names):
    primary, ci = contrast(rows, 'candidate', PRIMARY)
    fails = {n: sum(r['arms'][n]['run'] != 'SUCCESS' for r in rows) for n in names}
    cpu = {n: statistics.median(r['arms'][n]['cpu_ns'] for r in rows) / 1e9 for n in names}
    delivered = all(cpu[n] >= MIN_DELIVERY * SEARCH_S for n in ('candidate', PRIMARY))
    primary['verdict'] = part_verdict(ci, fails['candidate'] + fails[PRIMARY], delivered)
    cert = [r for r in rows if r['optimum'] is not None]
    out = {'hosts': len(rows), 'certified': len(cert), 'primary_candidate_minus_tabu_0.5s': primary,
           'secondary': {'candidate_minus_tabu_2s': contrast(rows, 'candidate', 'tabu_2s')[0],
                         'tabu_0.5s_minus_highs_2s': contrast(rows, 'tabu_0.5s', 'highs_2s')[0],
                         'candidate_minus_highs_2s': contrast(rows, 'candidate', 'highs_2s')[0]},
           'failures': fails,
           'optimum_hits': {n: sum(r['arms'][n]['value'] == r['optimum'] for r in cert) for n in names},
           'mean_gap_to_upper_bound': {n: round(statistics.fmean(r['reference']['upper'] - r['arms'][n]['value']
                                                                 for r in rows), 4) for n in names},
           'cpu_s_median': {n: round(cpu[n], 3) for n in names}, 'cpu_delivered': delivered,
           'reference_wall_s_median': round(statistics.median(r['reference']['wall_s'] for r in rows), 3)}
    return out


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
    H = hosts(out, log, excluded)
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for part in ('A', 'B'):
            for t in H[part]:
                if t.task_id in done:
                    continue
                seed = int(digest({'study': 'b20r68', 'task': t.task_id})[:12], 16)
                res, offered = {}, []
                for n, (reg, desc) in A.items():
                    res[n], sel = R41.run_arm(t, reg, desc, seed)
                    offered.append((n, sel))
                ref, opt = R41.reference(t, offered, registry, REF_S)
                r = {'part': part, 'task_id': t.task_id, 'stratum': t.family, 'split': t.split, 'edges': len(t.edges),
                     'arms': res, 'reference': ref, 'optimum': opt}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
                log(f'{part} {t.task_id[-4:]}: ' + ' '.join(f'{n} {res[n]["value"]}' for n in A)
                    + f' opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.1f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    names = list(A)
    parts = {p: analyse_part([r for r in rows if r['part'] == p], names) for p in ('A', 'B')}
    va = parts['A']['primary_candidate_minus_tabu_0.5s']['verdict']
    summary = {'schema': 'genesis-b20r68-e1d-domain-heuristic-v1', 'verdict': OVERALL.get(va, 'UNRESOLVED'),
               'part_verdicts': {p: parts[p]['primary_candidate_minus_tabu_0.5s']['verdict'] for p in parts},
               'parts': parts, 'descriptors': {n: d['descriptor_id'] for n, (_, d) in A.items()},
               'seeds': {'A': SEED_A, 'B': SEED_B, 'boot': BOOT_SEED}, 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV diagnostic for the strong-baseline decision; licenses nothing; no package changed'}
    R11.dump(out / 'summary.json', summary)
    log(f"verdict {summary['verdict']}; parts {summary['part_verdicts']}; "
        + '; '.join(f"{p}: {parts[p]['primary_candidate_minus_tabu_0.5s']['estimate']} "
                    f"{parts[p]['primary_candidate_minus_tabu_0.5s']['interval_90']}" for p in parts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
