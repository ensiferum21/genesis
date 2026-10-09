"""Independent C4 optimality replay using a cycle-hitting-set recurrence.

A C4-free edge set is the complement of a set of deleted edges that hits
all 4-cycles. This module does not call the candidate optimizer.
"""
from itertools import combinations
from functools import lru_cache
from c4_math_wedge import normalize, c4_by_cycles

MAX_REPLAY_EDGES = 20


def cycle_masks(n, host):
    host = normalize(n, host)
    index = {edge: i for i, edge in enumerate(host)}
    masks = set()
    for vertices in combinations(range(n), 4):
        a, b, c, d = vertices
        for order in ((a,b,c,d), (a,b,d,c), (a,c,b,d)):
            edges = [(min(x,y),max(x,y)) for x,y in zip(order,order[1:]+order[:1])]
            if all(e in index for e in edges):
                masks.add(sum(1 << index[e] for e in edges))
    return tuple(sorted(masks))


def replay(n, host):
    host = normalize(n, host)
    if len(host) > MAX_REPLAY_EDGES:
        raise ValueError('independent replay edge cap exceeded')
    cycles = cycle_masks(n, host)
    # Minimum hitting set over forbidden 4-edge sets, memoized by remaining cycles.
    @lru_cache(None)
    def hit(remaining):
        if not remaining:
            return (0, 0)
        first = remaining[0]
        best = (len(host) + 1, 0)
        bits = first
        while bits:
            bit = bits & -bits
            bits ^= bit
            cost, deleted = hit(tuple(c for c in remaining if not c & bit))
            if cost + 1 < best[0]:
                best = (cost + 1, deleted | bit)
        return best
    deletions, deleted_mask = hit(cycles)
    kept = tuple(e for i,e in enumerate(host) if not deleted_mask >> i & 1)
    if c4_by_cycles(n, kept):
        raise RuntimeError('replay witness contains a C4')
    return {'schema':'genesis-c4-hitting-set-replay-v1','n':n,'host':host,
            'optimum':len(host)-deletions,'selected':kept,
            'cycle_count':len(cycles),'subproblems':hit.cache_info().currsize,
            'method':'minimum-C4-hitting-set','formal_proof':False}


def cross_check(result):
    if not isinstance(result, dict) or type(result.get('n')) is not int:
        raise ValueError('invalid candidate result')
    n = result['n']
    host = normalize(n, result['host'])
    selected = normalize(n, result['selected'])
    if not set(selected).issubset(host) or c4_by_cycles(n, selected):
        return False
    if type(result.get('optimum')) is not int or result['optimum'] != len(selected):
        return False
    return replay(n, host)['optimum'] == result['optimum']
