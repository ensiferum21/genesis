"""Narrow offline request/receipt protocol for a separately operated custodian.

This module implements the service, not the fact of independent operation. No
production keys are created by the research CLI. Private panels stay in this service.
"""
import json
import os
from pathlib import Path
import random
import sqlite3
import time
from .common import canonical,bytes_hash,digest,load_json,utcnow,code_identity
from .models import GraphTask,SolverProgram,Limits
from .graphs import canonical_graph,certified_optimum,check_witness,SearchLimit
from .execution import execute
from .store import Store
from .evaluation import paired,sign_test


from .kernel.signing import sign,verify  # re-exported for existing callers
from .kernel import receipts as R


REQUEST_FIELDS={'schema','campaign_id','candidate_version','source_hash','programs','limits','seed',
                'task_count','domain','analysis','exposed_graph_fingerprints','expected_evaluator_hash',
                'campaign_export_sha256','claim_id','statement_hash','scope','evidence_kind','generation_transition',
                'transfer_source_domain'}


def _hex64(h):
    return isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h)


def validate_request(request):
    """Schema v3 binds the request to the campaign's public export bundle and to
    one claim and evidence kind (roadmap R-01).

    v1/v2 requests are refused: v1 had no export binding; v2 named no claim, so
    its receipt could be presented as support for any claim.
    """
    if not isinstance(request,dict) or set(request)!=REQUEST_FIELDS or request['schema']!=R.REQUEST:
        raise ValueError('evaluation request schema')
    problems=R.check_request(request)
    if problems:raise ValueError('evaluation request binding: '+'; '.join(problems))
    for key in ('campaign_id','candidate_version','source_hash','expected_evaluator_hash','campaign_export_sha256'):
        if not _hex64(request[key]):raise ValueError('hash field')
    if not isinstance(request['programs'],dict) or not {'baseline','candidate'}<=set(request['programs']) or len(request['programs'])>5:
        raise ValueError('comparison arms')
    programs={k:SolverProgram.model_validate_json(canonical(v)) for k,v in request['programs'].items()}
    if any(not k.isidentifier() for k in programs):raise ValueError('arm name')
    Limits.model_validate_json(canonical(request['limits']))
    if type(request['seed']) is not int or type(request['task_count']) is not int or not 1<=request['task_count']<=10000:
        raise ValueError('task count or seed')
    if request['domain'] not in R.DOMAINS:raise ValueError('domain')
    if request['analysis']!=R.ANALYSIS_V1:
        raise ValueError('unsupported preregistered analysis')
    if not isinstance(request['exposed_graph_fingerprints'],list):raise ValueError('exposure list')
    for h in request['exposed_graph_fingerprints']:
        if not _hex64(h):raise ValueError('exposure hash')
    return programs


def _private_root(path):
    path=Path(path)
    if not path.is_dir() or path.is_symlink():raise ValueError('pre-existing private directory required')
    st=path.stat()
    if st.st_uid!=os.geteuid() or st.st_mode&0o077:raise ValueError('private root must be owner-only')
    return path.resolve()


SCHEMA='''CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, body BLOB, anchor BLOB, state TEXT);
CREATE TABLE IF NOT EXISTS exposure_graphs(id INTEGER PRIMARY KEY, n INTEGER NOT NULL, edges TEXT NOT NULL,
                                           source TEXT NOT NULL, request_id TEXT);
CREATE TABLE IF NOT EXISTS registry_builds(request_id TEXT PRIMARY KEY, record BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY, n INTEGER NOT NULL, edges TEXT NOT NULL,
                                        request_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS adjudications(graph TEXT PRIMARY KEY, decision TEXT NOT NULL, record BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS exposure_digests(graph_hash TEXT PRIMARY KEY, request_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS panels(request_id TEXT PRIMARY KEY, pool_hash TEXT NOT NULL, salt TEXT NOT NULL,
                                  commitment TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS slots(slot TEXT PRIMARY KEY, request_id TEXT NOT NULL);'''


def _open_custody(root):
    db=sqlite3.connect(root/'custody.sqlite3',isolation_level=None)
    db.execute('PRAGMA synchronous=FULL');db.executescript(SCHEMA)
    return db


def _registry_from_db(db):
    from .exposure import GraphIndex
    index=GraphIndex()
    for n,edges,source in db.execute('SELECT n,edges,source FROM exposure_graphs ORDER BY id'):
        index.add(n,tuple(tuple(e) for e in json.loads(edges)),source)
    return index


# Kinds whose meaning needs evidence this custodian cannot yet check from the export
# (a learned-vs-fixed research lineage, or frozen successor versions): refused, not trusted.
UNSUPPORTED_KINDS={'sealed_improver_evaluation':'needs the research-lineage protocol (roadmap W21)',
                   'sealed_generation_evaluation':'needs frozen successor versions in the export (roadmap W21)'}


def campaign_facts(export):
    """Rebuild the requesting campaign from its export and read what it really is.

    The custodian must not take a request's campaign identity, source identity or
    domain on trust (B14 red team C1): they are read from the campaign history
    contained in the bound export (events.jsonl + objects, hash-chained)."""
    import shutil,tempfile,zipfile
    from .store import rebuild_from_export
    with tempfile.TemporaryDirectory(prefix='genesis-custody-export-') as d:
        with zipfile.ZipFile(export) as z:
            names=z.namelist()
            for n in names:
                p=Path(n)
                if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe path in campaign export')
            if 'events.jsonl' not in names:
                raise ValueError('campaign export has no event history; the request cannot be checked against it')
            z.extractall(d)
        for junk in ('campaign.sqlite3','writer.lock'):
            if (Path(d)/junk).exists():(Path(d)/junk).unlink()
        record=rebuild_from_export(d)
        if record.get('partial_tail_dropped'):raise ValueError('campaign export ends in a partial event')
        with Store(d) as s:
            row=s.db.execute("SELECT object_hash FROM entities WHERE kind='config' ORDER BY id").fetchone()
            config=s.get(row[0]) if row else {}
            facts={'campaign_id':s.state('campaign_id'),'source_hash':s.state('source_hash'),
                   'domain':config.get('domain'),'event_head':record['head']}
        shutil.rmtree(d,ignore_errors=True)
    return facts


def check_request_against_export(request,facts):
    problems=[]
    if request['evidence_kind'] in UNSUPPORTED_KINDS:
        problems.append(f"{request['evidence_kind']} {UNSUPPORTED_KINDS[request['evidence_kind']]}; refused")
    if facts['campaign_id']!=request['campaign_id']:problems.append('request campaign_id differs from the campaign export')
    if facts['source_hash']!=request['source_hash']:problems.append('request source_hash differs from the campaign export')
    if request['evidence_kind']=='sealed_transfer_evaluation':
        if facts['domain']!=request['transfer_source_domain'] or request['domain']==facts['domain']:
            problems.append('a transfer must evaluate on a domain other than the one the campaign worked in, '
                            'and name that campaign domain as its source')
    elif facts['domain']!=request['domain']:
        problems.append('request domain differs from the campaign export domain')
    return problems


def _load_pool(pool_path):
    pool=load_json(pool_path)
    if not isinstance(pool,list) or not pool:raise ValueError('pool must be a non-empty task list')
    tasks=[GraphTask.model_validate_json(canonical(t)) for t in pool]
    return pool,tasks


def register(private_root,request,key_path,operator_id,*,exposure_manifest,campaign_export,pool):
    """Run before outcome exposure. Signed time is an operator attestation,
    not an independent public timestamp service or proof of independence.

    The custodian rebuilds the exposure registry itself from its own manifest of
    public sources plus the requesting campaign's export bundle. A declaration
    that omits any host present in that export is rejected. The sealed panel is
    fixed now: the anchor carries a salted commitment to it, and `evaluate`
    refuses any other pool.
    """
    from .exposure import build_registry,campaign_hosts
    from .graphs import SearchLimit
    root=_private_root(private_root);validate_request(request);rid=digest(request)
    pool_data,pool_tasks=_load_pool(pool)
    if len(pool_tasks)!=request['task_count']:raise ValueError('pool size differs from the preregistered task count')
    salt=os.urandom(32).hex();pool_hash=digest(pool_data)
    commitment=digest({'schema':'genesis-panel-commitment-v1','pool':pool_hash,'salt':salt})
    export=Path(campaign_export)
    if bytes_hash(export.read_bytes())!=request['campaign_export_sha256']:
        raise ValueError('campaign export does not match the request binding')
    problems=check_request_against_export(request,campaign_facts(export))
    if problems:raise ValueError('request is not what the campaign export shows: '+'; '.join(problems))
    manifest_path=Path(exposure_manifest)
    st=manifest_path.stat()
    if manifest_path.is_symlink() or st.st_uid!=os.geteuid() or st.st_mode&0o022:
        raise ValueError('exposure manifest must be a custodian-owned, non-writable-by-others file')
    manifest=load_json(manifest_path)
    repo=Path(__file__).resolve().parents[2]
    index,record=build_registry(manifest,manifest_path.parent,repo,
                                extra_sources=[{'kind':'zip','path':str(export.resolve()),
                                                'label':f'campaign-export:{request["campaign_id"][:16]}'}])
    declared=set(request['exposed_graph_fingerprints']);omitted=0;unscreenable=0
    for k,es in campaign_hosts(export):
        task=GraphTask(task_id='exposure',n=k,edges=es,family='exposure')
        try:
            if canonical_graph(task) not in declared:omitted+=1
        except SearchLimit:unscreenable+=1
    if omitted:
        raise ValueError(f'exposure declaration omits {omitted} host graphs present in the campaign export')
    db=_open_custody(root)
    try:
        slot=R.registration_slot(request)
        payload={'schema':R.PREREG_ANCHOR,'request_hash':rid,'claim_id':request['claim_id'],
                 'statement_hash':request['statement_hash'],'scope':request['scope'],
                 'evidence_kind':request['evidence_kind'],'registration_slot':slot,'registered_at':utcnow(),
                 'operator_id':operator_id,'exposure_registry_root':record['root'],
                 'exposure_graphs':record['graphs'],'declaration_unscreenable_graphs':unscreenable,
                 'panel_commitment':commitment}
        problems=R.check_anchor(payload)
        if problems:raise RuntimeError('custodian built an invalid anchor: '+'; '.join(problems))
        anchor=sign(payload,key_path)
        with db:
            db.execute('BEGIN IMMEDIATE')
            taken=db.execute('SELECT request_id FROM slots WHERE slot=?',(slot,)).fetchone()
            if taken:
                # One preregistration per claim slot: re-running until a favourable draw is selective reporting.
                raise ValueError('this claim slot (claim, kind, domain, generation) is already registered by '
                                 f'request {taken[0][:12]}; a new claim needs a new claim_id')
            db.execute('INSERT INTO slots VALUES (?,?)',(slot,rid))
            db.execute('INSERT INTO requests VALUES (?,?,?,?)',(rid,canonical(request),canonical(anchor),'REGISTERED'))
            db.execute('INSERT INTO registry_builds VALUES (?,?)',(rid,canonical(record)))
            db.execute('INSERT INTO panels VALUES (?,?,?,?)',(rid,pool_hash,salt,commitment))
            known=_registry_from_db(db)
            rows=[(k,json.dumps([list(e) for e in es]),source,rid) for k,es,source in index.items()
                  if known.find(k,es) is None]
            db.executemany('INSERT INTO exposure_graphs(n,edges,source,request_id) VALUES (?,?,?,?)',rows)
            # Declared fingerprints can only make screening stricter.
            db.executemany('INSERT OR IGNORE INTO exposure_digests VALUES (?,?)',[(h,rid) for h in sorted(declared)])
        return anchor
    finally:db.close()


def sealed_index(private_root):
    """Evaluator-side index of everything sealed: reserved/consumed pool graphs and
    sealed statements in <private_root>/sealed_statements/*.json (lists of strings)."""
    from .kernel.leakscan import SealedIndex
    root=_private_root(private_root);index=SealedIndex()
    db=_open_custody(root)
    try:
        for i,(n,edges) in enumerate(db.execute('SELECT n,edges FROM reservations')):
            index.add_graph(f'reserved-{i}',n,json.loads(edges))
    finally:db.close()
    statements=root/'sealed_statements'
    if statements.is_dir():
        for f in sorted(statements.glob('*.json')):
            for j,text in enumerate(load_json(f)):
                index.add_statement(f'{f.stem}-{j}',text)
    return index


def screen_for_research(private_root,candidates,key_path,operator_id,*,query_budget=10000):
    """Narrow screening endpoint: returns a signed list of decisions only."""
    from .kernel.leakscan import OracleScreener
    oracle=OracleScreener(sealed_index(private_root),query_budget=query_budget)
    decisions=[oracle(c) for c in candidates]
    root=_private_root(private_root)
    ledger=root/'screening_ledger.jsonl'
    with open(ledger,'ab') as f:
        for entry in oracle.private_ledger():f.write(canonical(entry)+b'\n')
    return sign({'schema':'genesis-screening-receipt-v1','decisions':decisions,'operator_id':operator_id,
                 'candidates_sha256':digest(candidates),'issued_at':utcnow()},key_path)


def adjudicate(private_root,task,decision,key_path,operator_id,reason):
    """Record a signed near-duplicate decision before freeze (spec §18.2)."""
    if decision not in ('ALLOW','BLOCK'):raise ValueError('decision')
    root=_private_root(private_root)
    graph=json.dumps([task.n,[list(e) for e in task.edges]])
    record=sign({'schema':'genesis-adjudication-v1','graph':graph,'decision':decision,'reason':reason,
                 'operator_id':operator_id,'decided_at':utcnow()},key_path)
    db=_open_custody(root)
    try:
        with db:
            db.execute('INSERT INTO adjudications VALUES (?,?,?)',(graph,decision,canonical(record)))
    finally:db.close()
    return record


def reference_optimum(task,evidence=None):
    """Evaluator's exact optimum: dual exhaustive solvers up to 24 edges, otherwise a
    SAT/DRAT upper certificate (checked by drat-trim) meeting a checked witness."""
    if len(task.edges)<=24:return certified_optimum(task)
    from .verification.sat import certified_bounds
    from .dsl import solve
    start=solve(task,SolverProgram(rounds=8),100000,0)['selected']
    bounds=certified_bounds(task,seconds=600,start_witness=start)
    if bounds['status']!='OPTIMALITY_CHECKED':
        raise RuntimeError('CHECKER_ERROR: evaluator could not certify the optimum; task unusable')
    cert=dict(bounds['upper_certificate'])
    if evidence is not None and bounds.get('proof'):
        cert['proof_object']=evidence.put_bytes(bounds['proof'])
    if evidence is not None:
        # Full certificate custody inside the private evidence store (R-03): CNF, proof, witness.
        from .verification.certificates import build,persist
        cert['certificate_bundle']=persist(evidence,*build(task,bounds))
    return {'status':'FINITE_CERTIFIED','value':bounds['upper'],'witness':[list(e) for e in bounds['witness']],
            'upper_certificate':cert,'scope':'this finite host only','formal_proof':False,'novelty':'UNKNOWN',
            'method':'SAT_DRAT_UPPER+CHECKED_WITNESS'}


def evaluate(private_root,request_id,pool_path,key_path,operator_id):
    root=_private_root(private_root)
    db=_open_custody(root)
    try:
        row=db.execute('SELECT body,anchor,state FROM requests WHERE id=?',(request_id,)).fetchone()
        if not row:raise ValueError('request not preregistered')
        request=json.loads(row[0]);anchor=json.loads(row[1]);programs=validate_request(request)
        if row[2]!='REGISTERED':raise FileExistsError('evaluation already consumed; no automatic retry')
        identity=code_identity(Path(__file__).resolve().parents[2])['sha256']
        if identity!=request['expected_evaluator_hash']:raise ValueError('pinned evaluator source mismatch')
        pool,tasks=_load_pool(pool_path)
        if len(pool)!=request['task_count']:raise ValueError('incomplete pool')
        committed=db.execute('SELECT pool_hash,commitment FROM panels WHERE request_id=?',(request_id,)).fetchone()
        if committed is None or committed[0]!=digest(pool):
            raise ValueError('pool does not match the panel committed at registration')
        commitment=committed[1]
        if any(t.domain!=request['domain'] or t.split not in ('CONFIRM','FUTURE') for t in tasks):
            raise ValueError('wrong sealed pool domain/split')
        if len({t.task_id for t in tasks})!=len(tasks):raise ValueError('duplicate task identifiers')
        from .exposure import GraphIndex
        panel=GraphIndex()
        for t in tasks:
            if not panel.add(t.n,t.edges,t.task_id):raise ValueError('isomorphic duplicates in panel')
        db.execute('BEGIN IMMEDIATE')
        try:
            if db.execute('SELECT state FROM requests WHERE id=?',(request_id,)).fetchone()[0]!='REGISTERED':
                raise FileExistsError('concurrent evaluation reservation')
            exposed=_registry_from_db(db)
            reserved=GraphIndex()
            for n,edges,rid in db.execute('SELECT n,edges,request_id FROM reservations'):
                reserved.add(n,tuple(tuple(e) for e in json.loads(edges)),rid)
            decisions={g:d for g,d in db.execute('SELECT graph,decision FROM adjudications')}
            for t in tasks:
                key=json.dumps([t.n,[list(e) for e in t.edges]])
                if exposed.find(t.n,t.edges) is not None:
                    raise ValueError('panel overlaps research-visible exposure')
                try:fingerprint=canonical_graph(t)
                except SearchLimit:fingerprint=None
                if fingerprint and db.execute('SELECT 1 FROM exposure_digests WHERE graph_hash=?',(fingerprint,)).fetchone():
                    raise ValueError('panel overlaps research-visible exposure (declared fingerprint)')
                if reserved.find(t.n,t.edges) is not None:
                    raise ValueError('panel task was already consumed by an earlier evaluation')
                if decisions.get(key)=='BLOCK':raise ValueError('panel task blocked by adjudication')
                if exposed.near(t.n,t.edges) and decisions.get(key)!='ALLOW':
                    raise ValueError('near-duplicate of an exposed graph requires adjudication before use')
                db.execute('INSERT INTO reservations(n,edges,request_id) VALUES (?,?,?)',
                           (t.n,json.dumps([list(e) for e in t.edges]),request_id))
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
                    try:optimum=reference_optimum(task,evidence)
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
        payload={'schema':R.SCIENTIFIC_RECEIPT,'evidence_kind':request['evidence_kind'],
                 'claim_id':request['claim_id'],'statement_hash':request['statement_hash'],'scope':request['scope'],
                 'campaign_id':request['campaign_id'],'request_hash':request_id,
                 'anchor_hash':digest(anchor),'candidate_version':request['candidate_version'],
                 'candidate_program_hash':R.program_identity(request['programs']['candidate']),
                 'baseline_version':R.program_identity(request['programs']['baseline']),'source_hash':request['source_hash'],
                 'evaluator_hash':identity,'analysis':request['analysis'],'domain':request['domain'],
                 'domain_contract_hash':R.domain_contract_hash(request['domain']),
                 'transfer_source_domain':request['transfer_source_domain'],
                 'generation_transition':request['generation_transition'],'panel_commitment':commitment,
                 'task_count':len(tasks),'raw_evidence_root':integrity['head'],'raw_evidence_complete':complete,
                 'expected_rows':len(tasks)*len(programs),'completed_rows':total_rows,'execution_failures':failures,
                 'wins':comparison['wins'],'losses':comparison['losses'],'ties':comparison['ties'],
                 'paired_p':comparison['exploratory_sign_p'],'family_p':comparison['family_sensitivity_p'],
                 'outcome':None,'operator_id':operator_id,'registered_at':anchor['payload']['registered_at'],
                 'completed_at':utcnow(),'screen':'CUSTODIAN_BUILT_REGISTRY_ISOMORPHISM_AND_NEAR_DUPLICATE',
                 'independence':'OPERATOR_ATTESTATION_REQUIRED'}
        payload['outcome']=R.derive_outcome(payload)
        problems=R.check_receipt(payload,request['evidence_kind'])
        if problems:raise RuntimeError('custodian built an invalid receipt: '+'; '.join(problems))
        receipt=sign(payload,key_path)
        (work/'public_receipt.json').write_bytes(canonical(receipt))
        db.execute("UPDATE requests SET state='COMPLETE' WHERE id=?",(request_id,))
        return receipt
    finally:db.close()


from .kernel.roles import TRUST_ROOT_ENV,DEFAULT_TRUST_ROOT,ROLE_FIELDS,load_role_registry  # re-exported


def release_preflight(request,anchor,receipt,audit,*,trust_root=None):
    """Check externally pinned roles. Never lets a builder-created key self-promote.

    Uses the same receipt semantics as the evidence kernel and phase machine
    (kernel.receipts): exact schemas, role-to-kind authorization, request and
    anchor binding, and the signed outcome re-derived from the signed counts.
    """
    registry,reasons=load_role_registry(trust_root)
    if registry is None:
        return {'status':'BLOCKED','reasons':reasons,'promotion_allowed':False}
    pins=registry['pins']
    try:
        validate_request(request)
        rid=digest(request);kind=request['evidence_kind']
        a,why=R.accept_receipt(anchor,'preregistration_anchor',pins)
        reasons+=why
        r,why=R.accept_receipt(receipt,kind,pins)  # trusted role, schema, outcome, source eligibility
        reasons+=why
        review=verify(audit,pins['auditor_key'])
        if a is not None and r is not None:
            reasons+=R.anchor_mismatches(r,a,anchor)
            if a['request_hash']!=rid or r['request_hash']!=rid:reasons.append('unbound preregistration')
            expected_rows=request['task_count']*len(request['programs'])
            if a['registration_slot']!=R.registration_slot(request):reasons.append('anchor registers a different slot')
            for field,want in (('claim_id',request['claim_id']),('campaign_id',request['campaign_id']),
                               ('statement_hash',request['statement_hash']),('scope',request['scope']),
                               ('candidate_program_hash',R.program_identity(request['programs']['candidate'])),
                               ('candidate_version',request['candidate_version']),
                               ('evaluator_hash',request['expected_evaluator_hash']),
                               ('source_hash',request['source_hash']),('domain',request['domain']),
                               ('baseline_version',R.program_identity(request['programs']['baseline'])),
                               ('task_count',request['task_count']),('expected_rows',expected_rows),
                               ('generation_transition',request['generation_transition']),
                               ('transfer_source_domain',request['transfer_source_domain'])):
                if r[field]!=want:reasons.append(f'receipt {field} differs from the preregistered request')
            if r['outcome']=='INVALID':reasons.append('incomplete or inconsistent evidence (outcome INVALID)')
            elif r['outcome']=='INCONCLUSIVE':reasons.append('execution failures require adjudication (outcome INCONCLUSIVE)')
            elif r['outcome']!='SUPPORTED':reasons.append('preregistered superiority not supported (outcome NOT_SUPPORTED)')
        if review.get('request_hash')!=rid or review.get('receipt_hash')!=digest(receipt):reasons.append('audit scope mismatch')
        if review.get('status')!='PASS' or review.get('open_critical')!=0:reasons.append('independent audit not passing')
        if review.get('independent_operation_verified') is not True:reasons.append('custody independence not verified')
        if review.get('raw_replay_verified') is not True:reasons.append('private evidence replay not verified')
        if review.get('formal_replay_verified') is not True:reasons.append('formal replay not verified')
    except Exception as exc:reasons.append('signature/schema verification failed: '+type(exc).__name__)
    return {'status':'EXTERNAL_RELEASE_REVIEW_READY' if not reasons else 'BLOCKED','reasons':reasons,
            'promotion_allowed':False,'next_authority':pins['release_authority_id'],
            'trust_root':registry['trust_root'],'root_key_sha256':registry['root_key_sha256'],
            'note':'External release authority must record its decision; local preflight never activates a release.'}
