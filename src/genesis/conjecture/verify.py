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
