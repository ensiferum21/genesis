"""Λ1, the front end of Genesis's engine language (B20_R153; `docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §2, §4).

**The languages.** Λ0 is mcx2's language (`candidate_kinds/mcx2.py`): a flat loop of physics operators with the S
and P guards. Λ1 is mcx3's (`candidate_kinds/mcx3.py`): Λ0 plus targets, ?-guards over run-time observables, repeats
and blocks, all of them the builder's (a human LANGUAGE change, Λ0 -> Λ1, never counted as Genesis's invention).
Λ1 + library is Λ1 with NAMED STATEMENTS: definitions with parameters, which a program calls like any statement.
The definitions are what Genesis is to add (X2, B20_R152); this module only gives them a meaning.

**A named statement** is a body (a Λ1 program, which may call earlier definitions only) with parameters $1..$k in
numeric places. A call `name(a1,...,ak)` is ONE item: its expansion is the body with the arguments substituted,
itself expanded, and wrapped in a block when it has more than one item (so that a guard before a call governs the
whole statement); a one-item body is that item (so that a named statement can be a named condition, a guard). A
parameter used in several places must satisfy every place's range.

**Libraries are versioned.** A `Library` is immutable; `extend` returns a new one whose `parent` is the old
version, and `version` is a hash of the definitions and the parent. A configuration never holds a call: `config`
expands a genome's program for the kind, so the engine and its checks do not depend on the library.

**Description length** (§2: the bound N of the expressiveness measure E(Λ, N)). `length` is the number of items a
program is written with (operators, guards, repeats, blocks and calls count one each; a call's arguments are part of
its token, as an operator's argument is). `bits` is a prefix code of the same program over its alphabet (for the
minimum-description-length scores of library learning): each item's symbol costs log2 of the alphabet size (mcx3's
symbols, an end-of-list mark and the library's names), each number costs the Elias gamma code of (value + 1), each
operator a target flag and, with a target, log2(3 + 255) bits, each ?-guard log2(4) + 1 bits for its observable and
comparison. `library_bits` is a library's own cost (each definition's name, arity and body).
"""
import hashlib
import json
import math

from ..candidate_kinds import mcx3 as K

NUMERIC = {'B': K.ARG_RANGE['B'], 'b': K.ARG_RANGE['b'], 'S': K.ARG_RANGE['S'], 'P': K.ARG_RANGE['P'],
           '*': K.ARG_RANGE['*'], **{'?' + o: r for o, r in K.OBSERVABLES.items()}}
SYMBOLS = tuple(K.OPS) + ('S', 'P', '?', '*', '[', 'end')


class Library:
    """An immutable, versioned set of named statements, in definition order."""

    def __init__(self, defs=(), parent=None):
        self.defs = tuple(defs)
        self.parent = parent
        self._by = {d['name']: d for d in self.defs}

    @property
    def version(self):
        blob = json.dumps({'parent': self.parent, 'defs': [(d['name'], d['params'], d['body']) for d in self.defs]})
        return 'lang-' + hashlib.sha256(blob.encode()).hexdigest()[:16]

    def names(self):
        return [d['name'] for d in self.defs]

    def get(self, name):
        if name not in self._by:
            raise ValueError(f'no named statement {name!r} in {self.version}')
        return self._by[name]

    def __len__(self):
        return len(self.defs)

    def guard_calls(self):
        """The names whose statement is a guard (its body is one guard, or a call of one)."""
        return frozenset(d['name'] for d in self.defs if d['guard'])

    def extend(self, name, body, provenance=None):
        """A new library with one more definition; a ValueError if it is not well formed."""
        if not K.NAME.match(name) or name in self._by:
            raise ValueError(f'bad or repeated name {name!r}')
        prog = K.parse(body, calls=True, params=True)
        uses = {}
        for x, (lo, hi), value in numeric_fields(prog, self):
            if isinstance(value, str):
                uses.setdefault(int(value[1:]), []).append((lo, hi))
        k = max(uses, default=0)
        if sorted(uses) != list(range(1, k + 1)):
            raise ValueError('parameters must be $1..$k, each used')
        ranges = []
        for i in range(1, k + 1):
            lo, hi = max(a for a, _ in uses[i]), min(b for _, b in uses[i])
            if lo > hi:
                raise ValueError(f'${i} has no value valid in all its places')
            ranges.append((lo, hi))
        gc = self.guard_calls()
        if any(x[0] == '*' and K._guardlike(x[2], gc) for x in K.walk(prog)):
            raise ValueError('a repeat governs a guard')
        canon = K.render(K.canonical(prog, gc))
        is_guard = len(prog) == 1 and K._guardlike(prog[0], self.guard_calls())
        d = {'name': name, 'params': k, 'ranges': ranges, 'body': canon, 'guard': is_guard, 'provenance': provenance}
        lib = Library(self.defs + (d,), parent=self.version)
        for args in ([lo for lo, _ in ranges], [hi for _, hi in ranges]):      # trial expansions at both ends
            call = name + (f'({",".join(map(str, args))})' if k else '')
            expand(K.parse(call + ' b1', calls=True), lib)
        return lib

    def to_json(self):
        return {'version': self.version, 'parent': self.parent, 'defs': [dict(d) for d in self.defs]}

    @classmethod
    def from_json(cls, data):
        """The library a `to_json` wrote, rebuilt definition by definition and checked against its version."""
        lib = Library()
        for d in data['defs']:
            lib = lib.extend(d['name'], d['body'], d.get('provenance'))
        if lib.version != data['version']:
            raise ValueError(f'library version {data["version"]} does not rebuild ({lib.version})')
        return lib


EMPTY = Library()


def numeric_fields(prog, library):
    """(item, (lo, hi), value) for every numeric place of the program, outermost first; a call's arguments take the
    ranges of the callee's parameters."""
    out = []
    for x in K.walk(prog):
        k = x[0]
        if k == 'op' and x[2] is not None:
            out.append((x, NUMERIC[x[1]], x[2]))
        elif k in ('S', 'P', '*'):
            out.append((x, NUMERIC[k], x[1]))
        elif k == '?':
            out.append((x, NUMERIC['?' + x[1]], x[3]))
        elif k == 'call':
            d = library.get(x[1])
            if len(x[2]) != d['params']:
                raise ValueError(f'{x[1]} takes {d["params"]} arguments')
            out += [(x, tuple(d['ranges'][j]), a) for j, a in enumerate(x[2])]
    return out


def _substitute(x, args):
    def num(v):
        return args[int(v[1:]) - 1] if isinstance(v, str) else v
    k = x[0]
    if k == 'op':
        return ('op', x[1], None if x[2] is None else num(x[2]), x[3])
    if k in ('S', 'P'):
        return (k, num(x[1]))
    if k == '?':
        return ('?', x[1], x[2], num(x[3]))
    if k == '*':
        return ('*', num(x[1]), _substitute(x[2], args))
    if k == '[':
        return ('[', tuple(_substitute(y, args) for y in x[1]))
    return ('call', x[1], tuple(num(a) for a in x[2]))


def expand(prog, library):
    """The program with every call expanded: the kind's canonical program, checked (a ValueError if it is not one)."""
    def item(x, depth):
        if depth > 64:
            raise ValueError('expansion too deep')
        k = x[0]
        if k == 'call':
            d = library.get(x[1])
            if len(x[2]) != d['params']:
                raise ValueError(f'{x[1]} takes {d["params"]} arguments')
            for j, a in enumerate(x[2]):
                lo, hi = d['ranges'][j]
                if not isinstance(a, int) or not lo <= a <= hi:
                    raise ValueError(f'{x[1]}: argument {j + 1} outside [{lo}, {hi}]')
            body = K.parse(d['body'], calls=True, params=True)
            body = tuple(item(_substitute(y, x[2]), depth + 1) for y in body)
            return body[0] if len(body) == 1 else ('[', body)
        if k == '[':
            return ('[', tuple(item(y, depth) for y in x[1]))
        if k == '*':
            return ('*', x[1], item(x[2], depth))
        return x
    out = K.canonical(tuple(item(x, 0) for x in prog))
    text = K.render(out)
    out = K.canonical(K.parse(text))                  # re-read: a call that expanded to a guard after a repeat fails
    why = K.check(out)
    if why:
        raise ValueError(why)
    return out


def length(prog):
    """The description length in items (the bound N of E(Λ, N))."""
    return K.size(prog)


def _gamma(v):
    return 2 * int(math.floor(math.log2(v + 1))) + 1


def bits(prog, library=EMPTY):
    """The prefix-code length of the program in bits (see the module docstring)."""
    sym = math.log2(len(SYMBOLS) + len(library))

    def item(x):
        k = x[0]
        if k == 'op':
            return sym + (0 if x[2] is None else _gamma(x[2])) + 1 + (0 if x[3] is None else math.log2(3 + 255))
        if k in ('S', 'P'):
            return sym + _gamma(x[1])
        if k == '?':
            return sym + 2 + 1 + _gamma(x[3])
        if k == '*':
            return sym + _gamma(x[1]) + item(x[2])
        if k == '[':
            return sym + sum(item(y) for y in x[1]) + sym
        return sym + sum(_gamma(a) for a in x[2])
    return sum(item(x) for x in prog) + sym


def library_bits(library):
    """A library's own description length: per definition, its name (8 bits per character), arity (gamma) and body
    (coded with the definitions before it)."""
    total, lib = 0.0, EMPTY
    for d in library.defs:
        body = K.parse(d['body'], calls=True, params=True)
        body = tuple(_substitute(x, [1] * d['params']) for x in body)       # parameters cost as the value 1
        total += 8 * len(d['name']) + _gamma(d['params']) + bits(body, lib)
        lib = Library(lib.defs + (d,), parent=lib.version)
    return total


def surface(text, library=EMPTY):
    """A program in Λ1 + library, read and canonical (calls not expanded); a ValueError if malformed."""
    prog = K.canonical(K.parse(text, calls=True), library.guard_calls())
    for x in K.walk(prog):
        if x[0] == 'call':
            library.get(x[1])
    expand(prog, library)
    return prog


def config(genome, library=EMPTY):
    """The kind configuration of a genome ({'prog': a program in Λ1 + library, and mcx3's options})."""
    c = dict(genome)
    c['prog'] = K.render(expand(surface(genome['prog'], library), library))
    why = K.check_config(c)
    if why:
        raise ValueError(why)
    return c
