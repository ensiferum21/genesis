"""Candidate kind `mqlib-heuristic-v1` (registry v2, B20_R87): any heuristic of MQLib (Dunning, Gupta and Silberholz
2018), the reference library of 37 Max-Cut and QUBO heuristics, so that the best of them per host (the virtual best
solver) can be compared, not only BURER2002.

Why. Dunning et al. found that no single heuristic is best everywhere; a 2025 benchmark (arXiv 2507.22117) uses
BURER2002, PALUBECKIS2004bMST2 (iterated tabu search) and MERZ1999GLS (genetic algorithm with local search) as the
strongest classical baselines by instance class. Taking, per host, the best of several of them is an oracle no
single heuristic and no algorithm selector can beat. (MQLib's own hyper-heuristic, `-hh`, does not work in the pinned
build: it returns an empty cut immediately, apparently for want of its trained model; it is not used.)

Everything else is `mqlib-v1`'s (the same pinned binary, seeds modulo 65,536, the instance through a pipe, the cut
completed greedily, loud failure); this kind only widens the heuristic to MQLib's listed codes. Parameters (data
only): {heuristic, cpu_seconds}. Domain: triangle_free_host_v1.
"""
DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/mqlib_heuristic.py', 'candidate_kinds/mqlib.py')
HEURISTICS = ('BURER2002', 'DESOUSA2013', 'DUARTE2005', 'FESTA2002G', 'FESTA2002GPR', 'FESTA2002GVNS',
              'FESTA2002GVNSPR', 'FESTA2002VNS', 'FESTA2002VNSPR', 'LAGUNA2009CE', 'LAGUNA2009HCE', 'ALKHAMIS1998',
              'BEASLEY1998SA', 'BEASLEY1998TS', 'GLOVER1998a', 'GLOVER2010', 'HASAN2000GA', 'HASAN2000TS',
              'KATAYAMA2000', 'KATAYAMA2001', 'LODI1999', 'LU2010', 'MERZ1999CROSS', 'MERZ1999GLS', 'MERZ1999MUTATE',
              'MERZ2002GREEDY', 'MERZ2002GREEDYKOPT', 'MERZ2002KOPT', 'MERZ2002ONEOPT', 'MERZ2004',
              'PALUBECKIS2004bMST1', 'PALUBECKIS2004bMST2', 'PALUBECKIS2004bMST3', 'PALUBECKIS2004bMST4',
              'PALUBECKIS2004bMST5', 'PALUBECKIS2004bSTS', 'PALUBECKIS2006', 'PARDALOS2008')


def check_parameters(domain, params):
    from . import mqlib as MQ
    if domain not in DOMAINS:
        return f'mqlib-heuristic-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'heuristic', 'cpu_seconds'}:
        return 'mqlib-heuristic-v1 takes {heuristic, cpu_seconds}'
    if params['heuristic'] not in HEURISTICS:
        return 'heuristic must be one of MQLib\'s listed codes'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    got = MQ.binary_digest()
    if got != MQ.BINARY_SHA256:
        return f'the MQLib binary is missing or not the pinned build ({got})'
    return None


def solve(view, params, cpu_seconds, seed):
    from . import mqlib as MQ
    return MQ.solve(view, params, cpu_seconds, seed)
