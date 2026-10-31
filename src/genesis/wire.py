"""Plain data as tagged JSON, with shared and cyclic references kept (the obstacle loop's wire and job checkpoints).

It replaces pickle (defect B20R184-PICKLE: GI6-02 forbids unsafe deserialisation in shipped code). Decoding builds
only: None, booleans, numbers, strings, lists, tuples, dicts (any hashable keys), sets, frozensets, OrderedDicts,
instances of the classes the caller names (their `__dict__` restored, no constructor or other code run), and the
functions the caller names (by name, the caller's own object); anything else is refused. Every container and instance is encoded once: a second occurrence of the same object is a reference
to the first, so aliasing (two attributes holding the same list) survives a round trip as it did under pickle.

    {"l": [id, [items]]}  list            {"t": [id, [items]]}  tuple
    {"d": [id, [[k, v]...]]}  dict        {"od": [id, [[k, v]...]]}  OrderedDict
    {"s": [id, [items]]}  set             {"f": [id, [items]]}  frozenset
    {"o": [id, "Class", {name: value}]}   an instance of a named class
    {"fn": "name"}                        a named function
    {"r": id}                             the object first encoded with that id
Scalars are JSON's own (floats by repr, so they round-trip exactly; NaN and the infinities as JSON's extensions)."""
from collections import OrderedDict
import json

SCALARS = (type(None), bool, int, float, str)


class WireError(ValueError):
    pass


def _allowed(allowed):
    classes = {c.__name__: c for c in allowed if isinstance(c, type)}
    functions = {f.__name__: f for f in allowed if not isinstance(f, type) and callable(f)}
    return classes, functions


def to_data(obj, allowed=()):
    """The JSON-able form of obj. `allowed`: the classes whose instances, and the functions, that may be encoded."""
    names, functions = _allowed(allowed)
    ids = {}

    def enc(x):
        if isinstance(x, SCALARS):
            return x
        if callable(x) and not isinstance(x, type) and functions.get(getattr(x, '__name__', None)) is x:
            return {'fn': x.__name__}
        k = id(x)
        if k in ids:
            return {'r': ids[k][0]}
        n = len(ids)
        ids[k] = (n, x)                                    # keep x alive, so that its id is not reused
        if type(x) is list:
            return {'l': [n, [enc(v) for v in x]]}
        if type(x) is tuple:
            return {'t': [n, [enc(v) for v in x]]}
        if type(x) is OrderedDict:
            return {'od': [n, [[enc(a), enc(b)] for a, b in x.items()]]}
        if type(x) is dict:
            return {'d': [n, [[enc(a), enc(b)] for a, b in x.items()]]}
        if type(x) is set:
            return {'s': [n, [enc(v) for v in x]]}
        if type(x) is frozenset:
            return {'f': [n, [enc(v) for v in x]]}
        cls = type(x)
        if names.get(cls.__name__) is cls and hasattr(x, '__dict__'):
            return {'o': [n, cls.__name__, {a: enc(b) for a, b in vars(x).items()}]}
        raise WireError(f'cannot encode a {cls.__module__}.{cls.__qualname__}')
    return enc(obj)


def from_data(data, allowed=()):
    """The object `to_data` encoded. Refuses any other tag, and any class or function not named."""
    names, functions = _allowed(allowed)
    made = {}

    def dec(x):
        if isinstance(x, SCALARS):
            return x
        if isinstance(x, list):
            raise WireError('a bare JSON list is not a value of this format')
        if not isinstance(x, dict) or len(x) != 1:
            raise WireError('malformed value')
        (tag, body), = x.items()
        if tag == 'fn':
            if body not in functions:
                raise WireError(f'refused function {body!r}')
            return functions[body]
        if tag == 'r':
            if body not in made:
                raise WireError(f'a reference to {body!r} before its object')
            return made[body]
        if not isinstance(body, list) or not body or not isinstance(body[0], int) or body[0] in made:
            raise WireError('malformed tagged value')
        n = body[0]
        if tag == 'l':
            out = made[n] = []
            out.extend(dec(v) for v in body[1])
            return out
        if tag in ('d', 'od'):
            out = made[n] = OrderedDict() if tag == 'od' else {}
            for a, b in body[1]:
                out[dec(a)] = dec(b)
            return out
        if tag == 'o':
            cls = names.get(body[1])
            if cls is None:
                raise WireError(f'refused class {body[1]!r}')
            out = made[n] = cls.__new__(cls)
            out.__dict__.update({a: dec(b) for a, b in body[2].items()})
            return out
        if tag in ('t', 's', 'f'):                         # immutable or hashed: built from its items
            items = [dec(v) for v in body[1]]
            out = made[n] = tuple(items) if tag == 't' else set(items) if tag == 's' else frozenset(items)
            return out
        raise WireError(f'unknown tag {tag!r}')
    return dec(data)


def dumps(obj, allowed=()):
    return json.dumps(to_data(obj, allowed), separators=(',', ':'))


def loads(text, allowed=()):
    return from_data(json.loads(text), allowed)
