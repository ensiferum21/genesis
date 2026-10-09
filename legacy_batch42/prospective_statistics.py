"""DEV-only, exact descriptive inference on prospectively accounted paired outcomes.

No result from this module authorizes scientific promotion.  Invalid executions are
excluded rather than treated as ties, and any invalid execution blocks a verdict.
"""
import math
from collections import defaultdict


def _pvalue(wins, losses):
    n = wins + losses
    if not n:
        return None
    # Integer binomial arithmetic avoids float overflow for large n.
    # Sum the smaller tail and complement when appropriate.
    if wins > n // 2:
        numerator = sum(math.comb(n, k) for k in range(n - wins + 1))
        return numerator / (1 << n)
    numerator = sum(math.comb(n, k) for k in range(wins))
    return 1.0 - numerator / (1 << n)


def analyze_pairs(pairs, *, task_clusters, alpha=0.05):
    if type(alpha) not in (float, int) or isinstance(alpha, bool) or not 0 < alpha < 1:
        raise ValueError('invalid alpha')
    if not isinstance(pairs, list) or not pairs:
        raise ValueError('nonempty paired outcomes required')
    if not isinstance(task_clusters, dict):
        raise ValueError('frozen task cluster mapping required')
    allowed = {'PASS', 'FAIL', 'TIMEOUT', 'CANCELLED', 'CHECKER_ERROR', 'UNSUPPORTED'}
    invalid = {'CHECKER_ERROR', 'UNSUPPORTED'}
    ids = []
    counts = defaultdict(int)
    wins = losses = ties = invalid_pairs = 0
    for p in pairs:
        if not isinstance(p, dict) or not {'task_id', 'baseline', 'candidate'} <= p.keys():
            raise ValueError('malformed pair')
        t, b, c = p['task_id'], p['baseline'], p['candidate']
        if not isinstance(t, str) or not t or b not in allowed or c not in allowed:
            raise ValueError('malformed outcome')
        ids.append(t)
        if b in invalid or c in invalid:
            invalid_pairs += 1
            continue
        delta = int(c == 'PASS') - int(b == 'PASS')
        wins += delta > 0
        losses += delta < 0
        ties += delta == 0
        counts[task_clusters.get(t)] += delta
    if len(set(ids)) != len(ids) or set(ids) != set(task_clusters):
        raise ValueError('task roster and cluster mapping mismatch')
    if any(not isinstance(v, str) or not v.strip() for v in task_clusters.values()):
        raise ValueError('every cluster must have a nonempty frozen label')
    # Cluster sign test on cluster-level aggregate paired advantage. This is
    # sensitivity analysis, not proof of exchangeability or independent clusters.
    cluster_wins = sum(v > 0 for v in counts.values())
    cluster_losses = sum(v < 0 for v in counts.values())
    p_task = _pvalue(wins, losses)
    p_cluster = _pvalue(cluster_wins, cluster_losses)
    return {
        'schema': 'genesis-descriptive-paired-statistics-dev-v1',
        'task_wins': wins, 'task_losses': losses, 'task_ties': ties,
        'invalid_pairs': invalid_pairs,
        'task_sign_p_one_sided': p_task,
        'cluster_wins': cluster_wins, 'cluster_losses': cluster_losses,
        'cluster_sign_p_one_sided': p_cluster,
        'cluster_count': len(set(task_clusters.values())),
        'alpha': float(alpha),
        'descriptive_task_threshold_met': invalid_pairs == 0 and p_task is not None and p_task <= alpha,
        'descriptive_cluster_threshold_met': invalid_pairs == 0 and p_cluster is not None and p_cluster <= alpha,
        'statistical_assumptions_independently_checked': False,
        'execution_evidence_replayed': False,
        'promotion_allowed': False,
        'scientific_claim': 'NONE',
    }


def analyze_frozen_trial(*, registration, public_tasks, sealed_commitment, config,
                         baseline, candidate, events, budget_per_arm, max_attempts,
                         split='CONFIRM', alpha=0.05):
    """Require a frozen cluster label for each registered task in the chosen split.

    Cluster labels are an external analysis plan, not part of v1 registration;
    callers must freeze them independently before looking at results.
    """
    from frozen_trial import audit_frozen_trial
    accounted = audit_frozen_trial(public_tasks=public_tasks, sealed_commitment=sealed_commitment,
                                   config=config, baseline=baseline, candidate=candidate,
                                   registration=registration, events=events,
                                   budget_per_arm=budget_per_arm, max_attempts=max_attempts, split=split)
    ids = sorted(t['id'] for t in public_tasks if t['split'] == split)
    # Order of JSON events is not the order of attempts. Use the terminal
    # attempt number after the accounting gate checks continuity.
    terminal = {}
    for e in events:
        key = (e['task_id'], e['arm'])
        if key not in terminal or e['attempt'] > terminal[key]['attempt']:
            terminal[key] = e
    pairs = [{'task_id': t, 'baseline': terminal[(t, 'baseline')]['state'],
              'candidate': terminal[(t, 'candidate')]['state']} for t in ids]
    # No cluster assumption is silently invented. The default is each task its
    # own cluster, explicitly labeled as a NON-INDEPENDENT exploratory proxy.
    stats = analyze_pairs(pairs, task_clusters={t:t for t in ids}, alpha=alpha)
    stats['cluster_assignment'] = 'TASK_AS_CLUSTER_EXPLORATORY_ONLY'
    stats['cluster_independence_supported'] = False
    stats['registration_sha256'] = accounted['registration_sha256']
    stats['raw_events_sha256'] = accounted['raw_events_sha256']
    stats['accounting_status'] = accounted['status']
    stats['promotion_allowed'] = False
    return stats
