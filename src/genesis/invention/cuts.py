"""Generated valid inequalities: a relaxation family (handoff s15.3 / W10, GV4 component; B20_R31).

The B20_RX3 components build on the LP relaxation of the largest triangle-free subgraph:

    max Σ x_e   s.t.   x(T) ≤ 2 for every host triangle T,   0 ≤ x ≤ 1.

This module generates *new* inequalities for that relaxation, instead of hand-writing them.

**Generator.** It enumerates every graph F on at most MAX_VERTICES vertices and MAX_EDGES edges
(the networkx atlas: all graphs up to isomorphism) that is connected and has every edge in a
triangle. For each F it computes two numbers:
  * ex(F), the largest triangle-free subgraph of F, by exhaustive search;
  * the triangle-LP value of F alone.
F is kept iff the LP value exceeds ex(F). Only then is the inequality

    x(φ(E(F))) ≤ ex(F)   for every copy φ of F in the host

not implied by the triangle inequalities. At these bounds the generator keeps K5 (ex 6, LP 20/3)
and the 5-wheel W5 (ex 7, LP 15/2).

**Validity (Lean, `PCDefs`).** Write a(u, v) for the 0/1 adjacency of an edge set S. For every S
that is triangle-free and lists edges as (u, v) with u < v (host form), three facts hold:
  * `pc_adj_le_one`: a(u, v) ≤ 1;
  * `pc_bridge`: a(x, y) + a(y, z) + a(x, z) ≤ 2 for all x, y, z. A sorted triple of mutually
    adjacent vertices would be a GT triangle;
  * one statement per generated pattern: Σ over the pattern's edges of a(φ u, φ v) ≤ ex(F), for every
    assignment of the pattern's vertices (copies, and degenerate assignments too).
The pattern statement follows from the bridge instances on F's triangles by integer rounding
(`omega`, with a ≤ 1 on every edge). For W5 the five triangle instances sum to 2·spokes + rim ≤ 10;
adding rim ≤ 5 gives 2·Σ ≤ 15, hence Σ ≤ 7. On a host edge set S, a(u, v) is exactly the indicator
of the edge {u, v} in S, so the statement says the cut holds on every copy of F in every host.

**Use as a component.** `cut_lp_values(task, patterns)` solves the strengthened LP: the triangle
rows plus one row per copy of each checked pattern. `cut_lp_greedy` is the B20_RX3 LP-ordered
greedy with LP-perturbed restarts, run on those values. Every witness is re-checked by the domain
checker. The float LP is search guidance, never a certificate.
"""
import itertools

from . import representations as RP

MAX_VERTICES, MAX_EDGES = 6, 15                  # every graph on at most six vertices
MODULE = 'PCDefs'
ORIGIN = 'generated:pattern-inequalities-v1'
FAMILY = 'relaxation'


# ---------------------------------------------------------------- generator

def _tf(edges):
    adj = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v); adj.setdefault(v, set()).add(u)
    return not any(adj[u] & adj[v] for u, v in edges)


def extremal(edges):
    """ex(F): the largest triangle-free subset of the edge list, by exhaustive search."""
    E = list(edges)
    best = 0
    for mask in range(1 << len(E)):
        k = bin(mask).count('1')
        if k > best and _tf([E[i] for i in range(len(E)) if mask >> i & 1]):
            best = k
    return best


def pattern_triangles(edges):
    E = {frozenset(e) for e in edges}
    V = sorted({x for e in edges for x in e})
    return [t for t in itertools.combinations(V, 3) if all(frozenset(p) in E for p in itertools.combinations(t, 2))]


class _Graph:
    """A pattern seen as a host (vertices 0..n-1, sorted edge list)."""

    def __init__(self, n, edges):
        self.n, self.edges = n, [tuple(sorted(e)) for e in edges]


def relaxation_lp(n, edges, kept=()):
    """The LP value of F under the triangle rows and every copy, inside F, of the patterns in
    `kept` (float; generation only)."""
    import numpy as np
    from scipy.optimize import linprog
    E = sorted(tuple(sorted(e)) for e in edges)
    idx = {e: i for i, e in enumerate(E)}
    rows = [([idx[tuple(sorted(p))] for p in itertools.combinations(t, 2)], 2) for t in pattern_triangles(E)]
    for q in kept:
        rows += [([idx[e] for e in c], q['ex']) for c in copies(_Graph(n, E), q)[0]]
    if not rows:
        return float(len(E))
    A = np.zeros((len(rows), len(E)))
    for j, (r, _) in enumerate(rows):
        A[j, r] = 1
    res = linprog(-np.ones(len(E)), A_ub=A, b_ub=np.array([c for _, c in rows], float), bounds=(0, 1), method='highs')
    return -res.fun


def triangle_lp(edges):
    """The triangle-LP value of F alone (float; generation only)."""
    n = 1 + max((x for e in edges for x in e), default=-1)
    return relaxation_lp(n, edges)


def generate(max_vertices=MAX_VERTICES, max_edges=MAX_EDGES, *, stats=None):
    """The generated patterns, in atlas order (vertices, then edges). F is kept iff it is connected,
    every edge lies in a triangle, and the LP of F under the triangle rows and the copies of the
    patterns kept before it exceeds ex(F). `stats` (a dict), if given, receives the counts."""
    import networkx as nx
    from networkx.generators.atlas import graph_atlas_g
    out = []
    st = {'graphs_in_range': 0, 'connected_triangle_covered': 0, 'implied_by_triangle_rows': 0,
          'implied_by_earlier_patterns': [], 'kept': 0}
    for G in graph_atlas_g()[1:]:
        n, m = G.number_of_nodes(), G.number_of_edges()
        if n < 4 or n > max_vertices or m > max_edges:
            continue
        st['graphs_in_range'] += 1
        if not nx.is_connected(G):
            continue
        E = sorted(tuple(sorted(e)) for e in G.edges())
        tri_edges = {frozenset(p) for t in pattern_triangles(E) for p in itertools.combinations(t, 2)}
        if any(frozenset(e) not in tri_edges for e in E):
            continue
        st['connected_triangle_covered'] += 1
        ex, lp_tri = extremal(E), relaxation_lp(n, E)
        if lp_tri <= ex + 1e-6:
            st['implied_by_triangle_rows'] += 1
            continue
        lp = relaxation_lp(n, E, out)
        pid = f'pat{n}_{m}_' + ''.join(f'{u}{v}' for u, v in E)
        if lp <= ex + 1e-6:
            st['implied_by_earlier_patterns'].append({'id': pid, 'ex': ex, 'lp_triangle_rows': round(lp_tri, 6)})
            continue
        out.append({'id': pid, 'vertices': n, 'edges': E, 'ex': ex, 'lp': round(lp, 6),
                    'lp_triangle_rows': round(lp_tri, 6), 'triangles': pattern_triangles(E)})
    st['kept'] = len(out)
    if stats is not None:
        stats.update(st)
    return out


# ---------------------------------------------------------------- copies in a host

def maps(task, pattern, *, limit=None, stop=None):
    """One vertex map per distinct copy of the pattern in the host (subgraph monomorphisms, not
    necessarily induced; the first map found in a fixed search order), as a list of host vertices
    indexed by pattern vertex. Enumeration ends early when `stop()` turns true or `limit` copies
    are found."""
    return _enumerate(task, pattern, limit, stop)[0]


def copies(task, pattern, *, limit=None, stop=None):
    """Distinct copies as sorted tuples of host edges (u, v), u < v, and whether enumeration was cut."""
    found, cut = _enumerate(task, pattern, limit, stop)
    return [tuple(sorted(tuple(sorted((phi[u], phi[v]))) for u, v in pattern['edges'])) for phi in found], cut


def _enumerate(task, pattern, limit, stop):
    adj = {v: set() for v in range(task.n)}
    for u, v in task.edges:
        adj[u].add(v); adj[v].add(u)
    P = pattern['edges']
    n = pattern['vertices']
    padj = {v: set() for v in range(n)}
    for u, v in P:
        padj[u].add(v); padj[v].add(u)
    order = sorted(range(n), key=lambda v: (-len(padj[v]), v))       # most constrained first
    seen, out, cut = set(), [], [False]

    def extend(i, phi):
        if cut[0] or (limit is not None and len(out) >= limit) or (stop is not None and stop()):
            cut[0] = True
            return
        if i == n:
            es = tuple(sorted(tuple(sorted((phi[u], phi[v]))) for u, v in P))
            if es not in seen:
                seen.add(es); out.append([phi[v] for v in range(n)])
            return
        p = order[i]
        mapped = [q for q in padj[p] if q in phi]
        cand = set(range(task.n)) if not mapped else set.intersection(*(adj[phi[q]] for q in mapped))
        used = set(phi.values())
        for h in sorted(cand - used):
            if len(adj[h]) < len(padj[p]):
                continue
            phi[p] = h
            extend(i + 1, phi)
            del phi[p]
    extend(0, {})
    return out, cut[0]


# ---------------------------------------------------------------- the component

def cut_lp_values(task, patterns, *, stop=None, max_rows=20000):
    """LP values per host edge for the triangle LP strengthened by every found copy of the
    patterns (floats from an untrusted producer). Returns (x, {pattern id: (copies, complete)},
    LP value)."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    from ..discovery.obstruction import triangles
    E = [tuple(e) for e in task.edges]
    if not E:
        return [], {}, 0.0
    idx = {e: i for i, e in enumerate(E)}
    rows = [[idx[e] for e in t] for t in triangles(task)]
    rhs = [2] * len(rows)
    added = {}
    for pat in patterns:
        cs, cut = copies(task, pat, limit=max_rows, stop=stop)
        added[pat['id']] = (len(cs), not cut)
        rows += [[idx[e] for e in c] for c in cs]
        rhs += [pat['ex']] * len(cs)
        if cut:
            break
    if not rows:
        return [1.0] * len(E), added, float(len(E))
    A = lil_matrix((len(rows), len(E)))
    for j, r in enumerate(rows):
        for i in r:
            A[j, i] = 1
    res = linprog(-np.ones(len(E)), A_ub=A.tocsr(), b_ub=np.array(rhs, float), bounds=(0, 1), method='highs')
    if res.status != 0:
        raise RuntimeError(f'LP producer failed: {res.message}')
    return list(res.x), added, -res.fun


SEPARATION_SHARE = 0.5


def cut_lp_greedy(task, patterns, budget, seed=0):
    """The B20_RX3 LP-ordered greedy with LP-perturbed restarts (discovery.construct.lp_greedy), on
    the strengthened LP's values. Copy enumeration stops at SEPARATION_SHARE of the budget, and the
    LP solve is charged to the same budget."""
    from ..discovery.construct import Budget, lp_greedy
    b = budget if isinstance(budget, Budget) else Budget(budget)
    x, added, value = cut_lp_values(task, patterns, stop=lambda: b.used() >= SEPARATION_SHARE * b.seconds)
    o = lp_greedy(task, b, seed, x=x)
    return dict(o, copies={k: list(v) for k, v in added.items()}, lp_value=value)


def proposal(patterns):
    return {'id': 'cut_lp_greedy', 'family': FAMILY, 'origin': ORIGIN,
            'patterns': [{'id': p['id'], 'edges': p['edges'], 'ex': p['ex'], 'lp': p['lp']} for p in patterns],
            'ingredients': ['generated pattern inequalities x(copy of F) <= ex(F) (validity: PCDefs lemmas)',
                            'triangle LP strengthened by every copy found within half the budget',
                            'LP-ordered greedy with LP-perturbed restarts (B20_RX3 lp_greedy), checker-validated'],
            'kind': 'conservative-definition', 'validity': 'one Lean lemma per pattern over PC.adj'}


# ---------------------------------------------------------------- Lean obligations

SOURCE = f'''import {RP.DEFS_MODULE}

namespace PC

/-- 0/1 adjacency of an edge set, either orientation (B20_R31, {ORIGIN}). -/
def adj (S : GT.Edges) (u v : ℕ) : ℕ := if (u, v) ∈ S ∨ (v, u) ∈ S then 1 else 0

end PC
'''

HOST_FORM = '∀ e ∈ S, e.1 < e.2'
SAMPLE_VERTICES = 7


def adj_model(S, u, v):
    return 1 if (u, v) in S or (v, u) in S else 0


def _sampler(names):
    def sample(rng):
        V = range(SAMPLE_VERTICES)
        S = frozenset((u, v) for u in V for v in V if u < v and rng.random() < 0.45)
        # thin to triangle-free half the time, so the hypotheses hold on many samples
        if rng.random() < 0.5:
            keep = []
            for e in sorted(S, key=lambda _: rng.random()):
                if _tf(keep + [e]):
                    keep.append(e)
            S = frozenset(keep)
        out = {'S': S}
        out.update({n: rng.randrange(SAMPLE_VERTICES) for n in names})
        return out
    return sample


def _lean_value(b, x):
    if b['type'] == 'GT.Edges':
        return RP.lean_value(b, x)
    return str(x)


def _host_form(S):
    return all(u < v for u, v in S)


def _conj(cid, names, concl, model, role, subject, hyps=True):
    tf = RP.DOMAINS['triangle_free_host_v1']['model']
    binders = [{'name': 'S', 'type': 'GT.Edges'}]
    if hyps:
        binders += [{'name': 'hS', 'hyp': True, 'lean': 'GT.TriangleFree S', 'model': lambda v: tf(v['S'])},
                    {'name': 'hH', 'hyp': True, 'lean': HOST_FORM, 'model': lambda v: _host_form(v['S'])}]
    binders += [{'name': n, 'type': 'ℕ'} for n in names]
    return {'id': cid, 'binders': binders, 'concl': concl, 'model': model, 'sampler': _sampler(names),
            'origin': ORIGIN, 'role': role, 'subject': subject, 'lean_value': _lean_value}


def pattern_sum(p, names='v'):
    return ' + '.join(f'PC.adj S {names}{u} {names}{v}' for u, v in p['edges'])


def conjectures(patterns):
    """adj ≤ 1, the bridge, and one bound per generated pattern; each with a Python model for the screen."""
    out = [_conj('pc_adj_le_one', ['u', 'v'], 'PC.adj S u v ≤ 1',
                 lambda v: adj_model(v['S'], v['u'], v['v']) <= 1, 'adj', 'adj', hyps=False),
           _conj('pc_bridge', ['x', 'y', 'z'], 'PC.adj S x y + PC.adj S y z + PC.adj S x z ≤ 2',
                 lambda v: adj_model(v['S'], v['x'], v['y']) + adj_model(v['S'], v['y'], v['z']) +
                 adj_model(v['S'], v['x'], v['z']) <= 2, 'bridge', 'bridge')]
    for p in patterns:
        names = [f'v{i}' for i in range(p['vertices'])]
        out.append(_conj(f'pc_{p["id"]}', names, f'{pattern_sum(p)} ≤ {p["ex"]}',
                         lambda v, p=p: sum(adj_model(v['S'], v[f'v{a}'], v[f'v{b}']) for a, b in p['edges']) <= p['ex'],
                         'pattern', p['id']))
    return out


def _orientation_cases():
    tri = [f'exact hS _ {a} _ {b} _ {c} ⟨rfl, rfl, rfl⟩' for a, b, c in itertools.permutations(('h1', 'h2', 'h3'))]
    order = '(have o1 := hH _ h1; have o2 := hH _ h2; have o3 := hH _ h3; (try simp only at o1 o2 o3); omega)'
    return ['exfalso', 'unfold GT.TriangleFree at hS',
            'rcases h1 with h1 | h1 <;> rcases h2 with h2 | h2 <;> rcases h3 with h3 | h3',
            'all_goals first\n' + '\n'.join(f'  | {c}' for c in tri + [order])]


def recipes(patterns):
    """Builder-written recipes (named in every receipt): `extra(conj, library)` for loop.prove_all."""
    by_id = {p['id']: p for p in patterns}

    def extra(conj, library):
        role = conj.get('role')
        if role == 'adj':
            return [('adj-split', 'intro S u v\nunfold PC.adj\nsplit <;> omega'),
                    ('adj-split-ifs', 'intro S u v\nunfold PC.adj\nsplit_ifs <;> omega')]
        if role == 'bridge':
            head = ['intro S hS hH x y z', 'unfold PC.adj']
            by_cases = ['by_cases h1 : (x, y) ∈ S ∨ (y, x) ∈ S <;> by_cases h2 : (y, z) ∈ S ∨ (z, y) ∈ S <;> '
                        'by_cases h3 : (x, z) ∈ S ∨ (z, x) ∈ S <;> simp only [h1, h2, h3, if_true, if_false] <;> '
                        'try omega']
            split = ['split_ifs with h1 h2 h3 <;> try omega']
            return [('adjacency-orientation-cases', '\n'.join(head + split + _orientation_cases())),
                    ('adjacency-orientation-by-cases', '\n'.join(head + by_cases + _orientation_cases()))]
        if role == 'pattern':
            p = by_id.get(conj['subject'])
            lib = {entry['statement']: entry['const'] for entry in library}
            if p is None or 'pc_bridge' not in lib or 'pc_adj_le_one' not in lib:
                return []
            names = ' '.join(f'v{i}' for i in range(p['vertices']))
            haves = [f'have t{j} := {lib["pc_bridge"]} S hS hH v{a} v{b} v{c}' for j, (a, b, c) in enumerate(p['triangles'])]
            haves += [f'have b{j} := {lib["pc_adj_le_one"]} S v{u} v{v}' for j, (u, v) in enumerate(p['edges'])]
            return [('bridge-instances-omega', '\n'.join([f'intro S hS hH {names}'] + haves + ['omega']))]
        return []
    return extra


def obligations_ok(state, patterns):
    """{statement id: status} and the patterns whose bound is CHECKED (adj and bridge CHECKED too)."""
    st = {s['id']: s.get('status') for s in state['statements']}
    base = st.get('pc_adj_le_one') == 'CHECKED' and st.get('pc_bridge') == 'CHECKED'
    return st, [p for p in patterns if base and st.get(f'pc_{p["id"]}') == 'CHECKED']


__all__ = ['generate', 'extremal', 'triangle_lp', 'copies', 'cut_lp_values', 'cut_lp_greedy', 'proposal',
           'conjectures', 'recipes', 'obligations_ok', 'SOURCE', 'MODULE', 'ORIGIN', 'FAMILY', 'adj_model']
