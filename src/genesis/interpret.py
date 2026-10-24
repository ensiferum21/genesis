"""The interpretation engine, first version (Genesis Ω contract §9, §16.7): explanations of archived rules, without
LLMs: symbolic simplification under declared feature ranges, behavioural fingerprints, conjectures of equivalence
tested against counterexamples, and ablations. Explanations are separate artifacts with their own status; the
original discovery is never modified.

Rules here are programs of Genesis's acquisition language (`science.acquire`). Their features have declared ranges
(RANGES: probabilities and normalised entropy in [0, 1], gains and improvements >= 0, counts >= 0). That makes some
rewrites exact:
  * sqrt(sq(x)) = |x|, and |x| = x when x >= 0;
  * min(x, c) = x when x <= c everywhere, max(x, c) = x when x >= c everywhere (interval reasoning);
  * x * 1 = x, x + 0 = x, constants folded.
`simplify` applies them bottom-up to a fixed point, and returns the simplified program and the rewrites used, each
an exact identity under the ranges ("mathematically established" for the rewrite, given the ranges' correctness).

`fingerprint(prog, domains, budget)`: the sequence of experiments the rule chooses on each of a set of domains,
exactly the behaviour that matters. Two rules with the same fingerprint on many domains are CONJECTURED
equivalent; `test_conjecture` looks for a counterexample on further domains and returns the first one found (the
conjecture is then rejected) or none (it stays empirically supported, never proven by testing). `ablate` replaces
each subtree in turn by a neutral constant and reports the change in a score, which names the parts a rule's
behaviour depends on.
"""
import json
import math

from .science import acquire as Q

INF = math.inf
RANGES = {'eig': (0.0, INF), 'dec': (0.0, 1.0), 'decf': (0.0, 1.0), 'eigall': (0.0, INF), 'decall': (0.0, 1.0),
          'decfall': (0.0, 1.0), 'ent': (0.0, 1.0), 'maxp': (0.0, 1.0), 'pf': (0.0, 1.0), 'seen': (0.0, INF),
          'left': (1.0, INF), 'one': (1.0, 1.0)}


def interval(t):
    """The range of a tree's values over the features' declared ranges."""
    if isinstance(t, str):
        return RANGES[t]
    if isinstance(t, float):
        return (t, t)
    if len(t) == 2:
        lo, hi = interval(t[1])
        if t[0] == 'sq':
            if lo >= 0:
                return (lo * lo, hi * hi)
            if hi <= 0:
                return (hi * hi, lo * lo)
            return (0.0, max(lo * lo, hi * hi))
        if t[0] == 'sqrt':
            a = 0.0 if lo <= 0 <= hi else min(abs(lo), abs(hi))
            return (math.sqrt(a), math.sqrt(max(abs(lo), abs(hi))))
        a = 0.0 if lo <= 0 <= hi else min(abs(lo), abs(hi))          # inv1 = 1 / (1 + |x|)
        return (1.0 / (1.0 + max(abs(lo), abs(hi))), 1.0 / (1.0 + a))
    (a, b), (c, d) = interval(t[1]), interval(t[2])
    if t[0] == '+':
        return (a + c, b + d)
    if t[0] == '-':
        return (a - d, b - c)
    if t[0] == '*':
        ps = [x * y for x in (a, b) for y in (c, d) if not (math.isinf(x) and y == 0) and not (math.isinf(y) and x == 0)]
        return (min(ps), max(ps)) if ps else (0.0, 0.0)
    if t[0] == 'max':
        return (max(a, c), max(b, d))
    return (min(a, c), min(b, d))


def _rewrite(t):
    """One bottom-up pass; returns (tree, [rewrite names])."""
    if isinstance(t, (str, float)):
        return t, []
    used = []
    kids = []
    for k in t[1:]:
        nk, u = _rewrite(k)
        kids.append(nk)
        used += u
    t = [t[0]] + kids
    if len(t) == 2:
        x = t[1]
        if t[0] == 'sqrt' and isinstance(x, list) and x[0] == 'sq':
            lo, _ = interval(x[1])
            if lo >= 0:
                return x[1], used + ['sqrt(sq(x)) = x for x >= 0']
        if isinstance(x, float):
            return float({'sqrt': math.sqrt(abs(x)), 'sq': x * x, 'inv1': 1 / (1 + abs(x))}[t[0]]), \
                used + ['constant folded']
        return t, used
    a, b = t[1], t[2]
    (la, ha), (lb, hb) = interval(a), interval(b)
    if t[0] == 'min':
        if ha <= lb:
            return a, used + ['min(x, y) = x when x <= y everywhere']
        if hb <= la:
            return b, used + ['min(x, y) = y when y <= x everywhere']
    if t[0] == 'max':
        if la >= hb:
            return a, used + ['max(x, y) = x when x >= y everywhere']
        if lb >= ha:
            return b, used + ['max(x, y) = y when y >= x everywhere']
    if t[0] == '*':
        if a == 1.0:
            return b, used + ['1 * x = x']
        if b == 1.0:
            return a, used + ['x * 1 = x']
    if t[0] == '+':
        if a == 0.0:
            return b, used + ['0 + x = x']
        if b == 0.0:
            return a, used + ['x + 0 = x']
    if isinstance(a, float) and isinstance(b, float):
        v = {'+': a + b, '-': a - b, '*': a * b, 'max': max(a, b), 'min': min(a, b)}[t[0]]
        return float(v), used + ['constant folded']
    return t, used


def simplify(prog):
    """(simplified program, rewrites used). Every rewrite is an identity under RANGES. The result may use constants
    outside the language's CONSTANTS (it is an explanation, evaluated by `acquire.scores`, which accepts them)."""
    t, used = prog['expr'], []
    for _ in range(20):
        nt, u = _rewrite(t)
        used += u
        if nt == t:
            break
        t = nt
    return {'agg': prog['agg'], 'expr': t}, used


def fingerprint(prog, domains, budget):
    """The experiments the rule chooses, in order, on each domain."""
    from .science import design as D
    out = []
    for d in domains:
        r, _ = D.run(d, {'kind': 'program', 'program': prog}, budget)
        out.append(tuple(r.done))
    return out


def test_conjecture(a, b, domains, budget):
    """'a and b choose the same experiments': the index of the first domain that refutes it, or None."""
    fa, fb = fingerprint(a, domains, budget), fingerprint(b, domains, budget)
    for k, (x, y) in enumerate(zip(fa, fb)):
        if x != y:
            return k
    return None


def _paths(t, path=()):
    yield path
    if isinstance(t, list):
        for k in range(1, len(t)):
            yield from _paths(t[k], path + (k,))


def ablate(prog, score, neutral=1.0):
    """[(path, subtree, score with the subtree replaced by `neutral`, change)] for every proper subtree."""
    base = score(prog)
    out = []
    for path in _paths(prog['expr']):
        if not path:
            continue
        sub = prog['expr']
        for k in path:
            sub = sub[k]
        t = json.loads(json.dumps(prog['expr']))
        node = t
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = neutral
        s = score({'agg': prog['agg'], 'expr': t})
        out.append((list(path), sub, s, s - base))
    return out


def text(prog):
    """A readable form that tolerates constants outside the language's list."""
    return Q.text(prog)
