"""Generated valid inequalities, generator v2: patterns on up to seven vertices (B20_R37).

B20_R31's generator (`invention.cuts.generate`, v1) enumerates every graph on at most six
vertices and keeps K5 (≤ 6) and the 5-wheel (≤ 7). On the dense hosts of B20_R35 those rows leave
LP gaps of 1–2 edges. Generator v2 extends the same rule to every graph on at most seven vertices
(the networkx atlas: 1,253 graphs). A graph F is kept iff three conditions hold:
  * F is connected and every edge of F lies in a triangle;
  * F's LP under the triangle rows exceeds ex(F);
  * F's LP under the triangle rows and every copy, inside F, of the patterns kept before it
    exceeds ex(F).
At seven vertices exhaustive search over 2^21 edge subsets is too slow. ex(F) is therefore
computed with HiGHS's exact MILP, an untrusted producer. Its solution is re-checked as a
triangle-free subset, which proves ex(F) ≥ that value. The upper side, Σ ≤ ex(F), is what Lean
proves. A wrong (too small) ex would make the Lean statement false, and Lean would not check it.

**Lean (`PCDefs`, the B20_R31 definitions).** v2 adds one lemma, `pc_adj_comm`:
PC.adj S u v = PC.adj S v u. A pattern bound may then use, besides the bridge instances and
adj ≤ 1:
  * instances of the *earlier* checked pattern bounds on every copy of an earlier pattern inside
    F;
  * commutation facts that orient their terms.
`omega` closes the goal by integer rounding. A pattern whose bound is beyond this rank stays
UNRESOLVED and is not used.

**Copies in a host.** v1's `invention.cuts.maps` enumerates every subgraph monomorphism and keeps
one per edge set. That is |Aut(F)| maps per copy, 5,040 for K7. v2's `maps_fast` breaks symmetry
instead: it computes Aut(F) by brute force (|V(F)| ≤ 7) and keeps only maps φ that are
lexicographically least, as tuples of host vertices, among {φ ∘ σ : σ ∈ Aut(F)}. That is one map
per edge-set copy. Partial maps are pruned with a necessary condition on the vertices already
fixed. The result is the same set of copies, in a deterministic order.
"""
import itertools
import time

from . import cuts as C1
from . import representations as RP

MAX_VERTICES = 7
HEAVY_EDGES, HEAVY_HEARTBEATS = 17, 4000000      # proofs over 17+ atoms get a larger elaboration budget
ORIGIN = 'generated:pattern-inequalities-v2'
FAMILY = 'relaxation'


def ex_milp(edges):
    """(ex(F), a maximum triangle-free subset) by HiGHS MILP, re-checked."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    E = sorted(tuple(sorted(e)) for e in edges)
    T = C1.pattern_triangles(E)
    if not T:
        return len(E), E
    idx = {e: i for i, e in enumerate(E)}
    A = np.zeros((len(T), len(E)))
    for j, t in enumerate(T):
        for p in itertools.combinations(t, 2):
            A[j, idx[tuple(sorted(p))]] = 1
    r = milp(-np.ones(len(E)), constraints=LinearConstraint(A, -np.inf, 2), integrality=np.ones(len(E)),
             bounds=Bounds(0, 1))
    if r.status != 0:
        raise RuntimeError(f'MILP failed: {r.message}')
    sub = [E[i] for i in range(len(E)) if r.x[i] > 0.5]
    if not C1._tf(sub):
        raise RuntimeError('MILP solution is not triangle-free')
    return len(sub), sub


def automorphisms(n, edges):
    E = {frozenset(e) for e in edges}
    return [p for p in itertools.permutations(range(n)) if {frozenset((p[u], p[v])) for u, v in edges} == E]


def maps_fast(task, pattern, *, limit=None, stop=None):
    """One vertex map per distinct copy (the lexicographically least under Aut(F)); same copies as
    invention.cuts.maps. Returns (maps, cut)."""
    adj = {v: set() for v in range(task.n)}
    for u, v in task.edges:
        adj[u].add(v); adj[v].add(u)
    P = [tuple(e) for e in pattern['edges']]
    n = pattern['vertices']
    padj = {v: set() for v in range(n)}
    for u, v in P:
        padj[u].add(v); padj[v].add(u)
    if len(P) == n * (n - 1) // 2:                       # a clique: increasing vertex sets
        return _clique_maps(adj, n, limit, stop)
    aut = [s for s in (pattern.get('_aut') or automorphisms(n, P)) if list(s) != list(range(n))]
    stab = [[s for s in aut if all(s[j] <= i for j in range(i + 1))] for i in range(n)]
    out, cut = [], [False]
    phi = [None] * n

    def least():
        t = tuple(phi)
        return all(tuple(phi[s[i]] for i in range(n)) >= t for s in aut)

    def partial_ok(i):
        # necessary: no automorphism that maps 0..i into 0..i gives a smaller prefix
        pre = tuple(phi[:i + 1])
        return all(tuple(phi[s[j]] for j in range(i + 1)) >= pre for s in stab[i])

    def extend(i):
        if cut[0] or (limit is not None and len(out) >= limit) or (stop is not None and stop()):
            cut[0] = True
            return
        if i == n:
            if least():
                out.append(list(phi))
            return
        mapped = [q for q in padj[i] if q < i]
        cand = set(range(task.n)) if not mapped else set.intersection(*(adj[phi[q]] for q in mapped))
        cand -= set(phi[:i])
        for h in sorted(cand):
            if len(adj[h]) < len(padj[i]):
                continue
            phi[i] = h
            if partial_ok(i):
                extend(i + 1)
            phi[i] = None
    extend(0)
    return out, cut[0]


def _clique_maps(adj, k, limit, stop):
    out, cut = [], [False]

    def grow(clique, cand):
        if cut[0] or (limit is not None and len(out) >= limit) or (stop is not None and stop()):
            cut[0] = True
            return
        if len(clique) == k:
            out.append(list(clique))
            return
        for v in sorted(cand):
            if v > (clique[-1] if clique else -1):
                grow(clique + [v], cand & adj[v])
    grow([], set(adj))
    return out, cut[0]


def copies_fast(task, pattern, *, limit=None, stop=None):
    found, cut = maps_fast(task, pattern, limit=limit, stop=stop)
    return [tuple(sorted(tuple(sorted((phi[u], phi[v]))) for u, v in pattern['edges'])) for phi in found], cut


class _Graph(C1._Graph):
    pass


def generate(max_vertices=MAX_VERTICES, *, stats=None):
    """The generated patterns on up to `max_vertices` vertices, atlas order; each with its earlier
    patterns' copies inside it ('uses'), for the Lean proof."""
    import networkx as nx
    from networkx.generators.atlas import graph_atlas_g
    out = []
    st = {'graphs_in_range': 0, 'connected_triangle_covered': 0, 'implied_by_triangle_rows': 0,
          'implied_by_earlier_patterns': [], 'kept': 0}
    for G in graph_atlas_g()[1:]:
        n, m = G.number_of_nodes(), G.number_of_edges()
        if n < 4 or n > max_vertices:
            continue
        st['graphs_in_range'] += 1
        if not nx.is_connected(G):
            continue
        E = sorted(tuple(sorted(e)) for e in G.edges())
        tri_edges = {frozenset(p) for t in C1.pattern_triangles(E) for p in itertools.combinations(t, 2)}
        if any(frozenset(e) not in tri_edges for e in E):
            continue
        st['connected_triangle_covered'] += 1
        ex, witness = ex_milp(E)
        lp_tri = C1.relaxation_lp(n, E)
        if lp_tri <= ex + 1e-6:
            st['implied_by_triangle_rows'] += 1
            continue
        lp = C1.relaxation_lp(n, E, out)
        pid = f'pat{n}_{m}_' + ''.join(f'{u}{v}' for u, v in E)
        if lp <= ex + 1e-6:
            st['implied_by_earlier_patterns'].append({'id': pid, 'ex': ex, 'lp_triangle_rows': round(lp_tri, 6)})
            continue
        host = C1._Graph(n, E)
        uses = [{'pattern': q['id'], 'maps': maps_fast(host, q)[0]} for q in out]
        out.append({'id': pid, 'vertices': n, 'edges': E, 'ex': ex, 'ex_witness': witness, 'lp': round(lp, 6),
                    'lp_triangle_rows': round(lp_tri, 6), 'triangles': C1.pattern_triangles(E),
                    'uses': [u for u in uses if u['maps']]})
    st['kept'] = len(out)
    if stats is not None:
        stats.update(st)
    return out


# ---------------------------------------------------------------- proof support

def proof_support(pattern, earlier):
    """The rows of F's LP (triangles, and copies of earlier patterns inside F) with a positive dual
    weight at the LP optimum: the instances a rounding proof of Σ ≤ ex(F) needs. Untrusted
    guidance; Lean checks the proof."""
    import numpy as np
    from scipy.optimize import linprog
    n, E = pattern['vertices'], [tuple(e) for e in pattern['edges']]
    idx = {e: i for i, e in enumerate(E)}
    rows = [('triangle', None, list(t), [idx[tuple(sorted(p))] for p in itertools.combinations(t, 2)], 2)
            for t in pattern['triangles']]
    host = C1._Graph(n, E)
    for q in earlier:
        for phi in maps_fast(host, q)[0]:
            rows.append(('pattern', q['id'], phi, [idx[tuple(sorted((phi[a], phi[b])))] for a, b in q['edges']], q['ex']))
    A = np.zeros((len(rows), len(E)))
    for j, r in enumerate(rows):
        A[j, r[3]] = 1
    res = linprog(-np.ones(len(E)), A_ub=A, b_ub=np.array([r[4] for r in rows], float), bounds=(0, 1), method='highs')
    y = -res.ineqlin.marginals
    return [(r[0], r[1], r[2]) for j, r in enumerate(rows) if y[j] > 1e-9]


def proof_certificate(pattern, earlier, *, max_denominator=60):
    """An integer rounding certificate for Σ ≤ ex(F), or None. From F's LP dual (untrusted), with
    weights rationalised: integer multipliers m_r on rows (triangles and earlier-pattern copies),
    multipliers s_e on adj ≤ 1 for edges covered less than D times, such that every edge is covered
    at least D times and floor(K / D) = ex(F), where K = Σ m_r b_r + Σ s_e. Checked exactly here;
    Lean checks the proof built from it."""
    from fractions import Fraction
    from math import lcm
    import numpy as np
    from scipy.optimize import linprog
    n, E = pattern['vertices'], [tuple(e) for e in pattern['edges']]
    idx = {e: i for i, e in enumerate(E)}
    rows = [('triangle', None, list(t), [idx[tuple(sorted(p))] for p in itertools.combinations(t, 2)], 2)
            for t in pattern['triangles']]
    host = C1._Graph(n, E)
    for q in earlier:
        for phi in maps_fast(host, q)[0]:
            rows.append(('pattern', q['id'], phi, [idx[tuple(sorted((phi[a], phi[b])))] for a, b in q['edges']], q['ex']))
    A = np.zeros((len(rows), len(E)))
    for j, r in enumerate(rows):
        A[j, r[3]] = 1
    res = linprog(-np.ones(len(E)), A_ub=A, b_ub=np.array([r[4] for r in rows], float), bounds=(0, 1), method='highs')
    y = [Fraction(float(v)).limit_denominator(max_denominator) for v in -res.ineqlin.marginals]
    keep = [j for j in range(len(rows)) if y[j] > 0]
    D = 1
    for j in keep:
        D = lcm(D, y[j].denominator)
    m = {j: int(y[j] * D) for j in keep}
    cover = [0] * len(E)
    for j in keep:
        for i in rows[j][3]:
            cover[i] += m[j]
    slack = {i: D - cover[i] for i in range(len(E)) if cover[i] < D}
    K = sum(m[j] * rows[j][4] for j in keep) + sum(slack.values())
    if K // D != pattern['ex']:
        return None
    return {'D': D, 'K': K, 'rows': [(rows[j][0], rows[j][1], rows[j][2], m[j], rows[j][4]) for j in keep],
            'slack': {E[i]: v for i, v in slack.items()}}


# ---------------------------------------------------------------- Lean obligations

SOURCE = C1.SOURCE                     # PCDefs, unchanged: PC.adj is B20_R31's definition
MODULE = C1.MODULE


def conjectures(patterns):
    base = C1.conjectures([])          # pc_adj_le_one, pc_bridge (with their screening models)
    comm = C1._conj('pc_adj_comm', ['u', 'v'], 'PC.adj S u v = PC.adj S v u',
                    lambda v: C1.adj_model(v['S'], v['u'], v['v']) == C1.adj_model(v['S'], v['v'], v['u']),
                    'comm', 'comm', hyps=False)
    out = [base[0], comm, base[1]]
    for p in patterns:
        names = [f'v{i}' for i in range(p['vertices'])]
        out.append(C1._conj(f'pc_{p["id"]}', names, f'{C1.pattern_sum(p)} ≤ {p["ex"]}',
                            lambda v, p=p: sum(C1.adj_model(v['S'], v[f'v{a}'], v[f'v{b}']) for a, b in p['edges']) <= p['ex'],
                            'pattern', p['id']))
    for c in out:
        c['origin'] = ORIGIN
    return out


def recipes(patterns):
    """Builder-written recipes (named in every receipt): adj, comm and bridge as in v1; a pattern
    bound from its LP support (bridge instances, earlier pattern instances with orienting comm
    facts), every adj ≤ 1, then omega."""
    by_id = {p['id']: p for p in patterns}
    v1 = C1.recipes([])

    def extra(conj, library):
        role = conj.get('role')
        if role in ('adj', 'bridge'):
            return v1(conj, library)
        if role == 'comm':
            return [('comm-or-swap', 'intro S u v\nunfold PC.adj\nsimp only [or_comm]'),
                    ('comm-split', 'intro S u v\nunfold PC.adj\nsplit_ifs <;> first | rfl | (exfalso; tauto)')]
        if role != 'pattern':
            return []
        p = by_id.get(conj['subject'])
        lib = {entry['statement']: entry['const'] for entry in library}
        if p is None or any(k not in lib for k in ('pc_bridge', 'pc_adj_le_one', 'pc_adj_comm')):
            return []
        earlier = [by_id[q] for q in by_id if by_id[q] is not p and patterns.index(by_id[q]) < patterns.index(p)
                   and f'pc_{q}' in lib]
        support = proof_support(p, earlier)
        names = ' '.join(f'v{i}' for i in range(p['vertices']))
        lines = [f'intro S hS hH {names}']
        comm, k = set(), 0
        for kind, qid, verts in support:
            k += 1
            if kind == 'triangle':
                a, b, c = verts
                lines.append(f'have r{k} := {lib["pc_bridge"]} S hS hH v{a} v{b} v{c}')
            else:
                q = by_id[qid]
                lines.append(f'have r{k} := {lib[f"pc_{qid}"]} S hS hH ' + ' '.join(f'v{x}' for x in verts))
                for a, b in q['edges']:
                    x, y = verts[a], verts[b]
                    if x > y:
                        comm.add((x, y))
        for j, (x, y) in enumerate(sorted(comm)):
            lines.append(f'have s{j} := {lib["pc_adj_comm"]} S v{x} v{y}')
        lines += [f'have b{j} := {lib["pc_adj_le_one"]} S v{u} v{v}' for j, (u, v) in enumerate(p['edges'])]
        out = []
        cert = proof_certificate(p, earlier)
        heavy = len(p['edges']) >= HEAVY_EDGES
        if cert is not None:
            text = _sum_tactic(p, cert, by_id, lib)
            if heavy:                                    # hoisted before the theorem (search.split_options)
                text = f'set_option maxHeartbeats {HEAVY_HEARTBEATS} in\n' + text
            out.append(('lp-certificate-sum', text))
        if not heavy:                                    # a heavy fallback would exhaust the shared module
            out.append(('lp-support-omega', '\n'.join(lines + ['omega'])))
        return out
    return extra


def _sum_tactic(p, cert, by_id, lib):
    """intro; one scaled fact per certificate row (Nat.mul_le_mul with a literal multiplier); their
    sum as a single fact; clear everything else but the comm facts; omega."""
    names = ' '.join(f'v{i}' for i in range(p['vertices']))
    lines = [f'intro S hS hH {names}']
    facts, comm = [], set()
    for k, (kind, qid, verts, mult, rhs) in enumerate(cert['rows']):
        if kind == 'triangle':
            a, b, c = verts
            src = f'{lib["pc_bridge"]} S hS hH v{a} v{b} v{c}'
        else:
            src = f'{lib[f"pc_{qid}"]} S hS hH ' + ' '.join(f'v{x}' for x in verts)
            for a, b in by_id[qid]['edges']:
                x, y = verts[a], verts[b]
                if x > y:
                    comm.add((x, y))
        lines.append(f'have k{k} := Nat.mul_le_mul (Nat.le_refl {mult}) ({src})' if mult != 1 else f'have k{k} := {src}')
        facts.append(f'k{k}')
    for j, ((u, v), mult) in enumerate(sorted(cert['slack'].items())):
        lines.append(f'have e{j} := Nat.mul_le_mul (Nat.le_refl {mult}) ({lib["pc_adj_le_one"]} S v{u} v{v})'
                     if mult != 1 else f'have e{j} := {lib["pc_adj_le_one"]} S v{u} v{v}')
        facts.append(f'e{j}')
    for j, (x, y) in enumerate(sorted(comm)):
        lines.append(f'have s{j} := {lib["pc_adj_comm"]} S v{x} v{y}')
    acc = facts[-1]
    for f in reversed(facts[:-1]):
        acc = f'Nat.add_le_add {f} ({acc})'
    lines.append(f'have key := {acc}')
    lines.append('clear ' + ' '.join(facts))
    lines.append('omega')
    return '\n'.join(lines)


def obligations_ok(state, patterns):
    st = {s['id']: s.get('status') for s in state['statements']}
    base = all(st.get(k) == 'CHECKED' for k in ('pc_adj_le_one', 'pc_adj_comm', 'pc_bridge'))
    return st, [p for p in patterns if base and st.get(f'pc_{p["id"]}') == 'CHECKED']
