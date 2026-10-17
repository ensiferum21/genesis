"""Generated valid inequalities for sum-free subsets of integer hosts: the pattern generator, transferred from
triangle-free and C4-free subgraphs to additive combinatorics (B20_R55).

**What is transferred.** The row-invention procedure of generator v2 (B20_R31 v1, B20_R37 v2; transferred to C4 in
B20_R46, `cuts_c4.py`):
  1. enumerate small structures F;
  2. compute ex(F), the largest admissible subset of F;
  3. keep F when the LP of F, under the motif rows and the copies of earlier kept patterns, exceeds ex(F);
  4. prove Σ_{x ∈ F} x ≤ ex(F) in Lean from an integer rounding of F's LP dual.
Here the objects are integers under addition, not edges of a graph. The admissible sets are sum-free sets (no
a + b = c inside the set, a = b allowed), a different theorem family (Schur, Erdős; additive combinatorics). The
registered adaptation changes only the motif-specific parts:
  * the structures F are sets of positive integers P ⊆ {1, …, m} with max P = m and gcd 1 (dilations are the same
    pattern), every element of which lies in a Schur triple of P;
  * the motif rows are Schur triples: x_a + x_b + x_c ≤ 2 for a < b, a + b = c, and x_a + x_{2a} ≤ 1;
  * a copy of a pattern inside a set is an injective map that sends each Schur triple of the pattern to a Schur
    triple (a Freiman-type copy, found by backtracking), not a graph embedding;
  * the Lean domain predicate is `SF.SumFree` (`SFDefs`, new and conservative), and pattern statements quantify over
    values satisfying the pattern's additive relations. No distinctness is needed: every fact used in a proof holds
    for any values.

**Structural caveat (B20_R46-R52 GV6 draft).** Abstractly the problem is the largest subset of a ground set
containing no hyperedge of a 3-uniform hypergraph (the Schur triples), as triangle-freeness is for the triangles of a
host. The objects and the theorem family differ; the abstract structure does not. Whether this target counts as
structurally different for GV6 is the reviewer's decision (B20R46-OPEN-1).

**Kept rule (unchanged from v2).** F's LP under the Schur rows exceeds ex(F), and F's LP under those rows plus every
copy, inside F, of the patterns kept before it also exceeds ex(F).
  * ex(F) comes from HiGHS's exact MILP, an untrusted producer. Its witness is re-checked as sum-free, which proves
    ex(F) ≥ that value.
  * Lean proves the upper side. A wrong (too small) ex would make the Lean statement false.

**Lean (`SFDefs`, new; a trusted definition module for review).**
  * `SF.SumFree S := ∀ a ∈ S, ∀ b ∈ S, a + b ∉ S` for `S : Finset ℕ`;
  * `SF.ind S x := if x ∈ S then 1 else 0`.
The obligations:
  * sf_ind_le_one: SF.ind S x ≤ 1;
  * sf_bridge: SF.SumFree S → a + b = c → ind a + ind b + ind c ≤ 2;
  * sf_bridge_double: SF.SumFree S → a + a = c → ind a + ind c ≤ 1;
  * one bound per pattern: SF.SumFree S → (v_a + v_b = v_c for each Schur triple of P) → Σ_i ind v_i ≤ ex(P).
"""
import itertools
from math import gcd

MAX_ELEMENT = 8
MODULE = 'SFDefs'
ORIGIN = 'generated:pattern-inequalities-sumfree-v1'
FAMILY = 'relaxation'
DOMAIN = 'sumfree_host_v1'
HEAVY_ELEMENTS, HEAVY_HEARTBEATS = 7, 4000000


# ---------------------------------------------------------------- the domain

def schur_triples(values):
    """Schur triples (a, b, c) of a set of integers: a <= b, a + b = c, all three in the set."""
    s = set(values)
    vs = sorted(s)
    return [(a, b, a + b) for i, a in enumerate(vs) for b in vs[i:] if a + b in s]


def sumfree(values):
    s = set(values)
    return not any(a + b in s for a in s for b in s)


def _index_triples(P):
    idx = {x: i for i, x in enumerate(P)}
    return [(idx[a], idx[b], idx[c]) for a, b, c in schur_triples(P)]


def copies(P, host, *, cap=None):
    """Injective maps phi: P -> host (as tuples of images in P's order) that send every Schur triple of P to a Schur
    triple of the host. Images that are the same set are kept once (their rows coincide)."""
    T = _index_triples(P)
    k = len(P)
    S = set(host)
    hs = sorted(S)
    by_last = {}
    for t in T:
        by_last.setdefault(max(t), []).append(t)
    out, seen = [], set()

    def rec(i, phi, used):
        if cap is not None and len(out) >= cap:
            return
        if i == k:
            key = frozenset(phi)
            if key not in seen:
                seen.add(key)
                out.append(tuple(phi))
            return
        forced = None
        for a, b, c in by_last.get(i, ()):
            if c == i and a < i and b < i:
                forced = phi[a] + phi[b]
                break
        cands = [forced] if forced is not None else hs
        for y in cands:
            if y not in S or y in used:
                continue
            phi.append(y)
            if all(phi[a] + phi[b] == phi[c] for a, b, c in by_last.get(i, ())):
                rec(i + 1, phi, used | {y})
            phi.pop()
    rec(0, [], frozenset())
    return out


def ex_milp(P):
    """(ex(P), a maximum sum-free subset of P) by HiGHS MILP, re-checked."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    P = sorted(P)
    T = _index_triples(P)
    if not T:
        return len(P), P
    A = np.zeros((len(T), len(P)))
    ub = []
    for j, (a, b, c) in enumerate(T):
        for i in {a, b, c}:
            A[j, i] = 1
        ub.append(1 if a == b else 2)
    r = milp(-np.ones(len(P)), constraints=LinearConstraint(A, -np.inf, ub), integrality=np.ones(len(P)),
             bounds=Bounds(0, 1))
    if r.status != 0:
        raise RuntimeError(f'MILP failed: {r.message}')
    sub = [P[i] for i in range(len(P)) if r.x[i] > 0.5]
    if not sumfree(sub):
        raise RuntimeError('MILP solution is not sum-free')
    return len(sub), sub


def _rows(P, kept):
    """Rows over the elements of P (indices into sorted P): (kind, pattern id, data, columns, rhs)."""
    P = sorted(P)
    idx = {x: i for i, x in enumerate(P)}
    rows = []
    for a, b, c in schur_triples(P):
        if a == b:
            rows.append(('double', None, [a, c], [idx[a], idx[c]], 1))
        else:
            rows.append(('schur', None, [a, b, c], [idx[a], idx[b], idx[c]], 2))
    for q in kept:
        for phi in copies(q['elements'], P):
            rows.append(('pattern', q['id'], list(phi), [idx[y] for y in phi], q['ex']))
    return rows


def _lp(P, rows):
    import numpy as np
    from scipy.optimize import linprog
    if not rows:
        return float(len(P)), None
    A = np.zeros((len(rows), len(P)))
    for j, r in enumerate(rows):
        A[j, r[3]] = 1
    res = linprog(-np.ones(len(P)), A_ub=A, b_ub=np.array([r[4] for r in rows], float), bounds=(0, 1), method='highs')
    return -res.fun, -res.ineqlin.marginals


def relaxation_lp(P, kept=()):
    return _lp(sorted(P), _rows(P, kept))[0]


def candidates(max_element=MAX_ELEMENT):
    """Every P ⊆ {1..m}, m <= max_element, with max P = m, gcd 1 and at least 3 elements, in a fixed order (by m,
    then size, then lexicographic): the analogue of the graph atlas."""
    for m in range(3, max_element + 1):
        rest = range(1, m)
        for k in range(2, m):
            for sub in itertools.combinations(rest, k):
                P = sub + (m,)
                g = 0
                for x in P:
                    g = gcd(g, x)
                if g == 1:
                    yield P


def generate(max_element=MAX_ELEMENT, *, stats=None):
    """The generated sum-free patterns with elements up to `max_element`, in candidate order."""
    out = []
    st = {'candidates': 0, 'triple_covered': 0, 'implied_by_schur_rows': 0, 'implied_by_earlier_patterns': [],
          'kept': 0}
    for P in candidates(max_element):
        st['candidates'] += 1
        T = schur_triples(P)
        covered = {x for t in T for x in t}
        if not T or any(x not in covered for x in P):
            continue
        st['triple_covered'] += 1
        ex, witness = ex_milp(P)
        lp_schur = relaxation_lp(P)
        if lp_schur <= ex + 1e-6:
            st['implied_by_schur_rows'] += 1
            continue
        lp = relaxation_lp(P, out)
        pid = 'sfpat_' + '_'.join(map(str, P))
        if lp <= ex + 1e-6:
            st['implied_by_earlier_patterns'].append({'id': pid, 'ex': ex, 'lp_schur_rows': round(lp_schur, 6)})
            continue
        out.append({'id': pid, 'elements': list(P), 'ex': ex, 'ex_witness': witness, 'lp': round(lp, 6),
                    'lp_schur_rows': round(lp_schur, 6), 'triples': [list(t) for t in T]})
    st['kept'] = len(out)
    if stats is not None:
        stats.update(st)
    return out


def proof_certificate(pattern, earlier, *, max_denominator=60):
    """An integer rounding certificate for Σ ≤ ex(P) from P's LP dual (untrusted; rationalised and checked exactly
    here; Lean checks the proof built from it), or None. As cuts_c4.proof_certificate, with Schur rows."""
    from fractions import Fraction
    from math import lcm
    P = list(pattern['elements'])
    rows = _rows(P, earlier)
    _, marg = _lp(P, rows)
    y = [Fraction(float(v)).limit_denominator(max_denominator) for v in marg]
    keep = [j for j in range(len(rows)) if y[j] > 0]
    D = 1
    for j in keep:
        D = lcm(D, y[j].denominator)
    m = {j: int(y[j] * D) for j in keep}
    cover = [0] * len(P)
    for j in keep:
        for i in rows[j][3]:
            cover[i] += m[j]
    slack = {i: D - cover[i] for i in range(len(P)) if cover[i] < D}
    K = sum(m[j] * rows[j][4] for j in keep) + sum(slack.values())
    if K // D != pattern['ex']:
        return None
    return {'D': D, 'K': K, 'rows': [(rows[j][0], rows[j][1], rows[j][2], m[j], rows[j][4]) for j in keep],
            'slack': {P[i]: v for i, v in slack.items()}}


# ---------------------------------------------------------------- Lean obligations

SOURCE = f'''import Mathlib.Data.Finset.Powerset

namespace SF

/-- Domain contract (sumfree_host_v1, {ORIGIN}): no a + b (a = b allowed) of S lies in S. -/
def SumFree (S : Finset ℕ) : Prop := ∀ a ∈ S, ∀ b ∈ S, a + b ∉ S

instance (S : Finset ℕ) : Decidable (SumFree S) := by
  unfold SumFree; infer_instance

/-- 0/1 membership indicator. -/
def ind (S : Finset ℕ) (x : ℕ) : ℕ := if x ∈ S then 1 else 0

end SF
'''
SAMPLE_MAX = 24


def ind_model(S, x):
    return 1 if x in S else 0


def _sampler(names, pattern=None):
    def sample(rng):
        U = range(1, SAMPLE_MAX + 1)
        S = [x for x in U if rng.random() < 0.4]
        if rng.random() < 0.6:                        # thin to sum-free most of the time, so hypotheses hold often
            keep = []
            for x in sorted(S, key=lambda _: rng.random()):
                if sumfree(keep + [x]):
                    keep.append(x)
            S = keep
        out = {'S': frozenset(S)}
        if pattern is not None and rng.random() < 0.8:  # values satisfying the relations: a dilation of P
            c = rng.randrange(1, 4)
            out.update({n: c * x for n, x in zip(names, pattern['elements'])})
        else:
            out.update({n: rng.randrange(0, SAMPLE_MAX + 1) for n in names})
        return out
    return sample


def _lean_value(b, x):
    if b['type'] == 'Finset ℕ':
        return '({' + ', '.join(map(str, sorted(x))) + '} : Finset ℕ)' if x else '(∅ : Finset ℕ)'
    return str(x)


def _hyp(name, lean, model):
    return {'name': name, 'hyp': True, 'lean': lean, 'model': model}


def _conj(cid, names, concl, model, role, subject, *, sf=True, relations=(), pattern=None):
    binders = [{'name': 'S', 'type': 'Finset ℕ'}]
    if sf:
        binders.append(_hyp('hS', 'SF.SumFree S', lambda v: sumfree(v['S'])))
    binders += [{'name': n, 'type': 'ℕ'} for n in names]
    for k, (a, b, c) in enumerate(relations):
        binders.append(_hyp(f'r{k}', f'{a} + {b} = {c}', lambda v, a=a, b=b, c=c: v[a] + v[b] == v[c]))
    return {'id': cid, 'binders': binders, 'concl': concl, 'model': model, 'sampler': _sampler(names, pattern),
            'origin': ORIGIN, 'role': role, 'subject': subject, 'lean_value': _lean_value}


def pattern_sum(p, names='v'):
    return ' + '.join(f'SF.ind S {names}{i}' for i in range(len(p['elements'])))


def pattern_relations(p):
    return [(f'v{a}', f'v{b}', f'v{c}') for a, b, c in _index_triples(p['elements'])]


def conjectures(patterns):
    out = [_conj('sf_ind_le_one', ['x'], 'SF.ind S x ≤ 1', lambda v: ind_model(v['S'], v['x']) <= 1, 'ind', 'ind',
                 sf=False),
           _conj('sf_bridge', ['a', 'b', 'c'], 'SF.ind S a + SF.ind S b + SF.ind S c ≤ 2',
                 lambda v: ind_model(v['S'], v['a']) + ind_model(v['S'], v['b']) + ind_model(v['S'], v['c']) <= 2,
                 'bridge', 'bridge', relations=[('a', 'b', 'c')]),
           _conj('sf_bridge_double', ['a', 'c'], 'SF.ind S a + SF.ind S c ≤ 1',
                 lambda v: ind_model(v['S'], v['a']) + ind_model(v['S'], v['c']) <= 1,
                 'bridge_double', 'bridge_double', relations=[('a', 'a', 'c')])]
    for p in patterns:
        names = [f'v{i}' for i in range(len(p['elements']))]
        out.append(_conj(f'sf_{p["id"]}', names, f'{pattern_sum(p)} ≤ {p["ex"]}',
                         lambda v, p=p, names=names: sum(ind_model(v['S'], v[n]) for n in names) <= p['ex'],
                         'pattern', p['id'], relations=pattern_relations(p), pattern=p))
    return out


BRIDGE_TACTIC = '\n'.join([
    'intro S hS a b c r0',
    'unfold SF.ind',
    'split_ifs with h1 h2 h3 <;> try omega',
    'exfalso',
    'exact hS a h1 b h2 (by subst r0; exact h3)'])
BRIDGE_DOUBLE_TACTIC = '\n'.join([
    'intro S hS a c r0',
    'unfold SF.ind',
    'split_ifs with h1 h2 <;> try omega',
    'exfalso',
    'exact hS a h1 a h1 (by subst r0; exact h2)'])


def recipes(patterns):
    """Builder-written recipes (named in every receipt): the indicator bound, the two Schur bridges, and a pattern
    bound from its integer rounding certificate (scaled facts summed, then omega)."""
    by_id = {p['id']: p for p in patterns}

    def extra(conj, library):
        role = conj.get('role')
        if role == 'ind':
            return [('ind-split', 'intro S x\nunfold SF.ind\nsplit <;> omega'),
                    ('ind-split-ifs', 'intro S x\nunfold SF.ind\nsplit_ifs <;> omega')]
        if role == 'bridge':
            return [('sf-bridge-subst', BRIDGE_TACTIC),
                    ('sf-bridge-rw', BRIDGE_TACTIC.replace('(by subst r0; exact h3)', '(by rw [r0]; exact h3)'))]
        if role == 'bridge_double':
            return [('sf-bridge-double-subst', BRIDGE_DOUBLE_TACTIC),
                    ('sf-bridge-double-rw', BRIDGE_DOUBLE_TACTIC.replace('(by subst r0; exact h2)',
                                                                         '(by rw [r0]; exact h2)'))]
        if role != 'pattern':
            return []
        p = by_id.get(conj['subject'])
        lib = {entry['statement']: entry['const'] for entry in library}
        if p is None or any(k not in lib for k in ('sf_bridge', 'sf_bridge_double', 'sf_ind_le_one')):
            return []
        earlier = [by_id[q] for q in by_id if by_id[q] is not p and patterns.index(by_id[q]) < patterns.index(p)
                   and f'sf_{q}' in lib]
        cert = proof_certificate(p, earlier)
        if cert is None:
            return []
        text = _sum_tactic(p, cert, by_id, lib)
        if len(p['elements']) >= HEAVY_ELEMENTS:          # hoisted before the theorem (search.split_options)
            text = f'set_option maxHeartbeats {HEAVY_HEARTBEATS} in\n' + text
        return [('lp-certificate-sum', text)]
    return extra


def _sum_tactic(p, cert, by_id, lib):
    P = list(p['elements'])
    name = {x: f'v{i}' for i, x in enumerate(P)}
    names = [name[x] for x in P]
    rels = [f'r{k}' for k in range(len(pattern_relations(p)))]
    lines = [f'intro S hS {" ".join(names)} {" ".join(rels)}']
    facts = []
    for k, (kind, qid, vals, mult, rhs) in enumerate(cert['rows']):
        if kind == 'schur':
            a, b, c = vals
            src = f'{lib["sf_bridge"]} S hS {name[a]} {name[b]} {name[c]} (by omega)'
        elif kind == 'double':
            a, c = vals
            src = f'{lib["sf_bridge_double"]} S hS {name[a]} {name[c]} (by omega)'
        else:
            q = by_id[qid]
            nrel = len(pattern_relations(q))
            src = (f'{lib[f"sf_{qid}"]} S hS ' + ' '.join(name[y] for y in vals) + ' ' +
                   ' '.join('(by omega)' for _ in range(nrel)))
        lines.append(f'have k{k} := Nat.mul_le_mul (Nat.le_refl {mult}) ({src})' if mult != 1 else f'have k{k} := {src}')
        facts.append(f'k{k}')
    for j, (x, mult) in enumerate(sorted(cert['slack'].items())):
        lines.append(f'have e{j} := Nat.mul_le_mul (Nat.le_refl {mult}) ({lib["sf_ind_le_one"]} S {name[x]})'
                     if mult != 1 else f'have e{j} := {lib["sf_ind_le_one"]} S {name[x]}')
        facts.append(f'e{j}')
    acc = facts[-1]
    for f in reversed(facts[:-1]):
        acc = f'Nat.add_le_add {f} ({acc})'
    lines.append(f'have key := {acc}')
    lines.append('clear ' + ' '.join(facts))
    lines.append('omega')
    return '\n'.join(lines)


def obligations_ok(state, patterns):
    st = {s['id']: s.get('status') for s in state['statements']}
    base = all(st.get(k) == 'CHECKED' for k in ('sf_ind_le_one', 'sf_bridge', 'sf_bridge_double'))
    return st, [p for p in patterns if base and st.get(f'sf_{p["id"]}') == 'CHECKED']


__all__ = ['generate', 'candidates', 'ex_milp', 'schur_triples', 'sumfree', 'copies', 'relaxation_lp',
           'proof_certificate', 'conjectures', 'recipes', 'obligations_ok', 'SOURCE', 'MODULE', 'ORIGIN', 'FAMILY',
           'DOMAIN', 'ind_model']
