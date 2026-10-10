"""Frozen copy of the v1 solver interpreter (commit c2d53a9), used only as a test oracle."""
import random
from itertools import combinations
from genesis.models import SolverProgram
from genesis.graphs import motifs,neighbors,check_witness,components


def solve(task,program,query_budget,seed):
    if type(query_budget) is not int or not 1<=query_budget<=100000:raise ValueError('query budget')
    rng=random.Random(seed);es=task.edges;m=len(es);cycles=motifs(task)
    adj=neighbors(task.n,es);degrees=[x.bit_count() for x in adj]
    features=[(degrees[u]+degrees[v],degrees[u]*degrees[v],(adj[u]&adj[v]).bit_count(),
               sum(bool(c&(1<<i)) for c in cycles)) for i,(u,v) in enumerate(es)]
    group={v:i for i,c in enumerate(components(task)) for v in c}
    queries=0;best=0;trace=[]
    def valid(mask):
        nonlocal queries
        if queries>=query_budget:return None
        queries+=1
        return not any(mask&cycle==cycle for cycle in cycles)
    for r in range(program.rounds):
        jitter=[rng.random() for _ in es]
        def priority(i):
            score=sum(w*x for w,x in zip(program.weights,features[i]))
            return (group[es[i][0]] if program.componentwise else 0,score,jitter[i],i)
        order=sorted(range(m),key=priority);chosen=0
        for i in order:
            trial=chosen|(1<<i);ok=valid(trial)
            if ok is None:break
            if ok:chosen=trial
        if program.exchange:
            improved=True
            while improved and queries<query_budget:
                improved=False
                present=[i for i in range(m) if chosen>>i&1]
                missing=[i for i in range(m) if not chosen>>i&1]
                rng.shuffle(present);rng.shuffle(missing)
                for drop in present:
                    for a,b in combinations(missing,2):
                        trial=(chosen&~(1<<drop))|(1<<a)|(1<<b);ok=valid(trial)
                        if ok is None:break
                        if ok:chosen=trial;improved=True;break
                    if improved or queries>=query_budget:break
        if chosen.bit_count()>best.bit_count():best=chosen
        trace.append({'round':r,'value':chosen.bit_count(),'queries':queries})
        if queries>=query_budget or best.bit_count()==m:break
    selected=tuple(e for i,e in enumerate(es) if best>>i&1)
    checked=check_witness(task,selected)
    return {'selected':selected,'value':checked['value'],'queries':queries,
            'meter':'trusted-DSL-interpreter-v1','trace':trace}


def baseline_programs():
    return {
        'multistart':SolverProgram(rounds=32),
        'exchange':SolverProgram(rounds=32,exchange=True),
        'low_cycle':SolverProgram(weights=(0,0,0,1),rounds=32),
    }
