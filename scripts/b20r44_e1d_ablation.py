#!/usr/bin/env python3
"""B20_R44: a registered ablation of E1's discovered representation, and an E1d ablation re-pilot
(DEV; GV3 path, causal control; B20R41-OPEN-1).

    taskset -c 0 python3 scripts/b20r44_e1d_ablation.py OUT_DIR      run (resumable) and analyse

**Why.** GV3 asks that a *checked machine-produced discovery* helps on fresh tasks beyond strong
baselines, with controls. E1d's candidate is represent-and-repair over the representation
`cross_2`, which B18's representation grammar proposed. Lean checked the representation's
soundness, and DEV ranking chose it. B20_R41 showed the candidate beats every registered baseline in
the dense family. It did not show that the discovered representation is what helps. Until now no
transform was registered for that component, so it could not license any causal level
(replay_contracts: "Components without a registered transform cannot license a causal level").

**The registered ablation (kernel/replay_contracts.INTERVENTIONS, added in this commit).**
  * The component is `representation` of represent-and-repair-v1.
  * Ablation: `cross_2` → `ordered_2`. This is the same grammar, encoder space (2^n), search,
    repair and budget. Only the decoder is weaker.
  * B18's package records the checks:
      - Lean checked `ordered_2_within_cross_2`: for every encoding, ordered_2 decodes a subset of
        cross_2;
      - the converse `cross_2_within_ordered_2` is DISPROVED;
      - ordered_2 is sound on triangle-free hosts (`ordered_2_sound_tf`, CHECKED).
    The ablation therefore removes information the discovered decoder keeps, and nothing else.
  * No placebo is registered. The only other sound k = 2 decoder, `adjacent_2`, is Lean-checked equal
    to cross_2 in both directions. It would be an identical arm, not an inert one. So at most
    ABLATION_SUPPORTED can be licensed.
  * Descriptor ids are unchanged: interventions live in the kernel, not in candidates.py.
  * One older test changes on purpose. B20_R15's test asserted that represent-and-repair had *no*
    registered intervention (tests_genesis/test_b14_open4_contracts.py). It now asserts this
    ablation, the absence of a placebo, and the refusal of every other representation.

**A negative control (a null arm; the idea of null worlds comes from the MISSING-BIT-1 design material the user
supplied).** The arm `adjacent_2` is Lean-checked EQUAL to cross_2: both `cross_2_within_adjacent_2` and
`adjacent_2_within_cross_2` are CHECKED. It has the same search and budget. The truth here is known: no
difference. So the arm measures what the whole pipeline (sandbox, timing-dependent search, reference,
analysis) reports when there is none.
  * The prediction is candidate − null ≈ 0.
  * NULL_CONTROL_CLEAN iff the 90% t-interval of the per-host difference lies inside ±0.5, the
    minimum useful effect. Otherwise NULL_CONTROL_FLAGGED, which would cast doubt on any effect this
    pipeline reports at that size.
  * It is not a placebo and licenses nothing causal.

**The re-pilot (fixed before running).**
  * 30 fresh DEV hosts, round-robin over the settings that the B20_R43 calibration record (B20_R41's
    rows, rule `e1-hard-v3-draft`) selects. Seed 20264401. They exclude every identity
    b20r24_repilots.exposure excludes, including all B20_R41 and B20_R43 hosts.
  * The hosts are saved before anything runs, and reloaded on resume.
  * Arms, all in runc under E1's profile:
      - E1's frozen candidate;
      - its registered ablation, checked by replay_contracts.intervention_problems;
      - the null control (`adjacent_2`).
  * Reference: B20_R41's generated-rows route, seeded with the best arm witness, at 120 s.
  * Analysis: b20r41_e1d_readiness.analyse, with the ablation as the only comparator.
      - This gives the 75% certification gate per stratum, the B19 DRAFT plan core (minimum useful
        effect 0.5, cost ratio at most 3.0), a dry run and the centred power model.
      - Verdicts: UNSETTLED_REFERENCE / EFFECT_BELOW_MUE / COST_RULE_FAILS / UNDERPOWERED /
        READY_FOR_REVIEW.

**Development look (disclosed).** On three B20_R41 pilot hosts, which were already exposed, both
new descriptors rebuilt. No new hosts were used.
  * The ablation scored 106, 116 and 107, against the candidate's 117, 126 and 115 (the optima).
  * The null control scored 117, 126 and 115.

**Status.** A DEV readiness study for a causal follow-up. It licenses nothing. A real
ABLATION_SUPPORTED level needs three things: a custodian-signed ablation evaluation of the claim, a
reviewer accepting the registered transform, and the E1d adoption decisions (B20R41-OPEN-1).
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import candidates as C1  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.kernel import replay_contracts as RC  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r37_generator_v2 as R37  # noqa: E402
import b20r41_e1d_readiness as R41  # noqa: E402

TF = RD.TF
SEED, N, REF_S = 20264401, 30, 120
RECORD = ROOT / 'evidence' / 'e1d_package_b20r43' / 'calibration_triangle_free_host_v1_e1_hard_v3_draft.json'


def arms():
    cand = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
    abl = C1.build_descriptor('represent-and-repair-v1', TF, dict(cand['parameters'], representation='ordered_2'),
                              **cand['resource_profile'])
    why, path = RC.intervention_problems('ablation', cand, abl)
    if why or path != ('representation',):
        raise RuntimeError(f'the ablation is not the registered one: {why} {path}')
    null = C1.build_descriptor('represent-and-repair-v1', TF, dict(cand['parameters'], representation='adjacent_2'),
                               **cand['resource_profile'])
    if C1.descriptor_problems(null, domain=TF):
        raise RuntimeError('the null control does not rebuild')
    return {'candidate': cand, 'ablation': abl, 'null_control': null}


def null_control(rows):
    """Candidate − null control: mean, 90% t-interval, and CLEAN iff the interval lies inside ±0.5."""
    import math
    import statistics
    from scipy.stats import t as tdist
    d = [r['arms']['candidate']['value'] - r['arms']['null_control']['value'] for r in rows]
    n, mean = len(d), statistics.fmean(d)
    sd = statistics.stdev(d) if n > 1 else 0.0
    half = tdist.ppf(0.95, n - 1) * sd / math.sqrt(n) if n > 1 else float('inf')
    lo, hi = mean - half, mean + half
    return {'mean': round(mean, 4), 'interval_90': [round(lo, 4), round(hi, 4)], 'sd': round(sd, 4),
            'wins_ties_losses': [sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)],
            'equivalence_margin': 0.5,
            'verdict': 'NULL_CONTROL_CLEAN' if -0.5 < lo and hi < 0.5 else 'NULL_CONTROL_FLAGGED'}


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
            seed = int(digest({'study': 'b20r44', 'task': t.task_id})[:12], 16)
            res, offered = {}, []
            for n, desc in A.items():
                res[n], sel = R41.run_arm(t, 'v1', desc, seed)
                offered.append((n, sel))
            ref, opt = R41.reference(t, offered, registry, REF_S)
            r = {'task_id': t.task_id, 'stratum': t.family, 'split': t.split, 'edges': len(t.edges), 'arms': res,
                 'reference': ref, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id[-4:]}: candidate {res["candidate"]["value"]} ablation {res["ablation"]["value"]} '
                f'null {res["null_control"]["value"]} opt {opt} [{ref["lower"]}..{ref["upper"]}] {ref["wall_s"]:.1f}s')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    analysis, power = R41.analyse(rows, ['candidate', 'ablation', 'null_control'], ['ablation'])
    analysis['negative_control'] = null_control(rows)
    R11.dump(out / 'pilot_summary.json', analysis)
    if power is not None:
        R11.dump(out / 'power_analysis_centred.json', power)
    summary = {'schema': 'genesis-b20r44-e1d-ablation-v1', 'verdict': analysis['verdict'],
               'negative_control': analysis['negative_control']['verdict'],
               'intervention': {'component': 'representation', 'kind': 'ablation', 'from': 'cross_2', 'to': 'ordered_2',
                                'meaning': RC.INTERVENTIONS[('represent-and-repair-v1', ('representation',))]['meaning']},
               'descriptors': {n: d['descriptor_id'] for n, d in A.items()}, 'pilot': analysis, 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV causal-readiness pilot; licenses nothing; the transform awaits review'}
    R11.dump(out / 'summary.json', summary)
    log(f'verdict {analysis["verdict"]}; mean {analysis.get("mean_difference")}; cpu ratio '
        f'{analysis["cpu_ratio_candidate_to_comparator"]}; negative control {analysis["negative_control"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
