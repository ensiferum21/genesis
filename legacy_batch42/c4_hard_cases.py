"""Public DEV-only search for C4 instances that challenge multistart greedy.

No hidden evaluation, formal certificate, or scientific novelty claim.
"""
import hashlib
import json
import random
from itertools import combinations
from c4_math_wedge import normalize, exact, verify
from c4_independent_replay import replay
from c4_benchmark import multistart_greedy


def sample_cases(*, seed=20261009, count=60, restarts=32):
    if type(seed) is not int or type(count) is not int or not 1 <= count <= 200 or type(restarts) is not int or not 1 <= restarts <= 1024:
        raise ValueError('invalid search parameters')
    rng = random.Random(seed)
    cases = []
    for i in range(count):
        n = 6 + i % 3
        all_edges = list(combinations(range(n), 2))
        # Alternate random and deliberately bipartite hosts; the latter are
        # rich in C4 obstructions and can expose greedy ordering sensitivity.
        if i % 2:
            cut = n // 2
            all_edges = [(u,v) for u,v in all_edges if u < cut <= v]
        rng.shuffle(all_edges)
        m = min(len(all_edges), 12 + i % 9)
        host = normalize(n, all_edges[:m])
        cases.append({'id':f'public-dev-{i:03d}', 'n':n, 'host':host,
                      'family':'bipartite' if i % 2 else 'random'})
    return cases


def compare(cases, *, seed=112358, restarts=32):
    if not isinstance(cases,list) or not cases:
        raise ValueError('nonempty cases required')
    ids=set(); records=[]
    for case in cases:
        cid=case['id']
        if not isinstance(cid,str) or not cid or cid in ids:
            raise ValueError('invalid or duplicate id')
        ids.add(cid)
        n=case['n']; host=normalize(n,case['host'])
        if len(host)>20:
            raise ValueError('host too large for exact replay')
        trial_seed=int.from_bytes(hashlib.sha256(f'{seed}:{cid}'.encode()).digest()[:8],'big')
        baseline=multistart_greedy(n,host,seed=trial_seed,restarts=restarts)
        optimal=exact(n,host)
        checked=replay(n,host)
        if optimal['optimum']!=checked['optimum'] or not verify(n,host,baseline['selected']):
            raise RuntimeError('independent exact replay mismatch')
        records.append({'id':cid,'family':case['family'],'n':n,'host':[list(e) for e in host],
                        'host_edges':len(host),'greedy_size':baseline['size'],
                        'exact_size':optimal['optimum'],'gap':optimal['optimum']-baseline['size'],
                        'exact_nodes':optimal['search_nodes'],'replay_subproblems':checked['subproblems']})
    payload=json.dumps(cases,sort_keys=True,separators=(',',':')).encode()
    return {'schema':'genesis-c4-public-hard-search-v1','status':'PUBLIC_DEV_ONLY',
            'cases_sha256':hashlib.sha256(payload).hexdigest(),
            'restarts':restarts,'count':len(records),
            'greedy_suboptimal_count':sum(x['gap']>0 for x in records),
            'largest_gap':max(x['gap'] for x in records),'records':records,
            'independent_exact_crosscheck':True,'matched_compute':False,
            'sealed':False,'promotion_allowed':False}
