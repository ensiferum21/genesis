"""Solver programs (B20_R78): a small, closed language of low-level search steps for the triangle-free domain, an
interpreter, and the random generation and mutation that a program search uses.

Why. B20_R77's engine, which beat CP-SAT and BURER2002 on DEV, was assembled by the builder: simulated bifurcation
(added in B20_R69 from the literature), a portfolio, and (1,2)-swap local search chosen after a diagnosis. Daniel
asked that the system find such a solver itself. This module gives it the parts and none of the assembly: no
simulated bifurcation (no continuous dynamics at all), no swap move, no portfolio. A program is data, checked
against the grammar below, and run by the interpreter; no code comes from data.

State. An encoding c (a label in Fin k per vertex, for one of the system's own licensed representations from B18,
such as cross_2, the cut) and a triangle-free edge set S of the host, kept as bitsets; and the best S seen so far.

Statements (a block is a list of 1..MAX_BLOCK statements; nesting depth at most MAX_DEPTH):
  ["init"]                      a random encoding; S := the decoded edges, completed greedily
  ["descent"]                   one-label descent on the decoded size (random vertex order, first improving label,
                                sweeps until none improves), then S := decoded and completed (B18's engine)
  ["relabel", SEL, ACC, N]      N single-vertex relabels, SEL in {random, best}, judged on the decoded size by ACC;
                                then S := decoded and completed
  ["edges", MOVE, ACC, N]       N moves on S, judged on |S| by ACC:
                                  drop: remove a random chosen edge, then add every edge at its two ends that closes
                                        no triangle (random order);
                                  force: add a random unchosen edge, first removing, for each vertex that blocks it,
                                        one of the two blocking edges (at random), then add free edges at the
                                        touched vertices
  ["sweep", MOVE, ACC]          the move once at every chosen edge (drop) or every unchosen edge (force), in random
                                order, each judged by ACC
  ["repeat", STALL, BLOCK]      run BLOCK until STALL runs in a row find no new best
  ["loop", BLOCK]               run BLOCK until the enclosing time share ends
  ["split", FRAC, BLOCK, BLOCK] the first block gets FRAC of the remaining time share, the second the rest
  ["best"]                      S := the best edge set seen so far
ACC in {improve (Δ > 0), sideways (Δ ≥ 0), always, anneal (Metropolis, T from 1 to 0.05 over the enclosing time
share)}. A program is {"rep": REP, "body": BLOCK}; the body runs again and again until the budget is spent.

Every step checks the clock; every edge set is triangle-free by construction, and the domain checker re-checks the
returned witness.
"""
import math
import random
import time

MAX_BLOCK, MAX_DEPTH, MAX_NODES = 6, 3, 30
SEL = ('random', 'best')
ACC = ('improve', 'sideways', 'always', 'anneal')
MOVES = ('drop', 'force')
NS = (1, 10, 100, 1000)
STALLS = (1, 3, 10, 30)
FRACS = (0.1, 0.25, 0.5, 0.75, 0.9)
OPS = ('init', 'descent', 'relabel', 'edges', 'sweep', 'repeat', 'loop', 'split', 'best')
CONTROL = ('repeat', 'loop', 'split')
T_HOT, T_COLD = 1.0, 0.05


# ----------------------------------------------------------------------------------------------- the grammar

def problems(program, licensed_reps):
    """[] or the reasons the program is not in the language."""
    out = []
    if not isinstance(program, dict) or set(program) != {'rep', 'body'}:
        return ['a program is {rep, body}']
    if program['rep'] not in licensed_reps:
        out.append(f'representation {program["rep"]!r} is not licensed')
    nodes = [0]

    def block(b, depth):
        if not isinstance(b, list) or not 1 <= len(b) <= MAX_BLOCK:
            out.append(f'a block has 1..{MAX_BLOCK} statements')
            return
        for s in b:
            stmt(s, depth)

    def stmt(s, depth):
        nodes[0] += 1
        if not isinstance(s, list) or not s or s[0] not in OPS:
            out.append(f'unknown statement {s!r}')
            return
        op, args = s[0], s[1:]
        shape = {'init': (), 'descent': (), 'best': (), 'relabel': (SEL, ACC, NS), 'edges': (MOVES, ACC, NS),
                 'sweep': (MOVES, ACC)}
        if op in shape:
            if len(args) != len(shape[op]) or any(type(a) not in (str, int) or a not in dom
                                                  for a, dom in zip(args, shape[op])):
                out.append(f'bad arguments in {s!r}')
            return
        if depth >= MAX_DEPTH:
            out.append('nested too deeply')
            return
        if op == 'repeat':
            if len(args) != 2 or args[0] not in STALLS or type(args[0]) is not int:
                out.append(f'bad repeat {s[:2]!r}')
                return
            block(args[1], depth + 1)
        elif op == 'loop':
            if len(args) != 1:
                out.append('bad loop')
                return
            block(args[0], depth + 1)
        else:
            if len(args) != 3 or args[0] not in FRACS or type(args[0]) is not float:
                out.append(f'bad split {s[:2]!r}')
                return
            block(args[1], depth + 1)
            block(args[2], depth + 1)
    block(program['body'], 0)
    if nodes[0] > MAX_NODES:
        out.append(f'more than {MAX_NODES} statements')
    return out


def size(program):
    def block(b):
        return sum(1 + (block(s[2]) if s[0] == 'repeat' else block(s[1]) if s[0] == 'loop'
                        else block(s[2]) + block(s[3]) if s[0] == 'split' else 0) for s in b)
    return block(program['body'])


# ----------------------------------------------------------------------------------------------- the interpreter

class Machine:
    def __init__(self, n, E, rep, rng):
        self.n, self.E, self.rng = n, E, rng
        self.m = len(E)
        self.eid = {e: i for i, e in enumerate(E)}
        self.inc = [[] for _ in range(n)]
        for i, (u, v) in enumerate(E):
            self.inc[u].append(i)
            self.inc[v].append(i)
        self.k = rep['k']
        py = rep['_py']
        self.keep = [[bool(py(a, b)) for b in range(self.k)] for a in range(self.k)]   # keep[c_low][c_high]
        self.nb = [[] for _ in range(n)]       # (other, self_is_low)
        for u, v in E:
            self.nb[u].append((v, True))
            self.nb[v].append((u, False))
        self.c = [0] * n
        self.N = [0] * n
        self.inS = bytearray(self.m)
        self.size = 0
        self.best = []
        self.log = None

    # --- edge set
    def _add(self, i):
        u, v = self.E[i]
        self.N[u] |= 1 << v
        self.N[v] |= 1 << u
        self.inS[i] = 1
        self.size += 1
        if self.log is not None:
            self.log.append(('a', i))

    def _rem(self, i):
        u, v = self.E[i]
        self.N[u] &= ~(1 << v)
        self.N[v] &= ~(1 << u)
        self.inS[i] = 0
        self.size -= 1
        if self.log is not None:
            self.log.append(('r', i))

    def _undo(self):
        log, self.log = self.log, None
        for op, i in reversed(log):
            (self._rem if op == 'a' else self._add)(i)

    def _fill(self, verts):
        cand = [i for x in verts for i in self.inc[x] if not self.inS[i]]
        self.rng.shuffle(cand)
        for i in cand:
            u, v = self.E[i]
            if not self.inS[i] and not (self.N[u] & self.N[v]):
                self._add(i)

    def _note(self):
        if self.size > len(self.best):
            self.best = [self.E[i] for i in range(self.m) if self.inS[i]]
            return True
        return False

    def _set_edges(self, chosen):
        self.N = [0] * self.n
        self.inS = bytearray(self.m)
        self.size = 0
        for e in chosen:
            self._add(self.eid[e])

    # --- encoding
    def _kept_at(self, v, label):
        c, keep = self.c, self.keep
        return sum(keep[label][c[w]] if low else keep[c[w]][label] for w, low in self.nb[v])

    def _decode_complete(self):
        c, keep = self.c, self.keep
        self._set_edges([(u, v) for u, v in self.E if keep[c[u]][c[v]]])
        self._fill(range(self.n))
        self._note()

    def init(self):
        self.c = [self.rng.randrange(self.k) for _ in range(self.n)]
        self._decode_complete()

    def descent(self, deadline):
        improved = True
        while improved and time.process_time() < deadline:
            improved = False
            for v in self.rng.sample(range(self.n), self.n):
                cur = self._kept_at(v, self.c[v])
                for alt in range(self.k):
                    if alt != self.c[v]:
                        new = self._kept_at(v, alt)
                        if new > cur:
                            self.c[v], cur, improved = alt, new, True
        self._decode_complete()

    def relabel(self, sel, acc, count, deadline, temp):
        for j in range(count):
            if j % 16 == 15 and time.process_time() >= deadline:
                break
            if sel == 'random':
                v = self.rng.randrange(self.n)
                alt = (self.c[v] + 1 + self.rng.randrange(self.k - 1)) % self.k
                delta = self._kept_at(v, alt) - self._kept_at(v, self.c[v])
            else:
                v, alt, delta = None, None, None
                for x in range(self.n):
                    here = self._kept_at(x, self.c[x])
                    for a in range(self.k):
                        if a != self.c[x]:
                            d = self._kept_at(x, a) - here
                            if delta is None or d > delta or (d == delta and self.rng.random() < 0.5):
                                v, alt, delta = x, a, d
            if self._accept(acc, delta, temp()):
                self.c[v] = alt
        self._decode_complete()

    def _move(self, move, i):
        """Apply one move at edge i (drop: a chosen edge; force: an unchosen one); the change in |S|."""
        before = self.size
        u, v = self.E[i]
        if move == 'drop':
            self._rem(i)
            self._fill((u, v))
        else:
            b = self.N[u] & self.N[v]
            touched = {u, v}
            while b:
                w = (b & -b).bit_length() - 1
                b &= b - 1
                x = u if self.rng.random() < 0.5 else v
                self._rem(self.eid[(x, w) if x < w else (w, x)])
                touched.add(w)
            self._add(i)
            self._fill(touched)
        return self.size - before

    def _accept(self, acc, delta, T):
        if acc == 'always' or delta > 0 or (delta == 0 and acc != 'improve'):
            return True
        return acc == 'anneal' and self.rng.random() < math.exp(delta / T)

    def _try(self, move, i, acc, T):
        self.log = []
        d = self._move(move, i)
        if self._accept(acc, d, T):
            self.log = None
            self._note()
        else:
            self._undo()

    def edges(self, move, acc, count, deadline, temp):
        for j in range(count):
            if j % 16 == 15 and time.process_time() >= deadline:
                break
            pool = [i for i in range(self.m) if bool(self.inS[i]) == (move == 'drop')]
            if not pool:
                break
            self._try(move, self.rng.choice(pool), acc, temp())

    def sweep(self, move, acc, deadline, temp):
        order = [i for i in range(self.m) if bool(self.inS[i]) == (move == 'drop')]
        self.rng.shuffle(order)
        for j, i in enumerate(order):
            if j % 16 == 15 and time.process_time() >= deadline:
                break
            if bool(self.inS[i]) == (move == 'drop'):
                self._try(move, i, acc, temp())

    def to_best(self):
        if self.best:
            self._set_edges(self.best)

    # --- control
    def run_block(self, block, start, deadline):
        def temp():
            span = max(1e-9, deadline - start)
            frac = min(1.0, max(0.0, (time.process_time() - start) / span))
            return T_HOT * (T_COLD / T_HOT) ** frac
        for s in block:
            if time.process_time() >= deadline:
                return
            op = s[0]
            if op == 'init':
                self.init()
            elif op == 'descent':
                self.descent(deadline)
            elif op == 'relabel':
                self.relabel(s[1], s[2], s[3], deadline, temp)
            elif op == 'edges':
                self.edges(s[1], s[2], s[3], deadline, temp)
            elif op == 'sweep':
                self.sweep(s[1], s[2], deadline, temp)
            elif op == 'best':
                self.to_best()
            elif op == 'repeat':
                stall = 0
                while stall < s[1] and time.process_time() < deadline:
                    before = len(self.best)
                    self.run_block(s[2], start, deadline)
                    stall = 0 if len(self.best) > before else stall + 1
            elif op == 'loop':
                t0 = time.process_time()
                while time.process_time() < deadline:
                    self.run_block(s[1], t0, deadline)
            elif op == 'split':
                now = time.process_time()
                mid = now + s[1] * (deadline - now)
                self.run_block(s[2], now, mid)
                self.run_block(s[3], mid, deadline)
            self._note()


def run(program, rep, n, edges, cpu_seconds, seed):
    """The best triangle-free edge set the program finds within the CPU budget (the body repeats until then)."""
    start = time.process_time()
    deadline = start + cpu_seconds
    E = [tuple(e) for e in edges]
    rng = random.Random(seed)
    m = Machine(n, E, rep, rng)
    if not E:
        return []
    m.init()
    while time.process_time() < deadline:
        t0 = time.process_time()
        m.run_block(program['body'], t0, deadline)
    return sorted(m.best)


# ----------------------------------------------------------------------------------------------- generation and mutation

def random_stmt(rng, depth):
    ops = list(OPS) if depth < MAX_DEPTH else [o for o in OPS if o not in CONTROL]
    weights = [3 if o in ('init', 'descent', 'relabel', 'edges', 'sweep') else 1.5 if o in CONTROL else 1 for o in ops]
    op = rng.choices(ops, weights)[0]
    if op in ('init', 'descent', 'best'):
        return [op]
    if op == 'relabel':
        return [op, rng.choice(SEL), rng.choice(ACC), rng.choice(NS)]
    if op == 'edges':
        return [op, rng.choice(MOVES), rng.choice(ACC), rng.choice(NS)]
    if op == 'sweep':
        return [op, rng.choice(MOVES), rng.choice(ACC)]
    if op == 'repeat':
        return [op, rng.choice(STALLS), random_block(rng, depth + 1)]
    if op == 'loop':
        return [op, random_block(rng, depth + 1)]
    return [op, rng.choice(FRACS), random_block(rng, depth + 1), random_block(rng, depth + 1)]


def random_block(rng, depth, length=None):
    return [random_stmt(rng, depth) for _ in range(length or rng.randint(1, 3))]


def random_program(rng, reps):
    """A random program in the language. Drawn again until it is in it: nested blocks can exceed MAX_NODES (found
    by a B20_R82 test before B20_R79's search had produced anything; B20_R79 was restarted with this fix)."""
    while True:
        p = {'rep': rng.choice(sorted(reps)), 'body': random_block(rng, 0)}
        if not problems(p, reps):
            return p


def _blocks(program):
    """Every block of the program with its depth, as (list object, depth)."""
    out = []

    def walk(b, d):
        out.append((b, d))
        for s in b:
            if s[0] == 'repeat':
                walk(s[2], d + 1)
            elif s[0] == 'loop':
                walk(s[1], d + 1)
            elif s[0] == 'split':
                walk(s[2], d + 1)
                walk(s[3], d + 1)
    walk(program['body'], 0)
    return out


def mutate(program, rng, reps):
    """A copy of the program with one random edit; retried until the result is in the language."""
    import copy
    for _ in range(50):
        p = copy.deepcopy(program)
        b, d = rng.choice(_blocks(p))
        kind = rng.choice(('param', 'param', 'replace', 'insert', 'delete', 'wrap', 'unwrap', 'rep'))
        i = rng.randrange(len(b))
        s = b[i]
        if kind == 'param':
            if s[0] == 'relabel':
                j = rng.randrange(1, 4)
                s[j] = rng.choice((SEL, ACC, NS)[j - 1])
            elif s[0] in ('edges', 'sweep'):
                j = rng.randrange(1, len(s))
                s[j] = rng.choice((MOVES, ACC, NS)[j - 1])
            elif s[0] == 'repeat':
                s[1] = rng.choice(STALLS)
            elif s[0] == 'split':
                s[1] = rng.choice(FRACS)
            else:
                continue
        elif kind == 'replace':
            b[i] = random_stmt(rng, d)
        elif kind == 'insert':
            b.insert(rng.randint(0, len(b)), random_stmt(rng, d))
        elif kind == 'delete':
            if len(b) < 2:
                continue
            del b[i]
        elif kind == 'wrap':
            if d >= MAX_DEPTH:
                continue
            j = rng.randint(i + 1, len(b))
            inner = b[i:j]
            w = rng.choice(CONTROL)
            new = (['repeat', rng.choice(STALLS), inner] if w == 'repeat' else ['loop', inner] if w == 'loop'
                   else (['split', rng.choice(FRACS), inner, random_block(rng, d + 1)] if rng.random() < 0.5
                         else ['split', rng.choice(FRACS), random_block(rng, d + 1), inner]))
            b[i:j] = [new]
        elif kind == 'unwrap':
            if s[0] not in CONTROL:
                continue
            inner = s[2] if s[0] == 'repeat' else s[1] if s[0] == 'loop' else s[rng.choice((2, 3))]
            b[i:i + 1] = inner
        else:
            p['rep'] = rng.choice(sorted(reps))
        if not problems(p, reps) and p != program:
            return p
    return copy.deepcopy(program)


def crossover(a, b, rng, reps):
    """Replace a random block of a (or a's body) by a copy of a random block of b, if the result is valid."""
    import copy
    for _ in range(20):
        child = copy.deepcopy(a)
        target, d = rng.choice(_blocks(child))
        donor, _ = rng.choice(_blocks(b))
        target[:] = copy.deepcopy(donor)
        if not problems(child, reps) and child != a:
            return child
    return mutate(a, rng, reps)
