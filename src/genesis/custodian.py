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
# v4 (B20_R5, H05): the arms are candidate descriptors (genesis.candidates); each descriptor carries
# its resource profile, so the request has no separate DSL `limits`.
REQUEST_FIELDS_V4=(REQUEST_FIELDS-{'programs','limits'})|{'arms'}
# Statement evaluations (B20_R7, handoff s13.3): descriptor arms on a statement domain; the custodian
# generates the sealed panel itself from the preregistered `panel_spec` (no graph fingerprints).
REQUEST_FIELDS_STATEMENTS=(REQUEST_FIELDS_V4-{'exposed_graph_fingerprints'})|{'panel_spec'}
STATEMENT_KIND='formal-research-successor-v1'


def _hex64(h):
    return isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h)


def validate_request(request):
    """Schema v3 binds the request to the campaign's public export bundle and to
    one claim and evidence kind (roadmap R-01).

    v1/v2 requests are refused: v1 had no export binding; v2 named no claim, so
    its receipt could be presented as support for any claim.

    Schema v4 (B20_R5) names its arms as candidate descriptors; returns {arm: descriptor}
    for v4 and {arm: SolverProgram} for v3.
    """
    if isinstance(request,dict) and request.get('schema')==R.REQUEST_V4:return _validate_v4(request)
    if isinstance(request,dict) and request.get('schema')==R.REQUEST_STATEMENTS:return _validate_statements(request)
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
    _validate_common(request)
    return programs


def _validate_v4(request):
    """Executable-candidate request: every arm is a descriptor of a closed kind that this code
    rebuilds and accepts (implementation unchanged, parameters licensed, profile valid), all arms
    share one resource profile, and the analysis is a v2 plan."""
    from . import candidates as C
    if set(request)!=REQUEST_FIELDS_V4:raise ValueError('evaluation request schema')
    problems=R.check_request(request)
    if problems:raise ValueError('evaluation request binding: '+'; '.join(problems))
    for key in ('campaign_id','candidate_version','source_hash','expected_evaluator_hash','campaign_export_sha256'):
        if not _hex64(request[key]):raise ValueError('hash field')
    arms=request['arms']
    if not isinstance(arms,dict) or not {'baseline','candidate'}<=set(arms) or len(arms)>5:
        raise ValueError('comparison arms')
    if any(not isinstance(k,str) or not k.isidentifier() for k in arms):raise ValueError('arm name')
    for name,desc in arms.items():
        why=C.descriptor_problems(desc,domain=request['domain'])
        if why:raise ValueError(f'candidate descriptor for arm {name}: '+', '.join(why))
    if len({canonical(d['resource_profile']) for d in arms.values()})!=1:
        raise ValueError('arms must share one resource profile (equal resource accounting)')
    _validate_common(request)
    return dict(arms)


def _validate_statements(request):
    """Statement evaluation request: formal-research-successor descriptors on one statement domain,
    one shared resource profile and prover setting, a valid panel spec matching the task count."""
    from . import candidates as C
    from .learning import statement_panels as SP
    if set(request)!=REQUEST_FIELDS_STATEMENTS:raise ValueError('evaluation request schema')
    problems=R.check_request(request)
    if problems:raise ValueError('evaluation request binding: '+'; '.join(problems))
    for key in ('campaign_id','candidate_version','source_hash','expected_evaluator_hash','campaign_export_sha256'):
        if not _hex64(request[key]):raise ValueError('hash field')
    arms=request['arms']
    if not isinstance(arms,dict) or set(arms)!={'baseline','candidate'}:
        raise ValueError('comparison arms: a statement evaluation compares exactly candidate and baseline')
    for name,desc in arms.items():
        why=C.descriptor_problems(desc,domain=request['domain'])
        if why:raise ValueError(f'candidate descriptor for arm {name}: '+', '.join(why))
        if desc['kind']!=STATEMENT_KIND:raise ValueError(f'arm {name} is not a {STATEMENT_KIND} descriptor')
    if len({canonical(d['resource_profile']) for d in arms.values()})!=1 or \
            len({canonical({k:v for k,v in d['parameters'].items() if k!='manifest_id'}) for d in arms.values()})!=1:
        raise ValueError('arms must share one resource profile and prover setting (equal accounting)')
    why=SP.spec_problems(request['panel_spec'],domain=request['domain'],task_count=request['task_count'])
    if why:raise ValueError('panel spec: '+'; '.join(why))
    if type(request['seed']) is not int:raise ValueError('seed')
    if request['domain'] not in R.DOMAINS:raise ValueError('domain')
    if not R.analysis_ok(request['analysis']):raise ValueError('unsupported preregistered analysis')
    return dict(arms)


def _validate_common(request):
    if type(request['seed']) is not int or type(request['task_count']) is not int or not 1<=request['task_count']<=10000:
        raise ValueError('task count or seed')
    if request['domain'] not in R.DOMAINS:raise ValueError('domain')
    if not R.analysis_ok(request['analysis']):
        raise ValueError('unsupported preregistered analysis')
    if not isinstance(request['exposed_graph_fingerprints'],list):raise ValueError('exposure list')
    for h in request['exposed_graph_fingerprints']:
        if not _hex64(h):raise ValueError('exposure hash')


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
CREATE TABLE IF NOT EXISTS decision_records(request_id TEXT PRIMARY KEY, record BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS comparator_selections(id TEXT PRIMARY KEY, record BLOB NOT NULL);'''


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
                    if upd['key'] in ('campaign_id','source_hash','frozen_candidate_descriptor','frozen_baseline_descriptor',
                                      'comparator_selection'):
                        written.setdefault(upd['key'],set()).add(canonical(upd['value']))
            summary=s.state('summary') or {}
            from . import lineage as L
            facts={'campaign_id':s.state('campaign_id'),'source_hash':s.state('source_hash'),
                   'lineage':L.export_from_store(s),
                   'domain':configs[0][1].get('domain') if len(configs)==1 else None,
                   'config_entities':len(configs),
                   'identity_rewritten':any(len(v)>1 for k,v in written.items() if k in ('campaign_id','source_hash')),
                   'descriptor_rewritten':any(len(written.get(k,()))>1 for k in ('frozen_candidate_descriptor',
                                                                                 'frozen_baseline_descriptor',
                                                                                 'comparator_selection')),
                   'frozen_descriptor':s.state('frozen_candidate_descriptor'),
                   'frozen_baseline_descriptor':s.state('frozen_baseline_descriptor'),
                   'comparator_selection':s.state('comparator_selection'),
                   'successor_manifests':dict(entities('successor_manifest')),
                   'proof_objects':dict(entities('proof_object')),
                   'exposed_statements':[v for _,v in entities('exposed_statement')],
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
    if R.is_statement_request(request):return problems+statement_export_problems(request,facts)
    if R.descriptor_arms(request):return problems+descriptor_export_problems(request,facts)
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


def descriptor_export_problems(request,facts):
    """v4: the custodian rebuilds the arms from the campaign's frozen export (handoff s13.1),
    never from the request. The candidate arm must be the descriptor the campaign froze
    (write-once state ``frozen_candidate_descriptor``, recorded in a candidate_version document
    with the campaign source), still valid under the current reviewed implementation; the
    baseline arm must be the campaign's strongest conventional baseline as a DSL descriptor
    under the same resource profile; any further arm must be another conventional baseline."""
    from . import candidates as C
    from .dsl import baseline_programs
    out=[];arms=request['arms']
    if facts.get('descriptor_rewritten'):out.append('the frozen candidate descriptor was rewritten in the export history')
    frozen=facts.get('frozen_descriptor')
    if frozen is None:
        return out+['the campaign export holds no frozen candidate descriptor; a v4 request cannot be checked against it']
    why=C.descriptor_problems(frozen,domain=facts['domain'])
    if why:out.append('the frozen candidate descriptor is no longer valid: '+', '.join(why))
    if not isinstance(frozen,dict) or frozen.get('descriptor_id')!=arms['candidate'].get('descriptor_id'):
        out.append('NOT_THE_FROZEN_CANDIDATE: the candidate arm is not the descriptor the campaign froze')
    doc=facts['candidate_versions'].get(request['candidate_version'])
    if doc is None or digest(doc)!=request['candidate_version']:
        out.append('candidate_version is not a frozen version recorded in the campaign export')
    elif doc.get('descriptor')!=frozen or doc.get('source')!=request['source_hash']:
        out.append('candidate_version does not describe the frozen descriptor and source')
    if why or not isinstance(frozen,dict):return out
    rp=frozen['resource_profile'];domain=facts['domain']
    if request['evidence_kind'] in ('ablation','placebo'):
        # B20_R15 (B14-OPEN-4): a causal evaluation compares the frozen candidate with ONE copy of it
        # changed by the registered ablation or placebo of exactly one component; the kernel replays
        # the same provenance check from the arms the receipt commits to.
        from .kernel import replay_contracts as RC
        if set(arms)!={'candidate','baseline'}:
            return out+['an ablation or placebo compares the frozen candidate with one intervened copy only']
        why,_=RC.intervention_problems(request['evidence_kind'],frozen,arms['baseline'])
        return out+[f"the baseline is not a registered {request['evidence_kind']} of the frozen candidate: "+w for w in why]
    selection=facts.get('comparator_selection')
    if selection is not None:
        # B20_R12: the comparator is the one THIS custodian selected on its own private SELECT panel
        # (signed record, recorded in its database, then written into the campaign before export).
        known=facts.get('custodian_selections') or {}
        if digest(selection) not in known or known[digest(selection)]!=selection:
            return out+['the comparator selection in the export was not made by this custodian']
        sp=selection['payload']
        if (sp['campaign_id'],sp['source_hash'],sp['domain'])!=(facts['campaign_id'],facts['source_hash'],domain):
            out.append('the comparator selection is for another campaign, source or domain')
        if sp['resource_profile']!=rp:
            out.append("the comparator selection used another resource profile than the candidate's")
        chosen=sp['baselines'][sp['selected']]
        if arms['baseline'].get('descriptor_id')!=chosen['descriptor_id']:
            out.append('the baseline is not the comparator this custodian selected on its SELECT panel')
        allowed={d['descriptor_id'] for d in sp['baselines'].values()}
        for name in sorted(set(arms)-{'candidate','baseline'}):
            if arms[name].get('descriptor_id') not in allowed:
                out.append(f'arm {name} is not one of the selected-against conventional baselines')
        return out
    def dsl(program):
        return C.build_descriptor('dsl-program-v1',domain,{'program':program.model_dump(mode='json')},**rp)['descriptor_id']
    strongest=baseline_programs().get(facts['strongest_baseline'])
    if strongest is None or dsl(strongest)!=arms['baseline'].get('descriptor_id'):
        out.append("the baseline is not the campaign's strongest conventional baseline under the candidate's resource profile")
    conventional={dsl(p) for p in baseline_programs().values()}
    for name in sorted(set(arms)-{'candidate','baseline'}):
        if arms[name].get('descriptor_id') not in conventional:
            out.append(f'arm {name} is not a conventional baseline under the candidate resource profile')
    return out


def statement_export_problems(request,facts):
    """Statement evaluations: both arms are rebuilt from the frozen research export. The candidate
    must be the write-once frozen candidate descriptor and the baseline the write-once frozen
    baseline descriptor (fixed before any panel existed); each arm's successor manifest must be in
    the export, pass custody (proof objects present and unaltered, uids bound, lemmas true in the
    variety, premises earlier) and match the descriptor."""
    from . import candidates as C
    from .learning import custody as CU
    from .learning import research_export as RX
    out=[];arms=request['arms']
    if facts.get('descriptor_rewritten'):out.append('a frozen descriptor was rewritten in the export history')
    frozen={'candidate':facts.get('frozen_descriptor'),'baseline':facts.get('frozen_baseline_descriptor')}
    if None in frozen.values():
        return out+['the export holds no frozen candidate and baseline successors; a statement request cannot be checked']
    try:
        manifests,objects,_=RX.research_material(facts)
    except (ValueError,KeyError,TypeError) as exc:
        return out+[f'research material in the export is malformed ({type(exc).__name__})']
    for name in ('candidate','baseline'):
        desc=frozen[name]
        why=C.descriptor_problems(desc,domain=facts['domain'])
        if why:out.append(f'the frozen {name} descriptor is no longer valid: '+', '.join(why));continue
        if desc.get('kind')!=STATEMENT_KIND:out.append(f'the frozen {name} is not a {STATEMENT_KIND} descriptor');continue
        if desc['descriptor_id']!=arms[name].get('descriptor_id'):
            out.append(f'NOT_THE_FROZEN_{name.upper()}: the {name} arm is not the descriptor the research froze')
        m=manifests.get(desc['parameters']['manifest_id'])
        if m is None or m.get('manifest_id')!=desc['parameters']['manifest_id']:
            out.append(f'the {name} successor manifest is not in the export');continue
        codes=sorted({p['code'] for p in CU.successor_problems(m,objects)})
        if codes:out.append(f'the {name} successor fails custody: {", ".join(codes)}')
    doc=facts['candidate_versions'].get(request['candidate_version'])
    if doc is None or digest(doc)!=request['candidate_version']:
        out.append('candidate_version is not a frozen version recorded in the campaign export')
    elif doc.get('descriptor')!=frozen['candidate'] or doc.get('baseline_descriptor')!=frozen['baseline'] or \
            doc.get('source')!=request['source_hash']:
        out.append('candidate_version does not describe the frozen successors and source')
    return out


COMPARATOR_SCHEMA='genesis-comparator-selection-v1'


def _selections(root):
    db=_open_custody(root)
    try:return {i:json.loads(r) for i,r in db.execute('SELECT id,record FROM comparator_selections')}
    finally:db.close()


def select_comparator(private_root,campaign_export,baselines,key_path,operator_id,*,exposure_manifest,task_count=30,
                      study=None):
    """Choose the E1 comparator on a private SELECT panel (B20_R12; the DRAFT's rule "the strongest
    fixed baseline on the SELECT panel", drawn and held by the custodian).

    ``baselines``: {name: descriptor} of conventional kinds (fixed DSL programs, plain or
    time-matched), one shared resource profile, on the campaign's domain. The custodian draws
    ``task_count`` hosts from the adopted calibration with a private seed, screened against its
    exposure registry (manifest and the campaign export) and every reserved host, runs every
    baseline in the sandbox, reserves the hosts for good, and signs the selection. The research
    operator records the signed selection in the campaign before exporting; ``register`` then
    requires the request's baseline to be the selected one."""
    from . import candidates as C
    from . import calibration as CAL
    from .dsl import baseline_programs
    from .exposure import GraphIndex,build_registry
    root=_private_root(private_root)
    export=Path(campaign_export);facts=campaign_facts(export)
    domain=facts['domain']
    if not isinstance(baselines,dict) or len(baselines)<2:raise ValueError('at least two conventional baselines')
    programs={canonical(p.model_dump(mode='json')) for p in baseline_programs().values()}
    for name,d in baselines.items():
        why=C.descriptor_problems(d,domain=domain)
        if why or d['kind'] not in C.CONVENTIONAL_KINDS or canonical(d['parameters']['program']) not in programs:
            raise ValueError(f'baseline {name} is not a valid conventional baseline: {why}')
    if len({canonical(d['resource_profile']) for d in baselines.values()})!=1:
        raise ValueError('baselines must share one resource profile')
    from . import sandbox as S
    if not S.available():raise RuntimeError('ISOLATION_UNAVAILABLE: baselines run in the OCI sandbox')
    manifest_path,manifest=_manifest_file(exposure_manifest)
    repo=Path(__file__).resolve().parents[2]
    index,record=build_registry(manifest,manifest_path.parent,repo,
                                extra_sources=[{'kind':'zip','path':str(export.resolve()),'label':'campaign-export'}])
    db=_open_custody(root)
    try:
        reserved=GraphIndex()
        for n,edges,rid in db.execute('SELECT n,edges,request_id FROM reservations'):
            reserved.add(n,tuple(tuple(e) for e in json.loads(edges)),rid)
        seed=int.from_bytes(os.urandom(8),'big')
        calib=CAL.load(domain,repo,study=study)
        candidates_,_=CAL.calibrated_panel(calib,seed,task_count*3,'SELECT')
        tasks=[t for t in candidates_ if index.find(t.n,t.edges) is None and not index.near(t.n,t.edges)
               and reserved.find(t.n,t.edges) is None][:task_count]
        if len(tasks)<task_count:raise ValueError('INSUFFICIENT_DISTINCT_MATERIAL for the SELECT panel')
        runs={}
        for t in tasks:
            tseed=int(digest({'select':seed,'task':t.task_id})[:16],16)
            for name,d in sorted(baselines.items()):
                r=C.run(t,d,seed=tseed,expected_id=d['descriptor_id'],isolation='runc')
                runs[(t.task_id,name)]={'status':r['status'],'value':(r.get('result') or {}).get('value',0) if r['status']=='SUCCESS' else 0,
                                        'cpu_ns':r.get('cpu_ns')}
        totals={name:sum(runs[(t.task_id,name)]['value'] for t in tasks) for name in baselines}
        selected=max(totals,key=lambda n:(totals[n],n))
        salt=os.urandom(32).hex()
        commitment=digest({'schema':'genesis-panel-commitment-v1','pool':digest([t.model_dump(mode='json') for t in tasks]),
                           'salt':salt})
        payload={'schema':COMPARATOR_SCHEMA,'campaign_id':facts['campaign_id'],'source_hash':facts['source_hash'],
                 'domain':domain,'baselines':{k:baselines[k] for k in sorted(baselines)},'totals':totals,
                 'selected':selected,'resource_profile':next(iter(baselines.values()))['resource_profile'],
                 'task_count':len(tasks),'panel_commitment':commitment,'exposure_registry_root':record['root'],
                 'rule':'strongest total on the custodian SELECT panel (ties: greatest name)',
                 'calibration':{'study':study,'record_sha256':digest(calib),'rule':(calib.get('rule') or {}).get('name')},
                 'operator_id':operator_id,'selected_at':utcnow()}
        env=sign(payload,key_path)
        (root/'comparator_selections').mkdir(mode=0o700,exist_ok=True)
        atomic_write(root/'comparator_selections'/f'{digest(env)}.json',
                     canonical({'tasks':[t.model_dump(mode='json') for t in tasks],'salt':salt,'seed':seed,
                                'runs':[{'task':k[0],'arm':k[1],**v} for k,v in sorted(runs.items())]}),mode=0o600)
        with db:
            db.execute('BEGIN IMMEDIATE')
            db.executemany('INSERT INTO reservations(n,edges,request_id) VALUES (?,?,?)',
                           [(t.n,json.dumps([list(e) for e in t.edges]),'select:'+digest(env)) for t in tasks])
            db.execute('INSERT INTO comparator_selections VALUES (?,?)',(digest(env),canonical(env)))
        return env
    finally:db.close()


def _load_pool(pool_path):
    pool=load_json(pool_path)
    if not isinstance(pool,list) or not pool:raise ValueError('pool must be a non-empty task list')
    tasks=[GraphTask.model_validate_json(canonical(t)) for t in pool]
    return pool,tasks


def register(private_root,request,key_path,operator_id,*,exposure_manifest,campaign_export,pool,decision_record=None,
             accepted_selection_keys=()):
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
    if R.is_statement_request(request):
        raise ValueError('statement evaluation requests are registered with register_statements')
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
    facts=campaign_facts(export)
    facts['custodian_selections']=_selections(root)
    selection=facts.get('comparator_selection')
    if request['evidence_kind'] in R.REPLICATION_KINDS and selection is not None \
            and digest(selection) not in facts['custodian_selections']:
        # B20_R15/R21: an internal replicator or an external reproducer repeats an evaluation whose
        # comparator another custodian selected. It accepts that selection only under a public key its
        # operator names here (the registry's custodian key); the kernel checks that the repetition's
        # arms are the original's.
        for key in accepted_selection_keys:
            try:verify(selection,key)
            except Exception:continue
            facts['custodian_selections'][digest(selection)]=selection;break
    problems=check_request_against_export(request,facts)
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
        if R.is_statement_request(request):raise ValueError('statement evaluations run through evaluate_statements')
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
        v4=R.descriptor_arms(request)
        if v4:
            # Fail before the panel is reserved: without the sandbox the arms cannot run as declared.
            from . import sandbox as S
            if not S.available():
                raise RuntimeError('ISOLATION_UNAVAILABLE: executable-candidate arms need the OCI sandbox '
                                   '(root with runc, or a launcher socket); the panel was not reserved')
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
        limits=None if v4 else Limits.model_validate_json(canonical(request['limits']))
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
                        if v4:
                            from . import candidates as C
                            desc=programs[name]
                            aid=evidence.start(task.task_id+'-'+name,{'kind':'solver','task':task.model_dump(mode='json'),
                                'descriptor':desc,'arm':name,'seed':seed,'limits':desc['resource_profile']})
                            receipt=C.run(task,desc,seed=seed,expected_id=desc['descriptor_id'],isolation='runc')
                        else:
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
    if R.descriptor_arms(request):
        schema=R.SCIENTIFIC_RECEIPT_V4
        arm_fields={'candidate_descriptor_id':R.arm_identity(request,'candidate'),
                    'baseline_descriptor_id':R.arm_identity(request,'baseline'),
                    'arms_sha256':digest(request['arms']),'isolation':R.ISOLATION_V4}
    else:
        schema=R.SCIENTIFIC_RECEIPT_V3 if v2 else R.SCIENTIFIC_RECEIPT
        arm_fields={'candidate_program_hash':R.arm_identity(request,'candidate'),
                    'baseline_version':R.arm_identity(request,'baseline')}
    payload={'schema':schema,'evidence_kind':request['evidence_kind'],
             'claim_id':request['claim_id'],'statement_hash':request['statement_hash'],'scope':request['scope'],
             'campaign_id':request['campaign_id'],'request_hash':request_id,
             'anchor_hash':digest(anchor),'candidate_version':request['candidate_version'],
             **arm_fields,'source_hash':request['source_hash'],
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
        from .judge import analysis_rows,statement_rows
        rows=statement_rows(evidence,tasks) if R.is_statement_request(request) else analysis_rows(evidence,tasks)
        result=analyze(rows,request['analysis'],family_p_values=family_p_values)
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
        if p.get('schema') in R.ANALYSIS_RECEIPTS and p['analysis_result'].get('decision')!='INVALID' and \
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
    pv=(p['analysis_result'].get('p_value') if p.get('schema') in R.ANALYSIS_RECEIPTS else p.get('paired_p'))
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
        if R.is_statement_request(request):
            # The sealed panel never left the custodian: read it from the private root.
            _,pool,commitment=_statement_panel(root,db,request_id)
            tasks=statement_tasks(pool)
        else:
            pool,tasks=_load_pool(pool_path)
            pool_hash,commitment=db.execute('SELECT pool_hash,commitment FROM panels WHERE request_id=?',(request_id,)).fetchone()
            if digest(pool)!=pool_hash:raise ValueError('pool does not match the panel committed at registration')
        work.mkdir(parents=True,mode=0o700,exist_ok=True)
        from .store import rebuild_from_export
        try:evidence=Store(work)
        except RuntimeError:
            rebuild_from_export(work);evidence=Store(work)
        with evidence:
            for kind,key,value in (('request',request_id,request),
                                   ('statement_panel' if R.is_statement_request(request) else 'pool',digest(pool),pool),
                                   ('anchor',request_id,anchor)):
                evidence.save(kind,key,value)   # idempotent; records them if the crash came first
            interrupted=evidence.interrupt_running()
            complete=evidence.db.execute("SELECT 1 FROM entities WHERE kind='comparison' AND id=?",
                                         (request_id,)).fetchone() is not None
            evidence.event('EVALUATION_RECOVERED',{'interrupted_attempts':interrupted,'comparison_recorded':complete})
            receipt=_seal(evidence,request_id,request,anchor,commitment,identity,operator_id,key_path,tasks,programs,
                          complete=complete,family_p_values=_family_p(db,request,request_id))
        return _publish(db,work,request_id,receipt,request,kind='RECOVERED')
    finally:db.close()


# ---------------------------------------------------------------- sealed statement evaluations (B20_R7)

STATEMENT_SCHEMA='CREATE TABLE IF NOT EXISTS statement_reservations(structural TEXT PRIMARY KEY, request_id TEXT NOT NULL);'


def _manifest_file(path):
    path=Path(path);st=path.stat()
    if path.is_symlink() or st.st_uid!=os.geteuid() or st.st_mode&0o022:
        raise ValueError('exposure manifest must be a custodian-owned, non-writable-by-others file')
    return path,load_json(path)


def _statement_exposure(root,manifest_path,manifest,facts):
    """Everything a statement panel must avoid: what the requesting research saw (export), the
    custodian's public statement sources (manifest ``statement_sources``: JSON lists of statement
    texts, paths relative to the manifest, no '..'), and every statement already sealed in a
    registered panel at this custodian (route 'sealed')."""
    from .learning import research_export as RX
    from .learning import statement_panels as SP
    _,_,research=RX.research_material(facts)
    items=[(system,SP.eq_of(text),route) for system,text,route in research]
    for src in manifest.get('statement_sources',[]):
        rel=Path(src['path'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('statement source paths must stay inside the manifest directory')
        for text in load_json(manifest_path.parent/rel):
            items.append((src['system'],SP.eq_of(text),'import'))
    panels=root/'statement_panels'
    if panels.is_dir():
        for f in sorted(panels.glob('*.json')):
            doc=load_json(f)
            items+=[(doc['panel']['system'],SP.eq_of(x['statement']),'sealed') for x in doc['panel']['statements']]
    return items


def _screen_salt(root):
    """A per-custodian secret salt for the statement screen's public commitment (created once)."""
    path=root/'statement_screen_salt'
    if not path.exists():
        atomic_write(path,os.urandom(32).hex().encode(),mode=0o600)
    return bytes.fromhex(path.read_text())


def screen_statements_for_research(private_root,items,key_path,operator_id,*,query_budget=10000):
    """Narrow, signed ALLOW/BLOCK screen of statements research wants to insert (B20R7-OPEN-2).

    ``items``: [{'route', 'system', 'statement'}]. The reserved set is every statement sealed in a
    registered panel at this custodian; relations follow the partition policy (EXACT, ALPHA,
    INSTANCE: blocked; GENERALIZES: quarantined, hence blocked). The signed receipt carries one
    decision per item, the digest of the items and a salted commitment to the reserved set, never
    a reserved statement; relations and matches stay in the private ledger."""
    from .learning import partitions as P
    from .learning import statement_panels as SP
    root=_private_root(private_root)
    if not isinstance(items,list) or any(not isinstance(x,dict) or set(x)!={'route','system','statement'} for x in items):
        raise ValueError('items must be [{route, system, statement}]')
    reserved=[]
    panels=root/'statement_panels'
    if panels.is_dir():
        for f in sorted(panels.glob('*.json')):
            doc=load_json(f)
            reserved+=[(doc['panel']['system'],SP.eq_of(x['statement'])) for x in doc['panel']['statements']]
    screen=P.InsertionScreen(reserved,salt=_screen_salt(root),query_budget=query_budget)
    decisions=[]
    for x in items:
        try:item=SP.eq_of(x['statement'])
        except Exception:item=None
        decisions.append(screen(x['route'],x['system'],item)['decision'] if item is not None else 'BLOCK')
    with open(root/'statement_screening_ledger.jsonl','ab') as f:
        for entry in screen.private_ledger():f.write(canonical(entry)+b'\n')
    return sign({'schema':'genesis-statement-screening-receipt-v1','decisions':decisions,'items_sha256':digest(items),
                 'reserved_commitment':screen.commitment(),'operator_id':operator_id,'issued_at':utcnow()},key_path)


def statement_tasks(panel):
    """Evaluator-side task objects for a statement panel (task id and stratum)."""
    from types import SimpleNamespace
    return [SimpleNamespace(task_id=x['task_id'],family=x['stratum'],statement=x['statement'])
            for x in panel['statements']]


def _statement_panel(root,db,request_id):
    """(private document, panel, commitment) for a registered statement request; the panel must
    hash to the commitment made at registration and pass the structural check."""
    from .learning import statement_panels as SP
    committed=db.execute('SELECT pool_hash,commitment FROM panels WHERE request_id=?',(request_id,)).fetchone()
    path=root/'statement_panels'/f'{request_id}.json'
    if committed is None or not path.is_file():raise ValueError('no sealed statement panel registered for this request')
    doc=load_json(path);panel=doc['panel']
    if digest(panel)!=committed[0]:raise ValueError('statement panel does not match the commitment made at registration')
    problems=SP.panel_problems(panel)
    if problems:raise ValueError('statement panel: '+'; '.join(problems))
    return doc,panel,committed[1]


def register_statements(private_root,request,key_path,operator_id,*,exposure_manifest,campaign_export,decision_record):
    """Register a statement evaluation and generate its sealed panel here, after the research froze.

    The panel is drawn from a fresh private seed under the preregistered spec, screened against
    everything the requesting research saw (rebuilt from the bound export), the custodian's public
    statement sources and every statement already sealed at this custodian; it stays in the
    private root, and the anchor carries a salted commitment to it. INSUFFICIENT material refuses
    the registration (nothing is recorded)."""
    from . import decision_record as DR
    from .learning import statement_panels as SP
    root=_private_root(private_root)
    if not R.is_statement_request(request):raise ValueError('register_statements takes a statement evaluation request')
    validate_request(request);rid=digest(request)
    problems=DR.problems(decision_record,request['analysis'],task_count=request['task_count'],require_frozen=True)
    if problems:raise ValueError('decision record: '+'; '.join(problems))
    export=Path(campaign_export);data=export.read_bytes()
    if bytes_hash(data)!=request['campaign_export_sha256']:raise ValueError('campaign export does not match the request binding')
    facts=campaign_facts(export)
    problems=check_request_against_export(request,facts)
    if problems:raise ValueError('request is not what the campaign export shows: '+'; '.join(problems))
    manifest_path,manifest=_manifest_file(exposure_manifest)
    db=_open_custody(root);db.executescript(STATEMENT_SCHEMA)
    try:
        slots=R.registration_slots(request)
        for one in slots:
            taken=db.execute('SELECT request_id FROM slots WHERE slot=?',(one,)).fetchone()
            if taken:raise ValueError(f'this claim or candidate slot is already registered by request {taken[0][:12]}')
        exposure=_statement_exposure(root,manifest_path,manifest,facts)
        seed=os.urandom(32).hex()
        try:panel,record=SP.generate(request['panel_spec'],private_seed=seed,exposure=exposure)
        except SP.PanelError as exc:raise ValueError(f'statement panel: {exc.code}') from None
        salt=os.urandom(32).hex();pool_hash=digest(panel)
        commitment=digest({'schema':'genesis-panel-commitment-v1','pool':pool_hash,'salt':salt})
        payload={'schema':R.PREREG_ANCHOR,'request_hash':rid,'claim_id':request['claim_id'],
                 'statement_hash':request['statement_hash'],'scope':request['scope'],
                 'evidence_kind':request['evidence_kind'],'registration_slot':R.registration_slot(request),
                 'registered_at':utcnow(),'operator_id':operator_id,'exposure_registry_root':record['exposure_root'],
                 'exposure_graphs':0,'declaration_unscreenable_graphs':0,'panel_commitment':commitment}
        problems=R.check_anchor(payload)
        if problems:raise RuntimeError('custodian built an invalid anchor: '+'; '.join(problems))
        anchor=sign(payload,key_path)
        # Private files first: a crash before the commit below leaves an orphan file, never a registration
        # without its panel.
        for d in ('statement_panels','statement_exports','sealed_statements'):(root/d).mkdir(mode=0o700,exist_ok=True)
        atomic_write(root/'statement_panels'/f'{rid}.json',canonical({'panel':panel,'record':record,'private_seed':seed}),
                     mode=0o600,overwrite=True)
        atomic_write(root/'statement_exports'/f'{rid}.zip',data,mode=0o600,overwrite=True)
        atomic_write(root/'sealed_statements'/f'{rid}.json',canonical([x['statement'] for x in panel['statements']]),
                     mode=0o600,overwrite=True)
        from .custody_records import family_of,family_size_of,registration_problems
        with db:
            db.execute('BEGIN IMMEDIATE')
            problems=registration_problems(_log_entries(db),request)
            if problems:raise ValueError('hypothesis family: '+'; '.join(problems))
            for one in slots:
                taken=db.execute('SELECT request_id FROM slots WHERE slot=?',(one,)).fetchone()
                if taken:raise ValueError(f'this claim or candidate slot is already registered by request {taken[0][:12]}')
            db.executemany('INSERT INTO slots VALUES (?,?)',[(one,rid) for one in slots])
            db.execute('INSERT INTO requests VALUES (?,?,?,?)',(rid,canonical(request),canonical(anchor),'REGISTERED'))
            db.execute('INSERT INTO registry_builds VALUES (?,?)',(rid,canonical(record)))
            db.execute('INSERT INTO panels VALUES (?,?,?,?)',(rid,pool_hash,salt,commitment))
            db.execute('INSERT INTO decision_records VALUES (?,?)',(rid,canonical(decision_record)))
            _append_log(db,'REGISTERED',{'request_hash':rid,'claim_id':request['claim_id'],
                'statement_hash':request['statement_hash'],'evidence_kind':request['evidence_kind'],
                'domain':request['domain'],'campaign_id':request['campaign_id'],
                'candidate_version':request['candidate_version'],'family':family_of(request),
                'family_size':family_size_of(request),'analysis':'v2','anchor_sha256':digest(anchor),
                'decision_record_sha256':digest(decision_record)})
        return anchor
    finally:db.close()


def evaluate_statements(private_root,request_id,key_path,operator_id):
    """Run a registered statement evaluation: reserve the sealed statements (never reused), run each
    arm's frozen successor in the sandbox on every statement (shuffled arm order), and replay every
    claimed proof in Lean from custody (verification attempts, accounted separately). A statement
    scores 1 for an arm only when its replay is CHECKED."""
    from .learning import research_export as RX
    root=_private_root(private_root)
    db=_open_custody(root);db.executescript(STATEMENT_SCHEMA)
    try:
        row=db.execute('SELECT body,anchor,state FROM requests WHERE id=?',(request_id,)).fetchone()
        if not row:raise ValueError('request not preregistered')
        request=json.loads(row[0]);anchor=json.loads(row[1])
        if not R.is_statement_request(request):raise ValueError('not a statement evaluation request')
        arms=validate_request(request)
        if row[2]!='REGISTERED':raise FileExistsError('evaluation already consumed; no automatic retry')
        identity=code_identity(Path(__file__).resolve().parents[2])['sha256']
        if identity!=request['expected_evaluator_hash']:raise ValueError('pinned evaluator source mismatch')
        doc,panel,commitment=_statement_panel(root,db,request_id)
        export=root/'statement_exports'/f'{request_id}.zip'
        if bytes_hash(export.read_bytes())!=request['campaign_export_sha256']:raise ValueError('stored export differs from the binding')
        facts=campaign_facts(export)
        problems=check_request_against_export(request,facts)
        if problems:raise ValueError('request is not what the campaign export shows: '+'; '.join(problems))
        manifests,objects,_=RX.research_material(facts)
        from . import sandbox as S
        if not S.available():
            raise RuntimeError('ISOLATION_UNAVAILABLE: successor arms need the OCI sandbox; the panel was not reserved')
        db.execute('BEGIN IMMEDIATE')
        try:
            if db.execute('SELECT state FROM requests WHERE id=?',(request_id,)).fetchone()[0]!='REGISTERED':
                raise FileExistsError('concurrent evaluation reservation')
            for x in panel['statements']:
                if db.execute('SELECT 1 FROM statement_reservations WHERE structural=?',(x['structural_sha256'],)).fetchone():
                    raise ValueError('panel statement was already consumed by an earlier evaluation')
                db.execute('INSERT INTO statement_reservations VALUES (?,?)',(x['structural_sha256'],request_id))
            db.execute("UPDATE requests SET state='CONSUMED_NO_RETRY' WHERE id=?",(request_id,))
            from .custody_records import family_of
            _append_log(db,'RESERVED',{'request_hash':request_id,'family':family_of(request),'tasks':len(panel['statements'])})
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
        point('custodian.reserve')
        work=root/'evaluations'/request_id
        work.mkdir(parents=True,mode=0o700)
        tasks=statement_tasks(panel)
        with Store(work) as evidence:
            evidence.save('request',request_id,request)
            evidence.save('statement_panel',digest(panel),panel)
            evidence.save('panel_record',request_id,doc['record'])
            evidence.save('anchor',request_id,anchor)
            for desc in arms.values():
                m=manifests[desc['parameters']['manifest_id']]
                evidence.save('successor_manifest',m['manifest_id'],m)
                for lem in m['lemmas']:
                    evidence.save('proof_object',lem['proof_sha256'],
                                  {'sha256':lem['proof_sha256'],'text':objects.get(lem['proof_sha256']).decode()})
            try:
                _statement_rows_run(evidence,request,panel,arms,manifests,objects)
                evidence.save('comparison',request_id,{'statements':len(tasks),'arms':sorted(arms)})
                evidence.verify();evidence.snapshot('complete.sqlite3')
            except BaseException as exc:
                evidence.event('EVALUATION_FAILED',{'exception':type(exc).__name__,'message':str(exc)})
                evidence.interrupt_running();raise
            receipt=_seal(evidence,request_id,request,anchor,commitment,identity,operator_id,key_path,tasks,arms,
                          complete=True,family_p_values=_family_p(db,request,request_id))
        return _publish(db,work,request_id,receipt,request)
    finally:db.close()


def _statement_rows_run(evidence,request,panel,arms,manifests,objects):
    from . import candidates as C
    from .learning import custody as CU
    checker={'checker_identity':CU.checker_identity()['identity']}
    for x in panel['statements']:
        task={'task_id':x['task_id'],'statement':x['statement'],'domain':request['domain']}
        names=sorted(arms);seed=int(digest({'seed':request['seed'],'task':x['task_id']})[:16],16)
        random.Random(seed).shuffle(names)
        for name in names:
            desc=arms[name];m=manifests[desc['parameters']['manifest_id']]
            aid=evidence.start(f"{x['task_id']}-{name}",{'kind':'solver','task':task,'descriptor':desc,'arm':name,
                                                          'seed':seed,'limits':desc['resource_profile']})
            receipt=C.run(task,desc,seed=seed,expected_id=desc['descriptor_id'],isolation='runc',context={'manifest':m})
            evidence.finish(aid,receipt)
            point('custodian.evaluate')
            res=receipt.get('result') or {}
            if receipt.get('status')!='SUCCESS' or res.get('claim')!='PROOF':continue
            local=CU.MemoryObjects({l['proof_sha256']:objects.get(l['proof_sha256']) for l in m['lemmas']})
            record=CU.claim_record(m,local,panel_id=panel['panel_sha256'],task_id=x['task_id'],statement=x['statement'],
                                   prover_status=res['prover_status'],proof=res['proof'],premise_uids=res['premise_uids'],
                                   eligible=True,attempt_id=aid)
            vid=evidence.start(f"replay-{x['task_id']}-{name}",{'kind':'replay','task_id':x['task_id'],'arm':name,
                                                                 'solver_attempt':aid,'record':record})
            start=time.monotonic_ns()
            check=CU.replay_target(record,m,local,task_statement=x['statement'],trust_context=checker,
                                   name=f"st{record['record_id'][:12]}")
            ran=check['status'] in ('CHECKED','CHECK_FAILED','CHECK_UNSUPPORTED','CHECK_INCOMPLETE')
            evidence.finish(vid,{'status':'SUCCESS' if ran else 'CHECKER_ERROR','replay':check,
                                 'wall_ns':time.monotonic_ns()-start,'cpu_ns':check.get('cpu_ns')})


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
            expected_rows=request['task_count']*len(R.arm_names(request))
            arm_fields=((('candidate_descriptor_id',R.arm_identity(request,'candidate')),
                         ('baseline_descriptor_id',R.arm_identity(request,'baseline')),
                         ('arms_sha256',digest(request['arms']))) if R.descriptor_arms(request) else
                        (('candidate_program_hash',R.arm_identity(request,'candidate')),
                         ('baseline_version',R.arm_identity(request,'baseline'))))
            if a['registration_slot']!=R.registration_slot(request):reasons.append('anchor registers a different slot')
            for field,want in (('claim_id',request['claim_id']),('campaign_id',request['campaign_id']),
                               ('statement_hash',request['statement_hash']),('scope',request['scope']),
                               *arm_fields,
                               ('candidate_version',request['candidate_version']),
                               ('evaluator_hash',request['expected_evaluator_hash']),
                               ('source_hash',request['source_hash']),('domain',request['domain']),
                               ('task_count',request['task_count']),('expected_rows',expected_rows),
                               ('generation_transition',request['generation_transition']),
                               ('transfer_source_domain',request['transfer_source_domain'])):
                if r.get(field)!=want:reasons.append(f'receipt {field} differs from the preregistered request')
            if r['outcome']=='INVALID':reasons.append('incomplete or inconsistent evidence (outcome INVALID)')
            elif r['outcome']=='INCONCLUSIVE':reasons.append('execution failures require adjudication (outcome INCONCLUSIVE)')
            elif r['outcome']!='SUPPORTED':reasons.append('preregistered superiority not supported (outcome NOT_SUPPORTED)')
        if review.get('request_hash')!=rid or review.get('receipt_hash')!=digest(receipt):reasons.append('audit scope mismatch')
        if review.get('status')!='PASS' or review.get('open_critical')!=0:reasons.append('independent audit not passing')
        if review.get('independent_operation_verified') is not True:reasons.append('custody independence not verified')
        if review.get('raw_replay_verified') is not True:reasons.append('private evidence replay not verified')
        if review.get('formal_replay_verified') is not True:reasons.append('formal replay not verified')
        from .custody_records import check_log,independence,receipt_log_problems
        v3=receipt.get('payload',{}).get('schema') in R.ANALYSIS_RECEIPTS
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
