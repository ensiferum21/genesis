"""Generated valid inequalities for C4-free subgraphs: the pattern generator, transferred from triangle-free (B20_R46).

**What is transferred.** The triangle-free generator (B20_R31 v1, B20_R37 v2) is an invention procedure:
  1. enumerate small graphs F;
  2. compute ex(F), the largest motif-free subgraph of F;
  3. keep F when the LP of F, under the motif rows and the copies of earlier kept patterns, exceeds ex(F);
  4. prove Σ_{e ∈ F} x_e ≤ ex(F) in Lean from an integer rounding of F's LP dual.
This module runs the same procedure, unchanged, for a structurally different motif, the 4-cycle (domain
c4_host_v2). Only the motif-specific parts change:
  * the motif rows are 4-cycles a-b-c-d-a with 3 on the right (a C4-free set keeps at most 3 of a 4-cycle's
    edges), not triangles with 2;
  * the Lean bridge needs a ≠ c and b ≠ d. The domain's `G4.C4Free` only forbids 4-cycles on distinct
    opposite vertices, so pattern statements carry pairwise distinctness of their vertices;
  * the domain predicate is `G4.C4Free` (B18's `G4Defs`, the c4_host_v2 contract), not `GT.TriangleFree`.

**Why it matters.** The evaluator's certification of C4 hosts uses LP over 4-cycle rows, then SAT/DRAT.
That LP is very weak: on K6 it gives 11.25 against ex = 7. This is why B20_R23's C4 causal pilot was
UNSETTLED_REFERENCE. The generated C4 rows tighten it (K6: 7.5).

**Kept rule (unchanged from v2).** F has 4 to 6 vertices, is connected, and every edge lies in a 4-cycle.
F's LP under the 4-cycle rows exceeds ex(F), and F's LP under those rows plus every copy, inside F, of the
patterns kept before it also exceeds ex(F).
  * ex(F) comes from HiGHS's exact MILP, an untrusted producer. Its witness is re-checked as C4-free, which
    proves ex(F) ≥ that value.
  * Lean proves the upper side. A wrong (too small) ex would make the Lean statement false.

**Lean (`P4Defs`, new).** It defines `P4.adj`, the 0/1 adjacency of an edge set (the same definition as
`PC.adj`, in its own namespace), and imports `G4Defs`. The obligations:
  * p4_adj_le_one: P4.adj S u v ≤ 1;
  * p4_adj_comm: P4.adj S u v = P4.adj S v u;
  * p4_bridge: G4.C4Free S → a ≠ c → b ≠ d → adj a b + adj b c + adj c d + adj d a ≤ 3;
  * one bound per pattern: G4.C4Free S → (pairwise distinct v_i) → Σ_{uv ∈ F} adj v_u v_v ≤ ex(F).
"""
import itertools

from . import cuts as C1
from . import cuts_v2 as C2
from . import representations as RP

MAX_VERTICES = 6
MODULE = 'P4Defs'
ORIGIN = 'generated:pattern-inequalities-c4-v1'
FAMILY = 'relaxation'
DOMAIN = 'c4_host_v2'
HEAVY_EDGES, HEAVY_HEARTBEATS = 13, 4000000


def pattern_cycles(edges):
    """The 4-cycles of F as vertex tuples (a, b, c, d) for the cycle a-b-c-d-a, each cycle once: a is the
    least vertex and b < d."""
    E = {frozenset(e) for e in edges}
    V = sorted({x for e in edges for x in e})
    out = []
    for a, b, c, d in itertools.permutations(V, 4):
        if a != min(a, b, c, d) or b > d:
            continue
        if all(frozenset(p) in E for p in ((a, b), (b, c), (c, d), (d, a))):
            out.append((a, b, c, d))
    return out


def cycle_edges(cyc):
    a, b, c, d = cyc
    return [tuple(sorted(p)) for p in ((a, b), (b, c), (c, d), (d, a))]


def c4free(edges):
    return RP.c4free(set(map(tuple, edges)))


def ex_milp(edges):
    """(ex_C4(F), a maximum C4-free subset) by HiGHS MILP, re-checked."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    E = sorted(tuple(sorted(e)) for e in edges)
    cyc = pattern_cycles(E)
    if not cyc:
        return len(E), E
    idx = {e: i for i, e in enumerate(E)}
    A = np.zeros((len(cyc), len(E)))
    for j, c in enumerate(cyc):
        for e in cycle_edges(c):
            A[j, idx[e]] = 1
    r = milp(-np.ones(len(E)), constraints=LinearConstraint(A, -np.inf, 3), integrality=np.ones(len(E)),
             bounds=Bounds(0, 1))
    if r.status != 0:
        raise RuntimeError(f'MILP failed: {r.message}')
    sub = [E[i] for i in range(len(E)) if r.x[i] > 0.5]
    if not c4free(sub):
        raise RuntimeError('MILP solution is not C4-free')
    return len(sub), sub


def _rows(n, E, kept):
    idx = {e: i for i, e in enumerate(E)}
    rows = [('cycle', None, list(c), [idx[e] for e in cycle_edges(c)], 3) for c in pattern_cycles(E)]
    host = C1._Graph(n, E)
    for q in kept:
        for phi in C2.maps_fast(host, q)[0]:
            rows.append(('pattern', q['id'], phi, [idx[tuple(sorted((phi[a], phi[b])))] for a, b in q['edges']], q['ex']))
    return rows


def _lp(n, E, rows):
    import numpy as np
    from scipy.optimize import linprog
    if not rows:
        return float(len(E)), None
    A = np.zeros((len(rows), len(E)))
    for j, r in enumerate(rows):
        A[j, r[3]] = 1
    res = linprog(-np.ones(len(E)), A_ub=A, b_ub=np.array([r[4] for r in rows], float), bounds=(0, 1), method='highs')
    return -res.fun, -res.ineqlin.marginals


def relaxation_lp(n, edges, kept=()):
    E = sorted(tuple(sorted(e)) for e in edges)
    return _lp(n, E, _rows(n, E, kept))[0]


def generate(max_vertices=MAX_VERTICES, *, stats=None):
    """The generated C4 patterns on up to `max_vertices` vertices, in atlas order."""
    import networkx as nx
    from networkx.generators.atlas import graph_atlas_g
    out = []
    st = {'graphs_in_range': 0, 'connected_cycle_covered': 0, 'implied_by_cycle_rows': 0,
          'implied_by_earlier_patterns': [], 'kept': 0}
    for G in graph_atlas_g()[1:]:
        n, m = G.number_of_nodes(), G.number_of_edges()
        if n < 4 or n > max_vertices:
            continue
        st['graphs_in_range'] += 1
        if not nx.is_connected(G):
            continue
        E = sorted(tuple(sorted(e)) for e in G.edges())
        covered = {e for c in pattern_cycles(E) for e in cycle_edges(c)}
        if any(e not in covered for e in E):
            continue
        st['connected_cycle_covered'] += 1
        ex, witness = ex_milp(E)
        lp_cyc = relaxation_lp(n, E)
        if lp_cyc <= ex + 1e-6:
            st['implied_by_cycle_rows'] += 1
            continue
        lp = relaxation_lp(n, E, out)
        pid = f'c4pat{n}_{m}_' + ''.join(f'{u}{v}' for u, v in E)
        if lp <= ex + 1e-6:
            st['implied_by_earlier_patterns'].append({'id': pid, 'ex': ex, 'lp_cycle_rows': round(lp_cyc, 6)})
            continue
        out.append({'id': pid, 'vertices': n, 'edges': E, 'ex': ex, 'ex_witness': witness, 'lp': round(lp, 6),
                    'lp_cycle_rows': round(lp_cyc, 6), 'cycles': pattern_cycles(E)})
    st['kept'] = len(out)
    if stats is not None:
        stats.update(st)
    return out


def proof_certificate(pattern, earlier, *, max_denominator=60):
    """An integer rounding certificate for Σ ≤ ex(F) from F's LP dual (untrusted; rationalised and
    checked exactly here; Lean checks the proof built from it), or None. As cuts_v2.proof_certificate,
    with 4-cycle rows (right side 3)."""
    from fractions import Fraction
    from math import lcm
    n, E = pattern['vertices'], [tuple(e) for e in pattern['edges']]
    rows = _rows(n, E, earlier)
    _, marg = _lp(n, E, rows)
    y = [Fraction(float(v)).limit_denominator(max_denominator) for v in marg]
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

SOURCE = f'''import {RP.C4_MODULE}

namespace P4

/-- 0/1 adjacency of an edge set, either orientation (B20_R46, {ORIGIN}). -/
def adj (S : GT.Edges) (u v : ℕ) : ℕ := if (u, v) ∈ S ∨ (v, u) ∈ S then 1 else 0

end P4
'''
SAMPLE_VERTICES = 7


def adj_model(S, u, v):
    return 1 if (u, v) in S or (v, u) in S else 0


def _sampler(names):
    def sample(rng):
        V = range(SAMPLE_VERTICES)
        S = frozenset((u, v) for u in V for v in V if u < v and rng.random() < 0.45)
        if rng.random() < 0.5:                        # thin to C4-free half the time, so hypotheses hold often
            keep = []
            for e in sorted(S, key=lambda _: rng.random()):
                if c4free(keep + [e]):
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


def _hyp(name, lean, model):
    return {'name': name, 'hyp': True, 'lean': lean, 'model': model}


def _conj(cid, names, concl, model, role, subject, *, c4=True, distinct=()):
    binders = [{'name': 'S', 'type': 'GT.Edges'}]
    if c4:
        binders.append(_hyp('hS', 'G4.C4Free S', lambda v: c4free(v['S'])))
    binders += [{'name': n, 'type': 'ℕ'} for n in names]
    for a, b in distinct:
        binders.append(_hyp(f'h_{a}_{b}', f'{a} ≠ {b}', lambda v, a=a, b=b: v[a] != v[b]))
    return {'id': cid, 'binders': binders, 'concl': concl, 'model': model, 'sampler': _sampler(names),
            'origin': ORIGIN, 'role': role, 'subject': subject, 'lean_value': _lean_value}


def pattern_sum(p, names='v'):
    return ' + '.join(f'P4.adj S {names}{u} {names}{v}' for u, v in p['edges'])


def conjectures(patterns):
    out = [_conj('p4_adj_le_one', ['u', 'v'], 'P4.adj S u v ≤ 1', lambda v: adj_model(v['S'], v['u'], v['v']) <= 1,
                 'adj', 'adj', c4=False),
           _conj('p4_adj_comm', ['u', 'v'], 'P4.adj S u v = P4.adj S v u',
                 lambda v: adj_model(v['S'], v['u'], v['v']) == adj_model(v['S'], v['v'], v['u']), 'comm', 'comm',
                 c4=False),
           _conj('p4_bridge', ['a', 'b', 'c', 'd'], 'P4.adj S a b + P4.adj S b c + P4.adj S c d + P4.adj S d a ≤ 3',
                 lambda v: sum(adj_model(v['S'], x, y) for x, y in ((v['a'], v['b']), (v['b'], v['c']),
                                                                       (v['c'], v['d']), (v['d'], v['a']))) <= 3,
                 'bridge', 'bridge', distinct=(('a', 'c'), ('b', 'd')))]
    for p in patterns:
        names = [f'v{i}' for i in range(p['vertices'])]
        out.append(_conj(f'p4_{p["id"]}', names, f'{pattern_sum(p)} ≤ {p["ex"]}',
                         lambda v, p=p: sum(adj_model(v['S'], v[f'v{a}'], v[f'v{b}']) for a, b in p['edges']) <= p['ex'],
                         'pattern', p['id'], distinct=tuple(itertools.combinations(names, 2))))
    return out


def _ne(x, y):
    """A proof term of v_x ≠ v_y from the pattern's pairwise hypotheses h_vi_vj (i < j)."""
    return f'h_v{x}_v{y}' if x < y else f'(Ne.symm h_v{y}_v{x})'


BRIDGE_TACTIC = '\n'.join([
    'intro S hS a b c d h_a_c h_b_d',
    'unfold P4.adj',
    'split_ifs with h1 h2 h3 h4 <;> try omega',
    'exfalso',
    'have m : ∀ x y : ℕ, ((x, y) ∈ S ∨ (y, x) ∈ S) → x ∈ G4.verts S := by',
    '  intro x y h',
    '  unfold G4.verts',
    '  rcases h with h | h',
    '  · exact Finset.mem_union_left _ (Finset.mem_image_of_mem Prod.fst h)',
    '  · exact Finset.mem_union_right _ (Finset.mem_image_of_mem Prod.snd h)',
    'exact hS a (m a b h1) b (m b c h2) c (m c d h3) d (m d a h4) h_a_c h_b_d ⟨h1, h2, h3, h4⟩'])


def recipes(patterns):
    """Builder-written recipes (named in every receipt): adj and comm as in generator v2, the C4 bridge, and a
    pattern bound from its integer rounding certificate (scaled facts summed, then omega)."""
    by_id = {p['id']: p for p in patterns}

    def extra(conj, library):
        role = conj.get('role')
        if role == 'adj':
            return [('adj-split', 'intro S u v\nunfold P4.adj\nsplit <;> omega'),
                    ('adj-split-ifs', 'intro S u v\nunfold P4.adj\nsplit_ifs <;> omega')]
        if role == 'comm':
            return [('comm-or-swap', 'intro S u v\nunfold P4.adj\nsimp only [or_comm]'),
                    ('comm-split', 'intro S u v\nunfold P4.adj\nsplit_ifs <;> first | rfl | (exfalso; tauto)')]
        if role == 'bridge':
            return [('c4-bridge-verts', BRIDGE_TACTIC),
                    ('c4-bridge-verts-simp', BRIDGE_TACTIC.replace('unfold G4.verts', 'simp only [G4.verts]'))]
        if role != 'pattern':
            return []
        p = by_id.get(conj['subject'])
        lib = {entry['statement']: entry['const'] for entry in library}
        if p is None or any(k not in lib for k in ('p4_bridge', 'p4_adj_le_one', 'p4_adj_comm')):
            return []
        earlier = [by_id[q] for q in by_id if by_id[q] is not p and patterns.index(by_id[q]) < patterns.index(p)
                   and f'p4_{q}' in lib]
        cert = proof_certificate(p, earlier)
        if cert is None:
            return []
        text = _sum_tactic(p, cert, by_id, lib)
        if len(p['edges']) >= HEAVY_EDGES:              # hoisted before the theorem (search.split_options)
            text = f'set_option maxHeartbeats {HEAVY_HEARTBEATS} in\n' + text
        return [('lp-certificate-sum', text)]
    return extra


def _sum_tactic(p, cert, by_id, lib):
    names = [f'v{i}' for i in range(p['vertices'])]
    hyps = [f'h_{a}_{b}' for a, b in itertools.combinations(names, 2)]
    lines = [f'intro S hS {" ".join(names)} {" ".join(hyps)}']
    facts, comm = [], set()
    for k, (kind, qid, verts, mult, rhs) in enumerate(cert['rows']):
        if kind == 'cycle':
            a, b, c, d = verts
            src = f'{lib["p4_bridge"]} S hS v{a} v{b} v{c} v{d} {_ne(a, c)} {_ne(b, d)}'
            orient = cycle_edges(verts)
            pairs = ((a, b), (b, c), (c, d), (d, a))
        else:
            q = by_id[qid]
            src = (f'{lib[f"p4_{qid}"]} S hS ' + ' '.join(f'v{x}' for x in verts) + ' ' +
                   ' '.join(_ne(verts[i], verts[j]) for i, j in itertools.combinations(range(q['vertices']), 2)))
            pairs = tuple((verts[a], verts[b]) for a, b in q['edges'])
        for x, y in pairs:                              # facts mention adj x y; the goal mentions adj min max
            if x > y:
                comm.add((x, y))
        lines.append(f'have k{k} := Nat.mul_le_mul (Nat.le_refl {mult}) ({src})' if mult != 1 else f'have k{k} := {src}')
        facts.append(f'k{k}')
    for j, ((u, v), mult) in enumerate(sorted(cert['slack'].items())):
        lines.append(f'have e{j} := Nat.mul_le_mul (Nat.le_refl {mult}) ({lib["p4_adj_le_one"]} S v{u} v{v})'
                     if mult != 1 else f'have e{j} := {lib["p4_adj_le_one"]} S v{u} v{v}')
        facts.append(f'e{j}')
    for j, (x, y) in enumerate(sorted(comm)):
        lines.append(f'have s{j} := {lib["p4_adj_comm"]} S v{x} v{y}')
    acc = facts[-1]
    for f in reversed(facts[:-1]):
        acc = f'Nat.add_le_add {f} ({acc})'
    lines.append(f'have key := {acc}')
    lines.append('clear ' + ' '.join(facts))
    lines.append('omega')
    return '\n'.join(lines)


def obligations_ok(state, patterns):
    st = {s['id']: s.get('status') for s in state['statements']}
    base = all(st.get(k) == 'CHECKED' for k in ('p4_adj_le_one', 'p4_adj_comm', 'p4_bridge'))
    return st, [p for p in patterns if base and st.get(f'p4_{p["id"]}') == 'CHECKED']


__all__ = ['generate', 'ex_milp', 'pattern_cycles', 'relaxation_lp', 'proof_certificate', 'conjectures', 'recipes',
           'obligations_ok', 'SOURCE', 'MODULE', 'ORIGIN', 'FAMILY', 'DOMAIN', 'adj_model']
