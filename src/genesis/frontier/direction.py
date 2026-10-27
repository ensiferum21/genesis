"""Directions and the divergent operators (research plane; F1, `docs/OMEGA_FRONTIER.md` §4.1-§4.2).

A direction is a problem with an approach: {'problem', 'representation', 'method', 'params', 'op', 'parent'}.
Its descriptor (problem, representation, method, params) is what novelty and independence are measured on.

Operators (all draw from the domain's grammar, `approaches(problem)`, which may grow when a representation is
invented):
  * imagine:   k candidates uniformly from the grammar; keep the most novel (the largest minimum distance to the
               archive of every descriptor tried). "Never before used" is operational: a descriptor not in the
               archive (novelty above 0). Novelty search: Lehman and Stanley 2011.
  * mutate:    change one component of a direction (representation, method, one parameter, or the problem, to a
               neighbour);
  * recombine: components of two directions on the same problem (a's representation with b's method, and so on);
  * branch_out: open directions on problems a result revealed (`successors`), with the parent's approach.
"""


def descriptor(d):
    return (d['problem'], d['representation'], d['method'], tuple(sorted(d['params'].items())))


def make(problem, representation, method, params, op='seed', parent=None):
    return {'problem': problem, 'representation': representation, 'method': method, 'params': dict(params),
            'op': op, 'parent': parent}


def distance(a, b, grammar=None):
    """Hamming on (problem, representation, method) plus the mean normalised parameter distance."""
    da, db = descriptor(a), descriptor(b)
    dist = float(da[0] != db[0]) + float(da[1] != db[1]) + float(da[2] != db[2])
    pa, pb = dict(da[3]), dict(db[3])
    keys = sorted(set(pa) | set(pb))
    if keys:
        s = 0.0
        for k in keys:
            if k not in pa or k not in pb:
                s += 1.0
                continue
            vals = (grammar or {}).get('params', {}).get(k)
            if vals and pa[k] in vals and pb[k] in vals and len(vals) > 1:
                s += abs(vals.index(pa[k]) - vals.index(pb[k])) / (len(vals) - 1)
            else:
                s += float(pa[k] != pb[k])
        dist += s / len(keys)
    return dist


def novelty(d, archive, grammar=None):
    """The minimum distance from d to the archive's directions (inf for an empty archive)."""
    if not archive:
        return float('inf')
    return min(distance(d, a, grammar) for a in archive)


def sample(grammar, problem, rng):
    return make(problem, rng.choice(grammar['representation']), rng.choice(grammar['method']),
                {k: rng.choice(v) for k, v in sorted(grammar['params'].items())}, op='imagine')


def imagine(grammar, problem, rng, archive, k=8):
    cands = [sample(grammar, problem, rng) for _ in range(k)]
    scored = [(novelty(c, archive, grammar), i, c) for i, c in enumerate(cands)]
    best = max(scored, key=lambda x: (x[0], -x[1]))
    return best[2]


def mutate(d, grammar, rng, neighbours=()):
    out = make(d['problem'], d['representation'], d['method'], d['params'], op='mutate', parent=descriptor(d))
    choices = ['representation', 'method'] + [f'param:{k}' for k in sorted(grammar['params'])]
    if neighbours:
        choices.append('problem')
    what = rng.choice(choices)
    if what == 'representation':
        opts = [r for r in grammar['representation'] if r != d['representation']] or grammar['representation']
        out['representation'] = rng.choice(opts)
    elif what == 'method':
        opts = [m for m in grammar['method'] if m != d['method']] or grammar['method']
        out['method'] = rng.choice(opts)
    elif what == 'problem':
        out['problem'] = rng.choice(list(neighbours))
    else:
        k = what.split(':', 1)[1]
        opts = [v for v in grammar['params'][k] if v != d['params'].get(k)] or grammar['params'][k]
        out['params'][k] = rng.choice(opts)
    return out


def recombine(a, b, rng):
    """None unless a and b are on the same problem."""
    if a['problem'] != b['problem']:
        return None
    pick = lambda x, y: x if rng.random() < 0.5 else y
    out = make(a['problem'], pick(a['representation'], b['representation']), pick(a['method'], b['method']),
               {k: pick(a['params'].get(k), b['params'].get(k)) for k in sorted(set(a['params']) | set(b['params']))},
               op='recombine', parent=(descriptor(a), descriptor(b)))
    if descriptor(out) in (descriptor(a), descriptor(b)):            # force a real recombination when possible
        if a['representation'] != b['representation'] and a['method'] != b['method']:
            out['representation'], out['method'] = a['representation'], b['method']
    return out


def valid(d, grammar):
    return (d['representation'] in grammar['representation'] and d['method'] in grammar['method']
            and all(d['params'].get(k) in v for k, v in grammar['params'].items()))
