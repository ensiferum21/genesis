"""The first theory: obstructions for triangle-free subgraphs (domain triangle_free_host_v1).

What is builder-written and what is generated:

* Builder-written (the domain contract, trusted): `GT.Edges` and `GT.TriangleFree`,
  with Python models that implement exactly the same definitions, including the
  ordered-pair reading (a self-loop (a, a) forms a "triangle" with itself).
* Generated concepts (trusted modules written by Genesis code from templates and
  searches):
  - `GT.TFBound H k`, the bound concept: every triangle-free S ⊆ H has |S| ≤ k;
  - `GT.Simple S`, the normal form (u < v), proposed when a counterexample uses
    an edge outside it;
  - gadget families, from an exhaustive search over small graphs, kept only when
    their deficit beats every packing of smaller gadgets inside them.
* Generated conjectures: closure and bound templates over the concepts. Each is
  screened against the Python model on sampled instances, and becomes
  - DISPROVED: a minimal counterexample turned into a Lean proof of the negation;
  - a corrected conjecture: the counterexample breaks the normal form, so the
    hypothesis `Simple` is added and the corrected statement goes back through
    screening;
  - CHECKED: a recipe from `search` proves it and `checker.accept` accepts it;
  - UNRESOLVED: no recipe succeeds within the budget;
  - UNSUPPORTED: the template needs a definition this theory does not have.
* The executable method (`packing_bound`) uses only gadget families and lemmas the
  package has CHECKED. Every bound it reports comes with a certificate, and
  `certificate_modules` turns that certificate into a Lean proof of `GT.TFBound host B`
  that reuses the package's lemmas.

Scope: hosts are finite sets of pairs (u, v) with u < v. The method gives upper bounds
only, not optima. All of this is rediscovery of elementary facts, a capability
demonstration with no novelty claim.
"""
from itertools import combinations, permutations
import random

from ..common import digest

NAMESPACE = 'GT'

DEFS_MODULE = 'GTDefs'
DEFS_SOURCE = '''import Mathlib.Data.Finset.Powerset

namespace GT

/-- Edge sets: ordered pairs (u, v), read as the edge {u, v}. Hosts list each edge once, with u < v. -/
abbrev Edges := Finset (ℕ × ℕ)

/-- No three edges (a, b), (b, c), (a, c). -/
def TriangleFree (S : Edges) : Prop :=
  ∀ e ∈ S, ∀ f ∈ S, ∀ g ∈ S, ¬ (e.1 = g.1 ∧ e.2 = f.1 ∧ f.2 = g.2)

instance (S : Edges) : Decidable (TriangleFree S) := by
  unfold TriangleFree; infer_instance

end GT
'''


# ---------------------------------------------------------------- Python models (same definitions)

def tf(S):
    return not any(e[0] == g[0] and e[1] == f[0] and f[1] == g[1] for e in S for f in S for g in S)


def tf_bound(H, k):
    H = sorted(H)
    return all(len(sub) <= k for r in range(len(H) + 1) for sub in combinations(H, r) if tf(sub))


def tf_opt(H):
    H = sorted(H)
    for r in range(len(H), -1, -1):
        if any(tf(sub) for sub in combinations(H, r)):
            return r
    return 0


def simple(S):
    return all(u < v for u, v in S)


# ---------------------------------------------------------------- gadget search (generated definitions)

def _canonical(n, edges):
    return min(tuple(sorted(tuple(sorted((p[u], p[v]))) for u, v in edges)) for p in permutations(range(n)))


def _connected(n, edges):
    adj = {v: set() for v in range(n)}
    for u, v in edges:
        adj[u].add(v); adj[v].add(u)
    seen, stack = {0}, [0]
    while stack:
        for w in adj[stack.pop()] - seen:
            seen.add(w); stack.append(w)
    return len(seen) == n


def _in_triangle(n, edges):
    E = set(edges)
    return all(any(tuple(sorted((u, w))) in E and tuple(sorted((v, w))) in E for w in range(n) if w not in (u, v))
               for u, v in edges)


def _best_packing(n, edges, catalog):
    """Largest total deficit of edge-disjoint embedded catalog gadgets (exhaustive, tiny graphs)."""
    E = set(edges)
    embeds = []
    for g in catalog:
        for verts in permutations(range(n), g['vertices']):
            es = frozenset(tuple(sorted((verts[i], verts[j]))) for i, j in g['pattern'])
            if es <= E:
                embeds.append((es, g['deficit']))
    best = 0

    def go(i, used, total):
        nonlocal best
        best = max(best, total)
        for j in range(i, len(embeds)):
            es, d = embeds[j]
            if not es & used:
                go(j + 1, used | es, total + d)
    go(0, frozenset(), 0)
    return best


def gadget_search(*, max_vertices=4, max_edges=6):
    """Connected graphs whose every edge lies in a triangle, up to isomorphism, kept when
    their deficit (|E| minus the largest triangle-free subgraph) beats every edge-disjoint
    packing of smaller kept gadgets. Returns (catalog, all candidates examined)."""
    catalog, examined = [], []
    for n in range(3, max_vertices + 1):
        seen = set()
        pairs = list(combinations(range(n), 2))
        for m in range(3, min(max_edges, len(pairs)) + 1):
            for edges in combinations(pairs, m):
                if not _connected(n, edges) or not _in_triangle(n, edges):
                    continue
                key = _canonical(n, edges)
                if key in seen:
                    continue
                seen.add(key)
                opt = tf_opt(set(key))
                deficit = len(key) - opt
                packing = _best_packing(n, key, catalog)
                row = {'vertices': n, 'pattern': [list(e) for e in key], 'edges': len(key), 'bound': opt,
                       'deficit': deficit, 'best_packing_of_smaller': packing, 'kept': deficit > packing}
                examined.append(row)
                if row['kept']:
                    row['name'] = f'Gad{n}e{len(key)}'
                    catalog.append(row)
    return catalog, examined


def gadget_definition(g):
    vs = [f'v{i}' for i in range(g['vertices'])]
    body = ', '.join(f'({vs[i]}, {vs[j]})' for i, j in g['pattern'])
    return (f'/-- Generated gadget: {g["vertices"]} vertices, {g["edges"]} edges, triangle-free bound {g["bound"]}. -/\n'
            f'def {g["name"]} ({" ".join(vs)} : ℕ) : Edges := {{{body}}}')


def concepts_source(catalog):
    gadgets = '\n\n'.join(gadget_definition(g) for g in catalog)
    return f'''import {DEFS_MODULE}

namespace GT

/-- Generated bound concept: `k` bounds every triangle-free edge set inside `H`. -/
def TFBound (H : Edges) (k : ℕ) : Prop := ∀ S ⊆ H, TriangleFree S → S.card ≤ k

instance (H : Edges) (k : ℕ) : Decidable (TFBound H k) := by
  unfold TFBound; infer_instance

/-- Generated normal form: every pair is listed with u < v. -/
def Simple (S : Edges) : Prop := ∀ e ∈ S, e.1 < e.2

instance (S : Edges) : Decidable (Simple S) := by
  unfold Simple; infer_instance

{gadgets}

end GT
'''


CONCEPTS_MODULE = 'GTConcepts'
UNFOLD = ['GT.TFBound', 'GT.TriangleFree']


# ---------------------------------------------------------------- conjecture templates

def E(name):
    return {'name': name, 'type': 'GT.Edges'}


def N(name):
    return {'name': name, 'type': 'ℕ'}


def P(name):
    return {'name': name, 'type': 'ℕ × ℕ'}


def H(name, lean, model):
    return {'name': name, 'hyp': True, 'lean': lean, 'model': model}


TEMPLATES = [
    ('down_closed', [E('S'), E('T'), H('h1', 'T ⊆ S', lambda v: v['T'] <= v['S']),
                     H('h2', 'GT.TriangleFree S', lambda v: tf(v['S']))],
     ('GT.TriangleFree T', lambda v: tf(v['T']))),
    ('union_closed', [E('S'), E('T'), H('h1', 'GT.TriangleFree S', lambda v: tf(v['S'])),
                      H('h2', 'GT.TriangleFree T', lambda v: tf(v['T']))],
     ('GT.TriangleFree (S ∪ T)', lambda v: tf(v['S'] | v['T']))),
    ('inter_closed', [E('S'), E('T'), H('h1', 'GT.TriangleFree S', lambda v: tf(v['S']))],
     ('GT.TriangleFree (S ∩ T)', lambda v: tf(v['S'] & v['T']))),
    ('insert_closed', [E('S'), P('e'), H('h1', 'GT.TriangleFree S', lambda v: tf(v['S']))],
     ('GT.TriangleFree (insert e S)', lambda v: tf(v['S'] | {v['e']}))),
    ('bound_card', [E('A')], ('GT.TFBound A A.card', lambda v: tf_bound(v['A'], len(v['A'])))),
    ('bound_union', [E('A'), E('B'), N('a'), N('b'), H('h1', 'GT.TFBound A a', lambda v: tf_bound(v['A'], v['a'])),
                     H('h2', 'GT.TFBound B b', lambda v: tf_bound(v['B'], v['b']))],
     ('GT.TFBound (A ∪ B) (a + b)', lambda v: tf_bound(v['A'] | v['B'], v['a'] + v['b']))),
    ('bound_mono', [E('A'), E('B'), N('a'), N('b'), H('h1', 'GT.TFBound B a', lambda v: tf_bound(v['B'], v['a'])),
                    H('h2', 'A ⊆ B', lambda v: v['A'] <= v['B']), H('h3', 'a ≤ b', lambda v: v['a'] <= v['b'])],
     ('GT.TFBound A b', lambda v: tf_bound(v['A'], v['b']))),
    ('bound_insert', [E('A'), N('a'), P('e'), H('h1', 'GT.TFBound A a', lambda v: tf_bound(v['A'], v['a']))],
     ('GT.TFBound (insert e A) a', lambda v: tf_bound(v['A'] | {v['e']}, v['a']))),
    ('bound_le_card', [E('A'), N('a'), H('h1', 'GT.TFBound A a', lambda v: tf_bound(v['A'], v['a']))],
     ('a ≤ A.card', lambda v: v['a'] <= len(v['A']))),
    ('bound_zero_empty', [E('A'), H('h1', 'GT.TFBound A 0', lambda v: tf_bound(v['A'], 0))],
     ('A = ∅', lambda v: not v['A'])),
    ('mantel', [E('A'), N('n'), H('h1', '∀ e ∈ A, e.1 < e.2 ∧ e.2 < n',
                                   lambda v: all(a < b < v['n'] for a, b in v['A']))],
     ('GT.TFBound A (n * n / 4)', lambda v: tf_bound(v['A'], v['n'] * v['n'] // 4))),
    # needs a definition this theory does not have: reported UNSUPPORTED, never guessed
    ('c4_down_closed', [E('S'), E('T'), H('h1', 'T ⊆ S', None), H('h2', 'GT.C4Free S', None)],
     ('GT.C4Free T', None)),
]
KNOWN = {'GT.Edges', 'GT.TriangleFree', 'GT.TFBound', 'GT.Simple'}


def supported(binders, concl):
    import re
    text = ' '.join([b.get('lean', '') for b in binders] + [concl[0]])
    used = set(re.findall(r'GT\.\w+', text))
    return used <= KNOWN and all(b.get('model', True) is not None for b in binders) and concl[1] is not None


def lean_statement(binders, concl):
    parts = []
    for b in binders:
        parts.append(f'({b["name"]} : {b["lean"] if b.get("hyp") else b["type"]})')
    return f'∀ {" ".join(parts)}, {concl[0]}' if parts else concl[0]


def corrected(name, binders, concl):
    """Add the normal-form hypothesis for every edge-set binder (`GT.Simple X`) and every
    pair binder (`e.1 < e.2`)."""
    extra = [H(f'hs{b["name"]}', f'GT.Simple {b["name"]}', (lambda nm: lambda v: simple(v[nm]))(b['name']))
             for b in binders if b.get('type') == 'GT.Edges']
    extra += [H(f'hs{b["name"]}', f'{b["name"]}.1 < {b["name"]}.2', (lambda nm: lambda v: v[nm][0] < v[nm][1])(b['name']))
              for b in binders if b.get('type') == 'ℕ × ℕ']
    edge_binders = [b for b in binders if not b.get('hyp')]
    hyps = [b for b in binders if b.get('hyp')]
    return f'{name}_simple', edge_binders + extra + hyps, concl


# ---------------------------------------------------------------- screening with the Python model

PAIRS = [(u, v) for u in range(3) for v in range(3)]


def _sample(binders, rng):
    v = {}
    for b in binders:
        if b.get('hyp'):
            continue
        if b['type'] == 'GT.Edges':
            v[b['name']] = frozenset(p for p in PAIRS if rng.random() < 0.3)
        elif b['type'] == 'ℕ':
            v[b['name']] = rng.randrange(0, 6)
        else:
            v[b['name']] = rng.choice(PAIRS)
    return v


def screen(name, binders, concl, *, samples=4000, seed=0):
    """(counterexample or None, number of instances satisfying the hypotheses)."""
    rng = random.Random(int(digest({'screen': name, 'seed': seed})[:12], 16))
    best, relevant = None, 0
    for _ in range(samples):
        v = _sample(binders, rng)
        if not all(b['model'](v) for b in binders if b.get('hyp')):
            continue
        relevant += 1
        if not concl[1](v):
            size = sum(len(x) if isinstance(x, frozenset) else (x if isinstance(x, int) else 1) for x in v.values())
            if best is None or size < best[0]:
                best = (size, v)
    return (None if best is None else best[1]), relevant


def lean_value(x, typ):
    if typ == 'GT.Edges':
        return '(∅ : GT.Edges)' if not x else '({' + ', '.join(f'({u}, {w})' for u, w in sorted(x)) + '} : GT.Edges)'
    if typ == 'ℕ':
        return str(x)
    return f'(({x[0]}, {x[1]}) : ℕ × ℕ)'


def breaks_normal_form(binders, values):
    return any((b['type'] == 'GT.Edges' and not simple(values[b['name']])) or
               (b['type'] == 'ℕ × ℕ' and values[b['name']][0] >= values[b['name']][1])
               for b in binders if not b.get('hyp'))


# ---------------------------------------------------------------- the executable method

def _embeddings(host, n, g):
    E = set(host)
    k = g['vertices']
    for verts in combinations(range(n), k):           # order-respecting embeddings only
        es = [(verts[i], verts[j]) for i, j in g['pattern']]
        if all(e in E for e in es):
            yield verts, es


def packing_bound(n, edges, method):
    """Upper bound on the largest triangle-free subgraph of the host, with a certificate.

    `method` is compiled from a package (`compile_method`): gadget families with their
    CHECKED bounds. Greedy, best deficit per edge first; every remaining edge counts in full."""
    used, parts = set(), []
    for g in sorted(method['gadgets'], key=lambda g: (-g['deficit'] / g['edges'], -g['edges'], g['name'])):
        for verts, es in _embeddings(edges, n, g):
            if not set(es) & used:
                used |= set(es)
                parts.append({'gadget': g['name'], 'vertices': list(verts), 'bound': g['bound']})
    rest = sorted(set(map(tuple, edges)) - used)
    return {'bound': sum(p['bound'] for p in parts) + len(rest), 'parts': parts, 'rest': [list(e) for e in rest],
            'edges': len(edges)}


def certificate_modules(task_tag, n, edges, cert, method):
    """Trusted statement module and untrusted proof module for `GT.TFBound host B`.

    The proof reuses the package's CHECKED lemmas bound_card, bound_union and bound_mono."""
    lib = method['lemmas']
    host = '{' + ', '.join(f'({u}, {v})' for u, v in sorted(map(tuple, edges))) + '}'
    rest = '{' + ', '.join(f'({u}, {v})' for u, v in cert['rest']) + '}' if cert['rest'] else '∅'
    spec_name, proof_name = f'GTTask{task_tag}', f'GTCert{task_tag}'
    spec = '\n'.join([f'import {CONCEPTS_MODULE}', f'namespace {spec_name}',
                      f'def host : GT.Edges := {host}',
                      f'def stmt : Prop := GT.TFBound host {cert["bound"]}', f'end {spec_name}', ''])
    lines = [f'import {CONCEPTS_MODULE}', f'import {spec_name}', *[f'import {m}' for m in method['library_modules']],
             f'namespace {proof_name}', f'def rest : GT.Edges := {rest}',
             f'theorem proof : {spec_name}.stmt := by', f'  unfold {spec_name}.stmt']
    for i, p in enumerate(cert['parts']):
        lines.append(f'  have h{i} : GT.TFBound (GT.{p["gadget"]} {" ".join(map(str, p["vertices"]))}) {p["bound"]} '
                     f':= by decide')
    lines.append(f'  have hr : GT.TFBound rest rest.card := {lib["bound_card"]} rest')
    acc = 'hr'
    for i in reversed(range(len(cert['parts']))):
        acc = f'({lib["bound_union"]} _ _ _ _ h{i} {acc})'
    lines.append(f'  exact {lib["bound_mono"]} _ _ _ _ {acc} (by decide +kernel) (by decide +kernel)')
    lines += [f'end {proof_name}', '']
    return ({'name': spec_name, 'source': spec, 'trusted': True},
            {'name': proof_name, 'source': '\n'.join(lines), 'trusted': False},
            {'spec': f'{spec_name}.stmt', 'proof': f'{proof_name}.proof'})


__all__ = ['DEFS_SOURCE', 'concepts_source', 'gadget_search', 'TEMPLATES', 'screen', 'corrected', 'packing_bound',
           'certificate_modules', 'tf', 'tf_bound', 'tf_opt']
