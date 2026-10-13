"""Fault-tolerant reasoning across evidence routes (W23, handoff s21.3).

A *route* answers one exact question about one input (is this edge set motif-free? what is the
largest motif-free subgraph of this host?) and declares the factors its failures depend on:

    implementation  the code or tool that decides (two copies of one routine are one implementation)
    language        python, c, lean ...
    arithmetic      'exact' or 'float'
    trust_base      what must be correct for the answer to be right (the Genesis Python code, the
                    Lean kernel, drat-trim ...)
    translation     the encoding step between the question and the decider, or None
    assumptions     the definitions/contract the route decides under (an identity)

Two routes are *diverse* only when they share neither implementation nor trust base. Several
copies of one routine, or several agents sharing one model and prompt, are not independent
evidence, however many of them agree.

``cross_check`` runs every route on the same input and returns one of

    AGREE        all decided routes give one answer and at least two of them are diverse
    CORRELATED   all decided routes agree, but no two are diverse (no independence is claimed)
    UNSETTLED    no route decided (resource limits, unsupported inputs, errors)
    DISAGREE     two decided routes give different answers

A disagreement is never settled by counting routes. ``Quarantine.record`` keeps the input, every
route's factors and outcome, and the possible causes from a closed vocabulary (CAUSES); the
subject stays quarantined (``Quarantine.problems`` is non-empty) until an *adjudication* names
the faulty route(s), one cause, evidence beyond the route outcomes themselves (a reproduction, a
proof object, a corrected translation) and the adjudicator. The quarantine record stays as
history; an adjudication by a person is recorded as an intervention.
"""
from dataclasses import dataclass, field
from typing import Callable

from ..common import canonical, digest, utcnow

SCHEMA_CHECK = 'genesis-cross-check-v1'
SCHEMA_QUARANTINE = 'genesis-quarantine-v1'
SCHEMA_ADJUDICATION = 'genesis-adjudication-v1'
OUTCOMES = ('DECIDED', 'RESOURCE_OUT', 'UNSUPPORTED', 'ERROR')
VERDICTS = ('AGREE', 'CORRELATED', 'UNSETTLED', 'DISAGREE')
CAUSES = ('DIFFERENT_ASSUMPTIONS', 'PARSER_TRANSLATION', 'UNSUPPORTED_PROOF_RULE', 'NUMERIC_APPROXIMATION',
          'RESOURCE_FAILURE', 'CHECKER_DEFECT')
FACTORS = ('implementation', 'language', 'arithmetic', 'trust_base', 'translation', 'assumptions')
INTERVENTIONS = ('HUMAN_INTERVENTION', 'EXTERNAL_REVIEW')


@dataclass(frozen=True)
class Route:
    name: str
    question: str
    factors: dict = field(hash=False)
    run: Callable = field(hash=False, compare=False, repr=False)

    def identity(self):
        return {'name': self.name, 'question': self.question,
                'factors': {k: self.factors.get(k) for k in FACTORS}}


def route_problems(route):
    out = []
    if not isinstance(route.name, str) or not route.name:
        out.append('route without a name')
    missing = [k for k in FACTORS if k not in route.factors]
    if missing:
        out.append(f'route {route.name} does not declare {missing}')
    if route.factors.get('arithmetic') not in ('exact', 'float'):
        out.append(f'route {route.name}: arithmetic must be exact or float')
    for k in ('implementation', 'trust_base', 'language'):
        if not route.factors.get(k):
            out.append(f'route {route.name}: empty {k}')
    return out


def diverse(a, b):
    """Meaningfully different failure modes: no shared implementation and no shared trust base."""
    return (a.factors['implementation'] != b.factors['implementation']
            and a.factors['trust_base'] != b.factors['trust_base'])


def _outcome(route, subject_input):
    from ..graphs import SearchLimit
    try:
        r = route.run(subject_input)
    except SearchLimit as exc:
        return {'status': 'RESOURCE_OUT', 'reason': str(exc)[:300]}
    except Exception as exc:                      # a route failure is an outcome, never a verdict
        return {'status': 'ERROR', 'reason': f'{type(exc).__name__}: {str(exc)[:300]}'}
    if not isinstance(r, dict) or r.get('status') not in OUTCOMES:
        return {'status': 'ERROR', 'reason': 'route returned no outcome'}
    if r['status'] == 'DECIDED' and 'answer' not in r:
        return {'status': 'ERROR', 'reason': 'decided without an answer'}
    return json_safe(r)


def json_safe(x):
    import json
    return json.loads(canonical(x))


def candidate_causes(routes, outcomes):
    """Possible causes of a disagreement, from the routes' declared factors and their outcomes.
    A list of hypotheses for an adjudicator, not a resolution. CHECKER_DEFECT is always possible."""
    by = {r.name: r for r in routes}
    decided = [n for n, o in outcomes.items() if o['status'] == 'DECIDED']
    groups = {}
    for n in decided:
        groups.setdefault(canonical(outcomes[n]['answer']), []).append(n)
    out = []
    if len({canonical(by[n].factors.get('assumptions')) for n in decided}) > 1:
        out.append('DIFFERENT_ASSUMPTIONS')
    if any(by[n].factors.get('translation') for n in decided):
        out.append('PARSER_TRANSLATION')
    if any(outcomes[n].get('unsupported_rule') for n in outcomes):
        out.append('UNSUPPORTED_PROOF_RULE')
    if any(by[n].factors.get('arithmetic') != 'exact' for n in decided):
        out.append('NUMERIC_APPROXIMATION')
    if any(outcomes[n].get('partial') for n in decided):     # e.g. a timed-out search reported as an answer
        out.append('RESOURCE_FAILURE')
    out.append('CHECKER_DEFECT')
    return out, sorted(groups.values())


def cross_check(question, subject, subject_input, routes, *, input_record=None):
    """Run every route of ``question`` on one input. ``subject`` names what is being checked (an
    artifact identity); ``input_record`` is the JSON kept for reproduction (defaults to the input)."""
    if not routes:
        raise ValueError('no routes')
    for r in routes:
        why = route_problems(r)
        if why:
            raise ValueError('; '.join(why))
        if r.question != question:
            raise ValueError(f'route {r.name} answers {r.question!r}, not {question!r}')
    if len({r.name for r in routes}) != len(routes):
        raise ValueError('route names must be distinct')
    outcomes = {r.name: _outcome(r, subject_input) for r in routes}
    decided = [r for r in routes if outcomes[r.name]['status'] == 'DECIDED']
    answers = {canonical(outcomes[r.name]['answer']) for r in decided}
    pairs = [(a.name, b.name) for i, a in enumerate(decided) for b in decided[i + 1:] if diverse(a, b)]
    if not decided:
        verdict = 'UNSETTLED'
    elif len(answers) > 1:
        verdict = 'DISAGREE'
    else:
        verdict = 'AGREE' if pairs else 'CORRELATED'
    body = {'schema': SCHEMA_CHECK, 'question': question, 'subject': subject,
            'input': json_safe(input_record if input_record is not None else subject_input),
            'routes': [r.identity() for r in routes], 'outcomes': outcomes, 'verdict': verdict,
            'diverse_pairs': pairs, 'checked_at': utcnow()}
    if verdict == 'DISAGREE':
        body['candidate_causes'], body['answer_groups'] = candidate_causes(routes, outcomes)
    else:
        body['answer'] = json_safe(outcomes[decided[0].name]['answer']) if decided else None
    return dict(body, check_id=digest(body))


class QuarantineError(PermissionError):
    pass


class Quarantine:
    """Quarantine and adjudication records kept as immutable entities of a Store."""

    def __init__(self, store):
        self.store = store

    def record(self, check):
        if not isinstance(check, dict) or check.get('schema') != SCHEMA_CHECK or check.get('verdict') != 'DISAGREE':
            raise ValueError('only a DISAGREE cross-check is quarantined')
        body = {k: v for k, v in check.items() if k != 'check_id'}
        if digest(body) != check.get('check_id'):
            raise ValueError('cross-check record does not match its identity')
        rec = {'schema': SCHEMA_QUARANTINE, 'subject': check['subject'], 'question': check['question'],
               'check': check, 'outcome_digests': sorted(digest(o) for o in check['outcomes'].values()),
               'status': 'QUARANTINED'}
        rid = digest(rec)
        self.store.save('quarantine', rid, rec)
        return rid

    def _entities(self, kind):
        rows = self.store.db.execute('SELECT id, object_hash FROM entities WHERE kind=? ORDER BY id', (kind,))
        return {i: self.store.get(h) for i, h in rows.fetchall()}

    def get(self, record_id):
        rec = self._entities('quarantine').get(record_id)
        if rec is None:
            raise KeyError(record_id)
        return rec

    def adjudications(self, record_id=None):
        adj = self._entities('adjudication')
        return {k: v for k, v in adj.items() if record_id is None or v['quarantine_id'] == record_id}

    def open(self, subject=None):
        """Unresolved quarantine records (optionally for one subject)."""
        resolved = {a['quarantine_id'] for a in self._entities('adjudication').values()}
        return {k: v for k, v in self._entities('quarantine').items()
                if k not in resolved and (subject is None or v['subject'] == subject)}

    def problems(self, subject):
        """Why ``subject`` may not license anything now (empty: no open quarantine)."""
        return [f'quarantined by {k[:12]}: routes disagree on {v["question"]} ({sorted(v["check"]["outcomes"])})'
                for k, v in sorted(self.open(subject).items())]

    def require_clear(self, subject):
        why = self.problems(subject)
        if why:
            raise QuarantineError('; '.join(why))

    def adjudicate(self, record_id, *, cause, faulty_routes, evidence, adjudicator,
                   intervention='HUMAN_INTERVENTION', note=''):
        """Lift one quarantine. Refused unless the adjudication names one cause, the faulty
        route(s) (not every decided route), evidence that is not merely the route outcomes, and the
        adjudicator; the routes left must agree. Counting routes is not evidence."""
        rec = self.get(record_id)
        check = rec['check']
        decided = {n for n, o in check['outcomes'].items() if o['status'] == 'DECIDED'}
        out = []
        if cause not in CAUSES:
            out.append(f'cause must be one of {CAUSES}')
        faulty = set(faulty_routes or ())
        if not faulty:
            out.append('name the faulty route(s)')
        if faulty - decided:
            out.append(f'not decided routes of this check: {sorted(faulty - decided)}')
        survivors = decided - faulty
        if not survivors:
            out.append('every decided route is marked faulty: nothing is left to stand on')
        if len({canonical(check['outcomes'][n]['answer']) for n in survivors}) > 1:
            out.append('the routes left still disagree')
        ev = list(evidence or ())
        if not ev or not all(isinstance(e, str) and len(e) == 64 and all(c in '0123456789abcdef' for c in e)
                             for e in ev):
            out.append('evidence must be sha256 identities of stored objects')
        elif set(ev) <= set(rec['outcome_digests']) | {record_id, check['check_id']}:
            out.append('the route outcomes themselves are not evidence about which route is wrong')
        else:
            missing = [e for e in ev if not _stored(self.store, e)]
            if missing:
                out.append(f'evidence objects not in the store: {[m[:12] for m in missing]}')
        if not isinstance(adjudicator, str) or not adjudicator.strip():
            out.append('name the adjudicator')
        if intervention not in INTERVENTIONS:
            out.append(f'intervention must be one of {INTERVENTIONS}')
        if out:
            raise QuarantineError('adjudication refused: ' + '; '.join(out))
        answer = check['outcomes'][sorted(survivors)[0]]['answer']
        adj = {'schema': SCHEMA_ADJUDICATION, 'quarantine_id': record_id, 'subject': rec['subject'],
               'cause': cause, 'faulty_routes': sorted(faulty), 'surviving_routes': sorted(survivors),
               'resolved_answer': answer, 'evidence': sorted(ev), 'adjudicator': adjudicator,
               'intervention': intervention, 'note': note, 'adjudicated_at': utcnow()}
        aid = digest(adj)
        self.store.save('adjudication', aid, adj)
        return aid


def _stored(store, h):
    try:
        store.get_bytes(h)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- routes for graph tasks

ASSUMPTIONS_GRAPHS = 'genesis.graphs domain contracts (c4_host_v2, triangle_free_host_v1)'


def _motif_free_py(fn):
    def run(inp):
        from ..graphs import normalize
        task, edges = inp
        es = normalize(task.n, edges)
        return {'status': 'DECIDED', 'answer': not fn(task, es)}
    return run


def _lean_assumptions():
    from ..formal_research import triangle_theory as T
    from ..invention import representations as R
    return digest({'GTDefs': T.DEFS_SOURCE, 'G4Defs': R.C4_SOURCE})


LEAN_DECIDE_MAX_VERTICES = 9


def _motif_free_lean(inp):
    """The Lean kernel decides the repository's own predicate (G4.C4Free / GT.TriangleFree) on the
    edge-set literal: both the statement and its negation are offered; exactly one may check."""
    from ..formal_research import checker as C
    from ..formal_research import triangle_theory as T
    from ..graphs import normalize
    from ..invention import representations as R
    task, edges = inp
    es = normalize(task.n, edges)
    if len({v for e in es for v in e}) > LEAN_DECIDE_MAX_VERTICES:
        return {'status': 'UNSUPPORTED', 'reason': f'more than {LEAN_DECIDE_MAX_VERTICES} vertices for kernel decide'}
    lit = '(∅ : GT.Edges)' if not es else '({' + ', '.join(f'({u}, {v})' for u, v in es) + '} : GT.Edges)'
    pred = 'G4.C4Free' if task.domain == 'c4_host_v2' else 'GT.TriangleFree'
    spec = '\n'.join(['import GTDefs', 'import G4Defs', 'namespace MFSpec',
                      f'def yes : Prop := {pred} {lit}', f'def no : Prop := ¬ {pred} {lit}', 'end MFSpec', ''])
    # One module per side: the false side fails to compile, which must not sink the true one.
    proofs = [{'name': f'MFProof{side.title()}', 'trusted': False,
               'source': '\n'.join(['import MFSpec', f'namespace MFProof{side.title()}',
                                    f'theorem proof : MFSpec.{side} := by unfold MFSpec.{side}; decide +kernel',
                                    f'end MFProof{side.title()}', ''])} for side in ('yes', 'no')]
    modules = [{'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True},
               {'name': R.C4_MODULE, 'source': R.C4_SOURCE, 'trusted': True},
               {'name': 'MFSpec', 'source': spec, 'trusted': True}] + proofs
    r = C.accept(modules, [{'spec': 'MFSpec.yes', 'proof': 'MFProofYes.proof'},
                           {'spec': 'MFSpec.no', 'proof': 'MFProofNo.proof'}])
    st = {b['spec']: b['status'] for b in r.get('bindings', [])}
    if r.get('status') == 'CHECKER_ERROR' or 'CHECKER_ERROR' in st.values():
        return {'status': 'ERROR', 'reason': f'Lean checker unavailable: {r.get("reason")}'}
    yes, no = st.get('MFSpec.yes') == 'CHECKED', st.get('MFSpec.no') == 'CHECKED'
    if yes and no:
        return {'status': 'ERROR', 'reason': 'both the predicate and its negation checked (inconsistent environment)'}
    if not (yes or no):
        return {'status': 'RESOURCE_OUT', 'reason': f'kernel decide settled neither side: {st}'}
    return {'status': 'DECIDED', 'answer': yes}


def motif_free_routes(*, lean=True):
    from .. import graphs as G
    py = {'language': 'python', 'arithmetic': 'exact', 'trust_base': 'genesis-python', 'translation': None,
          'assumptions': ASSUMPTIONS_GRAPHS}
    routes = [Route('explicit-motifs-v1', 'motif_free', dict(py, implementation='graphs.forbidden_a'),
                    _motif_free_py(G.forbidden_a)),
              Route('neighbor-bitsets-v1', 'motif_free', dict(py, implementation='graphs.forbidden_b'),
                    _motif_free_py(G.forbidden_b))]
    if lean:
        routes.append(Route('lean-kernel-decide-v1', 'motif_free',
                            {'implementation': 'lean kernel decide (Decidable instances of GTDefs/G4Defs)',
                             'language': 'lean', 'arithmetic': 'exact', 'trust_base': 'lean-kernel',
                             'translation': 'edge list -> GT.Edges literal', 'assumptions': ASSUMPTIONS_GRAPHS},
                            _motif_free_lean))
    return routes


def _opt(fn, label):
    def run(task):
        r = fn(task)
        return {'status': 'DECIDED', 'answer': r['value'], 'method': label}
    return run


def _opt_sat(task, seconds=60):
    from .sat import certified_bounds
    from ..verification.tools import ToolUnavailable
    try:
        b = certified_bounds(task, seconds=seconds)
    except ToolUnavailable as exc:
        return {'status': 'UNSUPPORTED', 'reason': f'SAT toolchain unavailable: {exc}'}
    if b.get('status') == 'OPTIMALITY_CHECKED':
        return {'status': 'DECIDED', 'answer': b['upper'],
                'method': (b.get('upper_certificate') or {}).get('method')}
    if b.get('status') == 'CHECKER_ERROR':
        return {'status': 'ERROR', 'reason': 'SAT route checker error'}
    return {'status': 'RESOURCE_OUT', 'reason': f'bounds only: [{b.get("lower")}, {b.get("upper")}]'}


def optimum_routes(*, sat=True, sat_seconds=60):
    from .. import graphs as G
    py = {'language': 'python', 'arithmetic': 'exact', 'trust_base': 'genesis-python', 'translation': None,
          'assumptions': ASSUMPTIONS_GRAPHS}
    routes = [Route('motif-hitting-set', 'max_motif_free_edges', dict(py, implementation='graphs.exact_producer'),
                    _opt(G.exact_producer, 'motif-hitting-set')),
              Route('incremental-branch-bound', 'max_motif_free_edges', dict(py, implementation='graphs.exact_checker'),
                    _opt(G.exact_checker, 'incremental-neighbor-branch-bound'))]
    if sat:
        routes.append(Route('sat-drat', 'max_motif_free_edges',
                            {'implementation': 'cadical (search) + drat-trim (proof check)', 'language': 'c',
                             'arithmetic': 'exact', 'trust_base': 'drat-trim + CNF encoder (sat.encode)',
                             'translation': 'CNF encoding (sat.encode)', 'assumptions': ASSUMPTIONS_GRAPHS},
                            lambda t: _opt_sat(t, sat_seconds)))
    return routes


def check_witness_routes(task, edges, *, lean=True):
    """Cross-check motif-freeness of a witness edge set (the subject is the task and edge set)."""
    from ..graphs import normalize
    es = normalize(task.n, edges)
    subject = digest({'task': task.model_dump(mode='json'), 'edges': [list(e) for e in es]})
    return cross_check('motif_free', subject, (task, es), motif_free_routes(lean=lean),
                       input_record={'task': task.model_dump(mode='json'), 'edges': [list(e) for e in es]})


def check_optimum_routes(task, *, sat=True, sat_seconds=60):
    subject = digest(task.model_dump(mode='json'))
    return cross_check('max_motif_free_edges', subject, task, optimum_routes(sat=sat, sat_seconds=sat_seconds),
                       input_record={'task': task.model_dump(mode='json')})


__all__ = ['Route', 'cross_check', 'diverse', 'candidate_causes', 'Quarantine', 'QuarantineError', 'CAUSES',
           'VERDICTS', 'motif_free_routes', 'optimum_routes', 'check_witness_routes', 'check_optimum_routes',
           'route_problems']
