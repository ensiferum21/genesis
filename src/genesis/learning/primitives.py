"""New primitives and research-language evolution (roadmap W22), DEV only.

An operator-completeness adversary looks for term patterns that recur in the material the
current language handles poorly (failed development targets and the lemmas used to reach
them). A recurring pattern P(X1..Xk) becomes a candidate primitive p with the semantic
contract

    p(X1, …, Xk) = P(X1, …, Xk)        (a definitional, hence conservative, extension)

with reference expansion `unfold` (replace every p(t1..tk) by P(t1..tk)) and folding
`fold` (the reverse, by matching). The contract is checked three ways before use:
  * round trip: unfold(fold(e)) == e on the pool;
  * decider: the deciders evaluate p through its definition (`equational.DEFINITIONS`);
  * Lean: a target proved in the extended system is bound to the *base* statement by
    instantiating p with λx̄. P(x̄) and discharging the definition by rfl.
The primitive must add capability beyond renaming: research with it is compared with
research over the same conjectures unfolded into the base language (a macro-renaming
control), at equal budgets on fresh base-language targets. Migration folds the library;
rollback unfolds it.
"""
from collections import Counter

from . import equational as Q


def _generalize(t, m):
    """Rename variables in order of appearance (pattern identity up to renaming)."""
    if t[0] == 'var':
        m.setdefault(t[1], f'P{len(m)}')
        return ('var', m[t[1]])
    return ('fn', t[1], tuple(_generalize(a, m) for a in t[2]))


def _subterms(t):
    if t[0] == 'fn' and t[2]:
        yield t
        for a in t[2]:
            yield from _subterms(a)


def propose(equations, *, top=3, min_size=2, max_size=4):
    """Recurring non-trivial patterns, most frequent first: [(pattern, count)]."""
    c = Counter()
    for l, r in equations:
        seen = set()
        for side in (l, r):
            for t in _subterms(side):
                if min_size <= Q.size(t) <= max_size:
                    g = _generalize(t, {})
                    if all(a[0] == 'var' for a in g[2]) and len({a[1] for a in g[2]}) == len(g[2]):
                        continue                  # an existing operation on distinct variables: a mere renaming
                    if g not in seen:
                        seen.add(g); c[g] += 1
    return c.most_common(top)


def primitive(pattern, name='p'):
    vs = []

    def collect(t):
        if t[0] == 'var':
            if t[1] not in vs:
                vs.append(t[1])
        else:
            for a in t[2]:
                collect(a)
    collect(pattern)
    return {'name': name, 'arity': len(vs), 'params': vs, 'pattern': pattern}


def _subst(t, m):
    if t[0] == 'var':
        return m.get(t[1], t)
    return ('fn', t[1], tuple(_subst(a, m) for a in t[2]))


def unfold(t, prim):
    if t[0] == 'var':
        return t
    args = tuple(unfold(a, prim) for a in t[2])
    if t[1] == prim['name']:
        return _subst(prim['pattern'], dict(zip(prim['params'], args)))
    return ('fn', t[1], args)


def _match(p, t, s):
    if p[0] == 'var':
        if p[1] in s:
            return s if s[p[1]] == t else None
        return {**s, p[1]: t}
    if t[0] != 'fn' or p[1] != t[1] or len(p[2]) != len(t[2]):
        return None
    for a, b in zip(p[2], t[2]):
        s = _match(a, b, s)
        if s is None:
            return None
    return s


def fold(t, prim):
    """Innermost-first folding of every instance of the pattern."""
    if t[0] == 'var':
        return t
    t = ('fn', t[1], tuple(fold(a, prim) for a in t[2]))
    m = _match(prim['pattern'], t, {})
    if m is not None and all(v in m for v in prim['params']):
        return ('fn', prim['name'], tuple(m[v] for v in prim['params']))
    return t


def extend(system, prim, *, name=None):
    """Register the definitional extension of `system` by `prim` and return its name. The
    definition is the last axiom; deciders evaluate the new symbol through it."""
    base = Q.SYSTEMS[system]
    if prim['name'] in base['ops'] or (prim['name'] in Q.DEFINITIONS and
                                       Q.DEFINITIONS[prim['name']] != (tuple(prim['params']), prim['pattern'])):
        raise ValueError(f'symbol {prim["name"]} is already in use')
    Q.DEFINITIONS[prim['name']] = (tuple(prim['params']), prim['pattern'])
    lhs = ('fn', prim['name'], tuple(('var', v) for v in prim['params']))
    definition = Q.text((lhs, prim['pattern']))
    name = name or f'{system}+{prim["name"]}'
    Q.register(name, {**base, 'ops': {**base['ops'], prim['name']: prim['arity']},
                      'axioms': base['axioms'] + [definition], 'primitive': prim, 'base': system,
                      'definition': definition})
    return name


def lean_definition(prim):
    """The (symbol, parameters, body) triple that `fof_lean.replay(definitions=…)` takes."""
    return (prim['name'], list(prim['params']), prim['pattern'])


def round_trip(prim, equations):
    """unfold(fold(e)) must give back e for every equation (the reference expansion)."""
    bad = [e for e in equations if (unfold(fold(e[0], prim), prim), unfold(fold(e[1], prim), prim)) != e]
    return {'checked': len(equations), 'failures': len(bad)}


def migrate(library, prim):
    """Fold every library lemma into the extended language (records the change)."""
    out = []
    for l in library:
        eq = Q.canon((fold(l['eq'][0], prim), fold(l['eq'][1], prim)))
        out.append(dict(l, eq=eq, text=Q.text(eq), migrated_from=l['text']))
    return out


def rollback(library, prim):
    out = []
    for l in library:
        eq = Q.canon((unfold(l['eq'][0], prim), unfold(l['eq'][1], prim)))
        out.append(dict(l, eq=eq, text=Q.text(eq)))
    return out


__all__ = ['propose', 'primitive', 'fold', 'unfold', 'extend', 'lean_definition', 'round_trip', 'migrate',
           'rollback']
