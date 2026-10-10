"""Narrow offline request/receipt protocol for a separately operated custodian.

This module implements the service, not the fact of independent operation. No
production keys are created by the research CLI. Private panels stay in this service.
"""
import base64
import json
import os
from pathlib import Path
import random
import sqlite3
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from .common import canonical,bytes_hash,digest,load_json,utcnow,code_identity
from .models import GraphTask,SolverProgram,Limits
from .graphs import canonical_graph,certified_optimum,check_witness
from .execution import execute
from .store import Store
from .evaluation import paired,sign_test


def sign(payload,key_path):
    key=serialization.load_pem_private_key(Path(key_path).read_bytes(),password=None)
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Ed25519 private key required')
    return {'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode()}


def verify(envelope,public_key_b64):
    if not isinstance(envelope,dict) or set(envelope)!={'payload','signature'}:raise ValueError('signed envelope schema')
    key=Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64,validate=True))
    key.verify(base64.b64decode(envelope['signature'],validate=True),canonical(envelope['payload']))
    return envelope['payload']


def validate_request(request):
    fields={'schema','campaign_id','candidate_version','source_hash','programs','limits','seed',
            'task_count','domain','analysis','exposed_graph_fingerprints','expected_evaluator_hash'}
    if not isinstance(request,dict) or set(request)!=fields or request['schema']!='genesis-evaluation-request-v1':
        raise ValueError('evaluation request schema')
    for key in ('campaign_id','candidate_version','source_hash','expected_evaluator_hash'):
        h=request[key]
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('hash field')
    if not isinstance(request['programs'],dict) or not {'baseline','candidate'}<=set(request['programs']) or len(request['programs'])>5:
        raise ValueError('comparison arms')
    programs={k:SolverProgram.model_validate_json(canonical(v)) for k,v in request['programs'].items()}
    if any(not k.isidentifier() for k in programs):raise ValueError('arm name')
    Limits.model_validate_json(canonical(request['limits']))
    if type(request['seed']) is not int or type(request['task_count']) is not int or not 1<=request['task_count']<=10000:
        raise ValueError('task count or seed')
    if request['domain'] not in ('c4_host_v2','triangle_free_host_v1'):raise ValueError('domain')
    if request['analysis']!={'primary':'paired-edge-count','alpha':0.05,'family_sensitivity':True,'hypotheses':1}:
        raise ValueError('unsupported preregistered analysis')
    if not isinstance(request['exposed_graph_fingerprints'],list):raise ValueError('exposure list')
    for h in request['exposed_graph_fingerprints']:
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('exposure hash')
    return programs


def _private_root(path):
    path=Path(path)
    if not path.is_dir() or path.is_symlink():raise ValueError('pre-existing private directory required')
    st=path.stat()
    if st.st_uid!=os.geteuid() or st.st_mode&0o077:raise ValueError('private root must be owner-only')
    return path.resolve()


def register(private_root,request,key_path,operator_id):
    """Run before outcome exposure. Signed time is an operator attestation,
    not an independent public timestamp service or proof of independence.
    """
    root=_private_root(private_root);validate_request(request);rid=digest(request)
    db=sqlite3.connect(root/'custody.sqlite3')
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.executescript('''CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, body BLOB, anchor BLOB, state TEXT);
                           CREATE TABLE IF NOT EXISTS exposure(graph_hash TEXT PRIMARY KEY, source TEXT NOT NULL);
                           CREATE TABLE IF NOT EXISTS reservations(graph_hash TEXT PRIMARY KEY, request_id TEXT NOT NULL);''')
        payload={'schema':'genesis-prereg-anchor-v1','request_hash':rid,'registered_at':utcnow(),'operator_id':operator_id}
        anchor=sign(payload,key_path)
        with db:
            db.execute('INSERT INTO requests VALUES (?,?,?,?)',(rid,canonical(request),canonical(anchor),'REGISTERED'))
            db.executemany('INSERT OR IGNORE INTO exposure VALUES (?,?)',[(h,'request-visible-exposure') for h in request['exposed_graph_fingerprints']])
        return anchor
    finally:db.close()


def evaluate(private_root,request_id,pool_path,key_path,operator_id):
    root=_private_root(private_root)
    db=sqlite3.connect(root/'custody.sqlite3',isolation_level=None)
    try:
        db.execute('PRAGMA synchronous=FULL')
        row=db.execute('SELECT body,anchor,state FROM requests WHERE id=?',(request_id,)).fetchone()
        if not row:raise ValueError('request not preregistered')
        request=json.loads(row[0]);anchor=json.loads(row[1]);programs=validate_request(request)
        if row[2]!='REGISTERED':raise FileExistsError('evaluation already consumed; no automatic retry')
        identity=code_identity(Path(__file__).resolve().parents[2])['sha256']
        if identity!=request['expected_evaluator_hash']:raise ValueError('pinned evaluator source mismatch')
        pool=load_json(pool_path)
        if not isinstance(pool,list) or len(pool)!=request['task_count']:raise ValueError('incomplete pool')
        tasks=[GraphTask.model_validate_json(canonical(t)) for t in pool]
        if any(t.domain!=request['domain'] or t.split not in ('CONFIRM','FUTURE') for t in tasks):
            raise ValueError('wrong sealed pool domain/split')
        if len({t.task_id for t in tasks})!=len(tasks):raise ValueError('duplicate task identifiers')
        fingerprints=[canonical_graph(t) for t in tasks]
        if len(set(fingerprints))!=len(tasks):raise ValueError('isomorphic duplicates in panel')
        db.execute('BEGIN IMMEDIATE')
        try:
            if db.execute('SELECT state FROM requests WHERE id=?',(request_id,)).fetchone()[0]!='REGISTERED':
                raise FileExistsError('concurrent evaluation reservation')
            for h in fingerprints:
                if db.execute('SELECT 1 FROM exposure WHERE graph_hash=?',(h,)).fetchone():
                    raise ValueError('panel overlaps research-visible exposure')
                db.execute('INSERT INTO reservations VALUES (?,?)',(h,request_id))
            db.execute("UPDATE requests SET state='CONSUMED_NO_RETRY' WHERE id=?",(request_id,))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
        work=root/'evaluations'/request_id
        work.mkdir(parents=True,mode=0o700)
        limits=Limits.model_validate_json(canonical(request['limits']))
        byarm={name:[] for name in programs};total_rows=0;failures=0
        with Store(work) as evidence:
            evidence.save('request',request_id,request)
            evidence.save('pool',digest(pool),pool)
            evidence.save('anchor',request_id,anchor)
            try:
                for task in tasks:
                    opt_aid=evidence.start('optimum-'+task.task_id,{'kind':'exact-check','task':task.model_dump(mode='json')})
                    start=time.monotonic_ns()
                    try:optimum=certified_optimum(task)
                    except BaseException as exc:
                        evidence.finish(opt_aid,{'status':'CHECKER_ERROR','error':type(exc).__name__,'wall_ns':time.monotonic_ns()-start});raise
                    evidence.finish(opt_aid,{'status':'SUCCESS','result':optimum,'wall_ns':time.monotonic_ns()-start})
                    names=sorted(programs);seed=int(digest({'seed':request['seed'],'task':task.task_id})[:16],16)
                    random.Random(seed).shuffle(names)
                    for name in names:
                        aid=evidence.start(task.task_id+'-'+name,{'kind':'solver','task':task.model_dump(mode='json'),
                            'program':programs[name].model_dump(mode='json'),'arm':name,'seed':seed,'limits':request['limits']})
                        receipt=execute(task,programs[name],limits,seed)
                        rh=evidence.finish(aid,receipt);total_rows+=1
                        value=receipt.get('result',{}).get('value',0)
                        if value>optimum['value']:raise RuntimeError('exact checker disagreement')
                        failures+=int(receipt['status']!='SUCCESS')
                        byarm[name].append({'task_id':task.task_id,'family':task.family,'value':value,'status':receipt['status'],'receipt':rh})
                comparison=paired([{'task_id':a['task_id'],'family':a['family'],'candidate':a['value'],'baseline':b['value']}
                                   for a,b in zip(byarm['candidate'],byarm['baseline'])])
                evidence.save('comparison',request_id,comparison)
                integrity=evidence.verify();evidence.snapshot('complete.sqlite3')
                complete=True
            except BaseException as exc:
                evidence.event('EVALUATION_FAILED',{'exception':type(exc).__name__,'message':str(exc)})
                evidence.interrupt_running();raise
        payload={'schema':'genesis-evaluation-receipt-v1','request_hash':request_id,
                 'candidate_version':request['candidate_version'],'pool_hash':digest(pool),
                 'evaluator_hash':identity,'operator_id':operator_id,'completed_at':utcnow(),
                 'anchor_hash':digest(anchor),'private_evidence_head':integrity['head'],
                 'expected_rows':len(tasks)*len(programs),'completed_rows':total_rows,'execution_failures':failures,
                 'wins':comparison['wins'],'losses':comparison['losses'],'ties':comparison['ties'],
                 'paired_p':comparison['exploratory_sign_p'],'family_p':comparison['family_sensitivity_p'],
                 'screen':'EXACT_ISOMORPHISM_WITH_EXPOSURE_LEDGER','raw_evidence_complete':complete,
                 'independence':'OPERATOR_ATTESTATION_REQUIRED','promotion_allowed':False}
        receipt=sign(payload,key_path)
        (work/'public_receipt.json').write_bytes(canonical(receipt))
        db.execute("UPDATE requests SET state='COMPLETE' WHERE id=?",(request_id,))
        return receipt
    finally:db.close()


def release_preflight(request,anchor,receipt,audit,*,pins):
    """Check externally pinned roles. Never lets a builder-created key self-promote."""
    reasons=[]
    if set(pins)!={'custodian_key','prereg_key','auditor_key','release_authority_id'}:
        return {'status':'BLOCKED','reasons':['independent role pins unavailable'],'promotion_allowed':False}
    if not pins['release_authority_id'] or len({pins['custodian_key'],pins['prereg_key'],pins['auditor_key']})<3:
        return {'status':'BLOCKED','reasons':['independent role identities required'],'promotion_allowed':False}
    try:
        validate_request(request)
        a=verify(anchor,pins['prereg_key']);r=verify(receipt,pins['custodian_key']);review=verify(audit,pins['auditor_key'])
        rid=digest(request)
        if a.get('request_hash')!=rid or r.get('request_hash')!=rid:reasons.append('unbound preregistration')
        if r.get('anchor_hash')!=digest(anchor):reasons.append('anchor mismatch')
        if r.get('candidate_version')!=request['candidate_version'] or r.get('evaluator_hash')!=request['expected_evaluator_hash']:
            reasons.append('version mismatch')
        expected=request['task_count']*len(request['programs'])
        if r.get('completed_rows')!=expected or r.get('expected_rows')!=expected or r.get('raw_evidence_complete') is not True:
            reasons.append('incomplete evidence')
        if any(type(r.get(k)) is not int or r[k]<0 for k in ('wins','losses','ties')):
            reasons.append('invalid outcome counts')
        elif sum(r[k] for k in ('wins','losses','ties'))!=request['task_count']:
            reasons.append('outcome counts do not cover the preregistered pool')
        elif r.get('paired_p')!=sign_test(r['wins'],r['losses']):
            reasons.append('statistics do not match signed counts')
        from datetime import datetime
        try:
            before=datetime.fromisoformat(a['registered_at']);after=datetime.fromisoformat(r['completed_at'])
            if before.tzinfo is None or after.tzinfo is None or before>=after:
                reasons.append('invalid signed chronology')
        except (KeyError,ValueError,TypeError):reasons.append('missing signed chronology')
        if r.get('execution_failures')!=0:reasons.append('execution failures require adjudication')
        if review.get('request_hash')!=rid or review.get('receipt_hash')!=digest(receipt):reasons.append('audit scope mismatch')
        if review.get('status')!='PASS' or review.get('open_critical')!=0:reasons.append('independent audit not passing')
        if review.get('independent_operation_verified') is not True:reasons.append('custody independence not verified')
        if review.get('raw_replay_verified') is not True:reasons.append('private evidence replay not verified')
        if review.get('formal_replay_verified') is not True:reasons.append('formal replay not verified')
        if any(type(r.get(k)) not in (float,int) or not 0<=r[k]<=1 for k in ('paired_p','family_p')):
            reasons.append('invalid statistics')
        elif max(r['paired_p'],r['family_p'])>request['analysis']['alpha']:reasons.append('preregistered superiority not supported')
    except Exception as exc:reasons.append('signature/schema verification failed: '+type(exc).__name__)
    return {'status':'EXTERNAL_RELEASE_REVIEW_READY' if not reasons else 'BLOCKED','reasons':reasons,
            'promotion_allowed':False,'next_authority':pins['release_authority_id'],
            'note':'External release authority must record its decision; local preflight never activates a release.'}
