"""Candidate kind `dsb-maxcut-v1` (max-cut runner, B20_R101): discrete simulated bifurcation on weighted max-cut.

Why. `ising-dsb-v1` (B20_R69) is Genesis's physics-inspired solver: the classical equations of motion of coupled
nonlinear oscillators driven through a bifurcation (Goto, Tatsumura and Dixon, Sci. Adv. 2019; Goto et al., Sci. Adv.
2021), whose positions settle at +1 or -1 near low Ising energy. Simulated-bifurcation machines report time-to-target
on Gset (G22 and others), so on the public benchmark it is the physics arm. Here it runs on the max-cut objective
itself, with weights: J = -W, so that low energy -1/2 sum J_ij s_i s_j is a heavy cut, as a sparse matrix (Gset has
up to 20,000 vertices).

Algorithm (fixed; `ising-dsb-v1`'s dynamics with weighted couplings). R = 32 replicas at a time from x, y ~ U(-0.1, 0.1):
    y_i <- y_i + dt * ( -(a0 - a(t)) x_i + c0 * sum_j J_ij sgn(x_j) );  x_i <- x_i + dt * a0 * y_i;  inelastic walls
with a0 = 1, a(t) rising linearly from 0 to a0 over STEPS = 400 steps, dt = 0.5, c0 = 0.5 / (rms(J) sqrt(n)), rms(J)
the root mean square of the off-diagonal couplings. Each replica's signs give a cut; batches repeat until the CPU
budget is spent; the heaviest cut is returned. No local-search polish: the arm measures the dynamics. Fairness as
`ising-dsb-v1` (one CPU, one BLAS thread, numpy import inside the budget).

Parameters (data only): {cpu_seconds}. Domain: maxcut_v1.
"""
import os
import time

DOMAINS = ('maxcut_v1',)
FILES = ('candidate_kinds/dsb_maxcut.py',)
REPLICAS, STEPS, A0, DT = 32, 400, 1.0, 0.5


def check_parameters(domain, params):
    if domain not in DOMAINS:
        return f'dsb-maxcut-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'dsb-maxcut-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 600:
        return 'cpu_seconds must be in (0, 600]'
    return None


def solve(view, params, cpu_seconds, seed):
    """{'side': '0101...', 'value': int} for the candidate view (n, weighted edges)."""
    start = time.process_time()
    try:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    except (AttributeError, OSError):
        pass
    for var in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[var] = '1'
    import numpy as np
    from scipy import sparse
    budget = min(params['cpu_seconds'], cpu_seconds)
    deadline = start + budget
    n, E = view.n, [tuple(e) for e in view.edges]
    if not E or n < 2:
        return {'side': '0' * n, 'value': 0}
    u = np.array([e[0] for e in E]); v = np.array([e[1] for e in E]); w = np.array([float(e[2]) for e in E])
    J = sparse.csr_matrix((np.concatenate([-w, -w]), (np.concatenate([u, v]), np.concatenate([v, u]))), shape=(n, n))
    rms = (2 * float((w ** 2).sum()) / (n * (n - 1))) ** 0.5
    c0 = 0.5 / (rms * n ** 0.5)
    gen = np.random.default_rng(seed)
    pump = A0 * np.arange(STEPS) / STEPS
    best_val, best = None, None
    while True:
        x = gen.uniform(-0.1, 0.1, (REPLICAS, n))
        y = gen.uniform(-0.1, 0.1, (REPLICAS, n))
        stopped = False
        for k in range(STEPS):
            y += DT * (-(A0 - pump[k]) * x + c0 * (J @ np.sign(x).T).T)
            x += DT * A0 * y
            wall = np.abs(x) > 1.0
            if wall.any():
                x[wall] = np.sign(x[wall])
                y[wall] = 0.0
            if k % 50 == 49 and time.process_time() >= deadline:
                stopped = True
                break
        s = x > 0
        vals = ((s[:, u] != s[:, v]) * w).sum(axis=1)
        r = int(np.argmax(vals))
        if best_val is None or vals[r] > best_val:
            best_val, best = float(vals[r]), s[r].copy()
        if stopped or time.process_time() >= deadline:
            break
    side = ''.join('1' if b else '0' for b in best)
    return {'side': side, 'value': sum(c for a, b, c in E if side[a] != side[b])}     # exact, in integers
