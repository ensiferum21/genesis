"""Decompositions with verified witness composition (handoff s15.3, W10; B20_R27).

This is the second family after the retired relational decoders. The quotient family is the
first; see ``quotients``.

A decomposition splits the host's vertices into m parts with few edges between them and solves
each induced part on its own. Parts are small, so the exact components (LP-ordered greedy, then
CaDiCaL raising the part one edge at a time) can often settle them. The part witnesses are
then composed, and the edges between parts are restored by greedy repair under the domain
checker.

**Composition (Lean, proved once for all edge sets).** Vertex-disjoint triangle-free edge sets have
a triangle-free union:

    GT.TriangleFree S → GT.TriangleFree T →
      (∀ e ∈ S, ∀ f ∈ T, e.1 ≠ f.1 ∧ e.1 ≠ f.2 ∧ e.2 ≠ f.1 ∧ e.2 ≠ f.2) → GT.TriangleFree (S ∪ T)

A triangle's three edges share endpoints pairwise, so they cannot be split between vertex-disjoint
sets. The m-part composition is m − 1 applications of the theorem, since a union of parts stays
vertex-disjoint from the remaining parts. The repaired witness is validated by the domain checker,
like every witness.

**Controls.** Exact components applied to the whole host are an existing capability (B20_RX3).
The study therefore compares a decomposition with *the same components on the whole host at the
same budget* (`whole`), not only with the menu and the DSL baselines. Any gain has to come from the
decomposition.
"""
import random

from ..discovery.construct import Budget, greedy, lp_greedy, lp_values, sat_climb
from ..models import GraphTask
from . import representations as RP

FAMILY = 'decomposition'
ORIGIN = 'generated:decomposition-v1'
MAX_PARTS = 4
SHARES = {'partition': 0.10, 'parts': 0.70, 'repair': 0.20}


# ---------------------------------------------------------------- partition

def cut_size(E, part):
    return sum(part[u] != part[v] for u, v in E)


def balanced_partition(n, E, m, rng, *, budget=None, passes=20):
    """Balanced m-way partition (sizes ⌊n/m⌋ or ⌈n/m⌉), improved by pairwise swaps that reduce the
    number of edges between parts. Local search with no optimality guarantee."""
    order = list(range(n))
    rng.shuffle(order)
    part = {v: i % m for i, v in enumerate(order)}
    nb = {v: [] for v in range(n)}
    for u, v in E:
        nb[u].append(v); nb[v].append(u)

    def ext(v):                            # v's neighbours in other parts, under the current assignment
        return sum(part[w] != part[v] for w in nb[v])
    for _ in range(passes):
        improved = False
        for u in range(n):
            for v in range(u + 1, n):
                if part[u] == part[v]:
                    continue
                before = ext(u) + ext(v)           # a u-v edge counts twice here and after the swap
                part[u], part[v] = part[v], part[u]
                if ext(u) + ext(v) < before:
                    improved = True
                else:
                    part[u], part[v] = part[v], part[u]
            if budget is not None and budget.left() <= 0:
                return part
        if not improved:
            break
    return part


def part_task(task, vertices, label):
    """The induced subgraph on `vertices`, relabelled 0..k-1: (GraphTask, back map)."""
    idx = {v: i for i, v in enumerate(sorted(vertices))}
    edges = tuple(sorted((idx[u], idx[v]) for u, v in task.edges if u in idx and v in idx))
    sub = GraphTask(task_id=f'{task.task_id[:100]}#{label}', domain=task.domain, n=len(idx), edges=edges,
                    family=task.family, split=task.split)
    return sub, {i: v for v, i in idx.items()}


def vertex_disjoint(S, T):
    vs = {x for e in S for x in e}
    return not any(x in vs for e in T for x in e)


# ---------------------------------------------------------------- solvers

def exact_components(task, seconds, seed=0):
    """LP-ordered greedy with restarts for a third of the time, then CaDiCaL climbing (the
    B20_RX3 components). Returns (witness, stop reason)."""
    if not task.edges:
        return (), 'EMPTY'
    b = Budget(seconds)
    start = lp_greedy(task, Budget(max(0.01, seconds / 3)), seed)['witness']
    if b.left() <= 0.02:
        return start, 'BUDGET'
    o = sat_climb(task, start, b)
    return o['witness'], o['stop']


def decompose_and_repair(task, m, *, cpu_seconds, seed=0):
    """Partition, solve the parts, compose (vertex-disjoint union), repair the edges between parts.
    CPU is charged with children (CaDiCaL) through discovery.construct.Budget."""
    if not 2 <= m <= MAX_PARTS:
        raise RP.ProposalError(f'part count must be in [2, {MAX_PARTS}]')
    total = Budget(cpu_seconds)
    rng = random.Random(seed)
    E = [tuple(e) for e in task.edges]
    part = balanced_partition(task.n, E, m, rng, budget=Budget(SHARES['partition'] * cpu_seconds))
    composed, stops = set(), []
    per_part = SHARES['parts'] * cpu_seconds / m
    for p in range(m):
        sub, back = part_task(task, [v for v in range(task.n) if part[v] == p], f'part{p}')
        w, stop = exact_components(sub, per_part, seed + p)
        stops.append(stop)
        lifted = {(back[u], back[v]) for u, v in w}
        if not vertex_disjoint(composed, lifted):          # cannot happen: parts are vertex-disjoint
            raise AssertionError('parts overlap')
        composed |= lifted
    composed_size = len(composed)
    cross = [e for e in E if part[e[0]] != part[e[1]]]
    best, tries = None, 0
    while True:
        S = set(composed)
        rng.shuffle(cross)
        for e in cross:
            if RP.tf_add_ok(S, e):
                S.add(e)
        tries += 1
        if best is None or len(S) > len(best):
            best = S
        if total.left() <= 0:
            break
    return {'witness': sorted(best), 'value': len(best), 'composed': composed_size, 'cut': len(cross),
            'part_stops': stops, 'repair_tries': tries, 'parts': m, 'cpu_s': total.used()}


def whole(task, *, cpu_seconds, seed=0):
    """The control: the same exact components on the whole host, at the same budget."""
    w, stop = exact_components(task, cpu_seconds, seed)
    return {'witness': sorted(w), 'value': len(w), 'stop': stop}


def proposal(m):
    if type(m) is not int or not 2 <= m <= MAX_PARTS:
        raise RP.ProposalError(f'part count m must be an integer in [2, {MAX_PARTS}]')
    return {'id': f'decomp_{m}', 'family': FAMILY, 'parts': m, 'origin': ORIGIN,
            'encoder': {'type': f'a balanced {m}-way vertex partition', 'space': 'partitions of the host'},
            'semantics': 'union of the parts\' witnesses (vertex-disjoint), then greedy repair of the cut edges',
            'retained': 'every edge inside a part that the part solver keeps',
            'lost': 'every edge between parts (restored only by repair)',
            'cost': {'partition': 'O(n² · passes)', 'parts': 'LP + CaDiCaL per part'},
            'failure_conditions': ['the partition is a local optimum of the cut',
                                   'cut edges are only repaired greedily'],
            'kind': 'conservative-definition', 'composition': 'DCConj.decomposition_union (vertex-disjoint union)'}


# ---------------------------------------------------------------- Lean obligation

DISJOINT = '∀ e ∈ S, ∀ f ∈ T, e.1 ≠ f.1 ∧ e.1 ≠ f.2 ∧ e.2 ≠ f.1 ∧ e.2 ≠ f.2'


def conjectures():
    tf = RP.DOMAINS['triangle_free_host_v1']['model']

    def sampler(rng):
        vs = list(range(6))
        rng.shuffle(vs)
        cut = rng.randrange(1, 6)
        A, B = vs[:cut], vs[cut:] if rng.random() < 0.8 else vs[cut - 1:]
        pick = lambda X: frozenset((u, v) for u in X for v in X if u != v and rng.random() < 0.35)
        return {'S': pick(A), 'T': pick(B)}
    S = {'name': 'S', 'type': 'GT.Edges'}
    T = {'name': 'T', 'type': 'GT.Edges'}
    hs = {'name': 'hS', 'hyp': True, 'lean': 'GT.TriangleFree S', 'model': lambda v: tf(v['S'])}
    ht = {'name': 'hT', 'hyp': True, 'lean': 'GT.TriangleFree T', 'model': lambda v: tf(v['T'])}
    hd = {'name': 'hd', 'hyp': True, 'lean': DISJOINT, 'model': lambda v: vertex_disjoint(v['S'], v['T'])}
    return [RP._conj('decomposition_union', [S, T, hs, ht, hd], 'GT.TriangleFree (S ∪ T)',
                     lambda v: tf(v['S'] | v['T']), sampler, ORIGIN, 'composition', 'decomposition')]


def recipes(conj, library):
    if conj.get('role') != 'composition':
        return []
    head = ['intro S T hS hT hd', 'unfold GT.TriangleFree at *', 'intro e he f hf g hg h',
            'simp only [Finset.mem_union] at he hf hg',
            'rcases he with he | he <;> rcases hf with hf | hf <;> rcases hg with hg | hg']
    cases = ['exact hS e he f hf g hg h', 'exact hT e he f hf g hg h'] + \
        [f'(have h1 := hd {a} h{a} {b} h{b}; omega)' for a, b in (('e', 'f'), ('e', 'g'), ('f', 'e'), ('f', 'g'),
                                                                 ('g', 'e'), ('g', 'f'))]
    body = 'all_goals first\n' + '\n'.join(f'  | {c}' for c in cases)
    return [('union-cases-omega', '\n'.join(head + [body]))]


__all__ = ['balanced_partition', 'cut_size', 'part_task', 'vertex_disjoint', 'exact_components',
           'decompose_and_repair', 'whole', 'proposal', 'conjectures', 'recipes', 'FAMILY', 'ORIGIN', 'MAX_PARTS']
