"""Quadratic penalty gadgets: executable encodings of relations, synthesised and verified (directive items 6-8).

A gadget for a relation R of arity k is a quadratic pseudo-Boolean polynomial over the k visible variables x and m
ancilla variables a,

    P(x, a) = c + sum_i h_i z_i + sum_{i<j} J_ij z_i z_j,     z = (x, a), integer coefficients,

that is **exact with gap g** when min_a P(x, a) = 0 for every x in R and min_a P(x, a) >= g > 0 for every x outside
R. A sum of exact gadgets, one per constraint, is zero exactly on the assignments satisfying every constraint, so a
problem made of relations becomes one quadratic objective (a QUBO), the form Genesis's max-cut engine solves through
the Problem Compiler. Decoding drops the ancillas.

**Verification is independent of synthesis.** `check` enumerates every (x, a) and evaluates P directly; nothing the
synthesiser computed is trusted. `check_matrix` evaluates the same polynomial a second way (as z^T Q z with numpy),
for the tests.

**Synthesisers** (both LLM-free; both proposals only, accepted only through `check`):
  * `synthesize_milp`: for m = 0, 1, ... ancillas, a mixed-integer program (HiGHS through `scipy.optimize.milp`):
    integer coefficients in [-bound, bound]; P >= 0 on R x {0,1}^m and P >= gap outside R; for each x in R a binary
    choice of ancilla pattern where P = 0 (big-M); minimise the sum of |coefficients|. The first m that is feasible
    is the fewest ancillas for that coefficient bound.
  * `synthesize_search`: a stochastic local search over integer coefficient vectors at a fixed m, minimising the
    violation (the baseline any synthesiser must beat at matched evaluations).
Known gadgets (for example the Rosenberg 1975 product reduction, or "exactly one" as (sum - 1)^2) are what the tests
rediscover; no novelty is claimed for a gadget unless a literature check says so.
"""
from itertools import combinations, product

from .relations import Relation, assignment

MAX_VARS = 8


class Gadget:
    __slots__ = ('k', 'm', 'c', 'h', 'J')

    def __init__(self, k, m, c, h, J):
        n = k + m
        if n > MAX_VARS:
            raise ValueError(f'at most {MAX_VARS} variables')
        if len(h) != n:
            raise ValueError('one linear coefficient per variable')
        if set(J) - {(i, j) for i, j in combinations(range(n), 2)}:
            raise ValueError('quadratic terms are pairs i < j of variables')
        self.k, self.m, self.c = int(k), int(m), int(c)
        self.h = [int(x) for x in h]
        self.J = {(int(i), int(j)): int(v) for (i, j), v in J.items() if v}

    def value(self, z):
        return self.c + sum(hi * zi for hi, zi in zip(self.h, z)) + sum(v * z[i] * z[j] for (i, j), v in self.J.items())

    def min_over_ancillas(self, x):
        return min(self.value(tuple(x) + a) for a in product((0, 1), repeat=self.m))

    def size(self):
        """Number of non-zero coefficients, and the largest magnitude."""
        coefs = [self.c] + self.h + list(self.J.values())
        return sum(1 for v in coefs if v), max((abs(v) for v in coefs), default=0)

    def to_json(self):
        return {'k': self.k, 'm': self.m, 'c': self.c, 'h': self.h,
                'J': [[i, j, v] for (i, j), v in sorted(self.J.items())]}

    @staticmethod
    def from_json(d):
        return Gadget(d['k'], d['m'], d['c'], d['h'], {(i, j): v for i, j, v in d['J']})

    def __eq__(self, other):
        return isinstance(other, Gadget) and self.to_json() == other.to_json()

    def __repr__(self):
        return f'Gadget({self.to_json()})'


def check(g, rel):
    """Exhaustive verification: {'exact', 'gap', 'zero_on_relation', 'nonnegative', 'violations'}."""
    if g.k != rel.k:
        return {'exact': False, 'gap': None, 'zero_on_relation': False, 'nonnegative': False,
                'violations': ['arity differs']}
    viol, gap, nonneg, zero, outside = [], None, True, True, []
    for i in range(1 << rel.k):
        x = assignment(i, rel.k)
        vals = [g.value(x + a) for a in product((0, 1), repeat=g.m)]
        mn = min(vals)
        if mn < 0:
            nonneg = False
            viol.append([list(x), 'negative'])
        if rel.contains(x):
            if mn != 0:
                zero = False
                viol.append([list(x), f'min {mn} on a member'])
        else:
            gap = mn if gap is None else min(gap, mn)
            outside.append(mn)
            if mn <= 0:
                viol.append([list(x), f'min {mn} on a non-member'])
    exact = not viol
    return {'exact': exact, 'gap': gap if gap is not None else 0, 'zero_on_relation': zero, 'nonnegative': nonneg,
            'uniform': exact and len(set(outside)) <= 1, 'violations': viol[:8]}


def check_matrix(g, rel):
    """The same verification computed differently: P = c + z^T Q z with Q upper-triangular (diagonal = h)."""
    import numpy as np
    n = g.k + g.m
    Q = np.zeros((n, n), dtype=np.int64)
    for i, v in enumerate(g.h):
        Q[i, i] = v
    for (i, j), v in g.J.items():
        Q[i, j] = v
    Z = np.array(list(product((0, 1), repeat=n)), dtype=np.int64)[:, ::-1]   # column t = variable t
    vals = g.c + np.einsum('si,ij,sj->s', Z, Q, Z)
    idx_x = (Z[:, :g.k] * (1 << np.arange(g.k))).sum(axis=1)
    mins = {}
    for ix, v in zip(idx_x.tolist(), vals.tolist()):
        mins[ix] = min(mins.get(ix, v), v)
    member = [bool(rel.table >> ix & 1) for ix in range(1 << g.k)]
    ok = all((mins[ix] == 0) if member[ix] else (mins[ix] >= 1) for ix in range(1 << g.k))
    ok = ok and min(vals.tolist()) >= 0
    return ok


# ------------------------------------------------------------------------------------------- synthesis

def _terms(n):
    return [('c',)] + [('h', i) for i in range(n)] + [('J', i, j) for i, j in combinations(range(n), 2)]


def _row(terms, z):
    out = []
    for t in terms:
        if t[0] == 'c':
            out.append(1)
        elif t[0] == 'h':
            out.append(z[t[1]])
        else:
            out.append(z[t[1]] * z[t[2]])
    return out


def _gadget(k, m, terms, coefs):
    n = k + m
    c, h, J = 0, [0] * n, {}
    for t, v in zip(terms, coefs):
        v = int(round(v))
        if t[0] == 'c':
            c = v
        elif t[0] == 'h':
            h[t[1]] = v
        else:
            J[(t[1], t[2])] = v
    return Gadget(k, m, c, h, J)


def synthesize_milp(rel, max_ancillas=2, bound=8, gap=1, time_limit=30.0, uniform=False):
    """The gadget with the fewest ancillas (up to max_ancillas), then the smallest sum of |coefficients|, with
    coefficients in [-bound, bound] and the given gap; None if none exists within those limits. With `uniform`, every
    non-member's minimum is exactly the gap, so a sum of such gadgets counts violated constraints (Max-CSP exact).
    Verified by `check` before it is returned. Returns (gadget, report)."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    tried = []
    for m in range(max_ancillas + 1):
        n = rel.k + m
        if n > MAX_VARS:
            break
        terms = _terms(n)
        T = len(terms)
        members = [assignment(i, rel.k) for i in range(1 << rel.k) if rel.table >> i & 1]
        pinned = members + ([assignment(i, rel.k) for i in range(1 << rel.k) if not rel.table >> i & 1]
                            if uniform else [])
        pats = list(product((0, 1), repeat=m))
        S = len(pinned) * len(pats) if m else 0
        big = bound * T + gap
        # variables: coefficients (T, integer), |coefficient| (T), selectors (S, binary)
        nv = 2 * T + S
        A, lo, hi = [], [], []

        def add(row, lb, ub):
            A.append(row)
            lo.append(lb)
            hi.append(ub)
        for i in range(1 << rel.k):
            x = assignment(i, rel.k)
            inside = bool(rel.table >> i & 1)
            for a in pats:
                r = _row(terms, x + a) + [0] * (T + S)
                add(r, 0 if inside else gap, np.inf)
        if m == 0:
            for x in pinned:
                target = 0 if rel.contains(x) else gap
                add(_row(terms, x) + [0] * (T + S), target, target)
        else:
            for xi, x in enumerate(pinned):
                target = 0 if rel.contains(x) else gap
                sel = []
                for ai, a in enumerate(pats):
                    s = xi * len(pats) + ai
                    r = _row(terms, x + a) + [0] * T + [0] * S
                    r[2 * T + s] = big                      # P + big * s <= big + target  (P = target when s = 1)
                    add(r, -np.inf, big + target)
                    sel.append(s)
                r = [0] * nv
                for s in sel:
                    r[2 * T + s] = 1
                add(r, 1, np.inf)
        for t in range(T):                                  # u_t >= |coef_t|
            r = [0] * nv
            r[t], r[T + t] = 1, 1
            add(r, 0, np.inf)
            r = [0] * nv
            r[t], r[T + t] = -1, 1
            add(r, 0, np.inf)
        cost = np.array([0.0] * T + [1.0] * T + [0.0] * S)
        integrality = np.array([1] * T + [0] * T + [1] * S)
        bounds = Bounds([-bound] * T + [0] * T + [0] * S, [bound] * T + [bound] * T + [1] * S)
        res = milp(cost, constraints=LinearConstraint(np.array(A, dtype=float), lo, hi), integrality=integrality,
                   bounds=bounds, options={'time_limit': time_limit, 'disp': False})
        tried.append({'ancillas': m, 'status': int(res.status), 'message': str(res.message)})
        if res.x is not None and res.status in (0, 1):
            g = _gadget(rel.k, m, terms, res.x[:T])
            ver = check(g, rel)
            tried[-1]['verified'] = ver['exact']
            if ver['exact'] and (ver['uniform'] or not uniform):
                return g, {'synthesizer': 'milp', 'tried': tried, 'bound': bound, 'gap': gap, 'uniform': uniform,
                           'optimal': res.status == 0, 'check': ver}
    return None, {'synthesizer': 'milp', 'tried': tried, 'bound': bound, 'gap': gap, 'uniform': uniform}


def violation(g, rel):
    """How far a candidate is from exact (0 when exact with gap >= 1)."""
    v = 0
    for i in range(1 << rel.k):
        x = assignment(i, rel.k)
        vals = [g.value(x + a) for a in product((0, 1), repeat=g.m)]
        mn = min(vals)
        v += sum(max(0, -y) for y in vals)
        v += abs(mn) if rel.contains(x) else max(0, 1 - mn)
    return v


def synthesize_search(rel, m, rng, evaluations=20000, bound=8):
    """Stochastic local search (random restarts plus single-coefficient moves) at m ancillas; returns (gadget or None,
    report with the evaluations used). A baseline for the MILP synthesiser at matched candidate evaluations."""
    n = rel.k + m
    terms = _terms(n)
    best_g, best_v, used = None, None, 0
    while used < evaluations:
        coefs = [rng.randint(-bound, bound) for _ in terms]
        g = _gadget(rel.k, m, terms, coefs)
        v = violation(g, rel)
        used += 1
        stall = 0
        while used < evaluations and stall < 200 and v > 0:
            t = rng.randrange(len(terms))
            old = coefs[t]
            coefs[t] = max(-bound, min(bound, old + rng.choice((-2, -1, 1, 2))))
            g2 = _gadget(rel.k, m, terms, coefs)
            v2 = violation(g2, rel)
            used += 1
            if v2 <= v:
                stall = stall + 1 if v2 == v else 0
                g, v = g2, v2
            else:
                coefs[t] = old
                stall += 1
        if best_v is None or v < best_v:
            best_g, best_v = g, v
        if v == 0:
            break
    ok = best_v == 0 and check(best_g, rel)['exact']
    return (best_g if ok else None), {'synthesizer': 'search', 'evaluations': used, 'best_violation': best_v,
                                      'ancillas': m}


def transport(g, rel_from, perm, flips):
    """A gadget for rel_from.transform(perm, flips), from a gadget g for rel_from: rename variables and substitute
    x -> 1 - x for negated ones (exactness and gap are preserved)."""
    n = g.k + g.m
    full = list(perm) + list(range(g.k, n))                 # ancillas keep their places
    neg = [bool(flips >> full[i] & 1) if i < g.k else False for i in range(n)]
    # P(z) in old variables; z_old[i] = y[full[i]] or 1 - y[full[i]]
    c, h, J = g.c, [0] * n, {}
    for i in range(n):
        hi = g.h[i]
        if neg[i]:
            c += hi
            h[full[i]] -= hi
        else:
            h[full[i]] += hi
    for (i, j), v in g.J.items():
        a, b = full[i], full[j]
        key = (min(a, b), max(a, b))
        if neg[i] and neg[j]:                               # (1 - ya)(1 - yb) = 1 - ya - yb + ya yb
            c += v
            h[a] -= v
            h[b] -= v
            J[key] = J.get(key, 0) + v
        elif neg[i]:                                        # (1 - ya) yb = yb - ya yb
            h[b] += v
            J[key] = J.get(key, 0) - v
        elif neg[j]:
            h[a] += v
            J[key] = J.get(key, 0) - v
        else:
            J[key] = J.get(key, 0) + v
    return Gadget(g.k, g.m, c, h, J)


__all__ = ['MAX_VARS', 'Gadget', 'check', 'check_matrix', 'synthesize_milp', 'synthesize_search', 'violation',
           'transport', 'Relation']
