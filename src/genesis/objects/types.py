"""The type registry of research objects (`docs/OMEGA_RECURSIVE_INVENTION.md` §3.3).

A type is a name, or a constructor applied to types: ['List', T], ['Map', K, V], ['Pair', A, B], ['Option', T]. Base
types have validators (pure functions of a value). A registry is an immutable value {'version', 'parent', 'types'}:
`register` returns a new registry naming its parent, so that new types are admitted the way library entries are, as
data with lineage, and an object written against a later registry is refused by an earlier one.

A new type is an ALIAS of a type expression over known types, optionally refined by a predicate drawn from the
registered refinements (non-empty, sorted, binary entries, ...): Genesis can define, for example, ['List', 'Int']
refined by 'binary' as an Assignment, without anyone writing a validator for it.
"""
import copy
import json

from ..common import digest

BASE = ('Any', 'Bool', 'Int', 'Real', 'Str', 'Graph', 'BQP', 'CSP', 'Relation', 'Gadget', 'Encoding', 'Assignment',
        'Distribution', 'Table', 'Expression', 'Program', 'Workflow', 'Proof', 'Statement', 'Process', 'Task',
        'Library', 'Object')
CONSTRUCTORS = {'List': 1, 'Map': 2, 'Pair': 2, 'Option': 1}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _graph(v):
    return (isinstance(v, dict) and _is_int(v.get('n')) and v['n'] >= 0 and isinstance(v.get('edges'), list) and
            all(isinstance(e, (list, tuple)) and len(e) in (2, 3) and all(_is_int(x) for x in e[:2]) and
                0 <= e[0] < v['n'] and 0 <= e[1] < v['n'] for e in v['edges']))


VALIDATORS = {
    'Any': lambda v: True,
    'Bool': lambda v: isinstance(v, bool),
    'Int': _is_int,
    'Real': lambda v: (isinstance(v, (int, float)) and not isinstance(v, bool)),
    'Str': lambda v: isinstance(v, str),
    'Graph': _graph,
    'BQP': lambda v: isinstance(v, dict) and {'n', 'constant', 'linear', 'quadratic', 'hard'} <= set(v),
    'CSP': lambda v: isinstance(v, dict) and 'n' in v and isinstance(v.get('constraints'), list),
    'Relation': lambda v: isinstance(v, dict) and _is_int(v.get('k')) and _is_int(v.get('table')),
    'Gadget': lambda v: isinstance(v, dict) and {'k', 'm', 'c', 'h', 'J'} <= set(v),
    'Encoding': lambda v: isinstance(v, dict) and {'D', 'b', 'code'} <= set(v),
    'Assignment': lambda v: isinstance(v, (list, tuple)) and all(x in (0, 1) and not isinstance(x, bool) for x in v),
    'Distribution': lambda v: (isinstance(v, dict) and all(isinstance(p, (int, float)) and p >= 0 for p in v.values())
                               and abs(sum(v.values()) - 1) < 1e-9),
    'Table': lambda v: isinstance(v, list) and all(isinstance(r, dict) for r in v),
    'Expression': lambda v: isinstance(v, (str, list, dict, int, float)),
    'Program': lambda v: isinstance(v, (dict, list, str)),
    'Workflow': lambda v: isinstance(v, dict) and isinstance(v.get('steps'), list),
    'Proof': lambda v: isinstance(v, dict),
    'Statement': lambda v: isinstance(v, (str, dict)),
    'Process': lambda v: isinstance(v, dict) and {'level', 'kind', 'params'} <= set(v),
    'Task': lambda v: isinstance(v, dict),
    'Library': lambda v: isinstance(v, dict) and 'schema' in v,
    'Object': lambda v: isinstance(v, dict) and v.get('schema') == 'genesis-research-object-v1',
}
REFINEMENTS = {
    'nonempty': lambda v: hasattr(v, '__len__') and len(v) > 0,
    'sorted': lambda v: isinstance(v, (list, tuple)) and list(v) == sorted(v),
    'binary': lambda v: isinstance(v, (list, tuple)) and all(x in (0, 1) for x in v),
    'nonnegative': lambda v: isinstance(v, (int, float)) and v >= 0,
    'probability': lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
    'distinct': lambda v: isinstance(v, (list, tuple)) and len(set(map(json.dumps, v))) == len(v),
}


def _version(types):
    return digest({'schema': 'genesis-object-types-v1', 'types': types})[:16]


SEED = {'parent': None, 'types': {}}
SEED['version'] = _version(SEED['types'])


def known(t, reg):
    if isinstance(t, str):
        return t in BASE or t in reg['types']
    if isinstance(t, list) and t and t[0] in CONSTRUCTORS:
        return len(t) == 1 + CONSTRUCTORS[t[0]] and all(known(x, reg) for x in t[1:])
    return False


def register(reg, name, expr, refine=(), lineage=None):
    """A new registry with the alias `name` = `expr` (a known type expression) refined by registered predicates."""
    if name in BASE or name in reg['types'] or name in CONSTRUCTORS:
        raise ValueError(f'type {name!r} exists')
    if not known(expr, reg):
        raise ValueError(f'unknown type expression {expr!r}')
    bad = [r for r in refine if r not in REFINEMENTS]
    if bad:
        raise ValueError(f'unknown refinements {bad}')
    types = copy.deepcopy(reg['types'])
    types[name] = {'expr': expr, 'refine': list(refine), 'lineage': lineage or {}}
    new = {'parent': reg['version'], 'types': types}
    new['version'] = _version(types)
    return new


def check(value, t, reg=SEED):
    """True when `value` belongs to type `t` under the registry."""
    if isinstance(t, str):
        if t in VALIDATORS:
            return bool(VALIDATORS[t](value))
        if t in reg['types']:
            d = reg['types'][t]
            return check(value, d['expr'], reg) and all(REFINEMENTS[r](value) for r in d['refine'])
        raise ValueError(f'unknown type {t!r}')
    head = t[0]
    if head == 'List':
        return isinstance(value, (list, tuple)) and all(check(v, t[1], reg) for v in value)
    if head == 'Map':
        return isinstance(value, dict) and all(check(k, t[1], reg) and check(v, t[2], reg) for k, v in value.items())
    if head == 'Pair':
        return isinstance(value, (list, tuple)) and len(value) == 2 and check(value[0], t[1], reg) and \
            check(value[1], t[2], reg)
    if head == 'Option':
        return value is None or check(value, t[1], reg)
    raise ValueError(f'unknown constructor {head!r}')


__all__ = ['BASE', 'CONSTRUCTORS', 'VALIDATORS', 'REFINEMENTS', 'SEED', 'known', 'register', 'check']
