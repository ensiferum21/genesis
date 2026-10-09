"""PUBLIC DEV C4 optimization with equal counted feasibility-check budgets.

Counts calls to the same dual-checker oracle. This is NOT equal CPU time.
"""
import hashlib
import random
from c4_math_wedge import normalize, verify, exact
from c4_benchmark import multistart_greedy


def budgeted_multistart(n, host, *, seed, budget):
    host=normalize(n,host)
    if type(budget) is not int or budget < len(host) or type(seed) is not int:
        raise ValueError('budget must cover one complete greedy pass')
    rng=random.Random(seed); used=0; best=()
    if not host:return {"selected":(),"size":0,"checks":0,"budget":budget}
    while used+len(host)<=budget:
        order=list(host)
        if used: rng.shuffle(order)
        chosen=[]
        for e in order:
            used+=1
            if verify(n,host,chosen+[e]): chosen.append(e)
        if len(chosen)>len(best):best=tuple(sorted(chosen))
    return {'selected':best,'size':len(best),'checks':used,'budget':budget}


def budgeted_exchange(n, host, *, seed, budget):
    """Greedy initial solution then randomized 1-for-2 exchange and greedy refill.

    Every oracle call counts, including rejected proposals. Never exceeds budget.
    """
    host=normalize(n,host)
    if type(budget) is not int or budget < len(host) or type(seed) is not int:
        raise ValueError('budget must cover one complete greedy pass')
    rng=random.Random(seed); used=0; best=set(); chosen=set()
    def checked(edges):
        nonlocal used
        if used>=budget: return None
        used+=1
        return verify(n,host,tuple(edges))
    for e in host:
        if checked(chosen|{e}):chosen.add(e)
    best=chosen.copy()
    # A local move can remove one chosen edge, then insert two previously absent
    # edges, followed by a maximal greedy refill. Retain only strict gains.
    while used<budget:
        before=used
        removals=list(best); rng.shuffle(removals)
        improved=False
        for drop in removals:
            base=best-{drop}
            missing=list(set(host)-base);rng.shuffle(missing)
            for i,e1 in enumerate(missing):
                if e1==drop:continue
                for e2 in missing[i+1:]:
                    if e2==drop:continue
                    proposal=base|{e1,e2}
                    valid=checked(proposal)
                    if valid is None:break
                    if valid:
                        remaining=list(set(host)-proposal);rng.shuffle(remaining)
                        for e in remaining:
                            valid2=checked(proposal|{e})
                            if valid2 is None:break
                            if valid2:proposal.add(e)
                        if len(proposal)>len(best):
                            best=proposal;improved=True
                            break
                if improved or used>=budget:break
            if improved or used>=budget:break
        if not improved or used==before:break
    return {'selected':tuple(sorted(best)),'size':len(best),'checks':used,'budget':budget}


def compare(cases, *, budget=256, seed=4040):
    if not isinstance(cases,list) or not cases:raise ValueError('cases required')
    records=[];seen=set()
    for case in cases:
        cid=case['id']
        if not isinstance(cid,str) or not cid or cid in seen:raise ValueError('duplicate/invalid id')
        seen.add(cid)
        n=case['n'];host=normalize(n,case['host'])
        if len(host)>20:raise ValueError('exact cap')
        s=int.from_bytes(hashlib.sha256(f'{seed}:{cid}'.encode()).digest()[:8],'big')
        base=budgeted_multistart(n,host,seed=s,budget=budget)
        candidate=budgeted_exchange(n,host,seed=s,budget=budget)
        optimum=exact(n,host)['optimum']
        if not verify(n,host,base['selected']) or not verify(n,host,candidate['selected']):raise RuntimeError('invalid witness')
        if max(base['size'],candidate['size'])>optimum:raise RuntimeError('exceeds optimum')
        records.append({'id':cid,'family':case['family'],'host_edges':len(host),'optimum':optimum,
                        'multistart':base['size'],'exchange':candidate['size'],
                        'multistart_checks':base['checks'],'exchange_checks':candidate['checks']})
    return {'schema':'genesis-c4-budgeted-comparison-dev-v1','status':'PUBLIC_DEV_ONLY',
            'budget_per_arm':budget,'records':records,
            'exchange_wins':sum(x['exchange']>x['multistart'] for x in records),
            'multistart_wins':sum(x['exchange']<x['multistart'] for x in records),
            'ties':sum(x['exchange']==x['multistart'] for x in records),
            'matched_feasibility_check_cap':True,'matched_wall_time':False,
            'sealed':False,'promotion_allowed':False}
