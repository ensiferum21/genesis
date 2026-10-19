"""Candidate kind `maxcut-tabu-v1` (registry v2, B20_R67): a standard max-cut heuristic as a domain baseline.

Why. A bipartite subgraph is triangle-free, and on dense hosts the largest triangle-free subgraph is close to a
maximum cut. The classical way to attack the problem is therefore a max-cut heuristic followed by a greedy
completion. E1's frozen candidate (`represent-and-repair-v1` with the `cross_2` decoder) is exactly the simplest
such heuristic, one-flip local search from random two-colourings, which its own search code shows. A comparison
claimed to be "beyond strong baselines" should include a standard method of the field. This kind is one: tabu
search over one-vertex flips, the textbook strong local search for max cut (Glover's tabu search; in the max-cut
literature, for example, Kochenberger et al. 2013, Benlic and Hao 2013 build on the same move).

Algorithm (fixed; data-only parameters {cpu_seconds}):
  * repeat until the CPU budget is spent:
      - a random two-colouring of the vertices;
      - tabu search over one-vertex flips: at each step flip the non-tabu vertex with the largest cut gain (a tabu
        vertex is allowed if the flip beats the best cut of this run, the aspiration rule); a flipped vertex stays
        tabu for n/10 + U{0..n/10} steps (at least 1); a run ends after 10 n steps without a new best cut;
      - the best cut of the run, completed greedily: the other host edges in random order, each added if it closes
        no triangle with the edges already chosen;
  * return the largest completed edge set seen.
The completion is the same as E1's candidate's repair. The domain checker re-checks the witness; the claimed value
is never trusted. Domain: triangle_free_host_v1 (a bipartite graph can contain 4-cycles, so the reduction does not
apply to C4).
"""
import random
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/maxcut_tabu.py',)
STALL_FACTOR = 10


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    if domain not in DOMAINS:
        return f'maxcut-tabu-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'cpu_seconds'}:
        return 'maxcut-tabu-v1 takes {cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    return None


def _tabu_cut(n, adj, rng, deadline):
    """One tabu-search run from a random colouring; the best colouring found and its cut size."""
    side = [rng.randrange(2) for _ in range(n)]
    gain = [0] * n                      # cut change if v flips: same-side neighbours minus other-side neighbours
    for v in range(n):
        for w in adj[v]:
            gain[v] += 1 if side[v] == side[w] else -1
    cut = sum(1 for v in range(n) for w in adj[v] if v < w and side[v] != side[w])
    best_cut, best_side = cut, side[:]
    tabu_until = [0] * n
    lo = max(1, n // 10)
    step, last_improve = 0, 0
    while step - last_improve < STALL_FACTOR * n:
        step += 1
        if step % 64 == 0 and time.process_time() >= deadline:
            break
        move, move_gain = None, None
        for v in range(n):
            g = gain[v]
            if tabu_until[v] > step and cut + g <= best_cut:
                continue
            if move is None or g > move_gain or (g == move_gain and rng.random() < 0.5):
                move, move_gain = v, g
        if move is None:
            break
        v = move
        side[v] ^= 1
        cut += move_gain
        gain[v] = -gain[v]
        for w in adj[v]:
            gain[w] += 2 if side[v] == side[w] else -2
        tabu_until[v] = step + lo + rng.randrange(lo + 1)
        if cut > best_cut:
            best_cut, best_side, last_improve = cut, side[:], step
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
    best = []
    while True:
        side, _ = _tabu_cut(n, adj, rng, deadline)
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
