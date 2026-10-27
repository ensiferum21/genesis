"""The proposal engine: a generative grammar of typed rewrites with holes filled by synthesis
(`docs/OMEGA_ARCHITECTURE_INVENTION.md` §5, §6; ARA-1).

`generate(ag)` yields every applicable rewrite of every node, checked against types, in a canonical order. None names
a problem or a known fix:

| Operator | Precondition | Effect | Class |
|---|---|---|---|
| INSERT(Sense) | a Features node takes a list of senses | a new Sense node whose expression is a hole | STRUCTURAL |
| FUSE(a, b) | two senses feed the same Features port | a new Sense node op(a, scale * b); op and scale are holes | STRUCTURAL |
| GENERALISE(n) | the policy library has a more flexible family than n's | n becomes the next family | STRUCTURAL |
| SPECIALISE(n, s) | n is global and sense s is available | n becomes a threshold policy over s alone | STRUCTURAL |
| SUBSTITUTE(n, op') | op' has n's role and type | n's operator is swapped (any role but Sense, Features, Output) | STRUCTURAL |
| REALLOCATE(a -> b, f) | both nodes have budget shares | a fraction f of a's share moves to b | TUNING |
| LIFT(n.p) | p is a liftable constant of n | p joins the parameters the search varies | TUNING |
| RETRIEVE(Sense) | the archive holds senses from other environments | a new Sense node with the best archived sense | STRUCTURAL |

**Holes** are filled by bounded search on dev_a only (`Synthesis`): a sense expression by random senses and mutations
of the best (`senses.graph`), a fusion's operator and scale by enumeration of the menu, each scored by the 2-fold
cross-validated value of the best single-cut threshold policy on the exact dev_a table. The search's sense units are
charged. A synthesised sense whose values on a fixed probe set equal those of a sense already in the graph or in the
archive is a **rediscovery** (`fingerprint`), recorded as such.

**Limitation inversion** (`followups`): the rewrites of a realised variant that act on the nodes the last rewrite
introduced (a new sense can be fused, a new family generalised), so that chains grow to a bounded depth.
"""
import copy
import itertools
import random

from ..common import digest
from ..senses import graph as SG
from . import graph as G
from . import policies as PO

OPERATORS = ('INSERT', 'FUSE', 'GENERALISE', 'SPECIALISE', 'SUBSTITUTE', 'REALLOCATE', 'LIFT', 'RETRIEVE')
CLASS = {'INSERT': 'STRUCTURAL', 'FUSE': 'STRUCTURAL', 'GENERALISE': 'STRUCTURAL', 'SPECIALISE': 'STRUCTURAL',
         'SUBSTITUTE': 'STRUCTURAL', 'REALLOCATE': 'TUNING', 'LIFT': 'TUNING', 'RETRIEVE': 'STRUCTURAL'}
SENSE_RANDOM, SENSE_MUTATIONS = 60, 90
REALLOCATE_FRACTIONS = (0.25, 0.5)


def role_of(ag, rw):
    """The role a rewrite acts on (for ranking by the diagnosis's localisation)."""
    if rw['op'] in ('INSERT', 'FUSE', 'RETRIEVE'):
        return 'Sense'
    if rw['op'] == 'REALLOCATE':
        return ag['nodes'][rw['args']['to']]['role']
    return ag['nodes'][rw['target']]['role']


def generate(ag, archive=()):
    nodes = ag['nodes']
    out = []
    feats = sorted(n for n, nd in nodes.items() if nd['role'] == 'Features')
    for f in feats:
        out.append({'op': 'INSERT', 'target': f, 'args': {}})
        srcs = G.inputs_of(ag, f).get('senses', [])
        for a, b in itertools.permutations(srcs, 2):
            out.append({'op': 'FUSE', 'target': f, 'args': {'a': a, 'b': b}})
        if archive:
            out.append({'op': 'RETRIEVE', 'target': f, 'args': {}})
    for n in sorted(nodes):
        nd = nodes[n]
        if nd['kernel']:
            continue
        role, op = nd['role'], nd['op']
        if role == 'Policy':
            order = G.ORDER['Policy']
            nxt = order[order.index(op) + 1] if order.index(op) + 1 < len(order) else None
            if nxt:
                out.append({'op': 'GENERALISE', 'target': n, 'args': {'to': nxt}})
            if op == 'global':
                for s in sorted({s for f in feats for s in G.inputs_of(ag, f).get('senses', [])}):
                    out.append({'op': 'SPECIALISE', 'target': n, 'args': {'sense': s}})
            for p in G.LIFTABLE.get(op, ()):
                if p not in nd['searched']:
                    out.append({'op': 'LIFT', 'target': n, 'args': {'param': p}})
        if role in ('Policy', 'Search', 'Evaluator'):
            for alt in G.ORDER[role]:
                if alt != op and not (role == 'Policy' and alt == _next(op)):
                    out.append({'op': 'SUBSTITUTE', 'target': n, 'args': {'to': alt}})
    shares = sorted(ag['budget']['split'])
    for a, b in itertools.permutations(shares, 2):
        for f in REALLOCATE_FRACTIONS:
            out.append({'op': 'REALLOCATE', 'target': a, 'args': {'to': b, 'fraction': f}})
    return out


def _next(op):
    order = G.ORDER['Policy']
    i = order.index(op)
    return order[i + 1] if i + 1 < len(order) else None


def _fresh(ag, prefix):
    k = 1
    while f'{prefix}{k}' in ag['nodes']:
        k += 1
    return f'{prefix}{k}'


def apply(ag, rw, fill):
    """The rewritten AG with holes filled from `fill` (a dict the synthesis produced). Lineage names the parent
    and the rewrite."""
    new = copy.deepcopy(ag)
    nodes = new['nodes']
    op, t, a = rw['op'], rw['target'], rw['args']
    added = []
    if op in ('INSERT', 'RETRIEVE'):
        nid = _fresh(new, 's')
        nodes[nid] = G.node('Sense', 'expr', {'expr': fill['expr']})
        new['edges'].append([nid, t, 'senses'])
        added.append(nid)
    elif op == 'FUSE':
        nid = _fresh(new, 'f')
        nodes[nid] = G.node('Sense', 'fuse', {'op': fill['op'], 'scale': fill['scale']})
        new['edges'] += [[a['a'], nid, 'a'], [a['b'], nid, 'b'], [nid, t, 'senses']]
        added.append(nid)
    elif op in ('GENERALISE', 'SUBSTITUTE'):
        nd = nodes[t]
        keep = {k: v for k, v in nd['params'].items() if k in G.LIB[nd['role']][a['to']]['params']}
        if nd['role'] == 'Search':
            keep = {k: v for k, v in keep.items() if k != 'start'}     # a start belongs to the procedure it served
        nodes[t] = G.node(nd['role'], a['to'], keep, [p for p in nd['searched'] if p in G.LIFTABLE.get(a['to'], ())])
    elif op == 'SPECIALISE':
        nodes[t] = G.node('Policy', 'threshold', {'n_cuts': 1})
        fs = [d for d, p in G.consumers(new, a['sense']) if new['nodes'][d]['role'] == 'Features']
        for f in fs:
            new['edges'] = [e for e in new['edges'] if not (e[1] == f and e[2] == 'senses' and e[0] != a['sense'])]
        _prune(new)
    elif op == 'LIFT':
        nodes[t]['searched'] = sorted(set(nodes[t]['searched']) | {a['param']})
    elif op == 'REALLOCATE':
        sp = new['budget']['split']
        move = sp[t] * a['fraction']
        sp[t] = round(sp[t] - move, 9)
        sp[a['to']] = round(sp[a['to']] + move, 9)
    new['lineage'] = {'parent': G.ag_id(ag), 'rewrite': rw, 'fill': fill, 'added': added}
    return new


def _prune(ag):
    """Remove non-kernel nodes nothing consumes (senses left unused by a rewrite), and their shares."""
    while True:
        used = {s for s, d, p in ag['edges']}
        dead = [n for n, nd in ag['nodes'].items() if not nd['kernel'] and nd['role'] == 'Sense' and n not in used]
        if not dead:
            return
        for n in dead:
            del ag['nodes'][n]
            ag['budget']['split'].pop(n, None)
            ag['edges'] = [e for e in ag['edges'] if e[1] != n]


# ------------------------------------------------------------------------------------------------ synthesis

PROBES = None


def probes():
    """A fixed probe set of small graphs (Erdős–Rényi, seeded), for behavioural fingerprints."""
    global PROBES
    if PROBES is None:
        rng = random.Random('architecture-probes')
        out = []
        for k in range(8):
            n = 12 + 3 * k
            p = rng.uniform(0.1, 0.5)
            out.append({'n': n, 'edges': [[u, v, 1] for u in range(n) for v in range(u + 1, n) if rng.random() < p]})
        PROBES = out
    return PROBES


def fingerprint(expr):
    return digest([round(SG.evaluate(expr, g), 9) for g in probes()])


class Synthesis:
    """Fills holes on dev_a only: the exact dev_a table (from the diagnosis lab) and the view's dev_a graphs."""

    def __init__(self, view, lab, seed, archive=()):
        self.view, self.lab, self.seed = view, lab, seed
        self.archive = list(archive)
        self.graphs = view.graphs('dev_a')
        self.sense_units = 0.0
        self.log = []

    def values(self, expr):
        self.sense_units += SG.size(expr) * len(self.graphs) * G.SENSE_UNIT
        return G.column(expr, self.graphs, self.lab.sense_cache)

    def score_column(self, col):
        """The 2-fold cross-validated value of the best one-cut threshold policy on this feature."""
        T, K = self.lab.table_a, self.lab.K
        n = len(col)
        folds = [list(range(0, n, 2)), list(range(1, n, 2))]
        v = 0.0
        for k in (0, 1):
            tr, te = folds[k], folds[1 - k]
            X = [[col[i]] for i in tr]
            p = PO.fit('threshold', {'n_cuts': 1}, X, K, _T([T[i] for i in tr]), 'exhaustive', {}, self.seed)
            ch = PO.apply('threshold', p, [[col[i]] for i in te])
            v += sum(T[i][c] for i, c in zip(te, ch))
        return v / n

    def sense(self, existing=()):
        """A sense expression by random senses then mutations of the best; returns (expr, score, rediscovery)."""
        rng = random.Random(f'sense|{self.seed}|{len(existing)}')
        seen = {fingerprint(e) for e in existing} | {a['fingerprint'] for a in self.archive}
        best = None
        tried = {}
        for k in range(SENSE_RANDOM + SENSE_MUTATIONS):
            e = SG.random_sense(rng) if (best is None or k < SENSE_RANDOM) else SG.mutate(best[1], rng)
            key = repr(e)
            if key in tried:
                continue
            s = self.score_column(self.values(e))
            tried[key] = s
            if best is None or s > best[0] + 1e-12:
                best = (s, e)
        fp = fingerprint(best[1])
        rec = {'expr': best[1], 'score': best[0], 'tried': len(tried), 'rediscovery': fp in seen, 'fingerprint': fp}
        self.log.append(rec)
        return rec

    def fusion(self, a_expr, b_expr):
        best = None
        for op in G.FUSE_OPS:
            for sc in G.FUSE_SCALES:
                e = [op, a_expr, b_expr if sc == 1.0 else ['mul_s', sc, b_expr]]
                if SG.check(e) is not None:
                    continue
                s = self.score_column(self.values(e))
                if best is None or s > best[0] + 1e-12:
                    best = (s, op, sc, e)
        if best is None:
            return None
        rec = {'op': best[1], 'scale': best[2], 'score': best[0], 'fingerprint': fingerprint(best[3])}
        self.log.append(rec)
        return rec

    def retrieve(self):
        best = None
        for a in self.archive:
            s = self.score_column(self.values(a['expr']))
            if best is None or s > best[0] + 1e-12:
                best = (s, a)
        return None if best is None else {'expr': best[1]['expr'], 'score': best[0], 'source': best[1].get('source')}

    def fill(self, ag, rw):
        """The hole values for a rewrite (None when a hole cannot be filled)."""
        op = rw['op']
        if op == 'INSERT':
            return self.sense([G.sense_expr(ag, n) for n, nd in ag['nodes'].items() if nd['role'] == 'Sense'])
        if op == 'FUSE':
            return self.fusion(G.sense_expr(ag, rw['args']['a']), G.sense_expr(ag, rw['args']['b']))
        if op == 'RETRIEVE':
            return self.retrieve()
        return {}


class _T:
    def __init__(self, t):
        self.t, self.n = t, len(t)

    def value(self, assign, idx=None):
        idx = list(range(self.n) if idx is None else idx)
        return sum(self.t[i][assign[i]] for i in idx) / max(1, len(idx))

    def table(self, K):
        return self.t


def realise(ag, rw, synth):
    """(variant AG, fill) or (None, why): holes filled, then admitted only if type-correct, kernel-closed and
    within budget."""
    fill = synth.fill(ag, rw)
    if fill is None:
        return None, 'a hole could not be filled'
    new = apply(ag, rw, fill)
    why = G.admissible(ag, new)
    return (None, why) if why else (new, fill)


def followups(variant, rw, archive=()):
    """Rewrites of the variant acting on what the last rewrite introduced (bounded limitation inversion)."""
    new_nodes = set(variant['lineage'].get('added', []))
    out = []
    for r in generate(variant, archive):
        if r['op'] == 'FUSE' and ({r['args']['a'], r['args']['b']} & new_nodes):
            out.append(r)
        elif r['op'] in ('GENERALISE', 'LIFT') and rw['op'] in ('GENERALISE', 'SPECIALISE', 'SUBSTITUTE') and \
                r['target'] == rw['target']:
            out.append(r)
    return out


__all__ = ['OPERATORS', 'CLASS', 'role_of', 'generate', 'apply', 'probes', 'fingerprint', 'Synthesis', 'realise',
           'followups']
