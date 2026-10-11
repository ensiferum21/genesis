"""Missing-concept recovery by typed anti-unification (roadmap W09).

The pipeline:
  1. Ingestion. Lean itself, in the trusted check stage, dumps the statement tree of
     every declaration in the library modules, together with its type, the constants it
     uses and the size of its proof term.
  2. Cutoff snapshot. Only modules before the cutoff are visible. Recovery records the
     digest of every tree it read. The fresh families come after the cutoff and are
     generated only once the recovered concept is fixed, so no future library information
     reaches the recovery.
  3. Typed anti-unification. Plotkin's least general generalisation, over pairs of
     statement trees. Differing closed subterms become holes. A hole is typed by the Lean
     types of the subterms it replaces, and two differing subterms with different types
     are never merged. Subterms with loose bound variables are not abstracted
     (first-order only).
  4. Reification. A generalisation shared by at least two library statements becomes a
     Lean definition, `def RC.<name> (P₁ : τ₁) … : Prop := <body>`. Every source
     statement is checked to be a definitional instance (`… = RC.<name> args := rfl`).
  5. Evaluation on fresh families, in four arms:
     - no library;
     - retrieval: the instance lemmas from before the cutoff;
     - recovered concept: one proof of the concept per fresh predicate, plus generic
       lemmas over the concept;
     - manual: an equivalent, builder-supplied abstraction, Mathlib's `Antitone`.
     Caching (reuse of a proof by statement digest) is counted in every arm. Metrics:
     statements proved, search candidates, CPU, and proof-term size.

The recovered abstraction must not use hidden constants. During recovery, the hidden set
is Mathlib's order-theoretic `Antitone` and `Monotone` and their lemmas. The leakage check
looks at the reified definition's dependencies.
"""
import json

from ..common import digest

HIDDEN = ('Antitone', 'Monotone', 'AntitoneOn', 'MonotoneOn', 'StrictAnti', 'StrictMono', 'IsLowerSet',
          'IsUpperSet')


class Hole:
    __slots__ = ('index',)

    def __init__(self, index):
        self.index = index

    def __eq__(self, other):
        return isinstance(other, Hole) and other.index == self.index

    def __hash__(self):
        return hash(('hole', self.index))

    def __repr__(self):
        return f'?{self.index}'


def _loose(t, depth=0):
    """Does tree t contain a bound variable that escapes `depth` binders?"""
    if isinstance(t, Hole) or not isinstance(t, list) or not t:
        return False
    tag = t[0]
    if tag == 'bvar':
        return t[1] >= depth
    if tag in ('lam', 'pi'):
        return _loose(t[1], depth) or _loose(t[2], depth + 1)
    if tag == 'let':
        return _loose(t[1], depth) or _loose(t[2], depth) or _loose(t[3], depth + 1)
    if tag == 'app':
        return _loose(t[1], depth) or _loose(t[2], depth)
    if tag == 'proj':
        return _loose(t[3], depth)
    return False


def anti_unify(trees, types):
    """LGG of several statement trees. `types(t)` gives the Lean type string of a closed
    subterm (or None if unknown). Returns (generalisation, holes) where holes is a list of
    {'index', 'type', 'fillers': [per input tree]} or (None, None) if typing blocks it."""
    holes = {}
    order = []

    def go(ts, depth):
        first = ts[0]
        if all(t == first for t in ts):
            return first
        if all(isinstance(t, list) and t and t[0] == first[0] for t in ts) and first[0] in (
                'app', 'lam', 'pi', 'let') and all(len(t) == len(first) for t in ts):
            inner = [go([t[i] for t in ts], depth + (1 if first[0] in ('lam', 'pi') and i == 2 else 0)
                        + (1 if first[0] == 'let' and i == 3 else 0)) for i in range(1, len(first))]
            if any(x is None for x in inner):
                return None
            return [first[0], *inner]
        if any(_loose(t, 0) for t in ts):
            return None                                  # first-order only
        tys = [types(t) for t in ts]
        if None in tys or len(set(tys)) != 1:
            return None                                  # typed: fillers must share one known type
        key = tuple(json.dumps(t, sort_keys=True) for t in ts)
        if key not in holes:
            holes[key] = Hole(len(order))
            order.append({'index': len(order), 'type': tys[0], 'fillers': list(ts)})
        return holes[key]

    g = go(list(trees), 0)
    if g is None:
        return None, None
    return g, order


def size(t):
    if isinstance(t, Hole) or not isinstance(t, list):
        return 1
    return 1 + sum(size(x) for x in t[1:] if isinstance(x, (list, Hole)))


def constants(t):
    if isinstance(t, Hole) or not isinstance(t, list) or not t:
        return set()
    if t[0] == 'const':
        return {t[1]}
    return set().union(*[constants(x) for x in t[1:] if isinstance(x, (list, Hole))]) if len(t) > 1 else set()


def render(t, names=None, holes=('P',)):
    """Lean surface syntax for a tree with explicit applications (`@c args`)."""
    names = names or []
    if isinstance(t, Hole):
        return holes[t.index]
    tag = t[0]
    if tag == 'bvar':
        return names[-1 - t[1]]
    if tag == 'const':
        return f'@{t[1]}'
    if tag == 'sort':
        return 'Prop' if t[1] == '0' else ('Type' if t[1] == '1' else f'Sort ({t[1]})')
    if tag == 'nat':
        return f'({t[1]} : ℕ)'
    if tag == 'str':
        return json.dumps(t[1])
    if tag == 'app':
        f, args = t, []
        while isinstance(f, list) and f[0] == 'app':
            args.append(f[2]); f = f[1]
        return '(' + ' '.join([render(f, names, holes)] + [render(a, names, holes) for a in reversed(args)]) + ')'
    if tag in ('pi', 'lam'):
        x = f'x{len(names)}'
        dom = render(t[1], names, holes)
        body = render(t[2], names + [x], holes)
        return f'(∀ ({x} : {dom}), {body})' if tag == 'pi' else f'(fun ({x} : {dom}) => {body})'
    raise ValueError(f'cannot render {tag}')


def candidates(statements, types, *, min_instances=2, min_size=8):
    """Abstraction candidates: generalisations of pairs (then extended greedily) that keep
    at least `min_size` tree nodes and have at least one hole."""
    out, seen = [], set()
    items = sorted(statements.items())
    for i, (a, ta) in enumerate(items):
        for b, tb in items[i + 1:]:
            g, holes = anti_unify([ta, tb], types)
            if g is None or not holes or size(g) < min_size:
                continue
            key = json.dumps(g, default=repr, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            members = [a, b]
            for c, tc in items:
                if c in members:
                    continue
                g2, h2 = anti_unify([statements[m] for m in members] + [tc], types)
                if g2 is not None and json.dumps(g2, default=repr, sort_keys=True) == key:
                    members.append(c)
            if len(members) >= min_instances:
                _, hs = anti_unify([statements[m] for m in members], types)
                out.append({'generalisation': g, 'holes': hs, 'members': sorted(members), 'size': size(g),
                            'constants': sorted(constants(g))})
    out.sort(key=lambda c: (-len(c['members']), -c['size'], c['members']))
    return out


def reify(candidate, name, namespace='RC'):
    """`def RC.<name> (P₀ : τ₀) … : Prop := body` and one instance check per member."""
    hs = candidate['holes']
    params = [f'P{h["index"]}' for h in hs]
    body = render(candidate['generalisation'], holes=params)
    binders = ' '.join(f'({p} : {h["type"]})' for p, h in zip(params, hs))
    definition = f'def {name} {binders} : Prop := {body}'
    checks = []
    for j, m in enumerate(candidate['members']):
        args = ' '.join(render(h['fillers'][j]) for h in hs)
        checks.append({'member': m, 'lean': f'example : @{m} = @{namespace}.{name} {args} := rfl'})
    return {'name': f'{namespace}.{name}', 'definition': definition, 'params': params,
            'hole_types': [h['type'] for h in hs], 'checks': checks,
            'uses_hidden': sorted(c for c in candidate['constants'] if c.split('.')[0] in HIDDEN or c in HIDDEN)}


def snapshot(declarations, modules):
    """The cutoff snapshot: statement trees of definitions whose value is a Prop statement,
    from the given (pre-cutoff) modules, with the digest of each tree."""
    out = {}
    for d in declarations:
        if d['module'] in modules and d['kind'] == 'def' and not d['internal'] and d.get('value_tree') \
                and d['type'] == 'Prop':
            out[d['name']] = d['value_tree']
    return out, {k: digest(v) for k, v in sorted(out.items())}


def type_table(declarations):
    """Type strings for constants defined in ingested modules (used to type holes)."""
    table = {d['name']: d['type'] for d in declarations}

    def types(t):
        if isinstance(t, list) and t and t[0] == 'const':
            return table.get(t[1])
        return None
    return types


__all__ = ['anti_unify', 'candidates', 'reify', 'render', 'snapshot', 'type_table', 'Hole', 'HIDDEN', 'size']
