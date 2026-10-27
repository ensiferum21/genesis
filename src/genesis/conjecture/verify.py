"""Exact refutation certificates for upper bounds on the Laplacian spectral radius (KERNEL SIDE; F2,
`docs/OMEGA_FRONTIER.md` §5.5).

A claim "mu(G) <= max f(...)" is refuted by a certificate (G, x), x a nonzero rational vector, when

    q(x) = x^T L x / x^T x  >  hi,

where L is G's Laplacian and hi is an exact rational upper end of an interval enclosure of max f over G's vertices
(or edges). By Rayleigh-Ritz q(x) <= mu(G) for every nonzero x, so q(x) > hi >= max f proves mu(G) > max f.
Everything here is `fractions.Fraction` arithmetic; no floating point is used in a verdict. x^T L x is computed as
the sum over edges uv of (x_u - x_v)^2, so the cost is O(n + m) for any n.

Verdicts: REFUTED (with the certificate's digest), NOT_CERTIFIED (q(x) <= hi at the finest resolution tried), or
UNDEFINED (the bound is undefined at some vertex or edge of G, a negative radicand or a zero divisor: G is never a
counterexample, by the domain's convention).
"""
from fractions import Fraction
import hashlib
import json

from . import expr as E
from . import graphs as Gr

RESOLUTIONS = (64, 128, 256)


def rayleigh(n, edges, x):
    x = [Fraction(v) for v in x]
    if len(x) != n:
        raise ValueError('certificate vector has the wrong length')
    den = sum(v * v for v in x)
    if den == 0:
        raise ValueError('the zero vector certifies nothing')
    num = sum((x[u] - x[v]) ** 2 for u, v in edges)
    return num / den


def upper(ast, kind, n, edges, bits):
    """An exact upper end of an enclosure of the bound's maximum, or None if undefined or undecidable at `bits`."""
    his = []
    for env in Gr.envs(n, edges, kind):
        iv = E.enclose(ast, env, bits)
        if iv is None:
            return None
        his.append(iv[1])
    return max(his)


def defined(ast, kind, n, edges):
    return all(E.evaluate(ast, env) is not None for env in Gr.envs(n, edges, kind))


def check(formula, kind, n, edges, x):
    """Verify a refutation certificate of `mu <= max f` with f = `formula` (text in `expr`'s grammar)."""
    n, edges = Gr.normalise(n, edges)
    ast = E.parse(formula, kind)
    if not defined(ast, kind, n, edges):
        return {'verdict': 'UNDEFINED'}
    q = rayleigh(n, edges, x)
    hi = None
    for bits in RESOLUTIONS:
        hi = upper(ast, kind, n, edges, bits)
        if hi is not None and q > hi:
            cert = {'n': n, 'edges': [list(e) for e in edges], 'x': [str(Fraction(v)) for v in x],
                    'formula': E.render(ast), 'kind': kind}
            return {'verdict': 'REFUTED', 'q': str(q), 'hi': str(hi), 'bits': bits,
                    'digest': hashlib.sha256(json.dumps(cert, sort_keys=True).encode()).hexdigest()}
    return {'verdict': 'NOT_CERTIFIED', 'q': str(q), 'hi': None if hi is None else str(hi)}


def verifier(posed):
    """For a study (kernel side): verify(pid, artifact) -> 1.0 if the artifact's certificate refutes the posed bound
    exactly, else 0.0. `posed` is {id: (formula, kind)}; artifacts are those of `conjecture.domain`."""
    def verify(pid, art):
        formula, kind = posed[pid]
        try:
            res = check(formula, kind, art['n'], [tuple(e) for e in art['edges']], [Fraction(v) for v in art['x']])
        except (KeyError, ValueError, ZeroDivisionError, TypeError):
            return 0.0
        return 1.0 if res['verdict'] == 'REFUTED' else 0.0
    return verify


# ------------------------------------------------------------------------------------- an independent check

def charpoly(n, edges):
    """Coefficients [1, c1, ..., cn] of det(xI - L), L the Laplacian, by Berkowitz's division-free algorithm over the
    integers (exact)."""
    L = [[0] * n for _ in range(n)]
    for u, v in edges:
        L[u][u] += 1
        L[v][v] += 1
        L[u][v] -= 1
        L[v][u] -= 1
    vect = [1, -L[0][0]]
    for r in range(1, n):
        C = [L[i][r] for i in range(r)]
        R = L[r][:r]
        M = [row[:r] for row in L[:r]]
        t = [1, -L[r][r]]
        v = C[:]
        for _ in range(r):
            t.append(-sum(R[i] * v[i] for i in range(r)))
            v = [sum(M[i][j] * v[j] for j in range(r)) for i in range(r)]
        vect = [sum(t[i - j] * vect[j] for j in range(len(vect)) if 0 <= i - j < len(t)) for i in range(r + 2)]
    return vect


def _poly_eval(p, x):
    acc = Fraction(0)
    for c in p:                                   # highest degree first
        acc = acc * x + c
    return acc


def _poly_rem(a, b):
    """The remainder of a by b (lists of Fractions, highest degree first)."""
    a = list(a)
    while len(a) >= len(b) and any(a):
        f = a[0] / b[0]
        for i in range(len(b)):
            a[i] -= f * b[i]
        a.pop(0)
    while a and a[0] == 0:
        a.pop(0)
    return a


def _sturm(p):
    p = [Fraction(c) for c in p]
    dp = [c * (len(p) - 1 - i) for i, c in enumerate(p[:-1])]
    chain = [p, dp]
    while True:
        r = _poly_rem(chain[-2], chain[-1])
        if not r:
            break
        chain.append([-c for c in r])
    return chain


def roots_above(p, c):
    """The number of distinct real roots of p greater than the rational c (c not a root)."""
    chain = _sturm(p)

    def changes(vals):
        s = [v for v in vals if v != 0]
        return sum(1 for a, b in zip(s, s[1:]) if (a > 0) != (b > 0))
    at_c = changes([_poly_eval(q, Fraction(c)) for q in chain])
    at_inf = changes([q[0] for q in chain])        # signs of the leading coefficients
    return at_c - at_inf


def check_charpoly(formula, kind, n, edges, max_n=40):
    """An independent check of a refutation: mu(G) > hi, the bound's exact upper end, shown by a Sturm count on the
    exact characteristic polynomial (no certificate vector). For n <= max_n; None above."""
    n, edges = Gr.normalise(n, edges)
    if n > max_n:
        return None
    ast = E.parse(formula, kind)
    if not defined(ast, kind, n, edges):
        return {'verdict': 'UNDEFINED'}
    p = [Fraction(c) for c in charpoly(n, edges)]
    for bits in RESOLUTIONS:
        hi = upper(ast, kind, n, edges, bits)
        if hi is None:
            continue
        q = p
        while _poly_eval(q, hi) == 0:                 # hi is a root: divide it out (synthetic division, exact)
            out, acc = [], Fraction(0)
            for c in q[:-1]:
                acc = acc * hi + c
                out.append(acc)
            q = out
        if roots_above(q, hi) >= 1:
            return {'verdict': 'REFUTED', 'hi': str(hi), 'bits': bits}
        return {'verdict': 'NOT_CERTIFIED', 'hi': str(hi)}
    return {'verdict': 'NOT_CERTIFIED', 'hi': None}


# ------------------------------------------------------------------------------------- upper certificates

def collatz_upper(matrix, x):
    """An exact upper bound on the spectral radius of a nonnegative matrix from a positive rational vector x:
    rho(M) <= max_i (M x)_i / x_i (Collatz-Wielandt). For refuting LOWER bounds on a spectral radius (the direction
    the Rayleigh certificate cannot certify): the adjacency matrix for lambda_1, the signless Laplacian for an upper
    bound on mu (mu <= q). Raises on a non-positive x or a negative entry."""
    x = [Fraction(v) for v in x]
    if any(v <= 0 for v in x):
        raise ValueError('the Collatz-Wielandt vector must be positive')
    n = len(x)
    if any(len(row) != n for row in matrix) or any(e < 0 for row in matrix for e in row):
        raise ValueError('a square nonnegative matrix is required')
    return max(sum(Fraction(matrix[i][j]) * x[j] for j in range(n)) / x[i] for i in range(n))


def adjacency(n, edges):
    A = [[0] * n for _ in range(n)]
    for u, v in edges:
        A[u][v] = A[v][u] = 1
    return A


def check_matrix_form(formula, kind, n, edges, x):
    """A second, independently written Rayleigh check for graphs too large for the characteristic polynomial: the
    Laplacian as a matrix, one exact power step y = (L + Delta I) x from the certificate vector (a different vector),
    and q(y) = y^T L y / y^T y by matrix products in exact arithmetic. REFUTED if q(y) exceeds the bound's exact
    upper end."""
    n, edges = Gr.normalise(n, edges)
    ast = E.parse(formula, kind)
    if not defined(ast, kind, n, edges):
        return {'verdict': 'UNDEFINED'}
    L = [[0] * n for _ in range(n)]
    for u, v in edges:
        L[u][u] += 1
        L[v][v] += 1
        L[u][v] -= 1
        L[v][u] -= 1
    nz = [[(j, L[i][j]) for j in range(n) if L[i][j]] for i in range(n)]
    x = [Fraction(v) for v in x]
    delta = max(L[i][i] for i in range(n))
    y = [sum(c * x[j] for j, c in nz[i]) + delta * x[i] for i in range(n)]
    Ly = [sum(c * y[j] for j, c in nz[i]) for i in range(n)]
    den = sum(v * v for v in y)
    if den == 0:
        return {'verdict': 'NOT_CERTIFIED'}
    q = sum(a * b for a, b in zip(y, Ly)) / den
    for bits in RESOLUTIONS:
        hi = upper(ast, kind, n, edges, bits)
        if hi is not None and q > hi:
            return {'verdict': 'REFUTED', 'bits': bits}
    return {'verdict': 'NOT_CERTIFIED'}
