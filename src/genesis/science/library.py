"""A self-extending primitive library for Genesis's acquisition language (Genesis Ω contract §4, §16.3).

A PRIMITIVE is a named, typed expression over the language's features and earlier primitives, with a CONTRACT: its
value range under the features' declared ranges (`interpret.interval`), that it is pure and total (it is an
expression of the language: no state, no I/O, defined everywhere), and its lineage (where it was synthesised from).
A LIBRARY is an immutable, versioned list of primitives; a new primitive makes a new version, whose ID is the digest
of its content; an earlier version is never changed, so rolling back is choosing an earlier version.

  * `synthesise(programs, library)`: the most frequent proper subtree (at least MIN_SIZE nodes, canonical form) of
    the given programs that is not already a primitive's body, with its count; the caller decides from evidence
    (e.g. the subtree recurs in the best rules found) whether to register it.
  * `register(library, name, body, lineage)`: a new version with the primitive added, after checks (the name is new
    and not a feature; the body uses only features and earlier primitives; it is a valid tree of the language).
  * Programs may use primitive names as leaves (`features(library)` gives the extended feature set to the search
    operators of `acquire`); `expand(program, library)` replaces them by their bodies; `check(program, library)`
    refuses a program that names a primitive the library version does not have, so a program written against a
    rolled-back primitive is refused, never silently reinterpreted.
  * `acq(program, library)`: the acquisition to run, already expanded (the scientist evaluates base-language trees).
"""
import json

from ..common import digest
from . import acquire as Q
from .design import FEATURES

MIN_SIZE = 3
EMPTY = {'schema': 'genesis-acquire-library-v1', 'primitives': [], 'parent': None}


def version(lib):
    return digest(lib)


def names(lib):
    return [p['name'] for p in lib['primitives']]


def features(lib):
    return tuple(FEATURES) + tuple(names(lib))


def _uses(t):
    if isinstance(t, str):
        return {t}
    if isinstance(t, float):
        return set()
    out = set()
    for k in t[1:]:
        out |= _uses(k)
    return out


def expand_tree(t, lib):
    body = {p['name']: p['body'] for p in lib['primitives']}

    def ex(x):
        if isinstance(x, str):
            return ex(body[x]) if x in body else x
        if isinstance(x, float):
            return x
        return [x[0]] + [ex(k) for k in x[1:]]
    return ex(t)


def expand(prog, lib):
    return {'agg': prog['agg'], 'expr': expand_tree(prog['expr'], lib)}


def check(prog, lib):
    """None, or why the program is not valid against this library version. The size limits apply to the program as
    written (a primitive is one node: the point of a library is compression); its expansion must be a valid tree
    of the base language."""
    why = Q.check(prog, features(lib))
    if why:
        return why
    try:
        Q._shape(expand(prog, lib)['expr'])
    except ValueError as e:
        return f'expansion is not a tree of the base language: {e}'
    return None


def register(lib, name, body, lineage):
    if not isinstance(name, str) or not name.isidentifier() or name in FEATURES or name in names(lib):
        raise ValueError(f'primitive name {name!r} must be a new identifier, not a feature or an existing primitive')
    unknown = _uses(body) - set(features(lib))
    if unknown:
        raise ValueError(f'the body uses unknown names {sorted(unknown)}')
    try:
        Q._shape(body, features(lib))
    except ValueError as e:
        raise ValueError(f'not a tree of the language: {e}')
    from .. import interpret as I
    lo, hi = I.interval(expand_tree(body, lib))
    entry = {'name': name, 'body': json.loads(json.dumps(body)), 'type': 'float', 'pure': True, 'total': True,
             'range': [lo, hi], 'lineage': lineage}
    return {'schema': lib['schema'], 'primitives': lib['primitives'] + [entry], 'parent': version(lib)}


def _subtrees(t):
    if isinstance(t, list):
        yield t
        for k in t[1:]:
            yield from _subtrees(k)


def synthesise(programs, lib):
    """(body, count) of the most frequent proper subtree of at least MIN_SIZE nodes, not already a primitive body;
    ties to the smaller tree, then the canonical text; None if there is none."""
    bodies = {json.dumps(p['body'], sort_keys=True) for p in lib['primitives']}
    counts = {}
    for prog in programs:
        seen = set()
        for sub in _subtrees(prog['expr']):
            if sub is prog['expr'] or Q._count(sub) < MIN_SIZE:
                continue
            k = json.dumps(sub, sort_keys=True)
            if k in bodies or k in seen:
                continue
            seen.add(k)
            counts[k] = counts.get(k, 0) + 1
    if not counts:
        return None
    best = max(counts, key=lambda k: (counts[k], -Q._count(json.loads(k)), k))
    return json.loads(best), counts[best]


def acq(prog, lib):
    why = check(prog, lib)
    if why:
        raise ValueError(why)
    return {'kind': 'program', 'program': expand(prog, lib)}
