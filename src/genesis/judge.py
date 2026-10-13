"""Independent recomputation of a sealed evaluation (roadmap W07: "analysis is executable
from raw receipts; the judge recomputes outcomes").

A judge given read access to the custodian's evaluation evidence store copies it,
rebuilds it from its append-only export (checking the hash chain ends at the
receipt's signed raw_evidence_root), rebuilds the per-task rows from the raw
attempt receipts, re-runs the preregistered analysis and compares every field of
the result with the signed one. The judge never trusts the custodian's numbers.
"""
import json
from pathlib import Path
import shutil
import tempfile

from .common import canonical, digest
from .kernel import receipts as R
from .resources import account, arm_fairness
from .kernel.analysis import analyze
from .models import GraphTask
from .store import Store, rebuild_from_export


def analysis_rows(evidence, tasks):
    """Per-task raw rows for the v2 analysis, rebuilt from the evidence journal (W07: the
    analysis is executable from raw receipts). A failed run scores 0 and keeps its cost."""
    unsupported={i for i,_ in evidence.db.execute("SELECT id,object_hash FROM entities WHERE kind='unsupported_task'")}
    byarm={}
    for status,req,rec in evidence.db.execute('SELECT status,request,receipt FROM attempts ORDER BY rowid'):
        if rec is None or status in ('RUNNING','INTERRUPTED'):continue
        request=evidence.get(req)
        if request.get('kind')!='solver' or request['arm'] not in ('candidate','baseline'):continue
        receipt=evidence.get(rec)
        ok=receipt['status']=='SUCCESS'
        cpu=receipt.get('cpu_ns') if type(receipt.get('cpu_ns')) is int else receipt.get('wall_ns')
        byarm[(request['task']['task_id'],request['arm'])]={
            'value':receipt['result']['value'] if ok else 0,'run':'SUCCESS' if ok else 'FAILED',
            'cpu_ns':cpu if type(cpu) is int else 0}
    rows=[]
    for t in tasks:
        if t.task_id in unsupported:
            rows.append({'task_id':t.task_id,'stratum':t.family,'status':'UNSUPPORTED'})
        elif (t.task_id,'candidate') in byarm and (t.task_id,'baseline') in byarm:
            rows.append({'task_id':t.task_id,'stratum':t.family,'status':'SCORED',
                         'candidate':byarm[(t.task_id,'candidate')],'baseline':byarm[(t.task_id,'baseline')]})
    return rows


def witness_problems(evidence, tasks, request):
    """Re-check every scored solver result from its raw receipt (handoff s13.3: the judge
    independently recomputes; a candidate's claimed value is never the score).

    For each terminal SUCCESS solver attempt: the task must be the pool's task, the witness must
    pass the domain checker and give the recorded value. For a v4 request the attempt must have
    run the request's descriptor for that arm, inside the declared sandbox."""
    from .domains import adapter
    pool = {t.task_id: t for t in tasks}
    out, rechecked = [], 0
    for status, req, rec in evidence.db.execute('SELECT status,request,receipt FROM attempts ORDER BY rowid'):
        if rec is None or status in ('RUNNING', 'INTERRUPTED'):
            continue
        attempt = evidence.get(req)
        if attempt.get('kind') != 'solver':
            continue
        receipt = evidence.get(rec)
        tid = (attempt.get('task') or {}).get('task_id')
        if tid not in pool or attempt['task'] != pool[tid].model_dump(mode='json'):
            out.append(f'solver attempt on {tid!r} is not a task of the sealed pool')
            continue
        if R.is_v4(request):
            if attempt.get('descriptor') != request['arms'].get(attempt.get('arm')):
                out.append(f'attempt {tid}/{attempt.get("arm")} did not run the descriptor the request names for its arm')
            if receipt.get('status') == 'SUCCESS' and receipt.get('isolation') != R.ISOLATION_V4:
                out.append(f'attempt {tid}/{attempt.get("arm")} did not run inside the declared sandbox')
        if receipt.get('status') != 'SUCCESS':
            continue
        result = receipt.get('result') or {}
        checked = adapter(pool[tid].domain).validate(pool[tid], result.get('selected') or [])
        rechecked += 1
        if checked['status'] != 'VALID' or checked['value'] != result.get('value'):
            out.append(f'attempt {tid}/{attempt.get("arm")}: the recorded witness does not give the recorded value')
    return {'problems': out, 'rechecked': rechecked}


def recompute(evaluation_root, request, receipt, *, registration_log_entries=None):
    payload = receipt['payload']
    out = {'schema': 'genesis-judge-recomputation-v1', 'request_hash': digest(request),
           'receipt_sha256': digest(receipt), 'problems': []}
    if payload.get('schema') not in R.ANALYSIS_RECEIPTS:
        out['problems'].append('only v3/v4 receipts carry a recomputable v2 analysis')
        out['agrees'] = False
        return out
    with tempfile.TemporaryDirectory(prefix='genesis-judge-') as d:
        shutil.copy(Path(evaluation_root) / 'events.jsonl', Path(d) / 'events.jsonl')
        shutil.copytree(Path(evaluation_root) / 'objects', Path(d) / 'objects')
        record = rebuild_from_export(d)
        with Store(d) as s:
            head = s.verify()['head']
            if head != payload['raw_evidence_root'] and record['head'] != payload['raw_evidence_root']:
                out['problems'].append('the evidence store does not end at the signed raw_evidence_root')
            pools = [s.get(h) for (h,) in s.db.execute("SELECT object_hash FROM entities WHERE kind='pool'")]
            if len(pools) != 1 or digest(pools[0]) is None:
                out['problems'].append('the evidence store does not hold exactly one pool')
                out['agrees'] = False
                return out
            tasks = [GraphTask.model_validate_json(canonical(t)) for t in pools[0]]
            rows = analysis_rows(s, tasks)
            witnesses = witness_problems(s, tasks, request)
            out['witnesses_rechecked'] = witnesses['rechecked']
            out['problems'] += witnesses['problems']
            resources = account(s)
            fairness = arm_fairness(s)
            saved = s.db.execute("SELECT object_hash FROM entities WHERE kind='resource_account' AND id=?",
                                 (digest(request),)).fetchone()
            if saved is None:
                out['problems'].append('the evidence store holds no resource account')
            elif s.get(saved[0]) != resources:
                out['problems'].append('the recorded resource account differs from the attempt journal')
            out['problems'] += ['fairness: ' + p for p in fairness['problems']]
    out.update(resource_account=resources, fairness=fairness)
    if registration_log_entries is not None:
        from .custody_records import family_of, published_p_values_before
        family_p = published_p_values_before(registration_log_entries, family_of(request), digest(request))
    else:
        family_p = payload['analysis_result'].get('family_p_values', [])
        out['problems'].append('no registration log supplied: family p-values taken from the receipt')
    result = analyze(rows, request['analysis'], family_p_values=family_p)
    differences = sorted(k for k in set(result) | set(payload['analysis_result'])
                         if result.get(k) != payload['analysis_result'].get(k))
    out.update(recomputed=result, differences=differences, rows_sha256=digest(rows),
               recomputed_outcome=result['decision'], signed_outcome=payload['outcome'])
    if differences:
        out['problems'].append(f'recomputed analysis differs from the signed result in {differences}')
    if result['decision'] != payload['outcome']:
        out['problems'].append('recomputed decision differs from the signed outcome')
    out['agrees'] = not [p for p in out['problems'] if not p.startswith('no registration log')]
    return out
