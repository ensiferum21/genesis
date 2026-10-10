"""End-to-end offline research, causal controls, transfer and successor experiments.

All generated panels are public engineering material. Running this protocol does
not provide independent custody or permission to promote a scientific claim.
"""
from dataclasses import asdict
import importlib.metadata
import json
import platform
from pathlib import Path
import time
from .common import canonical,code_identity,digest,utcnow
from .models import Config,GraphTask,SolverProgram,Evidence,Capability,Modification
from .store import Store
from .graphs import certified_optimum,check_witness,canonical_graph,SearchLimit
from .dsl import baseline_programs
from .execution import execute
from .research import make_panel,propose,diagnose,Ecology,compile_trace
from .evaluation import paired,causal_controls,transition,evidence_wording


def _file_hash(path):
    from .common import bytes_hash
    path=Path(path)
    return bytes_hash(path.read_bytes()) if path.exists() else None


def version_components(config):
    """Values for SystemVersion fields that do not change within a campaign."""
    from .ir import CONTRACTS
    from .mrdl import __file__ as mrdl_file
    repo=Path(__file__).resolve().parents[2]
    pins=repo/'toolchain'/'PINS.json'
    return {
        'cognitive_kernel':digest({'contracts':{k:[list(v[0]),v[1]] for k,v in CONTRACTS.items()},
                                   'mrdl':_file_hash(mrdl_file)}),
        'verifier_set':{'graph-dual-predicates':_file_hash(Path(__file__).with_name('graphs.py')),
                        'exact-solvers':_file_hash(Path(__file__).with_name('graphs.py')),
                        'toolchain-pins':_file_hash(pins) or 'absent'},
        'dependency_lock':_file_hash(repo/'requirements.lock') or 'absent',
        'environment_digest':digest(environment()),
        'curriculum_policy':{'panel_generator':'research.make_panel','tasks_per_panel':config.tasks_per_panel,
                             'max_exact_edges':config.max_exact_edges},
        'model_configuration':None,
        'resolved_config':config.model_dump(mode='json'),
    }


def environment():
    packages={}
    for name in ('pydantic','numpy','scipy','scikit-learn','cryptography'):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    return {'python':platform.python_version(),'implementation':platform.python_implementation(),
            'platform':platform.platform(),'packages':packages,'hosted_model':None}


class Campaign:
    def __init__(self,root):
        self.store=Store(root);self.root=self.store.root
        self.config=Config.model_validate_json((self.root/'resolved_config.json').read_bytes())
        rows=self.store.db.execute("SELECT object_hash FROM entities WHERE kind='config'").fetchall()
        if len(rows)!=1 or self.store.get(rows[0][0])!=self.config.model_dump(mode='json'):
            # The editable file must never diverge from the recorded configuration (B14 round 3, F2).
            self.store.close()
            raise RuntimeError('resolved_config.json differs from the configuration recorded at initialization')
        self.optima={}

    def close(self):self.store.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

    @classmethod
    def initialize(cls,root,config):
        root=Path(root)
        if root.exists() and any(root.iterdir()):raise FileExistsError('campaign destination must be empty')
        root.mkdir(parents=True,exist_ok=True)
        (root/'resolved_config.json').write_bytes(canonical(config.model_dump(mode='json')))
        with Store(root) as s:
            s.set_state('campaign_id',digest({'config':config.model_dump(mode='json'),'created':utcnow()}))
            s.set_state('phase','CREATED')
            s.save('config','resolved',config.model_dump(mode='json'))
            s.save('environment','initial',environment())
            identity=code_identity(Path(__file__).resolve().parents[2])
            s.save('source','initial',identity);s.set_state('source_hash',identity['sha256'])
            transition(s,'VALIDATED_CONFIG')
        return root

    def _check_frozen_environment(self):
        identity=code_identity(Path(__file__).resolve().parents[2])
        if identity['sha256']!=self.store.state('source_hash'):
            raise RuntimeError('source changed after campaign initialization; create a new campaign')
        row=self.store.db.execute("SELECT object_hash FROM entities WHERE kind='environment' AND id='initial'").fetchone()
        if self.store.get(row[0])!=environment():raise RuntimeError('environment drift; new campaign required')

    def _panel(self,seed,split,seen,domain=None):
        tasks,seen=make_panel(seed,self.config.tasks_per_panel,domain or self.config.domain,split,
                              seen,self.config.max_exact_edges)
        for task in tasks:self.store.save('task',task.task_id,task.model_dump(mode='json'))
        return tasks,seen

    def _optimum(self,task):
        key=digest({'domain':task.domain,'n':task.n,'edges':task.edges})
        if key not in self.optima:
            aid=self.store.start('check-'+key,{'kind':'exact-check','task':task.model_dump(mode='json')})
            start=time.perf_counter_ns()
            try:
                result=certified_optimum(task,self.config.max_exact_edges)
                receipt={'status':'SUCCESS','result':result,'wall_ns':time.perf_counter_ns()-start,
                         'cost_category':'evaluation-checking','not_charged_to_solver_arm':True}
                self.optima[key]=result['value']
            except SearchLimit as e:
                receipt={'status':'UNSETTLED','reason':str(e),'wall_ns':time.perf_counter_ns()-start,
                         'cost_category':'evaluation-checking'}
                self.optima[key]=None
            except BaseException as e:
                self.store.finish(aid,{'status':'CHECKER_ERROR','reason':type(e).__name__,
                                      'wall_ns':time.perf_counter_ns()-start})
                raise
            self.store.finish(aid,receipt)
        return self.optima[key]

    def trial(self,task,program,context,seed):
        request={'kind':'solver','task':task.model_dump(mode='json'),
                 'program':program.model_dump(mode='json'),'limits':self.config.limits.model_dump(mode='json'),
                 'seed':seed,'context':context}
        trial_id=digest(request)
        aid=self.store.start(trial_id,request)
        try:receipt=execute(task,program,self.config.limits,seed)
        except BaseException as e:
            self.store.finish(aid,{'status':'HARNESS_ERROR','reason':type(e).__name__,'cost_unknown':True})
            raise
        rh=self.store.finish(aid,receipt)
        optimum=self._optimum(task)
        result=receipt.get('result',{})
        row={'task_id':task.task_id,'family':task.family,'status':receipt['status'],
             'value':result.get('value',0),'queries':result.get('queries'),
             'wall_ns':receipt['wall_ns'],'cpu_ns':receipt['cpu_ns'],
             'optimum':optimum,'receipt':rh,'trace':result.get('trace',[])}
        if optimum is not None and row['value']>optimum:raise RuntimeError('checker disagreement')
        return row

    def evaluate(self,tasks,program,context,seed):
        return [self.trial(t,program,context,int(digest({'seed':seed,'task':t.task_id})[:16],16)) for t in tasks]

    def improve(self,tasks,parent,policy,generation,seed):
        # Both policies have identical proposal count, panel, execution limits and
        # outer trial budget. Failed candidates remain charged and visible.
        candidates=propose(parent,self.config.proposals_per_epoch,seed,policy,
                           self.store.state('diagnosis',{'gap_cases':1}),
                           self.store.state('mutation_weights',[1,1,1,1]))
        per_candidate=min(len(tasks),self.config.research_trials//len(candidates))
        if per_candidate<1:raise ValueError('outer budget too small')
        visible=tasks[:per_candidate];scores=[];all_rows=[]
        ecology=Ecology(self.config.max_active_worlds,scope=f'g{generation}:{policy}:{seed}')
        for i,candidate in enumerate(candidates):
            if i%4==0:ecology.next_epoch()
            wid=ecology.birth(candidate)
            ecology.action(wid)
            rows=self.evaluate(visible,candidate,f'g{generation}:{policy}:proposal-{i}',seed)
            all_rows.extend(rows)
            score=sum(r['value'] for r in rows)
            failures=sum(r['status']!='SUCCESS' for r in rows)
            # Deterministic selection: score, fewer failures, shorter description.
            scores.append((score,-failures,-len(canonical(candidate.model_dump(mode='json')))))
            ecology.observe(wid,(score,-failures,-sum(r['wall_ns'] for r in rows)),diagnose(rows))
            self.store.save('world',wid,{**asdict(ecology.worlds[wid]),'program':candidate.model_dump(mode='json')})
        winner=max(range(len(candidates)),key=lambda i:scores[i])
        summary={'policy':policy,'generation':generation,'seed':seed,'trials':len(all_rows),
                 'outer_trial_cap':self.config.research_trials,'scores':scores,'winner':winner,
                 'frontier':ecology.frontier(),'all_candidate_ids':[digest(x.model_dump(mode='json')) for x in candidates],
                 'mutation_weights':self.store.state('mutation_weights',[1,1,1,1]),
                 'candidate_programs':[x.model_dump(mode='json') for x in candidates],
                 'effects':['USES_DEV_DATA'],'all_costs_retained':True}
        self.store.save('research',f'g{generation}-{policy}',summary)
        return candidates[winner],summary,all_rows

    def run(self):
        self._check_frozen_environment()
        phase=self.store.state('phase')
        if phase=='CANDIDATE_FROZEN':return self.store.state('summary')
        if phase=='DEV_RUNNING':
            interrupted=self.store.interrupt_running()
            transition(self.store,'ABORTED')
            raise RuntimeError(f'interrupted DEV campaign preserved ({len(interrupted)} attempts); start a new campaign')
        if phase!='VALIDATED_CONFIG':raise ValueError('campaign not ready')
        transition(self.store,'DEV_RUNNING')
        seen=set();parent=SolverProgram(rounds=32);history=[];library=[]
        from .kernel.version import SystemVersion
        fixed=version_components(self.config)
        initial=SystemVersion(generation=-1,parent=None,solver=parent.model_dump(mode='json'),tool_library=(),
                              memory_snapshot=self.store.verify()['head'],research_policy={'policy':'uniform'},
                              source=self.store.state('source_hash'),**fixed)
        parent_version=initial.version_id();self.store.save('system_version',parent_version,initial.model_dump(mode='json'))
        try:
            for generation in range(self.config.generations):
                seed=self.config.seed+100000*generation
                dev,seen=self._panel(seed,'DEV',seen)
                select,seen=self._panel(seed+1,'SELECT',seen)
                self.store.event('GENERATION_STARTED',{'generation':generation,'public_panels':True})
                children={};summaries={};research_rows={}
                for policy in ('uniform','adaptive'):
                    child,summary,rows=self.improve(dev,parent,policy,generation,seed+2)
                    children[policy]=child;summaries[policy]=summary;research_rows[policy]=rows
                # SELECT chooses between fixed baseline methods and confirms which
                # research-generated candidate to freeze, not a scientific claim.
                baseline_scores={};baseline_rows={}
                for name,program in baseline_programs().items():
                    rows=self.evaluate(select,program,f'g{generation}:select-baseline-{name}',seed+3)
                    baseline_rows[name]=rows;baseline_scores[name]=sum(r['value'] for r in rows)
                baseline_name=max(baseline_scores,key=lambda x:(baseline_scores[x],x))
                baseline=baseline_programs()[baseline_name]
                child_select={p:self.evaluate(select,x,f'g{generation}:select-{p}',seed+3) for p,x in children.items()}
                policy=max(children,key=lambda p:(sum(r['value'] for r in child_select[p]),p))
                selected=children[policy]
                # Frozen before the subsequently generated public future panels.
                version=SystemVersion(generation=generation,parent=parent_version,solver=selected.model_dump(mode='json'),
                                      tool_library=tuple(library),memory_snapshot=self.store.verify()['head'],
                                      research_policy={'policy':policy,'mutation_weights':self.store.state('mutation_weights',[1,1,1,1])},
                                      source=self.store.state('source_hash'),**fixed)
                vid=version.version_id();self.store.save('system_version',vid,version.model_dump(mode='json'))
                self.store.event('DEV_SUCCESSOR_FROZEN',{'version':vid,'candidate':selected.model_dump(mode='json')})
                future,seen=self._panel(seed+4,'FUTURE',seen)
                # Deterministic arm order is alternated per generation, and paired
                # task RNG is held fixed across all arms.
                programs={'baseline':baseline,'parent':parent,'uniform':children['uniform'],'adaptive':children['adaptive']}
                names=list(programs)
                if generation%2:names.reverse()
                evaluated={name:self.evaluate(future,programs[name],f'g{generation}:future-{name}',seed+5) for name in names}
                def compare_rows(a,b):
                    return paired([{'task_id':x['task_id'],'family':x['family'],'candidate':x['value'],
                                    'baseline':y['value']} for x,y in zip(a,b)])
                solver=compare_rows(evaluated[policy],evaluated['baseline'])
                improver=compare_rows(evaluated['adaptive'],evaluated['uniform'])
                # Real intervention/placebo executions on public SELECT material.
                ablated=SolverProgram(weights=(0,0,0,0),rounds=selected.rounds,
                                      exchange=False,componentwise=False)
                ablation=self.evaluate(select,ablated,f'g{generation}:ablation',seed+3)
                placebo=self.evaluate(select,baseline,f'g{generation}:placebo-no-op',seed+3)
                asmap=lambda rows:{r['task_id']:r['value'] for r in rows}
                causal=causal_controls(asmap(baseline_rows[baseline_name]),asmap(child_select[policy]),
                                      asmap(ablation),asmap(placebo))
                transfer_domain='triangle_free_host_v1' if self.config.domain=='c4_host_v2' else 'c4_host_v2'
                transfer,seen=self._panel(seed+6,'FUTURE',seen,transfer_domain)
                a=self.evaluate(transfer,selected,f'g{generation}:transfer-candidate',seed+7)
                b=self.evaluate(transfer,baseline,f'g{generation}:transfer-baseline',seed+7)
                transfer_result=compare_rows(a,b)
                diagnosis=diagnose(research_rows[policy]);self.store.set_state('diagnosis',diagnosis)
                macro=compile_trace(selected,[r['trace'] for r in research_rows[policy]])
                mid=digest(macro);self.store.save('macro',mid,macro)
                # DEV retention uses SELECT alone; public future outcomes cannot
                # be used to retain/choose a different child for this generation.
                retained=sum(r['value'] for r in child_select[policy])>=baseline_scores[baseline_name]
                cap=Capability(name=f'g{generation}-compiled-solver',program=selected,domains=(self.config.domain,),
                    preconditions=('simple host graph, n <= 63','fixed bounded DSL'),
                    evidence=Evidence(math='EXECUTABLE',utility='DEV_ONLY',effects=('USES_DEV_DATA',),references=(mid,)),
                    maintenance_queries=self.config.limits.queries,status='DEV_RETAINED' if retained else 'QUARANTINED',
                    rollback=digest(parent.model_dump(mode='json')))
                cid=digest(cap.model_dump(mode='json'));self.store.save('capability',cid,cap.model_dump(mode='json'))
                mod=Modification(parent=parent_version,child=vid,
                    hypothesis='priority and local exchange improve finite-host search within fixed resources',
                    predicted_effect='higher witnessed edge count on future hosts',
                    falsifier='no future benefit or benefits vanish under matched resources and ablation',
                    rollback=parent_version,component='solver_program',
                    evidence=Evidence(math='EXECUTABLE',utility='DEV_ONLY',effects=('USES_DEV_DATA',)))
                self.store.save('modification',vid,mod.model_dump(mode='json'))
                result={'generation':generation,'version':vid,'selected_policy':policy,'baseline':baseline_name,
                        'research':summaries,'solver_comparison':solver,'better_improver_diagnostic':improver,
                        'causal_controls':causal,'transfer':transfer_result,'retained_in_dev':retained,
                        'scientifically_confirmed':False,'public_panel_freshness':'exact graph isomorphism disjoint within campaign'}
                self.store.save('generation',str(generation),result);history.append(result)
                # Learn a bounded proposal-allocation policy from DEV outcomes only.
                # Freeze it as a child policy for the next generation; FUTURE scores
                # never train or select it. This is a mechanism, not evidence of gain.
                learned=list(self.store.state('mutation_weights',[1,1,1,1]))
                adaptive_summary=summaries['adaptive'];base_score=adaptive_summary['scores'][0][0]
                for program_data,score in zip(adaptive_summary['candidate_programs'],adaptive_summary['scores']):
                    if score[0]>base_score:
                        for i,(old,new) in enumerate(zip(parent.weights,program_data['weights'])):
                            if old!=new:learned[i]=min(32,learned[i]+1)
                self.store.save('research_policy',str(generation),{
                    'parent_weights':adaptive_summary['mutation_weights'],'child_weights':learned,
                    'training_source':f'g{generation}-adaptive','effects':['USES_DEV_DATA'],
                    'claim':'candidate future research policy, utility unconfirmed'})
                self.store.set_state('mutation_weights',learned)
                self.store.set_state('completed_dev_generations',generation+1)
                self.store.snapshot(f'g{generation}.sqlite3')
                if retained:parent=selected;parent_version=vid;library.append(cid)
            self.store.set_state('latest_program',parent.model_dump(mode='json'))
            self.store.set_state('exposure_fingerprints',sorted(seen))
            summary={'status':'DEV_EXPERIMENT_COMPLETE','claim_ceiling':'FINITE_INSTANCE_RESULTS_AND_DEV_DIAGNOSTICS',
                     'generations':history,'promotion_allowed':False,'independent_custody':False,
                     'theorem_checked':False,'retained_dev_capabilities':library,
                     'scientific_generations_confirmed':0,'external_replication':False,
                     'total_attempts':self.store.db.execute('SELECT count(*) FROM attempts').fetchone()[0],
                     'limitations':['All panels public and locally generated','Fixed bounded candidate grammar',
                         'Exact solver is an evaluation reference, not a matched heuristic competitor',
                         'CPU limits matched; observed wall/CPU costs may differ','Discovery and checking costs separately ledgered',
                         'No Lean executable or arbitrary-code sandbox required by this data-only route',
                         'No novelty or recursive-improvement claim']}
            summary=json.loads(canonical(summary))
            self.store.set_state('summary',summary);transition(self.store,'CANDIDATE_FROZEN')
            self.report(summary)
            return summary
        except BaseException as exc:
            self.store.event('CAMPAIGN_ERROR',{'exception':type(exc).__name__,'message':str(exc)})
            self.store.interrupt_running()
            if self.store.state('phase')=='DEV_RUNNING':transition(self.store,'ABORTED')
            raise

    def report(self,summary=None):
        summary=summary or self.store.state('summary')
        if summary is None:raise ValueError('no completed report')
        lines=['# Genesis executed development campaign','',
               '**No scientific promotion. All results are public development diagnostics.**','',
               '| Generation | Candidate / baseline wins / ties | Adaptive / uniform wins / ties | Transfer wins / losses / ties |',
               '|---|---|---|---|']
        for g in summary['generations']:
            cells=[]
            for name in ('solver_comparison','better_improver_diagnostic','transfer'):
                r=g[name];cells.append(f"{r['wins']} / {r['losses']} / {r['ties']}")
            lines.append('| '+str(g['generation'])+' | '+' | '.join(cells)+' |')
        lines+=['',f"Executed attempts, including exact-check attempts: {summary['total_attempts']}.",'',
                '## Limitations','']+['- '+x for x in summary['limitations']]
        from .kernel.wording import require_clean
        text='\n'.join(lines)+'\n'
        require_clean(text,{'math':'FINITE_CERTIFIED','utility':'DEV_ONLY','causality':'NOT_TESTED',
                            'improver':'NOT_TESTED','novelty':'UNKNOWN','replication':'NONE'})
        (self.root/'reports/report.md').write_text(text)
        (self.root/'reports/results.json').write_bytes(canonical(summary))

    def replay(self,limit=10):
        if type(limit) is not int or limit<1:raise ValueError('replay limit')
        self._check_frozen_environment();results=[]
        rows=self.store.db.execute("SELECT id,request,receipt FROM attempts WHERE status='SUCCESS' ORDER BY rowid").fetchall()
        for aid,reqh,rh in rows:
            req=self.store.get(reqh)
            if req['kind']!='solver':continue
            task=GraphTask.model_validate_json(canonical(req['task']))
            p=SolverProgram.model_validate_json(canonical(req['program']))
            from .models import Limits
            replay_aid=self.store.start('replay-'+aid,{'kind':'replay','original_attempt':aid,'request':reqh})
            receipt=execute(task,p,Limits.model_validate_json(canonical(req['limits'])),req['seed'])
            original=self.store.get(rh)
            passed=receipt['status']=='SUCCESS' and all(receipt['result'][k]==original['result'][k] for k in ('selected','value','queries','trace'))
            self.store.finish(replay_aid,{**receipt,'deterministic_match':passed})
            results.append({'attempt':aid,'matched':passed})
            if len(results)>=limit:break
        return {'records':results,'all_matched':bool(results) and all(r['matched'] for r in results),
                'scope':'internal deterministic replay, timing excluded'}
