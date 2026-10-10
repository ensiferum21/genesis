"""Executable typed Research IR for the bounded graph wedge.

The sixteen primitive names have concrete narrow handlers. Their availability does
not imply the broad scientific macro catalogue is implemented or validated.
"""
from dataclasses import dataclass
from typing import Any
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


CONTRACTS={
 'FORMALIZE':(('RawTask',),'Goal'), 'REPRESENT':(('Goal',),'Representation'),
 'DISTINGUISH':(('Predictions',),'Experiment'), 'FACTOR':(('Goal',),'Decomposition'),
 'TRANSFORM':(('Goal',),'Goal'), 'PROPOSE':(('Program',),'Candidates'),
 'EXECUTE':(('Goal','Program'),'Receipt'), 'OBSERVE':(('Receipt',),'Observation'),
 'INTERVENE':(('Program',),'Program'), 'VERIFY':(('Goal','Witness'),'Certificate'),
 'TRANSPORT':(('Goal','Witness'),'TransportedWitness'), 'COMPOSE':(('Goal','Witnesses'),'Witness'),
 'BRANCH':(('Program',),'Candidates'), 'COMPRESS':(('Program','Traces'),'Macro'),
 'SYNTHESIZE':(('Program',),'Candidates'), 'REFLECT':(('Rows',),'Hypotheses')}


class Interpreter:
    def __init__(self,limits=None,max_actions=24,seed=0):
        self.limits=limits or Limits();self.max_actions=max_actions;self.seed=seed;self.actions=0

    def invoke(self,op,values,params=None):
        params=params or {}
        if op not in CONTRACTS:raise ValueError('unregistered primitive')
        ins,kind=CONTRACTS[op]
        if tuple(v.kind for v in values)!=ins:raise ValueError('IR type mismatch')
        if self.actions>=self.max_actions:raise RuntimeError('IR action grant exhausted')
        self.actions+=1;xs=[v.data for v in values]
        allowed={'REPRESENT':{'expression'},'DISTINGUISH':{'costs'},'TRANSFORM':{'permutation'},
                 'PROPOSE':{'count','policy'},'BRANCH':{'count','policy'},'SYNTHESIZE':{'count','policy'},
                 'INTERVENE':{'changes'},'TRANSPORT':{'permutation'}}.get(op,set())
        if set(params)-allowed:raise ValueError('IR parameter outside contract')
        own=[]
        if op=='FORMALIZE':data=GraphTask.model_validate_json(canonical(xs[0]))
        elif op=='REPRESENT':data=evaluate(params['expression'],xs[0])
        elif op=='DISTINGUISH':
            # Finite hypothesis prediction table: pick the greatest pairwise
            # disagreement per independently supplied action cost.
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
        elif op=='TRANSFORM':data=relabel(xs[0],params['permutation'])
        elif op in ('PROPOSE','BRANCH','SYNTHESIZE'):
            data=propose(xs[0],params.get('count',4),self.seed,params.get('policy','uniform'))
            own=['UNCHECKED_PROPOSAL']
        elif op=='EXECUTE':data=execute(xs[0],xs[1],self.limits,self.seed)
        elif op=='OBSERVE':
            if xs[0].get('status')!='SUCCESS':raise ValueError('no successful observation')
            data={'value':xs[0]['result']['value'],'queries':xs[0]['result']['queries'],
                  'wall_ns':xs[0]['wall_ns'],'provenance':'execution receipt','instrument':'fixed-DSL-counter'}
        elif op=='INTERVENE':
            changes=params['changes']
            if set(changes)-{'weights','rounds','exchange','componentwise'}:raise PermissionError('protected component mutation')
            data=SolverProgram.model_validate_json(canonical({**xs[0].model_dump(mode='json'),**changes}))
            own=['INTERVENTION_CANDIDATE']
        elif op=='VERIFY':data=check_witness(xs[0],xs[1])
        elif op=='TRANSPORT':
            check_witness(xs[0],xs[1]);order=params['permutation'];target=relabel(xs[0],order)
            witness=tuple(sorted(tuple(sorted((order[u],order[v]))) for u,v in xs[1]))
            data={'task':target,'witness':witness,'check':check_witness(target,witness),
                  'relation':'VERTEX_RELABEL_EQUIVALENCE'}
        elif op=='COMPOSE':
            data=tuple(sorted(set(e for witness in xs[1] for e in witness)))
            check_witness(xs[0],data)
        elif op=='COMPRESS':data=compile_trace(xs[0],xs[1]);own=['USES_DEV_DATA']
        elif op=='REFLECT':data=diagnose(xs[0]);own=['HYPOTHETICAL']
        effects=propagate_effects([{'effects':v.effects} for v in values],own)
        provenance=tuple(sorted({p for v in values for p in v.provenance}))
        return Value(kind,data,effects,provenance)

    def run(self,nodes,inputs):
        if not isinstance(nodes,list) or len(nodes)>64:raise ValueError('IR graph bound')
        values=dict(inputs)
        for node in nodes:
            if set(node)!={'id','op','inputs','params'} or node['id'] in values:raise ValueError('IR node schema/identity')
            if any(key not in values for key in node['inputs']):raise ValueError('IR dependency missing or cycle')
            values[node['id']]=self.invoke(node['op'],[values[x] for x in node['inputs']],node['params'])
        return values
