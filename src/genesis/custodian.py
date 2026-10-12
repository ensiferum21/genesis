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
from .common import atomic_write,canonical,bytes_hash,digest,load_json,utcnow,code_identity
from .faults import point
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
    if not R.analysis_ok(request['analysis']):
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
CREATE TABLE IF NOT EXISTS slots(slot TEXT PRIMARY KEY, request_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS registration_log(seq INTEGER PRIMARY KEY, entry BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS decision_records(request_id TEXT PRIMARY KEY, record BLOB NOT NULL);'''


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


def _log_entries(db):
    return [json.loads(e) for (e,) in db.execute('SELECT entry FROM registration_log ORDER BY seq')]


def _append_log(db,kind,fields):
    """Append one public registration-log entry; call inside the transaction that makes the change."""
    from .custody_records import new_entry
    entry=new_entry(_log_entries(db),kind,fields)
    db.execute('INSERT INTO registration_log VALUES (?,?)',(entry['seq'],canonical(entry)))
    return entry


def _is_v2(request):
    from .kernel.analysis import PLAN_SCHEMA
    return isinstance(request['analysis'],dict) and request['analysis'].get('schema')==PLAN_SCHEMA


def registration_log(private_root,key_path):
    """The signed public registration log (W06): every registration, reservation and result,
    with hypothesis families; names no task."""
    from .custody_records import export_log
    root=_private_root(private_root);db=_open_custody(root)
    try:return export_log(_log_entries(db),sign,key_path)
    finally:db.close()


# Kinds whose meaning needs evidence this custodian cannot yet check from the export: refused,
# not trusted. A generation evaluation is checked against the export's native research-lineage
# records (lineage.export_from_store; B20_R4, H08); an improver evaluation needs two research
# lineages (learned and fixed policy) evaluated jointly, which no export carries yet.
UNSUPPORTED_KINDS={'sealed_improver_evaluation':'needs paired research lineages (learned and fixed policy) evaluated '
                                               'jointly, which the export protocol does not carry yet (roadmap W21)'}


def generation_problems(request,facts):
    """Why a sealed_generation_evaluation request is not a qualifying transition of the campaign.

    The transition must be one of the export's ACCEPTED transitions inside the qualifying chain
    (``lineage.accepted_chain``: the validator found no problem on it or on any transition
    before it); the candidate arm must run the child version's solver and the baseline arm the
    parent version's; the transition must change the evaluated program."""
    from . import lineage as L
    lin=facts.get('lineage')
    if lin is None or lin.get('source')!='native':
        return ['sealed_generation_evaluation needs native research-lineage records in the campaign export; refused']
    chain=L.accepted_chain(lin)
    t=request.get('generation_transition') or {}
    qualifying={x['transition_id']:x for x in lin['transitions'] if x['transition_id'] in chain['transitions']}
    match=[x for x in qualifying.values() if x.get('index')==t.get('index') and x.get('from_version')==t.get('from_version')
           and x.get('to_version')==t.get('to_version')]
    if not match:
        codes=sorted({p['code'] for p in chain['problems']})
        return ['generation_transition is not a qualifying transition of the campaign lineage'
                +(f" (lineage problems: {', '.join(codes)})" if codes else '')]
    out=[]
    child,parent=lin['versions'][t['to_version']],lin['versions'][t['from_version']]
    try:
        if R.program_identity(request['programs']['candidate'])!=R.program_identity(child['solver']):
            out.append("the candidate arm is not the child version's solver")
        if R.program_identity(request['programs']['baseline'])!=R.program_identity(parent['solver']):
            out.append("the baseline arm is not the parent version's solver")
        if R.program_identity(child['solver'])==R.program_identity(parent['solver']):
            out.append('the transition does not change the evaluated program (nothing to evaluate)')
    except Exception as exc:
        out.append(f'generation programs could not be checked ({type(exc).__name__})')
    if child.get('source')!=request['source_hash']:out.append('child version source differs from the request source')
    return out


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
            def entities(kind):
                return [(i,s.get(h)) for i,h in s.db.execute('SELECT id,object_hash FROM entities WHERE kind=? ORDER BY id',(kind,))]
            configs=entities('config')
            written={}
            for (raw,) in s.db.execute('SELECT body FROM events ORDER BY seq'):
                body=json.loads(raw)
                if body['kind']=='STATE_UPDATED':
                    upd=s.get(body['payload'])
                    if upd['key'] in ('campaign_id','source_hash'):written.setdefault(upd['key'],set()).add(canonical(upd['value']))
            summary=s.state('summary') or {}
            from . import lineage as L
            facts={'campaign_id':s.state('campaign_id'),'source_hash':s.state('source_hash'),
                   'lineage':L.export_from_store(s),
                   'domain':configs[0][1].get('domain') if len(configs)==1 else None,
                   'config_entities':len(configs),
                   'identity_rewritten':any(len(v)>1 for v in written.values()),
                   'phase':s.state('phase'),'latest_program':s.state('latest_program'),
                   'candidate_versions':dict(entities('candidate_version')),
                   'strongest_baseline':(summary.get('generations') or [{}])[-1].get('baseline'),
                   'research_domains':sorted({task.get('domain') for _,task in entities('task')
                                              if task.get('split') in ('DEV','SELECT')}),
                   'event_head':record['head']}
        shutil.rmtree(d,ignore_errors=True)
    return facts


def check_request_against_export(request,facts):
    """The request must describe the frozen candidate this campaign actually produced."""
    from .dsl import baseline_programs
    problems=[]
    generation=request['evidence_kind']=='sealed_generation_evaluation'
    if request['evidence_kind'] in UNSUPPORTED_KINDS:
        problems.append(f"{request['evidence_kind']} {UNSUPPORTED_KINDS[request['evidence_kind']]}; refused")
    if generation:problems+=generation_problems(request,facts)
    if facts['identity_rewritten']:problems.append('campaign identity or source was rewritten in the export history')
    if facts['config_entities']!=1:problems.append('campaign export must hold exactly one resolved configuration')
    if facts['campaign_id']!=request['campaign_id']:problems.append('request campaign_id differs from the campaign export')
    if facts['source_hash']!=request['source_hash']:problems.append('request source_hash differs from the campaign export')
    if any(d!=facts['domain'] for d in facts['research_domains']):
        problems.append('campaign research ran on a domain other than its configuration states')
    if request['evidence_kind']=='sealed_transfer_evaluation':
        if facts['domain']!=request['transfer_source_domain'] or request['domain']==facts['domain']:
            problems.append('a transfer must evaluate on a domain other than the one the campaign worked in, '
                            'and name that campaign domain as its source')
    elif facts['domain']!=request['domain']:
        problems.append('request domain differs from the campaign export domain')
    if facts['phase']!='CANDIDATE_FROZEN':
        problems.append(f"campaign export is not of a frozen candidate (phase {facts['phase']})")
    if generation:return problems     # the arms are the transition's versions, checked above
    try:
        candidate=R.program_identity(request['programs']['candidate'])
        doc=facts['candidate_versions'].get(request['candidate_version'])
        if doc is None or digest(doc)!=request['candidate_version']:
            problems.append('candidate_version is not a frozen version recorded in the campaign export')
        elif R.program_identity(doc.get('program'))!=candidate or doc.get('source')!=request['source_hash']:
            problems.append('candidate_version does not describe the requested candidate program and source')
        if facts['latest_program'] is None or R.program_identity(facts['latest_program'])!=candidate:
            problems.append("the candidate program is not the campaign's frozen program")
        strongest=baseline_programs().get(facts['strongest_baseline'])
        if strongest is None or R.program_identity(strongest.model_dump(mode='json'))!= \
                R.program_identity(request['programs']['baseline']):
            problems.append("the baseline is not the campaign's strongest conventional baseline")
    except Exception as exc:
        problems.append(f'candidate/baseline programs could not be checked ({type(exc).__name__})')
    return problems


def _load_pool(pool_path):
    pool=load_json(pool_path)
    if not isinstance(pool,list) or not pool:raise ValueError('pool must be a non-empty task list')
    tasks=[GraphTask.model_validate_json(canonical(t)) for t in pool]
    return pool,tasks


def register(private_root,request,key_path,operator_id,*,exposure_manifest,campaign_export,pool,decision_record=None):
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
    if _is_v2(request):
        # A v2 plan must name a published (FROZEN) pre-freeze decision record that agrees with it.
        from . import decision_record as DR
        problems=DR.problems(decision_record,request['analysis'],task_count=request['task_count'],require_frozen=True)
        if problems:raise ValueError('decision record: '+'; '.join(problems))
    elif decision_record is not None:
        raise ValueError('a decision record accompanies a v2 analysis plan only')
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
        slot=R.registration_slot(request);slots=R.registration_slots(request)
        payload={'schema':R.PREREG_ANCHOR,'request_hash':rid,'claim_id':request['claim_id'],
                 'statement_hash':request['statement_hash'],'scope':request['scope'],
                 'evidence_kind':request['evidence_kind'],'registration_slot':slot,'registered_at':utcnow(),
                 'operator_id':operator_id,'exposure_registry_root':record['root'],
                 'exposure_graphs':record['graphs'],'declaration_unscreenable_graphs':unscreenable,
                 'panel_commitment':commitment}
        problems=R.check_anchor(payload)
        if problems:raise RuntimeError('custodian built an invalid anchor: '+'; '.join(problems))
        anchor=sign(payload,key_path)
        from .custody_records import family_of,family_size_of,registration_problems
        with db:
            db.execute('BEGIN IMMEDIATE')
            if _is_v2(request):
                problems=registration_problems(_log_entries(db),request)
                if problems:raise ValueError('hypothesis family: '+'; '.join(problems))
            for one in slots:
                taken=db.execute('SELECT request_id FROM slots WHERE slot=?',(one,)).fetchone()
                if taken:
                    # One sealed draw per claim and per candidate: re-running until a favourable draw is
                    # selective reporting, whatever the claim is renamed to.
                    raise ValueError('this claim or candidate slot (campaign, kind, domain, generation) is already '
                                     f'registered by request {taken[0][:12]}')
            db.executemany('INSERT INTO slots VALUES (?,?)',[(one,rid) for one in slots])
            db.execute('INSERT INTO requests VALUES (?,?,?,?)',(rid,canonical(request),canonical(anchor),'REGISTERED'))
            db.execute('INSERT INTO registry_builds VALUES (?,?)',(rid,canonical(record)))
            db.execute('INSERT INTO panels VALUES (?,?,?,?)',(rid,pool_hash,salt,commitment))
            if decision_record is not None:
                db.execute('INSERT INTO decision_records VALUES (?,?)',(rid,canonical(decision_record)))
            _append_log(db,'REGISTERED',{'request_hash':rid,'claim_id':request['claim_id'],
                'statement_hash':request['statement_hash'],'evidence_kind':request['evidence_kind'],
                'domain':request['domain'],'campaign_id':request['campaign_id'],
                'candidate_version':request['candidate_version'],'family':family_of(request),
                'family_size':family_size_of(request),'analysis':'v2' if _is_v2(request) else 'v1',
                'anchor_sha256':digest(anchor),
                'decision_record_sha256':digest(decision_record) if decision_record is not None else None})
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
            from .custody_records import family_of
            _append_log(db,'RESERVED',{'request_hash':request_id,'family':family_of(request),'tasks':len(tasks)})
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
        point('custodian.reserve')
        work=root/'evaluations'/request_id
        work.mkdir(parents=True,mode=0o700)
        limits=Limits.model_validate_json(canonical(request['limits']))
        with Store(work) as evidence:
            evidence.save('request',request_id,request)
            evidence.save('pool',digest(pool),pool)
            evidence.save('anchor',request_id,anchor)
            try:
                for task in tasks:
                    opt_aid=evidence.start('optimum-'+task.task_id,{'kind':'exact-check','task':task.model_dump(mode='json')})
                    start=time.monotonic_ns()
                    if _is_v2(request):
                        # W05: what the evaluator cannot certify is an explicit UNSUPPORTED row,
                        # handled by the preregistered policy; it is never dropped silently.
                        from .domains import Unsupported,adapter
                        optimum=adapter(task.domain).reference(task,evidence=evidence)
                        if isinstance(optimum,Unsupported):
                            evidence.finish(opt_aid,{'status':'UNSUPPORTED','reason':optimum.reason,
                                                     'wall_ns':time.monotonic_ns()-start})
                            evidence.save('unsupported_task',task.task_id,optimum.record())
                            continue
                    else:
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
                        evidence.finish(aid,receipt)
                        point('custodian.evaluate')
                        value=receipt.get('result',{}).get('value',0)
                        if value>optimum['value']:raise RuntimeError('exact checker disagreement')
                comparison=_comparison(evidence,tasks,programs)[0]
                evidence.save('comparison',request_id,comparison)
                evidence.verify();evidence.snapshot('complete.sqlite3')
            except BaseException as exc:
                evidence.event('EVALUATION_FAILED',{'exception':type(exc).__name__,'message':str(exc)})
                evidence.interrupt_running();raise
            receipt=_seal(evidence,request_id,request,anchor,commitment,identity,operator_id,key_path,tasks,programs,
                          complete=True,family_p_values=_family_p(db,request,request_id))
        return _publish(db,work,request_id,receipt,request)
    finally:db.close()


def _family_p(db,request,request_id):
    from .custody_records import family_of,published_p_values_before
    return published_p_values_before(_log_entries(db),family_of(request),request_id)


def _comparison(evidence,tasks,programs):
    """Per-arm rows rebuilt from the evidence journal (terminal solver attempts only).
    Returns (paired comparison over tasks where both arms finished, completed rows, failures)."""
    byarm={name:{} for name in programs};completed=0;failures=0
    for status,req,rec in evidence.db.execute('SELECT status,request,receipt FROM attempts ORDER BY rowid'):
        if rec is None or status in ('RUNNING','INTERRUPTED'):continue
        request=evidence.get(req)
        if request.get('kind')!='solver':continue
        receipt=evidence.get(rec);completed+=1;failures+=int(receipt['status']!='SUCCESS')
        byarm[request['arm']][request['task']['task_id']]=receipt.get('result',{}).get('value',0)
    rows=[{'task_id':t.task_id,'family':t.family,'candidate':byarm['candidate'][t.task_id],
           'baseline':byarm['baseline'][t.task_id]}
          for t in tasks if t.task_id in byarm['candidate'] and t.task_id in byarm['baseline']]
    return paired(rows),completed,failures


def _seal(evidence,request_id,request,anchor,commitment,identity,operator_id,key_path,tasks,programs,*,complete,
          family_p_values=()):
    comparison,completed,failures=_comparison(evidence,tasks,programs)
    v2=_is_v2(request)
    if v2:
        # W07: what every arm and the ground truth cost, recorded inside the signed evidence
        # root so the judge can recompute it (deterministic: a re-seal after recovery
        # computes the same account from the same terminal attempts).
        from .resources import account
        evidence.save('resource_account',request_id,account(evidence))
    integrity=evidence.verify()
    unsupported=evidence.db.execute("SELECT count(*) FROM entities WHERE kind='unsupported_task'").fetchone()[0]
    expected=(len(tasks)-unsupported)*len(programs) if v2 else len(tasks)*len(programs)
    payload={'schema':R.SCIENTIFIC_RECEIPT_V3 if v2 else R.SCIENTIFIC_RECEIPT,'evidence_kind':request['evidence_kind'],
             'claim_id':request['claim_id'],'statement_hash':request['statement_hash'],'scope':request['scope'],
             'campaign_id':request['campaign_id'],'request_hash':request_id,
             'anchor_hash':digest(anchor),'candidate_version':request['candidate_version'],
             'candidate_program_hash':R.program_identity(request['programs']['candidate']),
             'baseline_version':R.program_identity(request['programs']['baseline']),'source_hash':request['source_hash'],
             'evaluator_hash':identity,'analysis':request['analysis'],'domain':request['domain'],
             'domain_contract_hash':R.domain_contract_hash(request['domain']),
             'transfer_source_domain':request['transfer_source_domain'],
             'generation_transition':request['generation_transition'],'panel_commitment':commitment,
             'task_count':len(tasks),'raw_evidence_root':integrity['head'],
             'raw_evidence_complete':bool(complete and completed==expected),
             'expected_rows':expected,'completed_rows':completed,'execution_failures':failures,
             'wins':comparison['wins'],'losses':comparison['losses'],'ties':comparison['ties'],
             'paired_p':comparison['exploratory_sign_p'],'family_p':comparison['family_sensitivity_p'],
             'outcome':None,'operator_id':operator_id,'registered_at':anchor['payload']['registered_at'],
             'completed_at':utcnow(),'screen':'CUSTODIAN_BUILT_REGISTRY_ISOMORPHISM_AND_NEAR_DUPLICATE',
             'independence':'OPERATOR_ATTESTATION_REQUIRED'}
    if v2:
        from .kernel.analysis import analyze
        from .kernel.stats import sign_test
        from .judge import analysis_rows
        result=analyze(analysis_rows(evidence,tasks),request['analysis'],family_p_values=family_p_values)
        payload['analysis_result']=result
        if result['decision']!='INVALID':
            payload.update(wins=result['wins'],losses=result['losses'],ties=result['ties'],
                           paired_p=sign_test(result['wins'],result['losses']),family_p=result['p_value'],
                           execution_failures=result['failures']['candidate']+result['failures']['baseline'])
    payload['outcome']=R.derive_outcome(payload)
    problems=R.check_receipt(payload,request['evidence_kind'])
    if problems:raise RuntimeError('custodian built an invalid receipt: '+'; '.join(problems))
    receipt=sign(payload,key_path)
    point('custodian.sign')
    return receipt


def _publish(db,work,request_id,receipt,request,kind='PUBLISHED'):
    from .custody_records import family_of,published_p_values_before
    p=receipt['payload']
    db.execute('BEGIN IMMEDIATE')
    try:
        if p.get('schema')==R.SCIENTIFIC_RECEIPT_V3 and p['analysis_result'].get('decision')!='INVALID' and \
                p['analysis_result']['family_p_values']!=[round(float(x),10) for x in
                                                          published_p_values_before(_log_entries(db),family_of(request),request_id)]:
            raise RuntimeError('family results changed while this evaluation was sealed; run recover to re-seal')
        atomic_write(work/'public_receipt.json',canonical(receipt))
        point('custodian.publish')
        db.execute("UPDATE requests SET state='COMPLETE' WHERE id=?",(request_id,))
        _log_result(db,request,request_id,receipt,kind)
        db.execute('COMMIT')
    except BaseException:
        if db.in_transaction:db.execute('ROLLBACK')
        raise
    return receipt


def _log_result(db,request,request_id,receipt,kind):
    from .custody_records import family_of
    p=receipt['payload']
    pv=(p['analysis_result'].get('p_value') if p.get('schema')==R.SCIENTIFIC_RECEIPT_V3 else p.get('paired_p'))
    _append_log(db,kind,{'request_hash':request_id,'family':family_of(request),'receipt_sha256':digest(receipt),
                         'outcome':p['outcome'],'p_value':pv if p['outcome']!='INVALID' else None})


def recover(private_root,request_id,pool_path,key_path,operator_id):
    """Finish the record of an evaluation interrupted after its panel was reserved.

    The panel stays consumed (no automatic retry). The custodian still publishes
    a signed receipt, so an interrupted evaluation cannot silently disappear:
      * receipt already published -> mark COMPLETE and return it unchanged;
      * every row finished before the crash -> the complete receipt;
      * otherwise -> a receipt with raw_evidence_complete=false, whose derived
        outcome is INVALID (it licenses nothing).
    The operator supplies the same pool; it must match the registered commitment.
    """
    root=_private_root(private_root)
    db=_open_custody(root)
    try:
        row=db.execute('SELECT body,anchor,state FROM requests WHERE id=?',(request_id,)).fetchone()
        if not row:raise ValueError('request not preregistered')
        request=json.loads(row[0]);anchor=json.loads(row[1]);programs=validate_request(request)
        if row[2]=='REGISTERED':raise ValueError('evaluation never reserved a panel; nothing to recover')
        work=root/'evaluations'/request_id
        published=work/'public_receipt.json'
        if published.exists():
            receipt=json.loads(published.read_bytes())
            # Never re-sign, and never adopt a file this custodian's key did not sign for this request.
            from cryptography.hazmat.primitives import serialization as _ser
            pub=_ser.load_pem_private_key(Path(key_path).read_bytes(),password=None).public_key().public_bytes(
                _ser.Encoding.Raw,_ser.PublicFormat.Raw)
            import base64 as _b64
            try:payload=verify(receipt,_b64.b64encode(pub).decode())
            except Exception as exc:raise RuntimeError(f'published receipt does not verify under the custodian key ({type(exc).__name__})')
            if payload.get('request_hash')!=request_id or payload.get('anchor_hash')!=digest(anchor):
                raise RuntimeError('published receipt names another request')
            logged=any(e['kind'] in ('PUBLISHED','RECOVERED') and e['request_hash']==request_id
                       for e in _log_entries(db))
            db.execute('BEGIN IMMEDIATE')
            if row[2]!='COMPLETE':db.execute("UPDATE requests SET state='COMPLETE' WHERE id=?",(request_id,))
            if not logged:_log_result(db,request,request_id,receipt,'PUBLISHED')
            db.execute('COMMIT')
            return receipt
        if row[2]!='CONSUMED_NO_RETRY':raise RuntimeError(f'unexpected request state {row[2]}')
        identity=code_identity(Path(__file__).resolve().parents[2])['sha256']
        if identity!=request['expected_evaluator_hash']:raise ValueError('pinned evaluator source mismatch')
        pool,tasks=_load_pool(pool_path)
        pool_hash,commitment=db.execute('SELECT pool_hash,commitment FROM panels WHERE request_id=?',(request_id,)).fetchone()
        if digest(pool)!=pool_hash:raise ValueError('pool does not match the panel committed at registration')
        work.mkdir(parents=True,mode=0o700,exist_ok=True)
        from .store import rebuild_from_export
        try:evidence=Store(work)
        except RuntimeError:
            rebuild_from_export(work);evidence=Store(work)
        with evidence:
            for kind,key,value in (('request',request_id,request),('pool',digest(pool),pool),('anchor',request_id,anchor)):
                evidence.save(kind,key,value)   # idempotent; records them if the crash came first
            interrupted=evidence.interrupt_running()
            complete=evidence.db.execute("SELECT 1 FROM entities WHERE kind='comparison' AND id=?",
                                         (request_id,)).fetchone() is not None
            evidence.event('EVALUATION_RECOVERED',{'interrupted_attempts':interrupted,'comparison_recorded':complete})
            receipt=_seal(evidence,request_id,request,anchor,commitment,identity,operator_id,key_path,tasks,programs,
                          complete=complete,family_p_values=_family_p(db,request,request_id))
        return _publish(db,work,request_id,receipt,request,kind='RECOVERED')
    finally:db.close()


from .kernel.roles import TRUST_ROOT_ENV,DEFAULT_TRUST_ROOT,ROLE_FIELDS,load_role_registry  # re-exported


def release_preflight(request,anchor,receipt,audit,*,trust_root=None,revocations=(),registration_log=None,
                      control_declarations=None):
    """Check externally pinned roles. Never lets a builder-created key self-promote.

    Uses the same receipt semantics as the evidence kernel and phase machine
    (kernel.receipts): exact schemas, role-to-kind authorization, request and
    anchor binding, and the signed outcome re-derived from the signed counts.

    W06: `registration_log` is the custodian-signed public log; `control_declarations`
    maps custodian / auditor / release_authority to signed control declarations. Both are
    required for v3 (analysis-plan-v2) receipts. Shared control is disclosed and limits the
    result to LIMITED_SAME_OPERATOR; it never reaches EXTERNAL_RELEASE_REVIEW_READY.
    """
    family_info=None;indep=None
    registry,reasons=load_role_registry(trust_root)
    if registry is None:
        return {'status':'BLOCKED','reasons':reasons,'promotion_allowed':False}
    pins=registry['pins']
    try:
        validate_request(request)
        rid=digest(request);kind=request['evidence_kind']
        # `revocations`: the evidence store's revocation feed (REVOCATIONS.json records).
        revoked_keys=[x['artifact'] for x in revocations if x.get('target_type')=='key']
        revoked_evals={x['artifact'] for x in revocations if x.get('target_type')=='evaluation'}
        a,why=R.accept_receipt(anchor,'preregistration_anchor',pins,revoked_keys=revoked_keys)
        reasons+=why
        r,why=R.accept_receipt(receipt,kind,pins,revoked_keys=revoked_keys)  # role, schema, outcome, source
        reasons+=why
        for name,env in (('anchor',anchor),('receipt',receipt)):
            if R.evaluation_identity(R.unwrap_unverified(R.wrap(env))) in revoked_evals:
                reasons.append(f'the {name} is revoked in the supplied revocation feed')
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
        from .custody_records import check_log,independence,receipt_log_problems
        v3=receipt.get('payload',{}).get('schema')==R.SCIENTIFIC_RECEIPT_V3
        if registration_log is not None:
            log,why=check_log(registration_log,pins['custodian_key'],verify)
            reasons+=why
            if log is not None:
                why,state=receipt_log_problems(log['entries'],request,receipt)
                reasons+=why
                family_info={'family':state['family'],'registered':len(state['registered']),
                             'declared_sizes':state['declared_sizes'],'outstanding':state['outstanding']}
                if not v3 and len(state['registered'])>1:
                    reasons.append(f"ANALYSIS_V1 has no multiplicity correction and its family holds "
                                   f"{len(state['registered'])} registrations")
        elif v3:reasons.append('a v3 receipt needs the custodian-signed public registration log')
        if control_declarations is not None:
            indep=independence(control_declarations,pins,verify)
            if indep['status']=='UNDECLARED':reasons+=indep['reasons']
        elif v3:reasons.append('control declarations (custodian, auditor, release authority) are required')
    except Exception as exc:reasons.append('signature/schema verification failed: '+type(exc).__name__)
    status='BLOCKED' if reasons else ('LIMITED_SAME_OPERATOR' if indep and indep['status']=='SAME_OPERATOR_DISCLOSED'
                                      else 'EXTERNAL_RELEASE_REVIEW_READY')
    return {'status':status,'reasons':reasons,'registration_family':family_info,'independence':indep,
            'promotion_allowed':False,'next_authority':pins['release_authority_id'],
            'trust_root':registry['trust_root'],'root_key_sha256':registry['root_key_sha256'],
            'note':'External release authority must record its decision; local preflight never activates a release.'}
