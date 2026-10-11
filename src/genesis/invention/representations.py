"""Representation invention (roadmap W10).

A typed proposal grammar over host graphs. A representation is an *encoder space* (a
vertex map `c : ℕ → Fin k`) and a *decoder* that turns a host and an encoding into an
edge set. Decoders come from a small typed vocabulary: cross-class edges, within-class
edges, edges pointing up the class order, and edges between adjacent classes. Every
proposal is type-checked and bounded before anything runs: k ≤ 3, an encoder space of
k^n points, decoding in O(|H|).

For each proposal Genesis records the semantics (a Lean definition generated from the
proposal, and a Python executable that implements it), the domain, the information it
keeps and loses, its obligations, decoder, cost, failure conditions, and whether it is a
conservative definition or a stronger assumption. Every proposal here is a conservative
definition: no axiom is added. The obligations are Lean statements:

  * image:     decode c H ⊆ H (the feasibility mapping);
  * soundness: decode c H is free of the domain's forbidden motif, for every host and
               every encoding (the reduction from encodings to valid witnesses);
  * dominance: one sound decoder's output is contained in another's, for the same
               encoding (so the first loses information relative to the second);
  * loss:      a motif-free graph that no 2-class encoding decodes exactly. This is a
               checked witness that the representation is incomplete.

Soundness that the screen refutes is recorded as DISPROVED, with a Lean-checked
counterexample. That is the expected outcome for every decoder on the C4 domain, an
honest negative result for this grammar.

The method built on a sound representation, `represent_and_repair`, is generic: local
search over encodings to maximise the decoded size, then greedy completion under the
domain checker. Which representation it uses is decided by the grammar and the checked
soundness theorem, and the choice is ranked on a DEV selection panel. The domain checker
validates every witness it returns.
"""
from itertools import combinations
import random
import time

from ..formal_research import triangle_theory as T

DEFS_MODULE = T.DEFS_MODULE
C4_MODULE = 'G4Defs'
REP_MODULE = 'RPDefs'
MAX_K = 3

C4_SOURCE = f'''import {DEFS_MODULE}

namespace G4

/-- Domain contract (c4_host_v2): u and v are joined in S, in either orientation. -/
def adj (S : GT.Edges) (u v : ℕ) : Prop := (u, v) ∈ S ∨ (v, u) ∈ S

instance (S : GT.Edges) (u v : ℕ) : Decidable (adj S u v) := by
  unfold adj; infer_instance

def verts (S : GT.Edges) : Finset ℕ := S.image Prod.fst ∪ S.image Prod.snd

/-- No 4-cycle a-b-c-d-a with a ≠ c and b ≠ d. -/
def C4Free (S : GT.Edges) : Prop :=
  ∀ a ∈ verts S, ∀ b ∈ verts S, ∀ c ∈ verts S, ∀ d ∈ verts S,
    a ≠ c → b ≠ d → ¬ (adj S a b ∧ adj S b c ∧ adj S c d ∧ adj S d a)

instance (S : GT.Edges) : Decidable (C4Free S) := by
  unfold C4Free; infer_instance

end G4
'''


def c4free(S):
    S = set(map(tuple, S))
    adj = lambda u, v: (u, v) in S or (v, u) in S
    V = sorted({u for u, _ in S} | {v for _, v in S})
    return not any(a != c and b != d and adj(a, b) and adj(b, c) and adj(c, d) and adj(d, a)
                   for a in V for b in V for c in V for d in V)


DOMAINS = {'triangle_free_host_v1': {'motif': 'GT.TriangleFree', 'model': T.tf},
           'c4_host_v2': {'motif': 'G4.C4Free', 'model': c4free}}

# decoder vocabulary: name -> (Lean predicate on an edge e under c, python predicate, retained, lost)
DECODERS = {
    'cross': ('c e.1 ≠ c e.2', lambda cu, cv: cu != cv,
              'edges whose endpoints lie in different classes', 'every edge inside a class'),
    'inside': ('c e.1 = c e.2', lambda cu, cv: cu == cv,
               'edges inside a class', 'every edge between classes'),
    'ordered': ('c e.1 < c e.2', lambda cu, cv: cu < cv,
                'edges from a lower class to a higher class (by the host orientation u < v)',
                'edges inside a class and edges pointing down the class order'),
    'adjacent': ('(c e.1).val + 1 = (c e.2).val ∨ (c e.2).val + 1 = (c e.1).val',
                 lambda cu, cv: abs(cu - cv) == 1,
                 'edges between consecutive classes', 'edges inside a class and edges skipping a class'),
}


class ProposalError(ValueError):
    pass


def typecheck(proposal):
    """A proposal is {'decoder': name, 'k': int}. Returns its typed record or raises."""
    dec, k = proposal.get('decoder'), proposal.get('k')
    if dec not in DECODERS:
        raise ProposalError(f'unknown decoder {dec!r}')
    if type(k) is not int or not 2 <= k <= MAX_K:
        raise ProposalError(f'class count k must be an integer in [2, {MAX_K}]')
    if set(proposal) - {'decoder', 'k'}:
        raise ProposalError('unknown proposal fields')
    lean_pred, py, retained, lost = DECODERS[dec]
    name = f'{dec}_{k}'
    return {'id': name, 'decoder': dec, 'k': k, 'lean_name': f'RP.{name}',
            'encoder': {'type': f'ℕ → Fin {k}', 'space': f'{k}^n encodings of an n-vertex host'},
            'decoder_lean': f'fun e => {lean_pred}', 'semantics': f'RP.{name} c H = H.filter (fun e => {lean_pred})',
            'retained': retained, 'lost': lost,
            'cost': {'decode': 'O(|H|)', 'encoder_space': f'{k}^n', 'bound': f'k ≤ {MAX_K}'},
            'failure_conditions': ['exhaustive search over encodings is infeasible beyond small n; '
                                   'local search gives no optimality guarantee',
                                   'a decoder that is unsound for a domain must not be used there'],
            'kind': 'conservative-definition', '_py': py}


def proposals():
    return [typecheck({'decoder': d, 'k': k}) for d in DECODERS for k in range(2, MAX_K + 1)]


def decode(rep, c, H):
    return frozenset(e for e in H if rep['_py'](c.get(e[0], 0), c.get(e[1], 0)))


def rep_source(reps):
    lines = [f'import {DEFS_MODULE}', '', 'namespace RP', '']
    for r in reps:
        lines.append(f'/-- Generated representation `{r["id"]}`: {r["retained"]}. -/')
        lines.append(f'def {r["id"]} (c : ℕ → Fin {r["k"]}) (H : GT.Edges) : GT.Edges := H.filter {r["decoder_lean"]}')
        lines.append('')
    lines += ['end RP', '']
    return '\n'.join(lines)


# ---------------------------------------------------------------- conjectures (for formal_research.loop)

PAIRS3 = [(u, v) for u in range(4) for v in range(4)]


def _sample_edges(rng, p=0.35, vertices=4, simple_only=False):
    pairs = [(u, v) for u in range(vertices) for v in range(vertices) if not simple_only or u < v]
    return frozenset(e for e in pairs if rng.random() < p)


def lean_value(b, x):
    t = b['type']
    if t == 'GT.Edges':
        return '(∅ : GT.Edges)' if not x else '({' + ', '.join(f'({u}, {v})' for u, v in sorted(x)) + '} : GT.Edges)'
    if t.startswith('ℕ → Fin '):
        k = int(t.split()[-1])
        n = max(x) + 1 if x else 1
        table = ', '.join(str(x.get(v, 0)) for v in range(n))
        return f'(fun v => ([{table}] : List (Fin {k})).getD v 0)'
    raise ValueError(f'no Lean printer for {t}')


def _conj(cid, binders, concl, model, sampler, origin, role, subject):
    return {'id': cid, 'binders': binders, 'concl': concl, 'model': model, 'sampler': sampler, 'origin': origin,
            'role': role, 'subject': subject, 'lean_value': lean_value}


def conjectures(reps):
    out = []
    for r in reps:
        k = r['k']
        enc = {'name': 'c', 'type': f'ℕ → Fin {k}'}
        host = {'name': 'H', 'type': 'GT.Edges'}

        def sampler(rng, k=k):
            return {'c': {v: rng.randrange(k) for v in range(4)}, 'H': _sample_edges(rng)}
        out.append(_conj(f'{r["id"]}_image', [enc, host], f'RP.{r["id"]} c H ⊆ H',
                         lambda v, r=r: decode(r, v['c'], v['H']) <= v['H'], sampler,
                         'generated:representation-grammar', 'image', r['id']))
        for dom, spec in DOMAINS.items():
            short = 'tf' if dom.startswith('triangle') else 'c4'
            out.append(_conj(f'{r["id"]}_sound_{short}', [enc, host], f'{spec["motif"]} (RP.{r["id"]} c H)',
                             lambda v, r=r, m=spec['model']: m(decode(r, v['c'], v['H'])), sampler,
                             'generated:representation-grammar', 'soundness', f'{r["id"]}@{dom}'))
    return out


def follow_up_conjectures(reps, sound):
    """After soundness is settled: dominance between sound decoders of equal k, and a loss
    witness for each sound 2-class decoder (found by exhaustive Python search)."""
    out = []
    by_k = {}
    for r in reps:
        if (r['id'], 'tf') in sound:
            by_k.setdefault(r['k'], []).append(r)
    for k, rs in by_k.items():
        for a in rs:
            for b in rs:
                if a is b:
                    continue
                enc = {'name': 'c', 'type': f'ℕ → Fin {k}'}
                host = {'name': 'H', 'type': 'GT.Edges'}
                out.append(_conj(f'{a["id"]}_within_{b["id"]}', [enc, host], f'RP.{a["id"]} c H ⊆ RP.{b["id"]} c H',
                                 lambda v, a=a, b=b: decode(a, v['c'], v['H']) <= decode(b, v['c'], v['H']),
                                 lambda rng, k=k: {'c': {x: rng.randrange(k) for x in range(4)},
                                                   'H': _sample_edges(rng)},
                                 'generated:representation-grammar', 'dominance', f'{a["id"]}<={b["id"]}'))
    for r in by_k.get(2, []):
        w = loss_witness(r)
        if w is None:
            continue
        n, S = w
        lit = '{' + ', '.join(f'({u}, {v})' for u, v in S) + '}'
        concl = (f'∃ S : GT.Edges, GT.TriangleFree S ∧ ∀ A ∈ (Finset.range {n}).powerset, '
                 f'RP.{r["id"]} (fun v => if v ∈ A then 1 else 0) S ≠ S')
        c = _conj(f'{r["id"]}_loses_tf', [], concl, None, None, 'generated:representation-grammar', 'loss',
                  r['id'])
        c['witness_tactic'] = f'exact ⟨{lit}, by decide, by decide⟩'
        out.append(c)
    return out


def loss_witness(rep, max_n=5):
    """Smallest simple triangle-free graph that no 2-class encoding decodes exactly."""
    for n in range(3, max_n + 1):
        pairs = list(combinations(range(n), 2))
        for m in range(1, len(pairs) + 1):
            for S in combinations(pairs, m):
                S = frozenset(S)
                if not T.tf(S):
                    continue
                if all(decode(rep, {v: (1 if v in A else 0) for v in range(n)}, S) != S
                       for r_ in range(n + 1) for A in map(set, combinations(range(n), r_))):
                    return n, sorted(S)
    return None


def extra_recipes(conj, library):
    """Builder-written recipes for representation obligations (named in every receipt)."""
    if conj.get('witness_tactic'):
        return [('witness-evaluation', conj['witness_tactic'])]
    role, sub = conj.get('role'), conj.get('subject', '')
    rep = sub.split('@')[0]
    out = []
    if role == 'soundness' and sub.endswith('@triangle_free_host_v1'):
        out.append(('destructure-subst-omega', '\n'.join([
            'intro c H', f'unfold GT.TriangleFree RP.{rep}',
            "rintro ⟨a, b⟩ he ⟨b', d⟩ hf ⟨a', d'⟩ hg ⟨h1, h2, h3⟩",
            'simp only [Finset.mem_filter] at he hf hg', 'simp only at h1 h2 h3', 'subst h1 h2 h3', 'omega'])))
    if role == 'image':
        out.append(('filter-subset', f'intro c H\nsimp_all [RP.{rep}]'))
    if role == 'dominance':
        a, b = sub.split('<=')
        out.append(('filter-pointwise', '\n'.join([
            'intro c H', f'unfold RP.{a} RP.{b}', 'intro x hx', 'simp only [Finset.mem_filter] at hx ⊢',
            'exact ⟨hx.1, by have := hx.2; omega⟩'])))
    return out


# ---------------------------------------------------------------- the method built on a sound representation

def represent_and_repair(n, edges, rep, motif_ok, *, cpu_seconds, seed=0):
    """Local search over encodings maximising |decode|, then greedy completion that keeps the
    domain predicate. `motif_ok(S, e)` says whether adding e to S keeps S valid."""
    rng = random.Random(seed)
    E = [tuple(e) for e in edges]
    adj = {v: [] for v in range(n)}
    for u, v in E:
        adj[u].append(v); adj[v].append(u)
    k = rep['k']
    best, rounds = None, 0
    end = time.process_time() + cpu_seconds
    while True:
        rounds += 1
        c = {v: rng.randrange(k) for v in range(n)}
        improved = True
        while improved:
            improved = False
            for v in rng.sample(range(n), n):
                cur = sum(rep['_py'](c[v], c[w]) if v < w else rep['_py'](c[w], c[v]) for w in adj[v])
                for alt in range(k):
                    if alt == c[v]:
                        continue
                    new = sum(rep['_py'](alt, c[w]) if v < w else rep['_py'](c[w], alt) for w in adj[v])
                    if new > cur:
                        c[v], cur, improved = alt, new, True
        S = set(decode(rep, c, E))
        rest = [e for e in E if e not in S]
        rng.shuffle(rest)
        for e in rest:
            if motif_ok(S, e):
                S.add(e)
        if best is None or len(S) > len(best[0]):
            best = (S, dict(c))
        if time.process_time() >= end:
            break
    return {'witness': sorted(best[0]), 'value': len(best[0]), 'encoding': best[1], 'rounds': rounds,
            'decoded_before_repair': len(decode(rep, best[1], E))}


def tf_add_ok(S, e):
    u, v = e
    nb = lambda x: {b for a, b in S if a == x} | {a for a, b in S if b == x}
    return not (nb(u) & nb(v))


__all__ = ['proposals', 'typecheck', 'conjectures', 'follow_up_conjectures', 'extra_recipes', 'rep_source',
           'represent_and_repair', 'tf_add_ok', 'c4free', 'C4_SOURCE', 'DOMAINS', 'ProposalError']
