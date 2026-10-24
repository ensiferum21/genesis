"""The research-object record, its validation, execution and storage (`docs/OMEGA_RECURSIVE_INVENTION.md` §3).

An object is a JSON value with schema `genesis-research-object-v1`:

    {schema, kind, name, definition, executor, inputs: {name: type}, outputs: {name: type}, pre: [checker],
     post: [checker], effect, determinism, cost, dependencies: [object id], limitations: [str], lineage: {...}}

Its identity (`oid`) is the digest of the record. `run(obj, inputs, fuel, ...)`:
  1. validates the object against the type and kind registries (the registry versions are part of the call);
  2. type-checks the inputs, and checks the preconditions;
  3. runs the registered executor under the shared fuel (one unit per run, plus what the executor charges) and a
     depth limit (objects that run objects, such as compositions and improvers, nest);
  4. type-checks the outputs and runs the postcondition checkers, which are registered apart from the executors;
  5. returns {ok, outputs, violations, fuel_spent} and, with a vault, stores the object and the run (an
     ExperimentSpec naming the object's artifact as its parent).
A failed check is reported as a failure of the object, never repaired. `OutOfFuel` from any level propagates.
"""
import copy
import json

from ..autonomy import process as P
from ..common import digest
from . import executors as EX
from . import kinds as KI
from . import types as TY

SCHEMA = 'genesis-research-object-v1'
MAX_DEPTH = 8
DETERMINISM = ('deterministic', 'seeded')


def make(kind, definition, executor, inputs, outputs, *, name=None, pre=(), post=(), effect=None,
         determinism='deterministic', cost=None, dependencies=(), limitations=(), lineage=None):
    return {'schema': SCHEMA, 'kind': kind, 'name': name, 'definition': copy.deepcopy(definition),
            'executor': executor, 'inputs': dict(inputs), 'outputs': dict(outputs), 'pre': list(pre),
            'post': list(post), 'effect': effect, 'determinism': determinism, 'cost': cost or {},
            'dependencies': list(dependencies), 'limitations': list(limitations), 'lineage': lineage or {}}


def oid(obj):
    return digest(obj)[:16]


def derive(obj, *, definition=None, lineage=None, **changes):
    """A child object: the parent's record with a new definition (or other fields), its lineage naming the parent."""
    child = copy.deepcopy(obj)
    if definition is not None:
        child['definition'] = copy.deepcopy(definition)
    child.update(changes)
    child['lineage'] = dict(lineage or {}, parent=oid(obj))
    return child


def validate(obj, types=TY.SEED, kinds=KI.SEED):
    """None, or why the object is malformed."""
    if not isinstance(obj, dict) or obj.get('schema') != SCHEMA:
        return 'not a research object'
    if obj['kind'] not in kinds['kinds']:
        return f"unknown kind {obj['kind']!r}"
    if obj['executor'] not in EX.EXECUTORS:
        return f"unknown executor {obj['executor']!r}"
    for side in ('inputs', 'outputs'):
        for n, t in obj[side].items():
            if not TY.known(t, types):
                return f'unknown type {t!r} for {side[:-1]} {n!r}'
    for c in obj['pre'] + obj['post']:
        if c not in EX.CHECKERS:
            return f'unknown checker {c!r}'
    eff = kinds['kinds'][obj['kind']]['effect']
    if obj['effect'] is not None and obj['effect'] != eff:
        return f"effect {obj['effect']!r} contradicts kind {obj['kind']!r} ({eff})"
    if obj['determinism'] not in DETERMINISM:
        return f'determinism is one of {DETERMINISM}'
    try:
        json.dumps(obj, sort_keys=True)
    except TypeError:
        return 'not JSON-representable'
    return None


def run(obj, inputs, fuel, types=TY.SEED, kinds=KI.SEED, vault=None, creator='genesis', depth=0):
    if depth > MAX_DEPTH:
        raise P.OutOfFuel('object nesting deeper than MAX_DEPTH')
    why = validate(obj, types, kinds)
    if why:
        return {'ok': False, 'outputs': {}, 'violations': [f'invalid object: {why}'], 'fuel_spent': 0}
    viol = []
    for n, t in obj['inputs'].items():
        if n not in inputs:
            viol.append(f'missing input {n!r}')
        elif not TY.check(inputs[n], t, types):
            viol.append(f'input {n!r} is not a {t}')
    for c in obj['pre']:
        if not viol and not EX.CHECKERS[c](inputs, {}):
            viol.append(f'precondition {c} failed')
    if viol:
        return {'ok': False, 'outputs': {}, 'violations': viol, 'fuel_spent': 0}
    before = fuel.spent
    fuel.take()
    ctx = {'fuel': fuel, 'types': types, 'kinds': kinds, 'depth': depth, 'self': obj}
    try:
        outputs = EX.EXECUTORS[obj['executor']](obj['definition'], inputs, ctx)
    except EX.ExecutionError as e:
        return {'ok': False, 'outputs': {}, 'violations': [f'execution: {e}'], 'fuel_spent': fuel.spent - before}
    for n, t in obj['outputs'].items():
        if n not in outputs:
            viol.append(f'missing output {n!r}')
        elif not TY.check(outputs[n], t, types):
            viol.append(f'output {n!r} is not a {t}')
    for c in obj['post']:
        if not viol and not EX.CHECKERS[c](inputs, outputs):
            viol.append(f'postcondition {c} failed')
    res = {'ok': not viol, 'outputs': outputs, 'violations': viol, 'fuel_spent': fuel.spent - before}
    if vault is not None:
        res['record'] = record(vault, obj, inputs, res, creator, types, kinds)
    return res


def store(vault, obj, creator='genesis', kinds=KI.SEED, parents=()):
    """Store the object exactly as a vault artifact of its kind's storage type; returns its artifact ID."""
    rec = vault.record(kinds['kinds'][obj['kind']]['storage'], obj, domain='research-objects', creator=creator,
                       parents=parents)
    return vault.put(rec, status='generated')


def record(vault, obj, inputs, res, creator, types, kinds):
    aid = store(vault, obj, creator, kinds)
    exp = vault.record('ExperimentSpec', {'object': oid(obj), 'inputs_digest': digest(inputs)[:16],
                                          'ok': res['ok'], 'violations': res['violations'],
                                          'outputs_digest': digest(json.loads(json.dumps(res['outputs'],
                                                                                         default=str)))[:16],
                                          'fuel_spent': res['fuel_spent'], 'types': types['version'],
                                          'kinds': kinds['version']},
                       domain='research-objects', creator=creator, parents=[aid])
    return {'object': aid, 'run': vault.put(exp, status='generated')}


__all__ = ['SCHEMA', 'MAX_DEPTH', 'make', 'oid', 'derive', 'validate', 'run', 'store', 'record']
