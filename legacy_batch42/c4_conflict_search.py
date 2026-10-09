"""Cycle-aware greedy search, DEV only. Query budget is not CPU budget."""
import hashlib
import random
from c4_math_wedge import normalize, verify
from c4_independent_replay import cycle_masks, replay
from c4_budget_search import run as baseline


def run(n, edges, *, seed=0, budget=60):
    host=normalize(n,edges)
    if type(seed) is not int or type(budget) is not int or not 1<=budget<=100000:
        raise ValueError('invalid seed/budget')
    cycles=cycle_masks(n,host)
    m=len(host)
    # Count cycles each edge participates in; low-conflict edges first.
    degree=[sum(bool(c & (1<<j)) for c in cycles) for j in range(m)]
    rng=random.Random(seed)
    queries=0; best=0; rounds=0
    while queries<budget:
        # Different cycle-aware rankings, with reproducible randomized ties.
        jitter=[rng.random() for _ in range(m)]
        if rounds%3==0:
            order=sorted(range(m),key=lambda j:(degree[j],jitter[j]))
        elif rounds%3==1:
            order=sorted(range(m),key=lambda j:(degree[j]+rng.random()*max(1,max(degree,default=0)),jitter[j]))
        else:
            order=sorted(range(m),key=lambda j:(degree[j],-jitter[j]))
        mask=0
        for j in order:
            if queries>=budget:break
            candidate=mask | (1<<j)
            queries+=1
            if not any((candidate & c)==c for c in cycles):mask=candidate
        if mask.bit_count()>best.bit_count():best=mask
        rounds+=1
        if m==0 or best.bit_count()==m:break
    selected=tuple(e for j,e in enumerate(host) if best>>j&1)
    if not verify(n,host,selected):raise RuntimeError('invalid witness')
    return {'size':len(selected),'selected':selected,'queries':queries,'budget':budget,'method':'cycle_aware','cpu_matched':False}


def compare(cases,*,seed=703,budget=60):
    if not isinstance(cases,list) or not cases:raise ValueError('cases required')
    ids=set();records=[]
    for case in cases:
        cid=case['id']
        if not isinstance(cid,str) or not cid or cid in ids:raise ValueError('duplicate case id')
        ids.add(cid)
        n,host=case['n'],normalize(case['n'],case['host'])
        if len(host)>20:raise ValueError('exact replay cap exceeded')
        trial_seed=int.from_bytes(hashlib.sha256(f'{seed}:{cid}'.encode()).digest()[:8],'big')
        a=baseline(n,host,seed=trial_seed,budget=budget,method='multistart')
        b=run(n,host,seed=trial_seed,budget=budget)
        optimum=replay(n,host)['optimum']
        if max(a['size'],b['size'])>optimum:raise RuntimeError('invalid optimum')
        records.append({'id':cid,'family':case['family'],'baseline':a['size'],'cycle_aware':b['size'],'optimum':optimum,'baseline_queries':a['queries'],'cycle_queries':b['queries']})
    return {'schema':'genesis-c4-cycle-aware-dev-v1','status':'PUBLIC_DEV_ONLY','budget':budget,'records':records,'cycle_wins':sum(r['cycle_aware']>r['baseline'] for r in records),'baseline_wins':sum(r['baseline']>r['cycle_aware'] for r in records),'ties':sum(r['baseline']==r['cycle_aware'] for r in records),'cpu_matched':False,'sealed':False,'promotion_allowed':False}
