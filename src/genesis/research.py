"""Bounded world ecology, program synthesis, reusable capabilities and diagnostics."""
from collections import Counter
from dataclasses import dataclass,field
from itertools import combinations
import random
from .common import digest
from .models import GraphTask,SolverProgram
from .graphs import canonical_graph,SearchLimit


def make_panel(seed,count,domain,split,excluded=None,max_edges=18):
    rng=random.Random(seed);seen=set(excluded or ());out=[];tries=0
    while len(out)<count and tries<count*2000:
        tries+=1;n=rng.choice((5,6,7));family=rng.choice(('erdos_sparse','erdos_dense','bipartite','planted_cluster'))
        p=.32 if family=='erdos_sparse' else .64
        edges=[]
        for u,v in combinations(range(n),2):
            probability=p
            if family=='bipartite':probability=.7 if (u<n//2)!=(v<n//2) else 0
            if family=='planted_cluster':probability=.85 if u<n//2 and v<n//2 else .32
            if rng.random()<probability:edges.append((u,v))
        if not 5<=len(edges)<=max_edges:continue
        task=GraphTask(task_id=f'{split.lower()}-{seed}-{len(out):04}',domain=domain,n=n,
                       edges=tuple(edges),family=family,split=split)
        try:key=canonical_graph(task)
        except SearchLimit:continue
        if key in seen:continue
        seen.add(key);out.append(task)
    if len(out)!=count:raise RuntimeError('insufficient structurally distinct tasks within generator budget')
    return out,seen


def propose(parent,count,seed,policy='uniform',failure_summary=None,mutation_weights=None):
    if policy not in ('uniform','adaptive'):raise ValueError('unknown policy')
    if not 2<=count<=8:raise ValueError('proposal cap')
    rng=random.Random(seed)
    candidates=[parent,SolverProgram(rounds=32,exchange=True)]
    if policy=='adaptive' and failure_summary and failure_summary.get('gap_cases',0):
        candidates.append(SolverProgram(weights=(0,0,0,1),rounds=32,exchange=True))
    while len(candidates)<count:
        weights=list(parent.weights)
        if policy=='adaptive':
            # Bounded mutation near the incumbent; reserve the last proposal for
            # a structurally different random grammar point to preserve exploration.
            dimension=rng.choices(range(4),weights=mutation_weights or (1,1,1,1))[0]
            weights[dimension]=rng.randint(-3,3)
        else:weights=[rng.randint(-3,3) for _ in range(4)]
        p=SolverProgram(weights=tuple(weights),rounds=rng.choice((2,4,8,32)),
                        exchange=rng.choice((False,True)),componentwise=rng.choice((False,True)))
        if p not in candidates:candidates.append(p)
    return candidates[:count]


def diagnose(rows):
    gaps=[r for r in rows if r.get('optimum') is not None and r.get('value',0)<r['optimum']]
    failures=Counter(r.get('status','UNKNOWN') for r in rows if r.get('status')!='SUCCESS')
    return {'gap_cases':len(gaps),'failure_types':dict(failures),
            'families':dict(Counter(r['family'] for r in gaps)),
            'hypotheses':(['SEARCH_POLICY_LIMITED','REPRESENTATION_LIMITED'] if gaps else [])+
                         (['EXECUTION_LIMITED'] if failures else []),
            'epistemic_type':'HYPOTHESIS','universal_barrier_claim':False}


def dominates(a,b):
    if len(a)!=len(b):raise ValueError('Pareto dimension mismatch')
    return all(x>=y for x,y in zip(a,b)) and any(x>y for x,y in zip(a,b))


@dataclass
class World:
    world_id:str
    parents:tuple[str,...]
    depth:int
    program:SolverProgram
    state:str='ACTIVE'
    panels:int=0
    metrics:tuple[float,...]=()
    lessons:dict=field(default_factory=dict)


class Ecology:
    def __init__(self,cap=8,scope='local'):
        if not 1<=cap<=8:raise ValueError('world cap')
        self.scope=scope;self.cap=cap;self.worlds={};self.epoch=0;self.births=0;self.hybrids=0
        self.actions=Counter();self.shared=0

    def next_epoch(self):
        self.epoch+=1;self.births=0;self.hybrids=0;self.actions.clear();self.shared=0

    def birth(self,program,parents=()):
        if len(parents)>2 or len(set(parents))!=len(parents):raise ValueError('parent arity')
        if any(p not in self.worlds for p in parents):raise ValueError('unknown parent')
        if self.births>=4 or sum(w.state=='ACTIVE' for w in self.worlds.values())>=self.cap:
            raise ValueError('world birth budget exhausted')
        if len(parents)==2 and self.hybrids>=1:raise ValueError('hybrid budget exhausted')
        depth=1+max((self.worlds[p].depth for p in parents),default=-1)
        if depth>8:raise ValueError('lineage cap')
        wid=digest({'scope':self.scope,'epoch':self.epoch,'birth':self.births,'parents':parents,'program':program.model_dump(mode='json')})
        self.worlds[wid]=World(wid,tuple(parents),depth,program)
        self.births+=1;self.hybrids+=int(len(parents)==2)
        return wid

    def action(self,wid):
        if self.worlds[wid].state!='ACTIVE' or self.actions[wid]>=4:raise ValueError('world action budget')
        self.actions[wid]+=1

    def shared_experiment(self):
        if self.shared>=8:raise ValueError('shared experiment budget')
        self.shared+=1

    def observe(self,wid,metrics,lessons):
        w=self.worlds[wid]
        if w.state!='ACTIVE':raise ValueError('inactive world')
        w.panels+=1;w.metrics=tuple(metrics);w.lessons=dict(lessons)
        if w.panels>=2:w.state='DORMANT'

    def retire(self,wid,reason):
        w=self.worlds[wid];w.state='RETIRED';w.lessons={**w.lessons,'retirement_reason':reason}

    def frontier(self):
        scored=[w for w in self.worlds.values() if w.metrics and w.state!='RETIRED']
        return [w.world_id for w in scored if not any(dominates(v.metrics,w.metrics) for v in scored)]


def compile_trace(program,traces):
    """Lossless trace grammar compression, not a newly proved algorithm."""
    patterns=Counter(tuple((r['round'],r['value']) for r in trace) for trace in traces)
    return {'schema':'graph-trace-macro-v1','program':program.model_dump(mode='json'),
            'patterns':[{'pattern':p,'count':n} for p,n in patterns.items()],
            'scope':'reusable fixed DSL solver program; counts from DEV',
            'effects':['USES_DEV_DATA'],'evidence':'EXECUTABLE'}
