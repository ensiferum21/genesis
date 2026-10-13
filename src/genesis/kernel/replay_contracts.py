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


__all__ = ['EXACT_SCHEMA', 'FORMAL_SCHEMA', 'DEV_SCHEMA', 'THEOREM_SCHEMA', 'PRIORITY_SCHEMA', 'EXACT_METHODS',
           'CONTRACTED', 'INTERVENTIONS', 'theorem_object', 'theorem_problems', 'exact_problems', 'formal_problems',
           'dev_problems', 'priority_problems', 'pinned_library', 'intervention_problems']
