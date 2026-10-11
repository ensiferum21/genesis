"""Replayable research macros and proof-carrying compression (roadmap W18).

A research macro is a parameterized research program induced from successful
trajectories. Here a macro is an ordered list of lemma *schemas* (equations over
operation parameters) with, for each step:
  * the E budget it needs (resource bound),
  * the earlier steps its source proof used (proof dependencies),
  * and its effect: the lemma it adds to the library.
Its precondition is a signature shape (operation names and arities); its expansion
semantics instantiates the schemas under a signature map and proves them in order, each
from the axioms and the lemmas added by earlier steps. Nothing in a macro is trusted: an
expansion is a sequence of ordinary proof attempts, and a lemma enters the library only
with its own E proof object.

Induction (direct compression). From a source run's trajectory, keep the lemmas that
were used (by a target proof or a lemma proof) together with their dependency closure,
in their original order. All other attempts — failures and unused lemmas — are kept in
the induction record and dropped from the macro. Description length is reported for
the trajectory and for the macro.

Faithful replay. Expanding the macro on its source system must prove every step again,
from the same dependencies.

Revocation. Revoking a lemma invalidates every macro step that depends on it, directly or
through other steps. Those steps are removed from the macro, and the change is recorded.
"""
from ..common import digest
from . import equational as Q
from .research import used_inputs, _cpu
from ..verification.eprover import prove

SCHEMA = 'genesis-research-macro-v1'


def _rename(t, m):
    if t[0] == 'var':
        return t
    return ('fn', m.get(t[1], t[1]), tuple(_rename(a, m) for a in t[2]))


def induce(result, evaluation, *, name):
    """A macro from one research run and the evaluation of its successor."""
    lib = {l['id']: l for l in result['library']}
    used = set(evaluation['lemma_use'])
    closure, stack = set(), list(used)
    while stack:
        i = stack.pop()
        if i in closure or i not in lib:
            continue
        closure.add(i)
        stack += lib[i]['uses']
    steps = []
    index = {}
    for l in result['library']:
        if l['id'] not in closure:
            continue
        index[l['id']] = len(steps)
        steps.append({'schema': l['eq'], 'text': l['text'], 'depends_on': sorted(index[u] for u in l['uses']
                                                                                 if u in index),
                      'budget_s': 2, 'source_lemma': l['id']})
    ops = Q.SYSTEMS[result['system']]['ops']
    trajectory_dl = sum(len(s['eq']) for s in result['trajectory'])
    macro_dl = sum(len(s['text']) for s in steps)
    return {'schema': SCHEMA, 'name': name, 'source_system': result['system'], 'precondition': {'ops': ops},
            'steps': steps, 'resource_bound_s': sum(s['budget_s'] for s in steps),
            'induction': {'trajectory_attempts': len(result['trajectory']), 'library_size': len(result['library']),
                          'kept': len(steps), 'dropped_attempts': len(result['trajectory']) - len(steps),
                          'description_length': {'trajectory': trajectory_dl, 'macro': macro_dl}},
            'revoked': [], 'macro_sha256': digest([s['text'] for s in steps])}


def applicable(macro, system, op_map=None):
    """Precondition: the target signature has the macro's operations (after renaming)."""
    op_map = op_map or {}
    ops = Q.SYSTEMS[system]['ops']
    return all(ops.get(op_map.get(f, f)) == a for f, a in macro['precondition']['ops'].items())


def expand(macro, system, *, op_map=None, library=None, budget_s=None, strict=True):
    """Prove the macro's steps in order on `system`. Returns the library and a step log.
    strict: a step whose source dependencies were not proved is skipped (the recorded
    semantics). Non-strict (added in B20 after the Wolfram transfer, where one failed first
    step blocked every later one): each step is attempted with whatever earlier steps were
    proved."""
    if not applicable(macro, system, op_map):
        raise ValueError('macro precondition fails for this system')
    op_map = op_map or {}
    ax = Q.axioms(system)
    library = list(library or [])
    log, by_step = [], {}
    start = _cpu()
    for k, st in enumerate(macro['steps']):
        if budget_s is not None and _cpu() - start >= budget_s:
            log.append({'step': k, 'outcome': 'BUDGET'}); break
        eq = Q.canon((_rename(st['schema'][0], op_map), _rename(st['schema'][1], op_map)))
        deps = [by_step[d] for d in st['depends_on'] if d in by_step]
        if len(deps) < len(st['depends_on']):
            if strict:
                log.append({'step': k, 'eq': Q.text(eq), 'outcome': 'DEPENDENCY_MISSING'}); continue
            deps = list(by_step.values())[-8:]
        if not Q.holds(eq, Q.SYSTEMS[system]['decider']):
            log.append({'step': k, 'eq': Q.text(eq), 'outcome': 'FALSE_HERE'}); continue
        c0 = _cpu()
        r = prove(ax + [Q.closed(d['eq']) for d in deps], Q.closed(eq), seconds=st['budget_s'], mode='auto')
        ok = r['status'] == 'THEOREM' and bool(r['proof'])
        if ok:
            used = used_inputs(r['proof'], len(ax) + len(deps))
            lem = {'id': f'M{len(library)}', 'eq': eq, 'text': Q.text(eq), 'proof': r['proof'],
                   'uses': [deps[i - len(ax)]['id'] for i in used if i >= len(ax)],
                   'premise_ids': [d['id'] for d in deps], 'macro_step': k}
            library.append(lem); by_step[k] = lem
        log.append({'step': k, 'eq': Q.text(eq), 'outcome': 'PROVED' if ok else 'UNPROVED',
                    'cpu_s': round(_cpu() - c0, 3)})
    return library, log


def replay_faithful(macro):
    """Expand on the source system; every step must be proved again."""
    lib, log = expand(macro, macro['source_system'])
    return {'steps': len(macro['steps']), 'proved': sum(s['outcome'] == 'PROVED' for s in log),
            'faithful': all(s['outcome'] == 'PROVED' for s in log) and len(log) == len(macro['steps']), 'log': log}


def revoke(macro, step_index, reason):
    """Remove a step and every step that depends on it (transitively); record it."""
    dead = {step_index}
    changed = True
    while changed:
        changed = False
        for k, st in enumerate(macro['steps']):
            if k not in dead and set(st['depends_on']) & dead:
                dead.add(k); changed = True
    keep = [k for k in range(len(macro['steps'])) if k not in dead]
    remap = {old: new for new, old in enumerate(keep)}
    steps = [dict(macro['steps'][k], depends_on=[remap[d] for d in macro['steps'][k]['depends_on']]) for k in keep]
    rec = {'revoked_step': step_index, 'reason': reason, 'invalidated': sorted(dead),
           'texts': [macro['steps'][k]['text'] for k in sorted(dead)]}
    out = dict(macro, steps=steps, revoked=macro['revoked'] + [rec],
               resource_bound_s=sum(s['budget_s'] for s in steps), macro_sha256=digest([s['text'] for s in steps]))
    return out


__all__ = ['induce', 'expand', 'replay_faithful', 'revoke', 'applicable', 'SCHEMA']
