"""DEV-only precommitted theorem-family analysis; no independence or proof claims."""
import hashlib
import re
from sealed_benchmark import canonical, register
from frozen_trial import audit_frozen_trial
from prospective_statistics import analyze_pairs

HEX = re.compile(r'^[0-9a-f]{64}$')


def freeze_cluster_plan(*, registration, public_tasks, sealed_commitment, config,
                        baseline, candidate, clusters, split='CONFIRM'):
    expected = register(public_tasks, sealed_commitment, config, baseline, candidate)
    if registration != expected:
        raise ValueError('registration mismatch')
    if split not in ('DEV', 'SELECT', 'CONFIRM'):
        raise ValueError('invalid public split')
    ids = {t['id'] for t in public_tasks if t['split'] == split}
    if not ids or type(clusters) is not dict or set(clusters) != ids:
        raise ValueError('cluster plan must cover exactly frozen task roster')
    if any(type(v) is not str or not v.strip() or len(v) > 256 for v in clusters.values()):
        raise ValueError('invalid cluster label')
    payload = {'schema': 'genesis-cluster-plan-dev-v1', 'registration_sha256': registration['registration_sha256'],
               'split': split, 'clusters': clusters}
    return {'schema': payload['schema'], 'registration_sha256': payload['registration_sha256'],
            'split': split, 'cluster_count': len(set(clusters.values())),
            'commitment_sha256': hashlib.sha256(canonical(payload)).hexdigest(),
            'promotion_allowed': False}


def analyze_precommitted_clusters(*, plan, clusters, registration, public_tasks,
                                   sealed_commitment, config, baseline, candidate,
                                   events, budget_per_arm, max_attempts, split='CONFIRM', alpha=.05):
    expected = freeze_cluster_plan(registration=registration, public_tasks=public_tasks,
                                   sealed_commitment=sealed_commitment, config=config,
                                   baseline=baseline, candidate=candidate, clusters=clusters, split=split)
    if type(plan) is not dict or plan != expected:
        raise ValueError('cluster plan not committed to this exact experiment')
    accounted = audit_frozen_trial(public_tasks=public_tasks, sealed_commitment=sealed_commitment,
                                   config=config, baseline=baseline, candidate=candidate,
                                   registration=registration, events=events,
                                   budget_per_arm=budget_per_arm, max_attempts=max_attempts, split=split)
    # Use terminal attempt per arm, not arbitrary input order or first attempt.
    terminal = {}
    for e in events:
        key = (e['task_id'], e['arm'])
        if key not in terminal or e['attempt'] > terminal[key]['attempt']:
            terminal[key] = e
    pairs = [{'task_id': tid, 'baseline': terminal[(tid, 'baseline')]['state'],
              'candidate': terminal[(tid, 'candidate')]['state']} for tid in sorted(clusters)]
    stats = analyze_pairs(pairs, task_clusters=clusters, alpha=alpha)
    stats.update({'cluster_assignment': 'PRECOMMITTED_EXTERNAL_PLAN_REQUIRED',
                  'cluster_plan_sha256': plan['commitment_sha256'],
                  'registration_sha256': accounted['registration_sha256'],
                  'raw_events_sha256': accounted['raw_events_sha256'],
                  'accounting_status': accounted['status'],
                  'cluster_independence_supported': False,
                  'precommitment_timestamp_independently_verified': False,
                  'external_checker_verified': False,
                  'promotion_allowed': False, 'scientific_claim': 'NONE'})
    return stats
