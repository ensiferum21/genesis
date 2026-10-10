"""Executable typed Research IR for the bounded graph wedge (spec §4, §32).

The sixteen primitive names have concrete narrow handlers. A primitive may have
a few typed overloads (e.g. VERIFY a witness, or VERIFY an upper-bound
contract); each overload has an explicit input signature, output kind and
allowed parameters. Their availability does not imply the broad scientific
macro catalogue is implemented or validated.

Every invocation is recorded in `Interpreter.trace` with its inputs, concrete
parameters and a digest of the deterministic part of its output, so an
executed macro is itself an IR program that can be replayed and compared.
"""
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel
from .common import canonical,digest
from .models import GraphTask,SolverProgram,Limits
from .graphs import check_witness,components,relabel,canonical_graph
from .execution import execute
from .research import propose,diagnose,compile_trace
from .evaluation import propagate_effects
from .mrdl import evaluate


@dataclass(frozen=True)
class Value:
    kind:str
    data:Any
    effects:tuple[str,...]=()
    provenance:tuple[str,...]=()


# Primary signature per primitive (kept for compatibility and documentation).
CONTRACTS={
 'FORMALIZE':(('RawTask',),'Goal'), 'REPRESENT':(('Goal',),'Representation'),
 'DISTINGUISH':(('Predictions',),'Experiment'), 'FACTOR':(('Goal',),'Decomposition'),
 'TRANSFORM':(('Goal',),'Goal'), 'PROPOSE':(('Program',),'Candidates'),
 'EXECUTE':(('Goal','Program'),'Receipt'), 'OBSERVE':(('Receipt',),'Observation'),
 'INTERVENE':(('Program',),'Program'), 'VERIFY':(('Goal','Witness'),'Certificate'),
 'TRANSPORT':(('Goal','Witness'),'TransportedWitness'), 'COMPOSE':(('Goal','Witnesses'),'Witness'),
 'BRANCH':(('Program',),'Candidates'), 'COMPRESS':(('Program','Traces'),'Macro'),
 'SYNTHESIZE':(('Program',),'Candidates'), 'REFLECT':(('Rows',),'Hypotheses')}

# (primitive, inputs, output kind, allowed params, overload tag). '*' = zero or more of that kind.
OVERLOADS=[
 ('FORMALIZE',('RawTask',),'Goal',set(),'task'),
 ('REPRESENT',('Goal',),'Representation',{'expression'},'mrdl'),
 ('DISTINGUISH',('Predictions',),'Experiment',{'costs'},'max-separation'),
 ('FACTOR',('Goal',),'Decomposition',set(),'components'),
 ('TRANSFORM',('Goal',),'Goal',{'permutation'},'relabel'),
 ('TRANSFORM',('Goal',),'Goal',{'induced'},'induced-subgraph'),
 ('PROPOSE',('Program',),'Candidates',{'count','policy'},'programs'),
 ('EXECUTE',('Goal','Program'),'Receipt',set(),'fixed-dsl'),
 ('OBSERVE',('Receipt',),'Observation',set(),'metrics'),
 ('OBSERVE',('Receipt',),'Witness',{'field'},'witness'),
 ('INTERVENE',('Program',),'Program',{'changes'},'program-edit'),
 ('VERIFY',('Goal','Witness'),'Certificate',set(),'witness'),
 ('VERIFY',('Goal','Witness'),'Certificate',{'contract','seconds'},'upper-bound'),
 ('TRANSPORT',('Goal','Witness'),'TransportedWitness',{'permutation'},'relabel'),
 ('TRANSPORT',('Goal','Witness'),'TransportedWitness',{'mapping','target'},'embedding'),
 ('COMPOSE',('Goal','Witnesses'),'Witness',set(),'union'),
 ('COMPOSE',('Goal','TransportedWitness*'),'Witness',set(),'union-transported'),
 ('BRANCH',('Program',),'Candidates',{'count','policy'},'programs'),
 ('COMPRESS',('Program','Traces'),'Macro',set(),'trace-grammar'),
 ('SYNTHESIZE',('Program',),'Candidates',{'count','policy'},'programs'),
 ('REFLECT',('Rows',),'Hypotheses',set(),'diagnose'),
]


def _match(signature,kinds):
    if signature and signature[-1].endswith('*'):
        fixed=signature[:-1];rest=signature[-1][:-1]
        return tuple(kinds[:len(fixed)])==fixed and all(k==rest for k in kinds[len(fixed):])
    return tuple(kinds)==signature


def to_json(x):
    if isinstance(x,BaseModel):return {'__model__':type(x).__name__,'data':x.model_dump(mode='json')}
    if isinstance(x,dict):return {str(k):to_json(v) for k,v in sorted(x.items(),key=lambda kv:str(kv[0]))}
    if isinstance(x,(list,tuple)):return [to_json(v) for v in x]
    if isinstance(x,(set,frozenset)):return sorted(to_json(v) for v in x)
    return x


def from_json(kind,data):
    """Rebuild Values recorded as program inputs (only kinds that enter from outside)."""
    def model(x):
        if isinstance(x,dict) and set(x)=={'__model__','data'}:
            return {'GraphTask':GraphTask,'SolverProgram':SolverProgram}[x['__model__']].model_validate_json(canonical(x['data']))
        if isinstance(x,list):return [model(v) for v in x]
        if isinstance(x,dict):return {k:model(v) for k,v in x.items()}
        return x
    data=model(data)
    if kind=='Traces':data=[[dict(r) for r in t] for t in data]
    return data


def stable(kind,data):
    """Deterministic projection used for replay comparison (timings excluded)."""
    if kind=='Receipt':
        r=data.get('result',{}) if isinstance(data,dict) else {}
        return {'status':data.get('status'),'selected':to_json(r.get('selected')),'value':r.get('value'),
                'queries':r.get('queries'),'trace':r.get('trace')}
    if kind=='Observation':return {k:data.get(k) for k in ('value','queries')}
    if kind=='Certificate' and isinstance(data,dict) and 'lower' in data:
        return {k:to_json(data.get(k)) for k in ('status','lower','upper','gap','witness')}
    return to_json(data)


class Interpreter:
    def __init__(self,limits=None,max_actions=24,seed=0,custody=None):
        """`custody`: a Store whose CAS receives certificate bundles and proof objects (R-03).
        Without it, bundles and objects are kept in memory (self.certificates / self.objects)."""
        self.limits=limits or Limits();self.max_actions=max_actions;self.seed=seed;self.actions=0
        self.trace=[];self.custody=custody;self.certificates={};self.objects={}

    # Parameter that selects an overload when a primitive has several with the same input kinds.
    DISCRIMINATOR={('TRANSFORM','permutation'):'relabel',('TRANSFORM','induced'):'induced-subgraph',
                   ('OBSERVE','field'):'witness',('VERIFY','contract'):'upper-bound',
                   ('TRANSPORT','permutation'):'relabel',('TRANSPORT','mapping'):'embedding'}

    def _overload(self,op,values,params):
        if op not in CONTRACTS:raise ValueError('unregistered primitive')
        kinds=tuple(v.kind for v in values)
        typed=[o for o in OVERLOADS if o[0]==op and _match(o[1],kinds)]
        if not typed:raise ValueError('IR type mismatch')
        if len(typed)>1:
            tags={self.DISCRIMINATOR[(op,k)] for k in params if (op,k) in self.DISCRIMINATOR}
            if len(tags)>1:raise ValueError('IR parameter outside contract')
            default={'OBSERVE':'metrics','VERIFY':'witness'}.get(op)
            tag=tags.pop() if tags else default
            typed=[o for o in typed if o[4]==tag]
            if not typed:raise ValueError('IR parameter outside contract')
        overload=typed[0]
        if set(params)-overload[3]:raise ValueError('IR parameter outside contract')
        if overload[4]=='upper-bound' and params.get('contract')!='upper_bound':raise ValueError('unknown contract')
        return overload

    def invoke(self,op,values,params=None,*,node_id=None,input_ids=()):
        params=params or {}
        overload=self._overload(op,values,params)
        if self.actions>=self.max_actions:raise RuntimeError('IR action grant exhausted')
        self.actions+=1;xs=[v.data for v in values];tag=overload[4];kind=overload[2]
        own=[]
        if op=='FORMALIZE':data=GraphTask.model_validate_json(canonical(xs[0]))
        elif op=='REPRESENT':data=evaluate(params['expression'],xs[0])
        elif op=='DISTINGUISH':
            table=xs[0];costs=params['costs']
            if not table or set(table)!=set(costs):raise ValueError('experiment schema')
            scored=[]
            for action,preds in table.items():
                if type(costs[action]) not in (int,float) or costs[action]<=0:raise ValueError('experiment cost')
                if not preds:raise ValueError('prediction table')
                score=sum(preds[i]!=preds[j] for i in range(len(preds)) for j in range(i))/costs[action]
                scored.append((score,action))
            score,action=max(scored)
            data={'action':action if score else None,'separation_per_cost':score,
                  'status':'PROPOSED_EXPERIMENT' if score else 'NO_SEPARATING_ACTION',
                  'predictions_are_observations':False};own=['HYPOTHETICAL']
        elif op=='FACTOR':
            data={'components':components(xs[0]),'relation':'DISJOINT_CONNECTED_COMPONENTS',
                  'composition':'union witnesses, then independently check against original host'}
        elif op=='TRANSFORM' and tag=='relabel':data=relabel(xs[0],params['permutation'])
        elif op=='TRANSFORM':
            vertices=params['induced']
            if not isinstance(vertices,list) or len(set(vertices))!=len(vertices) or \
                    any(type(v) is not int or not 0<=v<xs[0].n for v in vertices):
                raise ValueError('induced vertex subset')
            order=sorted(vertices);index={v:i for i,v in enumerate(order)}
            edges=tuple(sorted((index[u],index[v]) for u,v in xs[0].edges if u in index and v in index))
            data=GraphTask(task_id=xs[0].task_id+'/induced',domain=xs[0].domain,n=len(order),edges=edges,
                           family=xs[0].family,split=xs[0].split)
        elif op in ('PROPOSE','BRANCH','SYNTHESIZE'):
            data=propose(xs[0],params.get('count',4),self.seed,params.get('policy','uniform'))
            own=['UNCHECKED_PROPOSAL']
        elif op=='EXECUTE':data=execute(xs[0],xs[1],self.limits,self.seed)
        elif op=='OBSERVE' and tag=='witness':
            if params['field']!='selected' or xs[0].get('status')!='SUCCESS':raise ValueError('no witness to observe')
            data=tuple(tuple(e) for e in xs[0]['result']['selected']);own=['UNCHECKED_PROPOSAL']
        elif op=='OBSERVE':
            if xs[0].get('status')!='SUCCESS':raise ValueError('no successful observation')
            data={'value':xs[0]['result']['value'],'queries':xs[0]['result']['queries'],
                  'wall_ns':xs[0]['wall_ns'],'provenance':'execution receipt','instrument':'fixed-DSL-counter'}
        elif op=='INTERVENE':
            changes=params['changes']
            if set(changes)-{'weights','rounds','exchange','componentwise'}:raise PermissionError('protected component mutation')
            data=SolverProgram.model_validate_json(canonical({**xs[0].model_dump(mode='json'),**changes}))
            own=['INTERVENTION_CANDIDATE']
        elif op=='VERIFY' and tag=='upper-bound':
            from .verification.sat import certified_bounds
            seconds=params.get('seconds',60)
            if type(seconds) not in (int,float) or not 0<seconds<=3600:raise ValueError('verification budget')
            bounds=certified_bounds(xs[0],seconds=seconds,start_witness=xs[1])
            data={k:bounds.get(k) for k in ('status','lower','upper','gap','witness')}
            data['upper_method']=(bounds.get('upper_certificate') or {}).get('method')
            data['upper_checker']=(bounds.get('upper_certificate') or {}).get('checker')
            data['certificate']=None
            if bounds.get('status')!='CHECKER_ERROR' and bounds.get('upper_certificate') is not None:
                # Keep the original proof artifacts, not just their summary (R-03).
                from .verification.certificates import build,persist
                bundle,blobs=build(xs[0],bounds)
                if self.custody is not None:data['certificate']=persist(self.custody,bundle,blobs)
                else:
                    data['certificate']=digest(bundle);self.certificates[data['certificate']]=bundle
                    self.objects.update(blobs)
        elif op=='VERIFY':data=check_witness(xs[0],xs[1])
        elif op=='TRANSPORT' and tag=='relabel':
            check_witness(xs[0],xs[1]);order=params['permutation'];target=relabel(xs[0],order)
            witness=tuple(sorted(tuple(sorted((order[u],order[v]))) for u,v in xs[1]))
            data={'task':target,'witness':witness,'check':check_witness(target,witness),
                  'relation':'VERTEX_RELABEL_EQUIVALENCE'}
        elif op=='TRANSPORT':
            check_witness(xs[0],xs[1])
            target=GraphTask.model_validate_json(canonical(params['target']))
            mapping=params['mapping']
            if not isinstance(mapping,list) or len(mapping)!=xs[0].n or len(set(mapping))!=len(mapping):
                raise ValueError('embedding mapping')
            witness=tuple(sorted(tuple(sorted((mapping[u],mapping[v]))) for u,v in xs[1]))
            if not set(witness)<=set(target.edges):raise ValueError('embedding leaves the target host')
            data={'task':target,'witness':witness,'relation':'INDUCED_SUBGRAPH_EMBEDDING',
                  'note':'validity on the target is checked after composition, not inherited'}
        elif op=='COMPOSE' and tag=='union':
            data=tuple(sorted(set(e for witness in xs[1] for e in witness)))
            check_witness(xs[0],data)
        elif op=='COMPOSE':
            data=tuple(sorted(set(e for t in xs[1:] for e in t['witness'])))
            check_witness(xs[0],data)  # the glued witness is re-checked on the original host
        elif op=='COMPRESS':data=compile_trace(xs[0],xs[1]);own=['USES_DEV_DATA']
        elif op=='REFLECT':data=diagnose(xs[0]);own=['HYPOTHETICAL']
        effects=propagate_effects([{'effects':v.effects} for v in values],own)
        if op=='VERIFY':effects=tuple(e for e in effects if e not in ('UNCHECKED_PROPOSAL','INTERVENTION_CANDIDATE'))
        provenance=tuple(sorted({p for v in values for p in v.provenance}))
        out=Value(kind,data,effects,provenance)
        self.trace.append({'id':node_id or f'n{len(self.trace)}','op':op,'overload':tag,
                           'inputs':list(input_ids),'params':to_json(params),'kind':kind,
                           'output_digest':digest(stable(kind,data)),'effects':list(effects)})
        if kind=='Certificate' and isinstance(data,dict) and data.get('certificate'):
            self.trace[-1]['artifacts']=[data['certificate']]
        return out

    def run(self,nodes,inputs):
        if not isinstance(nodes,list) or len(nodes)>64:raise ValueError('IR graph bound')
        values=dict(inputs)
        for node in nodes:
            if set(node)!={'id','op','inputs','params'} or node['id'] in values:raise ValueError('IR node schema/identity')
            if any(key not in values for key in node['inputs']):raise ValueError('IR dependency missing or cycle')
            values[node['id']]=self.invoke(node['op'],[values[x] for x in node['inputs']],node['params'],
                                           node_id=node['id'],input_ids=node['inputs'])
        return values


def program_record(name,inputs,trace,seed,limits):
    """Serializable IR program for an executed macro: inputs + concrete nodes + output digests."""
    return {'schema':'genesis-ir-program-v1','macro':name,'seed':seed,'limits':limits.model_dump(mode='json'),
            'inputs':{k:{'kind':v.kind,'data':to_json(v.data),'effects':list(v.effects),
                         'provenance':list(v.provenance)} for k,v in inputs.items()},
            'nodes':[{**{k:n[k] for k in ('id','op','inputs','params','output_digest')},
                      **({'artifacts':n['artifacts']} if n.get('artifacts') else {})} for n in trace]}


def replay(record,max_actions=64):
    """Re-execute a recorded IR program; return (ok, mismatching node ids)."""
    ir=Interpreter(Limits.model_validate_json(canonical(record['limits'])),max_actions=max_actions,seed=record['seed'])
    inputs={k:Value(v['kind'],from_json(v['kind'],v['data']),tuple(v['effects']),tuple(v['provenance']))
            for k,v in record['inputs'].items()}
    def params(p):
        return from_json('params',p)
    nodes=[{'id':n['id'],'op':n['op'],'inputs':n['inputs'],'params':params(n['params'])} for n in record['nodes']]
    ir.run(nodes,inputs)
    mismatches=[n['id'] for n,t in zip(record['nodes'],ir.trace) if n['output_digest']!=t['output_digest']]
    return not mismatches and len(ir.trace)==len(record['nodes']),mismatches
