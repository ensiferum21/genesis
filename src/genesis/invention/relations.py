"""Machine-generated relational decoders (handoff s15.3, W10: richer representation invention).

The B18 grammar (``representations``) has a hand-written menu of four vertex-class decoders.
This module adds ONE new representation family, generated rather than listed: an oriented
relational decoder over k classes,

    decode_R c H = { (u, v) ∈ H : (c u, c v) ∈ R },     R ⊆ Fin k × Fin k,

which reads the host orientation (hosts list each edge once as (u, v) with u < v). The family is
generated, checked and reduced mechanically:

  * enumeration: every non-empty R for 2 ≤ k ≤ MAX_K (the grammar's existing bound, 3; a larger k
    would be a versioned expansion, not a silent one);
  * exact soundness for triangle-free hosts: decode_R c H is triangle-free for EVERY host and
    encoding iff no x, y, z ∈ Fin k have R x y ∧ R y z ∧ R x z. (If such x, y, z exist, the host
    {(0,1), (1,2), (0,2)} with c = (x, y, z) decodes to a triangle; conversely a decoded triangle
    (a,b), (b,d), (a,d) gives such a triple.) The check is exhaustive over k³ triples, and the
    soundness theorem is stated and proved in Lean for every generated decoder that is used;
  * dominance: a sub-relation decodes a subset, so only inclusion-maximal sound relations are kept;
  * symmetry: relabelling classes by a permutation π maps decode_R c to decode_{πR} (π ∘ c), and
    π ∘ c ranges over all encodings, so relations in one orbit are the same representation. One
    canonical representative per orbit is kept (the lexicographically least relabelling);
  * reduction: a class no pair of R uses only deletes edges, so it is removed before comparison;
  * novelty against the menu: a generated relation is NEW only if its reduced canonical form
    differs from every menu decoder's (cross, inside, ordered, adjacent; k ≤ MAX_K).

Each proposal carries what the representation keeps and loses, its cost and failure conditions,
a Lean definition, and the obligations (image, triangle-free soundness) with builder-written
recipes. ``representations.represent_and_repair`` runs it unchanged (it only calls ``_py``), and
the domain checker validates every witness it returns.
"""
from itertools import permutations

from . import representations as RP

MAX_K = RP.MAX_K
MODULE = 'RLDefs'
ORIGIN = 'generated:relation-enumeration-v1'
# Versioned expansion (B20_R19). v1 (B20_R17) is kept exactly as it ran. v2 lifts the class bound
# to 4 -- justified because the v1 space is exhausted (one NEW maximal decoder, NO_UTILITY_AFTER_COST)
# and k = 4 is the next level of the same family, still a finite space (2^16 relations, 4^n
# encodings) -- and strengthens equivalence: classes that are twins (identical out- and
# in-relations, and no relation among themselves or to themselves) are merged, since splitting a
# class into twins decodes exactly the same edge sets. v2 therefore never calls a twin-split of a
# menu decoder NEW.
VERSIONS = {'v1': {'max_k': 3, 'twins': False, 'origin': 'generated:relation-enumeration-v1'},
            'v2': {'max_k': 4, 'twins': True, 'origin': 'generated:relation-enumeration-v2'}}
MAX_K_ANY = max(v['max_k'] for v in VERSIONS.values())


def all_relations(k):
    pairs = [(x, y) for x in range(k) for y in range(k)]
    for mask in range(1, 1 << len(pairs)):
        yield frozenset(p for i, p in enumerate(pairs) if mask >> i & 1)


def tf_sound(R, k):
    """Exact: decode_R is triangle-free for every host and encoding."""
    return not any((x, y) in R and (y, z) in R and (x, z) in R for x in range(k) for y in range(k) for z in range(k))


def reduce(R, k):
    """Drop classes no pair uses and renumber the rest in order: (R', k')."""
    used = sorted({x for p in R for x in p})
    idx = {x: i for i, x in enumerate(used)}
    return frozenset((idx[x], idx[y]) for x, y in R), len(used)


def merge_twins(R, k):
    """Merge twin classes until none are left: x, y are twins if they relate to and from every
    other class alike and R has none of (x,x), (y,y), (x,y), (y,x). Returns (R', k')."""
    while True:
        pair = next(((x, y) for x in range(k) for y in range(x + 1, k)
                     if all(((x, z) in R) == ((y, z) in R) and ((z, x) in R) == ((z, y) in R)
                            for z in range(k) if z not in (x, y))
                     and not {(x, x), (y, y), (x, y), (y, x)} & R), None)
        if pair is None:
            return R, k
        x, y = pair
        keep = [z for z in range(k) if z != y]
        idx = {z: i for i, z in enumerate(keep)}
        R = frozenset((idx[a], idx[b]) for a, b in R if y not in (a, b))
        k -= 1


def canonical(R, k, twins=False):
    """(k, least relabelling) after reduction (and, with ``twins``, twin merging): one representative
    per symmetry orbit."""
    R, k = reduce(R, k)
    if twins:
        R, k = merge_twins(R, k)
    return k, min(tuple(sorted((p[x], p[y]) for x, y in R)) for p in permutations(range(k)))


def menu_relation(decoder, k):
    py = RP.DECODERS[decoder][1]
    return frozenset((x, y) for x in range(k) for y in range(k) if py(x, y))


def menu_forms(twins=False):
    """{canonical form: 'name = name …'} for the hand-written menu (cross_2 and adjacent_2 coincide)."""
    forms = {}
    for d in RP.DECODERS:
        for k in range(2, MAX_K + 1):
            forms.setdefault(canonical(menu_relation(d, k), k, twins), []).append(f'{d}_{k}')
    return {f: ' = '.join(sorted(names)) for f, names in forms.items()}


def generate(max_k=MAX_K, version='v1'):
    """Inclusion-maximal sound relations per k, reduced to canonical orbit representatives, each
    marked NEW or with the menu decoder it equals. Deterministic order. ``version`` fixes the bound
    and the equivalence (VERSIONS); v1 is exactly the B20_R17 generator."""
    spec = VERSIONS[version]
    if not 2 <= max_k <= spec['max_k']:
        raise ValueError(f'k is bounded by the grammar version {version}: 2 <= k <= {spec["max_k"]}')
    menu = menu_forms(spec['twins'])
    out, seen = [], set()
    for k in range(2, max_k + 1):
        sound = [R for R in all_relations(k) if tf_sound(R, k)]
        sound_set = set(sound)
        maximal = [R for R in sound if not any(R | {p} in sound_set for p in _pairs(k) if p not in R)]
        for R in sorted(maximal, key=lambda R: sorted(R)):
            form = canonical(R, k, spec['twins'])
            if form in seen:
                continue
            seen.add(form)
            out.append({'k': form[0], 'relation': [list(p) for p in form[1]], 'equals_menu': menu.get(form),
                        'enumerated_at_k': k})
    return out


def _pairs(k):
    return [(x, y) for x in range(k) for y in range(k)]


def _name(k, rel):
    return f'rel{k}_' + ''.join(f'{x}{y}' for x, y in rel)


def proposal(k, relation, version='v1'):
    """Typed record for one relational decoder (same shape as ``representations.typecheck``)."""
    bound = VERSIONS[version]['max_k']
    if type(k) is not int or not 2 <= k <= bound:
        raise RP.ProposalError(f'class count k must be an integer in [2, {bound}]')
    rel = sorted({(int(x), int(y)) for x, y in relation})
    if not rel or any(not (0 <= x < k and 0 <= y < k) for x, y in rel):
        raise RP.ProposalError('relation must be a non-empty set of class pairs below k')
    R = frozenset(rel)
    name = _name(k, rel)
    lit = '[' + ', '.join(f'({x}, {y})' for x, y in rel) + ']'
    lean_pred = f'((c e.1).val, (c e.2).val) ∈ ({lit} : List (ℕ × ℕ))'
    text = ', '.join(f'{x}→{y}' for x, y in rel)
    return {'id': name, 'decoder': 'relation', 'k': k, 'relation': [list(p) for p in rel], 'lean_name': f'RL.{name}',
            'encoder': {'type': f'ℕ → Fin {k}', 'space': f'{k}^n encodings of an n-vertex host'},
            'decoder_lean': f'fun e => {lean_pred}', 'semantics': f'RL.{name} c H = H.filter (fun e => {lean_pred})',
            'retained': f'host edges (u, v), u < v, whose class pair is one of {text}',
            'lost': 'every other host edge (in particular every edge inside a class)',
            'cost': {'decode': 'O(|H|)', 'encoder_space': f'{k}^n', 'bound': f'k ≤ {bound}'},
            'failure_conditions': ['local search over encodings gives no optimality guarantee',
                                   'reads the host orientation: the same graph listed in another vertex order can '
                                   'decode differently'],
            'kind': 'conservative-definition', 'origin': VERSIONS[version]['origin'], 'tf_sound_exact': tf_sound(R, k),
            '_py': lambda cu, cv, R=R: (cu, cv) in R}


def source(props):
    lines = [f'import {RP.DEFS_MODULE}', '', 'namespace RL', '']
    for r in props:
        lines.append(f'/-- Generated relational decoder `{r["id"]}` ({r["origin"]}): {r["retained"]}. -/')
        lines.append(f'def {r["id"]} (c : ℕ → Fin {r["k"]}) (H : GT.Edges) : GT.Edges := H.filter {r["decoder_lean"]}')
        lines.append('')
    lines += ['end RL', '']
    return '\n'.join(lines)


def conjectures(props):
    """Image and triangle-free soundness, as Lean statements with Python models for the screen."""
    out = []
    for r in props:
        k = r['k']
        enc = {'name': 'c', 'type': f'ℕ → Fin {k}'}
        host = {'name': 'H', 'type': 'GT.Edges'}

        def sampler(rng, k=k):
            return {'c': {v: rng.randrange(k) for v in range(4)}, 'H': RP._sample_edges(rng)}
        out.append(RP._conj(f'{r["id"]}_image', [enc, host], f'RL.{r["id"]} c H ⊆ H',
                            lambda v, r=r: RP.decode(r, v['c'], v['H']) <= v['H'], sampler, r['origin'], 'image', r['id']))
        out.append(RP._conj(f'{r["id"]}_sound_tf', [enc, host], f'GT.TriangleFree (RL.{r["id"]} c H)',
                            lambda v, r=r: RP.DOMAINS['triangle_free_host_v1']['model'](RP.decode(r, v['c'], v['H'])),
                            sampler, r['origin'], 'soundness', f'{r["id"]}@triangle_free_host_v1'))
    return out


def recipes(props):
    by_id = {r['id']: r for r in props}

    def extra(conj, library):
        role, sub = conj.get('role'), conj.get('subject', '')
        r = by_id.get(sub.split('@')[0])
        if r is None:
            return []
        if role == 'image':
            return [('filter-subset', f'intro c H\nsimp_all [RL.{r["id"]}]'),
                    ('filter-subset-lemma', f'intro c H\nunfold RL.{r["id"]}\nexact Finset.filter_subset _ _')]
        if role != 'soundness':
            return []
        k = r['k']
        lit = '[' + ', '.join(f'({x}, {y})' for x, y in r['relation']) + ']'
        head = ['intro c H', f'unfold GT.TriangleFree RL.{r["id"]}',
                "rintro ⟨a, b⟩ he ⟨b', d⟩ hf ⟨a', d'⟩ hg ⟨h1, h2, h3⟩",
                'simp only [Finset.mem_filter] at he hf hg', 'simp only at h1 h2 h3', 'subst h1 h2 h3']
        key = (f'have key : ∀ x y z : Fin {k}, ¬ ((x.val, y.val) ∈ ({lit} : List (ℕ × ℕ)) ∧ '
               f'(y.val, z.val) ∈ ({lit} : List (ℕ × ℕ)) ∧ (x.val, z.val) ∈ ({lit} : List (ℕ × ℕ))) := by decide')
        return [('class-triple-decide', '\n'.join(head + [key, 'exact key _ _ _ ⟨he.2, hf.2, hg.2⟩'])),
                ('class-triple-omega', '\n'.join(head + [
                    'simp only [List.mem_cons, List.mem_singleton, Prod.mk.injEq, List.not_mem_nil, or_false] '
                    'at he hf hg', 'omega']))]
    return extra


__all__ = ['generate', 'proposal', 'source', 'conjectures', 'recipes', 'tf_sound', 'canonical', 'reduce',
           'merge_twins', 'menu_forms', 'all_relations', 'MODULE', 'ORIGIN', 'VERSIONS']
