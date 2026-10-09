"""DEV-only binding of prospective accounting to independently registered inputs.

Does not verify execution receipts or prove independence of custody.
"""
import hashlib
from sealed_benchmark import canonical, register
from prospective_accounting import audit


def audit_frozen_trial(*, public_tasks, sealed_commitment, config, baseline,
                       candidate, registration, events, budget_per_arm, max_attempts,
                       split='CONFIRM'):
    if split not in ('DEV', 'SELECT', 'CONFIRM'):
        raise ValueError('SEALED task plaintext cannot enter this audit')
    expected = register(public_tasks, sealed_commitment, config, baseline, candidate)
    if type(registration) is not dict or registration != expected:
        raise ValueError('registration does not match complete frozen inputs')
    tasks = sorted(t['id'] for t in public_tasks if t['split'] == split)
    if not tasks:
        raise ValueError('no tasks in requested split')
    # A single task roster is derived from the registered content, never caller supplied.
    result = audit(registration, tasks, events, budget_per_arm=budget_per_arm,
                   max_attempts=max_attempts)
    result['schema'] = 'genesis-frozen-trial-dev-v1'
    result['split'] = split
    result['task_roster_sha256'] = hashlib.sha256(canonical(tasks)).hexdigest()
    result['registration_recomputed'] = True
    result['execution_evidence_replayed'] = False
    result['sealed_split_evaluated'] = False
    result['promotion_allowed'] = False
    result['scientific_claim'] = 'NONE'
    return result
