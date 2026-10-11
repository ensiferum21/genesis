"""The pre-freeze decision record (roadmap Appendix B, W06/W07).

"Before each scientific freeze, publish a concise decision record: exact claim;
capability changes; permissible information; baselines; total budget; primary
outcome; minimum useful effect; sample/power justification; statistical and
stopping rules; exposure policy; raw-evidence custody; signatures and independent
roles; rejection criteria; and allowed conclusion."

The record embeds the analysis plan's core (the plan without its record reference)
and the DEV-only power analysis; the plan then names the record by SHA-256, and the
custodian refuses a v2 registration whose record is missing, unfrozen or
inconsistent with the request.
"""
from .common import digest, utcnow
from .kernel.analysis import check_plan, plan_core

SCHEMA = 'genesis-decision-record-v1'
FIELDS = frozenset({
    'schema', 'status', 'created_at', 'exact_claim', 'capability_changes', 'permissible_information',
    'baselines', 'total_budget', 'primary_outcome', 'minimum_useful_effect', 'sample_size_justification',
    'statistical_rules', 'stopping_rule', 'exposure_policy', 'raw_evidence_custody', 'roles',
    'rejection_criteria', 'allowed_conclusion', 'analysis_plan_core'})
TEXT_FIELDS = ('exact_claim', 'capability_changes', 'permissible_information', 'exposure_policy',
               'raw_evidence_custody', 'rejection_criteria', 'allowed_conclusion')


def build(*, plan_core_dict, power, exact_claim, capability_changes, permissible_information, baselines,
          total_budget, exposure_policy, raw_evidence_custody, roles, rejection_criteria, allowed_conclusion,
          status='DRAFT'):
    return {'schema': SCHEMA, 'status': status, 'created_at': utcnow(), 'exact_claim': exact_claim,
            'capability_changes': capability_changes, 'permissible_information': permissible_information,
            'baselines': baselines, 'total_budget': total_budget,
            'primary_outcome': {'endpoint': plan_core_dict['primary'], 'estimand': plan_core_dict['estimand'],
                                'strata': plan_core_dict['strata']},
            'minimum_useful_effect': plan_core_dict['minimum_useful_effect'],
            'sample_size_justification': power,
            'statistical_rules': {'test': plan_core_dict['test'], 'alpha': plan_core_dict['alpha'],
                                  'interval': plan_core_dict['interval'],
                                  'multiplicity': plan_core_dict['multiplicity'],
                                  'failures': plan_core_dict['failures'], 'unsupported': plan_core_dict['unsupported'],
                                  'sensitivity': plan_core_dict['sensitivity']},
            'stopping_rule': plan_core_dict['stopping'], 'exposure_policy': exposure_policy,
            'raw_evidence_custody': raw_evidence_custody, 'roles': roles,
            'rejection_criteria': rejection_criteria, 'allowed_conclusion': allowed_conclusion,
            'analysis_plan_core': plan_core_dict}


def problems(record, plan=None, *, task_count=None, require_frozen=False):
    if not isinstance(record, dict) or record.get('schema') != SCHEMA:
        return ['not a decision record']
    if set(record) != FIELDS:
        return [f'decision record fields differ: missing {sorted(FIELDS - set(record))}, '
                f'extra {sorted(set(record) - FIELDS)}']
    out = []
    if record['status'] not in ('DRAFT', 'FROZEN'):
        out.append('status must be DRAFT or FROZEN')
    if require_frozen and record['status'] != 'FROZEN':
        out.append('the decision record must be FROZEN (published) before registration')
    for f in TEXT_FIELDS:
        if not isinstance(record[f], str) or len(record[f].strip()) < 10:
            out.append(f'{f} must be stated')
    core = record['analysis_plan_core']
    full = dict(core, decision_record_sha256='0' * 64)
    out += ['analysis plan: ' + p for p in check_plan(full) if 'decision_record' not in p]
    if record['minimum_useful_effect'] != core.get('minimum_useful_effect'):
        out.append('minimum useful effect differs from the analysis plan')
    if record['stopping_rule'] != core.get('stopping'):
        out.append('stopping rule differs from the analysis plan')
    if not isinstance(record['baselines'], dict) or not record['baselines']:
        out.append('baselines must be named')
    if not isinstance(record['total_budget'], dict) or not record['total_budget']:
        out.append('total budget must be stated')
    if not isinstance(record['roles'], dict) or not record['roles']:
        out.append('roles must be named')
    power = record['sample_size_justification']
    if not isinstance(power, dict) or power.get('schema') != 'genesis-power-analysis-v1':
        out.append('sample size must be justified by a power analysis (genesis.power)')
    else:
        if power.get('plan_core_sha256') != digest(core):
            out.append('the power analysis was run for a different plan')
        if not power.get('chosen'):
            out.append('the power analysis found no sample size reaching the power target')
        elif task_count is not None and task_count < power['chosen']['total_tasks']:
            out.append(f"task count {task_count} is below the {power['chosen']['total_tasks']} the power analysis requires")
    if plan is not None:
        if plan_core(plan) != core:
            out.append('the analysis plan differs from the one embedded in the decision record')
        if plan.get('decision_record_sha256') != digest(record):
            out.append('the analysis plan does not name this decision record')
    return out


def freeze(record):
    """The published form: status FROZEN. Its digest is what the plan names."""
    frozen = dict(record, status='FROZEN')
    return frozen, digest(frozen)
