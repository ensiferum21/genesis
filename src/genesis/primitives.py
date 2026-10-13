"""Derived primitives for the representation language (W22, handoff s21.1-21.2).

A *derived primitive* is a named, typed operation of MRDL (``mrdl.py``) whose meaning is its
*reference expansion*: an MRDL expression over the already accepted operations. Because every
use can be expanded, a derived primitive never widens the trusted base. A contract records the
name, version, parameter and output types, precondition, semantics, the expansion (data only), the
effects (must be none), failure modes, resource bounds, the optional native implementation and its
source digest, and the hypothesis about downstream benefit.

Rules (handoff s21.1-21.2):

* A proposer (person, trace miner or model) supplies *data*: a contract whose expansion is a
  template. It cannot supply code. A native implementation can only be named from ``NATIVE``,
  which is trusted code in this module, and its source digest is pinned in the contract.
* Native evaluation is an optimization. Conformance tests against the expansion catch bugs but are
  not a semantic proof, so anything that licenses a claim uses the expansion
  (``licensing_value``). Proof-bearing results still go to the independent checkers.
* Contracts are versioned. A registry has an identity (``Registry.identity``) that belongs in
  SystemVersion.cognitive_kernel (``cognitive_kernel``); a program record pins the registry
  identity it ran under, and replay uses that historical registry, so old programs keep their
  semantics. A migration adapter maps an old primitive version to an expression of the new
  registry and must agree with the old semantics on a corpus before it is recorded.
* Naming a macro "primitive" is not a capability gain. ``compare`` measures, on fresh DEV hosts,
  the incumbent language (the expanded expression), the equivalent macro (same expansion, shorter
  description, same cost) and the native primitive (with its conformance cost charged). The
  verdict rule is fixed in ``VERDICT_RULE``.

Expansion templates (all data):
  {'kind': 'fixed', 'expr': <MRDL with {'$param': name} placeholders for vertex parameters>}
  {'kind': 'sum_vertices', 'term': <MRDL with '$v'>}     sum over v < n (balanced Add tree)
  {'kind': 'sum_pairs', 'term': <MRDL with '$u','$v'>}   sum over u < v < n
  {'kind': 'scaled', 'num': int, 'den': int, 'of': <template>}
A template may use other derived primitives by name; cycles and depth are refused.
"""
from fractions import Fraction
import hashlib
import inspect
import time

from .common import canonical, digest
from . import mrdl

SCHEMA = 'genesis-primitive-contract-v1'
REGISTRY_SCHEMA = 'genesis-primitive-registry-v1'
STATUSES = ('EXPERIMENTAL', 'CONFORMANT', 'USEFUL', 'NOT_A_CAPABILITY_GAIN', 'REJECTED', 'RETIRED')
PARAM_TYPES = ('vertex',)
OUTPUT_TYPES = ('int', 'rational')
CONTRACT_FIELDS = frozenset({'schema', 'name', 'version', 'params', 'output', 'precondition', 'semantics', 'expansion',
                             'effects', 'failure_modes', 'resource_bounds', 'native', 'implementation_sha256',
                             'hypothesis', 'proposer'})
MAX_TEMPLATE_DEPTH = 6
VERDICT_RULE = ('USEFUL iff the native implementation agrees with the expansion on every comparison host and its '
                'total CPU, including the conformance run, is at most half of the expanded expression\'s; '
                'NOT_A_CAPABILITY_GAIN if it agrees but saves less; REJECTED if they ever differ or the expansion '
                'cannot be evaluated within the language\'s bounds where the native one can.')


class PrimitiveError(ValueError):
    pass


# ---------------------------------------------------------------- trusted native implementations

def _edge_count(task, p):
    return len(task.edges)


def _triangle_count(task, p):
    a = mrdl.neighbors(task.n, task.edges)
    return sum((a[u] & a[v]).bit_count() for u, v in task.edges) // 3


def _sum_degree_squares(task, p):
    return sum(x.bit_count() ** 2 for x in mrdl.neighbors(task.n, task.edges))


def _pair_codegree_falling2(task, p):
    a = mrdl.neighbors(task.n, task.edges)
    return sum((lambda c: c * (c - 1))((a[u] & a[v]).bit_count())
               for u in range(task.n) for v in range(u + 1, task.n))


NATIVE = {'edge_count_v1': _edge_count, 'triangle_count_v1': _triangle_count,
          'sum_degree_squares_v1': _sum_degree_squares, 'pair_codegree_falling2_v1': _pair_codegree_falling2}


def native_sha256(name):
    return hashlib.sha256(inspect.getsource(NATIVE[name]).encode()).hexdigest()


# ---------------------------------------------------------------- contracts and registries

def contract(name, *, expansion, output='int', params=None, precondition='any host', semantics, failure_modes=(),
             resource_bounds=None, native=None, hypothesis, proposer='builder', version=1):
    c = {'schema': SCHEMA, 'name': name, 'version': version, 'params': dict(params or {}), 'output': output,
         'precondition': precondition, 'semantics': semantics, 'expansion': expansion, 'effects': [],
         'failure_modes': list(failure_modes), 'resource_bounds': dict(resource_bounds or {'max_nodes': 256}),
         'native': native, 'implementation_sha256': native_sha256(native) if native else None,
         'hypothesis': hypothesis, 'proposer': proposer}
    return c


def contract_problems(c, known):
    """Why contract ``c`` cannot join a registry whose other primitives are ``known`` (name -> contract)."""
    out = []
    if not isinstance(c, dict) or set(c) != CONTRACT_FIELDS or c.get('schema') != SCHEMA:
        return ['not a primitive contract (exact field set)']
    if not isinstance(c['name'], str) or not c['name'].isidentifier() or c['name'] in mrdl.OPS:
        out.append('name must be a new identifier (not an existing MRDL operation)')
    if type(c['version']) is not int or c['version'] < 1:
        out.append('version must be a positive integer')
    if c['effects']:
        out.append(f'derived primitives have no effects (declared {c["effects"]})')
    if any(t not in PARAM_TYPES for t in c['params'].values()) or not all(isinstance(k, str) for k in c['params']):
        out.append(f'parameter types must be among {PARAM_TYPES}')
    if c['output'] not in OUTPUT_TYPES:
        out.append(f'output must be one of {OUTPUT_TYPES}')
    if c['native'] is not None:
        if c['native'] not in NATIVE:
            out.append('a native implementation can only be named from the trusted table (proposers supply data, not code)')
        elif c['implementation_sha256'] != native_sha256(c['native']):
            out.append('native implementation source differs from the pinned digest')
    elif c['implementation_sha256'] is not None:
        out.append('implementation digest without a native implementation')
    rb = c['resource_bounds']
    if not isinstance(rb, dict) or set(rb) != {'max_nodes'} or type(rb['max_nodes']) is not int \
            or not 1 <= rb['max_nodes'] <= 256:
        out.append('resource_bounds must be {max_nodes: 1..256} (the language cap)')
    try:
        _template_refs(c['expansion'], set(c['params']), 0)
    except PrimitiveError as exc:
        out.append(str(exc))
    else:
        for ref in sorted(_template_refs(c['expansion'], set(c['params']), 0)):
            if ref not in known and ref != c['name']:
                out.append(f'expansion uses unknown operation {ref}')
        if _reaches(c['name'], c['expansion'], known):
            out.append('expansion is recursive (reaches itself)')
    for k in ('semantics', 'precondition', 'hypothesis', 'proposer'):
        if not isinstance(c[k], str) or not c[k].strip():
            out.append(f'{k} must be stated')
    return out


def _template_refs(t, params, depth):
    """Derived-primitive names a template uses; raises on malformed templates."""
    if depth > MAX_TEMPLATE_DEPTH:
        raise PrimitiveError('template nesting too deep')
    if not isinstance(t, dict) or t.get('kind') not in ('fixed', 'sum_vertices', 'sum_pairs', 'scaled'):
        raise PrimitiveError('expansion template kind must be fixed, sum_vertices, sum_pairs or scaled')
    if t['kind'] == 'scaled':
        if set(t) != {'kind', 'num', 'den', 'of'} or type(t['num']) is not int or type(t['den']) is not int or not t['den']:
            raise PrimitiveError('scaled template needs integer num/den (den != 0) and of')
        return _template_refs(t['of'], params, depth + 1)
    key = 'expr' if t['kind'] == 'fixed' else 'term'
    if set(t) != {'kind', key}:
        raise PrimitiveError(f'{t["kind"]} template has exactly the field {key}')
    bound = params | ({'$v'} if t['kind'] == 'sum_vertices' else {'$u', '$v'} if t['kind'] == 'sum_pairs' else set())
    refs = set()

    def walk(e, d):
        if d > 16:
            raise PrimitiveError('expression too deep')
        if not isinstance(e, dict) or set(e) - {'op', 'args', 'params'} or not isinstance(e.get('op'), str):
            raise PrimitiveError('expression schema')
        if e['op'] not in mrdl.OPS:
            refs.add(e['op'])
        for v in (e.get('params') or {}).values():
            if isinstance(v, dict):
                if set(v) != {'$param'} or v['$param'] not in bound:
                    raise PrimitiveError(f'unbound placeholder {v}')
            elif isinstance(v, str):
                if v not in bound:
                    raise PrimitiveError(f'unbound placeholder {v!r}')
        for a in e.get('args') or []:
            walk(a, d + 1)
    walk(t[key], 0)
    return refs


def _reaches(name, template, known, seen=None):
    seen = set() if seen is None else seen
    for ref in _template_refs(template, _all_names(template), 0):
        if ref == name:
            return True
        if ref in known and ref not in seen:
            seen.add(ref)
            if _reaches(name, known[ref]['expansion'], known, seen):
                return True
    return False


def _all_names(template):
    out = set()

    def walk(t):
        if t['kind'] == 'scaled':
            return walk(t['of'])
        key = 'expr' if t['kind'] == 'fixed' else 'term'

        def w(e):
            for v in (e.get('params') or {}).values():
                if isinstance(v, dict):
                    out.add(v['$param'])
                elif isinstance(v, str):
                    out.add(v)
            for a in e.get('args') or []:
                w(a)
        w(t[key])
    walk(template)
    return out


class Registry:
    """An ordered set of derived-primitive contracts with an identity; earlier identities are kept."""

    def __init__(self, contracts=(), *, history=()):
        self.contracts = {}
        for c in contracts:
            why = contract_problems(c, self.contracts)
            if why:
                raise PrimitiveError(f'{c.get("name") if isinstance(c, dict) else c}: ' + '; '.join(why))
            if c['name'] in self.contracts:
                raise PrimitiveError(f'{c["name"]} defined twice')
            self.contracts[c['name']] = c
        self.history = list(history)

    def identity(self):
        return digest({'schema': REGISTRY_SCHEMA, 'contracts': [self.contracts[k] for k in sorted(self.contracts)]})

    def record(self):
        return {'schema': REGISTRY_SCHEMA, 'identity': self.identity(),
                'contracts': [self.contracts[k] for k in sorted(self.contracts)], 'history': self.history}

    def revise(self, contracts, *, reason):
        """A new registry; this one's identity joins the history. Same-name contracts must bump version."""
        new = {c['name']: c for c in contracts}
        for k, c in new.items():
            old = self.contracts.get(k)
            if old is not None and old != c and c['version'] <= old['version']:
                raise PrimitiveError(f'{k}: a changed contract needs a higher version')
        merged = dict(self.contracts, **new)
        entry = {'identity': self.identity(), 'reason': reason}
        return Registry([merged[k] for k in _topo(merged)], history=self.history + [entry])


def _topo(contracts):
    order, done = [], set()

    def visit(k, stack=()):
        if k in done:
            return
        if k in stack:
            raise PrimitiveError('recursive registry')
        for ref in _template_refs(contracts[k]['expansion'], set(contracts[k]['params']), 0):
            if ref in contracts:
                visit(ref, stack + (k,))
        done.add(k)
        order.append(k)
    for k in sorted(contracts):
        visit(k)
    return order


def cognitive_kernel(registry):
    """The digest that belongs in SystemVersion.cognitive_kernel: IR contracts, MRDL operations and
    caps, and the derived-primitive registry."""
    from .ir import CONTRACTS
    return digest({'contracts': {k: [list(v[0]), v[1]] for k, v in CONTRACTS.items()},
                   'mrdl_ops': sorted(mrdl.OPS), 'mrdl_caps': {'nodes': 256, 'depth': 16, 'int_bits': 1024},
                   'derived_primitives': registry.identity()})


# ---------------------------------------------------------------- expansion and evaluation

def _subst(e, binding):
    out = {'op': e['op']}
    if 'params' in e:
        out['params'] = {k: (binding[v['$param']] if isinstance(v, dict) else binding[v] if isinstance(v, str) else v)
                         for k, v in e['params'].items()}
    if 'args' in e:
        out['args'] = [_subst(a, binding) for a in e['args']]
    return out


def _balanced_add(terms):
    if not terms:
        return {'op': 'Const', 'params': {'value': 0}}
    while len(terms) > 1:
        terms = [{'op': 'Add', 'args': [terms[i], terms[i + 1]]} if i + 1 < len(terms) else terms[i]
                 for i in range(0, len(terms), 2)]
    return terms[0]


def _instantiate(template, binding, n):
    k = template['kind']
    if k == 'fixed':
        return _subst(template['expr'], binding)
    if k == 'sum_vertices':
        return _balanced_add([_subst(template['term'], dict(binding, **{'$v': v})) for v in range(n)])
    if k == 'sum_pairs':
        return _balanced_add([_subst(template['term'], dict(binding, **{'$u': u, '$v': v}))
                              for u in range(n) for v in range(u + 1, n)])
    inner = _instantiate(template['of'], binding, n)
    return {'op': 'Mul', 'args': [inner, {'op': 'Rat', 'params': {'num': template['num'], 'den': template['den']}}]}


def expand(expr, n, registry, *, _depth=0):
    """The pure MRDL expression (accepted operations only) of ``expr`` on hosts with n vertices."""
    if _depth > 2 * MAX_TEMPLATE_DEPTH + len(registry.contracts):
        raise PrimitiveError('expansion depth')
    if not isinstance(expr, dict) or not isinstance(expr.get('op'), str):
        raise PrimitiveError('expression schema')
    op = expr['op']
    if op in mrdl.OPS:
        out = {k: v for k, v in expr.items() if k != 'args'}
        if 'args' in expr:
            out['args'] = [expand(a, n, registry, _depth=_depth) for a in expr['args']]
        return out
    c = registry.contracts.get(op)
    if c is None:
        raise PrimitiveError(f'unknown operation {op}')
    if expr.get('args'):
        raise PrimitiveError(f'{op} takes parameters, not arguments')
    params = expr.get('params') or {}
    if set(params) != set(c['params']):
        raise PrimitiveError(f'{op} takes parameters {sorted(c["params"])}')
    for k, t in c['params'].items():
        if t == 'vertex' and (type(params[k]) is not int or not 0 <= params[k] < n):
            raise PrimitiveError(f'{op}.{k} must be a vertex of the host')
    inst = _instantiate(c['expansion'], dict(params), n)
    return expand(inst, n, registry, _depth=_depth + 1)


def size(expr):
    return 1 + sum(size(a) for a in expr.get('args') or [])


def licensing_value(expr, task, registry):
    """The value anything that licenses a claim must use: the reference expansion, evaluated by the
    accepted MRDL evaluator (its own caps apply: too large an expansion is refused, not approximated)."""
    return mrdl.evaluate(expand(expr, task.n, registry), task)


def native_value(expr, task, registry):
    """Evaluation with native implementations of derived primitives where available (search use)."""
    op = expr['op']
    if op in mrdl.OPS:
        if expr.get('args'):
            vals = [native_value(a, task, registry) for a in expr['args']]
            if any(type(x) not in (int, Fraction) for x in vals):
                raise ValueError('numeric type mismatch')
            return {'Add': lambda: vals[0] + vals[1], 'Sub': lambda: vals[0] - vals[1],
                    'Mul': lambda: vals[0] * vals[1]}[op]()
        return mrdl.evaluate(expr, task)
    c = registry.contracts[op]
    if c['native'] is None:
        return mrdl.evaluate(expand(expr, task.n, registry), task)
    if native_sha256(c['native']) != c['implementation_sha256']:
        raise PrimitiveError('native implementation changed since the contract was pinned')
    return NATIVE[c['native']](task, expr.get('params') or {})


# ---------------------------------------------------------------- conformance, comparison, migration

def _cpu(fn):
    t = time.process_time_ns()
    try:
        return fn(), time.process_time_ns() - t, None
    except Exception as exc:
        return None, time.process_time_ns() - t, f'{type(exc).__name__}: {str(exc)[:120]}'


def conformance(name, registry, tasks):
    """Native against expansion on ``tasks``. A test, not a proof."""
    c = registry.contracts[name]
    if c['native'] is None:
        return {'primitive': name, 'verdict': 'NO_NATIVE', 'rows': []}
    rows, cpu = [], 0
    expr = {'op': name, 'params': {}}
    for t in tasks:
        ref, c1, e1 = _cpu(lambda: licensing_value(expr, t, registry))
        nat, c2, e2 = _cpu(lambda: native_value(expr, t, registry))
        cpu += c1 + c2
        rows.append({'task_id': t.task_id, 'n': t.n, 'reference': _plain(ref), 'native': _plain(nat),
                     'reference_error': e1, 'native_error': e2,
                     'agree': e1 is None and e2 is None and ref == nat})
    evaluable = [r for r in rows if r['reference_error'] is None]
    verdict = ('CONFORMANT' if evaluable and all(r['agree'] for r in evaluable) else
               'NONCONFORMANT' if evaluable else 'UNTESTABLE')
    return {'primitive': name, 'contract_sha256': digest(c), 'verdict': verdict, 'rows': rows, 'cpu_ns': cpu,
            'beyond_language_bounds': sum(1 for r in rows if r['reference_error'])}


def _plain(x):
    return [x.numerator, x.denominator] if isinstance(x, Fraction) else x


def compare(name, registry, conformance_record, fresh_tasks):
    """The s21.2 comparison on fresh hosts: incumbent (expanded expression) vs the equivalent macro
    (same expansion, one-node description, same cost) vs the native primitive (conformance CPU
    charged). Verdict by VERDICT_RULE."""
    c = registry.contracts[name]
    expr = {'op': name, 'params': {}}
    rows, inc_cpu, nat_cpu = [], 0, conformance_record.get('cpu_ns', 0)
    for t in fresh_tasks:
        try:
            exp = expand(expr, t.n, registry)
            n_nodes = size(exp)
        except PrimitiveError as exc:
            exp, n_nodes = None, f'not expandable: {exc}'
        ref, c1, e1 = _cpu(lambda: mrdl.evaluate(exp, t)) if exp is not None else (None, 0, 'not expandable')
        nat, c2, e2 = _cpu(lambda: native_value(expr, t, registry)) if c['native'] else (None, 0, 'no native')
        inc_cpu += c1
        nat_cpu += c2
        rows.append({'task_id': t.task_id, 'n': t.n, 'incumbent_nodes': n_nodes, 'macro_nodes': 1,
                     'incumbent_cpu_ns': c1, 'native_cpu_ns': c2, 'reference': _plain(ref), 'native': _plain(nat),
                     'reference_error': e1, 'native_error': e2,
                     'agree': e1 is None and e2 is None and ref == nat})
    if c['native'] is None:
        verdict = 'NOT_A_CAPABILITY_GAIN'      # a named expansion: shorter description, same cost (a macro)
    elif conformance_record.get('verdict') != 'CONFORMANT' or any(
            r['reference_error'] is None and r['native_error'] is None and not r['agree'] for r in rows):
        verdict = 'REJECTED'
    elif any(r['reference_error'] and not r['native_error'] for r in rows):
        verdict = 'REJECTED'           # the native one answers where the trusted language cannot: unlicensed reach
    elif c['native'] and nat_cpu * 2 <= inc_cpu:
        verdict = 'USEFUL'
    else:
        verdict = 'NOT_A_CAPABILITY_GAIN'
    return {'primitive': name, 'contract_sha256': digest(c), 'registry': registry.identity(), 'rule': VERDICT_RULE,
            'verdict': verdict, 'incumbent_cpu_ns': inc_cpu, 'native_cpu_ns_with_conformance': nat_cpu,
            'conformance_cpu_ns': conformance_record.get('cpu_ns', 0), 'rows': rows,
            'macro_note': 'the equivalent macro has the native description length and the incumbent cost'}


def program_record(name, exprs, registry):
    """A representation program pinned to the registry it was written under."""
    return {'schema': 'genesis-representation-program-v1', 'name': name, 'registry': registry.identity(),
            'expressions': exprs}


def replay(program, task, registries):
    """Evaluate a pinned program under its own historical registry (``registries``: identity -> Registry)."""
    reg = registries.get(program['registry'])
    if reg is None:
        raise PrimitiveError('the registry this program was written under is not available')
    return [_plain(licensing_value(e, task, reg)) for e in program['expressions']]


def migration(old_registry, new_registry, mapping, corpus):
    """Check a migration adapter: ``mapping`` maps an old primitive name to an expression of the new
    registry. Accepted only if it agrees with the old semantics on every corpus host."""
    rows = []
    for old_name, new_expr in mapping.items():
        for t in corpus:
            a, _, e1 = _cpu(lambda: licensing_value({'op': old_name, 'params': {}}, t, old_registry))
            b, _, e2 = _cpu(lambda: licensing_value(new_expr, t, new_registry))
            rows.append({'primitive': old_name, 'task_id': t.task_id, 'old': _plain(a), 'new': _plain(b),
                         'agree': e1 is None and e2 is None and a == b})
    return {'schema': 'genesis-primitive-migration-v1', 'from': old_registry.identity(),
            'to': new_registry.identity(), 'mapping': mapping, 'accepted': bool(rows) and all(r['agree'] for r in rows),
            'rows': rows}


# ---------------------------------------------------------------- proposals from traces

def _abstract(e):
    """The shape of an expression with vertex parameters abstracted."""
    out = {'op': e['op']}
    if 'params' in e:
        out['params'] = {k: ('$' if type(v) is int and k in ('u', 'v') else v) for k, v in sorted(e['params'].items())}
    if 'args' in e:
        out['args'] = [_abstract(a) for a in e['args']]
    return out


def mine(expressions, *, min_count=3, min_size=3):
    """Repeated sub-expression shapes in DEV traces (vertex constants abstracted), most total nodes
    first. Candidates for derived primitives; a proposal, not a decision."""
    counts = {}

    def walk(e):
        s = size(e)
        if s >= min_size:
            key = canonical(_abstract(e))
            counts[key] = counts.get(key, 0) + 1
        for a in e.get('args') or []:
            walk(a)
    for e in expressions:
        walk(e)
    import json
    found = [{'shape': json.loads(k), 'count': n, 'nodes_each': size(json.loads(k)),
              'nodes_total': n * size(json.loads(k))} for k, n in counts.items() if n >= min_count]
    return sorted(found, key=lambda x: (-x['nodes_total'], canonical(x['shape'])))


# ---------------------------------------------------------------- the builder's starting set

def starting_registry():
    """Four derived primitives over accepted operations, with native implementations. Builder-written."""
    deg = lambda x: {'op': 'Degree', 'params': {'u': x}}
    cod = lambda: {'op': 'Codegree', 'params': {'u': '$u', 'v': '$v'}}
    return Registry([
        contract('EdgeCount', expansion={'kind': 'scaled', 'num': 1, 'den': 2,
                                         'of': {'kind': 'fixed', 'expr': {'op': 'TracePower', 'params': {'k': 2}}}},
                 output='rational', semantics='number of host edges (tr A^2 / 2)', native='edge_count_v1',
                 hypothesis='edge budgets in representation features without the trace computation'),
        contract('TriangleCount', expansion={'kind': 'scaled', 'num': 1, 'den': 6,
                                             'of': {'kind': 'fixed', 'expr': {'op': 'TracePower', 'params': {'k': 3}}}},
                 output='rational', semantics='number of host triangles (tr A^3 / 6)', native='triangle_count_v1',
                 hypothesis='triangle-free host screening without cubing the adjacency matrix'),
        contract('SumDegreeSquares', expansion={'kind': 'sum_vertices',
                                                'term': {'op': 'Mul', 'args': [deg('$v'), deg('$v')]}},
                 semantics='sum over vertices of degree^2', native='sum_degree_squares_v1',
                 hypothesis='the pair-count (Cauchy-Schwarz) slack of a host in one operation',
                 failure_modes=['expansion exceeds the 256-node language cap above about 50 vertices']),
        contract('PairCodegreeFalling2', expansion={'kind': 'sum_pairs', 'term': {'op': 'Mul', 'args': [
            cod(), {'op': 'Sub', 'args': [cod(), {'op': 'Const', 'params': {'value': 1}}]}]}},
                 output='int', semantics='sum over vertex pairs u < v of codeg(u,v) * (codeg(u,v) - 1) '
                                        '(= 4 x the number of 4-cycles)',
                 native='pair_codegree_falling2_v1',
                 hypothesis='C4 density of a host in one operation (the CRPD-2 codegree abstraction)',
                 failure_modes=['expansion exceeds the 256-node language cap above about 7 vertices']),
    ])


__all__ = ['contract', 'contract_problems', 'Registry', 'cognitive_kernel', 'expand', 'licensing_value', 'native_value',
           'conformance', 'compare', 'program_record', 'replay', 'migration', 'mine', 'starting_registry', 'NATIVE',
           'VERDICT_RULE', 'PrimitiveError', 'size']
