#!/usr/bin/env python3
"""B19 / W17: literature, priority and faithful formalization records.

  b19_literature.py OUT_DIR

Inputs: the retrieval transcripts in evidence/literature_b19/retrieved/ (tool outputs kept
exactly as received, with the searches that found them) and the pinned Mathlib sources of
the formal workspace. Outputs: sources, claims, links (with Lean and executable checks),
ambiguity records, the adjudication queue and novelty reports for four Genesis results.
"""
import argparse
from fractions import Fraction
from itertools import combinations, product
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import literature as LIT  # noqa: E402
from genesis.formal_research import checker  # noqa: E402
from genesis.formal_research import triangle_theory as T  # noqa: E402
from genesis.formal_research import workspace as W  # noqa: E402
from genesis.invention import representations as R  # noqa: E402

RETRIEVED = ROOT / 'evidence' / 'literature_b19' / 'retrieved'
B18 = ROOT / 'evidence' / 'invention_b18'


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


# ---------------------------------------------------------------- small graphs

def random_graphs(seed, count, n_max=7, p=0.6):
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        n = rng.randint(3, n_max)
        out.append((n, tuple((u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p)))
    return out


def triangles(E):
    S = set(E)
    vs = sorted({x for e in E for x in e})
    return [((a, b), (b, c), (a, c)) for a, b, c in combinations(vs, 3)
            if (a, b) in S and (b, c) in S and (a, c) in S]


def tau(E):
    tri = triangles(E)
    for k in range(len(E) + 1):
        for C in combinations(E, k):
            c = set(C)
            if all(any(e in c for e in t) for t in tri):
                return k


def nu_star(E):
    """Fractional triangle packing number (LP, floating point; a check, not a certificate)."""
    tri = triangles(E)
    if not tri:
        return 0.0
    from scipy.optimize import linprog
    import numpy as np
    A = np.zeros((len(E), len(tri)))
    idx = {e: i for i, e in enumerate(E)}
    for j, t in enumerate(tri):
        for e in t:
            A[idx[e], j] = 1
    r = linprog(-np.ones(len(tri)), A_ub=A, b_ub=np.ones(len(E)), bounds=(0, None), method='highs')
    return -r.fun


def check_c1(graphs):
    """Our readings of τ and ν* (C1) against the quoted theorem and the B19 bound."""
    from genesis.discovery import obstruction as O
    from genesis.models import GraphTask
    bad = []
    for n, E in graphs:
        t, ns = tau(E), nu_star(E)
        opt = T.tf_opt(set(E))
        task = GraphTask(task_id='lit', domain='triangle_free_host_v1', n=n, edges=E, family='lit')
        cert, _ = O.lp_dual(task)
        bound = O.check_certificate(task, cert)['bound']
        ok = (len(E) - t == opt) and (ns <= t + 1e-9) and (t <= 2 * ns + 1e-9) and (bound >= opt) and \
             (Fraction(cert['objective']) >= len(E) - Fraction(ns).limit_denominator(10 ** 6) - Fraction(1, 10 ** 5))
        if not ok:
            bad.append({'n': n, 'edges': E, 'tau': t, 'nu_star': ns, 'opt': opt, 'bound': bound})
    return {'check': 'executable agreement on random small graphs', 'instances': len(graphs),
            'verdict': 'PASS' if not bad else 'FAIL', 'failures': bad[:5],
            'reading': 'τ = min edges meeting all triangles; ν* = LP triangle packing; checked: m − τ = largest '
                       'triangle-free subgraph, ν* ≤ τ ≤ 2ν* (the quoted theorem), and the B19 certificate '
                       'bound ≥ the optimum with objective = m − ν* up to rounding'}


def check_c3(graphs):
    cross = next(r for r in R.proposals() if r['id'] == 'cross_2')
    bad = []
    for n, E in graphs:
        best = max(len(R.decode(cross, dict(enumerate(c)), list(E))) for c in product(range(2), repeat=n))
        if 2 * best < len(E):
            bad.append({'n': n, 'edges': E, 'best_cut': best})
    return {'check': 'max over cross_2 encodings ≥ m/2, brute force', 'instances': len(graphs),
            'verdict': 'PASS' if not bad else 'FAIL', 'failures': bad[:5]}


def edge_subsets(n):
    K = [(u, v) for u in range(n) for v in range(u + 1, n)]
    return [frozenset(c) for k in range(len(K) + 1) for c in combinations(K, k)]


PREDICATES = {
    'triangle_free': lambda S: T.tf(S),
    'bipartite': lambda S: _bip(S),
    'c4_free': lambda S: R.c4free(S),
    'max_degree_le_1': lambda S: all(sum(x in e for e in S) <= 1 for x in range(6)),
    'non_empty': lambda S: len(S) > 0,
    'has_triangle': lambda S: not T.tf(S),
}


def _bip(S):
    from genesis.invention.worlds import bipartite
    return bipartite(set(S))


def down_closed(P, subsets):
    return all(P(B) for A in subsets if P(A) for B in subsets if B <= A)


def edge_vertex_closed(P, subsets):
    """Alon–Shapira reading on edge sets: closed under removing one edge, or one vertex
    (all its edges)."""
    for A in subsets:
        if not P(A):
            continue
        for e in A:
            if not P(A - {e}):
                return False
        for x in {v for e in A for v in e}:
            if not P(frozenset(e for e in A if x not in e)):
                return False
    return True


def check_c2(n=4):
    subsets = edge_subsets(n)
    rows = {k: {'rc_c0_down_closed': down_closed(P, subsets), 'alon_shapira_reading': edge_vertex_closed(P, subsets)}
            for k, P in PREDICATES.items()}
    agree = all(r['rc_c0_down_closed'] == r['alon_shapira_reading'] for r in rows.values())
    return {'check': f'both readings on every edge subset of K{n}', 'rows': rows,
            'verdict': 'PASS' if agree else 'FAIL'}


# ---------------------------------------------------------------- Lean links

LEAN_SPEC = '''import GTDefs
import HSDefs
import RCDefs
import Mathlib.Order.Defs.Unbundled
import Mathlib.Order.Monotone.Defs

namespace LitSpec

/-- The recovered concept is Mathlib's `Antitone` (order-theoretic name). -/
def rc_antitone : Prop := ∀ P : GT.Edges → Prop, RC.C0 P ↔ Antitone P

/-- The recovered concept says that {x | P x} is a lower set (down-set). -/
def rc_lower_set : Prop := ∀ P : GT.Edges → Prop, RC.C0 P ↔ IsLowerSet {x | P x}

end LitSpec
'''
LEAN_PROOF = '''import LitSpec

namespace LitProof

theorem rc_antitone : LitSpec.rc_antitone := fun _ =>
  ⟨fun h _ _ hab hb => h _ _ hab hb, fun h _ _ h01 hx => h h01 hx⟩

theorem rc_lower_set : LitSpec.rc_lower_set := fun _ =>
  ⟨fun h _ _ hba ha => h _ _ hba ha, fun h _ _ h01 hx => h h01 hx⟩

end LitProof
'''


def lean_links():
    pkg = json.loads((B18 / 'recovery' / 'concept' / 'package.json').read_text())
    mods = {m['name']: m for m in pkg['modules']}
    chain = [dict(mods[n], trusted=True) for n in ('GTDefs', 'HSDefs', 'RCDefs')] + [
        {'name': 'LitSpec', 'source': LEAN_SPEC, 'trusted': True},
        {'name': 'LitProof', 'source': LEAN_PROOF, 'trusted': False}]
    rc = checker.accept(chain, [{'spec': 'LitSpec.rc_antitone', 'proof': 'LitProof.rc_antitone'},
                                {'spec': 'LitSpec.rc_lower_set', 'proof': 'LitProof.rc_lower_set'}])
    out = {}
    for b in rc['bindings']:
        out[b['spec']] = {'check': 'Lean theorem accepted by formal_research.checker', 'verdict': b['status'],
                          'axioms': b.get('axioms'), 'proof': b['proof']}
    return out, {'modules': [(m['name'], m.get('result')) for m in rc['modules']],
                 'spec_sha256': LIT.sha(LEAN_SPEC), 'proof_sha256': LIT.sha(LEAN_PROOF)}


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    ws = W.locate()
    manifest = json.loads((ws / 'WORKSPACE_MANIFEST.json').read_text())
    rev = manifest['mathlib_rev']
    src_root = ws / 'src'

    # sources
    sources = {}
    for f in sorted(RETRIEVED.glob('S*.json')):
        s = LIT.from_retrieval(json.loads(f.read_text()))
        sources[s['source_id']] = s
    sources['L1'] = LIT.from_library('L1', src_root, 'Mathlib/Order/Monotone/Defs.lean', 67, 69, revision=rev)
    sources['L2'] = LIT.from_library('L2', src_root, 'Mathlib/Order/Defs/Unbundled.lean', 257, 263, revision=rev)
    searches = json.loads((RETRIEVED / 'searches.json').read_text())
    dump(out / 'sources.json', sources)

    # claims (exact quotes)
    C = {}
    C['C1'] = LIT.claim('C1', sources['S1'], 'Krivelevich who proved that $\\tau \\leq 2\\nu^*$',
                        statement='For every graph, τ ≤ 2ν*: the least number of edges meeting all triangles is at '
                                  'most twice the fractional triangle packing number (Krivelevich).',
                        assumptions=['finite simple graph'],
                        notation=['graph', 'set of edges meeting all triangles', 'edge-disjoint triangles'])
    C['C1def'] = LIT.claim('C1def', sources['S1'], 'minimum size $\\tau$ of a set of edges meeting all triangles',
                           statement='τ(G) is the minimum size of an edge set meeting every triangle.',
                           notation=['set of edges meeting all triangles'])
    C['C2'] = LIT.claim('C2', sources['S2'],
                        'A graph property is called monotone if it is closed under removal of edges and vertices.',
                        statement='A monotone graph property is one closed under removing edges and vertices.',
                        assumptions=['graph properties are isomorphism-invariant'],
                        notation=['monotone graph property'])
    C['C3'] = LIT.claim('C3', sources['S3'],
                        'every graph G = (V, E) with m edges contains a bipartite cut (V1, V2) spanning at least m/2 '
                        'edges.', statement='Every graph with m edges has a cut with at least m/2 edges.',
                        assumptions=['finite simple graph'], notation=['graph', 'edges m', 'bipartite cut'])
    C['C4'] = LIT.claim('C4', sources['S4'], 'all validated by the formal proof assistant language Lean.',
                        statement='The ETP results, including automated proofs, were validated in Lean.',
                        notation=['equational law'])
    C['C5'] = LIT.claim('C5', sources['S5'],
                        'We present Duper, a proof-producing theorem prover for Lean based on the superposition '
                        'calculus.', statement='Duper is a proof-producing superposition prover for Lean.')
    C['L1'] = LIT.claim('L1', sources['L1'], 'def Antitone (f : α → β) : Prop :=\n  ∀ ⦃a b⦄, a ≤ b → f b ≤ f a',
                        statement='Antitone f: a ≤ b implies f b ≤ f a.', notation=['antitone'])
    C['L2'] = LIT.claim('L2', sources['L2'], 'Also called down-set, downward-closed set.',
                        statement='A lower set contains every element below one of its members.',
                        notation=['lower set'])
    dump(out / 'claims.json', C)

    # checks and links
    graphs = random_graphs(20261025, 60)
    lean, lean_receipt = lean_links()
    c1, c2, c3 = check_c1(graphs), check_c2(), check_c3(graphs)
    links = [
        LIT.link(C['C1'], formal='B19 LP dual certificate bound: |S| ≤ ⌊m − ν*⌋ (genesis.discovery.obstruction)',
                 kind='CONTEXT', checks=[c1],
                 note='the B19 bound is weak LP duality for the triangle packing/cover relaxation; C1 is the '
                      'fractional packing literature it belongs to'),
        LIT.link(C['C2'], formal='RC.C0 (B18 recovered concept), restricted to isomorphism-invariant predicates',
                 kind='SPECIALIZATION', checks=[c2],
                 note='RC.C0 does not require isomorphism invariance, so a monotone graph property is the special '
                      'case of RC.C0 for invariant predicates'),
        LIT.link(C['L1'], formal='∀ P, RC.C0 P ↔ Antitone P', kind='EXACT', checks=[lean['LitSpec.rc_antitone']]),
        LIT.link(C['L2'], formal='∀ P, RC.C0 P ↔ IsLowerSet {x | P x}', kind='EXACT',
                 checks=[lean['LitSpec.rc_lower_set']]),
        LIT.link(C['C3'], formal='max over cross_2 encodings c of |decode(cross_2, c, H)| ≥ |H| / 2', kind='EXACT',
                 checks=[c3]),
        LIT.link(C['C4'], formal='B19 W16: E proof objects replayed step by step in Lean', kind='CONTEXT',
                 checks=[], note='prior work validating automated equational proofs in Lean'),
        LIT.link(C['C5'], formal='B19 W16: E proof objects replayed step by step in Lean', kind='CONTEXT',
                 checks=[], note='prior work on superposition proof reconstruction in Lean'),
    ]
    dump(out / 'links.json', {'links': links, 'lean_receipt': lean_receipt})

    # ambiguity records
    subsets = edge_subsets(4)
    amb = [
        LIT.ambiguity('"at least m/2" (C3)', {
            'real': lambda g: 2 * _maxcut(g) >= len(g[1]),
            'ceiling': lambda g: _maxcut(g) >= -(-len(g[1]) // 2)}, graphs[:30], used='real',
            describe=lambda g: {'n': g[0], 'edges': g[1]}),
        LIT.ambiguity('"monotone" (C2 vs Mathlib Monotone)', {
            'graph_theory_down_closed': lambda P: down_closed(PREDICATES[P], subsets),
            'order_theory_up_closed': lambda P: all(PREDICATES[P](B) for A in subsets if PREDICATES[P](A)
                                                    for B in subsets if A <= B)},
            sorted(PREDICATES), used='graph_theory_down_closed', describe=str),
        LIT.ambiguity('"C4-free" (Genesis domain)', {
            'no_4_cycle_subgraph': lambda S: R.c4free(S),
            'no_induced_4_cycle': lambda S: _no_induced_c4(S)}, subsets, used='no_4_cycle_subgraph',
            describe=lambda S: sorted(S)),
    ]
    dump(out / 'ambiguity.json', amb)

    queue = [
        LIT.adjudication('ADJ-1', 'Do the quotes from S1–S5 match the original documents verbatim?',
                         context='retrieved through a fetch tool that excerpts and may paraphrase (fidelity '
                                 'TOOL_SUMMARIZED); S4 and S5 were split or summarised by the tool',
                         options=['confirmed', 'corrected (give the exact text)', 'source unusable']),
        LIT.adjudication('ADJ-2', 'How should the m/2 cut bound be attributed?',
                         context='S3 calls it simple and gives no attribution; it is commonly credited to Erdős',
                         options=['folklore', 'Erdős (give the reference)', 'other']),
        LIT.adjudication('ADJ-3', 'Is the B18 recovered concept correctly reported as a rediscovery of lower '
                                  'sets / Antitone predicates / monotone graph properties?',
                         context='links L1 and L2 are Lean-checked; C2 is a specialization with a naming clash',
                         options=['yes', 'no (explain)']),
        LIT.adjudication('ADJ-4', 'Is the prior art for the B19 LP certificates adequately credited?',
                         context='the bound is LP duality for fractional triangle packing/cover (C1 context)',
                         options=['yes', 'add references (give them)']),
    ]
    dump(out / 'adjudication_queue.json', queue)

    lib = LIT.library_search(src_root, [r'def Antitone\b', r'def IsUpperSet\b', r'IsLowerSet', r'def CliqueFree\b',
                                        r'[Tt]riangle[- ]?[Ff]ree', r'[Tt]uza', r'[Mm]ax[- ]?[Cc]ut'], revision=rev)
    reports = [
        LIT.novelty('B18-RC.C0', description='the concept recovered by typed anti-unification in B18',
                    searches=['Q2'], sources_read=['S2', 'L1', 'L2'], library_searches=[lib[0], lib[1], lib[2]],
                    prior_art=[{'source': 'L1', 'relation': 'definitionally equal (Lean-checked link)'},
                               {'source': 'L2', 'relation': 'equivalent (Lean-checked link)'},
                               {'source': 'S2', 'relation': 'monotone graph property: special case'}],
                    scope='Mathlib at the pinned revision; one web search; one paper read'),
        LIT.novelty('B19-LP-certificates', description='exact LP dual certificates for the largest triangle-free '
                    'subgraph (W13)', searches=['Q1'], sources_read=['S1'], library_searches=[lib[4], lib[5]],
                    prior_art=[{'source': 'S1', 'relation': 'fractional triangle packing/cover; the bound is weak '
                                                            'LP duality for this relaxation'}],
                    scope='one web search; one abstract read; Mathlib at the pinned revision'),
        LIT.novelty('B18-cross_2', description='the cut representation (2 vertex classes, cross decoder)',
                    searches=['Q3'], sources_read=['S3'], library_searches=[lib[3], lib[6]],
                    prior_art=[{'source': 'S3', 'relation': 'the max-cut ≥ m/2 guarantee; bipartite subgraphs'}],
                    scope='one web search; one paper read'),
        LIT.novelty('B19-W16-lean-replay', description='step-by-step Lean replay of E proof objects (W16)',
                    searches=['Q4'], sources_read=['S4', 'S5'], library_searches=[],
                    prior_art=[{'source': 'S4', 'relation': 'automated equational proofs validated in Lean'},
                               {'source': 'S5', 'relation': 'superposition proof reconstruction in Lean'}],
                    scope='one web search; two abstracts read'),
    ]
    dump(out / 'novelty.json', {'reports': reports, 'searches': searches})
    summary = {
        'sources': {k: {'fidelity': v['fidelity'], 'quarantined': v['screen']['quarantined']} for k, v in sources.items()},
        'claims': {k: v['status'] for k, v in C.items()},
        'links': {l['claim_id']: [l['kind'], l['status']] for l in links},
        'lean_links': {k: v['verdict'] for k, v in lean.items()},
        'executable_checks': {'C1': c1['verdict'], 'C2': c2['verdict'], 'C3': c3['verdict']},
        'ambiguities_material': {x['phrase']: x['material_on_tested_range'] for x in amb},
        'adjudication_pending': len(queue),
        'novelty': {r['result_id']: r['conclusion'] for r in reports},
    }
    dump(out / 'summary.json', summary)
    print(json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False))
    ok = all(v['status'] == 'EXTRACTED' for v in C.values()) and all(v == 'CHECKED' for v in summary['lean_links'].values())
    return 0 if ok else 1


def _maxcut(g):
    n, E = g
    return max(sum((c[u] != c[v]) for u, v in E) for c in product(range(2), repeat=n))


def _no_induced_c4(S):
    S = set(S)
    vs = sorted({x for e in S for x in e})
    adj = lambda a, b: (min(a, b), max(a, b)) in S
    for q in combinations(vs, 4):
        for a, b, c, d in ((q[0], q[1], q[2], q[3]), (q[0], q[1], q[3], q[2]), (q[0], q[2], q[1], q[3])):
            if adj(a, b) and adj(b, c) and adj(c, d) and adj(d, a) and not adj(a, c) and not adj(b, d):
                return False
    return True


if __name__ == '__main__':
    sys.exit(main())
