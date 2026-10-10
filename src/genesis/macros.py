"""Macro engines as executable Research IR programs (spec §6, Appendix A).

Each macro is a Python driver that only acts through `Interpreter.invoke` on
the sixteen primitives. The executed node list (with concrete parameters and
output digests) is returned as an IR program record that `ir.replay` can
re-execute and compare, so every macro run is reproducible from IR.

Implemented here, all in the bounded graph wedge:
  ghost_census      DISTINGUISH + EXECUTE + VERIFY  (+ FORMALIZE, OBSERVE)
  barrier_escape    DISTINGUISH + VERIFY + TRANSFORM (+ EXECUTE, OBSERVE)
  local_to_global   FACTOR + TRANSPORT + COMPOSE + VERIFY (+ TRANSFORM, EXECUTE, OBSERVE)
  gap_engine        FORMALIZE + DISTINGUISH + TRANSFORM + REFLECT (+ EXECUTE, OBSERVE)
  cognitive_compile COMPRESS + SYNTHESIZE + VERIFY (+ EXECUTE, OBSERVE)
Glue primitives in parentheses (FORMALIZE/EXECUTE/OBSERVE) are how an engine
touches the world; Appendix A lists only the characteristic operators.
"""
from .ir import Interpreter, Value, program_record
from .models import Limits, SolverProgram

GHOST_STATES = ('PROVED', 'GHOST_FOUND', 'UNSETTLED', 'HARNESS_ERROR')


class _Run:
    def __init__(self, name, seed, limits, max_actions, custody=None):
        self.name = name
        self.ir = Interpreter(limits or Limits(), max_actions=max_actions, seed=seed, custody=custody)
        self.inputs = {}
        self.n = 0

    def input(self, key, kind, data, effects=(), provenance=()):
        self.inputs[key] = Value(kind, data, tuple(effects), tuple(provenance))
        return key, self.inputs[key]

    def __call__(self, op, args, params=None):
        self.n += 1
        nid = f'{op.lower()}_{self.n}'
        out = self.ir.invoke(op, [a[1] for a in args], params or {}, node_id=nid, input_ids=[a[0] for a in args])
        return nid, out

    def record(self):
        return program_record(self.name, self.inputs, self.ir.trace, self.ir.seed, self.ir.limits)

    def ops(self):
        return sorted({t['op'] for t in self.ir.trace})


def ghost_census(task, bound, program, *, seeds=(0, 1, 2), verify_seconds=60, limits=None, custody=None):
    """Is "optimum <= bound" true for this host? Search for a checked countermodel (ghost);
    if none is found, try an independently checked upper certificate. Failure to find a
    ghost is never reported as proof."""
    r = _Run('ghost_census', seeds[0], limits, 8 + 4 * len(seeds), custody)
    try:
        raw = r.input('task', 'RawTask', task.model_dump(mode='json'), ('USES_DEV_DATA',))
        prog = r.input('program', 'Program', program)
        goal = r('FORMALIZE', [raw])
        # Which action separates "bound true" from "bound false" more per unit cost?
        table = r.input('predictions', 'Predictions', {'search': [0, 1], 'certify': [1, 0]})
        plan = r('DISTINGUISH', [table], {'costs': {'search': 1, 'certify': 3}})
        best = None
        for _ in seeds:
            receipt = r('EXECUTE', [goal, prog])
            if receipt[1].data.get('status') != 'SUCCESS':
                continue
            witness = r('OBSERVE', [receipt], {'field': 'selected'})
            checked = r('VERIFY', [goal, witness])
            if best is None or checked[1].data['value'] > best[1].data['value']:
                best, best_witness = checked, witness
            if checked[1].data['value'] > bound:
                return {'status': 'GHOST_FOUND', 'bound': bound, 'ghost_value': checked[1].data['value'],
                        'plan': plan[1].data, 'program': r.record(), 'ops': r.ops()}
        start = best_witness if best else r.input('empty', 'Witness', ())
        cert = r('VERIFY', [goal, start], {'contract': 'upper_bound', 'seconds': verify_seconds})
        d = cert[1].data
        if d['lower'] > bound:
            status = 'GHOST_FOUND'
        elif d['upper'] <= bound and d['upper_method'] in ('SAT_DRAT', 'HOST_EDGE_COUNT'):
            status = 'PROVED'
        else:
            status = 'UNSETTLED'
        return {'status': status, 'bound': bound, 'certificate': d, 'plan': plan[1].data, 'no_ghost_found': status != 'GHOST_FOUND',
                'proof': status == 'PROVED', 'program': r.record(), 'ops': r.ops()}
    except (ValueError, RuntimeError) as exc:
        return {'status': 'HARNESS_ERROR', 'reason': f'{type(exc).__name__}: {exc}', 'program': r.record(), 'ops': r.ops()}


def barrier_escape(task, program, *, seeds=(0, 1, 2, 3), verify_seconds=60, limits=None, custody=None):
    """Measure the best value a search class reaches (its empirical barrier), then try to
    certify the barrier as the true optimum; if certification instead yields a better witness,
    the class was escaped by moving to the exact (PB/SAT) representation."""
    r = _Run('barrier_escape', seeds[0], limits, 6 + 3 * len(seeds), custody)
    raw = r.input('task', 'RawTask', task.model_dump(mode='json'), ('USES_DEV_DATA',))
    prog = r.input('program', 'Program', program)
    goal = r('FORMALIZE', [raw])
    plan = r('DISTINGUISH', [r.input('predictions', 'Predictions', {'more_seeds': [0, 0], 'exact_repr': [0, 1]})],
             {'costs': {'more_seeds': 1, 'exact_repr': 2}})
    barrier, witness = -1, None
    for _ in seeds:
        receipt = r('EXECUTE', [goal, prog])
        if receipt[1].data.get('status') == 'SUCCESS':
            w = r('OBSERVE', [receipt], {'field': 'selected'})
            v = r('VERIFY', [goal, w])[1].data['value']
            if v > barrier:
                barrier, witness = v, w
    # Semantic randomization: the barrier should not depend on vertex labels.
    reversed_goal = r('TRANSFORM', [goal], {'permutation': list(reversed(range(task.n)))})
    receipt = r('EXECUTE', [reversed_goal, prog])
    relabel_value = receipt[1].data.get('result', {}).get('value')
    cert = r('VERIFY', [goal, witness or r.input('empty', 'Witness', ())],
             {'contract': 'upper_bound', 'seconds': verify_seconds})
    d = cert[1].data
    verdict = ('CLASS_OPTIMAL' if d['status'] == 'OPTIMALITY_CHECKED' and d['lower'] == barrier else
               'ESCAPED' if d['lower'] > barrier else 'BARRIER_UNSETTLED')
    return {'status': verdict, 'class_barrier': barrier, 'escape_value': d['lower'], 'upper': d['upper'],
            'certified': d['status'] == 'OPTIMALITY_CHECKED', 'certificate': d.get('certificate'),
            'witness': [list(e) for e in (d.get('witness') or ())], 'label_sensitivity': relabel_value != barrier,
            'plan': plan[1].data, 'program': r.record(), 'ops': r.ops()}


def local_to_global(task, program, *, limits=None):
    """Solve each connected component in its own induced representation, transport the
    local witnesses back, glue, and re-check the glued witness on the original host."""
    r = _Run('local_to_global', 0, limits, 64)
    raw = r.input('task', 'RawTask', task.model_dump(mode='json'), ('USES_DEV_DATA',))
    prog = r.input('program', 'Program', program)
    goal = r('FORMALIZE', [raw])
    parts = r('FACTOR', [goal])
    transported = []
    for comp in parts[1].data['components']:
        if len(comp) < 2:
            continue
        local = r('TRANSFORM', [goal], {'induced': list(comp)})
        if not local[1].data.edges:
            continue
        receipt = r('EXECUTE', [local, prog])
        if receipt[1].data.get('status') != 'SUCCESS':
            return {'status': 'LOCAL_FAILURE', 'program': r.record(), 'ops': r.ops()}
        w = r('OBSERVE', [receipt], {'field': 'selected'})
        transported.append(r('TRANSPORT', [local, w], {'mapping': sorted(comp),
                                                        'target': task.model_dump(mode='json')}))
    glued = r('COMPOSE', [goal, *transported])
    checked = r('VERIFY', [goal, glued])
    return {'status': 'GLUED', 'value': checked[1].data['value'], 'components': len(parts[1].data['components']),
            'program': r.record(), 'ops': r.ops()}


def gap_engine(task, program, rows, *, limits=None):
    """Diagnose why search fails before scaling it: reflect on failure rows, test label
    sensitivity (representation dependence), and choose the most separating next experiment."""
    r = _Run('gap_engine', 0, limits, 16)
    raw = r.input('task', 'RawTask', task.model_dump(mode='json'), ('USES_DEV_DATA',))
    prog = r.input('program', 'Program', program)
    goal = r('FORMALIZE', [raw])
    hypotheses = r('REFLECT', [r.input('rows', 'Rows', rows, ('USES_DEV_DATA',))])
    base = r('EXECUTE', [goal, prog])
    moved = r('TRANSFORM', [goal], {'permutation': list(reversed(range(task.n)))})
    alt = r('EXECUTE', [moved, prog])
    v0 = base[1].data.get('result', {}).get('value'); v1 = alt[1].data.get('result', {}).get('value')
    representation_sensitive = v0 != v1
    # Predictions of each next action under (SEARCH_POLICY_LIMITED, REPRESENTATION_LIMITED).
    table = {'more_rounds': [1, 0], 'exchange_moves': [1, 1], 'exact_representation': [0, 1]}
    plan = r('DISTINGUISH', [r.input('predictions', 'Predictions', table)],
             {'costs': {'more_rounds': 1, 'exchange_moves': 2, 'exact_representation': 4}})
    diagnosis = list(hypotheses[1].data['hypotheses'])
    if representation_sensitive and 'REPRESENTATION_LIMITED' not in diagnosis:
        diagnosis.append('REPRESENTATION_LIMITED')
    return {'status': 'DIAGNOSED' if diagnosis else 'NO_GAP_OBSERVED', 'hypotheses': diagnosis,
            'representation_sensitive': representation_sensitive, 'next_experiment': plan[1].data['action'],
            'epistemic_type': 'HYPOTHESIS', 'program': r.record(), 'ops': r.ops()}


def cognitive_compile(tasks, program, *, limits=None):
    """Compile recurring solver behaviour into a reusable macro and check, on the same DEV
    tasks, that the compiled program preserves the witnessed values (not a new algorithm)."""
    r = _Run('cognitive_compile', 0, limits, 8 + 4 * len(tasks))
    prog = r.input('program', 'Program', program)
    traces, values = [], []
    for i, t in enumerate(tasks):
        goal = r('FORMALIZE', [r.input(f'task{i}', 'RawTask', t.model_dump(mode='json'), ('USES_DEV_DATA',))])
        receipt = r('EXECUTE', [goal, prog])
        traces.append(receipt[1].data['result']['trace'])
        w = r('OBSERVE', [receipt], {'field': 'selected'})
        values.append(r('VERIFY', [goal, w])[1].data['value'])
    macro = r('COMPRESS', [prog, r.input('traces', 'Traces', traces, ('USES_DEV_DATA',))])
    variants = r('SYNTHESIZE', [prog], {'count': 2})
    return {'status': 'COMPILED', 'macro': macro[1].data, 'preserved_values': values,
            'synthesized_candidates': len(variants[1].data), 'evidence': 'DEV_ONLY', 'program': r.record(),
            'ops': r.ops()}


IMPLEMENTED = {
    'Ghost Census': (ghost_census, {'DISTINGUISH', 'EXECUTE', 'VERIFY'}),
    'Barrier & Escape': (barrier_escape, {'DISTINGUISH', 'VERIFY', 'TRANSFORM'}),
    'Local-to-Global Engine': (local_to_global, {'FACTOR', 'TRANSPORT', 'COMPOSE', 'VERIFY'}),
    'Gap Engine': (gap_engine, {'FORMALIZE', 'DISTINGUISH', 'TRANSFORM', 'REFLECT'}),
    'Cognitive Compilation': (cognitive_compile, {'COMPRESS', 'SYNTHESIZE', 'VERIFY'}),
}
