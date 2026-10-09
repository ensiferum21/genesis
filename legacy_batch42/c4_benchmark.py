"""Reproducible DEV-only C4 benchmark; no sealed or independent-custody claims."""
import hashlib
import json
import random
from itertools import combinations
from c4_math_wedge import normalize, verify, exact
from c4_independent_replay import replay


def ordered_greedy(n, host, order):
    host = normalize(n, host)
    if tuple(sorted(order)) != host or len(order) != len(host):
        raise ValueError('order must be a permutation of host edges')
    chosen = []
    for edge in order:
        if verify(n, host, chosen + [edge]):
            chosen.append(edge)
    return tuple(sorted(chosen))


def multistart_greedy(n, host, *, seed, restarts=32):
    """Fairer baseline: fixed number of independently shuffled greedy starts."""
    host = normalize(n, host)
    if type(seed) is not int or type(restarts) is not int or not 1 <= restarts <= 1024:
        raise ValueError('invalid seed/restarts')
    rng = random.Random(seed)
    best = ordered_greedy(n, host, host)
    for _ in range(restarts):
        order = list(host)
        rng.shuffle(order)
        candidate = ordered_greedy(n, host, order)
        if len(candidate) > len(best):
            best = candidate
    return {'selected':best,'size':len(best),'starts':restarts+1}


def fresh_suite(seed=20261009, cases=24):
    """Deterministic graph generator, deliberately PUBLIC/DEV, not sealed."""
    if type(seed) is not int or type(cases) is not int or not 1 <= cases <= 200:
        raise ValueError('invalid suite parameters')
    rng = random.Random(seed)
    suite = []
    for i in range(cases):
        n = 5 + i % 3
        edges = list(combinations(range(n), 2))
        rng.shuffle(edges)
        m = min(len(edges), 10 + (i * 7) % 11)
        host = normalize(n, edges[:m])
        suite.append({'case':f'dev-{i:03d}', 'n':n, 'host':host,
                      'family':f'n{n}-density{m // 5}'})
    return suite


def evaluate(suite, *, baseline_seed=707, restarts=32):
    if not isinstance(suite, list) or not suite:
        raise ValueError('nonempty suite required')
    ids = [x['case'] for x in suite]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate case IDs')
    results = []
    for item in suite:
        n, host = item['n'], normalize(item['n'], item['host'])
        if len(host) > 20:
            raise ValueError('host too large for independent exact verification')
        trial_seed = int.from_bytes(hashlib.sha256(f"{baseline_seed}:{item['case']}".encode()).digest()[:8], 'big')
        base = multistart_greedy(n, host, seed=trial_seed, restarts=restarts)
        candidate = exact(n, host)
        independent = replay(n, host)
        if candidate['optimum'] != independent['optimum'] or not verify(n, host, base['selected']):
            raise RuntimeError('exact solver / independent replay / baseline disagreement')
        results.append({'case':item['case'],'family':item['family'],'n':n,'host_edges':len(host),
                        'baseline':base['size'],'exact':candidate['optimum'],
                        'improvement':candidate['optimum']-base['size'],
                        'candidate_search_nodes':candidate['search_nodes'],
                        'independent_replay_subproblems':independent['subproblems']})
    canonical = json.dumps(suite, sort_keys=True, separators=(',', ':')).encode()
    return {'schema':'genesis-c4-dev-comparison-v1','suite_sha256':hashlib.sha256(canonical).hexdigest(),
            'status':'PUBLIC_DEV_NOT_PROSPECTIVE','restarts_per_case':restarts,
            'cases':results,'candidate_wins':sum(x['improvement']>0 for x in results),
            'ties':sum(x['improvement']==0 for x in results),
            'baseline_wins':sum(x['improvement']<0 for x in results),
            'independent_exact_replay':True,'external_replication':False,
            'sealed_benchmark':False,'promotion_allowed':False}
