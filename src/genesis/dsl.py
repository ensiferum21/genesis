"""Fixed, bounded graph program interpreter. Candidate data cannot execute Python.

Validity queries are answered incrementally: every trial is a valid incumbent
plus one or two added edges, so only forbidden motifs containing an added edge
can become complete. This returns exactly the same answer as checking every
motif, with the same query accounting and random stream; the v1 interpreter is
kept under tests_genesis/reference as an equivalence oracle.
"""
import random
from itertools import combinations
from .models import SolverProgram
from .graphs import motifs,neighbors,check_witness,components


def motif_index(task):
    """Map each host edge index to the forbidden-motif masks that contain it."""
    cycles=motifs(task);index=[[] for _ in task.edges]
    for c in cycles:
        rest=c
        while rest:
            bit=rest&-rest;rest^=bit
            index[bit.bit_length()-1].append(c)
    return cycles,index


def solve(task,program,query_budget,seed):
    if type(query_budget) is not int or not 1<=query_budget<=100000:raise ValueError('query budget')
    rng=random.Random(seed);es=task.edges;m=len(es);cycles,by_edge=motif_index(task)
    adj=neighbors(task.n,es);degrees=[x.bit_count() for x in adj]
    features=[(degrees[u]+degrees[v],degrees[u]*degrees[v],(adj[u]&adj[v]).bit_count(),
               len(by_edge[i])) for i,(u,v) in enumerate(es)]
    group={v:i for i,c in enumerate(components(task)) for v in c}
    queries=0;best=0;trace=[]
    def valid(trial,added):
        # Precondition (maintained below): trial minus `added` is motif-free.
        nonlocal queries
        if queries>=query_budget:return None
        queries+=1
        for i in added:
            for cycle in by_edge[i]:
                if trial&cycle==cycle:return False
        return True
    for r in range(program.rounds):
        jitter=[rng.random() for _ in es]
        def priority(i):
            score=sum(w*x for w,x in zip(program.weights,features[i]))
            return (group[es[i][0]] if program.componentwise else 0,score,jitter[i],i)
        order=sorted(range(m),key=priority);chosen=0
        for i in order:
            trial=chosen|(1<<i);ok=valid(trial,(i,))
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
                        trial=(chosen&~(1<<drop))|(1<<a)|(1<<b);ok=valid(trial,(a,b))
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
