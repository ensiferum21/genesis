"""One command line for the integrated offline runtime and reviewable exports."""
import argparse
import json
from pathlib import Path
import zipfile
from .common import canonical,digest,code_identity,load_json
from .models import Config,SolverProgram,GraphTask
from .campaign import Campaign
from .store import Store
from .formal import doctor,export_witness
from .dsl import baseline_programs


def request_bundle(campaign,task_count=300):
    campaign._check_frozen_environment()
    s=campaign.store;program=s.state('latest_program')
    if program is None or s.state('phase')!='CANDIDATE_FROZEN':raise ValueError('completed frozen candidate required')
    source=s.state('source_hash')
    version={'program':program,'source':source,'environment':__import__('genesis.campaign',fromlist=['environment']).environment(),
             'config':campaign.config.model_dump(mode='json'),'library':s.state('summary')['retained_dev_capabilities']}
    strongest_name=s.state('summary')['generations'][-1]['baseline']
    export=campaign.root/'exports/campaign_export.zip'
    if not export.exists():export_replication(campaign.root,export,store=s)
    from .common import bytes_hash
    request={'schema':'genesis-evaluation-request-v2','campaign_id':s.state('campaign_id'),
        'campaign_export_sha256':bytes_hash(export.read_bytes()),
        'candidate_version':digest(version),'source_hash':source,
        'programs':{'baseline':baseline_programs()[strongest_name].model_dump(mode='json'),'candidate':program,
                    'exchange':baseline_programs()['exchange'].model_dump(mode='json'),
                    'low_cycle':baseline_programs()['low_cycle'].model_dump(mode='json')},
        'limits':campaign.config.limits.model_dump(mode='json'),'seed':campaign.config.seed,
        'task_count':task_count,'domain':campaign.config.domain,
        'analysis':{'primary':'paired-edge-count','alpha':0.05,'family_sensitivity':True,'hypotheses':1},
        'exposed_graph_fingerprints':s.state('exposure_fingerprints'),
        'expected_evaluator_hash':source}
    from .custodian import validate_request
    validate_request(request)
    s.save('frozen_request',digest(request),request)
    if s.state('frozen_request_hash') not in (None,digest(request)):raise FileExistsError('a different request is already frozen')
    s.set_state('frozen_request_hash',digest(request))
    path=campaign.root/'exports/evaluation_request.json'
    if path.exists() and path.read_bytes()!=canonical(request):raise FileExistsError('request already exported with different scope')
    path.write_bytes(canonical(request));return path


def export_replication(root,destination,store=None):
    root=Path(root);destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    def snapshot(s):
        s.verify();s.snapshot('export-'+digest({'events':s.verify()['head']})[:16]+'.sqlite3');s.recover_export()
    if store is None:
        with Store(root) as s:snapshot(s)
    else:snapshot(store)
    manifest={}
    from .common import bytes_hash
    skip=('writer.lock','campaign.sqlite3','campaign.sqlite3-wal','campaign.sqlite3-shm','campaign.sqlite3-journal')
    files=[p for p in sorted(root.rglob('*')) if p.is_file() and p.name not in skip and p.resolve()!=destination.resolve()]
    for p in files:
        if p.is_symlink():raise ValueError('symlink in replication data')
        manifest[str(p.relative_to(root))]=bytes_hash(p.read_bytes())
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,str(p.relative_to(root)))
        z.writestr('MANIFEST.json',canonical({'files':manifest,'root':digest(manifest),'scope':'public offline campaign'}))
    return {'path':str(destination.resolve()),'files':len(files),'root':digest(manifest)}


def _rungs(text):
    out=[]
    for part in text.split(','):
        if '-' in part:
            a,b=part.split('-');out.extend(range(int(a),int(b)+1))
        elif part:out.append(int(part))
    return tuple(out)


def run_benchmark(args):
    from .ladder import default_preregistration,run_ladder
    candidate=None
    if args.candidate:
        with Store(args.candidate) as s:
            if s.state('phase')!='CANDIDATE_FROZEN':raise ValueError('candidate campaign is not frozen')
            candidate=SolverProgram.model_validate_json(canonical(s.state('latest_program')))
    prereg=default_preregistration(args.domain,_rungs(args.dev),_rungs(args.test),args.cpu_seconds,args.seed,candidate)
    results=run_ladder(args.root,prereg,progress=lambda r:print(json.dumps({k:r[k] for k in ('split','n','arm','best_value')}|
        {'status':r['classification']['status']}),flush=True))
    return {'report':str(Path(args.root)/'reports/ladder_report.md'),'status':results['status'],
            'per_arm_test_summary':results['per_arm_test_summary'],'promotion_allowed':False}


def main(argv=None):
    ap=argparse.ArgumentParser(prog='genesis');subs=ap.add_subparsers(dest='command',required=True)
    p=subs.add_parser('init');p.add_argument('root',type=Path);p.add_argument('--config',type=Path)
    subs.add_parser('doctor')
    p=subs.add_parser('smoke');p.add_argument('root',type=Path);p.add_argument('--seed',type=int,default=20261010)
    p=subs.add_parser('campaign');p.add_argument('action',choices=['run','status']);p.add_argument('root',type=Path)
    p=subs.add_parser('world');p.add_argument('action',choices=['list']);p.add_argument('root',type=Path)
    p=subs.add_parser('trial');p.add_argument('action',choices=['replay']);p.add_argument('root',type=Path);p.add_argument('--limit',type=int,default=10)
    p=subs.add_parser('artifact');p.add_argument('action',choices=['verify']);p.add_argument('root',type=Path);p.add_argument('hash')
    p=subs.add_parser('evidence');p.add_argument('action',choices=['show']);p.add_argument('root',type=Path)
    p=subs.add_parser('freeze');p.add_argument('action',choices=['candidate']);p.add_argument('root',type=Path);p.add_argument('--tasks',type=int,default=300)
    p=subs.add_parser('report');p.add_argument('action',choices=['build']);p.add_argument('root',type=Path)
    p=subs.add_parser('export');p.add_argument('action',choices=['replication-bundle']);p.add_argument('root',type=Path);p.add_argument('destination',type=Path)
    p=subs.add_parser('formal');p.add_argument('task',type=Path);p.add_argument('witness',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--check',action='store_true',help='kernel-check the obligation with the pinned Lean in the sandbox')
    p=subs.add_parser('research');p.add_argument('action',choices=['loop']);p.add_argument('root',type=Path)
    p.add_argument('--tasks',type=int,default=6);p.add_argument('--epochs',type=int,default=3)
    p.add_argument('--cpu-per-epoch',type=float,default=60.0);p.add_argument('--seed',type=int,default=20261013)
    p=subs.add_parser('experiment');p.add_argument('name',choices=['ghost-census']);p.add_argument('root',type=Path)
    p.add_argument('--problems',type=int,default=16);p.add_argument('--budget',type=float,default=12.0)
    p.add_argument('--seed',type=int,default=20261014)
    p=subs.add_parser('registry');p.add_argument('action',choices=['show','summary'])
    p=subs.add_parser('store');p.add_argument('action',choices=['verify','rebuild','index']);p.add_argument('root',type=Path)
    p.add_argument('--out',type=Path,help='index destination (store index)')
    p=subs.add_parser('benchmark');p.add_argument('action',choices=['ladder']);p.add_argument('root',type=Path)
    p.add_argument('--domain',choices=['c4_host_v2','triangle_free_host_v1'],default='c4_host_v2')
    p.add_argument('--dev',default='4-20',help='development rungs, e.g. 4-20');p.add_argument('--test',default='21-40')
    p.add_argument('--cpu-seconds',type=float,default=20.0);p.add_argument('--seed',type=int,default=20261010)
    p.add_argument('--candidate',type=Path,help='frozen campaign whose candidate program joins as an arm')
    args=ap.parse_args(argv)
    if args.command=='doctor':result=doctor()
    elif args.command=='benchmark':result=run_benchmark(args)
    elif args.command=='research':
        from .worldstep import ResearchLoop,LoopConfig
        cfg=LoopConfig(seed=args.seed,tasks=args.tasks,epochs=args.epochs,cpu_budget_per_epoch=args.cpu_per_epoch)
        with ResearchLoop(args.root,cfg) as loop:result=loop.run()
    elif args.command=='experiment':
        from .experiment_b import ExperimentBPrereg,run_experiment
        result=run_experiment(args.root,ExperimentBPrereg(seed=args.seed,problems=args.problems,
                                                          budget_seconds=args.budget))
        result={k:result[k] for k in ('counts','gate','contradictions','scope','promotion_allowed')}
    elif args.command=='registry':
        from .registry import registry,summary
        result=summary() if args.action=='summary' else registry()
    elif args.command=='store':
        if args.action=='rebuild':
            from .store import rebuild_from_export
            result=rebuild_from_export(args.root)
            with Store(args.root) as s:result['verify']=s.verify()
        elif args.action=='index':
            from .kernel.index import build_index
            with Store(args.root) as s:result=build_index(s,args.out or args.root/'reports'/'index.sqlite3')
        else:
            with Store(args.root) as s:result=s.verify()
    elif args.command=='init':
        cfg=Config.model_validate_json(args.config.read_bytes()) if args.config else Config()
        result={'root':str(Campaign.initialize(args.root,cfg).resolve())}
    elif args.command=='smoke':
        cfg=Config(seed=args.seed,generations=1,tasks_per_panel=3,proposals_per_epoch=2,research_trials=8)
        Campaign.initialize(args.root,cfg)
        with Campaign(args.root) as c:result=c.run()
    elif args.command=='formal':
        task=GraphTask.model_validate_json(args.task.read_bytes());witness=load_json(args.witness)
        result=export_witness(task,witness,args.destination)
        if args.check:
            from .verification.lean import check_witness_formally
            receipt=check_witness_formally(task,witness)
            (Path(args.destination)/'lean_receipt.json').write_bytes(canonical(receipt))
            result={'obligation':result,'lean_status':receipt['status'],'axioms':receipt.get('axioms'),
                    'scope':receipt.get('obligation',{}).get('scope')}
    elif args.command=='export':result=export_replication(args.root,args.destination)
    elif args.command in ('world','artifact','evidence'):
        with Store(args.root) as s:
            if args.command=='world':result=[s.get(h) for (h,) in s.db.execute("SELECT object_hash FROM entities WHERE kind='world'")]
            elif args.command=='artifact':result={'sha256':args.hash,'bytes':len(s.get_bytes(args.hash)),'valid':True}
            else:result={'integrity':s.verify(),'summary':s.state('summary'),'promotion_allowed':False}
    else:
        with Campaign(args.root) as c:
            if args.command=='campaign':result=c.run() if args.action=='run' else {'phase':c.store.state('phase'),'summary':c.store.state('summary')}
            elif args.command=='trial':result=c.replay(args.limit)
            elif args.command=='freeze':result={'request_path':str(request_bundle(c,args.tasks)),'promotion_allowed':False}
            elif args.command=='report':c.report();result={'report':str(c.root/'reports/report.md')}
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=='__main__':main()
