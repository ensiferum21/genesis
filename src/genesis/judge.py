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


def recompute(evaluation_root, request, receipt, *, registration_log_entries=None):
    payload = receipt['payload']
    out = {'schema': 'genesis-judge-recomputation-v1', 'request_hash': digest(request),
           'receipt_sha256': digest(receipt), 'problems': []}
    if payload.get('schema') != R.SCIENTIFIC_RECEIPT_V3:
        out['problems'].append('only v3 receipts carry a recomputable v2 analysis')
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
