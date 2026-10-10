"""DEV-only measured-resource C4 comparisons; no sealed or independent custody claim."""
import hashlib
import json
import time
import tracemalloc
from c4_math_wedge import normalize, verify
from c4_independent_replay import replay
from c4_budget_search import run as multistart
from c4_conflict_search import run as cycle_aware


def measure(fn, n, host, *, seed, budget):
    """Measure full algorithm invocation, including preprocessing; peak traced Python allocations.

    Tracemalloc is not process RSS. Timing is noisy and not a CPU-equivalence guarantee.
    """
    if tracemalloc.is_tracing():
        raise RuntimeError('external tracemalloc session active')
    tracemalloc.start()
    start_cpu=time.process_time_ns()
    start_wall=time.perf_counter_ns()
    try:
        result=fn(n,host,seed=seed,budget=budget)
        wall=time.perf_counter_ns()-start_wall
        cpu=time.process_time_ns()-start_cpu
        _,peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    selected=normalize(n,result['selected'])
    if type(result.get('size')) is not int or result['size'] != len(selected):
        raise RuntimeError('claimed size differs from normalized witness')
    if type(result.get('queries')) is not int or result['queries'] < 0:
        raise RuntimeError('invalid nonnegative query charge')
    if not verify(n,host,selected):
        raise RuntimeError('invalid solver witness')
    if result['queries']>budget:
        raise RuntimeError('query budget exceeded')
    return {'size':len(selected),'selected':selected,'queries':result['queries'],
            'query_accounting':'LEGACY_SELF_REPORTED_NOT_PROMOTABLE',
            'cpu_ns':cpu,'wall_ns':wall,'peak_traced_bytes':peak,
            'witness_sha256':hashlib.sha256(json.dumps(result['selected']).encode()).hexdigest()}


def compare(cases, *, seed=20261009, budget=60):
    if not isinstance(cases,list) or not cases or type(seed) is not int or type(budget) is not int or budget<1:
        raise ValueError('invalid comparison inputs')
    seen=set(); records=[]
    for case in cases:
        cid=case['id']
        if type(cid) is not str or not cid or cid in seen:raise ValueError('invalid case id')
        seen.add(cid)
        n=case['n']; host=normalize(n,case['host'])
        if len(host)>20:raise ValueError('independent replay cap exceeded')
        trial_seed=int.from_bytes(hashlib.sha256(f'{seed}:{cid}'.encode()).digest()[:8],'big')
        # Alternate arm order to reduce systematic first-run effects.
        arms=[('multistart',multistart),('cycle_aware',cycle_aware)]
        if len(records)%2:arms.reverse()
        results={name:measure(fn,n,host,seed=trial_seed,budget=budget) for name,fn in arms}
        optimum=replay(n,host)['optimum']
        if any(x['size']>optimum for x in results.values()):raise RuntimeError('replay contradiction')
        records.append({'id':cid,'family':case['family'],'n':n,'host_edges':len(host),
                        'optimum':optimum,'arm_order':[name for name,_ in arms],
                        **results})
    return {'schema':'genesis-c4-resource-benchmark-dev-v1','status':'PUBLIC_DEV_ONLY',
            'query_budget_per_arm':budget,'records':records,
            'cycle_wins':sum(x['cycle_aware']['size']>x['multistart']['size'] for x in records),
            'baseline_wins':sum(x['cycle_aware']['size']<x['multistart']['size'] for x in records),
            'ties':sum(x['cycle_aware']['size']==x['multistart']['size'] for x in records),
            'timing_method':'process_time_ns','memory_method':'tracemalloc_peak_python_allocations',
            'cpu_budget_matched':False,'sealed':False,'promotion_allowed':False}
