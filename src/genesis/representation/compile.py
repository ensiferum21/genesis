"""From relations to one quadratic program: the transformation and the decoder (directive item 6).

A constraint problem is data:

    {'n': variables, 'constraints': [{'relation': {k, table}, 'vars': [i, ...], 'weight': w}],
     'objective': {'constant', 'linear': [[i, a]], 'quadratic': [[i, j, b]]} or None}

`compile(problem, lib, mode)` replaces every constraint by its gadget from the library (renamed onto the
constraint's variables, its ancillas appended as fresh variables) and returns a BQP of the Problem Compiler's form
with no hard constraints (`compiler.bqp`; solved by any of its back-ends, max-cut through `to_maxcut`), plus the map
back. The modes:
  * `satisfy`: penalty weight 1 per constraint; the BQP's minimum is 0 exactly when every constraint can hold;
  * `max_csp`: every gadget of a soft constraint must be uniform with gap 1 (each violated constraint costs exactly
    1, times its weight), so the BQP's minimum over ancillas is the total weight of violated constraints: exact for
    weighted Max-CSP. A constraint marked `hard` (weight above the total soft weight) needs only an exact gadget;
  * `optimize`: the objective plus a penalty W x (sum of gadgets), W = 1 + the objective's total range (sum of
    |coefficients|), so any assignment violating a constraint costs more than any change of the objective: exact for
    the constrained optimum.
Missing relations are reported (`missing`), not guessed: the problem can then be parked in the vault until a
gadget is found (`library.park`).

`decode` drops the ancillas. `verify` is the independent checker: it evaluates every constraint relation on the
decoded assignment and the objective directly from the problem, never from the BQP.
"""
import json

from .relations import relation_from_json
from . import library as LB


def missing(problem, lib, mode='satisfy'):
    out, seen = [], set()
    for c in problem['constraints']:
        r = relation_from_json(c['relation'])
        need_uniform = mode == 'max_csp' and not c.get('hard')
        if not LB.supports(lib, r, need_uniform) and r.id() not in seen:
            seen.add(r.id())
            out.append(r)
    return out


def _objective_range(obj):
    if not obj:
        return 0
    return sum(abs(a) for _, a in obj.get('linear', [])) + sum(abs(b) for _, _, b in obj.get('quadratic', []))


def compile(problem, lib, mode='satisfy'):
    """(bqp, info) or raises KeyError listing the missing relations' IDs."""
    miss = missing(problem, lib, mode)
    if miss:
        raise KeyError('missing relations: ' + ', '.join(r.id() for r in miss))
    n = problem['n']
    lin, quad, const = {}, {}, 0
    nxt = n
    W = 1 if mode in ('satisfy', 'max_csp') else 1 + _objective_range(problem.get('objective'))
    cache = {}
    for c in problem['constraints']:
        uni = mode == 'max_csp' and not c.get('hard')
        ck = (json.dumps(c['relation'], sort_keys=True), uni)
        if ck not in cache:
            r = relation_from_json(c['relation'])
            cache[ck] = (r, LB.lookup(lib, r, uni), LB.entry(lib, r, uni))
        r, g, e = cache[ck]
        if uni and e['gap'] != 1:
            raise ValueError(f'max_csp needs uniform gadgets of gap 1; relation {r.id()} has gap {e["gap"]}')
        names = list(c['vars']) + list(range(nxt, nxt + g.m))
        nxt += g.m
        scale = W * c.get('weight', 1)
        const += scale * g.c
        for i, v in enumerate(g.h):
            if v:
                lin[names[i]] = lin.get(names[i], 0) + scale * v
        for (i, j), v in g.J.items():
            a, b = names[i], names[j]
            if a == b:                                     # a constraint naming one variable twice: x*x = x
                lin[a] = lin.get(a, 0) + scale * v
                continue
            key = (min(a, b), max(a, b))
            quad[key] = quad.get(key, 0) + scale * v
    obj = problem.get('objective') or {}
    const += obj.get('constant', 0)
    for i, a in obj.get('linear', []):
        lin[i] = lin.get(i, 0) + a
    for i, j, b in obj.get('quadratic', []):
        key = (min(i, j), max(i, j))
        quad[key] = quad.get(key, 0) + b
    bqp = {'n': nxt, 'constant': const, 'linear': [[i, a] for i, a in sorted(lin.items()) if a],
           'quadratic': [[i, j, b] for (i, j), b in sorted(quad.items()) if b], 'hard': {}}
    return bqp, {'mode': mode, 'penalty_weight': W, 'visible': n, 'ancillas': nxt - n, 'library': LB.version(lib)}


def decode(x, info):
    return list(x[:info['visible']])


def verify(problem, x):
    """The independent check: (violated constraints' total weight, objective value), from the problem alone."""
    viol = 0
    for c in problem['constraints']:
        r = relation_from_json(c['relation'])
        if not r.contains([x[i] for i in c['vars']]):
            viol += c.get('weight', 1)
    obj = problem.get('objective') or {}
    val = obj.get('constant', 0) + sum(a * x[i] for i, a in obj.get('linear', [])) + \
        sum(b * x[i] * x[j] for i, j, b in obj.get('quadratic', []))
    return viol, val


def bqp_value(bqp, z):
    return bqp['constant'] + sum(a * z[i] for i, a in bqp['linear']) + sum(b * z[i] * z[j] for i, j, b in bqp['quadratic'])


def brute_force(bqp):
    """The minimum of a small BQP by enumeration: (value, assignment)."""
    from itertools import product
    if bqp['n'] > 22:
        raise ValueError('too large to enumerate')
    best = None
    for z in product((0, 1), repeat=bqp['n']):
        v = bqp_value(bqp, z)
        if best is None or v < best[0]:
            best = (v, z)
    return best


__all__ = ['missing', 'compile', 'decode', 'verify', 'bqp_value', 'brute_force']
