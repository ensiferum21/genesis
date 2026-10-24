"""Problem families for the Problem Compiler, each with its own generator, verifier and natural encodings.

A family turns an instance into a BQP (`compile`) and maps a BQP assignment back to the family's answer (`decode`).
Its VERIFIER checks an answer against the instance alone and scores it; it never trusts the compiler. Where a
specialist encoding is the natural one (the classic MaxSAT encoding of a problem), the family gives it (`wcnf`), so a
MaxSAT solver is judged on the encoding its community would use. Every family is to be MINIMISED or MAXIMISED as
stated in SENSE; `score` is in the family's own terms.

  * `mis`: maximum independent set of a graph (G(n, d/n)). Answer: a vertex set; valid iff independent; score = size.
  * `coloring`: k-colouring with fewest conflicts (G(n, d/n), k colours). Answer: a colour per vertex; score = the
    number of edges whose ends share a colour (to minimise; 0 is a proper colouring).
  * `max2sat`: random 2-CNF (n variables, m clauses). Answer: an assignment; score = satisfied clauses.
  * `maxcut`: unweighted max-cut (G(n, d/n)). Answer: a side per vertex; score = cut edges. The control: the native
    problem of Genesis's engine.
Instances are reproducible from (family, seed, params).
"""
import random

SENSE = {'mis': 'max', 'coloring': 'min', 'max2sat': 'max', 'maxcut': 'max'}


def _graph(rng, n, d):
    E = set()
    m = round(n * d / 2)
    while len(E) < m:
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            E.add((min(u, v), max(u, v)))
    return sorted(E)


def generate(family, seed, params):
    rng = random.Random(f'{family}|{seed}|{sorted(params.items())}')
    if family in ('mis', 'coloring', 'maxcut'):
        inst = {'n': params['n'], 'edges': [list(e) for e in _graph(rng, params['n'], params['d'])]}
        if family == 'coloring':
            inst['k'] = params['k']
        return inst
    if family == 'max2sat':
        n, m = params['n'], params['m']
        cls = []
        for _ in range(m):
            a, b = rng.sample(range(1, n + 1), 2)
            cls.append([a * rng.choice((1, -1)), b * rng.choice((1, -1))])
        return {'n': n, 'clauses': cls}
    raise ValueError(f'unknown family {family!r}')


def compile(family, inst):
    """The instance as a BQP to MINIMISE (for a maximisation family, minus its score plus a constant)."""
    if family == 'mis':
        return {'n': inst['n'], 'constant': 0, 'linear': [[i, -1] for i in range(inst['n'])], 'quadratic': [],
                'hard': {'exclusive': [list(e) for e in inst['edges']]}}
    if family == 'coloring':
        n, k = inst['n'], inst['k']
        var = lambda v, c: v * k + c                       # noqa: E731
        quad = [[var(u, c), var(v, c), 1] for u, v in inst['edges'] for c in range(k)]
        quad.sort()
        return {'n': n * k, 'constant': 0, 'linear': [], 'quadratic': quad,
                'hard': {'one': [[var(v, c) for c in range(k)] for v in range(n)]}}
    if family == 'max2sat':
        # a violated clause (l1 v l2) costs 1: (1 - L1)(1 - L2), with L = x or 1 - x
        lin, quad, const = {}, {}, 0
        for a, b in inst['clauses']:
            # 1 - L = (1 - x) if positive else x  ->  write 1 - L as (c0 + c1 x)
            terms = []
            for lit in (a, b):
                i = abs(lit) - 1
                terms.append((1, -1, i) if lit > 0 else (0, 1, i))
            (p0, p1, i), (q0, q1, j) = terms
            const += p0 * q0
            lin[i] = lin.get(i, 0) + p1 * q0
            lin[j] = lin.get(j, 0) + q1 * p0
            key = (min(i, j), max(i, j))
            quad[key] = quad.get(key, 0) + p1 * q1
        return {'n': inst['n'], 'constant': const, 'linear': [[i, a] for i, a in sorted(lin.items()) if a],
                'quadratic': [[i, j, b] for (i, j), b in sorted(quad.items()) if b], 'hard': {}}
    if family == 'maxcut':
        n = inst['n']
        lin, quad = {}, []
        for u, v in inst['edges']:                          # an edge is cut iff x_u + x_v - 2 x_u x_v = 1
            lin[u] = lin.get(u, 0) - 1
            lin[v] = lin.get(v, 0) - 1
            quad.append([u, v, 2])
        return {'n': n, 'constant': 0, 'linear': [[i, a] for i, a in sorted(lin.items())], 'quadratic': sorted(quad),
                'hard': {}}
    raise ValueError(f'unknown family {family!r}')


def decode(family, inst, x):
    if family == 'mis':
        return {'vertices': [i for i in range(inst['n']) if x[i]]}
    if family == 'coloring':
        k = inst['k']
        col = []
        for v in range(inst['n']):
            on = [c for c in range(k) if x[v * k + c]]
            col.append(on[0] if len(on) == 1 else -1)
        return {'colours': col}
    if family == 'max2sat':
        return {'assignment': [int(x[i]) for i in range(inst['n'])]}
    if family == 'maxcut':
        return {'side': [int(x[i]) for i in range(inst['n'])]}
    raise ValueError(f'unknown family {family!r}')


def verify(family, inst, ans):
    """(valid, score, reason): the family's own check of an answer, from the instance alone."""
    try:
        if family == 'mis':
            S = ans['vertices']
            if len(set(S)) != len(S) or any(not (0 <= v < inst['n']) for v in S):
                return False, None, 'not a vertex set'
            s = set(S)
            if any(u in s and v in s for u, v in inst['edges']):
                return False, None, 'not independent'
            return True, len(S), ''
        if family == 'coloring':
            col = ans['colours']
            if len(col) != inst['n'] or any(not (type(c) is int and 0 <= c < inst['k']) for c in col):
                return False, None, 'not a colouring with k colours'
            return True, sum(col[u] == col[v] for u, v in inst['edges']), ''
        if family == 'max2sat':
            asg = ans['assignment']
            if len(asg) != inst['n'] or set(asg) - {0, 1}:
                return False, None, 'not an assignment'
            sat = sum(any((asg[abs(l) - 1] == 1) == (l > 0) for l in c) for c in inst['clauses'])
            return True, sat, ''
        if family == 'maxcut':
            side = ans['side']
            if len(side) != inst['n'] or set(side) - {0, 1}:
                return False, None, 'not a cut'
            return True, sum(side[u] != side[v] for u, v in inst['edges']), ''
    except (KeyError, TypeError, IndexError) as e:
        return False, None, f'malformed answer: {e}'
    raise ValueError(f'unknown family {family!r}')


def wcnf(family, inst):
    """The natural MaxSAT encoding (hard clauses, soft unit-weight clauses, n_vars) and how to read an assignment of
    its variables back as an answer, or None if the generic one is to be used."""
    if family == 'mis':
        n = inst['n']
        return ([[-(u + 1), -(v + 1)] for u, v in inst['edges']], [(1, [i + 1]) for i in range(n)], n)
    if family == 'coloring':
        n, k = inst['n'], inst['k']
        var = lambda v, c: v * k + c + 1                  # noqa: E731
        hard = [[var(v, c) for c in range(k)] for v in range(n)]
        hard += [[-var(v, c), -var(v, d)] for v in range(n) for c in range(k) for d in range(c + 1, k)]
        soft = [(1, [-var(u, c), -var(v, c)]) for u, v in inst['edges'] for c in range(k)]
        return hard, soft, n * k
    if family == 'max2sat':
        return [], [(1, list(c)) for c in inst['clauses']], inst['n']
    if family == 'maxcut':
        soft = []
        for u, v in inst['edges']:
            soft += [(1, [u + 1, v + 1]), (1, [-(u + 1), -(v + 1)])]
        return [], soft, inst['n']
    return None
