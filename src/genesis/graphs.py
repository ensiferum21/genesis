"""Exact finite graph mathematics; no universal theorem or novelty claim.

Search producer uses forbidden-motif hitting sets. The optimum checker uses
vertex-neighbor incremental edge inclusion and never consumes producer search state.
"""
from functools import lru_cache
from itertools import combinations, permutations, product
from math import factorial, isqrt
from .common import digest
from .models import GraphTask


class SearchLimit(RuntimeError): pass


class CheckerDisagreement(RuntimeError):
    """Two checkers of one exact question disagree (W23): never a verdict. Carries the question, the
    input and both results so the caller can quarantine the subject (verification.reliability)."""
    def __init__(self,message,*,question,inputs,results):
        super().__init__(message)
        self.question=question;self.inputs=inputs;self.results=results


def normalize(n,edges):
    if type(n) is not int or not 0<=n<=63: raise ValueError('vertex bound')
    if not isinstance(edges,(list,tuple)): raise ValueError('edge collection')
    out=[]
    for e in edges:
        if not isinstance(e,(tuple,list)) or len(e)!=2: raise ValueError('edge shape')
        u,v=e
        if type(u) is not int or type(v) is not int or not 0<=u<n or not 0<=v<n or u==v:
            raise ValueError('edge endpoint')
        out.append((min(u,v),max(u,v)))
    if len(set(out))!=len(out): raise ValueError('duplicate edge')
    return tuple(sorted(out))


def neighbors(n,edges):
    a=[0]*n
    for u,v in edges:a[u]|=1<<v;a[v]|=1<<u
    return a


def forbidden_a(task,edges):
    """Explicit vertex/motif enumeration."""
    es=set(edges)
    if task.domain=='triangle_free_host_v1':
        return any((a,b) in es and (a,c) in es and (b,c) in es
                   for a,b,c in combinations(range(task.n),3))
    def edge(a,b):return (min(a,b),max(a,b)) in es
    return any(all(edge(x,y) for x,y in zip(order,order[1:]+order[:1]))
               for a,b,c,d in combinations(range(task.n),4)
               for order in ((a,b,c,d),(a,b,d,c),(a,c,b,d)))


def forbidden_b(task,edges):
    """Independent bitset neighbor criterion."""
    a=neighbors(task.n,edges)
    if task.domain=='triangle_free_host_v1':
        return any(a[u]&a[v] for u,v in edges)
    return any((a[u]&a[v]).bit_count()>=2 for u in range(task.n) for v in range(u+1,task.n))


def check_witness(task,edges):
    es=normalize(task.n,edges)
    if not set(es)<=set(task.edges):raise ValueError('witness edge outside host')
    a,b=forbidden_a(task,es),forbidden_b(task,es)
    if a!=b:raise CheckerDisagreement('CHECKER_ERROR: predicate disagreement',question='motif_free',
                                      inputs={'task':task.model_dump(mode='json'),'edges':[list(e) for e in es]},
                                      results={'explicit-motifs-v1':not a,'neighbor-bitsets-v1':not b})
    if a:raise ValueError('forbidden motif in witness')
    return {'status':'WITNESS_VALID','selected':es,'value':len(es),
            'task_sha256':digest(task.model_dump(mode='json')),
            'checkers':['explicit-motifs-v1','neighbor-bitsets-v1']}


def motifs(task):
    index={e:i for i,e in enumerate(task.edges)}; masks=set()
    k=3 if task.domain=='triangle_free_host_v1' else 4
    for vertices in combinations(range(task.n),k):
        if k==3: orders=(vertices,)
        else:
            a,b,c,d=vertices;orders=((a,b,c,d),(a,b,d,c),(a,c,b,d))
        for order in orders:
            edges=[tuple(sorted(e)) for e in zip(order,order[1:]+order[:1])]
            if all(e in index for e in edges):masks.add(sum(1<<index[e] for e in edges))
    return tuple(sorted(masks))


def universal_upper(task):
    n=task.n;m=len(task.edges)
    if task.domain=='triangle_free_host_v1':
        # Keep the reference contract: Mantel certificate only on complete hosts.
        return {'value':n*n//4 if m==n*(n-1)//2 else m,
                'method':'Mantel-complete-host' if m==n*(n-1)//2 else 'host-edge-count'}
    # 4m^2 - 2nm <= n^2(n-1), using exact integer arithmetic. Lean-checked since CRPD-2b
    # (invention.pair_count); v1 bundles still record it as an unchecked THEOREM bound, bundle v2
    # can carry it as PAIR_COUNT_LEAN with the theory package.
    bound=(n+n*isqrt(max(0,4*n-3)))//4
    while 4*(bound+1)**2-2*n*(bound+1)<=n*n*(n-1):bound+=1
    while 4*bound**2-2*n*bound>n*n*(n-1):bound-=1
    return {'value':min(m,max(0,bound)),'method':'C4-pair-count-quadratic'}


def exact_producer(task,max_edges=24,max_nodes=500000):
    if len(task.edges)>max_edges:raise SearchLimit('exact edge cap')
    cycles=motifs(task);nodes=0
    @lru_cache(None)
    def hit(remaining):
        nonlocal nodes
        nodes+=1
        if nodes>max_nodes:raise SearchLimit('exact node cap')
        if not remaining:return 0
        first=remaining[0]; best=None
        while first:
            bit=first & -first;first^=bit
            found=bit|hit(tuple(c for c in remaining if not c&bit))
            if best is None or found.bit_count()<best.bit_count():best=found
        return best
    deleted=hit(cycles)
    selected=tuple(e for i,e in enumerate(task.edges) if not deleted>>i&1)
    check_witness(task,selected)
    return {'selected':selected,'value':len(selected),'nodes':nodes,'method':'motif-hitting-set'}


def exact_checker(task,max_edges=24,max_nodes=1000000):
    """Separate include/exclude recursion, with incremental neighbor constraints."""
    if len(task.edges)>max_edges:raise SearchLimit('checker edge cap')
    es=task.edges;adj=[0]*task.n;best=();nodes=0
    def dfs(i,chosen):
        nonlocal best,nodes
        nodes+=1
        if nodes>max_nodes:raise SearchLimit('checker node cap')
        if len(chosen)+len(es)-i<=len(best):return
        if i==len(es):best=tuple(chosen);return
        u,v=es[i]
        if task.domain=='triangle_free_host_v1':valid=not(adj[u]&adj[v])
        else:
            # Adding uv creates a C4 iff there was a three-edge u-to-v path.
            valid=True
            for x in range(task.n):
                if adj[u]>>x&1 and adj[x]&adj[v]:valid=False;break
        if valid:
            adj[u]|=1<<v;adj[v]|=1<<u
            dfs(i+1,chosen+[es[i]])
            adj[u]&=~(1<<v);adj[v]&=~(1<<u)
        dfs(i+1,chosen)
    dfs(0,[])
    check_witness(task,best)
    return {'selected':best,'value':len(best),'nodes':nodes,'method':'incremental-neighbor-branch-bound'}


def certified_optimum(task,max_edges=24):
    producer=exact_producer(task,max_edges)
    checker=exact_checker(task,max_edges)
    if producer['value']!=checker['value']:
        raise CheckerDisagreement('CHECKER_ERROR: exact optimizers disagree',question='max_motif_free_edges',
                                  inputs={'task':task.model_dump(mode='json')},
                                  results={'motif-hitting-set':producer['value'],
                                           'incremental-branch-bound':checker['value']})
    return {'status':'FINITE_CERTIFIED','value':checker['value'],'producer':producer,'checker':checker,
            'scope':'this finite host only','formal_proof':False,'novelty':'UNKNOWN'}


def components(task):
    adj=neighbors(task.n,task.edges);remaining=set(range(task.n));out=[]
    while remaining:
        seed=min(remaining);todo=[seed];comp=set()
        while todo:
            u=todo.pop()
            if u in comp:continue
            comp.add(u);remaining.discard(u)
            todo.extend(v for v in range(task.n) if adj[u]>>v&1 and v not in comp)
        out.append(tuple(sorted(comp)))
    return tuple(out)


def canonical_graph(task,permutation_cap=200000):
    """Exact isomorphism fingerprint under a bounded color-class enumeration.

    Beyond the bound return UNSETTLED by raising, never a false freshness pass.
    Family labels and task IDs cannot alter the identity. Domain is deliberately
    excluded so the same host cannot cross C4/triangle split boundaries unnoticed.
    """
    adj=neighbors(task.n,task.edges);colors=[x.bit_count() for x in adj]
    for _ in range(task.n):
        sig=[(colors[u],tuple(sorted(colors[v] for v in range(task.n) if adj[u]>>v&1)))
             for u in range(task.n)]
        table={s:i for i,s in enumerate(sorted(set(sig)))}
        new=[table[s] for s in sig]
        if new==colors:break
        colors=new
    cells=[tuple(i for i,c in enumerate(colors) if c==color) for color in sorted(set(colors))]
    # Isolated vertices are interchangeable and contribute no edge choices.
    choices=[];count=1
    for cell in cells:
        if cell and adj[cell[0]]==0:choices.append((cell,));continue
        count*=factorial(len(cell))
        if count>permutation_cap:raise SearchLimit('isomorphism screening needs external adjudication')
        choices.append(permutations(cell))
    best=None
    for groups in product(*choices):
        order=sum((tuple(g) for g in groups),());mapping={v:i for i,v in enumerate(order)}
        encoded=tuple(sorted(tuple(sorted((mapping[u],mapping[v]))) for u,v in task.edges))
        if best is None or encoded<best:best=encoded
    return digest({'n':task.n,'edges':best or ()})


def relabel(task,order):
    if tuple(sorted(order))!=tuple(range(task.n)):raise ValueError('not a permutation')
    es=normalize(task.n,[(order[u],order[v]) for u,v in task.edges])
    return GraphTask(task_id=task.task_id,domain=task.domain,n=task.n,edges=es,family=task.family,split=task.split)


def check_ghost(task,witness,bound):
    if type(bound) is not int:raise ValueError('integer bound required')
    checked=check_witness(task,witness)
    if checked['value']>bound:
        return {'status':'GHOST_FOUND','refuted_statement':f'optimum <= {bound}','check':checked}
    return {'status':'UNSETTLED','no_ghost_found':True,'proof':False}
