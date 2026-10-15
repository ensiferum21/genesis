"""Quotient representations with a proved transport condition (handoff s15.3, W10; B20_R26).

The relational decoders of B20_R17/R19 (``relations``) fix a class relation R when the decoder is
generated, and search only over vertex encodings. They were retired as a utility source after two
attempts. This module is the next family. Here the *pattern* is part of the encoding and is chosen
per host:

    lift q Q H = { (u, v) ∈ H : (q u, q v) ∈ Q },      q : ℕ → ℕ (a partition into blocks),
                                                        Q ⊆ ℕ × ℕ (the pattern on the blocks).

**Transport condition (Lean, proved once for every q, Q and H).** If the pattern is triangle-free
in the repository's sense, ``GT.TriangleFree Q`` (no (a,b), (b,c), (a,c) in Q), then so is its lift:

    GT.TriangleFree Q → GT.TriangleFree (QT.lift q Q H),       and     QT.lift q Q H ⊆ H.

A lifted triangle (x,y), (y,z), (x,z) maps to (qx,qy), (qy,qz), (qx,qz) ∈ Q, which the condition
forbids. One parametric theorem replaces the per-decoder soundness theorems of the relational
family, and it covers every block count.

**What a host's representation is.** For a host, the method (``quotient_and_repair``) alternates
two steps:
  * the exact best pattern for the current partition. This is a maximum-weight transitive-triple-free
    relation on K blocks, found by branch and bound (``best_pattern``), where the weight of (a, b)
    counts host edges (u, v), u < v, from block a to block b;
  * vertex moves that improve the lift under that pattern.
Then the domain checker's greedy completion restores what the lift dropped, including edges
inside blocks. The domain checker validates every witness.

**Against the menu.** A fixed pattern is a relational decoder, so every menu decoder and every
generated relational decoder is the special case "Q fixed in advance". This family is new only in
that Q is optimised per host and the block count is larger (K ≤ 6). Whether that repays its cost
is what the preregistered study measures. The family is a builder-designed search space. What is
machine-generated is each host's quotient (partition and pattern), certified by the transport
theorem.
"""
import random
import time

from . import representations as RP

MODULE = 'QTDefs'
ORIGIN = 'generated:quotient-pattern-v1'
MAX_BLOCKS = 6
FAMILY = 'quotient'


# ---------------------------------------------------------------- exact pattern on the blocks

def transitive_triple(Q):
    """A triple (a,b), (b,c), (a,c) in Q, or None (the GT.TriangleFree pattern)."""
    Q = set(Q)
    for a, b in Q:
        for b2, c in Q:
            if b2 == b and (a, c) in Q:
                return (a, b), (b, c), (a, c)
    return None


def pattern_ok(Q):
    return transitive_triple(Q) is None


def best_pattern(W, K):
    """Exact maximum of Σ_{(a,b) ∈ Q} W[a][b] over relations Q on K blocks with no transitive
    triple. A loop (a, a) is a triple by itself, so Q is irreflexive. Depth-first branch and
    bound, arcs in decreasing weight. Returns (value, sorted arcs)."""
    arcs = sorted(((W[a][b], a, b) for a in range(K) for b in range(K) if a != b and W[a][b] > 0), reverse=True)
    suffix = [0] * (len(arcs) + 1)
    for i in range(len(arcs) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + arcs[i][0]
    out = set()
    inn = [set() for _ in range(K)]       # inn[b] = {a : (a, b) ∈ Q}
    outs = [set() for _ in range(K)]      # outs[a] = {b : (a, b) ∈ Q}
    best = [0, []]

    def creates(a, b):
        # (a,b) as the first arc: (b, c) and (a, c); as the second: (x, a) and (x, b); as the third: (a, y), (y, b)
        return bool(outs[b] & outs[a]) or bool(inn[a] & inn[b]) or bool(outs[a] & inn[b])

    def dfs(i, value):
        if value > best[0]:
            best[0], best[1] = value, sorted(out)
        if i == len(arcs) or value + suffix[i] <= best[0]:
            return
        w, a, b = arcs[i]
        if not creates(a, b):
            out.add((a, b)); outs[a].add(b); inn[b].add(a)
            dfs(i + 1, value + w)
            out.discard((a, b)); outs[a].discard(b); inn[b].discard(a)
        dfs(i + 1, value)
    dfs(0, 0)
    return best[0], best[1]


def block_weights(q, E, K):
    W = [[0] * K for _ in range(K)]
    for u, v in E:
        W[q[u]][q[v]] += 1
    return W


def lift(q, Q, H):
    Q = set(map(tuple, Q))
    return frozenset(e for e in H if (q.get(e[0], 0), q.get(e[1], 0)) in Q)


# ---------------------------------------------------------------- the method

def quotient_and_repair(n, edges, K, motif_ok, *, cpu_seconds, seed=0):
    """Alternate the exact pattern and vertex moves from random partitions until the CPU budget is
    spent; complete each local optimum greedily under the domain predicate. `motif_ok(S, e)` says
    whether adding e to S keeps S valid."""
    if not 2 <= K <= MAX_BLOCKS:
        raise RP.ProposalError(f'block count must be in [2, {MAX_BLOCKS}]')
    rng = random.Random(seed)
    E = [tuple(e) for e in edges]
    out_nb = {v: [] for v in range(n)}
    in_nb = {v: [] for v in range(n)}
    for u, v in E:
        out_nb[u].append(v); in_nb[v].append(u)
    best, rounds, patterns = None, 0, 0
    end = time.process_time() + cpu_seconds
    while True:
        rounds += 1
        q = {v: rng.randrange(K) for v in range(n)}
        value, Q = best_pattern(block_weights(q, E, K), K)
        patterns += 1
        while True:
            Qs = set(map(tuple, Q))
            moved = False
            for v in rng.sample(range(n), n):
                def gain(b):
                    return sum((b, q[w]) in Qs for w in out_nb[v]) + sum((q[w], b) in Qs for w in in_nb[v])
                cur = gain(q[v])
                alt = max(range(K), key=lambda b: (gain(b), b == q[v]))
                if gain(alt) > cur:
                    q[v] = alt
                    moved = True
            new_value, new_Q = best_pattern(block_weights(q, E, K), K)
            patterns += 1
            if not moved and new_value <= value:
                break
            if new_value < value:                   # cannot happen: Q is still feasible; kept as a guard
                break
            value, Q = new_value, new_Q
            if time.process_time() >= end:
                break
        S = set(lift(q, Q, E))
        decoded = len(S)
        rest = [e for e in E if e not in S]
        rng.shuffle(rest)
        for e in rest:
            if motif_ok(S, e):
                S.add(e)
        if best is None or len(S) > len(best['witness']):
            best = {'witness': sorted(S), 'partition': dict(q), 'pattern': [list(p) for p in Q],
                    'decoded_before_repair': decoded}
        if time.process_time() >= end:
            break
    return dict(best, value=len(best['witness']), rounds=rounds, patterns_solved=patterns, blocks=K)


def proposal(K):
    """Typed record for the quotient family at block count K (the shape `representations` uses)."""
    if type(K) is not int or not 2 <= K <= MAX_BLOCKS:
        raise RP.ProposalError(f'block count K must be an integer in [2, {MAX_BLOCKS}]')
    return {'id': f'quotient_{K}', 'family': FAMILY, 'k': K, 'lean_name': 'QT.lift', 'origin': ORIGIN,
            'encoder': {'type': 'ℕ → ℕ (blocks below K) and a pattern Q ⊆ ℕ × ℕ',
                        'space': f'{K}^n partitions × the transitive-triple-free relations on {K} blocks'},
            'semantics': 'QT.lift q Q H = H.filter (fun e => (q e.1, q e.2) ∈ Q)',
            'retained': 'host edges (u, v), u < v, whose block pair is in the per-host optimal pattern',
            'lost': 'edges inside a block and edges between blocks the pattern leaves out (restored only by repair)',
            'cost': {'decode': 'O(|H|)', 'pattern': f'branch and bound over ≤ {K * (K - 1)} arcs per partition'},
            'failure_conditions': ['local search over partitions gives no optimality guarantee',
                                   'branch and bound grows exponentially with the block count (bounded by K ≤ '
                                   f'{MAX_BLOCKS})',
                                   'reads the host orientation, like the relational decoders'],
            'kind': 'conservative-definition', 'transport': 'QT.lift_sound (one theorem for all q, Q, H)'}


SOURCE = f'''import {RP.DEFS_MODULE}

namespace QT

/-- Quotient lift: the host edges whose block pair lies in the pattern `Q` (B20_R26, {ORIGIN}). -/
def lift (q : ℕ → ℕ) (Q : GT.Edges) (H : GT.Edges) : GT.Edges := H.filter (fun e => (q e.1, q e.2) ∈ Q)

end QT
'''


def lean_value(b, x):
    t = b['type']
    if t == 'GT.Edges':
        return RP.lean_value(b, x)
    if t == 'ℕ → ℕ':
        n = max(x) + 1 if x else 1
        table = ', '.join(str(x.get(v, 0)) for v in range(n))
        return f'(fun v => ([{table}] : List ℕ).getD v 0)'
    raise ValueError(f'no Lean printer for {t}')


def conjectures():
    """Image and the transport condition, as Lean statements with Python models for the screen."""
    tf = RP.DOMAINS['triangle_free_host_v1']['model']

    def sampler(rng):
        k = rng.randrange(2, 4)
        return {'q': {v: rng.randrange(k) for v in range(4)},
                'Q': frozenset((a, b) for a in range(k) for b in range(k) if rng.random() < 0.4),
                'H': RP._sample_edges(rng)}
    q = {'name': 'q', 'type': 'ℕ → ℕ'}
    Qb = {'name': 'Q', 'type': 'GT.Edges'}
    H = {'name': 'H', 'type': 'GT.Edges'}
    hyp = {'name': 'hQ', 'hyp': True, 'lean': 'GT.TriangleFree Q', 'model': lambda v: tf(v['Q'])}
    mk = lambda cid, binders, concl, model, role: dict(RP._conj(cid, binders, concl, model, sampler, ORIGIN, role,
                                                                 'quotient'), lean_value=lean_value)
    return [mk('quotient_image', [q, Qb, H], 'QT.lift q Q H ⊆ H',
               lambda v: lift(v['q'], v['Q'], v['H']) <= v['H'], 'image'),
            mk('quotient_sound_tf', [q, Qb, H, hyp], 'GT.TriangleFree (QT.lift q Q H)',
               lambda v: tf(lift(v['q'], v['Q'], v['H'])), 'soundness')]


def recipes(conj, library):
    """Builder-written recipes (named in every receipt)."""
    role = conj.get('role')
    if role == 'image':
        return [('filter-subset', 'intro q Q H\nunfold QT.lift\nexact Finset.filter_subset _ _'),
                ('filter-subset-simp', 'intro q Q H\nsimp_all [QT.lift]')]
    if role == 'soundness':
        head = ['intro q Q H hQ', 'unfold GT.TriangleFree QT.lift',
                "rintro ⟨a, b⟩ he ⟨b', d⟩ hf ⟨a', d'⟩ hg ⟨h1, h2, h3⟩",
                'simp only [Finset.mem_filter] at he hf hg', 'simp only at h1 h2 h3', 'subst h1 h2 h3']
        return [('pattern-triple', '\n'.join(head + ['exact hQ _ he.2 _ hf.2 _ hg.2 ⟨rfl, rfl, rfl⟩'])),
                ('pattern-triple-unfold', '\n'.join(head + ['unfold GT.TriangleFree at hQ',
                                                            'exact hQ _ he.2 _ hf.2 _ hg.2 ⟨rfl, rfl, rfl⟩']))]
    return []


__all__ = ['best_pattern', 'pattern_ok', 'transitive_triple', 'block_weights', 'lift', 'quotient_and_repair',
           'proposal', 'conjectures', 'recipes', 'SOURCE', 'MODULE', 'MAX_BLOCKS', 'ORIGIN']
