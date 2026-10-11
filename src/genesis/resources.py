"""Resource accounting (roadmap W07).

"Measure discovery, inference, verification, retrieval, model calls, memory and human
time. A baseline receives the same allowed information and comparable resources.
Distinguish expensive ground-truth computation from a competing solver's budget."

`account(store)` classifies every attempt in an evidence journal (a DEV campaign or a
custodian evaluation) by what it was for, and totals what it cost. Every attempt is
charged, including failures, timeouts, interrupted and harness-error attempts. An attempt
of a kind this module does not know is listed as `unclassified`; it is never dropped.

  discovery     solver trials run while searching for candidates (DEV campaigns)
  inference     a named arm (candidate, baseline, ladder or experiment arm) run on a task
  verification  replays of recorded results
  ground_truth  exact reference computation by the evaluator; never charged to an arm
  retrieval     attempts of kind 'retrieval'
  model_calls   attempts of kind 'model-call'
  memory        peak resident memory per category, where the executor reports it
  human_time    operator time: never measured by the machine; DECLARED or NOT_MEASURED

A category with no recorded attempts is reported as NONE_RECORDED. That means the
journal holds no such attempt; it does not by itself prove the resource was unused
outside the journal. (This build contains no model client and solver programs are
data-only DSL programs run without network; a test checks the first statement.)

`arm_fairness(store)` checks, for a custodian evaluation, that the arms ran on the same
tasks with the same limits and seed, that each task has exactly one attempt per arm,
and that ground truth is accounted separately.
"""
from collections import defaultdict

from .common import canonical

SCHEMA = 'genesis-resource-account-v1'
CATEGORIES = ('discovery', 'inference', 'verification', 'ground_truth', 'retrieval', 'model_calls', 'memory',
              'human_time')
FIXED_KINDS = {'exact-check': 'ground_truth', 'replay': 'verification', 'retrieval': 'retrieval',
               'model-call': 'model_calls', 'ladder': 'inference', 'ladder-specialist': 'inference',
               'experiment_b': 'inference'}
MEMORY_FIELDS = ('peak_rss_bytes', 'peak_memory_bytes')


def _category(request):
    kind = request.get('kind')
    if kind == 'solver':
        return 'inference' if 'arm' in request else 'discovery'
    return FIXED_KINDS.get(kind, 'unclassified')


def _blank():
    return {'attempts': 0, 'by_status': {}, 'failures': 0, 'cpu_ns': 0, 'cpu_unknown': 0, 'wall_ns': 0,
            'wall_unknown': 0, 'queries': 0, 'peak_memory_bytes': None}


def _add(total, status, receipt):
    total['attempts'] += 1
    total['by_status'][status] = total['by_status'].get(status, 0) + 1
    if status != 'SUCCESS':
        total['failures'] += 1
    for field in ('cpu_ns', 'wall_ns'):
        v = receipt.get(field) if isinstance(receipt, dict) else None
        if type(v) is int and v >= 0:
            total[field] += v
        else:
            total[field.replace('_ns', '_unknown')] += 1
    result = receipt.get('result') if isinstance(receipt, dict) else None
    q = result.get('queries') if isinstance(result, dict) else None
    if type(q) is int and q >= 0:
        total['queries'] += q
    for field in MEMORY_FIELDS:
        m = receipt.get(field) if isinstance(receipt, dict) else None
        if type(m) is int and m >= 0:
            total['peak_memory_bytes'] = max(total['peak_memory_bytes'] or 0, m)


def _attempts(store):
    for aid, status, req, rec in store.db.execute('SELECT id,status,request,receipt FROM attempts ORDER BY rowid'):
        request = store.get(req)
        receipt = store.get(rec) if rec is not None else {}
        yield aid, status, request, receipt


def account(store, *, declared_human_seconds=None, declared_by=None):
    """A deterministic resource account of `store`'s attempt journal (no timestamps)."""
    totals = {c: _blank() for c in ('discovery', 'inference', 'verification', 'ground_truth', 'retrieval',
                                    'model_calls', 'unclassified')}
    arms = defaultdict(_blank)
    for _, status, request, receipt in _attempts(store):
        cat = _category(request)
        _add(totals[cat], status, receipt)
        if cat == 'inference':
            _add(arms[str(request.get('arm'))], status, receipt)
    out = {'schema': SCHEMA}
    for cat in ('discovery', 'inference', 'verification', 'ground_truth', 'retrieval', 'model_calls'):
        t = totals[cat]
        out[cat] = dict(t, status='MEASURED' if t['attempts'] else 'NONE_RECORDED')
    out['inference']['by_arm'] = {a: arms[a] for a in sorted(arms)}
    out['ground_truth']['charged_to_arm'] = False
    out['memory'] = {'status': 'MEASURED' if any(totals[c]['peak_memory_bytes'] is not None for c in totals)
                     else 'NOT_REPORTED_BY_EXECUTOR',
                     'peak_bytes_by_category': {c: totals[c]['peak_memory_bytes'] for c in sorted(totals)
                                                if totals[c]['peak_memory_bytes'] is not None}}
    if declared_human_seconds is None:
        out['human_time'] = {'status': 'NOT_MEASURED', 'seconds': None, 'declared_by': None}
    else:
        if type(declared_human_seconds) not in (int, float) or declared_human_seconds < 0 or not declared_by:
            raise ValueError('declared human time needs a non-negative number of seconds and who declares it')
        out['human_time'] = {'status': 'DECLARED', 'seconds': declared_human_seconds, 'declared_by': declared_by}
    out['unclassified'] = totals['unclassified']
    out['charged'] = 'every attempt, including failures, timeouts, interrupted and harness-error attempts'
    return out


def arm_fairness(store, arms=('candidate', 'baseline')):
    """Did the arms of a custodian evaluation get the same tasks, limits and seed?"""
    per_task = defaultdict(lambda: defaultdict(list))
    limits = set()
    for _, status, request, receipt in _attempts(store):
        if request.get('kind') != 'solver' or request.get('arm') not in arms:
            continue
        tid = request['task']['task_id']
        per_task[tid][request['arm']].append(request)
        limits.add(canonical(request.get('limits')))
    problems = []
    if len(limits) > 1:
        problems.append('the arms did not all run under the same limits')
    for tid in sorted(per_task):
        runs = per_task[tid]
        if any(len(runs.get(a, [])) != 1 for a in arms):
            problems.append(f'task {tid!r} does not have exactly one attempt per arm')
            continue
        first = runs[arms[0]][0]
        for a in arms[1:]:
            other = runs[a][0]
            if other['task'] != first['task']:
                problems.append(f'task {tid!r} was presented differently to the arms')
            if other.get('seed') != first.get('seed'):
                problems.append(f'task {tid!r} used different seeds for the arms')
    acct = account(store)
    by_arm = acct['inference']['by_arm']
    cpu = {a: by_arm.get(a, _blank())['cpu_ns'] for a in arms}
    return {'problems': problems, 'paired_tasks': len(per_task), 'same_limits': len(limits) <= 1,
            'cpu_ns_by_arm': cpu,
            'cpu_ratio': None if not cpu[arms[1]] else round(cpu[arms[0]] / cpu[arms[1]], 6),
            'information': 'each arm receives only the candidate view (domain, n, edges) built from the same task',
            'ground_truth_charged_to_arm': False}


__all__ = ['account', 'arm_fairness', 'CATEGORIES', 'SCHEMA']
