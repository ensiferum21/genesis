"""Worlds, counterfactual assumptions and checked transport (roadmap W12).

A world names its assumptions explicitly, along with its ontology (the concepts it uses),
representation, solver, memory (library lemmas it may use) and research policy. Every
assumption is a Lean predicate on a host, with a Python model that implements exactly the
same definition. Interventions add or remove assumptions and produce a new world with
recorded lineage.

What is checked, and how:
  * consistency: CONSISTENT only with a witness host, found by search and checked in Lean
    (`∃ H, A₁ H ∧ … ∧ Aₖ H` by evaluation); INCONSISTENT only with a Lean proof of
    `∀ H, A₁ H → … → Aₖ H → False`; otherwise UNKNOWN. Not finding a finite model never
    establishes inconsistency, and not finding a countermodel never establishes consistency;
  * implication between worlds: a Lean proof of `∀ H, (assumptions of B) → A` for each
    assumption A of the source world;
  * non-equivalence: a host satisfying one world's assumptions and not the other's,
    checked in Lean (`¬ ∀ H, …`);
  * transport: a claim moves from world A to world B only when every assumption of A is
    proved from B's assumptions and B is not inconsistent. The transported claim keeps
    B's assumptions and names the implication proofs it rests on;
  * claims from an inconsistent world are VACUOUS. They are never transported or used.

A discriminating experiment runs the competing worlds' predictions on real task data
(DEV): which assumptions hold on the hosts, and which world-recommended solver is right.
"""
from itertools import combinations
import random

from ..formal_research import triangle_theory as T

WORLD_MODULE = 'WDDefs'
BIP_N = 6

WORLD_SOURCE = f'''import {T.DEFS_MODULE}

namespace WD

/-- Assumption: every pair lies inside {{0, …, n-1}} and the host is 2-colourable there. -/
def Bipartite (n : ℕ) (H : GT.Edges) : Prop :=
  ∃ A ∈ (Finset.range n).powerset, ∀ e ∈ H, (e.1 ∈ A ↔ e.2 ∉ A)

instance (n : ℕ) (H : GT.Edges) : Decidable (Bipartite n H) := by
  unfold Bipartite; infer_instance

/-- Degree of v in H. -/
def deg (v : ℕ) (H : GT.Edges) : ℕ := (H.filter fun e => e.1 = v ∨ e.2 = v).card

/-- Assumption: no vertex of an edge has degree above d. -/
def MaxDegLe (d : ℕ) (H : GT.Edges) : Prop := ∀ e ∈ H, deg e.1 H ≤ d ∧ deg e.2 H ≤ d

instance (d : ℕ) (H : GT.Edges) : Decidable (MaxDegLe d H) := by
  unfold MaxDegLe; infer_instance

/-- Assumption: the host contains a triangle. -/
def HasTriangle (H : GT.Edges) : Prop := ¬ GT.TriangleFree H

instance (H : GT.Edges) : Decidable (HasTriangle H) := by
  unfold HasTriangle; infer_instance

end WD
'''


def bipartite(H, n=BIP_N):
    """Same meaning as WD.Bipartite: every endpoint below n and some A ⊆ {0..n-1} that every
    pair crosses. Decided by 2-colouring each component (a loop is never crossed)."""
    if any(not (0 <= u < n and 0 <= v < n) for u, v in H):
        return False
    adj = {}
    for u, v in H:
        adj.setdefault(u, set()).add(v); adj.setdefault(v, set()).add(u)
    colour = {}
    for s in adj:
        if s in colour:
            continue
        colour[s], stack = 0, [s]
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if y not in colour:
                    colour[y] = 1 - colour[x]; stack.append(y)
                elif colour[y] == colour[x]:
                    return False
    return True


def deg(v, H):
    return sum(1 for a, b in H if a == v or b == v)


def max_deg_le(H, d):
    return all(deg(u, H) <= d and deg(v, H) <= d for u, v in H)


ASSUMPTIONS = {
    'triangle_free': {'lean': 'GT.TriangleFree H', 'model': T.tf},
    'bipartite': {'lean': f'WD.Bipartite {BIP_N} H', 'model': bipartite},
    'has_triangle': {'lean': 'WD.HasTriangle H', 'model': lambda H: not T.tf(H)},
    'max_deg_1': {'lean': 'WD.MaxDegLe 1 H', 'model': lambda H: max_deg_le(H, 1)},
}


def world(wid, assumptions, *, solver, representation=None, ontology=(), memory=(), policy=None, parent=None,
          intervention=None):
    unknown = sorted(set(assumptions) - set(ASSUMPTIONS))
    if unknown:
        raise ValueError(f'unknown assumptions {unknown}')
    return {'id': wid, 'assumptions': sorted(assumptions), 'ontology': sorted(ontology) or ['GT.Edges', 'GT.TriangleFree'],
            'representation': representation, 'solver': solver, 'memory': list(memory),
            'research_policy': policy or {'proof_search': 'recipes', 'screening_samples': 3000},
            'lineage': {'parent': parent, 'intervention': intervention}}


def intervene(w, wid, *, add=(), remove=(), solver=None):
    return world(wid, (set(w['assumptions']) | set(add)) - set(remove), solver=solver or w['solver'],
                 representation=w['representation'], ontology=w['ontology'], memory=w['memory'],
                 policy=w['research_policy'], parent=w['id'],
                 intervention={'add': sorted(add), 'remove': sorted(remove)})


# ---------------------------------------------------------------- obligations as conjectures

def _hosts(rng, vertices=BIP_N, simple=True):
    pairs = [(u, v) for u in range(vertices) for v in range(vertices) if not simple or u < v]
    p = rng.choice((0.15, 0.3, 0.5))
    return frozenset(e for e in pairs if rng.random() < p)


def _lit(H):
    return '(∅ : GT.Edges)' if not H else '({' + ', '.join(f'({u}, {v})' for u, v in sorted(H)) + '} : GT.Edges)'


def lean_value(b, x):
    return _lit(x)


def _hyps(assumptions):
    return [{'name': f'h{i + 1}', 'hyp': True, 'lean': ASSUMPTIONS[a]['lean'],
             'model': (lambda m: lambda v: m(v['H']))(ASSUMPTIONS[a]['model'])} for i, a in enumerate(assumptions)]


def _sampler(rng):
    return {'H': _hosts(rng)}


def implication(premises, conclusion, *, role, subject):
    """∀ H, premises → conclusion (an assumption id), screened on sampled simple hosts."""
    c = {'id': f'imp_{"_".join(premises)}__{conclusion}', 'binders': [{'name': 'H', 'type': 'GT.Edges'}] + _hyps(premises),
         'concl': ASSUMPTIONS[conclusion]['lean'], 'model': (lambda m: lambda v: m(v['H']))(ASSUMPTIONS[conclusion]['model']),
         'sampler': _sampler, 'origin': 'generated:world-obligation', 'role': role, 'subject': subject,
         'lean_value': lean_value}
    return c


def inconsistency(w):
    return {'id': f'incons_{w["id"]}', 'binders': [{'name': 'H', 'type': 'GT.Edges'}] + _hyps(w['assumptions']),
            'concl': 'False', 'model': lambda v: False, 'sampler': _sampler, 'origin': 'generated:world-obligation',
            'role': 'inconsistency', 'subject': w['id'], 'lean_value': lean_value}


def find_model(assumptions, *, tries=20000, seed=0):
    rng = random.Random(seed)
    best = None
    for _ in range(tries):
        H = _hosts(rng)
        if all(ASSUMPTIONS[a]['model'](H) for a in assumptions):
            if best is None or len(H) < len(best):
                best = H
    return best


def consistency_witness(w, H):
    body = ' ∧ '.join(f'({ASSUMPTIONS[a]["lean"]})' for a in w['assumptions']) or 'True'
    return {'id': f'model_{w["id"]}', 'binders': [], 'concl': f'∃ H : GT.Edges, {body}', 'model': None,
            'sampler': None, 'origin': 'generated:world-obligation', 'role': 'consistency', 'subject': w['id'],
            'witness_tactic': f'exact ⟨{_lit(H)}, by decide⟩', 'witness': sorted(H), 'lean_value': lean_value}


def obligations(worlds, transports):
    """Conjectures for the implications that the requested transports need, then for the
    consistency (a witness model) or inconsistency (a proof of False) of every world.
    Implications come first, so an inconsistency proof may use them as library lemmas."""
    out, cons = [], []
    for w in worlds:
        H = find_model(w['assumptions'])
        cons.append(consistency_witness(w, H) if H is not None else inconsistency(w))
    seen = set()
    for src, dst in transports:
        ws, wd = next(w for w in worlds if w['id'] == src), next(w for w in worlds if w['id'] == dst)
        for a in ws['assumptions']:
            key = (tuple(wd['assumptions']), a)
            if a in wd['assumptions'] or key in seen:
                continue
            seen.add(key)
            out.append(implication(wd['assumptions'], a, role='implication', subject=f'{dst}=>{src}:{a}'))
    return out + cons


def extra_recipes(conj, library):
    if conj.get('witness_tactic'):
        return [('witness-evaluation', conj['witness_tactic'])]
    names = ' '.join(b['name'] for b in conj['binders'])
    out = []
    if conj.get('role') == 'implication' and conj['concl'] == 'GT.TriangleFree H':
        # a 2-colouring witness rules out the triangle pattern
        out.append(('witness-destructure-tauto', '\n'.join([
            f'intro {names}', 'obtain ⟨A, _, hA⟩ := h1', 'unfold GT.TriangleFree',
            "rintro ⟨a, b⟩ he ⟨b', d⟩ hf ⟨a', d'⟩ hg ⟨e1, e2, e3⟩", 'simp only at e1 e2 e3', 'subst e1 e2 e3',
            'have x := hA _ he', 'have y := hA _ hf', 'have z := hA _ hg', 'simp only at x y z', 'tauto'])))
    if conj.get('role') == 'inconsistency':
        lemmas = ', '.join(l['const'] for l in library) or 'trivial'
        out.append(('library-contradiction', f'intro {names}\nunfold WD.HasTriangle at *\n'
                                              f'exact absurd (by solve_by_elim [{lemmas}]) ‹¬ _›'))
        out.append(('library-solve', f'intro {names}\nunfold WD.HasTriangle at *\nsolve_by_elim [{lemmas}]'))
    return out


# ---------------------------------------------------------------- reading the checked results

def judge(worlds, transports, claims, statements):
    """Turn checked statements into world statuses, equivalences and transport decisions."""
    st = {s['id']: s for s in statements}
    status = {}
    for w in worlds:
        if st.get(f'model_{w["id"]}', {}).get('status') == 'CHECKED':
            status[w['id']] = {'status': 'CONSISTENT', 'evidence': st[f'model_{w["id"]}']['proof_const']}
        elif st.get(f'incons_{w["id"]}', {}).get('status') == 'CHECKED':
            status[w['id']] = {'status': 'INCONSISTENT', 'evidence': st[f'incons_{w["id"]}']['proof_const']}
        else:
            status[w['id']] = {'status': 'UNKNOWN',
                               'note': 'no checked model and no checked proof of False; neither is assumed'}
    decisions = []
    for src, dst in transports:
        ws, wd = next(w for w in worlds if w['id'] == src), next(w for w in worlds if w['id'] == dst)
        needed = [a for a in ws['assumptions'] if a not in wd['assumptions']]
        proofs, missing = [], []
        for a in needed:
            s = st.get(f'imp_{"_".join(wd["assumptions"])}__{a}')
            if s and s.get('status') == 'CHECKED':
                proofs.append(s['proof_const'])
            else:
                missing.append({'assumption': a, 'status': s.get('status') if s else 'NOT_STATED'})
        if status[dst]['status'] == 'INCONSISTENT':
            verdict = 'REFUSED_INCONSISTENT_TARGET'
        elif status[src]['status'] == 'INCONSISTENT':
            verdict = 'REFUSED_VACUOUS_SOURCE'
        elif missing:
            verdict = 'REFUSED_UNPROVED_CONDITIONS'
        else:
            verdict = 'TRANSPORTED'
        decisions.append({'from': src, 'to': dst, 'claims': [c['id'] for c in claims if c['world'] == src],
                          'verdict': verdict, 'conditions': needed, 'implication_proofs': proofs, 'missing': missing,
                          'transported_assumptions': wd['assumptions'] if verdict == 'TRANSPORTED' else None})
    # CRPD-1 (B20_R2): the soundness mode each decision licenses, derived from the same checks.
    from .soundness import transport_mode
    for d in decisions:
        d['soundness'] = transport_mode(d, status)
    claim_status = []
    for c in claims:
        s = status[c['world']]['status']
        claim_status.append({**c, 'status': 'VACUOUS' if s == 'INCONSISTENT' else
                             ('WORLD_RELATIVE' if s == 'CONSISTENT' else 'WORLD_STATUS_UNKNOWN'),
                             'assumptions': next(w for w in worlds if w['id'] == c['world'])['assumptions']})
    return {'worlds': status, 'transports': decisions, 'claims': claim_status}


def equivalence(a_to_b, b_to_a):
    """EQUIVALENT only with both implications CHECKED; DISTINCT when either is DISPROVED."""
    if 'DISPROVED' in (a_to_b, b_to_a):
        return 'DISTINCT'
    if a_to_b == b_to_a == 'CHECKED':
        return 'EQUIVALENT'
    return 'UNKNOWN'


__all__ = ['world', 'intervene', 'obligations', 'judge', 'equivalence', 'implication', 'extra_recipes',
           'ASSUMPTIONS', 'WORLD_SOURCE', 'bipartite', 'max_deg_le']
