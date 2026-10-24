"""Binary quadratic programs with hard constraints (the Problem Compiler's intermediate form).

A BQP over x in {0, 1}^n:
    minimise  constant + sum_i a_i x_i + sum_{i<j} b_ij x_i x_j        (integer coefficients)
    subject to hard constraints of four kinds:
        exclusive [i, j]:   x_i + x_j <= 1          (not both)
        cover [i, j]:       x_i + x_j >= 1          (at least one)
        one [S]:            sum_{i in S} x_i = 1     (exactly one)
        atmostone [S]:      sum_{i in S} x_i <= 1
As data: {'n', 'constant', 'linear': [[i, a]], 'quadratic': [[i, j, b]] (i < j), 'hard': {kind: [...]}}.

Forms, each exact for feasible points:
  * `penalised(bqp, P)`: one unconstrained QUBO, each violated constraint costing P (exclusive: P x_i x_j; cover:
    P (1 - x_i)(1 - x_j); one: P (1 - sum x)^2 = P (1 - sum x + 2 sum_{i<j} x_i x_j); atmostone: P sum_{i<j} x_i x_j).
    `default_penalty` is 1 + the largest change in the objective one flip can make, so on the penalised QUBO no
    single flip that breaks a constraint pays (the usual bound); the answer is still repaired and verified.
  * `to_maxcut(qubo)`: the Ising form (x = (1 + s) / 2, scaled by 4: J_ij = b_ij, h_i = 2 a_i + sum_j b_ij) as a
    weighted max-cut instance on n + 1 vertices (vertex n is the reference spin): minimising the QUBO is maximising
    the cut; x_i = 1 iff vertex i is on the reference's side. (The textbook reduction; e.g. Lucas 2014.)
  * `to_milp(bqp)`: products linearised exactly (b > 0: y >= x_i + x_j - 1; b < 0: y <= x_i, y <= x_j), the hard
    constraints as linear rows.
  * `to_wcnf(bqp)`: weighted partial MaxSAT, exact: hard clauses for the constraints; soft clauses for the objective
    (a > 0: (-x_i) of weight a; a < 0: (x_i) of weight -a; b > 0: (-x_i v -x_j) of weight b; b < 0: an auxiliary y
    with hard (-y v x_i), (-y v x_j) and soft (y) of weight -b). Its cost plus `wcnf_offset` is the objective.
`evaluate` gives the objective and the violated constraints of an assignment; `repair` makes an assignment feasible
greedily, constraint kind by kind (cheapest fix first), for answers from penalised forms.
"""
from itertools import combinations

KINDS = ('exclusive', 'cover', 'one', 'atmostone')


def check(bqp):
    """None, or why `bqp` is malformed."""
    if not isinstance(bqp, dict) or set(bqp) != {'n', 'constant', 'linear', 'quadratic', 'hard'}:
        return "a BQP is {'n', 'constant', 'linear', 'quadratic', 'hard'}"
    n = bqp['n']
    if type(n) is not int or n < 1:
        return 'n must be a positive integer'
    for i, a in bqp['linear']:
        if not (type(i) is int and 0 <= i < n and type(a) is int):
            return f'bad linear term {[i, a]}'
    seen = set()
    for i, j, b in bqp['quadratic']:
        if not (type(i) is int and type(j) is int and 0 <= i < j < n and type(b) is int) or (i, j) in seen:
            return f'bad quadratic term {[i, j, b]}'
        seen.add((i, j))
    if set(bqp['hard']) - set(KINDS):
        return f'hard constraint kinds are {KINDS}'
    for kind, items in bqp['hard'].items():
        for it in items:
            if kind in ('exclusive', 'cover') and not (len(it) == 2 and it[0] != it[1]):
                return f'{kind} constrains a pair'
            if any(not (type(v) is int and 0 <= v < n) for v in it) or len(set(it)) != len(it) or not it:
                return f'bad {kind} constraint {it}'
    return None


def evaluate(bqp, x):
    """(objective, number of violated constraints) of the 0/1 sequence x."""
    f = bqp['constant'] + sum(a * x[i] for i, a in bqp['linear']) + sum(b * x[i] * x[j] for i, j, b in bqp['quadratic'])
    bad = 0
    h = bqp['hard']
    bad += sum(1 for i, j in h.get('exclusive', []) if x[i] and x[j])
    bad += sum(1 for i, j in h.get('cover', []) if not x[i] and not x[j])
    bad += sum(1 for S in h.get('one', []) if sum(x[i] for i in S) != 1)
    bad += sum(1 for S in h.get('atmostone', []) if sum(x[i] for i in S) > 1)
    return f, bad


def _merge(n, constant, lin, quad):
    L = {}
    for i, a in lin:
        L[i] = L.get(i, 0) + a
    Q = {}
    for i, j, b in quad:
        k = (min(i, j), max(i, j))
        Q[k] = Q.get(k, 0) + b
    return {'n': n, 'constant': constant, 'linear': [[i, a] for i, a in sorted(L.items()) if a],
            'quadratic': [[i, j, b] for (i, j), b in sorted(Q.items()) if b], 'hard': {}}


def default_penalty(bqp):
    reach = [0] * bqp['n']
    for i, a in bqp['linear']:
        reach[i] += abs(a)
    for i, j, b in bqp['quadratic']:
        reach[i] += abs(b)
        reach[j] += abs(b)
    return 1 + max(reach)


def penalised(bqp, P):
    """The unconstrained QUBO with penalty P per violated constraint."""
    lin, quad, c = list(bqp['linear']), list(bqp['quadratic']), bqp['constant']
    h = bqp['hard']
    for i, j in h.get('exclusive', []):
        quad.append([i, j, P])
    for i, j in h.get('cover', []):
        c += P
        lin += [[i, -P], [j, -P]]
        quad.append([i, j, P])
    for S in h.get('one', []):
        c += P
        lin += [[i, -P] for i in S]
        quad += [[i, j, 2 * P] for i, j in combinations(S, 2)]
    for S in h.get('atmostone', []):
        quad += [[i, j, P] for i, j in combinations(S, 2)]
    return _merge(bqp['n'], c, lin, quad)


def to_maxcut(qubo):
    """(n + 1, sorted weighted edges [u, v, w]) of the max-cut instance whose maximum cut minimises the QUBO."""
    n = qubo['n']
    h = [0] * n
    for i, a in qubo['linear']:
        h[i] += 2 * a
    E = []
    for i, j, b in qubo['quadratic']:
        h[i] += b
        h[j] += b
        E.append((i, j, b))
    E += [(i, n, h[i]) for i in range(n) if h[i]]
    return n + 1, sorted(E)


def from_cut(side, n):
    """The assignment of a cut of `to_maxcut`'s instance (side: a 0/1 string or sequence of length n + 1)."""
    ref = side[n]
    return [1 if side[i] == ref else 0 for i in range(n)]


def to_milp(bqp):
    """(c, constant, rows [(coefficients {var: a}, lo, hi)], n_vars): variables x_0..x_{n-1}, then one y per product."""
    n = bqp['n']
    c = [0.0] * n
    for i, a in bqp['linear']:
        c[i] += a
    rows = []
    nv = n
    for i, j, b in bqp['quadratic']:
        y = nv
        nv += 1
        c.append(float(b))
        if b > 0:
            rows.append(({y: 1, i: -1, j: -1}, -1, None))         # y >= x_i + x_j - 1
        else:
            rows.append(({y: 1, i: -1}, None, 0))                  # y <= x_i
            rows.append(({y: 1, j: -1}, None, 0))                  # y <= x_j
    h = bqp['hard']
    rows += [({i: 1, j: 1}, None, 1) for i, j in h.get('exclusive', [])]
    rows += [({i: 1, j: 1}, 1, None) for i, j in h.get('cover', [])]
    rows += [({i: 1 for i in S}, 1, 1) for S in h.get('one', [])]
    rows += [({i: 1 for i in S}, None, 1) for S in h.get('atmostone', [])]
    return c, bqp['constant'], rows, nv


def to_wcnf(bqp):
    """(hard clauses, soft [(weight, clause)], n_vars, offset): literals are +-(var + 1); cost + offset = objective."""
    n = bqp['n']
    hard, soft = [], []
    offset = bqp['constant']
    nv = n
    for i, a in bqp['linear']:
        if a > 0:
            soft.append((a, [-(i + 1)]))
        elif a < 0:
            soft.append((-a, [i + 1]))
            offset += a
    for i, j, b in bqp['quadratic']:
        if b > 0:
            soft.append((b, [-(i + 1), -(j + 1)]))
        else:
            nv += 1
            hard += [[-nv, i + 1], [-nv, j + 1]]
            soft.append((-b, [nv]))
            offset += b
    h = bqp['hard']
    hard += [[-(i + 1), -(j + 1)] for i, j in h.get('exclusive', [])]
    hard += [[i + 1, j + 1] for i, j in h.get('cover', [])]
    for S in h.get('one', []):
        hard.append([i + 1 for i in S])
        hard += [[-(i + 1), -(j + 1)] for i, j in combinations(S, 2)]
    for S in h.get('atmostone', []):
        hard += [[-(i + 1), -(j + 1)] for i, j in combinations(S, 2)]
    return hard, soft, nv, offset


def wcnf_text(hard, soft, nv):
    """The post-2022 WCNF text (hard clauses as `h ...`)."""
    lines = ['c genesis compiler', f'c vars {nv}']
    lines += ['h ' + ' '.join(map(str, cl)) + ' 0' for cl in hard]
    lines += [f'{w} ' + ' '.join(map(str, cl)) + ' 0' for w, cl in soft]
    return '\n'.join(lines) + '\n'


def repair(bqp, x, rounds=3):
    """A feasible assignment near x, by kind: first remove (for each violated exclusive pair or atmostone set, turn off
    the variables whose removal costs least, keeping the best one of a set), then add (for each violated cover pair or
    one set, turn on the cheapest variable; extra ones in a one set are turned off, keeping the best). The cost of a
    flip is its change in the objective. Repeated `rounds` times; the answer is verified afterwards in any case."""
    x = list(x)
    n = bqp['n']
    lin = [0] * n
    nb = [[] for _ in range(n)]
    for i, a in bqp['linear']:
        lin[i] += a
    for i, j, b in bqp['quadratic']:
        nb[i].append((j, b))
        nb[j].append((i, b))

    def gain_on(i):                                  # objective change of setting x_i = 1 (from 0)
        return lin[i] + sum(b for j, b in nb[i] if x[j])

    h = bqp['hard']
    for _ in range(rounds):
        for i, j in h.get('exclusive', []):
            if x[i] and x[j]:
                x[i if gain_on(i) > gain_on(j) else j] = 0         # drop the one whose presence helps less
        for S in h.get('atmostone', []) + h.get('one', []):
            on = [i for i in S if x[i]]
            if len(on) > 1:
                keep = min(on, key=lambda i: (gain_on(i), i))
                for i in on:
                    if i != keep:
                        x[i] = 0
        for S in h.get('one', []):
            if not any(x[i] for i in S):
                x[min(S, key=lambda i: (gain_on(i), i))] = 1
        for i, j in h.get('cover', []):
            if not x[i] and not x[j]:
                x[i if (gain_on(i), i) <= (gain_on(j), j) else j] = 1
        if not evaluate(bqp, x)[1]:
            break
    return x
