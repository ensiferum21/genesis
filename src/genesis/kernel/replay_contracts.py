"""Replay contracts for evidence kinds that had none (B14-OPEN-4; handoff s12.2; B20_R8).

The evidence kernel licenses a level only when a trusted replay implementation re-derives it
from stored artifacts; a producer-written verdict is a claim, not evidence. Before B20_R8 the
kinds below had no contract and their levels were unreachable (fail closed). Each contract here
re-runs the check itself and returns problems (empty: the artifact replays):

  exact_check     -> math FINITE_CERTIFIED (needs two, by DIFFERENT methods)
      payload genesis-exact-check-v1 {task_sha256, value, method}; the task is the stored
      problem; ``method`` is one of a closed set of exhaustive optimizers in this repository
      (``graphs.exact_producer``, ``graphs.exact_checker``: different algorithms, one author,
      so "independent" means independent computations, not independent institutions). The
      kernel re-runs the method under its node limit; a SearchLimit is no result.
  formal_check    -> math THEOREM_CHECKED
      payload genesis-formal-check-v1, route equational-custody-v1 {theorem_sha256, manifest,
      record, proof_objects}: the stored theorem (system, its exact pinned axioms, the equation)
      must be what the custody record proves; the successor manifest must pass custody (proof
      objects present and unaltered, uids bound, lemmas true, premises earlier, the pinned
      axioms); the record must be bound to the proof object and the statement; and a fresh Lean
      replay of the proof with its whole lemma chain (pinned Lean, allowed axioms) must be
      CHECKED. The replay route's identity can be revoked like any verifier.
  dev_comparison  -> utility DEV_ONLY, causality CORRELATED
      payload genesis-dev-comparison-v1 {plan, rows, result}: a valid v2 plan, every row marked
      DEV, and the recorded result equal to the kernel's own ``analysis.analyze`` of the rows,
      with decision SUPPORTED. The rows themselves are producer data: this contract replays the
      analysis, not the executions, and a DEV level never satisfies a confirmation.

Still without a contract (their levels stay unreachable, fail closed): ablation and placebo
(causal arm assignment and intervention provenance), internal_replication (operator/control
independence and the reproduction performed) and priority_check (authorized adjudication and a
preserved literature-search record).
"""
from ..common import canonical, digest

EXACT_SCHEMA = 'genesis-exact-check-v1'
FORMAL_SCHEMA = 'genesis-formal-check-v1'
DEV_SCHEMA = 'genesis-dev-comparison-v1'
THEOREM_SCHEMA = 'genesis-theorem-statement-v1'
EXACT_METHODS = ('exact-producer', 'exact-checker')
FORMAL_ROUTES = ('equational-custody-v1',)
EXACT_FIELDS = frozenset({'schema', 'task_sha256', 'value', 'method'})
FORMAL_FIELDS = frozenset({'schema', 'route', 'theorem_sha256', 'manifest', 'record', 'proof_objects'})
DEV_FIELDS = frozenset({'schema', 'plan', 'rows', 'result'})
THEOREM_FIELDS = frozenset({'schema', 'system', 'axioms', 'statement'})
CONTRACTED = frozenset({'exact_check', 'formal_check', 'dev_comparison'})


def theorem_object(system, statement):
    """The stored form of a theorem claim's statement: the system, its exact axioms, the equation."""
    from ..learning import custody as CU
    from ..learning import equational as Q
    if system not in Q.SYSTEMS:
        raise ValueError('unknown system')
    return {'schema': THEOREM_SCHEMA, 'system': system,
            'axioms': [CU._formula_text(a) for a in Q.axioms(system)], 'statement': statement}


def theorem_problems(obj):
    from ..learning import custody as CU
    from ..learning import equational as Q
    if not isinstance(obj, dict) or obj.get('schema') != THEOREM_SCHEMA or set(obj) != THEOREM_FIELDS:
        return ['not a stored theorem statement (genesis-theorem-statement-v1)']
    if obj['system'] not in Q.SYSTEMS:
        return ['unknown system']
    if obj['axioms'] != [CU._formula_text(a) for a in Q.axioms(obj['system'])]:
        return ['the theorem names axioms other than the pinned axioms of its system']
    try:
        from ..learning.statement_panels import eq_of
        eq_of(obj['statement'])
    except Exception:
        return ['the theorem statement is not an equation']
    return []


# ---------------------------------------------------------------- exact_check

def exact_problems(get, payload, problem):
    """``get(hash)`` returns a stored object. Returns (problems, method)."""
    from .. import graphs
    from ..models import GraphTask
    if not isinstance(payload, dict) or payload.get('schema') != EXACT_SCHEMA or set(payload) != EXACT_FIELDS:
        return ['not a replayable exact check (genesis-exact-check-v1 with the stored problem and the method)'], None
    method = payload['method']
    if method not in EXACT_METHODS:
        return [f'unknown exact method {method!r}'], None
    if problem is None or 'task_sha256' not in problem or problem.get('claim') != 'optimum':
        return ['FINITE_CERTIFIED certifies the optimum of a stored finite problem; the claim is not one'], method
    if payload['task_sha256'] != problem['task_sha256'] or payload['value'] != problem['value']:
        return ['the exact check is for a different problem or value than the claim'], method
    try:
        task = GraphTask.model_validate_json(canonical(get(payload['task_sha256'])))
    except Exception:
        return ['stored problem missing or malformed'], method
    if digest(task.model_dump(mode='json')) != payload['task_sha256']:
        return ['stored problem does not hash to task_sha256'], method
    fn = {'exact-producer': graphs.exact_producer, 'exact-checker': graphs.exact_checker}[method]
    try:
        value = fn(task)['value']
    except graphs.SearchLimit:
        return [f'{method} exceeds its exhaustive limit on this problem: no certified value'], method
    if value != payload['value']:
        return [f'{method} does not replay to the recorded value ({value} != {payload["value"]})'], method
    return [], method


# ---------------------------------------------------------------- formal_check

def formal_problems(get, payload, problem, *, revoked_verifiers=()):
    """Returns (problems, replay record or None). Runs Lean (slow): callers cache by identity."""
    from ..learning import custody as CU
    if not isinstance(payload, dict) or payload.get('schema') != FORMAL_SCHEMA or set(payload) != FORMAL_FIELDS:
        return ['not a replayable formal check (genesis-formal-check-v1 with custody of the proof)'], None
    if payload['route'] not in FORMAL_ROUTES:
        return [f'unknown formal route {payload["route"]!r}'], None
    if problem is None or problem.get('claim') != 'theorem' or problem.get('theorem_sha256') != payload['theorem_sha256']:
        return ['the formal check proves a different statement than the claim names'], None
    try:
        theorem = get(payload['theorem_sha256'])
    except Exception:
        return ['stored theorem statement missing'], None
    why = theorem_problems(theorem)
    if why:
        return why, None
    checker = CU.checker_identity()['identity']
    if checker in set(revoked_verifiers):
        return [f'the Lean replay route {checker[:12]} is revoked'], None
    manifest, record = payload['manifest'], payload['record']
    try:
        objects = CU.MemoryObjects(dict(payload['proof_objects']))
    except Exception:
        return ['proof objects do not hash to their names'], None
    if not isinstance(manifest, dict) or manifest.get('system') != theorem['system']:
        return ['the custody manifest is for another system'], None
    codes = sorted({p['code'] for p in CU.successor_problems(manifest, objects)})
    if codes:
        return [f'the proof\'s library fails custody: {", ".join(codes)}'], None
    if not isinstance(record, dict) or not record.get('prover_reported'):
        return ['the record holds no prover-reported proof'], None
    try:
        codes = sorted({p['code'] for p in CU.target_problems(record, manifest, task_statement=theorem['statement'],
                                                             objects=objects)})
    except Exception as exc:
        return [f'malformed proof record ({type(exc).__name__})'], None
    if codes:
        return [f'the proof record fails custody: {", ".join(codes)}'], None
    r = CU.replay_target(record, manifest, objects, task_statement=theorem['statement'],
                         trust_context={'checker_identity': checker}, name=f'kr{record["record_id"][:12]}')
    if r['status'] != 'CHECKED':
        return [f'the proof does not replay in Lean ({r["status"]}: {r.get("reason") or r.get("problems")})'], r
    return [], r


# ---------------------------------------------------------------- dev_comparison

def dev_problems(payload):
    from . import analysis as AN
    if not isinstance(payload, dict) or payload.get('schema') != DEV_SCHEMA or set(payload) != DEV_FIELDS:
        return ['not a replayable DEV comparison (genesis-dev-comparison-v1 with plan, rows and result)']
    if AN.check_plan(payload['plan']):
        return ['the DEV comparison does not carry a valid v2 analysis plan']
    rows = payload['rows']
    if not isinstance(rows, list) or not rows or any(not isinstance(r, dict) or r.get('split') != 'DEV' for r in rows):
        return ['every row of a DEV comparison must be marked split DEV']
    recomputed = AN.analyze(rows, payload['plan'])
    if recomputed != payload['result']:
        return ['the recorded result differs from the kernel\'s analysis of the rows']
    if recomputed['decision'] != 'SUPPORTED':
        return [f'the DEV analysis decides {recomputed["decision"]}, not SUPPORTED']
    return []


__all__ = ['EXACT_SCHEMA', 'FORMAL_SCHEMA', 'DEV_SCHEMA', 'THEOREM_SCHEMA', 'EXACT_METHODS', 'CONTRACTED',
           'theorem_object', 'theorem_problems', 'exact_problems', 'formal_problems', 'dev_problems']
