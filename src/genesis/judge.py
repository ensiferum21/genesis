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
        if R.descriptor_arms(request):
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


def statement_rows(evidence, tasks):
    """Per-statement rows for a statement evaluation (B20_R7): an arm scores 1 on a statement only
    when its solver attempt succeeded, claimed a proof, and the evaluator's Lean replay of that
    claim from custody is CHECKED. Finding no proof is a valid 0, not an execution failure; a
    sandbox, decoding or harness failure is a FAILED run (scored 0, keeps its cost)."""
    solver, checked = {}, set()
    for status, req, rec in evidence.db.execute('SELECT status,request,receipt FROM attempts ORDER BY rowid'):
        if rec is None or status in ('RUNNING', 'INTERRUPTED'):
            continue
        request = evidence.get(req)
        receipt = evidence.get(rec)
        if request.get('kind') == 'solver' and request.get('arm') in ('candidate', 'baseline'):
            solver[(request['task']['task_id'], request['arm'])] = receipt
        elif request.get('kind') == 'replay' and (receipt.get('replay') or {}).get('status') == 'CHECKED':
            checked.add((request['task_id'], request['arm']))
    rows = []
    for t in tasks:
        if (t.task_id, 'candidate') not in solver or (t.task_id, 'baseline') not in solver:
            continue
        row = {'task_id': t.task_id, 'stratum': t.family, 'status': 'SCORED'}
        for arm in ('candidate', 'baseline'):
            r = solver[(t.task_id, arm)]
            ok = r.get('status') == 'SUCCESS'
            cpu = r.get('cpu_ns') if type(r.get('cpu_ns')) is int else r.get('wall_ns')
            row[arm] = {'value': int(ok and (t.task_id, arm) in checked), 'run': 'SUCCESS' if ok else 'FAILED',
                        'cpu_ns': cpu if type(cpu) is int else 0}
        rows.append(row)
    return rows


def proof_problems(evidence, panel, request, *, replay=True):
    """Re-check every proof claim of a statement evaluation from the raw store alone: the claim
    record must be bound to the solver attempt's proof and the panel statement, the arm's manifest
    and lemma proofs must be in the store and pass custody, and (``replay``) a fresh Lean replay
    must give the recorded status. Returns {'problems', 'replayed', 'claims'}."""
    from .learning import custody as CU
    manifests = {i: evidence.get(h) for i, h in evidence.db.execute(
        "SELECT id,object_hash FROM entities WHERE kind='successor_manifest'")}
    objects = CU.MemoryObjects({i: evidence.get(h)['text'] for i, h in evidence.db.execute(
        "SELECT id,object_hash FROM entities WHERE kind='proof_object'")})
    statements = {x['task_id']: x['statement'] for x in panel['statements']}
    attempts = {}
    for aid, status, req, rec in evidence.db.execute('SELECT id,status,request,receipt FROM attempts ORDER BY rowid'):
        if rec is not None and status not in ('RUNNING', 'INTERRUPTED'):
            attempts[aid] = (evidence.get(req), evidence.get(rec))
    out, replayed, claims = [], 0, 0
    tc = {'checker_identity': CU.checker_identity()['identity']}
    for aid, (req, rec) in attempts.items():
        if req.get('kind') == 'solver' and (rec.get('result') or {}).get('claim') == 'PROOF':
            claims += 1
            if not any(r.get('kind') == 'replay' and r.get('solver_attempt') == aid for r, _ in attempts.values()):
                out.append(f'proof claim {req["task"]["task_id"]}/{req["arm"]} was never replayed')
            if req['descriptor'] != request['arms'].get(req['arm']) or req['task']['statement'] != \
                    statements.get(req['task']['task_id']):
                out.append(f'solver attempt {req["task"]["task_id"]}/{req["arm"]} is not the request arm on the panel')
        if req.get('kind') != 'replay':
            continue
        solver = attempts.get(req.get('solver_attempt'))
        record = req.get('record') or {}
        tid, arm = req.get('task_id'), req.get('arm')
        if solver is None or solver[0].get('arm') != arm or solver[0]['task']['task_id'] != tid:
            out.append(f'replay {tid}/{arm} names no matching solver attempt')
            continue
        claim = solver[1].get('result') or {}
        m = manifests.get(record.get('manifest_id'))
        if m is None or m['manifest_id'] != request['arms'][arm]['parameters']['manifest_id']:
            out.append(f'replay {tid}/{arm}: the arm manifest is not in the store')
            continue
        local = CU.MemoryObjects({l['proof_sha256']: objects.get(l['proof_sha256']) for l in m['lemmas']
                                  if objects.has(l['proof_sha256'])})
        if CU.successor_problems(m, local):
            out.append(f'replay {tid}/{arm}: the arm manifest fails custody in the store')
            continue
        local.put(claim.get('proof') or '')
        if record.get('proof_sha256') != CU._sha(claim.get('proof') or '') or \
                record.get('premise_uids') != claim.get('premise_uids') or record.get('statement') != statements.get(tid):
            out.append(f'replay {tid}/{arm}: the claim record is not bound to the solver output and the panel')
            continue
        if CU.target_problems(record, m, task_statement=statements[tid], objects=local):
            out.append(f'replay {tid}/{arm}: the claim record fails custody')
            continue
        if replay:
            fresh = CU.replay_target(record, m, local, task_statement=statements[tid], trust_context=tc,
                                     name=f'jr{record["record_id"][:12]}')
            replayed += 1
            if fresh['status'] != (rec.get('replay') or {}).get('status'):
                out.append(f'replay {tid}/{arm}: a fresh replay gives {fresh["status"]}, the store records '
                           f'{(rec.get("replay") or {}).get("status")}')
    return {'problems': out, 'replayed': replayed, 'claims': claims}


def recompute(evaluation_root, request, receipt, *, registration_log_entries=None, replay=True):
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
            statements = R.is_statement_request(request)
            pools = [s.get(h) for (h,) in s.db.execute("SELECT object_hash FROM entities WHERE kind=?",
                                                         ('statement_panel' if statements else 'pool',))]
            if len(pools) != 1 or digest(pools[0]) is None:
                out['problems'].append('the evidence store does not hold exactly one pool')
                out['agrees'] = False
                return out
            if statements:
                from .custodian import statement_tasks
                tasks = statement_tasks(pools[0])
                rows = statement_rows(s, tasks)
                proofs = proof_problems(s, pools[0], request, replay=replay)
                out.update(proof_claims=proofs['claims'], proofs_replayed=proofs['replayed'],
                           replay='RERUN' if replay else 'NOT_RERUN')
                out['problems'] += proofs['problems']
            else:
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
