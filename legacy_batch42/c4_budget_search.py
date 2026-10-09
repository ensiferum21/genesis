"""DEV-only matched feasibility-query comparison on C4-free host graphs.

A query is one complete C4-freeness predicate evaluation. This is NOT a
matched CPU-time comparison, and constructing the cycle index is uncharged.
"""
import hashlib
import random
from c4_math_wedge import normalize, verify
from c4_independent_replay import cycle_masks, replay


def run(n, edges, *, seed=0, budget=660, method='multistart'):
    host = normalize(n, edges)
    if type(seed) is not int or type(budget) is not int or not 1 <= budget <= 100000:
        raise ValueError('invalid budget or seed')
    if method not in ('multistart', 'swap'):
        raise ValueError('unknown method')
    cycles = cycle_masks(n, host)
    m = len(host)
    rng = random.Random(seed)
    queries = 0
    best = 0
    def valid(mask):
        nonlocal queries
        if queries >= budget:
            return None
        queries += 1
        return not any((mask & c) == c for c in cycles)
    # Both methods use the same initial greedy and the same random stream.
    first = True
    while queries < budget:
        order = list(range(m))
        if not first:
            rng.shuffle(order)
        first = False
        mask = 0
        for j in order:
            candidate = mask | (1 << j)
            ok = valid(candidate)
            if ok is None:
                break
            if ok:
                mask = candidate
        if mask.bit_count() > best.bit_count():
            best = mask
        if method == 'swap' and queries < budget:
            # Delete one chosen edge, then add up to two absent edges.
            # Each candidate consumes one feasibility query, even if trivial.
            changed = True
            while changed and queries < budget:
                changed = False
                chosen = [j for j in range(m) if mask >> j & 1]
                missing = [j for j in range(m) if not mask >> j & 1]
                rng.shuffle(chosen)
                rng.shuffle(missing)
                for drop in chosen:
                    for i, add1 in enumerate(missing):
                        for add2 in missing[i+1:]:
                            trial = (mask & ~(1 << drop)) | (1 << add1) | (1 << add2)
                            ok = valid(trial)
                            if ok is None:
                                break
                            if ok:
                                mask = trial
                                changed = True
                                break
                        if changed or queries >= budget: break
                    if changed or queries >= budget: break
            if mask.bit_count() > best.bit_count():
                best = mask
        if m == 0 or best.bit_count() == m:
            break
    selected = tuple(e for i, e in enumerate(host) if best >> i & 1)
    if not verify(n, host, selected):
        raise RuntimeError('invalid witness')
    return {'size':len(selected), 'selected':selected, 'queries':queries,
            'budget':budget, 'method':method, 'cost_metric':'C4_feasibility_queries',
            'cpu_matched':False}


def compare(cases, *, seed=703, budget=660):
    if not isinstance(cases, list) or not cases:
        raise ValueError('nonempty cases required')
    ids = set()
    records = []
    for case in cases:
        cid = case['id']
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError('duplicate or invalid case ID')
        ids.add(cid)
        n, host = case['n'], normalize(case['n'], case['host'])
        if len(host) > 20:
            raise ValueError('exact replay capped at 20 edges')
        trial_seed = int.from_bytes(hashlib.sha256(f'{seed}:{cid}'.encode()).digest()[:8], 'big')
        a = run(n, host, seed=trial_seed, budget=budget, method='multistart')
        b = run(n, host, seed=trial_seed, budget=budget, method='swap')
        optimum = replay(n, host)['optimum']
        if a['size'] > optimum or b['size'] > optimum:
            raise RuntimeError('heuristic exceeds certified optimum')
        records.append({'id':cid, 'family':case['family'], 'optimum':optimum,
                        'multistart':a['size'], 'swap':b['size'],
                        'multistart_queries':a['queries'], 'swap_queries':b['queries']})
    return {'schema':'genesis-c4-query-budget-dev-v1','status':'PUBLIC_DEV_ONLY',
            'budget_per_arm':budget,'records':records,
            'swap_wins':sum(x['swap']>x['multistart'] for x in records),
            'multistart_wins':sum(x['multistart']>x['swap'] for x in records),
            'ties':sum(x['swap']==x['multistart'] for x in records),
            'sealed':False,'matched_cpu':False,'promotion_allowed':False}
