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
  formal_check, route lean-package-v1 (B20_R20) -> math THEOREM_CHECKED for a theory-package statement
      payload {theorem_sha256, package}: the stored genesis-lean-theorem-v1 object names the package
      (its package_sha256 binds every definition module), the statement id and its exact Lean text.
      The package must pass its integrity checks, hold the statement with that text, status CHECKED and
      allowed axioms only, define its specification constant as exactly that proposition, and bind a
      proof to it; the kernel then replays the whole package in Lean (theory_package.replay) under a
      revocable route identity (pinned Lean, workspace, checker code, allowed axioms).
  dev_comparison  -> utility DEV_ONLY, causality CORRELATED
      payload genesis-dev-comparison-v2 {plan, arms, rows, result} (B20_R18; v1, whose rows were
      producer data, is retired and licenses nothing): a valid v2 plan, every row marked DEV and
      bound to two executions recorded in this store's attempt journal, one per arm. The kernel
      re-reads each attempt: its request is a solver request for the row's DEV task with the arm's
      program or descriptor (``arms``), its terminal receipt gives the row's run status and CPU,
      and a successful run's witness re-checks (graphs.check_witness) to the row's value; a failed
      run scores zero. No attempt is used twice. The recorded result must equal the kernel's own
      ``analysis.analyze`` of the rows, with decision SUPPORTED. A DEV level never satisfies a
      confirmation.

B20_R15 adds the rest of B14-OPEN-4:

  priority_check  -> novelty REDISCOVERY, VARIANT or CANDIDATE_NOVEL (route equational-literature-v1)
      payload genesis-priority-check-v1 {theorem_sha256, level, sources, prior_art, searches,
      library_searches}. Sources are stored literature records (``literature.source``); the kernel
      re-hashes their text and re-runs the injection screen (a flagged source cannot be used). Each
      prior-art entry is an exact quote at a recorded span of a listed source plus its formalization
      as an equation of a known system; the kernel recomputes its relation to the claimed theorem
      (``partitions.EquationalAdapter``: same variety and signature; EXACT, ALPHA or INSTANCE make the
      theorem a REDISCOVERY, GENERALIZES a VARIANT). With no related prior art the level is
      CANDIDATE_NOVEL, and then the search record must be preserved and replayable: at least one search,
      at least one search of the pinned library (Mathlib at the workspace's pinned revision), every
      library search re-run by the kernel with the same hits, and every hit read (covered by a stored
      VERBATIM library excerpt). The declared level must equal the recomputed one and the level asked
      for. Limits: formalizing a quote is producer work (a wrong or missing formalization can only make
      the result look newer, which is why CANDIDATE_NOVEL stays a candidate); relations are syntactic,
      so a statement equivalent only modulo the theory's laws is not recognised as prior art.
  ablation, placebo -> causality ABLATION_SUPPORTED, PLACEBO_CONTROLLED
      signed custodian evaluations of their own kind (kernel.receipts). The kernel additionally replays
      the intervention's provenance from the stored arms (``arms_sha256``): both descriptors rebuild,
      share kind, domain, implementation and resource profile, and differ in exactly one registered
      component, whose altered value is the registered ablation or placebo transform of the candidate's
      value (``INTERVENTIONS``). PLACEBO_CONTROLLED needs an ablation and a placebo of the same component.
      Components without a registered transform cannot license a causal level.
  internal_replication -> replication INTERNAL_INDEPENDENT
      a signed evaluation by the internal-replicator role (registry v2), checked in kernel.evidence: it
      repeats a supporting sealed_evaluation of the same claim (same arms, analysis and domain) on another
      panel, by another operator identity, registered after the original completed. Distinct keys and
      operator identities are what code can check; whether the operators are independent is not.
      B20_R21: external_reproduction (replication EXTERNAL_REPRODUCTION, signed by the replicator role)
      must repeat a supporting sealed_evaluation in the same way, and may compare descriptors (v4).
"""
from ..common import canonical, digest

EXACT_SCHEMA = 'genesis-exact-check-v1'
FORMAL_SCHEMA = 'genesis-formal-check-v1'
DEV_SCHEMA = 'genesis-dev-comparison-v2'
DEV_SCHEMA_V1 = 'genesis-dev-comparison-v1'          # retired (B20R8-OPEN-1)
THEOREM_SCHEMA = 'genesis-theorem-statement-v1'
EXACT_METHODS = ('exact-producer', 'exact-checker')
FORMAL_ROUTES = ('equational-custody-v1', 'lean-package-v1')
LEAN_THEOREM_SCHEMA = 'genesis-lean-theorem-v1'
LEAN_THEOREM_FIELDS = frozenset({'schema', 'package_sha256', 'statement_id', 'statement'})
LEAN_PACKAGE_FIELDS = frozenset({'schema', 'route', 'theorem_sha256', 'package'})
EXACT_FIELDS = frozenset({'schema', 'task_sha256', 'value', 'method'})
FORMAL_FIELDS = frozenset({'schema', 'route', 'theorem_sha256', 'manifest', 'record', 'proof_objects'})
DEV_FIELDS = frozenset({'schema', 'plan', 'arms', 'rows', 'result'})
DEV_ROW_FIELDS = frozenset({'task_id', 'stratum', 'status', 'split', 'candidate', 'baseline'})
DEV_ARM_FIELDS = frozenset({'value', 'run', 'cpu_ns', 'attempt'})
THEOREM_FIELDS = frozenset({'schema', 'system', 'axioms', 'statement'})
PRIORITY_SCHEMA = 'genesis-priority-check-v1'
PRIORITY_ROUTES = ('equational-literature-v1',)
PRIORITY_FIELDS = frozenset({'schema', 'route', 'theorem_sha256', 'level', 'sources', 'prior_art', 'searches',
                             'library_searches'})
PRIOR_ART_FIELDS = frozenset({'source_sha256', 'span', 'quote', 'system', 'statement'})
PRIORITY_LEVELS = ('REDISCOVERY', 'VARIANT', 'CANDIDATE_NOVEL')
RELATION_LEVEL = {'EXACT': 'REDISCOVERY', 'ALPHA': 'REDISCOVERY', 'INSTANCE': 'REDISCOVERY',
                  'GENERALIZES': 'VARIANT'}
CONTRACTED = frozenset({'exact_check', 'formal_check', 'dev_comparison', 'priority_check'})


def theorem_object(system, statement):
    """The stored form of a theorem claim's statement: the system, its exact axioms, the equation."""
    from ..learning import custody as CU
    from ..learning import equational as Q
    if system not in Q.SYSTEMS:
        raise ValueError('unknown system')
    return {'schema': THEOREM_SCHEMA, 'system': system,
            'axioms': [CU._formula_text(a) for a in Q.axioms(system)], 'statement': statement}


def lean_theorem_object(package, statement_id):
    """The stored form of a Lean-package theorem claim (B20_R20): the package identity (which binds
    every definition module), the statement's id and its exact Lean text."""
    s = next((x for x in package['statements'] if x['id'] == statement_id), None)
    if s is None:
        raise ValueError(f'no statement {statement_id!r} in the package')
    return {'schema': LEAN_THEOREM_SCHEMA, 'package_sha256': package['package_sha256'], 'statement_id': statement_id,
            'statement': s['lean']}


def _lean_theorem_problems(obj):
    if set(obj) != LEAN_THEOREM_FIELDS:
        return ['not a stored Lean theorem statement (genesis-lean-theorem-v1)']
    if not (isinstance(obj['package_sha256'], str) and len(obj['package_sha256']) == 64 and
            isinstance(obj['statement_id'], str) and obj['statement_id'].isidentifier() and
            isinstance(obj['statement'], str) and obj['statement'].strip() and '\n' not in obj['statement']):
        return ['malformed Lean theorem statement']
    return []


def theorem_problems(obj):
    from ..learning import custody as CU
    from ..learning import equational as Q
    if isinstance(obj, dict) and obj.get('schema') == LEAN_THEOREM_SCHEMA:
        return _lean_theorem_problems(obj)
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
    if isinstance(payload, dict) and payload.get('schema') == FORMAL_SCHEMA and payload.get('route') == 'lean-package-v1':
        return lean_package_problems(get, payload, problem, revoked_verifiers=revoked_verifiers)
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
    if theorem.get('schema') != THEOREM_SCHEMA:
        return ['the equational custody route proves equational theorems only'], None
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


def package_checker_identity():
    """Identity of the Lean-package replay route: pinned Lean, the formal workspace's source and
    artifact identities, the checker and package-replay code, and the allowed axioms."""
    import hashlib
    from pathlib import Path
    from ..formal_research import checker as C
    from ..formal_research import workspace as W
    from ..verification.tools import tool
    here = Path(__file__).resolve().parents[1] / 'formal_research'
    ws = W.environment()
    ident = {'lean': tool('lean')['identity'],
             'workspace': {k: ws[k] for k in ('source_identity', 'artifact_identity')},
             'checker_sha256': hashlib.sha256((here / 'checker.py').read_bytes()).hexdigest(),
             'theory_package_sha256': hashlib.sha256((here / 'theory_package.py').read_bytes()).hexdigest(),
             'allowed_axioms': sorted(C.ALLOWED_AXIOMS)}
    return dict(ident, identity=digest(ident))


def lean_package_problems(get, payload, problem, *, revoked_verifiers=(), replay=None):
    """Route lean-package-v1 (B20_R20): THEOREM_CHECKED for a statement of a theory package
    (formal_research.theory_package). Returns (problems, replay report or None). Runs Lean (slow)."""
    from ..formal_research import checker as C
    from ..formal_research import theory_package as TP
    if set(payload) != LEAN_PACKAGE_FIELDS:
        return ['not a replayable Lean-package check (route lean-package-v1 with the whole package)'], None
    if problem is None or problem.get('claim') != 'theorem' or problem.get('theorem_sha256') != payload['theorem_sha256']:
        return ['the formal check proves a different statement than the claim names'], None
    try:
        theorem = get(payload['theorem_sha256'])
    except Exception:
        return ['stored theorem statement missing'], None
    if not isinstance(theorem, dict) or theorem.get('schema') != LEAN_THEOREM_SCHEMA:
        return ['the Lean-package route proves Lean theorem statements (genesis-lean-theorem-v1) only'], None
    why = theorem_problems(theorem)
    if why:
        return why, None
    pkg = payload['package']
    why = TP.integrity_problems(pkg) if isinstance(pkg, dict) else ['not a theory package']
    if why:
        return ['the package fails its integrity checks: ' + '; '.join(why)], None
    if pkg['package_sha256'] != theorem['package_sha256']:
        return ['the package is not the one the theorem names'], None
    s = next((x for x in pkg['statements'] if x.get('id') == theorem['statement_id']), None)
    if s is None or s.get('lean') != theorem['statement']:
        return ['the package does not hold this statement with this exact Lean text'], None
    if s.get('status') != 'CHECKED':
        return [f'the package records the statement as {s.get("status")}, not CHECKED'], None
    if set(s.get('axioms') or ()) - set(C.ALLOWED_AXIOMS):
        return ['the proof uses axioms outside the allowed set'], None
    module, _, name = str(s.get('spec_const')).partition('.')
    spec = next((m for m in pkg['modules'] if m['name'] == module), None)
    if spec is None or f'def {name} : Prop := {s["lean"]}' not in spec['source'].splitlines():
        return ['the specification constant is not defined as the stated proposition'], None
    if not any(b.get('spec') == s['spec_const'] and b.get('proof') == s.get('proof_const') for b in pkg['bindings']):
        return ['no binding of a proof to the specification constant'], None
    try:
        checker = package_checker_identity()['identity']
    except Exception as exc:
        return [f'the Lean-package replay route is unavailable here ({type(exc).__name__})'], None
    if checker in set(revoked_verifiers):
        return [f'the Lean-package replay route {checker[:12]} is revoked'], None
    r = (replay or TP.replay)(pkg)
    if r.get('verdict') != 'REPLAYED':
        return [f'the package does not replay in Lean ({"; ".join(r.get("differences", []))[:200]})'], r
    if (s['proof_const'].split('.')[0], 'CHECKED') not in {tuple(x) for x in r.get('bindings', [])} and \
            (s['proof_const'], 'CHECKED') not in {tuple(x) for x in r.get('bindings', [])}:
        return ['the replay did not check this statement\'s proof'], r
    return [], r


# ---------------------------------------------------------------- dev_comparison

def arm_identity_of_request(request):
    """Identity of the solver a journalled solver request ran: a DSL program digest, or a descriptor id."""
    if not isinstance(request, dict) or request.get('kind') != 'solver':
        return None
    if isinstance(request.get('descriptor'), dict):
        return request['descriptor'].get('descriptor_id')
    if isinstance(request.get('program'), dict):
        return digest(request['program'])
    return None


def dev_problems(get, payload, attempt):
    """``get(hash)`` reads a stored object; ``attempt(id)`` returns (status, request_hash, receipt_hash)
    from the store's attempt journal, or None."""
    from . import analysis as AN
    from ..graphs import check_witness
    from ..models import GraphTask
    if isinstance(payload, dict) and payload.get('schema') == DEV_SCHEMA_V1:
        return ['a v1 DEV comparison carries producer rows not bound to execution evidence (B20R8-OPEN-1); '
                'record a genesis-dev-comparison-v2']
    if not isinstance(payload, dict) or payload.get('schema') != DEV_SCHEMA or set(payload) != DEV_FIELDS:
        return ['not a replayable DEV comparison (genesis-dev-comparison-v2 with plan, arms, rows and result)']
    if AN.check_plan(payload['plan']):
        return ['the DEV comparison does not carry a valid v2 analysis plan']
    arms = payload['arms']
    if not isinstance(arms, dict) or set(arms) != {'candidate', 'baseline'} or not all(
            isinstance(v, str) and len(v) == 64 for v in arms.values()) or arms['candidate'] == arms['baseline']:
        return ['arms must name two different solver identities (program digest or descriptor id)']
    rows = payload['rows']
    if not isinstance(rows, list) or not rows or any(not isinstance(r, dict) or r.get('split') != 'DEV' for r in rows):
        return ['every row of a DEV comparison must be marked split DEV']
    used, out = set(), []
    for i, r in enumerate(rows):
        if set(r) != DEV_ROW_FIELDS or r['status'] != 'SCORED':
            out.append(f'row {i}: fields or status (bound rows are SCORED)')
            continue
        tasks = []
        for arm in ('candidate', 'baseline'):
            cell = r[arm]
            if not isinstance(cell, dict) or set(cell) != DEV_ARM_FIELDS:
                out.append(f'row {i} {arm}: fields')
                continue
            aid = cell['attempt']
            if not isinstance(aid, str) or aid in used:
                out.append(f'row {i} {arm}: attempt missing or used twice')
                continue
            used.add(aid)
            journal = attempt(aid)
            if journal is None or journal[2] is None:
                out.append(f'row {i} {arm}: attempt {str(aid)[:8]} is not a finished attempt in this store')
                continue
            status, req_h, rec_h = journal
            try:
                request, receipt = get(req_h), get(rec_h)
                task = GraphTask.model_validate_json(canonical(request['task']))
            except Exception:
                out.append(f'row {i} {arm}: stored request or receipt unreadable')
                continue
            if arm_identity_of_request(request) != arms[arm]:
                out.append(f'row {i} {arm}: the attempt ran another solver than the arm names')
                continue
            if task.task_id != r['task_id'] or task.split != 'DEV':
                out.append(f'row {i} {arm}: the attempt ran another task, or a non-DEV task')
                continue
            tasks.append(digest(task.model_dump(mode='json')))
            ok = status == 'SUCCESS' and receipt.get('status') == 'SUCCESS'
            if cell['run'] != ('SUCCESS' if ok else 'FAILED') or cell['cpu_ns'] != (receipt.get('cpu_ns') or 0):
                out.append(f'row {i} {arm}: run status or CPU differs from the attempt receipt')
                continue
            if ok:
                try:
                    value = check_witness(task, [tuple(e) for e in (receipt.get('result') or {}).get('selected', [])])['value']
                except Exception:
                    out.append(f'row {i} {arm}: the attempt witness does not re-check')
                    continue
            else:
                value = 0
            if value != cell['value']:
                out.append(f'row {i} {arm}: value {cell["value"]} is not what the attempt witness re-checks to ({value})')
        if len(tasks) == 2 and tasks[0] != tasks[1]:
            out.append(f'row {i}: the two arms ran different tasks')
    if out:
        return out[:5] + ([f'... {len(out) - 5} more'] if len(out) > 5 else [])
    recomputed = AN.analyze(rows, payload['plan'])
    if recomputed != payload['result']:
        return ['the recorded result differs from the kernel\'s analysis of the rows']
    if recomputed['decision'] != 'SUPPORTED':
        return [f'the DEV analysis decides {recomputed["decision"]}, not SUPPORTED']
    return []


def dev_comparison(store, plan, candidate_rows, baseline_rows):
    """Build a v2 payload from two lists of journalled trial rows (``campaign.Campaign.trial`` rows:
    attempt_id, task_id, family), paired by task. Values, runs and CPU are read back from the
    attempt receipts, never taken from the rows."""
    from . import analysis as AN
    from ..graphs import check_witness
    from ..models import GraphTask

    def journal(aid):
        return store.db.execute('SELECT status,request,receipt FROM attempts WHERE id=?', (aid,)).fetchone()

    def cell(aid):
        status, req_h, rec_h = journal(aid)
        request, receipt = store.get(req_h), store.get(rec_h)
        task = GraphTask.model_validate_json(canonical(request['task']))
        ok = status == 'SUCCESS' and receipt.get('status') == 'SUCCESS'
        value = check_witness(task, [tuple(e) for e in receipt['result']['selected']])['value'] if ok else 0
        return ({'value': value, 'run': 'SUCCESS' if ok else 'FAILED', 'cpu_ns': receipt.get('cpu_ns') or 0,
                 'attempt': aid}, arm_identity_of_request(request), task)
    base = {r['task_id']: r for r in baseline_rows}
    rows, arms = [], {}
    for r in candidate_rows:
        c, cid, task = cell(r['attempt_id'])
        b, bid, _ = cell(base[r['task_id']]['attempt_id'])
        arms.setdefault('candidate', cid); arms.setdefault('baseline', bid)
        if (arms['candidate'], arms['baseline']) != (cid, bid):
            raise ValueError('each arm must be one solver')
        rows.append({'task_id': r['task_id'], 'stratum': task.family, 'status': 'SCORED', 'split': task.split,
                     'candidate': c, 'baseline': b})
    return {'schema': DEV_SCHEMA, 'plan': plan, 'arms': arms, 'rows': rows, 'result': AN.analyze(rows, plan)}


# ---------------------------------------------------------------- priority_check

def pinned_library():
    """(source root, pinned revision) of the library the kernel replays searches in, or None."""
    import json as _json
    from ..formal_research import workspace as W
    try:
        ws = W.locate()
        rev = _json.loads((ws / 'WORKSPACE_MANIFEST.json').read_text())['mathlib_rev']
    except Exception:
        return None
    root = ws / 'src'
    return (root, rev) if (root / 'Mathlib').is_dir() and isinstance(rev, str) and rev else None


def _library_search(root, pattern, revision):
    from .. import literature as LIT
    return LIT.library_search(root, [pattern], revision=revision)[0]


def priority_problems(get, payload, problem, level, *, library=None, search=_library_search):
    """Returns (problems, recomputed level or None). ``library`` is ``pinned_library()`` (or None when
    the pinned library is not on this machine: CANDIDATE_NOVEL then cannot be replayed here)."""
    from .. import literature as LIT
    from ..learning import equational as Q
    from ..learning.partitions import EquationalAdapter
    from ..learning.statement_panels import eq_of
    if not isinstance(payload, dict) or payload.get('schema') != PRIORITY_SCHEMA or set(payload) != PRIORITY_FIELDS:
        return ['not a replayable priority check (genesis-priority-check-v1 with the literature record)'], None
    if payload['route'] not in PRIORITY_ROUTES:
        return [f'unknown priority route {payload["route"]!r}'], None
    if payload['level'] not in PRIORITY_LEVELS:
        return ['unknown novelty level'], None
    if problem is None or problem.get('claim') != 'theorem' or problem.get('theorem_sha256') != payload['theorem_sha256']:
        return ['the priority check is about a different statement than the claim names'], None
    if payload['level'] != level:
        return [f'the priority check establishes {payload["level"]}, not {level}'], None
    try:
        theorem = get(payload['theorem_sha256'])
    except Exception:
        return ['stored theorem statement missing'], None
    why = theorem_problems(theorem)
    if why:
        return why, None
    for k in ('sources', 'prior_art', 'searches', 'library_searches'):
        if not isinstance(payload[k], list):
            return [f'{k} must be a list'], None
    if len(set(map(str, payload['sources']))) != len(payload['sources']):
        return ['a source is listed twice'], None
    sources, out = {}, []
    for h in payload['sources']:
        try:
            src = get(h)
        except Exception:
            out.append(f'source {str(h)[:12]} is not stored')
            continue
        if not isinstance(src, dict) or src.get('schema') != LIT.SCHEMA or src.get('record') != 'source' \
                or not isinstance(src.get('text'), str) or src.get('fidelity') not in LIT.FIDELITY:
            out.append(f'source {h[:12]} is not a literature source record')
            continue
        if LIT.sha(src['text']) != src.get('text_sha256'):
            out.append(f'source {h[:12]} text does not hash to its recorded text_sha256')
            continue
        if LIT.screen(src['text']):
            out.append(f'source {h[:12]} is flagged by the injection screen: no claim may be taken from it '
                       'until a person adjudicates it')
            continue
        sources[h] = src
    if out:
        return out, None
    adapter = EquationalAdapter()
    target = adapter.normalize(eq_of(theorem['statement']))
    theory = adapter.theory(theorem['system'])
    levels = []
    for i, a in enumerate(payload['prior_art']):
        if not isinstance(a, dict) or set(a) != PRIOR_ART_FIELDS:
            out.append(f'prior art {i}: fields')
            continue
        src = sources.get(a['source_sha256'])
        if src is None:
            out.append(f'prior art {i} quotes a source that is not listed')
            continue
        span = a['span']
        if not (isinstance(span, list) and len(span) == 2 and all(type(x) is int for x in span)
                and 0 <= span[0] < span[1] <= len(src['text'])) or src['text'][span[0]:span[1]] != a['quote']:
            out.append(f'prior art {i}: the quote is not at the recorded span of its source')
            continue
        if a['system'] not in Q.SYSTEMS:
            out.append(f'prior art {i}: unknown system')
            continue
        try:
            eq = adapter.normalize(eq_of(a['statement']))
        except Exception:
            out.append(f'prior art {i}: the formalization is not an equation')
            continue
        if adapter.theory(a['system']) != theory:
            continue                                 # another signature: context, not prior art for this theorem
        rel = adapter.relation_normalized(target, eq)
        if rel is not None:
            levels.append(RELATION_LEVEL[rel])
    if out:
        return out, None
    found = 'REDISCOVERY' if 'REDISCOVERY' in levels else 'VARIANT' if 'VARIANT' in levels else 'CANDIDATE_NOVEL'
    if found != payload['level']:
        return [f'the recorded prior art makes this {found}, not {payload["level"]}'], found
    if found == 'CANDIDATE_NOVEL':
        out += _search_record_problems(payload, sources, library, search)
    return out, found


def _search_record_problems(payload, sources, library, search):
    """A preserved, replayable search record (needed only for CANDIDATE_NOVEL)."""
    out = []
    if not payload['searches'] or not all(isinstance(x, dict) and x for x in payload['searches']):
        out.append('CANDIDATE_NOVEL needs a preserved record of at least one search')
    if not payload['library_searches']:
        return out + ['CANDIDATE_NOVEL needs at least one search of the pinned library']
    if library is None:
        return out + ['the pinned library is not available here, so the library searches cannot be replayed']
    root, rev = library
    covered = [(s['provenance'].get('file'), s['provenance'].get('lines')) for s in sources.values()
               if s['kind'] == 'library' and s['fidelity'] == 'VERBATIM'
               and isinstance(s.get('provenance'), dict) and s['provenance'].get('revision') == rev]
    for i, ls in enumerate(payload['library_searches']):
        if not isinstance(ls, dict) or not isinstance(ls.get('pattern'), str) or ls.get('revision') != rev:
            out.append(f'library search {i} is not a search of the pinned revision')
            continue
        try:
            again = search(root, ls['pattern'], rev)
        except Exception as exc:
            out.append(f'library search {i} cannot be replayed ({type(exc).__name__})')
            continue
        if again != ls:
            out.append(f'library search {i} does not replay to the recorded hits')
            continue
        if ls['hit_count'] != len(ls['hits']):
            out.append(f'library search {i} records only {len(ls["hits"])} of {ls["hit_count"]} hits; narrow it')
            continue
        for h in ls['hits']:
            if not any(f == h['file'] and isinstance(lines, list) and len(lines) == 2 and lines[0] <= h['line'] <= lines[1]
                       for f, lines in covered):
                out.append(f'library hit {h["file"]}:{h["line"]} was not read (no stored excerpt covers it)')
    return out


# ---------------------------------------------------------------- ablation / placebo provenance

def _zero(v):
    return [0] * len(v) if isinstance(v, list) else None


def _rotate(v):
    return list(v[1:]) + list(v[:1]) if isinstance(v, list) and v else None


def _false(v):
    return False


_DSL = {('program', 'weights'): {'ablation': _zero, 'placebo': _rotate,
                                 'meaning': 'ablation: no priority signal (order by the seeded jitter only); '
                                            'placebo: the same weights attached to other features (rotated)'},
        ('program', 'exchange'): {'ablation': _false, 'placebo': None, 'meaning': 'no exchange moves'},
        ('program', 'componentwise'): {'ablation': _false, 'placebo': None, 'meaning': 'no component grouping'}}
INTERVENTIONS = {(kind, path): spec for kind in ('dsl-program-v1', 'dsl-time-matched-v1') for path, spec in _DSL.items()}


def _leaves(x, path=()):
    if isinstance(x, dict):
        out = {}
        for k in sorted(x):
            out.update(_leaves(x[k], path + (k,)))
        return out
    return {path: x}


def intervention_problems(kind, full, altered):
    """Returns (problems, component path or None): is ``altered`` the registered ``kind``
    intervention (ablation or placebo) of ``full`` on exactly one component?"""
    from .. import candidates as C
    if kind not in ('ablation', 'placebo'):
        return ['not an intervention kind'], None
    for name, d in (('candidate', full), ('intervened', altered)):
        why = C.descriptor_problems(d)
        if why:
            return [f'the {name} descriptor does not rebuild: {", ".join(why)}'], None
    for k in ('kind', 'domain', 'implementation', 'resource_profile'):
        if full[k] != altered[k]:
            return [f'the arms differ in {k}: an intervention changes one component of one candidate'], None
    a, b = _leaves(full['parameters']), _leaves(altered['parameters'])
    diff = sorted(p for p in set(a) | set(b) if a.get(p, ...) != b.get(p, ...))
    if len(diff) != 1:
        return [f'the arms differ in {len(diff)} components; an intervention changes exactly one'], None
    path = diff[0]
    spec = INTERVENTIONS.get((full['kind'], path))
    transform = spec and spec[kind]
    if transform is None:
        return [f'no registered {kind} for component {".".join(path)} of {full["kind"]}'], path
    want = transform(a.get(path))
    if want is None or want == a.get(path):
        return [f'the {kind} of {".".join(path)} does not change the candidate\'s value'], path
    if b.get(path) != want:
        return [f'the intervened value of {".".join(path)} is not the registered {kind}'], path
    return [], path


__all__ = ['EXACT_SCHEMA', 'FORMAL_SCHEMA', 'DEV_SCHEMA', 'DEV_SCHEMA_V1', 'dev_comparison', 'LEAN_THEOREM_SCHEMA', 'lean_theorem_object', 'lean_package_problems', 'package_checker_identity', 'THEOREM_SCHEMA', 'PRIORITY_SCHEMA', 'EXACT_METHODS',
           'CONTRACTED', 'INTERVENTIONS', 'theorem_object', 'theorem_problems', 'exact_problems', 'formal_problems',
           'dev_problems', 'priority_problems', 'pinned_library', 'intervention_problems']
