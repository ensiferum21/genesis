"""Candidate kind `ising-dsb-v1` (registry v2, B20_R69): discrete simulated bifurcation, a physics-inspired
max-cut solver, as a domain baseline for E1d.

Why. On dense hosts the largest triangle-free subgraph is close to a maximum cut (a bipartite subgraph is
triangle-free), and a maximum cut is the ground state of an antiferromagnetic Ising model on the host. Simulated
bifurcation (Goto, Tatsumura, Dixon, Sci. Adv. 2019; Goto et al., Sci. Adv. 2021, "High-performance combinatorial
optimization based on classical mechanics") finds Ising ground states by integrating the classical equations of
motion of coupled nonlinear oscillators whose bifurcation is driven slowly through a pitchfork: each oscillator's
position settles at +1 or -1, and the coupling biases the settlement towards low energy. Its discrete variant (dSB)
is among the strongest heuristics reported for dense max-cut instances. It is a fundamentally different search
from E1's candidate (one-flip descent) and from tabu search (`maxcut-tabu-v1`): all spins move at once,
continuously, following a Hamiltonian flow.

Algorithm (fixed; data-only parameters {cpu_seconds}). Ising couplings J = -A (A the host's adjacency matrix), so
that low energy -1/2 sum J_ij s_i s_j means many cut edges. For R = 32 replicas at a time, from x, y ~ U(-0.1, 0.1):
    y_i <- y_i + dt * ( -(a0 - a(t)) x_i + c0 * sum_j J_ij sgn(x_j) )        (dSB: sgn in the coupling)
    x_i <- x_i + dt * a0 * y_i
    |x_i| > 1  ->  x_i = sgn(x_i), y_i = 0                                     (inelastic walls)
with a0 = 1, a(t) rising linearly from 0 to a0 over STEPS = 400 steps, c0 = 0.5 / (rms(J) * sqrt(n)), rms(J)
the root mean square of the off-diagonal couplings (Goto et al. 2019), and time step dt = 0.5. (A step of 1, as
some later papers use, is unstable on these dense hosts: on one B20_R66 n60 host the coupling force per step
exceeds the wall distance and the readout cut fell to 51 of 420 edges, far below a random cut's 211; at 0.5
the readout reaches 259. That check, on one evidence host, fixed dt before any study used the kind.)
At the end each replica's spins s_i = sgn(x_i) give a cut, completed greedily to a triangle-free subgraph exactly
as E1's candidate and `maxcut-tabu-v1` complete theirs (the other host edges in random order, each added if it
closes no triangle). Batches of replicas repeat until the CPU budget is spent; the largest edge set is returned.
No local-search polish is added, so the arm measures the dynamics themselves. The domain checker re-checks the
witness; the claimed value is never trusted.

Fairness. As `milp-highs-v1`, the child pins itself to one CPU and limits BLAS to one thread before importing
numpy, so the cgroup meter stays comparable with single-threaded arms. Domain: triangle_free_host_v1 only.
"""
import os
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/ising_dsb.py',)
REPLICAS, STEPS, A0, DT = 32, 400, 1.0, 0.5


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    if domain not in DOMAINS:
        return f'ising-dsb-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'ising-dsb-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    return None


def _complete(E, n, side, rng):
    """The cut of `side`, completed greedily (shuffled order) to a triangle-free edge set."""
    nb = [set() for _ in range(n)]
    chosen, rest = [], []
    for u, v in E:
        if side[u] != side[v]:
            chosen.append((u, v)); nb[u].add(v); nb[v].add(u)
        else:
            rest.append((u, v))
    rng.shuffle(rest)
    for u, v in rest:
        if not (nb[u] & nb[v]):
            chosen.append((u, v)); nb[u].add(v); nb[v].add(u)
    return chosen


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
    n = view.n
    E = [tuple(e) for e in view.edges]
    if not E or n < 2:
        return {'selected': [list(e) for e in E], 'value': len(E)}
    J = np.zeros((n, n))
    for u, v in E:
        J[u, v] = J[v, u] = -1.0
    rms = (2 * len(E) / (n * (n - 1))) ** 0.5
    c0 = 0.5 / (rms * n ** 0.5)
    gen = np.random.default_rng(seed)
    rng = random.Random(seed)
    pump = A0 * np.arange(STEPS) / STEPS
    best = []
    while True:
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
            if k % 50 == 49 and time.process_time() >= deadline:
                stopped = True
                break
        s = x > 0
        for r in range(REPLICAS):
            chosen = _complete(E, n, s[r].tolist(), rng)
            if len(chosen) > len(best):
                best = chosen
        if stopped or time.process_time() >= deadline:
            break
    return {'selected': [list(e) for e in sorted(best)], 'value': len(best)}
