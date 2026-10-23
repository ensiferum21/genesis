"""Solver programs, language v2 (B20_R115): B20_R78's language plus moves at the scale the evidence points to.

Why. Where the strongest search stops, the best edge sets differ globally, not by a local repair (B20_R99). Neither
the system's programs nor a fresh contract-disciplined search beat annealing-then-descent in B20_R78's language
(B20_R111, R112). Meanwhile, on max-cut, population moves that act on whole groups of variables (an elite pool, the
Houdayer cluster exchange, keeping what elites agree on) were part of the engine that leads Gset (B20_R104-R110).
This language gives the system such moves as primitives for the triangle-free problem, and nothing else. How to
assemble them is left to the search.

Language. Exactly B20_R78's (`solver_programs`, frozen and unchanged: its programs keep their meaning and identity)
plus three statements over an elite pool of at most POOL_K distinct edge sets kept by the interpreter:
  ["elite"]     offer the current edge set S to the pool (kept if new and larger than the pool's smallest when full)
  ["agree"]     with at least two elites: S := the edges every elite contains, completed greedily in random order
                (keep what the elites agree on, rebuild the rest)
  ["cluster"]   with at least two elites a, b: the edges where they differ form clusters (edges sharing a vertex);
                S := a with a random half of the clusters taken from b, rebuilt triangle-free (a's and b's common
                edges first, then the rest in random order, each added only if it closes no triangle), then
                completed greedily (Houdayer's move, on edge sets)
Both leave the encoding as it was; `descent` and `relabel` re-decode from the encoding as in B20_R78. Every edge set
stays triangle-free by construction, and the domain checker re-checks the returned witness.
"""
import copy
import random
import time

from . import solver_programs as SP

POOL_K = 8
POOL_OPS = ('elite', 'agree', 'cluster')
OPS = SP.OPS + POOL_OPS
CONTROL = SP.CONTROL
MAX_BLOCK, MAX_DEPTH, MAX_NODES = SP.MAX_BLOCK, SP.MAX_DEPTH, SP.MAX_NODES


def problems(program, licensed_reps):
    """[] or the reasons the program is not in language v2."""
    out = []
    if not isinstance(program, dict) or set(program) != {'rep', 'body'}:
        return ['a program is {rep, body}']
    if program['rep'] not in licensed_reps:
        out.append(f'representation {program["rep"]!r} is not licensed')
    nodes = [0]
    shape = {'init': (), 'descent': (), 'best': (), 'elite': (), 'agree': (), 'cluster': (),
             'relabel': (SP.SEL, SP.ACC, SP.NS), 'edges': (SP.MOVES, SP.ACC, SP.NS), 'sweep': (SP.MOVES, SP.ACC)}

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
        if op in shape:
            if len(args) != len(shape[op]) or any(type(a) not in (str, int) or a not in dom
                                                  for a, dom in zip(args, shape[op])):
                out.append(f'bad arguments in {s!r}')
            return
        if depth >= MAX_DEPTH:
            out.append('nested too deeply')
            return
        if op == 'repeat':
            if len(args) != 2 or args[0] not in SP.STALLS or type(args[0]) is not int:
                out.append(f'bad repeat {s[:2]!r}')
                return
            block(args[1], depth + 1)
        elif op == 'loop':
            if len(args) != 1:
                out.append('bad loop')
                return
            block(args[0], depth + 1)
        else:
            if len(args) != 3 or args[0] not in SP.FRACS or type(args[0]) is not float:
                out.append(f'bad split {s[:2]!r}')
                return
            block(args[1], depth + 1)
            block(args[2], depth + 1)
    block(program['body'], 0)
    if nodes[0] > MAX_NODES:
        out.append(f'more than {MAX_NODES} statements')
    return out


size = SP.size


class Machine(SP.Machine):
    def __init__(self, n, E, rep, rng):
        super().__init__(n, E, rep, rng)
        self.pool = []

    def _current(self):
        return frozenset(i for i in range(self.m) if self.inS[i])

    def elite(self):
        s = self._current()
        if any(s == p for p in self.pool):
            return
        if len(self.pool) < POOL_K:
            self.pool.append(s)
            return
        worst = min(range(len(self.pool)), key=lambda j: (len(self.pool[j]), j))
        if len(self.pool[worst]) < len(s):
            self.pool[worst] = s

    def _build(self, first, rest):
        """S := edges of `first` (in order) then of `rest` (shuffled), each added only if it closes no triangle;
        then completed greedily."""
        self.N = [0] * self.n
        self.inS = bytearray(self.m)
        self.size = 0
        rest = list(rest)
        self.rng.shuffle(rest)
        for i in list(first) + rest:
            u, v = self.E[i]
            if not self.inS[i] and not (self.N[u] & self.N[v]):
                self._add(i)
        self._fill(range(self.n))
        self._note()

    def agree(self):
        if len(self.pool) < 2:
            return
        common = sorted(frozenset.intersection(*self.pool))
        self._build(common, ())

    def cluster(self):
        if len(self.pool) < 2:
            return
        a, b = self.rng.sample(self.pool, 2)
        diff = a ^ b
        at = {}
        for i in diff:
            for x in self.E[i]:
                at.setdefault(x, []).append(i)
        seen, take = set(), set(a)
        for i0 in sorted(diff):
            if i0 in seen:
                continue
            comp, stack = [], [i0]
            seen.add(i0)
            while stack:
                i = stack.pop()
                comp.append(i)
                for x in self.E[i]:
                    for j in at[x]:
                        if j not in seen:
                            seen.add(j)
                            stack.append(j)
            if self.rng.random() < 0.5:
                for i in comp:
                    if i in a:
                        take.discard(i)
                    else:
                        take.add(i)
        common = sorted(a & b)
        self._build(common, sorted(take - (a & b)))

    def run_block(self, block, start, deadline):
        def temp():
            span = max(1e-9, deadline - start)
            frac = min(1.0, max(0.0, (time.process_time() - start) / span))
            return SP.T_HOT * (SP.T_COLD / SP.T_HOT) ** frac
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
            elif op == 'elite':
                self.elite()
            elif op == 'agree':
                self.agree()
            elif op == 'cluster':
                self.cluster()
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
    weights = [3 if o in ('init', 'descent', 'relabel', 'edges', 'sweep') else 1.5 if o in CONTROL + POOL_OPS else 1
               for o in ops]
    op = rng.choices(ops, weights)[0]
    if op in ('init', 'descent', 'best') + POOL_OPS:
        return [op]
    if op == 'relabel':
        return [op, rng.choice(SP.SEL), rng.choice(SP.ACC), rng.choice(SP.NS)]
    if op == 'edges':
        return [op, rng.choice(SP.MOVES), rng.choice(SP.ACC), rng.choice(SP.NS)]
    if op == 'sweep':
        return [op, rng.choice(SP.MOVES), rng.choice(SP.ACC)]
    if op == 'repeat':
        return [op, rng.choice(SP.STALLS), random_block(rng, depth + 1)]
    if op == 'loop':
        return [op, random_block(rng, depth + 1)]
    return [op, rng.choice(SP.FRACS), random_block(rng, depth + 1), random_block(rng, depth + 1)]


def random_block(rng, depth, length=None):
    return [random_stmt(rng, depth) for _ in range(length or rng.randint(1, 3))]


def random_program(rng, reps):
    while True:
        p = {'rep': rng.choice(sorted(reps)), 'body': random_block(rng, 0)}
        if not problems(p, reps):
            return p


def mutate(program, rng, reps):
    """B20_R78's mutation, drawing new statements from language v2."""
    for _ in range(50):
        p = copy.deepcopy(program)
        b, d = rng.choice(SP._blocks(p))
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
            new = (['repeat', rng.choice(SP.STALLS), inner] if w == 'repeat' else ['loop', inner] if w == 'loop'
                   else (['split', rng.choice(SP.FRACS), inner, random_block(rng, d + 1)] if rng.random() < 0.5
                         else ['split', rng.choice(SP.FRACS), random_block(rng, d + 1), inner]))
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
    for _ in range(20):
        child = copy.deepcopy(a)
        target, d = rng.choice(SP._blocks(child))
        donor, _ = rng.choice(SP._blocks(b))
        target[:] = copy.deepcopy(donor)
        if not problems(child, reps) and child != a:
            return child
    return mutate(a, rng, reps)
