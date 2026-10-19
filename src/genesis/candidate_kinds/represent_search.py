"""Candidate kind `represent-search-v1` (registry v2, B20_R71): the system's representation-and-repair engine with
a choice of move rule, so that physics-inspired moves can be tested on every representation the system invented.

Why. E1's frozen candidate runs an invented representation (B18's typed decoders, Lean-checked sound) through
`invention.representations.represent_and_repair`: zero-temperature one-label descent over encodings, then greedy
repair. Descent stops at the first local optimum; B20_R66 and B20_R68 show the cost on n60 hosts (optimal on 3-4 of
10-13 certified hosts). Every representation the system invents inherits that engine. This kind keeps the
representation, the objective and the repair, and makes the move rule a closed parameter:
  * `descent`: the frozen engine's rule (random vertex order; each vertex takes the first alternative label that
    strictly increases the number of decoded edges at it; sweeps until none does; then repair and restart);
  * `eo`: tau-extremal optimization (Boettcher and Percus; docs/PHYSICS_INSPIRED_PLAN.md idea 3): a vertex's
    fitness is the fraction of its host edges the decoder keeps; pick rank k (worst first) with probability
    proportional to k^-tau, tau = 1 + 1/ln n, and move it to a uniformly random other label, unconditionally;
    keep the best encoding; restart after 20 n steps without a new best; then repair;
  * `anneal`: simulated annealing (Kirkpatrick, Gelatt and Vecchi, Science 1983), the Metropolis rule of
    statistical mechanics: a random vertex proposes a uniformly random other label; the move is accepted if it
    keeps no fewer edges, else with probability exp(delta / T); T falls geometrically from 2.0 to 0.05 over 200 n
    proposals per run; keep the best encoding; then repair.
All rules share this file's repair (the other host edges in random order, each added if it keeps the domain's
motif-freeness), which is faster than the frozen engine's, so a comparison between the two rules here isolates the
move rule. The frozen v1 candidate is not touched.

Parameters (data only): {representation, move, cpu_seconds}; the representation must be one of B18's proposals
whose soundness mode on the domain is SUFF or EQ (the same licence the v1 kind requires, from the same checked
package). Domain: triangle_free_host_v1. The domain checker re-checks the witness; the claimed value is never
trusted.
"""
from bisect import bisect_left
import json
import math
from pathlib import Path
import random
import time

DOMAINS = ('triangle_free_host_v1',)
FILES = ('candidate_kinds/represent_search.py', 'invention/representations.py', 'invention/soundness.py',
         'formal_research/triangle_theory.py')
MOVES = ('descent', 'eo', 'anneal')
T_HOT, T_COLD, ANNEAL_FACTOR = 2.0, 0.05, 200
STALL_FACTOR = 20
PACKAGE = Path(__file__).resolve().parents[3] / 'evidence' / 'invention_b18' / 'representations' / 'package.json'


def licensed(rep_id, domain):
    """The representation's established soundness mode on the domain, from B18's checked package."""
    from ..invention import soundness as S
    modes = S.representation_modes(json.loads(PACKAGE.read_text()))
    rec = modes.get((rep_id, domain))
    if rec is None:
        return None
    return rec['established'] if not S.problems(rec, 'lift_positive') else 'NOT_LIFTING'


def check_parameters(domain, params):
    """None, or the reason the parameters are refused."""
    if domain not in DOMAINS:
        return f'represent-search-v1 supports {DOMAINS}, not {domain}'
    if not isinstance(params, dict) or set(params) != {'representation', 'move', 'cpu_seconds'}:
        return 'represent-search-v1 takes {representation, move, cpu_seconds}'
    c = params['cpu_seconds']
    if type(c) not in (int, float) or isinstance(c, bool) or not 0 < c <= 60:
        return 'cpu_seconds must be in (0, 60]'
    if params['move'] not in MOVES:
        return f'move must be one of {MOVES}'
    if type(params['representation']) is not str:
        return 'representation must be a proposal id'
    try:
        mode = licensed(params['representation'], domain)
    except (OSError, ValueError, KeyError):
        return 'the representation package cannot be read'
    if mode not in ('SUFF', 'EQ'):
        return f'{params["representation"]} on {domain} is not licensed (mode {mode})'
    return None


def _graph(n, E, py):
    """Incident edges per vertex as (other, low): `low` says whether the vertex is the edge's first endpoint, which
    matters for orientation-sensitive decoders (ordered_k)."""
    inc = [[] for _ in range(n)]
    for u, v in E:
        inc[u].append((v, True))
        inc[v].append((u, False))
    return inc


def _keeps(py, c, v, w, low):
    return py(c[v], c[w]) if low else py(c[w], c[v])


def _descent(n, k, py, inc, rng, deadline):
    c = [rng.randrange(k) for _ in range(n)]
    improved = True
    while improved:
        improved = False
        for v in rng.sample(range(n), n):
            cur = sum(_keeps(py, c, v, w, low) for w, low in inc[v])
            for alt in range(k):
                if alt == c[v]:
                    continue
                old, c[v] = c[v], alt
                new = sum(_keeps(py, c, v, w, low) for w, low in inc[v])
                if new > cur:
                    cur, improved = new, True
                else:
                    c[v] = old
        if time.process_time() >= deadline:
            break
    return c


def _eo(n, k, py, inc, rng, deadline, cum):
    c = [rng.randrange(k) for _ in range(n)]
    deg = [len(inc[v]) for v in range(n)]
    kept = [sum(_keeps(py, c, v, w, low) for w, low in inc[v]) for v in range(n)]
    total = sum(kept) // 2
    best, best_c = total, c[:]
    order, mass = list(range(n)), cum[-1]
    step, last = 0, 0
    while step - last < STALL_FACTOR * n:
        step += 1
        if step % 64 == 0 and time.process_time() >= deadline:
            break
        rng.shuffle(order)
        order.sort(key=lambda x: kept[x] / deg[x] if deg[x] else 1.0)
        v = order[bisect_left(cum, rng.random() * mass)]
        before = [(w, _keeps(py, c, v, w, low)) for w, low in inc[v]]
        c[v] = (c[v] + 1 + rng.randrange(k - 1)) % k
        after = 0
        for (w, low), (_, was) in zip(inc[v], before):
            now = _keeps(py, c, v, w, low)
            after += now
            kept[w] += now - was
        total += after - kept[v]
        kept[v] = after
        if total > best:
            best, best_c, last = total, c[:], step
    return best_c


def _anneal(n, k, py, inc, rng, deadline):
    c = [rng.randrange(k) for _ in range(n)]
    total = sum(sum(_keeps(py, c, v, w, low) for w, low in inc[v]) for v in range(n)) // 2
    best, best_c = total, c[:]
    steps = ANNEAL_FACTOR * n
    ratio = T_COLD / T_HOT
    for s in range(steps):
        if s % 256 == 255 and time.process_time() >= deadline:
            break
        T = T_HOT * ratio ** (s / steps)
        v = rng.randrange(n)
        old = c[v]
        here = sum(_keeps(py, c, v, w, low) for w, low in inc[v])
        c[v] = (old + 1 + rng.randrange(k - 1)) % k
        delta = sum(_keeps(py, c, v, w, low) for w, low in inc[v]) - here
        if delta >= 0 or rng.random() < math.exp(delta / T):
            total += delta
            if total > best:
                best, best_c = total, c[:]
        else:
            c[v] = old
    return best_c


def _repair(E, n, keep, rng):
    """The decoded edges, completed greedily (shuffled order) without closing a triangle."""
    nb = [set() for _ in range(n)]
    chosen, rest = [], []
    for e in E:
        (chosen if keep(e) else rest).append(e)
    for u, v in chosen:
        nb[u].add(v); nb[v].add(u)
    rng.shuffle(rest)
    for u, v in rest:
        if not (nb[u] & nb[v]):
            chosen.append((u, v)); nb[u].add(v); nb[v].add(u)
    return chosen


def solve(view, params, cpu_seconds, seed):
    """{'selected': [[u, v], ...], 'value': int} for the candidate view (n, edges)."""
    start = time.process_time()
    from ..invention import representations as R
    rep = next(r for r in R.proposals() if r['id'] == params['representation'])
    budget = min(params['cpu_seconds'], cpu_seconds)
    deadline = start + budget
    rng = random.Random(seed)
    n, k, py = view.n, rep['k'], rep['_py']
    E = [tuple(e) for e in view.edges]
    inc = _graph(n, E, py)
    tau = 1.0 + 1.0 / math.log(n) if n > 2 else 2.0
    cum, acc = [], 0.0
    for r in range(1, n + 1):
        acc += r ** -tau
        cum.append(acc)
    best = []
    while True:
        if params['move'] == 'descent':
            c = _descent(n, k, py, inc, rng, deadline)
        elif params['move'] == 'eo':
            c = _eo(n, k, py, inc, rng, deadline, cum)
        else:
            c = _anneal(n, k, py, inc, rng, deadline)
        chosen = _repair(E, n, lambda e: py(c[e[0]], c[e[1]]), rng)
        if len(chosen) > len(best):
            best = chosen
        if time.process_time() >= deadline:
            break
    return {'selected': [list(e) for e in sorted(best)], 'value': len(best)}
