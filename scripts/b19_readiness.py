#!/usr/bin/env python3
"""B19: E1 and E2 readiness on DEV material (roadmap B19 "E1/E2 after DEV readiness").

  b19_readiness.py OUT_DIR

E1 (useful checked solver improvement). The candidate is B18's representation-and-repair
solver with the cut representation (cross_2), defined by its code identity and its
parameters. A fresh DEV pilot from the adopted triangle-free calibration compares it with
every fixed DSL baseline; the strongest baseline is the comparator, as the custodian rule
requires. The minimum useful effect and the design effect below were written before the
pilot ran. The output is a DRAFT decision record: no sealed task exists, nothing is
frozen or registered, and the custodian's evaluator cannot yet run this candidate (it
executes DSL programs only; see B19-OPEN-3).

E2 (concept/theory catalysis). A design draft from the DEV results of B18 and B19:
enabled, removed, placebo, equivalent-information alternative and effort arms, paired by
statement. It separates "helps this prover" from "new mathematics" (W17 found prior art
for the concept).
"""
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as C  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.domains import ADAPTERS, Unsupported  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.execution import execute  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.kernel.analysis import PLAN_SCHEMA, SENSITIVITY, plan_core  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402

PILOT_SEED = 20261026
PILOT_TASKS = 60
CANDIDATE = {'solver': 'genesis.invention.representations.represent_and_repair', 'representation': 'cross_2',
             'repair': 'tf_add_ok (greedy triangle-free completion)', 'cpu_seconds': 0.5,
             'seed_rule': 'int(digest({seed, task_id})[:12], 16)'}
# Fixed before the pilot ran (assumptions for review, not estimates):
MINIMUM_USEFUL_EFFECT = 0.5          # edges per task
DESIGN_EFFECT = 1.0                  # edges per task
MIN_TASKS_PER_STRATUM = 10


def candidate_identity():
    src = inspect.getsource(R)
    return {'module_sha256': hashlib.sha256(src.encode()).hexdigest(), 'parameters': CANDIDATE,
            'identity': digest({'m': hashlib.sha256(src.encode()).hexdigest(), 'p': CANDIDATE})}


def plan():
    return {'schema': PLAN_SCHEMA, 'primary': 'paired-edge-difference', 'estimand': 'mean-of-stratum-means',
            'strata': 'family', 'minimum_useful_effect': MINIMUM_USEFUL_EFFECT, 'design_effect': DESIGN_EFFECT,
            'alpha': 0.05, 'power_target': 0.8, 'test': 'stratified-sign-flip',
            'interval': {'method': 'stratified-bootstrap-percentile', 'level': 0.9, 'resamples': 4000},
            'multiplicity': {'method': 'holm', 'family_id': 'sealed_evaluation:triangle_free_host_v1',
                             'family_size': 3},
            'stopping': {'rule': 'single-analysis'}, 'failures': 'score-zero', 'unsupported': 'exclude-and-report',
            'max_unsupported_fraction': 0.05, 'cost': {'measure': 'cpu_ns', 'max_ratio': 3.0},
            'regression': {'max_stratum_loss': 1.0}, 'sensitivity': list(SENSITIVITY),
            'decision_rule': 'superiority-with-minimum-useful-effect', 'decision_record_sha256': '0' * 64}


def e1(out, log):
    record = C.load('triangle_free_host_v1', ROOT)
    tasks, _ = C.calibrated_panel(record, PILOT_SEED, PILOT_TASKS, 'DEV', excluded=set())
    C.require_dev(tasks)
    limits = C.CALIBRATION_LIMITS
    cross = next(r for r in R.proposals() if r['id'] == 'cross_2')
    runs, optima = {}, {}
    for t in tasks:
        adapter = ADAPTERS[t.domain]
        ref = adapter.reference(t, seconds=30)
        optima[t.task_id] = None if isinstance(ref, Unsupported) else ref['value']
        seed = int(digest({'seed': PILOT_SEED, 'task': t.task_id})[:12], 16)
        for name, prog in sorted(baseline_programs().items()):
            r = execute(t, prog, limits, seed)
            ok = r['status'] == 'SUCCESS'
            runs[(t.task_id, name)] = {'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED',
                                       'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else r['wall_ns']}
        c0 = time.process_time_ns()
        rr = R.represent_and_repair(t.n, t.edges, cross, R.tf_add_ok, cpu_seconds=CANDIDATE['cpu_seconds'], seed=seed)
        cpu = time.process_time_ns() - c0
        v = adapter.validate(t, rr['witness'])
        runs[(t.task_id, 'candidate')] = {'value': rr['value'] if v['status'] == 'VALID' else 0,
                                          'run': 'SUCCESS' if v['status'] == 'VALID' else 'FAILED', 'cpu_ns': cpu}
        log(f'{t.task_id}: optimum {optima[t.task_id]}, candidate {runs[(t.task_id, "candidate")]["value"]}, '
            f'baselines { {n: runs[(t.task_id, n)]["value"] for n in baseline_programs()} }')
    totals = {name: sum(runs[(t.task_id, name)]['value'] for t in tasks) for name in baseline_programs()}
    strongest = max(totals, key=lambda n: (totals[n], n))
    rows = [{'task_id': t.task_id, 'stratum': t.family, 'status': 'SCORED', 'split': t.split,
             'optimum': optima[t.task_id], 'candidate': runs[(t.task_id, 'candidate')],
             'baseline': runs[(t.task_id, strongest)]}
            for t in tasks if optima[t.task_id] is not None]
    (out / 'e1').mkdir(parents=True, exist_ok=True)
    (out / 'e1' / 'pilot_rows.json').write_text(json.dumps(rows, indent=1, sort_keys=True) + '\n')
    (out / 'e1' / 'baseline_totals.json').write_text(json.dumps({'totals': totals, 'strongest': strongest},
                                                                 indent=1, sort_keys=True) + '\n')
    return design(out, rows, totals, strongest, digest(record), limits)


def design(out, rows, totals, strongest, calibration_sha, limits):
    """Power and the DRAFT decision record from the pilot rows. Two headroom models are
    reported: the B16 one (candidate headroom) and the centred one added in B19; the
    draft embeds the centred one and says so (B19-OPEN-4)."""
    p = plan()
    power_b16 = required_sample(rows, p, sims=1000, min_tasks_per_stratum=MIN_TASKS_PER_STRATUM)
    power = required_sample(rows, p, sims=1000, min_tasks_per_stratum=MIN_TASKS_PER_STRATUM, headroom='centred')
    chosen = (power['chosen'] or {'tasks_per_stratum': 20})['tasks_per_stratum']
    agreement = approximation_check(rows, p, chosen, sims=40, headroom='centred')
    ident = candidate_identity()
    draft = DR.build(
        plan_core_dict=plan_core(p), power=power,
        exact_claim=('The frozen representation-and-repair candidate (cut representation cross_2, identity '
                     f'{ident["identity"][:16]}) scores more edges than the strongest frozen fixed baseline on a '
                     'custodian-held CONFIRM panel of triangle_free_host_v1 hosts drawn from the adopted calibration, '
                     'by at least the minimum useful effect, under the registered analysis.'),
        capability_changes=('Candidate: B18 W10 representation grammar (cross_2) with greedy repair; no change to '
                            'trusted checking. The custodian evaluator needs an adapter to execute it (B19-OPEN-3).'),
        permissible_information=('The candidate sees only the candidate view (domain, n, edges). Development used '
                                 'public DEV panels only. SELECT and CONFIRM are drawn and held by the custodian.'),
        baselines={'comparator': 'strongest fixed DSL baseline on the SELECT panel (pilot: ' + strongest + ')',
                   'all_fixed_baselines': sorted(baseline_programs()),
                   'not_a_competitor': 'the SAT/DRAT or LP reference optimum is evaluator ground truth'},
        total_budget={'solver_limits': limits.model_dump(mode='json'), 'candidate_cpu_seconds': CANDIDATE['cpu_seconds'],
                      'arms': 2, 'reference_seconds_per_task': 30,
                      'discovery_cost': 'B18 W10 representation search, recorded in evidence/invention_b18',
                      'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry; isomorphism and near-duplicate screening against every '
                         'DEV panel named in B16–B19 evidence; a CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=('Custodian private evidence store; the judge recomputes the analysis; the custodian '
                              'publishes a signed registration log.'),
        roles={'custodian': 'TO BE ASSIGNED (independent operator)', 'auditor': 'TO BE ASSIGNED',
               'release_authority': 'TO BE ASSIGNED', 'research_operator': 'Genesis builder'},
        rejection_criteria=('Any decision-record or plan check failing; an evaluator that cannot run the candidate; '
                            'registration beyond the declared family size; an INVALID or NOT_SUPPORTED outcome.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for triangle_free_host_v1 hosts from the '
                            'calibrated family on that panel only. Not better-improver, transfer or novelty.'),
        status='DRAFT')
    diffs = [r['candidate']['value'] - r['baseline']['value'] for r in rows]
    summary = {'pilot_tasks': len(rows), 'strata': sorted({r['stratum'] for r in rows}), 'strongest_baseline': strongest,
               'baseline_totals': totals, 'candidate_total': sum(r['candidate']['value'] for r in rows),
               'pilot_mean_difference': round(sum(diffs) / len(diffs), 4),
               'pilot_wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs),
                                          sum(d < 0 for d in diffs)],
               'candidate_optimum_hits': sum(r['candidate']['value'] == r['optimum'] for r in rows),
               'baseline_optimum_hits': sum(r['baseline']['value'] == r['optimum'] for r in rows),
               'chosen': power['chosen'], 'power_status': power['status'],
               'power_at_minimum_useful_effect': power['power_at_minimum_useful_effect'],
               'false_positive_rate_at_zero_effect': power['false_positive_rate_at_zero_effect'],
               'power_model': 'centred headroom (B19); the B16 model is reported beside it',
               'b16_model': {'status': power_b16['status'], 'chosen': power_b16['chosen'],
                             'power_at_minimum_useful_effect': power_b16['power_at_minimum_useful_effect']},
               'approximation_agreement': agreement, 'draft_problems': DR.problems(draft),
               'candidate_identity': ident, 'calibration_record_sha256': calibration_sha,
               'assumptions_fixed_before_pilot': {'minimum_useful_effect': MINIMUM_USEFUL_EFFECT,
                                                  'design_effect': DESIGN_EFFECT}}
    for name, obj in (('power_analysis', power), ('power_analysis_b16_model', power_b16),
                      ('decision_record_DRAFT', draft), ('summary', summary)):
        (out / 'e1').mkdir(parents=True, exist_ok=True)
        (out / 'e1' / f'{name}.json').write_text(json.dumps(obj, indent=1, sort_keys=True) + '\n')
    return summary


def e2(out):
    """Design draft from recorded DEV results (no new runs)."""
    b18 = json.loads((ROOT / 'evidence' / 'invention_b18' / 'recovery' / 'comparison.json').read_text())
    b19 = ROOT / 'evidence' / 'discovery_b19' / 'catalysis' / 'concept.json'
    controls = json.loads(b19.read_text())['controls'] if b19.exists() else {}
    arms = {k: {x: v[x] for x in ('proved', 'disproved', 'unresolved', 'fresh_statements')}
            for k, v in b18['arms'].items()}
    for k, v in controls.items():
        arms[k] = {x: v[x] for x in ('proved', 'disproved', 'unresolved', 'fresh_statements')}
    design = {
        'schema': 'genesis-e2-design-draft-v1', 'status': 'DRAFT', 'split': 'DEV results only',
        'question': 'Did the recovered concept (RC.C0) cause the proving benefit on fresh statement families?',
        'arms': {'enabled': 'concept (RC.C0 and its generic lemmas available)', 'removed': 'none',
                 'placebo': 'placebo (PC.C0: same shape, reversed order, no information about down-closed '
                            'predicates)',
                 'equivalent_information_alternative': 'manual (Mathlib Antitone, stated by a person)',
                 'effort_control': 'effort (no concept, 4x search heartbeats)',
                 'retrieval_control': 'retrieval (history library without the concept)'},
        'unit': 'a fresh statement; arms paired by statement',
        'primary_endpoint': 'statement proved and kernel-checked (CHECKED) within the per-statement search budget',
        'test': 'exact one-sided sign test on discordant pairs, enabled vs each control; Holm over the controls',
        'minimum_useful_effect': '+3 statements per 16 over the best control (stated, for review)',
        'confirm_material': 'fresh statement families generated by the custodian from a frozen generator with a '
                            'seed the builder never sees; the builder never sees the statements before the analysis',
        'separation': {'helps_this_prover': 'the E2 question above',
                       'new_mathematics': 'not claimed: W17 links RC.C0 to Mathlib Antitone / IsLowerSet (Lean-'
                                          'checked) and to monotone graph properties (Alon–Shapira)'},
        'dev_results': arms,
        'dev_reading': ('On DEV, concept and manual each proved 8 of 16 vs 4 for none and retrieval. The B19 '
                        'placebo and effort controls are recorded beside them. These are the numbers a reviewer '
                        'uses to judge whether a sealed E2 study is worth running; they are not a test.'),
        'open': ['custodian-side statement generator and sealed statement panel', 'independent review of this design',
                 'a power analysis on the statement level once the generator is fixed']}
    (out / 'e2').mkdir(parents=True, exist_ok=True)
    (out / 'e2' / 'design_DRAFT.json').write_text(json.dumps(design, indent=1, sort_keys=True,
                                                             ensure_ascii=False) + '\n')
    return {'arms': arms}


def main(argv=None):
    argv = argv or sys.argv[1:]
    if argv[0] == '--design-only':
        # recompute the design from recorded pilot rows (no new runs)
        out = Path(argv[1])
        rows = json.loads((out / 'e1' / 'pilot_rows.json').read_text())
        bt = json.loads((out / 'e1' / 'baseline_totals.json').read_text())
        s1 = design(out, rows, bt['totals'], bt['strongest'], digest(C.load('triangle_free_host_v1', ROOT)),
                    C.CALIBRATION_LIMITS)
        s2 = e2(out)
        (out / 'summary.json').write_text(json.dumps({'e1': s1, 'e2': s2}, indent=1, sort_keys=True,
                                                     default=str) + '\n')
        print(json.dumps(s1, indent=1, sort_keys=True, default=str))
        return 0
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    s1 = e1(out, log)
    s2 = e2(out)
    summary = {'e1': s1, 'e2': s2, 'wall_seconds': round(time.monotonic() - t0, 1)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + '\n')
    print(json.dumps(summary, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
