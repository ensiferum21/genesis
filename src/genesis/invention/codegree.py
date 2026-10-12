"""Codegree as an exact abstraction of C4-freeness (CRPD-2, B20_R2).

For an edge set S (the repository's ``GT.Edges``: a finite set of ordered pairs, adjacency
symmetric by definition) and vertices u, v of S, the *common neighbours* are the vertices
of S adjacent to both, and the codegree is their number. The statement

    ∀ S, G4.C4Free S ↔ CD.CodegLeOne S

(no closed walk a-b-c-d-a with a ≠ c and b ≠ d, iff every pair of distinct vertices has
at most one common neighbour) holds for arbitrary edge sets, loops and both orientations
included, with exactly the repository's C4 definition: two distinct common neighbours of
u ≠ v give such a walk, and such a walk gives a and c two distinct common neighbours.

This is a KNOWN elementary fact. The statement and its proof recipe are builder-written
(B17-OPEN-1 applies): this is a checked exact abstraction for later use, not a discovery.
Once Lean-checked it is Genesis's first EQ-mode abstraction (invention/soundness.py): it
licenses lifting, refuting and pruning for the C4 feasibility predicate.

Not included: the pair-count bound sum_v C(d(v), 2) <= C(n, 2) and the derived
4m^2 - 2nm <= n^2 (n - 1) (``graphs.universal_upper``, recorded as an unchecked THEOREM
bound). They need Finset big operators, which lie outside the pinned workspace's import
closure (``Mathlib.Data.Finset.Powerset``); adding them is a workspace pin revision that
needs a reviewed decision.
"""
from ..formal_research import triangle_theory as T
from . import representations as R

CD_MODULE = 'CDDefs'
CD_SOURCE = f'''import {T.DEFS_MODULE}
import {R.C4_MODULE}

namespace CD

/-- Common neighbours of u and v in S: the vertices of S adjacent to both. -/
def commonNbrs (S : GT.Edges) (u v : ℕ) : Finset ℕ :=
  (G4.verts S).filter (fun w => G4.adj S u w ∧ G4.adj S v w)

/-- Every pair of distinct vertices of S has at most one common neighbour (codegree ≤ 1). -/
def CodegLeOne (S : GT.Edges) : Prop :=
  ∀ u ∈ G4.verts S, ∀ v ∈ G4.verts S, u ≠ v → (commonNbrs S u v).card ≤ 1

end CD
'''

RECIPE = '\n'.join([
    'intro S',
    'have symm : ∀ x y, G4.adj S x y → G4.adj S y x := by',
    '  intro x y h',
    '  unfold G4.adj at *',
    '  exact h.symm',
    'unfold G4.C4Free CD.CodegLeOne',
    'constructor',
    '· intro h u hu v hv huv',
    '  by_contra hc',
    '  have hc2 : 1 < (CD.commonNbrs S u v).card := by omega',
    '  obtain ⟨b, hb, d, hd, hbd⟩ := Finset.one_lt_card.mp hc2',
    '  simp only [CD.commonNbrs, Finset.mem_filter] at hb hd',
    '  exact h u hu b hb.1 v hv d hd.1 huv hbd ⟨hb.2.1, symm _ _ hb.2.2, hd.2.2, symm _ _ hd.2.1⟩',
    '· intro h a ha b hb c hc d hd hac hbd habcd',
    '  obtain ⟨h1, h2, h3, h4⟩ := habcd',
    '  have hcard : 1 < (CD.commonNbrs S a c).card := by',
    '    apply Finset.one_lt_card.mpr',
    '    refine ⟨b, ?_, d, ?_, hbd⟩',
    '    · simp only [CD.commonNbrs, Finset.mem_filter]',
    '      exact ⟨hb, h1, symm _ _ h2⟩',
    '    · simp only [CD.commonNbrs, Finset.mem_filter]',
    '      exact ⟨hd, symm _ _ h4, h3⟩',
    '  have := h a ha c hc hac',
    '  omega',
])


def codeg_le_one(S):
    """Python model of CD.CodegLeOne, for screening (same definitions as the Lean module)."""
    S = set(map(tuple, S))
    adj = lambda u, v: (u, v) in S or (v, u) in S
    V = sorted({u for u, _ in S} | {v for _, v in S})
    return all(sum(adj(u, w) and adj(v, w) for w in V) <= 1 for u in V for v in V if u != v)


def conjecture():
    host = {'name': 'S', 'type': 'GT.Edges'}
    return {'id': 'codeg_iff_c4free', 'binders': [host], 'concl': 'G4.C4Free S ↔ CD.CodegLeOne S',
            'model': lambda v: R.c4free(v['S']) == codeg_le_one(v['S']),
            'sampler': lambda rng: {'S': R._sample_edges(rng, p=0.4, vertices=5)},
            'origin': 'builder-written (CRPD-2): known equivalence, stated over the repository definitions',
            'role': 'equivalence', 'subject': 'codegree@c4_host_v2', 'lean_value': R.lean_value}


def recipes(conj, library):
    return [('codegree-two-witnesses (builder-written)', RECIPE)] if conj['id'] == 'codeg_iff_c4free' else []


def base_modules():
    return [{'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True},
            {'name': R.C4_MODULE, 'source': R.C4_SOURCE, 'trusted': True},
            {'name': CD_MODULE, 'source': CD_SOURCE, 'trusted': True}]


def soundness_record(package):
    """The EQ-mode record of the abstraction, from the package's checked statement only."""
    from .soundness import establish
    st = next((s for s in package['statements'] if s['id'] == 'codeg_iff_c4free'), {})
    status = st.get('status')
    return establish('codegree <= 1 for C4-freeness', requested='EQ', forward=status, backward=status,
                     evidence=[st['proof_const']] if st.get('proof_const') else [], scope='c4_host_v2 (any GT.Edges)')


__all__ = ['CD_MODULE', 'CD_SOURCE', 'RECIPE', 'codeg_le_one', 'conjecture', 'recipes', 'base_modules',
           'soundness_record']
