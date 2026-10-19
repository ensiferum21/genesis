"""Solver programs with a library (B20_R82): each generation's discovered program becomes a building block of the
next, so that discoveries can compound (GV5).

Why. The roadmap's GV5 asks for gains across generations: three executable generations, each judged against the one
before on fresh panels, with causal evidence. In program search the natural way for one generation's result to carry
into the next is a library of abstractions, as in library learning (DreamCoder: Ellis et al., PLDI 2021): a found
program's body becomes a statement the next search can call, combine and modify around.

Language. Exactly B20_R78's (`solver_programs`, unchanged and frozen) plus one statement:
  ["macro", I]    run library entry I (a block) as a sub-block, with the enclosing time share.
A library is a list of blocks; entry I is valid when it is a B20_R78 block that may also call entries below I (so
there are no cycles). A program with a library is {"rep": REP, "body": BLOCK, "library": [BLOCK, ...]}; in the
search the library is fixed, and only the body evolves. A macro counts as one statement for size and depth.

Everything else (the interpreter's steps, the clock, triangle-freeness, the domain re-check) is B20_R78's.
"""
import copy
import time

from . import solver_programs as SP

OPS = SP.OPS + ('macro',)


def problems(program, licensed_reps):
    """[] or the reasons the program (with its library) is not in the language."""
    if not isinstance(program, dict) or set(program) != {'rep', 'body', 'library'}:
        return ['a program with a library is {rep, body, library}']
    lib = program['library']
    if not isinstance(lib, list) or len(lib) > 8:
        return ['a library is a list of at most 8 blocks']
    out = []
    for i, entry in enumerate(lib):
        out += [f'library entry {i}: {p}' for p in _block_problems(entry, program['rep'], licensed_reps, i)]
    out += _block_problems(program['body'], program['rep'], licensed_reps, len(lib))
    return out


def _block_problems(block, rep, licensed_reps, n_macros):
    out = []
    if rep not in licensed_reps:
        out.append(f'representation {rep!r} is not licensed')
    nodes = [0]

    def blk(b, depth):
        if not isinstance(b, list) or not 1 <= len(b) <= SP.MAX_BLOCK:
            out.append(f'a block has 1..{SP.MAX_BLOCK} statements')
            return
        for s in b:
            stmt(s, depth)

    def stmt(s, depth):
        nodes[0] += 1
        if isinstance(s, list) and s and s[0] == 'macro':
            if len(s) != 2 or type(s[1]) is not int or not 0 <= s[1] < n_macros:
                out.append(f'bad macro {s!r}')
            return
        if not isinstance(s, list) or not s or s[0] not in SP.OPS:
            out.append(f'unknown statement {s!r}')
            return
        if s[0] in SP.CONTROL and depth >= SP.MAX_DEPTH:
            out.append('nested too deeply')
            return
        # the statement's own shape, by B20_R78's grammar, with each nested block replaced by a valid placeholder;
        # the nested blocks themselves are checked here, so that they may call macros
        shell = copy.deepcopy(s)
        for j in _nested_positions(s):
            if len(shell) > j:
                shell[j] = [['init']]
        bad = SP.problems({'rep': rep, 'body': [shell]}, {rep})
        if bad:
            out.extend(bad)
            return
        for b in _nested(s):
            blk(b, depth + 1)
    blk(block, 0)
    if nodes[0] > SP.MAX_NODES:
        out.append(f'more than {SP.MAX_NODES} statements')
    return out


def _nested_positions(s):
    return {'repeat': (2,), 'loop': (1,), 'split': (2, 3)}.get(s[0], ())


def _nested(s):
    return [s[j] for j in _nested_positions(s)]


def size(program):
    def block(b):
        return sum(1 + sum(block(x) for x in _nested(s)) for s in b)
    return block(program['body'])


class Machine(SP.Machine):
    def __init__(self, n, E, rep, rng, library):
        super().__init__(n, E, rep, rng)
        self.library = library

    def run_block(self, block, start, deadline):
        plain = []
        for s in block:
            if s[0] == 'macro':
                if plain:
                    super().run_block(plain, start, deadline)
                    plain = []
                if time.process_time() >= deadline:
                    return
                self.run_block(self.library[s[1]], start, deadline)
                self._note()
            else:
                plain.append(s)        # B20_R78's control statements call self.run_block, so nested macros run here
        if plain:
            super().run_block(plain, start, deadline)


def run(program, rep, n, edges, cpu_seconds, seed):
    import random
    start = time.process_time()
    deadline = start + cpu_seconds
    E = [tuple(e) for e in edges]
    if not E:
        return []
    m = Machine(n, E, rep, random.Random(seed), program['library'])
    m.init()
    while time.process_time() < deadline:
        t0 = time.process_time()
        m.run_block(program['body'], t0, deadline)
    return sorted(m.best)


# ----------------------------------------------------------------------------------------------- generation and mutation

def random_stmt(rng, depth, n_macros):
    if n_macros and rng.random() < 0.3:
        return ['macro', rng.randrange(n_macros)]
    s = SP.random_stmt(rng, depth)
    for j in _nested_positions(s):
        s[j] = random_block(rng, depth + 1, n_macros)
    return s


def random_block(rng, depth, n_macros, length=None):
    return [random_stmt(rng, depth, n_macros) for _ in range(length or rng.randint(1, 3))]


def random_program(rng, reps, library):
    """A random program in the language with this library, drawn again until it is in it (as B20_R78's)."""
    while True:
        p = {'rep': rng.choice(sorted(reps)), 'body': random_block(rng, 0, len(library)), 'library': library}
        if not problems(p, reps):
            return p


def _blocks(program):
    out = []

    def walk(b, d):
        out.append((b, d))
        for s in b:
            for x in _nested(s):
                walk(x, d + 1)
    walk(program['body'], 0)
    return out


def mutate(program, rng, reps):
    """As B20_R78's mutation, over the body only, with macros as one more kind of statement."""
    nm = len(program['library'])
    for _ in range(50):
        p = copy.deepcopy(program)
        b, d = rng.choice(_blocks(p))
        kind = rng.choice(('param', 'param', 'replace', 'insert', 'delete', 'wrap', 'unwrap', 'rep'))
        i = rng.randrange(len(b))
        s = b[i]
        if kind == 'param':
            if s[0] == 'relabel':
                j = rng.randrange(1, 4)
                s[j] = rng.choice((SP.SEL, SP.ACC, SP.NS)[j - 1])
            elif s[0] in ('edges', 'sweep'):
                j = rng.randrange(1, len(s))
                s[j] = rng.choice((SP.MOVES, SP.ACC, SP.NS)[j - 1])
            elif s[0] == 'repeat':
                s[1] = rng.choice(SP.STALLS)
            elif s[0] == 'split':
                s[1] = rng.choice(SP.FRACS)
            elif s[0] == 'macro' and nm > 1:
                s[1] = rng.randrange(nm)
            else:
                continue
        elif kind == 'replace':
            b[i] = random_stmt(rng, d, nm)
        elif kind == 'insert':
            b.insert(rng.randint(0, len(b)), random_stmt(rng, d, nm))
        elif kind == 'delete':
            if len(b) < 2:
                continue
            del b[i]
        elif kind == 'wrap':
            if d >= SP.MAX_DEPTH:
                continue
            j = rng.randint(i + 1, len(b))
            inner = b[i:j]
            w = rng.choice(SP.CONTROL)
            new = (['repeat', rng.choice(SP.STALLS), inner] if w == 'repeat' else ['loop', inner] if w == 'loop'
                   else (['split', rng.choice(SP.FRACS), inner, random_block(rng, d + 1, nm)] if rng.random() < 0.5
                         else ['split', rng.choice(SP.FRACS), random_block(rng, d + 1, nm), inner]))
            b[i:j] = [new]
        elif kind == 'unwrap':
            if s[0] not in SP.CONTROL:
                continue
            nested = _nested(s)
            b[i:i + 1] = rng.choice(nested)
        else:
            p['rep'] = rng.choice(sorted(reps))
        if not problems(p, reps) and p != program:
            return p
    return copy.deepcopy(program)


def crossover(a, b, rng, reps):
    for _ in range(20):
        child = copy.deepcopy(a)
        target, _ = rng.choice(_blocks(child))
        donor, _ = rng.choice(_blocks(b))
        target[:] = copy.deepcopy(donor)
        if not problems(child, reps) and child != a:
            return child
    return mutate(a, rng, reps)


def as_library_entry(program):
    """A discovered program's body, for the next generation's library (its representation is not carried: the next
    generation's program chooses its own)."""
    return copy.deepcopy(program['body'])
