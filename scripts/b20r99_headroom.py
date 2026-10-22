#!/usr/bin/env python3
"""B20_R99: is there structure left where the searches stop? (GV4; the headroom pilot of docs/DISCOVERY_PLAN.md; DEV,
preregistered)

    taskset -c 0 python3 scripts/b20r99_headroom.py OUT_DIR      run ALONE (resumable per host), then analyse

**Why.** Daniel's note (22 Oct 2026) asks Genesis to discover the objects, relations and transformations that make a
problem easier, and to test whether jointly discovering representations, transformations and distinguishing
experiments yields transferable algorithms more efficiently than evolving code with a fixed representation. Before
building such a loop: is there anything left for it to find where today's searches stop, and is it describable?
The system's program search ties random programs of its language (B20_R80, R81) and its library adds nothing on the
training hosts (B20_R84); either the language leaves no headroom, or the headroom lies in coordinated changes it
cannot express. This pilot measures which.

**Design (fixed before running).**
  * **Hosts.** 16 fresh DEV hosts of `triangle_free_large_v1`, 4 per cell: planted_cluster (p_in 0.8, p_out 0.06)
    and G(n, 0.5), at n = 128 and 256 (B20_R97's cells), seeds HOST_SEED + cell, excluding every large-domain identity
    recorded under evidence/ (`autonomy.qet.large_exposure`).
  * **States.** The edge set S each arm returns, one seed:
      - `tfxw` in B20_R95's frozen configuration (`evidence/configure_tfxw_b20r95/config.json`), the strongest arm
        (B20_R97), through `candidates_large` in the runc sandbox, at 2 s and 10 s;
      - `hybrid-swap-v1` (B20_R77's engine) at 2 s and 10 s, and the language programs gen1 (B20_R79), gen2 (B20_R83),
        gen3 (B20_R85) and gen2's control (B20_R84) at 2 s: these are registered for n <= 63 only, so they run here
        in-process through their own `solve` / interpreters, pinned to the study's core, CPU-metered by the process
        clock (disclosed; their values are not compared with anything, only their states are analysed).
    Every state is re-checked triangle-free and a subset of the host. 16 x 8 = 128 states.
  * **Part A, exchanges (every state).** An anchor R is r chosen edges; an (r, r+1)-exchange removes R and adds r+1
    unchosen edges keeping S triangle-free (|S| + 1). Enumerated exhaustively for r <= 2 (`exchanges`; exact, checked
    against brute force in the tests). An anchor of one edge freeing 3 compatible edges counts as r = 1 (gain 2); a
    *strict* r = 2 anchor is one where neither edge improves alone. Exchange descent: apply improving exchanges (r = 1
    first, then r = 2, lowest anchor first) and greedy completion until none is left; its gain is recorded, and the
    state after descent with r = 1 only is checked for r = 2 exchanges.
  * **Part B, neighbourhoods (tfxw's states).** CENTRES = 16 seeded centres v per state; per centre three regions:
    ball2 = {v and 1 random host neighbour}, ball4 = {v and 3 random host neighbours}, rand4 = 4 random vertices.
    CP-SAT (the pinned tree; one worker; deterministic time limit CPSAT_DET = 2.0, wall cap 20 s; fixed seed)
    re-optimizes every host edge touching the region with the rest of S fixed, hinted with S. Outcome IMPROVES
    (gain > 0), PROVED_NONE (optimal, gain 0) or UNKNOWN; UNKNOWN never counts as headroom.
  * **Part C, descriptive.** Each state XOR the host's best state (the largest S of the study on that host) split
    into independently swappable pieces (`gap_components`): sizes, gains, vertices touched.
  * **Q1 (headroom).** A state has *local headroom* when Part A finds an improving exchange or Part B an improving
    region. Fractions: tfxw's states (both budgets together), and the programs' states after descent with r = 1 (an
    r = 2 exchange left).
  * **Q2 (structure).** Two classes: (i) r = 1 anchors (every chosen edge of every state; positive = improving);
    (ii) Part B regions with a decided outcome (positive = IMPROVES). Recognizers are conjunctions of 1..3 threshold
    predicates (feature >= or <= a training decile) over the primitive grammar G_LOW (`features`): degrees in S and in
    the host and their ratio, host triangles, S-edges inside the region or around an anchor, whether things share a
    vertex. G_LOW leaves out blocker counts, freed counts and tightness (derived constraint quantities a discovery
    loop should invent). Fit on 8 hosts (the first 2 of each cell in run order), judge on the other 8. The fitted
    recognizer maximizes training lift among those with training recall >= 0.3 and >= 5 training positives
    selected (exhaustive over sizes 1 and 2, greedy extension to 3). Null: NULL_DRAWS = 1,000 random recognizers of
    the fitted size (random features, directions and deciles; NULL_SEED) with training support at least the fitted
    one's; their held-out lift. A class *passes* if its fitted recognizer has held-out lift >= 2, held-out recall
    >= 0.3, and held-out lift above the null's 95th percentile. A class with fewer than 10 held-out positives is
    UNDERPOWERED and cannot pass.
  * **Verdict.** NO_HEADROOM if local headroom is found at fewer than 10% of tfxw's states *and* an r = 2 exchange is
    left at fewer than 10% of the programs' states after descent with r = 1; otherwise HEADROOM_STRUCTURED if a Q2
    class passes, else HEADROOM_UNSTRUCTURED. (Thresholds written in `docs/DISCOVERY_PLAN.md` at `ba2b052`, before
    any look.)
  * **Q3 (descriptive).** At tfxw's states: of the Part B regions selected by the fitted region recognizer, the
    fraction that improve, against all regions; the expected number of regions tried before the first improvement.

**Development looks (disclosed; exposed hosts only, 22 Oct 2026; `docs/DISCOVERY_PLAN.md` §3.1).** On planted n63
every arm reached the same value (why the pilot moved to the large domain); at n128/n256 tfxw left no exchange of
<= 3 edges in 6 states, hybrid-swap-v1 left 1-4 strict (2,3)-exchanges on planted hosts and none on G(n, 0.5), gen2
left (1,2)-exchanges; the gap to the best known witness was one giant component on 4 hosts; CP-SAT improved 2 of 10
4-vertex balls of one tfxw 2 s state and no random 4-set.

**Expectation, stated before running (informed by the looks).** The programs' states show r = 1 headroom often (the
swap, already known); hybrid-swap-v1 shows strict r = 2 exchanges on planted hosts and none on G(n, 0.5); tfxw shows
no exchange headroom and improving 4-balls on a minority of its 2 s states, fewer at 10 s, and more often than
random 4-sets; NO_HEADROOM is unlikely (the programs' states alone should pass 10%); HEADROOM_UNSTRUCTURED slightly
more likely than HEADROOM_STRUCTURED. **Cost (estimate).** States about 650 s, Part B at most about 3,100 s, the rest
minutes: about 1 h. **Status.** A DEV diagnostic; licenses nothing; changes no package, rule or comparator.
"""
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402

STUDY = 'b20r99'
LARGE = 'triangle_free_large_v1'
HOST_SEED, CENTRE_SEED, NULL_SEED = 20269901, 20269911, 20269921
CELLS = (('planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 128, 'p': 0.5}),
         ('planted_cluster', {'n': 256, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 256, 'p': 0.5}))
PER_CELL = 4
STATES = (('tfxw', 2.0), ('tfxw', 10.0), ('hybrid', 2.0), ('hybrid', 10.0),
          ('gen1', 2.0), ('gen2', 2.0), ('gen3', 2.0), ('control', 2.0))
PROGRAMS = ('gen1', 'gen2', 'gen3', 'control')
EV = ROOT / 'evidence'
SOURCES = {'gen1': EV / 'program_search_b20r79' / 'discovered_program.json',
           'gen2': EV / 'generation2_b20r83' / 'program.json',
           'gen3': EV / 'generation3_b20r85' / 'program.json',
           'control': EV / 'generation2_control_b20r84' / 'program.json'}
TFXW_CONFIG = EV / 'configure_tfxw_b20r95' / 'config.json'
CENTRES, REGIONS = 16, ('ball2', 'ball4', 'rand4')
CPSAT_DET, CPSAT_WALL = 2.0, 20.0
NULL_DRAWS, MIN_POS, MIN_RECALL, MIN_LIFT, MIN_HELDOUT_POS = 1000, 5, 0.3, 2.0, 10
HEADROOM_SHARE = 0.10


def log_to(out):
    t0 = time.time()

    def log(msg):
        line = f'[{time.time() - t0:8.1f}s] {msg}'
        print(line, flush=True)
        with open(out / 'run.log', 'a') as f:
            f.write(line + '\n')
    return log


# ----------------------------------------------------------------------------------------------- exchanges (Part A)

def key(a, b):
    return (a, b) if a < b else (b, a)


def masks(n, edges):
    N = [0] * n
    for a, b in edges:
        N[a] |= 1 << b
        N[b] |= 1 << a
    return N


def is_triangle_free(S, n):
    N = masks(n, S)
    return all(not (N[a] & N[b]) for a, b in S)


def structure(n, host, S):
    """S as a set, its masks, the free edges, and the unchosen edges freed by removing one edge (freed1) or a pair
    (freed2): f = uv is blocked at w when uw, vw are in S; removing R frees f when every blocking wedge meets R."""
    S = {key(*e) for e in S}
    N = masks(n, S)
    free, freed1, freed2 = [], {}, {}
    for f in host:
        f = key(*f)
        if f in S:
            continue
        u, v = f
        c = N[u] & N[v]
        k = bin(c).count('1')
        if k == 0:
            free.append(f)
        elif k == 1:
            w = c.bit_length() - 1
            for e in (key(u, w), key(v, w)):
                freed1.setdefault(e, []).append(f)
        elif k == 2:
            w1 = c.bit_length() - 1
            w2 = (c ^ (1 << w1)).bit_length() - 1
            for e1 in (key(u, w1), key(v, w1)):
                for e2 in (key(u, w2), key(v, w2)):
                    freed2.setdefault(frozenset((e1, e2)), []).append(f)
    return S, N, free, freed1, freed2


def compatible(adds, N, R):
    Nr = list(N)
    for a, b in R:
        Nr[a] &= ~(1 << b)
        Nr[b] &= ~(1 << a)
    for a, b in adds:
        if Nr[a] & Nr[b]:
            return False
        Nr[a] |= 1 << b
        Nr[b] |= 1 << a
    return True


def improving(anchor, cands, N, k):
    """k compatible edges among the freed candidates (after removing the anchor), or None."""
    cands = sorted(set(cands))
    if len(cands) < k:
        return None
    for adds in itertools.combinations(cands, k):
        if compatible(adds, N, anchor):
            return adds
    return None


def exchanges(n, host, S):
    """Every improving anchor with r <= 2: {'free', 'r1' {e: adds}, 'r1_gain2' [e], 'r2' {(e1, e2): adds}, 'r2_strict'
    [(e1, e2)], 'pairs_checked'}. A pair whose single edge frees 3 compatible edges alone is an r = 1 anchor."""
    S, N, free, freed1, freed2 = structure(n, host, S)
    r1, gain2 = {}, []
    for e, fs in freed1.items():
        x = improving((e,), fs, N, 2)
        if x:
            r1[e] = x
            if improving((e,), fs, N, 3):
                gain2.append(e)
    pairs = set(freed2)
    F1 = sorted(freed1)
    for i in range(len(F1)):
        for j in range(i + 1, len(F1)):
            pairs.add(frozenset((F1[i], F1[j])))
    r2 = {}
    for p in pairs:
        e1, e2 = sorted(p)
        if e1 in gain2 or e2 in gain2:
            continue
        x = improving((e1, e2), freed1.get(e1, []) + freed1.get(e2, []) + freed2.get(p, []), N, 3)
        if x:
            r2[(e1, e2)] = x
    strict = sorted(p for p in r2 if p[0] not in r1 and p[1] not in r1)
    return {'free': sorted(free), 'r1': r1, 'r1_gain2': sorted(gain2), 'r2': r2, 'r2_strict': strict,
            'pairs_checked': len(pairs)}


def complete(S, host, n):
    S = {key(*e) for e in S}
    N = masks(n, S)
    for f in sorted(key(*e) for e in host):
        if f not in S and not (N[f[0]] & N[f[1]]):
            S.add(f)
            N[f[0]] |= 1 << f[1]
            N[f[1]] |= 1 << f[0]
    return S


def exchange_descent(n, host, S, max_r=2):
    """Apply improving exchanges (r = 1 first, then r = 2, lowest anchor first) with greedy completion until none."""
    S = complete(S, host, n)
    steps = {1: 0, 2: 0}
    while True:
        x = exchanges(n, host, S)
        if x['r1']:
            e = min(x['r1'])
            S = complete((S - {e}) | set(x['r1'][e]), host, n)
            steps[1] += 1
        elif x['r2'] and max_r >= 2:
            p = min(x['r2'])
            S = complete((S - set(p)) | set(x['r2'][p]), host, n)
            steps[2] += 1
        else:
            return S, steps


def part_a(n, host, S):
    x = exchanges(n, host, S)
    D, steps = exchange_descent(n, host, S)
    D1, _ = exchange_descent(n, host, S, max_r=1)
    after1 = exchanges(n, host, D1)
    return {'free': len(x['free']), 'r1': len(x['r1']), 'r1_gain2': len(x['r1_gain2']), 'r2': len(x['r2']),
            'r2_strict': len(x['r2_strict']), 'pairs_checked': x['pairs_checked'],
            'descent_gain': len(D) - len(S), 'descent_steps': steps,
            'r2_after_r1_descent': len(after1['r2']), 'improving_r1_anchors': [list(e) for e in sorted(x['r1'])]}


# ----------------------------------------------------------------------------------------------- gap pieces (Part C)

def gap_components(n, host, S, B):
    """S XOR B split into pieces that can each be swapped alone: two edges of the difference are linked when a host
    triangle holds both and its third edge is in S or B. A piece's gain is |piece & B| - |piece & S|."""
    S = {key(*e) for e in S}
    B = {key(*e) for e in B}
    D, U = S ^ B, S | B
    H = masks(n, [key(*e) for e in host])
    parent = {e: e for e in D}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in D:
        c = H[a] & H[b]
        while c:
            w = c.bit_length() - 1
            c ^= 1 << w
            x, y = key(a, w), key(b, w)
            for p, q in ((x, y), (y, x)):
                if p in D and q in U:
                    ra, rb = find((a, b)), find(p)
                    if ra != rb:
                        parent[ra] = rb
    comps = {}
    for e in D:
        comps.setdefault(find(e), []).append(e)
    out = []
    for es in comps.values():
        gain = sum(1 for e in es if e in B) - sum(1 for e in es if e in S)
        out.append({'size': len(es), 'gain': gain, 'vertices': len({v for e in es for v in e})})
    return sorted(out, key=lambda c: (-c['size'], -c['gain']))


# ----------------------------------------------------------------------------------------------- regions (Part B)

def cpsat_module():
    """CP-SAT from the pinned tree (refused unless the tree is the pinned one)."""
    from genesis.candidate_kinds import cpsat as K
    if K.tree_digest() != K.SOTA_TREE_SHA256:
        raise SystemExit(f'the CP-SAT tree is not the pinned one ({K.tree_digest()} != {K.SOTA_TREE_SHA256})')
    if K.SOTA_DIR not in sys.path:
        sys.path.insert(0, K.SOTA_DIR)
    from ortools.sat.python import cp_model
    return cp_model


def reoptimize(cp_model, n, host, S, region, seed):
    """Re-optimize every host edge touching the region, the rest of S fixed: (gain, outcome)."""
    R = set(region)
    S = {key(*e) for e in S}
    H = [key(*e) for e in host]
    free = [e for e in H if e[0] in R or e[1] in R]
    fixed = S - set(free)
    Hm = masks(n, H)
    m = cp_model.CpModel()
    x = {e: m.NewBoolVar(f'x{e[0]}_{e[1]}') for e in free}
    seen = set()
    for a, b in free:
        c = Hm[a] & Hm[b]
        while c:
            w = c.bit_length() - 1
            c ^= 1 << w
            tri = tuple(sorted((a, b, w)))
            if tri in seen:
                continue
            seen.add(tri)
            es = (key(tri[0], tri[1]), key(tri[0], tri[2]), key(tri[1], tri[2]))
            if any(e not in x and e not in fixed for e in es):
                continue
            m.Add(sum(x[e] for e in es if e in x) <= 2 - sum(1 for e in es if e not in x))
    for e in free:
        m.AddHint(x[e], 1 if e in S else 0)
    m.Maximize(sum(x.values()))
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed % (2 ** 31)
    s.parameters.max_deterministic_time = CPSAT_DET
    s.parameters.max_time_in_seconds = CPSAT_WALL
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0, 'UNKNOWN', None
    new = fixed | {e for e in free if s.Value(x[e])}
    if not is_triangle_free(new, n):
        raise RuntimeError('CP-SAT returned a set with a triangle: the model is wrong')
    gain = len(new) - len(S)
    if gain > 0:
        return gain, 'IMPROVES', new
    return 0, 'PROVED_NONE' if st == cp_model.OPTIMAL else 'UNKNOWN', None


def regions_for(n, host, task_id, budget):
    rng = random.Random(int(digest({'study': STUDY, 'centres': task_id, 'budget': budget})[:12], 16) ^ CENTRE_SEED)
    nb = [[] for _ in range(n)]
    for a, b in host:
        nb[a].append(b)
        nb[b].append(a)
    out = []
    for c in rng.sample(range(n), CENTRES):
        ns = sorted(nb[c])
        rng.shuffle(ns)
        out.append((c, 'ball2', sorted([c] + ns[:1])))
        out.append((c, 'ball4', sorted([c] + ns[:3])))
        out.append((c, 'rand4', sorted(rng.sample(range(n), 4))))
    return out


# ----------------------------------------------------------------------------------------------- features (G_LOW)

def graph_stats(n, host, S):
    H = masks(n, [key(*e) for e in host])
    N = masks(n, S)
    degH = [bin(m).count('1') for m in H]
    degS = [bin(m).count('1') for m in N]
    triH = [sum(bin(H[v] & H[u]).count('1') for u in range(n) if H[v] >> u & 1) // 2 for v in range(n)]
    sAround = [sum(bin(N[u] & H[v]).count('1') for u in range(n) if H[v] >> u & 1) // 2 for v in range(n)]
    return H, N, degH, degS, triH, sAround


def anchor_features(st, e):
    H, N, degH, degS, triH, sAround = st
    a, b = e
    ratio = lambda v: degS[v] / degH[v] if degH[v] else 0.0
    return {'degS_sum': degS[a] + degS[b], 'degH_sum': degH[a] + degH[b], 'ratio_min': min(ratio(a), ratio(b)),
            'ratio_max': max(ratio(a), ratio(b)), 'host_triangles_edge': bin(H[a] & H[b]).count('1'),
            'host_triangles_ends': triH[a] + triH[b], 's_around_ends': sAround[a] + sAround[b],
            'degH_diff': abs(degH[a] - degH[b])}


def region_features(st, region):
    H, N, degH, degS, triH, sAround = st
    R = list(region)
    ratio = [degS[v] / degH[v] if degH[v] else 0.0 for v in R]
    inside_h = sum(1 for i, u in enumerate(R) for v in R[i + 1:] if H[u] >> v & 1)
    inside_s = sum(1 for i, u in enumerate(R) for v in R[i + 1:] if N[u] >> v & 1)
    return {'degS_mean': statistics.mean(degS[v] for v in R), 'degH_mean': statistics.mean(degH[v] for v in R),
            'ratio_mean': statistics.mean(ratio), 'ratio_min': min(ratio), 'host_edges_inside': inside_h,
            's_edges_inside': inside_s, 'host_triangles_mean': statistics.mean(triH[v] for v in R),
            's_around_mean': statistics.mean(sAround[v] for v in R), 'size': len(R)}


# ----------------------------------------------------------------------------------------------- recognizers (Q2)

class Items:
    """A class for Q2: a feature matrix (rows = items), labels and hosts."""

    def __init__(self, feats, X, y, host):
        import numpy as np
        self.feats, self.X, self.y, self.host = list(feats), np.asarray(X, float), np.asarray(y, bool), list(host)

    def subset(self, keep):
        import numpy as np
        idx = np.array([i for i, h in enumerate(self.host) if keep(h)], dtype=int)
        return Items(self.feats, self.X[idx] if len(idx) else self.X[:0], self.y[idx] if len(idx) else self.y[:0],
                     [self.host[i] for i in idx])


def predicates(train):
    """(feature index, direction, threshold) at the training deciles of each feature."""
    import numpy as np
    out = []
    for fi in range(len(train.feats)):
        col = np.sort(train.X[:, fi])
        qs = sorted({float(col[min(len(col) - 1, int(len(col) * k / 10))]) for k in range(1, 10)})
        out += [(fi, d, q) for q in qs for d in ('>=', '<=')]
    return out


def _mask(items, p):
    fi, d, q = p
    return items.X[:, fi] >= q if d == '>=' else items.X[:, fi] <= q


def score(items, rec):
    import numpy as np
    m = np.ones(len(items.y), bool)
    for p in rec:
        m &= _mask(items, p)
    pos, sel = int(items.y.sum()), int(m.sum())
    sp = int((m & items.y).sum())
    base = pos / len(items.y) if len(items.y) else 0.0
    prec = sp / sel if sel else 0.0
    return {'selected': sel, 'positives_selected': sp, 'precision': prec, 'lift': prec / base if base else 0.0,
            'recall': sp / pos if pos else 0.0}


def fit(train):
    """The recognizer with the highest training lift among those with recall >= 0.3 and >= 5 positives selected:
    exhaustive over 1 and 2 predicates on different features, greedy extension to 3. Ties: the earlier in order."""
    P = predicates(train)
    M = [_mask(train, p) for p in P]
    y, pos, total = train.y, int(train.y.sum()), len(train.y)
    base = pos / total

    def eval_mask(m):
        sel = int(m.sum())
        sp = int((m & y).sum())
        if sp < MIN_POS or sp / pos < MIN_RECALL:
            return None
        return (sp / sel) / base
    best = None
    for a in range(len(P)):
        v = eval_mask(M[a])
        if v is not None and (best is None or v > best[1]):
            best = ((a,), v)
    for a in range(len(P)):
        for b in range(a + 1, len(P)):
            if P[a][0] == P[b][0]:
                continue
            v = eval_mask(M[a] & M[b])
            if v is not None and (best is None or v > best[1]):
                best = ((a, b), v)
    if best is not None and len(best[0]) == 2:
        base_m = M[best[0][0]] & M[best[0][1]]
        used = {P[k][0] for k in best[0]}
        for c in range(len(P)):
            if P[c][0] in used:
                continue
            v = eval_mask(base_m & M[c])
            if v is not None and v > best[1]:
                best = (best[0] + (c,), v)
    if best is None:
        return None
    rec = tuple(P[k] for k in best[0])
    return rec, score(train, rec)


def null_lifts(train, test, size, support):
    """Held-out lifts of NULL_DRAWS random recognizers of `size` predicates (random distinct features, random
    direction and decile) whose training support is at least `support`."""
    rng = random.Random(NULL_SEED)
    P = predicates(train)
    by_f = {}
    for p in P:
        by_f.setdefault(p[0], []).append(p)
    feats = sorted(by_f)
    out, tries = [], 0
    while len(out) < NULL_DRAWS and tries < 200 * NULL_DRAWS:
        tries += 1
        rec = tuple(rng.choice(by_f[f]) for f in rng.sample(feats, size))
        if score(train, rec)['selected'] >= support:
            out.append(score(test, rec)['lift'])
    return out


def q2_class(items, train_hosts):
    train = items.subset(lambda h: h in train_hosts)
    test = items.subset(lambda h: h not in train_hosts)
    res = {'items': len(items.y), 'positives': int(items.y.sum()), 'train_positives': int(train.y.sum()),
           'heldout_positives': int(test.y.sum()), 'features': items.feats}
    if len(train.y) == 0 or len(test.y) == 0 or res['train_positives'] < MIN_POS:
        return dict(res, verdict='UNDERPOWERED', recognizer=None)
    best = fit(train)
    if best is None:
        return dict(res, verdict='NO_RECOGNIZER', recognizer=None)
    rec, s_train = best
    s_test = score(test, rec)
    nl = sorted(null_lifts(train, test, len(rec), s_train['selected']))
    p95 = nl[int(0.95 * (len(nl) - 1))] if nl else None
    passes = (res['heldout_positives'] >= MIN_HELDOUT_POS and s_test['lift'] >= MIN_LIFT
              and s_test['recall'] >= MIN_RECALL and p95 is not None and s_test['lift'] > p95)
    verdict = 'PASSES' if passes else ('UNDERPOWERED' if res['heldout_positives'] < MIN_HELDOUT_POS else 'FAILS')
    return dict(res, verdict=verdict, recognizer=[[items.feats[fi], d, q] for fi, d, q in rec], train=s_train,
                heldout=s_test, null={'draws': len(nl), 'p95_lift': p95,
                                      'median_lift': statistics.median(nl) if nl else None})


# ----------------------------------------------------------------------------------------------- running

def hosts(out, log):
    from genesis.autonomy import qet
    design = {'study': STUDY, 'cells': [list(c) for c in CELLS], 'per_cell': PER_CELL, 'host_seed': HOST_SEED}
    return qet.hosts(design, out, ROOT, log)


def programs():
    out = {}
    for arm, path in SOURCES.items():
        if not path.exists():
            raise SystemExit(f'{path} is missing: the study needs all four programs')
        out[arm] = (json.loads(path.read_text())['program'], hashlib.sha256(path.read_bytes()).hexdigest())
    return out


def tfxw_descriptors():
    from genesis import candidates_large as CL
    config = json.loads(TFXW_CONFIG.read_text())['config']
    return {b: CL.build_descriptor('tfxw-v1', {'cpu_seconds': b, 'config': config}, cpu_seconds=b,
                                   wall_seconds=max(30, int(3 * b) + 30)) for b in (2.0, 10.0)}


def edge_mask(E, S):
    """S as a hex bit mask over the host's sorted edge list (as `autonomy.qet`)."""
    m = 0
    for i, e in enumerate(E):
        if e in S:
            m |= 1 << i
    return format(m, 'x')


def unmask(E, hexmask):
    m = int(hexmask, 16)
    return {e for i, e in enumerate(E) if m >> i & 1}


def run_seed(task_id, arm, budget):
    return int(digest({'study': STUDY, 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def state(task, arm, budget, progs, tfx):
    """(edge set, metered CPU s, how): the arm's returned edge set on the task."""
    from types import SimpleNamespace
    seed = run_seed(task.task_id, arm, budget)
    E = [tuple(e) for e in task.edges]
    if arm == 'tfxw':
        from genesis import candidates_large as CL
        r = CL.run(task, tfx[budget], seed=seed, expected_id=tfx[budget]['descriptor_id'], isolation='runc')
        if r.get('status') != 'SUCCESS':
            raise RuntimeError(f'tfxw failed on {task.task_id}: {r.get("status")}')
        return [tuple(e) for e in r['result']['selected']], r['cpu_ns'] / 1e9, 'runc'
    t0 = time.process_time()
    if arm == 'hybrid':
        from genesis.candidate_kinds import hybrid_swap as HS
        sel = HS.solve(SimpleNamespace(n=task.n, edges=E), {'cpu_seconds': budget}, budget, seed)['selected']
    else:
        from genesis.invention import representations as R
        from genesis.invention import solver_library as SL
        from genesis.invention import solver_programs as SP
        prog = progs[arm][0]
        rep = next(r for r in R.proposals() if r['id'] == prog['rep'])
        run = SL.run if 'library' in prog else SP.run
        sel = run(prog, rep, task.n, E, budget, seed)
    return [tuple(e) for e in sel], time.process_time() - t0, 'in-process'


def run_host(task, progs, tfx, cp_model, log):
    E = [key(*e) for e in task.edges]
    Hset = set(E)
    states = {}
    for arm, b in STATES:
        S, cpu, how = state(task, arm, b, progs, tfx)
        S = {key(*e) for e in S}
        if not S <= Hset or not is_triangle_free(S, task.n):
            raise RuntimeError(f'{arm}@{b} returned an invalid edge set on {task.task_id}')
        states[f'{arm}@{b:g}'] = (S, cpu, how)
    best_name = max(states, key=lambda k: (len(states[k][0]), k))
    B = states[best_name][0]
    row = {'task_id': task.task_id, 'family': task.family.split(':')[0], 'n': task.n, 'edges': len(E),
           'best': {'state': best_name, 'value': len(B)}, 'states': {}}
    for name, (S, cpu, how) in states.items():
        a = part_a(task.n, E, S)
        rec = {'value': len(S), 'cpu_s': round(cpu, 3), 'how': how, 'part_a': a,
               'part_c': gap_components(task.n, E, S, B) if name != best_name else []}
        rec['mask'] = edge_mask(E, S)
        if name.startswith('tfxw@'):
            b = float(name.split('@')[1])
            regs = []
            for c, kind, region in regions_for(task.n, E, task.task_id, b):
                g, outcome, _ = reoptimize(cp_model, task.n, E, S, region,
                                           run_seed(task.task_id, f'region-{c}-{kind}', b))
                regs.append({'centre': c, 'kind': kind, 'region': region, 'gain': g, 'outcome': outcome})
            rec['part_b'] = regs
        row['states'][name] = rec
    log(f'{task.task_id}: best {best_name} {len(B)}; ' + ', '.join(
        f'{k} {v["value"]} r1={v["part_a"]["r1"]} r2s={v["part_a"]["r2_strict"]}'
        + (f' B+{sum(r["outcome"] == "IMPROVES" for r in v["part_b"])}/{len(v["part_b"])}' if 'part_b' in v else '')
        for k, v in row['states'].items()))
    return row


# ----------------------------------------------------------------------------------------------- analysis

def label(q1, q2):
    """The preregistered verdict from Q1's two shares and Q2's class verdicts."""
    if q1['tfxw_share'] < HEADROOM_SHARE and q1['programs_share'] < HEADROOM_SHARE:
        return 'NO_HEADROOM'
    if any(c['verdict'] == 'PASSES' for c in q2.values()):
        return 'HEADROOM_STRUCTURED'
    return 'HEADROOM_UNSTRUCTURED'


def q2_items(rows, tasks):
    """The two Q2 classes from the saved rows and hosts: r = 1 anchors (every chosen edge of every state) and the
    decided Part B regions, with their G_LOW features recomputed from the saved edge sets."""
    A_X, A_y, A_h, R_X, R_y, R_h = [], [], [], [], [], []
    a_feats = r_feats = None
    for r in rows:
        t = tasks[r['task_id']]
        E = [key(*e) for e in t['edges']]
        for name, v in r['states'].items():
            S = unmask(E, v['mask'])
            st = graph_stats(t['n'], E, S)
            pos = {tuple(e) for e in v['part_a']['improving_r1_anchors']}
            for e in sorted(S):
                f = anchor_features(st, e)
                a_feats = a_feats or sorted(f)
                A_X.append([f[k] for k in a_feats])
                A_y.append(e in pos)
                A_h.append(r['task_id'])
            for x in v.get('part_b', []):
                if x['outcome'] == 'UNKNOWN':
                    continue
                f = region_features(st, x['region'])
                r_feats = r_feats or sorted(f)
                R_X.append([f[k] for k in r_feats])
                R_y.append(x['outcome'] == 'IMPROVES')
                R_h.append(r['task_id'])
    return Items(a_feats or [], A_X, A_y, A_h), Items(r_feats or [], R_X, R_y, R_h)


def analyse(rows, tasks):
    tf_states = [(r, v) for r in rows for k, v in r['states'].items() if k.startswith('tfxw@')]
    prog_states = [(r, v) for r in rows for k, v in r['states'].items() if k.split('@')[0] in PROGRAMS]

    def local(v):
        a = v['part_a']
        return a['r1'] > 0 or a['r2'] > 0 or any(x['outcome'] == 'IMPROVES' for x in v.get('part_b', []))
    q1 = {'tfxw_states': len(tf_states), 'tfxw_with_local_headroom': sum(local(v) for _, v in tf_states),
          'programs_states': len(prog_states),
          'programs_with_r2_after_r1_descent': sum(v['part_a']['r2_after_r1_descent'] > 0 for _, v in prog_states)}
    q1['tfxw_share'] = q1['tfxw_with_local_headroom'] / max(1, q1['tfxw_states'])
    q1['programs_share'] = q1['programs_with_r2_after_r1_descent'] / max(1, q1['programs_states'])
    order = [r['task_id'] for r in rows]
    by_cell = {}
    for r in rows:
        by_cell.setdefault((r['family'], r['n']), []).append(r['task_id'])
    train_hosts = {t for ts in by_cell.values() for t in ts[:2]}
    anchors, regions = q2_items(rows, tasks)
    q2 = {'anchors_r1': q2_class(anchors, train_hosts), 'regions': q2_class(regions, train_hosts)}
    verdict = label(q1, q2)
    desc = {}
    for name in [f'{a}@{b:g}' for a, b in STATES]:
        vs = [r['states'][name] for r in rows if name in r['states']]
        desc[name] = {
            'states': len(vs), 'mean_value': statistics.mean(v['value'] for v in vs) if vs else None,
            'with_r1': sum(v['part_a']['r1'] > 0 for v in vs), 'with_r2_strict': sum(v['part_a']['r2_strict'] > 0 for v in vs),
            'mean_descent_gain': statistics.mean(v['part_a']['descent_gain'] for v in vs) if vs else None,
            'free_edges': sum(v['part_a']['free'] for v in vs)}
    part_b = {}
    for kind in REGIONS:
        xs = [x for _, v in tf_states for x in v.get('part_b', []) if x['kind'] == kind]
        part_b[kind] = {o: sum(x['outcome'] == o for x in xs) for o in ('IMPROVES', 'PROVED_NONE', 'UNKNOWN')}
    gaps = [c for r in rows for v in r['states'].values() for c in v['part_c']]
    part_c = {'pieces': len(gaps), 'improving_pieces': sum(c['gain'] > 0 for c in gaps),
              'largest_improving_piece_sizes': sorted((c['size'] for c in gaps if c['gain'] > 0), reverse=True)[:10],
              'improving_pieces_up_to_10_edges': sum(1 for c in gaps if c['gain'] > 0 and c['size'] <= 10)}
    q3 = None
    rec = q2['regions'].get('recognizer')
    if rec:
        idx = {f: i for i, f in enumerate(regions.feats)}
        s_all = score(regions, ())
        s_sel = score(regions, tuple((idx[f], d, q) for f, d, q in rec))
        q3 = {'all_regions': s_all['selected'], 'all_regions_improving_share': s_all['precision'],
              'selected_regions': s_sel['selected'], 'selected_improving_share': s_sel['precision'],
              'expected_tries_all': (1 / s_all['precision']) if s_all['precision'] else None,
              'expected_tries_selected': (1 / s_sel['precision']) if s_sel['precision'] else None}
    return {'verdict': verdict, 'q1': q1, 'q2': q2, 'q3': q3, 'descriptive': desc, 'part_b': part_b,
            'part_c': part_c, 'train_hosts': sorted(train_hosts), 'host_order': order}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (EV / 'headroom_b20r99').resolve():
        raise SystemExit('the registered output is evidence/headroom_b20r99')
    out.mkdir(parents=True, exist_ok=True)
    log = log_to(out)
    import b20r33_strong_baseline_audit as R33
    R33.pinned_core()
    log(f'{STUDY}; pinned to CPU {sorted(os.sched_getaffinity(0))}')
    progs = programs()
    tfx = tfxw_descriptors()
    cp_model = cpsat_module()
    tasks = hosts(out, log)
    rows_path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in rows_path.read_text().splitlines() if l.strip()} if rows_path.exists() else set()
    for t in tasks:
        if t.task_id in done:
            continue
        row = run_host(t, progs, tfx, cp_model, log)
        with open(rows_path, 'a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
    rows = [json.loads(l) for l in rows_path.read_text().splitlines() if l.strip()]
    by_id = {r['task_id']: r for r in rows}
    rows = [by_id[t.task_id] for t in tasks]
    res = analyse(rows, {t.task_id: t.model_dump(mode='json') for t in tasks})
    from genesis.candidate_kinds import cpsat as K
    summary = dict(res, study=STUDY, schema='genesis-b20r99-headroom-v1',
                   status='DEV diagnostic; licenses nothing; no package changed',
                   programs={a: {'path': str(SOURCES[a].relative_to(ROOT)), 'sha256': progs[a][1]} for a in progs},
                   tfxw={'config_sha256': hashlib.sha256(TFXW_CONFIG.read_bytes()).hexdigest(),
                         'descriptors': {f'{b:g}': d['descriptor_id'] for b, d in tfx.items()}},
                   cpsat={'tree_sha256': K.tree_digest(), 'deterministic_time': CPSAT_DET, 'workers': 1},
                   seeds={'hosts': HOST_SEED, 'centres': CENTRE_SEED, 'null': NULL_SEED},
                   code_identity=code_identity(ROOT)['sha256'])
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'verdict {res["verdict"]}; Q1 {res["q1"]}; Q2 ' + ', '.join(f'{k} {v["verdict"]}' for k, v in res['q2'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
