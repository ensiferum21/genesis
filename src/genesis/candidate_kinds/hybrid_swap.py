"""Candidate kind `hybrid-swap-v1` (registry v2, B20_R77): a portfolio of cut searches, then iterated local search
with (1,2)-swaps on the triangle-free problem itself.

Why (B20_R76 and its diagnosis, disclosed in the B20_R77 record). Every fast arm of B20_R76 searches two-colourings
(a cut) and then completes the cut greedily. On the hardest host (n63, 490 edges) they all stopped at 312-314, while
CP-SAT, given 60 s, found 315, certified optimal. That optimum is not a cut plus a completion of it: its largest
bipartite part has 300 edges, and its own two-colouring, with all of that colouring's cut edges kept, completes to
only 314. Reaching 315 means giving up cut edges to admit more same-side edges. A search over cuts optimizes the
wrong objective there; a move in the space of edge sets can do it. Second, different searches find different local
optima, and on one B20_R76 host dSB, one-flip descent and E1's candidate each reached the target in only 1 of 15
runs; mixing searches is what an algorithm portfolio does (Huberman, Lukose and Hogg, Science 1997; Gomes and
Selman, Artificial Intelligence 2001), and in the development looks adding descent restarts to dSB took this engine
on that host from 0 to 3-4 of 4 runs.

Algorithm (fixed; data-only parameters {cpu_seconds}).
  Phase 1, a portfolio, for FRAC = 0.8 of the budget, alternating:
    * a batch of discrete simulated bifurcation, exactly `ising-dsb-v1`'s dynamics (REPLICAS 32, STEPS 400,
      A0 1, DT 0.5, c0 = 0.5 / (rms(J) sqrt(n)), inelastic walls), each replica's cut completed greedily;
    * for the same CPU time (DESC_SHARE = 0.5 of the portfolio), one-flip descent from random two-colourings
      (flip a vertex while more of its neighbours are on its side than across), each local optimum completed;
    * a pool keeps the K = 4 best distinct completed colourings (by completed size).
  Phase 2, for the rest of the budget: on each pool member, (1,2)-swaps until none applies, then iterated local
  search round-robin over the members. A (1,2)-swap removes one chosen edge e and adds two edges that only e blocked
  (an unchosen edge {u, v} is blocked by w when {u, w} and {v, w} are chosen; it is freed by removing e only when w
  is its sole blocker and e is one of those two edges), then adds any edge that has become free. This is the move of
  Andrade, Resende and Werneck (J. Heuristics 2012) for maximum independent set, applied to the hypergraph whose
  vertices are host edges and whose hyperedges are host triangles. An iteration forces in one random unchosen edge
  (removing, for each of its blockers, one of the two blocking edges at random), adds free edges, applies (1,2)-swaps
  until none applies, and keeps the result if it is no smaller than the member's current one (else with probability
  P_WORSE = 0.1, else restores the member).
  The largest edge set seen is returned. The domain checker re-checks the witness; the claimed value is never trusted.

Not new ideas: dSB, descent, portfolios and (1,2)-swap ILS are published methods; the builder combined them, guided
by the diagnosis above. The system's own representation search did not propose this.

Start-up and fairness. As `ising-dsb-v1`: the child pins itself to one CPU and limits BLAS to one thread before
importing numpy, and the numpy import counts against the budget (the disclosed bias of B20_R70). Domain:
triangle_free_host_v1 only.
"""
import os
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/hybrid_swap.py',)
REPLICAS, STEPS, A0, DT = 32, 400, 1.0, 0.5          # equal to ising_dsb's (tested)
FRAC, DESC_SHARE, K, P_WORSE = 0.8, 0.5, 4, 0.1


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    if domain not in DOMAINS:
        return f'hybrid-swap-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'hybrid-swap-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    return None


class Solution:
    """A triangle-free edge set of the host as bitsets: N[u] holds u's chosen neighbours."""

    def __init__(self, n, E, inc, eid, rng, chosen=()):
        self.n, self.E, self.inc, self.eid, self.rng = n, E, inc, eid, rng
        self.N = [0] * n
        self.inS = bytearray(len(E))
        self.size = 0
        for e in chosen:
            self.add(eid[e])
        self.fill(range(n))

    def add(self, i):
        u, v = self.E[i]
        self.N[u] |= 1 << v
        self.N[v] |= 1 << u
        self.inS[i] = 1
        self.size += 1

    def remove(self, i):
        u, v = self.E[i]
        self.N[u] &= ~(1 << v)
        self.N[v] &= ~(1 << u)
        self.inS[i] = 0
        self.size -= 1

    def fill(self, verts):
        """Add, in random order, every unchosen edge at these vertices that closes no triangle."""
        cand = [i for x in verts for i in self.inc[x] if not self.inS[i]]
        self.rng.shuffle(cand)
        for i in cand:
            u, v = self.E[i]
            if not self.inS[i] and not (self.N[u] & self.N[v]):
                self.add(i)

    def swaps(self, deadline):
        """Apply (1,2)-swaps until none applies (or the deadline); the number applied."""
        E, N, inS, inc = self.E, self.N, self.inS, self.inc
        order = list(range(len(E)))
        applied = 0
        while time.process_time() < deadline:
            self.rng.shuffle(order)
            improved = False
            for e in order:
                if not inS[e]:
                    continue
                a, b = E[e]
                ma, mb = 1 << a, 1 << b
                cand = ([i for i in inc[a] if not inS[i] and N[E[i][0]] & N[E[i][1]] == mb]
                        + [i for i in inc[b] if not inS[i] and N[E[i][0]] & N[E[i][1]] == ma])
                if len(cand) < 2:
                    continue
                self.remove(e)
                self.rng.shuffle(cand)
                done = False
                for x in range(len(cand)):
                    f = cand[x]
                    self.add(f)
                    for y in range(x + 1, len(cand)):
                        u, v = E[cand[y]]
                        if not (N[u] & N[v]):
                            self.add(cand[y])
                            self.fill(E[e])
                            done = True
                            break
                    if done:
                        break
                    self.remove(f)
                if done:
                    improved = True
                    applied += 1
                else:
                    self.add(e)
            if not improved:
                break
        return applied

    def kick(self):
        """Force in one random unchosen edge, removing one of the two edges at each of its blockers."""
        E, N, inS, rng = self.E, self.N, self.inS, self.rng
        free = [i for i in range(len(E)) if not inS[i]]
        if not free:
            return
        i = rng.choice(free)
        u, v = E[i]
        b = N[u] & N[v]
        touched = {u, v}
        while b:
            w = (b & -b).bit_length() - 1
            b &= b - 1
            x = u if rng.random() < 0.5 else v
            self.remove(self.eid[(x, w) if x < w else (w, x)])
            touched.add(w)
        self.add(i)
        self.fill(touched)

    def snapshot(self):
        return list(self.N), bytearray(self.inS), self.size

    def restore(self, snap):
        self.N, self.inS, self.size = list(snap[0]), bytearray(snap[1]), snap[2]

    def edges(self):
        return [self.E[i] for i in range(len(self.E)) if self.inS[i]]


def _complete(E, n, side, rng):
    """The cut of `side`, completed greedily (shuffled order) to a triangle-free edge set."""
    nb = [0] * n
    chosen, rest = [], []
    for u, v in E:
        if side[u] != side[v]:
            chosen.append((u, v))
            nb[u] |= 1 << v
            nb[v] |= 1 << u
        else:
            rest.append((u, v))
    rng.shuffle(rest)
    for u, v in rest:
        if not (nb[u] & nb[v]):
            chosen.append((u, v))
            nb[u] |= 1 << v
            nb[v] |= 1 << u
    return chosen


def _descent(n, adj, deg, rng):
    """One-flip descent on the cut from a random two-colouring."""
    side = [rng.random() < 0.5 for _ in range(n)]
    mask = sum(1 << i for i in range(n) if side[i])
    improved = True
    while improved:
        improved = False
        for v in rng.sample(range(n), n):
            same = bin(adj[v] & (mask if side[v] else ~mask)).count('1')
            if 2 * same > deg[v]:
                side[v] = not side[v]
                mask ^= 1 << v
                improved = True
    return side


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    for var in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[var] = '1'
    import random
    import numpy as np
    budget = min(params['cpu_seconds'], cpu_seconds)
    deadline = start + budget
    portfolio_end = start + FRAC * budget
    n = view.n
    E = [tuple(e) for e in view.edges]
    if not E or n < 2:
        return {'selected': [list(e) for e in E], 'value': len(E)}
    rng = random.Random(seed)
    gen = np.random.default_rng(seed)
    eid = {e: i for i, e in enumerate(E)}
    inc = [[] for _ in range(n)]
    adj = [0] * n
    for i, (u, v) in enumerate(E):
        inc[u].append(i)
        inc[v].append(i)
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    deg = [bin(a).count('1') for a in adj]
    J = np.zeros((n, n))
    for u, v in E:
        J[u, v] = J[v, u] = -1.0
    rms = (2 * len(E) / (n * (n - 1))) ** 0.5
    c0 = 0.5 / (rms * n ** 0.5)
    pump = A0 * np.arange(STEPS) / STEPS
    pool = {}
    best = []

    def offer(side):
        nonlocal best
        key = tuple(side) if side[0] else tuple(not z for z in side)
        if key in pool:
            return
        chosen = _complete(E, n, side, rng)
        pool[key] = chosen
        if len(chosen) > len(best):
            best = chosen

    # Phase 1: the portfolio
    while True:
        t_batch = time.process_time()
        x = gen.uniform(-0.1, 0.1, (REPLICAS, n))
        y = gen.uniform(-0.1, 0.1, (REPLICAS, n))
        stopped = False
        for k in range(STEPS):
            y += DT * (-(A0 - pump[k]) * x + c0 * (np.sign(x) @ J))
            x += DT * A0 * y
            wall = np.abs(x) > 1.0
            if wall.any():
                x[wall] = np.sign(x[wall])
                y[wall] = 0.0
            if k % 50 == 49 and time.process_time() >= portfolio_end:
                stopped = True
                break
        for r in (x > 0).tolist():
            offer(r)
        spent = time.process_time() - t_batch
        until = min(portfolio_end, time.process_time() + spent * DESC_SHARE / (1 - DESC_SHARE))
        while time.process_time() < until:
            offer(_descent(n, adj, deg, rng))
        if len(pool) > 4 * K:
            for key in sorted(pool, key=lambda q: len(pool[q]))[:len(pool) - K]:
                del pool[key]
        if stopped or time.process_time() >= portfolio_end:
            break

    # Phase 2: (1,2)-swaps and iterated local search over the pool
    members = [Solution(n, E, inc, eid, rng, ch) for ch in sorted(pool.values(), key=len, reverse=True)[:K]]
    for s in members:
        s.swaps(deadline)
        if s.size > len(best):
            best = s.edges()
    current = [s.snapshot() for s in members]
    j = 0
    while members and time.process_time() < deadline:
        s = members[j]
        s.kick()
        s.swaps(deadline)
        if s.size > len(best):
            best = s.edges()
        if s.size >= current[j][2] or rng.random() < P_WORSE:
            current[j] = s.snapshot()
        else:
            s.restore(current[j])
        j = (j + 1) % len(members)
    return {'selected': [list(e) for e in sorted(best)], 'value': len(best)}
