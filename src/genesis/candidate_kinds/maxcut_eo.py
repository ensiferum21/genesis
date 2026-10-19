"""Candidate kind `maxcut-eo-v1` (registry v2, B20_R69): tau-extremal optimization, a search modelled on
self-organized criticality, as a domain baseline for E1d.

Why. Extremal optimization (Boettcher and Percus, Artificial Intelligence 2000; Phys. Rev. Lett. 2001,
"Optimization with extremal dynamics") takes its move rule from the Bak-Sneppen model of punctuated equilibrium:
instead of accepting moves by a temperature, it always changes one of the worst-adapted variables, chosen by a
power law over fitness ranks. The dynamics never freeze, and large rearrangements happen at all scales
("avalanches"), which is what lets it escape the local optima where one-flip descent (E1's candidate) stops. It is
reported to beat simulated annealing near the bipartitioning phase transition and to find spin-glass ground
states with little tuning.

Algorithm (fixed; data-only parameters {cpu_seconds}), for max cut on the host:
  * a vertex's fitness is the fraction of its edges that are cut, lambda_v = cut(v) / deg(v) (isolated vertices
    have fitness 1); ranks 1..n order the vertices from worst to best (ties in random order);
  * each step picks rank k with probability proportional to k^-tau, tau = 1 + 1/ln n (Boettcher and Percus's
    recommended scaling), and flips that vertex unconditionally;
  * the best cut seen is kept; a run restarts from a random two-colouring after 20 n steps without a new best;
  * each run's best cut is completed greedily to a triangle-free subgraph exactly as E1's candidate and
    `maxcut-tabu-v1` complete theirs; the largest edge set over the runs is returned.
The domain checker re-checks the witness; the claimed value is never trusted. Domain: triangle_free_host_v1 only.
"""
from bisect import bisect_left
import math
import random
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/maxcut_eo.py',)
STALL_FACTOR = 20


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    if domain not in DOMAINS:
        return f'maxcut-eo-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'maxcut-eo-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    return None


def tau_for(n):
    return 1.0 + 1.0 / math.log(n) if n > 2 else 2.0


def _eo_cut(n, adj, rng, deadline, cum):
    """One extremal-optimization run from a random colouring; the best colouring found and its cut."""
    side = [rng.randrange(2) for _ in range(n)]
    deg = [len(adj[v]) for v in range(n)]
    cutv = [sum(side[w] != side[v] for w in adj[v]) for v in range(n)]
    cut = sum(cutv) // 2
    best_cut, best_side = cut, side[:]
    order = list(range(n))
    total = cum[-1]
    step, last = 0, 0
    while step - last < STALL_FACTOR * n:
        step += 1
        if step % 64 == 0 and time.process_time() >= deadline:
            break
        rng.shuffle(order)
        order.sort(key=lambda v: cutv[v] / deg[v] if deg[v] else 1.0)
        v = order[bisect_left(cum, rng.random() * total)]
        side[v] ^= 1
        before = cutv[v]
        cutv[v] = deg[v] - before
        cut += cutv[v] - before
        for w in adj[v]:
            cutv[w] += 1 if side[w] != side[v] else -1
        if cut > best_cut:
            best_cut, best_side, last = cut, side[:], step
    return best_side, best_cut


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    budget = min(params['cpu_seconds'], cpu_seconds)
    deadline = start + budget
    rng = random.Random(seed)
    n = view.n
    E = [tuple(e) for e in view.edges]
    adj = [[] for _ in range(n)]
    for u, v in E:
        adj[u].append(v)
        adj[v].append(u)
    tau = tau_for(n)
    cum, acc = [], 0.0
    for k in range(1, n + 1):
        acc += k ** -tau
        cum.append(acc)
    best = []
    while True:
        side, _ = _eo_cut(n, adj, rng, deadline, cum)
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
        if len(chosen) > len(best):
            best = chosen
        if time.process_time() >= deadline:
            break
    return {'selected': [list(e) for e in sorted(best)], 'value': len(best)}
