#!/usr/bin/env python3
"""B16 study design draft for E1 (useful checked solver improvement), DEV material only.

  b16_study_design.py OUT_DIR

1. Draw a fresh DEV pilot panel from the adopted c4 calibration (selected settings only).
2. Run an illustrative candidate (a fixed DSL program that is NOT a research output and
   is NOT frozen) and every fixed baseline under the calibration limits; the strongest
   baseline on the pilot is the comparator, as the custodian would require.
3. Estimate the spread of paired differences per family and run the power analysis for
   the draft plan (minimum useful effect, design effect, Holm family size).
4. Write a DRAFT decision record. It is a design for review, not a frozen study: no
   candidate is frozen, no sealed task exists and nothing here is evidence of efficacy.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as C  # noqa: E402
from genesis import decision_record as DR  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.execution import execute  # noqa: E402
from genesis.kernel.analysis import PLAN_SCHEMA, SENSITIVITY, plan_core  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402
from genesis.power import approximation_check, required_sample  # noqa: E402

PILOT_SEED = 20261201
PILOT_TASKS = 60
# Design floor (stated choice): fewer tasks per family make the sensitivity analyses degenerate.
MIN_TASKS_PER_STRATUM = 10
ILLUSTRATIVE_CANDIDATE = SolverProgram(weights=(0, 0, 0, 1), rounds=32, exchange=True)


def draft_plan():
    return {'schema': PLAN_SCHEMA, 'primary': 'paired-edge-difference', 'estimand': 'mean-of-stratum-means',
            'strata': 'family', 'minimum_useful_effect': 0.25, 'design_effect': 0.5, 'alpha': 0.05,
            'power_target': 0.8, 'test': 'stratified-sign-flip',
            'interval': {'method': 'stratified-bootstrap-percentile', 'level': 0.9, 'resamples': 4000},
            'multiplicity': {'method': 'holm', 'family_id': 'sealed_evaluation:c4_host_v2', 'family_size': 3},
            'stopping': {'rule': 'single-analysis'}, 'failures': 'score-zero', 'unsupported': 'exclude-and-report',
            'max_unsupported_fraction': 0.05, 'cost': {'measure': 'cpu_ns', 'max_ratio': 3.0},
            'regression': {'max_stratum_loss': 1.0}, 'sensitivity': list(SENSITIVITY),
            'decision_rule': 'superiority-with-minimum-useful-effect', 'decision_record_sha256': '0' * 64}


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    record = C.load('c4_host_v2', ROOT)
    tasks, _ = C.calibrated_panel(record, PILOT_SEED, PILOT_TASKS, 'DEV',
                                  excluded=set())          # fresh DEV draw; DEV split enforced below
    C.require_dev(tasks)
    limits = C.CALIBRATION_LIMITS
    arms = dict(baseline_programs(), candidate=ILLUSTRATIVE_CANDIDATE)
    from genesis.domains import ADAPTERS, Unsupported
    runs, optima = {}, {}
    for t in tasks:
        ref = ADAPTERS[t.domain].reference(t, seconds=30)
        optima[t.task_id] = None if isinstance(ref, Unsupported) else ref['value']
        seed = int(digest({'seed': PILOT_SEED, 'task': t.task_id})[:12], 16)
        for name, prog in sorted(arms.items()):
            r = execute(t, prog, limits, seed)
            ok = r['status'] == 'SUCCESS'
            runs[(t.task_id, name)] = {'value': r['result']['value'] if ok else 0, 'run': 'SUCCESS' if ok else 'FAILED',
                                       'cpu_ns': r['cpu_ns'] if type(r.get('cpu_ns')) is int else r['wall_ns']}
    totals = {name: sum(runs[(t.task_id, name)]['value'] for t in tasks) for name in baseline_programs()}
    strongest = max(totals, key=lambda n: (totals[n], n))
    rows = [{'task_id': t.task_id, 'stratum': t.family, 'status': 'SCORED', 'split': t.split,
             'optimum': optima[t.task_id],
             'candidate': runs[(t.task_id, 'candidate')], 'baseline': runs[(t.task_id, strongest)]}
            for t in tasks if optima[t.task_id] is not None]
    plan = draft_plan()
    power = required_sample(rows, plan, sims=1000, min_tasks_per_stratum=MIN_TASKS_PER_STRATUM)
    agreement = approximation_check(rows, plan, (power['chosen'] or {'tasks_per_stratum': 20})['tasks_per_stratum'],
                                    sims=40)
    draft = DR.build(
        plan_core_dict=plan_core(plan), power=power,
        exact_claim=('A frozen research-generated candidate program scores more edges than the strongest frozen '
                     'baseline on a custodian-held CONFIRM panel of c4_host_v2 hosts drawn from the adopted '
                     'calibration, by at least the minimum useful effect, under the registered analysis.'),
        capability_changes=('To be filled at freeze: the candidate program and any library changes since the '
                            'parent version (none exist yet; no candidate is frozen).'),
        permissible_information=('Candidates see only the candidate view (domain, n, edges). Development may use '
                                 'public DEV panels and SELECT for choosing one candidate; CONFIRM is held by the '
                                 'custodian and never visible before the single analysis.'),
        baselines={'comparator': 'strongest fixed DSL baseline on the SELECT panel (pilot: ' + strongest + ')',
                   'all_fixed_baselines': sorted(baseline_programs()),
                   'not_a_competitor': 'the SAT/DRAT reference optimum is evaluator ground truth, not a solver arm'},
        total_budget={'solver_limits': limits.model_dump(mode='json'), 'arms': 2,
                      'reference_seconds_per_task': 30, 'charge': 'every attempt, retry, timeout and failure'},
        exposure_policy=('Custodian-built exposure registry from the public manifest and the campaign export; '
                         'isomorphism and near-duplicate screening; a CONFIRM panel is retired after its one use.'),
        raw_evidence_custody=('Custodian private evidence store (per-task raw receipts); the judge recomputes the '
                              'analysis from it; the custodian publishes a signed registration log.'),
        roles={'custodian': 'TO BE ASSIGNED (independent operator)', 'auditor': 'TO BE ASSIGNED',
               'release_authority': 'TO BE ASSIGNED', 'research_operator': 'Genesis builder'},
        rejection_criteria=('Any decision-record or plan check failing; registration beyond the declared family '
                            'size; an INVALID or NOT_SUPPORTED outcome; shared control between roles limits the '
                            'claim to an operator-attested evaluation.'),
        allowed_conclusion=('If SUPPORTED: a scoped better-solver statement for c4_host_v2 hosts from the '
                            'calibrated families on that panel only. Not better-improver, transfer, novelty or '
                            'self-improvement.'),
        status='DRAFT')
    (out / 'pilot_rows.json').write_text(json.dumps(rows, indent=1, sort_keys=True) + '\n')
    (out / 'power_analysis.json').write_text(json.dumps(power, indent=1, sort_keys=True) + '\n')
    (out / 'decision_record_DRAFT.json').write_text(json.dumps(draft, indent=1, sort_keys=True) + '\n')
    summary = {'pilot_tasks': len(rows), 'strata': sorted({r['stratum'] for r in rows}),
               'strongest_baseline': strongest, 'baseline_totals': totals,
               'candidate_total': sum(r['candidate']['value'] for r in rows),
               'pilot_mean_difference': round(sum(r['candidate']['value'] - r['baseline']['value'] for r in rows)
                                              / len(rows), 4),
               'chosen': power['chosen'], 'power_status': power['status'],
               'power_at_minimum_useful_effect': power['power_at_minimum_useful_effect'],
               'false_positive_rate_at_zero_effect': power['false_positive_rate_at_zero_effect'],
               'approximation_agreement': agreement, 'draft_problems': DR.problems(draft),
               'calibration_record_sha256': digest(record)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == '__main__':
    main(sys.argv[1])
