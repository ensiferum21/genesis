"""The inventor's search operators over Λ0 and Λ1 (B20_R153; `docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §2, §6).

**Why one implementation.** The factorial of B20_R151 crosses the language with the search. For the language factor
to be the language only, a search in Λ0 and a search in Λ1 must be the same search: the same algorithm, the same
operator code and the same draws wherever the two languages agree. Here the language is a parameter. In 'L0' the
operators make only mcx2 programs (flat; operators without targets; S and P guards); in 'L1' they also make the
constructs (targets, ?-guards, repeats, blocks) and, with a library, calls of named statements. A search over these
operators is `autonomy.feedback.steady_state_search` (or `selfimprove.search`) with `ops(...)` in place of
`selfimprove.engine_ops()`; nothing in the search changes.

**A genome** is {'prog': a canonical program in the language, written with the library's names, and mcx3's
options}; `lambda1.config` expands it for the kind. Every genome an operator returns parses, is canonical, expands
to a valid mcx3 program with at least one B or b, and has a description length (`lambda1.length`) of at most the
bound N (default 32, mcx2's MAX_STATEMENTS); in 'L0' it is also an mcx2 program.

**The operators** (each kind chosen with its weight, equal by default):
  * as in `selfimprove` (both languages): `arg` (rescale one number by a factor in [1/10, 10], clamped to its
    range; a 0 is redrawn), `insert` (a random statement into a list), `delete`, `replace` (a statement by a random
    one), `swap` (two adjacent items), `option` (one option redrawn), `duplicate` (an item repeated in place);
    in 'L0' the only list is the program, in 'L1' a list is the program or any block's;
  * 'L1' only: `target` (set, change or drop an operator's target), `guard` (put a random guard before an item, or
    change a ?-guard's observable or comparison), `block` (wrap two or three adjacent items in a block, or splice a
    block's items into its list), `repeat` (repeat an item 2 to 8 times, or drop a repeat);
  * 'L1' with a non-empty library: `call` (insert a call of a named statement, arguments drawn in its ranges, or
    replace an item by one).
  * crossover (both languages): with probability 1/2 a one-point splice of the two programs (selfimprove's), else an
    item of the first replaced by a copy of an item of the second (in 'L0' both are flat, so this replaces one
    statement); each option from either parent.
A random statement is one of mcx3's symbols drawn uniformly ('L0': B b X I C M H R D L S P, selfimprove's twelve;
'L1': those and ?), with B/b arguments log-uniform in [1, 2000], S in [1, 100000], P in [1, 20] (selfimprove's
draws); in 'L1' an operator other than b gets a random target with probability 1/4 (c, h, a, or one or two of the
levels 0-7), a ? guard a random observable, comparison and value (f uniform in 0..1000 by 50s; d, s, t log-uniform
in [1, 500], [1, 10^5], [1, 10^5]). A random engine has 1 to 6 statements (selfimprove's), in 'L1' each made a block
of two or three statements or a repeat (2 to 8) of an operator with probability 1/5; one statement is made a B or b
if none is; the options are drawn from mcx3's space.
"""
import copy
import math

from ..candidate_kinds import mcx3 as K
from . import lambda1 as L1

LANGS = ('L0', 'L1')
BOUND = K.LAMBDA0_MAX
L0_KINDS = ('arg', 'insert', 'delete', 'replace', 'swap', 'option', 'duplicate')
L1_KINDS = L0_KINDS + ('target', 'guard', 'block', 'repeat')
DRAW_HI = {'B': 2000, 'b': 2000, 'S': 100000, 'P': 20}
P_TARGET = 0.25
P_COMPOUND = 0.2


def kinds(lang, library=L1.EMPTY):
    if lang not in LANGS:
        raise ValueError(f'language must be one of {LANGS}')
    return L0_KINDS if lang == 'L0' else L1_KINDS + (('call',) if len(library) else ())


def _log_uniform(rng, lo, hi):
    return int(round(math.exp(rng.uniform(math.log(lo), math.log(hi)))))


# ---------------------------------------------------------------------------------- mutable items (lists, not tuples)

def _thaw(x):
    k = x[0]
    if k == '[':
        return ['[', [_thaw(y) for y in x[1]]]
    if k == '*':
        return ['*', x[1], _thaw(x[2])]
    if k == 'call':
        return ['call', x[1], list(x[2])]
    return list(x)


def _freeze(x):
    k = x[0]
    if k == '[':
        return ('[', tuple(_freeze(y) for y in x[1]))
    if k == '*':
        return ('*', x[1], _freeze(x[2]))
    if k == 'call':
        return ('call', x[1], tuple(x[2]))
    return tuple(x)


def _lists(top):
    """Every list of items: the program and each block's, in order."""
    out = []

    def lst(xs):
        out.append(xs)
        for x in xs:
            item(x)

    def item(x):
        if x[0] == '[':
            lst(x[1])
        elif x[0] == '*':
            item(x[2])
    lst(top)
    return out


def _places(top):
    """Every place an item sits in: (container, key) with container[key] the item; a repeat's body is (repeat, 2)."""
    out = []

    def lst(xs):
        for i, x in enumerate(xs):
            out.append((xs, i))
            item(x)

    def item(x):
        if x[0] == '[':
            lst(x[1])
        elif x[0] == '*':
            out.append((x, 2))
            item(x[2])
    lst(top)
    return out


def _nodes(top):
    return [c[k] for c, k in _places(top)]


# ----------------------------------------------------------------------------------------------- random statements

def random_target(rng):
    if rng.random() < 0.75:
        return rng.choice(('c', 'h', 'a'))
    return ''.join(sorted(set(rng.choice(K.LEVEL_DIGITS) for _ in range(rng.randint(1, 2)))))


def random_guard(rng, lang, g=None):
    g = g or rng.choice(('S', 'P') if lang == 'L0' else ('S', 'P', '?'))
    if g != '?':
        return [g, _log_uniform(rng, 1, DRAW_HI[g])]
    o = rng.choice('fdst')
    v = 50 * rng.randint(0, 20) if o == 'f' else _log_uniform(rng, 1, {'d': 500, 's': 10 ** 5, 't': 10 ** 5}[o])
    return ['?', o, rng.choice('<>'), v]


def random_op(rng, lang, op=None):
    op = op or rng.choice(K.OPS)
    arg = _log_uniform(rng, 1, DRAW_HI[op]) if op in 'Bb' else None
    tgt = random_target(rng) if lang == 'L1' and op != 'b' and rng.random() < P_TARGET else None
    return ['op', op, arg, tgt]


def random_stmt(rng, lang, guards=True):
    syms = tuple(K.OPS) + (('S', 'P') if lang == 'L0' else ('S', 'P', '?'))
    s = rng.choice(syms if guards else tuple(K.OPS))
    return random_guard(rng, lang, s) if s in ('S', 'P', '?') else random_op(rng, lang, s)


def _draw_cap(hi):
    """The top of a random draw in a range: the range's own when small, else selfimprove's caps."""
    return hi if hi <= 1000 else 2000 if hi <= 100000 else 100000


def random_call(rng, library):
    d = rng.choice(library.defs)
    return ['call', d['name'], [_log_uniform(rng, max(1, lo), max(max(1, lo), _draw_cap(hi))) for lo, hi in d['ranges']]]


def _repeat_body(c, k):
    """Whether the place (c, k) is a repeat's body (c a repeat node) rather than a list's k-th item."""
    return k == 2 and isinstance(c[0], str) and c[0] == '*'


def _random_options(rng):
    return {k: rng.choice(v) for k, v in K.SPACE.items()}


# ------------------------------------------------------------------------------------------------------- validity

def finish(top, options, lang, library=L1.EMPTY, bound=BOUND):
    """The genome of a mutable program and options, or None if it is not valid in the language at the bound."""
    try:
        prog = K.canonical(tuple(_freeze(x) for x in top), library.guard_calls())
        if not prog:
            return None
        text = K.render(prog)
        prog = L1.surface(text, library)
        if K.render(prog) != text or L1.length(prog) > bound:
            return None
        if lang == 'L0' and not K.is_lambda0(prog):
            return None
        L1.expand(prog, library)
    except ValueError:
        return None
    g = dict(options)
    g['prog'] = text
    return g


def _split(genome, library):
    prog = L1.surface(genome['prog'], library)
    return [_thaw(x) for x in prog], {k: genome[k] for k in K.SPACE}


def random_engine(rng, lang='L1', library=L1.EMPTY, bound=BOUND):
    while True:
        n = rng.randint(1, 6)
        top = []
        for _ in range(n):
            if lang == 'L1' and rng.random() < P_COMPOUND:
                if rng.random() < 0.5:
                    top.append(['[', [random_stmt(rng, lang) for _ in range(rng.randint(2, 3))]])
                else:
                    top.append(['*', rng.randint(2, 8), random_op(rng, lang)])
            else:
                top.append(random_stmt(rng, lang))
        if not any(x[0] == 'op' and x[1] in 'Bb' for x in _nodes(top)):
            c, k = rng.choice(_places(top))
            c[k] = random_op(rng, lang, rng.choice('Bb'))
        g = finish(top, _random_options(rng), lang, library, bound)
        if g is not None:
            return g


# ------------------------------------------------------------------------------------------------------- mutation

def _numeric_places(top, library):
    """(node, index, (lo, hi)) for every number of the program."""
    out = []
    for x in _nodes(top):
        k = x[0]
        if k == 'op' and x[2] is not None:
            out.append((x, 2, L1.NUMERIC[x[1]]))
        elif k in ('S', 'P', '*'):
            out.append((x, 1, L1.NUMERIC[k]))
        elif k == '?':
            out.append((x, 3, L1.NUMERIC['?' + x[1]]))
        elif k == 'call':
            d = library.get(x[1])
            out += [(x[2], j, tuple(d['ranges'][j])) for j in range(len(x[2]))]
    return out


def _apply(kind, top, opts, rng, lang, library):
    """Make one mutation of the given kind in place; False if it does not apply."""
    lists = _lists(top) if lang == 'L1' else [top]
    if kind == 'option':
        k = rng.choice(sorted(K.SPACE))
        opts[k] = rng.choice(K.SPACE[k])
        return True
    if kind == 'arg':
        places = _numeric_places(top, library)
        if not places:
            return False
        node, i, (lo, hi) = rng.choice(places)
        v = node[i]
        node[i] = (rng.randint(lo, min(hi, 10)) if v == 0 else
                   max(lo, min(hi, int(round(v * math.exp(rng.uniform(-math.log(10), math.log(10))))))))
        return True
    if kind == 'insert':
        xs = rng.choice(lists)
        xs.insert(rng.randint(0, len(xs)), random_stmt(rng, lang))
        return True
    if kind == 'delete':
        xs = [x for x in lists if len(x) >= 2]
        if not xs:
            return False
        xs = rng.choice(xs)
        del xs[rng.randrange(len(xs))]
        return True
    if kind == 'replace':
        places = [(c, k) for c, k in _places(top)] if lang == 'L1' else [(top, i) for i in range(len(top))]
        c, k = rng.choice(places)
        c[k] = random_stmt(rng, lang, guards=not _repeat_body(c, k))
        return True
    if kind == 'swap':
        xs = [x for x in lists if len(x) >= 2]
        if not xs:
            return False
        xs = rng.choice(xs)
        j = rng.randrange(len(xs) - 1)
        xs[j], xs[j + 1] = xs[j + 1], xs[j]
        return True
    if kind == 'duplicate':
        xs = rng.choice(lists)
        i = rng.randrange(len(xs))
        xs.insert(i, copy.deepcopy(xs[i]))
        return True
    if kind == 'target':
        ops = [x for x in _nodes(top) if x[0] == 'op']
        x = rng.choice(ops)
        if x[1] == 'b':
            x[1] = 'B'
            x[3] = random_target(rng)
        else:
            x[3] = None if x[3] is not None and rng.random() < 0.5 else random_target(rng)
        return True
    if kind == 'guard':
        qs = [x for x in _nodes(top) if x[0] == '?']
        if qs and rng.random() < 0.5:
            q = rng.choice(qs)
            if rng.random() < 0.5:
                q[2] = '<' if q[2] == '>' else '>'
            else:
                g = random_guard(rng, 'L1', '?')
                q[1], q[3] = g[1], g[3]
            return True
        xs = rng.choice(lists)
        xs.insert(rng.randrange(len(xs)), random_guard(rng, 'L1'))
        return True
    if kind == 'block':
        blocks = [(c, k) for c, k in _places(top) if c[k][0] == '[' and not _repeat_body(c, k)]
        if blocks and rng.random() < 0.5:
            c, k = rng.choice(blocks)
            c[k:k + 1] = c[k][1]
            return True
        xs = [x for x in lists if len(x) >= 2]
        if not xs:
            return False
        xs = rng.choice(xs)
        w = min(len(xs), rng.randint(2, 3))
        j = rng.randint(0, len(xs) - w)
        xs[j:j + w] = [['[', xs[j:j + w]]]
        return True
    if kind == 'repeat':
        reps = [(c, k) for c, k in _places(top) if c[k][0] == '*']
        if reps and rng.random() < 0.5:
            c, k = rng.choice(reps)
            c[k] = c[k][2]
            return True
        places = [(c, k) for c, k in _places(top) if c[k][0] not in K.GUARDS]
        if not places:
            return False
        c, k = rng.choice(places)
        c[k] = ['*', rng.randint(2, 8), c[k]]
        return True
    if kind == 'call':
        if not len(library):
            return False
        call = random_call(rng, library)
        xs = rng.choice(lists)
        if rng.random() < 0.5:
            xs.insert(rng.randint(0, len(xs)), call)
        else:
            xs[rng.randrange(len(xs))] = call
        return True
    raise ValueError(f'unknown mutation {kind}')


def mutate(genome, rng, lang='L1', library=L1.EMPTY, weights=None, used=None, bound=BOUND):
    """A valid mutant (or a copy of the genome if 50 tries give none); `used` receives the kind made."""
    ks = kinds(lang, library)
    w = [(weights or {}).get(k, 1.0) for k in ks]
    for _ in range(50):
        top, opts = _split(genome, library)
        m = rng.choices(ks, w)[0]
        if not _apply(m, top, opts, rng, lang, library):
            continue
        g = finish(top, opts, lang, library, bound)
        if g is not None and g != genome:
            if used is not None:
                used.append(m)
            return g
    return copy.deepcopy(genome)


def crossover(a, b, rng, lang='L1', library=L1.EMPTY, bound=BOUND):
    for _ in range(20):
        ta, _ = _split(a, library)
        tb, _ = _split(b, library)
        if rng.random() < 0.5:
            top = ta[:rng.randint(0, len(ta))] + tb[rng.randint(0, len(tb)):]
        else:
            top = ta
            places = _places(ta) if lang == 'L1' else [(ta, i) for i in range(len(ta))]
            donors = _nodes(tb) if lang == 'L1' else list(tb)
            c, k = rng.choice(places)
            c[k] = copy.deepcopy(rng.choice(donors))
        if not top:
            continue
        opts = {k: (a[k] if rng.random() < 0.5 else b[k]) for k in K.SPACE}
        g = finish(top, opts, lang, library, bound)
        if g is not None and g != a:
            return g
    return mutate(a, rng, lang, library, bound=bound)


def size(genome, library=L1.EMPTY):
    return L1.length(L1.surface(genome['prog'], library))


def ops(lang='L1', library=L1.EMPTY, weights=None, bound=BOUND):
    """The operators in the form `feedback.steady_state_search` takes."""
    kinds(lang, library)
    return {'random': lambda rng: random_engine(rng, lang, library, bound),
            'mutate': lambda p, rng: mutate(p, rng, lang, library, weights, bound=bound),
            'crossover': lambda x, y, rng: crossover(x, y, rng, lang, library, bound),
            'size': lambda p: size(p, library), 'library': library, 'lang': lang, 'bound': bound}
