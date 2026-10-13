"""The C4 pair-count bound, Lean-checked (CRPD-2b, B20 continuation).

``graphs.universal_upper`` bounds a C4-free subgraph of a host on n vertices by the largest
m with 4m^2 - 2nm <= n^2 (n - 1). Until now that bound was recorded as an *unchecked*
THEOREM bound (CRPD-2a: it needs Finset big operators, outside the pinned import closure).
The user approved a workspace pin revision on 13 Oct 2026 (CRPD-2b: "Go", time-boxed, revert
with a record on failure); toolchain/FORMAL_WORKSPACE.json now also builds
``Mathlib.Algebra.BigOperators.Group.Finset.Sigma`` and
``Mathlib.Algebra.Order.BigOperators.Ring.Finset``.

Two statements over the repository's own definitions (GT.Edges, G4.adj, G4.C4Free), for an
edge set S whose pairs (u, v) satisfy u < v < n (the host contract: each edge once, u < v,
vertices 0..n-1):

  pair_count_c4       sum over v < n of C(deg v, 2)  <=  C(n, 2)
                      (two common neighbours of a pair would close a 4-cycle, so each pair
                      of vertices is counted at most once)
  c4_quadratic_bound  4 |S|^2  <=  n^2 (n - 1) + 2 n |S|
                      (handshake sum deg = 2|S|, deg^2 = 2 C(deg, 2) + deg, Cauchy-Schwarz)

Both are KNOWN results (Kovari-Sos-Turan / Reiman style counting). Statements and proof
recipes are builder-written (B17-OPEN-1 applies): a checked bound for later use, not a
discovery. Over the integers the second is exactly ``universal_upper``'s inequality
4m^2 - 2nm <= n^2 (n - 1), since every quantity is a natural number and n - 1 is exact for
n >= 1 (both sides are 0 at n = 0).
"""
from pathlib import Path

from ..common import digest
from ..formal_research import triangle_theory as T
from . import representations as R

HOST_HYP = '∀ e ∈ S, e.1 < e.2 ∧ e.2 < n'
DEG = '((Finset.range n).filter (fun w => G4.adj S v w)).card'

PAIR_COUNT_CONCL = f'∑ v ∈ Finset.range n, ({DEG}).choose 2 ≤ n.choose 2'
QUADRATIC_CONCL = '4 * S.card ^ 2 ≤ n ^ 2 * (n - 1) + 2 * n * S.card'

PAIR_COUNT_RECIPE = '\n'.join([
    'intro n S hS hC',
    'unfold G4.C4Free at hC',
    'have hsymm : ∀ u w, G4.adj S u w → G4.adj S w u := by',
    '  intro u w h',
    '  unfold G4.adj at *',
    '  exact h.symm',
    'have hv : ∀ u w, G4.adj S u w → u ∈ G4.verts S := by',
    '  intro u w h',
    '  unfold G4.adj at h',
    '  unfold G4.verts',
    '  rcases h with h | h',
    '  · exact Finset.mem_union_left _ (Finset.mem_image.mpr ⟨(u, w), h, rfl⟩)',
    '  · exact Finset.mem_union_right _ (Finset.mem_image.mpr ⟨(w, u), h, rfl⟩)',
    'have key : ((Finset.range n).sigma (fun v => ((Finset.range n).filter (fun w => G4.adj S v w)).powersetCard 2)).card'
    ' ≤ ((Finset.range n).powersetCard 2).card := by',
    '  apply Finset.card_le_card_of_injOn (fun x => x.2)',
    '  · intro x hx',
    '    rw [Finset.mem_coe, Finset.mem_sigma, Finset.mem_powersetCard] at hx',
    '    rw [Finset.mem_coe, Finset.mem_powersetCard]',
    '    exact ⟨hx.2.1.trans (Finset.filter_subset _ _), hx.2.2⟩',
    '  · intro x hx y hy hxy',
    '    rw [Finset.mem_coe, Finset.mem_sigma, Finset.mem_powersetCard] at hx hy',
    '    dsimp only at hxy',
    '    by_cases hfst : x.1 = y.1',
    '    · exact Sigma.ext hfst (heq_of_eq hxy)',
    '    · exfalso',
    '      obtain ⟨a, b, hab, hP⟩ := Finset.card_eq_two.mp hx.2.2',
    '      have ha : a ∈ x.2 := by rw [hP]; exact Finset.mem_insert_self a {b}',
    '      have hb : b ∈ x.2 := by rw [hP]; exact Finset.mem_insert_of_mem (Finset.mem_singleton_self b)',
    '      have hax := hx.2.1 ha',
    '      have hbx := hx.2.1 hb',
    '      rw [hxy] at ha hb',
    '      have hay := hy.2.1 ha',
    '      have hby := hy.2.1 hb',
    '      rw [Finset.mem_filter] at hax hbx hay hby',
    '      exact hC a (hv _ _ (hsymm _ _ hax.2)) x.1 (hv _ _ hax.2) b (hv _ _ (hsymm _ _ hbx.2)) y.1'
    ' (hv _ _ hby.2) hab hfst ⟨hsymm _ _ hax.2, hbx.2, hsymm _ _ hby.2, hay.2⟩',
    'have hc1 : ((Finset.range n).sigma (fun v => ((Finset.range n).filter (fun w => G4.adj S v w)).powersetCard 2)).card'
    f' = ∑ v ∈ Finset.range n, ({DEG}).choose 2 := by',
    '  rw [Finset.card_sigma]',
    '  exact Finset.sum_congr rfl (fun v _ => Finset.card_powersetCard 2 _)',
    'have hc2 : ((Finset.range n).powersetCard 2).card = n.choose 2 := by',
    '  rw [Finset.card_powersetCard, Finset.card_range]',
    'rw [← hc1, ← hc2]',
    'exact key',
])


def quadratic_recipe(pair_count_const):
    """The quadratic bound from the checked pair count (``pair_count_const``)."""
    return '\n'.join([
        'intro n S hS hC',
        f'have hpc : {PAIR_COUNT_CONCL} := {pair_count_const} n S hS hC',
        f'have hdeg : ∀ v ∈ Finset.range n, {DEG} = ∑ w ∈ Finset.range n,'
        ' ((if (v, w) ∈ S then 1 else 0) + (if (w, v) ∈ S then 1 else 0)) := by',
        '  intro v _',
        '  rw [Finset.card_filter]',
        '  refine Finset.sum_congr rfl ?_',
        '  intro w _',
        '  by_cases h1 : (v, w) ∈ S <;> by_cases h2 : (w, v) ∈ S',
        '  · exfalso',
        '    have a1 := (hS _ h1).1',
        '    have a2 := (hS _ h2).1',
        '    dsimp only at a1 a2',
        '    omega',
        '  · have h : G4.adj S v w := Or.inl h1',
        '    simp [h, h1, h2]',
        '  · have h : G4.adj S v w := Or.inr h2',
        '    simp [h, h1, h2]',
        '  · have h : ¬ G4.adj S v w := by',
        '      intro h',
        '      rcases h with h | h',
        '      · exact h1 h',
        '      · exact h2 h',
        '    simp [h, h1, h2]',
        'have hfilt : (Finset.range n ×ˢ Finset.range n).filter (fun x => (x.1, x.2) ∈ S) = S := by',
        '  ext x',
        '  rw [Finset.mem_filter, Finset.mem_product, Finset.mem_range, Finset.mem_range, Prod.mk.eta]',
        '  constructor',
        '  · intro h',
        '    exact h.2',
        '  · intro h',
        '    have h\' := hS x h',
        '    exact ⟨⟨by omega, h\'.2⟩, h⟩',
        'have hone : ∑ v ∈ Finset.range n, ∑ w ∈ Finset.range n, (if (v, w) ∈ S then 1 else 0) = S.card := by',
        '  have hp := Finset.sum_product\' (Finset.range n) (Finset.range n) (fun v w => if (v, w) ∈ S then 1 else 0)',
        '  rw [← hp, Finset.sum_boole, Nat.cast_id, hfilt]',
        f'have hhand : ∑ v ∈ Finset.range n, {DEG} = 2 * S.card := by',
        '  rw [Finset.sum_congr rfl hdeg]',
        '  simp only [Finset.sum_add_distrib]',
        '  rw [hone, Finset.sum_comm, hone]',
        '  omega',
        'have hsq : ∀ d : ℕ, d ^ 2 = 2 * d.choose 2 + d := by',
        '  intro d',
        '  induction d with',
        '  | zero => rfl',
        '  | succ k ih =>',
        '    have e : (k + 1).choose 2 = k.choose 1 + k.choose 2 := rfl',
        '    rw [e, Nat.choose_one_right]',
        '    calc (k + 1) ^ 2 = k ^ 2 + 2 * k + 1 := by ring',
        '      _ = 2 * k.choose 2 + k + 2 * k + 1 := by rw [ih]',
        '      _ = 2 * (k + k.choose 2) + (k + 1) := by ring',
        f'have hsum_sq : ∑ v ∈ Finset.range n, {DEG} ^ 2 = 2 * ∑ v ∈ Finset.range n, ({DEG}).choose 2'
        f' + ∑ v ∈ Finset.range n, {DEG} := by',
        '  rw [Finset.mul_sum, ← Finset.sum_add_distrib]',
        '  exact Finset.sum_congr rfl (fun v _ => hsq _)',
        'have h3 : 2 * n.choose 2 = n * (n - 1) := by',
        '  have := hsq n',
        '  cases n with',
        '  | zero => rfl',
        '  | succ k =>',
        '    show 2 * (k + 1).choose 2 = (k + 1) * k',
        '    have e : (k + 1) ^ 2 = (k + 1) * k + (k + 1) := by ring',
        '    rw [e] at this',
        '    exact (Nat.add_right_cancel this).symm',
        f'have hQ : ∑ v ∈ Finset.range n, {DEG} ^ 2 ≤ n * (n - 1) + 2 * S.card := by',
        '  rw [hsum_sq, hhand, ← h3]',
        '  have := Nat.mul_le_mul_left 2 hpc',
        '  omega',
        f'have hcs := Finset.sum_mul_sq_le_sq_mul_sq (Finset.range n) (fun v => {DEG}) (fun _ => (1 : ℕ))',
        'simp only [mul_one, one_pow, ← Finset.card_eq_sum_ones, Finset.card_range] at hcs',
        'rw [hhand] at hcs',
        'calc 4 * S.card ^ 2 = (2 * S.card) ^ 2 := by ring',
        f'  _ ≤ (∑ v ∈ Finset.range n, {DEG} ^ 2) * n := hcs',
        '  _ ≤ (n * (n - 1) + 2 * S.card) * n := Nat.mul_le_mul_right n hQ',
        '  _ = n ^ 2 * (n - 1) + 2 * n * S.card := by ring',
    ])


# ------------------------------------------------------------------ Python models (screening only)

def degrees(n, S):
    S = set(map(tuple, S))
    return [sum(1 for w in range(n) if (v, w) in S or (w, v) in S) for v in range(n)]


def comb2(d):
    return d * (d - 1) // 2


def host_ok(n, S):
    return all(u < v < n for u, v in S)


def pair_count_holds(n, S):
    return sum(comb2(d) for d in degrees(n, S)) <= comb2(n)


def quadratic_holds(n, S):
    m = len(set(map(tuple, S)))
    return 4 * m * m <= n * n * max(n - 1, 0) + 2 * n * m


def _sample(rng):
    """Small hosts: half random simple edge sets, half maximal C4-free ones (where the bound is tight-ish)."""
    n = rng.randint(1, 8)
    pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
    if rng.random() < 0.5:
        p = rng.choice((0.15, 0.3, 0.5))
        return {'n': n, 'S': frozenset(e for e in pairs if rng.random() < p)}
    rng.shuffle(pairs)
    S = set()
    for e in pairs:
        if R.c4free(S | {e}):
            S.add(e)
    return {'n': n, 'S': frozenset(S)}


def lean_value(b, x):
    if b['type'] == 'ℕ':
        return str(int(x))
    return R.lean_value(b, x)


def _binders():
    return [{'name': 'n', 'type': 'ℕ'}, {'name': 'S', 'type': 'GT.Edges'},
            {'name': 'hS', 'hyp': True, 'lean': HOST_HYP, 'model': lambda v: host_ok(v['n'], v['S'])},
            {'name': 'hC', 'hyp': True, 'lean': 'G4.C4Free S', 'model': lambda v: R.c4free(v['S'])}]


def conjectures():
    origin = 'builder-written (CRPD-2b): known counting bound, stated over the repository definitions'
    return [
        {'id': 'pair_count_c4', 'binders': _binders(), 'concl': PAIR_COUNT_CONCL,
         'model': lambda v: pair_count_holds(v['n'], v['S']), 'sampler': _sample, 'origin': origin,
         'role': 'bound', 'subject': 'pair-count@c4_host_v2', 'lean_value': lean_value},
        {'id': 'c4_quadratic_bound', 'binders': _binders(), 'concl': QUADRATIC_CONCL,
         'model': lambda v: quadratic_holds(v['n'], v['S']), 'sampler': _sample, 'origin': origin,
         'role': 'bound', 'subject': 'C4-pair-count-quadratic@c4_host_v2', 'lean_value': lean_value},
    ]


def recipes(conj, library):
    if conj['id'] == 'pair_count_c4':
        return [('pair-count-injection (builder-written)', PAIR_COUNT_RECIPE)]
    if conj['id'] == 'c4_quadratic_bound':
        pc = next((x['const'] for x in library if x['statement'] == 'pair_count_c4'), None)
        return [('handshake-cauchy-schwarz (builder-written)', quadratic_recipe(pc))] if pc else []
    return []


IMPORTS_MODULE = 'PCImports'
IMPORTS_SOURCE = f'''import {R.C4_MODULE}
import Mathlib.Algebra.BigOperators.Group.Finset.Sigma
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
'''


def base_modules():
    """The repository definitions plus a definition-free module bringing Finset big operators
    (the CRPD-2b import roots) into scope for the statement and proof modules."""
    return [{'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True},
            {'name': R.C4_MODULE, 'source': R.C4_SOURCE, 'trusted': True},
            {'name': IMPORTS_MODULE, 'source': IMPORTS_SOURCE, 'trusted': True}]


def quadratic_upper(n):
    """The largest m with 4m^2 <= n^2 (n - 1) + 2nm (exact integers): the bound the checked
    theorem gives for a C4-free subgraph of any host on n vertices."""
    if n <= 0:
        return 0
    lo, hi = 0, n * n
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if 4 * mid * mid <= n * n * (n - 1) + 2 * n * mid:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ------------------------------------------------------------------ the checked bound as an upper certificate

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / 'evidence' / 'pair_count_b20r'
CONJ_NAME, PROOF_PREFIX = 'PCConj', 'PCP'
STATEMENT_ID = 'c4_quadratic_bound'
DOMAIN = 'c4_host_v2'


def expected_statement():
    from ..formal_research.loop import statement
    return statement(next(c for c in conjectures() if c['id'] == STATEMENT_ID))


def expected_conj_source():
    from ..formal_research.loop import conj_module
    return conj_module(CONJ_NAME, [m['name'] for m in base_modules() if m['trusted']], conjectures())


def package_problems(package):
    """Checks that need no Lean: ``package`` is an intact theory package whose trusted modules are
    exactly the repository definitions and the generated statement module, and in which the
    quadratic bound is CHECKED with allowed axioms only. (Whether the proof really checks is the
    Lean replay's job: ``replay_verdict``.)"""
    from ..formal_research import theory_package as TP
    from ..verification.lean import ALLOWED_AXIOMS
    if not isinstance(package, dict):
        return ['not a theory package']
    out = list(TP.integrity_problems(package))
    trusted = {m['name']: m['source'] for m in package.get('modules', []) if m.get('trusted')}
    want = {m['name']: m['source'] for m in base_modules()}
    want[CONJ_NAME] = expected_conj_source()
    if trusted != want:
        out.append('the trusted modules are not exactly the repository definitions and the generated statement module')
    st = {s.get('id'): s for s in package.get('statements', [])}.get(STATEMENT_ID)
    if st is None or st.get('status') != 'CHECKED':
        out.append(f'{STATEMENT_ID} is not CHECKED in the package')
    elif st.get('lean') != expected_statement() or st.get('spec_const') != f'{CONJ_NAME}.{STATEMENT_ID}':
        out.append(f'{STATEMENT_ID} is recorded with another statement or constant')
    if set((package.get('assumptions') or {}).get('axioms_used') or ()) - set(ALLOWED_AXIOMS):
        out.append('the package uses axioms outside the allowed set')
    return out


def applicability_problems(task):
    """The theorem's hypotheses for a host: the c4_host_v2 contract (G4.C4Free is that domain's
    motif-freeness) and edges (u, v) with u < v < n (GraphTask enforces this; re-checked here)."""
    out = []
    if getattr(task, 'domain', None) != DOMAIN:
        out.append(f'the pair-count bound is a theorem about {DOMAIN} hosts only')
    if any(not 0 <= u < v < task.n for u, v in task.edges):
        out.append('host edges are not ordered pairs u < v < n')
    return out


def checker_identity():
    """Identity of the Lean replay route for this bound: pinned Lean, formal workspace pins, the
    acceptance checker and the package replayer. Revoking it rejects every PAIR_COUNT_LEAN bound."""
    import hashlib
    import json as _json
    pins = _json.loads((REPO / 'toolchain' / 'PINS.json').read_text())
    ws = _json.loads((REPO / 'toolchain' / 'FORMAL_WORKSPACE.json').read_text())
    src = REPO / 'src' / 'genesis' / 'formal_research'
    ident = {'lean': pins['lean'], 'workspace': digest(ws),
             'checker_sha256': hashlib.sha256((src / 'checker.py').read_bytes()).hexdigest(),
             'replay_sha256': hashlib.sha256((src / 'theory_package.py').read_bytes()).hexdigest()}
    return digest(ident)


_REPLAYS = {}


def replay_verdict(package):
    """'REPLAYED' when the package rechecks from its sources in the pinned workspace (cached per
    package, workspace artifact identity and checker identity); otherwise the reason."""
    from ..formal_research import theory_package as TP
    from ..formal_research import workspace as W
    try:
        ws = W.environment()['artifact_identity']
    except Exception as exc:
        return f'CHECKER_ERROR: formal workspace unavailable ({type(exc).__name__})'
    key = (package.get('package_sha256'), ws, checker_identity())
    if key not in _REPLAYS:
        rep = TP.replay(package)
        _REPLAYS[key] = 'REPLAYED' if rep['verdict'] == 'REPLAYED' else f'DIFFERS: {rep["differences"][:3]}'
    return _REPLAYS[key]


def committed_package():
    import json as _json
    return _json.loads((EVIDENCE / 'package.json').read_text())


__all__ = ['PAIR_COUNT_CONCL', 'QUADRATIC_CONCL', 'PAIR_COUNT_RECIPE', 'quadratic_recipe', 'conjectures', 'recipes',
           'base_modules', 'quadratic_upper', 'degrees', 'pair_count_holds', 'quadratic_holds', 'host_ok',
           'package_problems', 'applicability_problems', 'checker_identity', 'replay_verdict', 'committed_package',
           'expected_statement', 'STATEMENT_ID', 'DOMAIN']
