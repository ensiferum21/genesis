"""The Architecture Graph (AG): a research workflow as typed, executable data (`docs/OMEGA_ARCHITECTURE_INVENTION.md`
§2; ARA-1).

An AG is JSON:

    {schema, library, nodes: {id: {role, op, params, searched, kernel}}, edges: [[src, dst, port], ...],
     budget: {total, split: {node: fraction}}, lineage: {parent, rewrite}}

* **Roles and operators** come from a library (`LIB`, versioned by its digest): each operator declares its input
  ports with their value types, its output type and its parameters. A port typed ['List', T] takes any number of
  edges, in edge order; any other port takes exactly one. Value types: `Column` (a sense's values over the task
  set, with its definition), `Features`, `Family` (a policy family), `Scheme` (an evaluator scheme), `Policy` (a
  fitted policy, JSON, applicable to new graphs).
* **The kernel is closed**: nodes marked `kernel: true` (the mandatory reattempt node `Output`, which hands the fitted
  policy to whoever judges it) may not be added, removed, re-wired or changed by a rewrite, nor may an edge into one.
  The judge and the sealed instances are never in an AG at all.
* **Budget**: `total` units for one execution. A node with a share in `split` may spend at most that fraction; the
  senses share the remainder. A rewrite may not raise `total` (conservation).
* **Execution** (`execute`) is a topological evaluation under the budget, deterministic given the AG, the seed and the
  view; every unit is charged to the node that spent it.
* **The diff classifier** (`classify`) labels a change TUNING (only parameters, searched sets or budget shares),
  STRUCTURAL (nodes, edges or operators) or LANGUAGE (the library itself), the largest that applies.

The AG's identity is the SHA-256 of its canonical JSON.
"""
import copy
import json
import math

from ..common import digest
from ..senses import graph as SG
from . import policies as PO

SCHEMA = 'genesis-architecture-graph-v1'
SENSE_UNIT = 0.01            # units per sense-tree node per instance
MAX_NEST = 3
FUSE_OPS = ('add_s', 'sub_s', 'mul_s', 'div_s')
FUSE_SCALES = (0.5, 1.0, 2.0, 3.0)
SEARCH_PARAMS = ('steps', 'step', 'k', 'start')
LIB = {
    'Sense': {
        'expr': {'in': {}, 'out': 'Column', 'params': ('expr',)},
        'fuse': {'in': {'a': 'Column', 'b': 'Column'}, 'out': 'Column', 'params': ('op', 'scale')},
    },
    'Features': {'stack': {'in': {'senses': ['List', 'Column']}, 'out': 'Features', 'params': ()}},
    'Policy': {f: {'in': {}, 'out': 'Family', 'params': {'global': (), 'threshold': ('n_cuts',), 'oblique': (),
                                                          'tree': (), 'knn': ('k',)}[f]} for f in PO.FAMILIES},
    'Evaluator': {s: {'in': {}, 'out': 'Scheme', 'params': ('repeats',)} for s in PO.SCHEMES},
    'Search': {s: {'in': {'features': 'Features', 'family': 'Family', 'scheme': 'Scheme'}, 'out': 'Policy',
                   'params': SEARCH_PARAMS} for s in PO.SEARCHES},
    'Output': {'reattempt': {'in': {'policy': 'Policy'}, 'out': 'Policy', 'params': ()}},
}
ORDER = {'Policy': PO.FAMILIES, 'Search': PO.SEARCHES, 'Evaluator': PO.SCHEMES}     # by strength or flexibility
LIFTABLE = {'threshold': ('n_cuts',), 'knn': ('k',)}


def library_version(lib=LIB):
    return digest({'schema': 'genesis-architecture-library-v1', 'lib': lib})[:16]


def node(role, op, params=None, searched=(), kernel=False):
    return {'role': role, 'op': op, 'params': dict(params or {}), 'searched': list(searched), 'kernel': bool(kernel)}


def make(nodes, edges, total, split=None, lineage=None, lib=LIB):
    return {'schema': SCHEMA, 'library': library_version(lib), 'nodes': copy.deepcopy(nodes),
            'edges': [list(e) for e in edges], 'budget': {'total': float(total), 'split': dict(split or {})},
            'lineage': dict(lineage or {})}


def ag_id(ag):
    return digest(ag)


def inputs_of(ag, nid):
    """{port: [src, ...]} in edge order."""
    out = {}
    for s, d, p in ag['edges']:
        if d == nid:
            out.setdefault(p, []).append(s)
    return out


def consumers(ag, nid):
    return [(d, p) for s, d, p in ag['edges'] if s == nid]


def topo(ag):
    """Node ids in a topological order (ties by id); raises ValueError on a cycle."""
    indeg = {n: 0 for n in ag['nodes']}
    for s, d, _ in ag['edges']:
        indeg[d] += 1
    ready = sorted(n for n, k in indeg.items() if k == 0)
    out = []
    while ready:
        n = ready.pop(0)
        out.append(n)
        for d, _ in consumers(ag, n):
            indeg[d] -= 1
            if indeg[d] == 0:
                ready.append(d)
                ready.sort()
    if len(out) != len(ag['nodes']):
        raise ValueError('the graph has a cycle')
    return out


# ------------------------------------------------------------------------------------------------ checks

def check(ag, lib=LIB):
    """The list of problems (empty when the AG is well formed and type correct)."""
    probs = []
    if not isinstance(ag, dict) or ag.get('schema') != SCHEMA:
        return ['not an architecture graph']
    if ag.get('library') != library_version(lib):
        probs.append('written against another library version')
    nodes = ag['nodes']
    for nid, nd in nodes.items():
        role, op = nd.get('role'), nd.get('op')
        if role not in lib or op not in lib[role]:
            probs.append(f'{nid}: unknown operator {role}.{op}')
            continue
        extra = set(nd['params']) - set(lib[role][op]['params'])
        if extra:
            probs.append(f'{nid}: unknown parameters {sorted(extra)}')
        bad = [p for p in nd.get('searched', []) if p not in LIFTABLE.get(op, ())]
        if bad:
            probs.append(f'{nid}: parameters {bad} cannot be searched')
        if role == 'Sense' and op == 'expr':
            why = SG.check(nd['params'].get('expr'))
            if why:
                probs.append(f'{nid}: {why}')
        if role == 'Sense' and op == 'fuse' and (nd['params'].get('op') not in FUSE_OPS or
                                                 nd['params'].get('scale') not in FUSE_SCALES):
            probs.append(f'{nid}: fusion operator outside the menu')
    for e in ag['edges']:
        if len(e) != 3 or e[0] not in nodes or e[1] not in nodes:
            probs.append(f'edge {e}: unknown node')
    if probs:
        return probs
    for nid, nd in nodes.items():
        spec = lib[nd['role']][nd['op']]
        got = inputs_of(ag, nid)
        for port in set(got) - set(spec['in']):
            probs.append(f'{nid}: no port {port!r}')
        for port, want in spec['in'].items():
            srcs = got.get(port, [])
            elem = want[1] if isinstance(want, list) else want
            if not isinstance(want, list) and len(srcs) != 1:
                probs.append(f'{nid}.{port}: takes exactly one input, has {len(srcs)}')
            if isinstance(want, list) and not srcs:
                probs.append(f'{nid}.{port}: needs at least one input')
            for s in srcs:
                out = lib[nodes[s]['role']][nodes[s]['op']]['out']
                if out != elem:
                    probs.append(f'{s} -> {nid}.{port}: {out} is not {elem}')
    try:
        topo(ag)
    except ValueError as e:
        probs.append(str(e))
    outs = [n for n, nd in nodes.items() if nd['role'] == 'Output']
    if len(outs) != 1 or not nodes[outs[0]]['kernel']:
        probs.append('exactly one kernel Output node (the mandatory reattempt)')
    b = ag['budget']
    if not (b['total'] > 0) or any(k not in nodes or not 0 <= v <= 1 for k, v in b['split'].items()) or \
            sum(b['split'].values()) > 1 + 1e-9:
        probs.append('budget shares must name nodes and sum to at most 1')
    for e in ag['edges']:
        for c in sense_fusions(ag, e):
            probs.append(c)
    return probs


def sense_fusions(ag, edge):
    """Problems with a fusion's inputs (both must be senses)."""
    s, d, p = edge
    nd = ag['nodes'][d]
    if nd['role'] == 'Sense' and nd['op'] == 'fuse' and ag['nodes'][s]['role'] != 'Sense':
        return [f'{d}: fuses only senses']
    return []


def kernel_violations(old, new):
    """Why `new` touches the kernel of `old` (empty when it does not)."""
    out = []
    ko = {n for n, nd in old['nodes'].items() if nd['kernel']}
    kn = {n for n, nd in new['nodes'].items() if nd['kernel']}
    if kn != ko:
        out.append('kernel nodes added or removed')
    for n in ko & kn:
        if old['nodes'][n] != new['nodes'][n]:
            out.append(f'kernel node {n} changed')
    eo = sorted(map(tuple, (e for e in old['edges'] if e[1] in ko or e[0] in ko)))
    en = sorted(map(tuple, (e for e in new['edges'] if e[1] in ko or e[0] in ko)))
    if eo != en:
        out.append('edges into or out of the kernel changed')
    return out


def admissible(old, new, lib=LIB):
    """None, or why a rewrite from `old` to `new` is refused before it runs."""
    probs = check(new, lib)
    if probs:
        return 'type check: ' + '; '.join(probs[:3])
    k = kernel_violations(old, new)
    if k:
        return 'kernel: ' + '; '.join(k)
    if new['budget']['total'] > old['budget']['total'] + 1e-9:
        return 'budget: a rewrite may not raise the total'
    return None


# ------------------------------------------------------------------------------------------------ classifier

def _structure(ag):
    return ({n: (nd['role'], nd['op'], nd['kernel']) for n, nd in ag['nodes'].items()},
            sorted(map(tuple, ag['edges'])))


def classify(old, new):
    """'NONE', 'TUNING', 'STRUCTURAL' or 'LANGUAGE' (the largest class that applies)."""
    if old.get('library') != new.get('library'):
        return 'LANGUAGE'
    if _structure(old) != _structure(new):
        return 'STRUCTURAL'
    tuning = any(old['nodes'][n]['params'] != new['nodes'][n]['params'] or
                 sorted(old['nodes'][n]['searched']) != sorted(new['nodes'][n]['searched'])
                 for n in old['nodes']) or old['budget'] != new['budget']
    return 'TUNING' if tuning else 'NONE'


# ------------------------------------------------------------------------------------------------ execution

class BudgetExceeded(Exception):
    pass


def sense_expr(ag, nid, memo=None):
    """A Sense node's expression (a fusion is built from its inputs' expressions)."""
    memo = {} if memo is None else memo
    if nid in memo:
        return memo[nid]
    nd = ag['nodes'][nid]
    if nd['op'] == 'expr':
        e = nd['params']['expr']
    else:
        ins = inputs_of(ag, nid)
        a, b = sense_expr(ag, ins['a'][0], memo), sense_expr(ag, ins['b'][0], memo)
        sc = nd['params']['scale']
        e = [nd['params']['op'], a, b if sc == 1.0 else ['mul_s', sc, b]]
    memo[nid] = e
    return e


def column(expr, graphs, cache=None):
    """A sense's values on the graphs (cached by expression and graph index)."""
    key = json.dumps(expr, sort_keys=True)
    out = []
    for i, g in enumerate(graphs):
        k = (key, id(g), i)
        if cache is not None and k in cache:
            out.append(cache[k])
            continue
        v = SG.evaluate(expr, g) if SG.check(expr) is None else 0.0
        if cache is not None:
            cache[k] = v
        out.append(v)
    return out


def execute(ag, view, split='dev_a', seed=0, depth=0, lib=LIB, sense_cache=None, draws=None):
    """Run the AG on the view's `split`: {policy, charges: {node: units}, units, id}. The fitted policy is JSON
    {family, fixed, senses, params} and can be applied to any graphs (`choose`)."""
    if depth > MAX_NEST:
        raise BudgetExceeded('nested architecture graphs deeper than MAX_NEST')
    probs = check(ag, lib)
    if probs:
        raise ValueError('ill-formed architecture graph: ' + '; '.join(probs[:3]))
    total, split_ = ag['budget']['total'], ag['budget']['split']
    caps = {n: f * total for n, f in split_.items()}
    meter = PO.Meter(caps)
    pool = total - sum(caps.values())
    graphs = view.graphs(split)
    vals, memo = {}, {}
    sense_spent = 0.0
    run_seed = int(digest({'ag': ag_id(ag), 'seed': seed})[:12], 16)
    for nid in topo(ag):
        nd = ag['nodes'][nid]
        role, op, params = nd['role'], nd['op'], nd['params']
        ins = inputs_of(ag, nid)
        if role == 'Sense':
            e = sense_expr(ag, nid, memo)
            cost = SG.size(e) * len(graphs) * SENSE_UNIT
            if nid not in caps:
                sense_spent += cost
                if sense_spent > pool + 1e-9:
                    raise BudgetExceeded(f'senses exceed their pool ({pool:g} units)')
            try:
                meter.charge(nid, cost)
            except PO.Exhausted:
                raise BudgetExceeded(f'{nid} exceeds its share')
            vals[nid] = {'expr': e, 'values': column(e, graphs, sense_cache)}
        elif role == 'Features':
            cols = [vals[s] for s in ins['senses']]
            vals[nid] = {'senses': [c['expr'] for c in cols],
                         'X': [[c['values'][i] for c in cols] for i in range(len(graphs))]}
        elif role == 'Policy':
            vals[nid] = {'family': op, 'fixed': dict(params), 'searched': list(nd['searched'])}
        elif role == 'Evaluator':
            vals[nid] = {'op': op, 'repeats': int(params.get('repeats', 1))}
        elif role == 'Search':
            feats, fam, sch = vals[ins['features'][0]], vals[ins['family'][0]], vals[ins['scheme'][0]]
            ev = PO.Evaluation(view, split, sch, meter, nid, draws)
            fixed = dict(fam['fixed'])
            for p in fam['searched']:
                fixed.pop(p, None)
            fitted = _fit_lifted(fam, fixed, feats['X'], view.K, ev, op, params, run_seed)
            vals[nid] = {'family': fam['family'], 'fixed': fitted[1], 'senses': feats['senses'],
                         'params': fitted[0]}
        elif role == 'Output':
            vals[nid] = vals[ins['policy'][0]]
    out = [n for n, nd in ag['nodes'].items() if nd['role'] == 'Output'][0]
    return {'policy': vals[out], 'charges': {k: round(v, 6) for k, v in sorted(meter.charges.items())},
            'units': round(meter.total, 6), 'id': ag_id(ag)}


def _fit_lifted(fam, fixed, X, K, ev, op, params, seed):
    """Fit, searching the lifted parameters too: (params, the fixed values used)."""
    family = fam['family']
    if family == 'threshold' and 'n_cuts' in fam['searched']:
        best = None
        for n in (1, 2, 3):
            f = dict(fixed, n_cuts=n)
            p = PO.fit(family, f, X, K, ev, op, params, seed + n)
            try:
                v = ev.value(PO.apply(family, p, X)) if p is not None else -math.inf
            except PO.Exhausted:                    # the search's share is spent: keep what was fitted so far
                if best is None:
                    best = (-math.inf, p, f)
                break
            if best is None or v > best[0]:
                best = (v, p, f)
        return best[1], best[2]
    if family == 'knn' and 'k' not in fam['searched']:
        fixed = dict(fixed)
        fixed.setdefault('k', 5)
    return PO.fit(family, fixed, X, K, ev, op, params, seed), fixed


def choose(policy, graphs, sense_cache=None):
    """The option a fitted policy chooses for each graph (its senses computed on the graphs)."""
    cols = [column(e, graphs, sense_cache) for e in policy['senses']]
    X = [[c[i] for c in cols] for i in range(len(graphs))]
    if policy['params'] is None:
        return [0] * len(graphs)
    return PO.apply(policy['family'], policy['params'], X)


def size_of(ag):
    """Nodes plus operators distinct from the defaults: the complexity tie-break's measure."""
    return len(ag['nodes']) + len(ag['edges'])


__all__ = ['SCHEMA', 'LIB', 'ORDER', 'LIFTABLE', 'FUSE_OPS', 'FUSE_SCALES', 'SENSE_UNIT', 'MAX_NEST',
           'library_version', 'node', 'make', 'ag_id', 'inputs_of', 'consumers', 'topo', 'check',
           'kernel_violations', 'admissible', 'classify', 'BudgetExceeded', 'sense_expr', 'column', 'execute',
           'choose', 'size_of']
