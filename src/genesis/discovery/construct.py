"""LP- and SAT-guided construction methods for motif-free subgraphs (GV4 capability pilot, B20_RX3).

Builder-written components that a research process may compose into solver methods. They are
search, never evidence: every witness they return is re-checked by ``graphs.check_witness`` by the
caller, and nothing here certifies a bound (the SAT solver's UNSAT answers are not proof-checked
here; certification stays in ``obstruction.certify`` / ``certificates``).

Budgets are CPU seconds and include the CPU of child processes (the SAT solver), so a method that
calls CaDiCaL is charged for it (``Budget``).

  lp_values(task)                 the LP relaxation max sum x_e s.t. x(M) <= |M| - 1 per motif, 0 <= x <= 1
                                  (scipy/HiGHS, an untrusted float producer)
  greedy(task, order)             the maximal motif-free edge set adding edges in ``order``
  lp_greedy(task, budget, seed)   greedy in LP order, then LP-perturbed restarts until the budget is spent
  sat_climb(task, start, budget)  ask CaDiCaL for lower+1 edges repeatedly; stop on UNSAT (the current
                                  witness is optimal, not proof-checked here), timeout or budget
"""
import os
import random
import resource
import subprocess
import tempfile
import time
from pathlib import Path

from ..graphs import check_witness, motifs, neighbors


class Budget:
    """CPU seconds of this process plus its waited-for children since construction."""

    def __init__(self, seconds):
        self.seconds = float(seconds)
        self.start = self._now()

    @staticmethod
    def _now():
        s, c = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
        return s.ru_utime + s.ru_stime + c.ru_utime + c.ru_stime

    def used(self):
        return self._now() - self.start

    def left(self):
        return self.seconds - self.used()


def _edge_masks(task):
    return [m for m in motifs(task)]


def lp_values(task):
    """LP relaxation values per host edge (floats from an untrusted producer)."""
    from scipy.optimize import linprog
    import numpy as np
    m = len(task.edges)
    ms = _edge_masks(task)
    if not m:
        return []
    if not ms:
        return [1.0] * m
    A = np.zeros((len(ms), m))
    b = np.zeros(len(ms))
    for i, mask in enumerate(ms):
        idx = [j for j in range(m) if mask >> j & 1]
        A[i, idx] = 1.0
        b[i] = len(idx) - 1
    r = linprog(-np.ones(m), A_ub=A, b_ub=b, bounds=[(0, 1)] * m, method='highs')
    if r.status != 0:
        return [0.5] * m
    return [float(x) for x in r.x]


def _can_add(task, adj, u, v):
    if task.domain == 'triangle_free_host_v1':
        return not (adj[u] & adj[v])
    # C4: adding uv closes a 4-cycle iff there is a path u-x-y-v with x != v, y != u
    for x in range(task.n):
        if adj[u] >> x & 1 and x != v and (adj[x] & adj[v] & ~(1 << u)):
            return False
    return True


def greedy(task, order):
    adj = [0] * task.n
    out = []
    for i in order:
        u, v = task.edges[i]
        if _can_add(task, adj, u, v):
            adj[u] |= 1 << v
            adj[v] |= 1 << u
            out.append((u, v))
    return tuple(sorted(out))


def lp_greedy(task, budget, seed=0, *, x=None):
    """Greedy in decreasing LP order (random tie-breaks), then LP-perturbed restarts until the budget."""
    b = budget if isinstance(budget, Budget) else Budget(budget)
    rng = random.Random(seed)
    x = lp_values(task) if x is None else x
    m = len(task.edges)
    best, k = (), 0
    while True:
        noise = 0.0 if k == 0 else 0.35
        keys = [x[i] + noise * rng.random() + 1e-6 * rng.random() for i in range(m)]
        order = sorted(range(m), key=lambda i: -keys[i])
        w = greedy(task, order)
        if len(w) > len(best):
            best = w
        k += 1
        if b.left() <= 0:
            break
    return {'witness': best, 'restarts': k, 'cpu_s': b.used()}


def _cadical():
    from ..verification.tools import tool
    return tool('cadical')['path']


def _sat_model(cnf, seconds):
    """CaDiCaL on ``cnf`` with a wall timeout (fractional); returns (status, model)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'f.cnf'
        p.write_bytes(cnf)
        try:
            proc = subprocess.run([_cadical(), '-q', str(p)], capture_output=True, text=True,
                                  timeout=max(0.05, seconds), env={'PATH': '/usr/bin:/bin'})
        except subprocess.TimeoutExpired:
            return 'UNKNOWN', None
    if proc.returncode == 10:
        lits = [int(t) for line in proc.stdout.splitlines() if line.startswith('v') for t in line.split()[1:]]
        return 'SAT', [l for l in lits if l]
    if proc.returncode == 20:
        return 'UNSAT', None
    return 'UNKNOWN', None


def sat_climb(task, start, budget):
    """Raise a witness one edge at a time with CaDiCaL (k = lower + 1) while the budget lasts."""
    from ..verification.sat import encode, witness_from_model
    b = budget if isinstance(budget, Budget) else Budget(budget)
    best = tuple(sorted(map(tuple, start)))
    calls, stop = 0, 'BUDGET'
    while b.left() > 0.02 and len(best) < len(task.edges):
        status, model = _sat_model(encode(task, len(best) + 1), b.left())
        calls += 1
        if status == 'SAT':
            w = check_witness(task, witness_from_model(task, model))['selected']
            if len(w) <= len(best):
                stop = 'NO_PROGRESS'
                break
            best = w
        elif status == 'UNSAT':
            stop = 'UNSAT'
            break
        else:
            stop = 'TIMEOUT'
            break
    return {'witness': best, 'sat_calls': calls, 'stop': stop, 'cpu_s': b.used()}


__all__ = ['Budget', 'lp_values', 'greedy', 'lp_greedy', 'sat_climb']
