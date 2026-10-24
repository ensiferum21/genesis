"""Registered executors and checkers of research objects (`docs/OMEGA_RECURSIVE_INVENTION.md` §3.2).

An executor interprets an object's `definition` (data, never code to `eval`) on typed inputs, under the shared fuel.
A checker verifies a postcondition independently of the executor that produced the outputs. Both are registered by
name; an object names its executor and its checkers, and `core.run` refuses unknown names.

Seed executors (the existing languages, adapted without changing them, and the first meta-executors):
  * `expr`: a small, bounded, typed expression language over the inputs (constants, input references,
    arithmetic, comparisons, list aggregates, bounded map and filter): the seed of the sense language (§4.1);
  * `gadget-eval`: a quadratic penalty gadget evaluated on an assignment (minimum over its ancillas);
  * `gadget-synth`: the MILP gadget synthesiser with its settings as the definition (`representation.gadgets`);
  * `acquire`: an acquisition program of `science.acquire` scoring experiments;
  * `mcx2`: Genesis's max-cut engine with a configuration as the definition (`candidate_kinds.mcx2`);
  * `sequence`: a composition running objects in order, each step's outputs added to the namespace;
  * `synth-yield`: a measure, the number of exact gadgets a synthesiser object produces on a set of relations;
  * `improver-yield`: a measure of an improver (what it produces from a base object, on a third task);
  * `improver`: typed self-application: proposes variants of a target object's definition within its declared space,
    measures them with a measure object on training tasks, and admits the best only through the promotion gate
    (strictly better on unfamiliar tasks at matched fuel). Its target may be any object with a variation space,
    including another improver.
"""
import copy
import json
import random
import statistics

MAX_EXPR_NODES = 10000


class ExecutionError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------- the expression language

def _expr(e, env, fuel, budget):
    budget[0] += 1
    if budget[0] > MAX_EXPR_NODES:
        raise ExecutionError('expression evaluation exceeded its node budget')
    if not isinstance(e, dict) or 'op' not in e:
        raise ExecutionError(f'not an expression: {e!r}')
    op = e['op']
    if op == 'const':
        return e['v']
    if op == 'input':
        if e['name'] not in env:
            raise ExecutionError(f"unbound name {e['name']!r}")
        return env[e['name']]
    if op in ('+', '-', '*', '/', 'max2', 'min2', '<', '<=', '==', 'and', 'or'):
        a, b = _expr(e['a'], env, fuel, budget), _expr(e['b'], env, fuel, budget)
        if op == '/':
            return a / b if b else 0.0
        return {'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b, 'max2': lambda: max(a, b),
                'min2': lambda: min(a, b), '<': lambda: a < b, '<=': lambda: a <= b, '==': lambda: a == b,
                'and': lambda: bool(a and b), 'or': lambda: bool(a or b)}[op]()
    if op in ('sum', 'mean', 'max', 'min', 'len', 'sd'):
        xs = list(_expr(e['of'], env, fuel, budget))
        if op == 'len':
            return len(xs)
        if not xs:
            return 0
        return {'sum': sum, 'mean': statistics.mean, 'max': max, 'min': min,
                'sd': lambda v: statistics.pstdev(v) if len(v) > 1 else 0.0}[op](xs)
    if op == 'index':
        return _expr(e['of'], env, fuel, budget)[_expr(e['at'], env, fuel, budget)]
    if op == 'field':
        return _expr(e['of'], env, fuel, budget)[e['name']]
    if op in ('map', 'filter'):
        xs = list(_expr(e['over'], env, fuel, budget))
        out = []
        for x in xs:
            v = _expr(e['body'], dict(env, **{e['var']: x}), fuel, budget)
            if op == 'map':
                out.append(v)
            elif v:
                out.append(x)
        return out
    if op == 'if':
        return _expr(e['then'] if _expr(e['cond'], env, fuel, budget) else e['else'], env, fuel, budget)
    raise ExecutionError(f'unknown operator {op!r}')


def expr_size(e):
    if not isinstance(e, dict):
        return 0
    return 1 + sum(expr_size(v) for k, v in e.items() if k not in ('op', 'v', 'name', 'var'))


def run_expr(defn, inputs, ctx):
    fuel = ctx['fuel']
    fuel.take(max(1, expr_size(defn['expr']) // 50))
    return {defn.get('output', 'value'): _expr(defn['expr'], dict(inputs), fuel, [0])}


# ------------------------------------------------------------------------------------------- adapters

def run_gadget_eval(defn, inputs, ctx):
    from ..representation import gadgets as GD
    return {'penalty': GD.Gadget.from_json(defn).min_over_ancillas(tuple(inputs['x']))}


def run_gadget_synth(defn, inputs, ctx):
    from ..representation import gadgets as GD
    from ..representation.relations import relation_from_json
    ctx['fuel'].take()
    g, rep = GD.synthesize_milp(relation_from_json(inputs['relation']), max_ancillas=defn['max_ancillas'],
                                bound=defn['bound'], uniform=defn.get('uniform', False),
                                time_limit=defn.get('time_limit', 10))
    return {'gadget': g.to_json() if g is not None else None}


def run_acquire(defn, inputs, ctx):
    from ..science import acquire as Q
    return {'scores': [float(x) for x in Q.scores(defn, inputs['n_exp'], [(i, f) for i, f in inputs['pairs']])]}


def run_mcx2(defn, inputs, ctx):
    from ..candidate_kinds import mcx2 as K
    from ..models_maxcut import MaxCutCandidateView
    g = inputs['graph']
    E = [tuple(e) if len(e) == 3 else (e[0], e[1], 1) for e in g['edges']]
    b = float(inputs.get('budget', 1.0))
    ctx['fuel'].take(max(1, int(b)))
    r = K.solve(MaxCutCandidateView(n=g['n'], edges=tuple(E)), {'cpu_seconds': b, 'config': defn}, b,
                int(inputs.get('seed', 1)))
    return {'assignment': [int(c) for c in r['side']], 'value': r['value']}


def run_sequence(defn, inputs, ctx):
    from . import core
    env = dict(inputs)
    for step in defn['steps']:
        res = core.run(step, {k: env[k] for k in step['inputs']}, ctx['fuel'], ctx['types'], ctx['kinds'],
                       depth=ctx['depth'] + 1)
        if not res['ok']:
            raise ExecutionError(f"step {step.get('name') or step['kind']} failed: {res['violations']}")
        env.update(res['outputs'])
    return {k: env[k] for k in defn['outputs']}


def run_synth_yield(defn, inputs, ctx):
    from . import core
    syn = inputs['synthesizer']
    found = 0
    for rel in inputs['relations']:
        res = core.run(syn, {'relation': rel}, ctx['fuel'], ctx['types'], ctx['kinds'], depth=ctx['depth'] + 1)
        if res['ok'] and res['outputs'].get('gadget') is not None:
            found += 1
    return {'yield': found}


def _mutate_definition(definition, space, step, rng):
    child = copy.deepcopy(definition)
    name = sorted(space)[rng.randrange(len(space))]
    choices = space[name]
    i = choices.index(child[name]) if child.get(name) in choices else 0
    j = min(len(choices) - 1, max(0, i + rng.choice((-step, step))))
    child[name] = choices[j]
    return child, name


def run_improver(defn, inputs, ctx):
    """Inputs: target (an object with definition['space'] or a 'space' in this improver), measure (an object
    measuring `measured` on a task), train and unfamiliar (tasks: input dicts for the measure). Outputs: the admitted
    object (the target itself if nothing passed the gate), the yields, and whether a descendant was admitted."""
    from . import core
    target, measure = inputs['target'], inputs['measure']
    slot = defn.get('slot', 'synthesizer')
    space = defn.get('space') or target['definition'].get('space') or {}
    if not space:
        raise ExecutionError('the target declares no variation space')
    rng = random.Random(defn.get('seed', 0))

    def yield_on(obj, task):
        res = core.run(measure, dict(task, **{slot: obj}), ctx['fuel'], ctx['types'], ctx['kinds'],
                       depth=ctx['depth'] + 1)
        if not res['ok']:
            raise ExecutionError(f"measure failed: {res['violations']}")
        return res['outputs']['yield']
    best, best_y = target, yield_on(target, inputs['train'])
    tried = []
    for _ in range(int(defn.get('variants', 4))):
        d, changed = _mutate_definition(best['definition'], {k: v for k, v in space.items()}, int(defn.get('step', 1)),
                                        rng)
        cand = core.derive(best, definition=d, lineage={'improver': core.oid(ctx['self']), 'changed': changed})
        y = yield_on(cand, inputs['train'])
        tried.append({'definition': d, 'train_yield': y})
        if y > best_y:
            best, best_y = cand, y
    if best is target:
        return {'object': target, 'admitted': False, 'train_yield': best_y, 'unfamiliar': None, 'tried': tried}
    yc, yt = yield_on(best, inputs['unfamiliar']), yield_on(target, inputs['unfamiliar'])
    admitted = yc > yt
    return {'object': best if admitted else target, 'admitted': admitted, 'train_yield': best_y,
            'unfamiliar': {'candidate': yc, 'incumbent': yt}, 'tried': tried}


def run_improver_yield(defn, inputs, ctx):
    """A measure of an improver: run it on a base object (with the base's measure, training and gate tasks) and
    return the yield of what it returns on a third, final task."""
    from . import core
    res = core.run(inputs['improver'], {'target': inputs['base'], 'measure': inputs['base_measure'],
                                        'train': inputs['train'], 'unfamiliar': inputs['gate']},
                   ctx['fuel'], ctx['types'], ctx['kinds'], depth=ctx['depth'] + 1)
    if not res['ok']:
        raise ExecutionError(f"improver failed: {res['violations']}")
    slot = inputs['improver']['definition'].get('slot', 'synthesizer')
    m = core.run(inputs['base_measure'], dict(inputs['final'], **{slot: res['outputs']['object']}), ctx['fuel'],
                 ctx['types'], ctx['kinds'], depth=ctx['depth'] + 1)
    if not m['ok']:
        raise ExecutionError(f"final measure failed: {m['violations']}")
    return {'yield': m['outputs']['yield']}


EXECUTORS = {'improver-yield': run_improver_yield, 'expr': run_expr, 'gadget-eval': run_gadget_eval, 'gadget-synth': run_gadget_synth,
             'acquire': run_acquire, 'mcx2': run_mcx2, 'sequence': run_sequence, 'synth-yield': run_synth_yield,
             'improver': run_improver}


# ------------------------------------------------------------------------------------------- checkers

def check_exact_gadget(inputs, outputs):
    from ..representation import gadgets as GD
    from ..representation.relations import relation_from_json
    if outputs.get('gadget') is None:
        return True                                  # "none found" is a valid answer; a wrong gadget is not
    g, rel = GD.Gadget.from_json(outputs['gadget']), relation_from_json(inputs['relation'])
    return GD.check(g, rel)['exact'] and GD.check_matrix(g, rel)


def check_cut_value(inputs, outputs):
    g, x = inputs['graph'], outputs['assignment']
    if len(x) != g['n']:
        return False
    val = sum((e[2] if len(e) == 3 else 1) for e in g['edges'] if x[e[0]] != x[e[1]])
    return val == outputs['value']


def check_nonnegative(inputs, outputs):
    return all(v >= 0 for v in outputs.values() if isinstance(v, (int, float)) and not isinstance(v, bool))


def check_finite(inputs, outputs):
    import math
    return all(math.isfinite(v) for v in outputs.values() if isinstance(v, float))


CHECKERS = {'exact_gadget': check_exact_gadget, 'cut_value': check_cut_value, 'nonnegative': check_nonnegative,
            'finite': check_finite}


__all__ = ['ExecutionError', 'EXECUTORS', 'CHECKERS', 'expr_size', 'MAX_EXPR_NODES']
