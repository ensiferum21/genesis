"""Successor proof custody and checked scoring (Repair C, finding B20-REVIEW-03).

B20 replayed 67 of 68 lemma-using target proofs in Lean, but only for the fixed and
learned policies on the first evaluation seed per system: 67 of the 778 reported target
successes (8.6%). Proof objects of the other scored targets were never stored, so those
scores cannot be checked retroactively. This module makes custody come before counting.

Successor manifest (``genesis-successor-manifest-v1``)
    the run identity, system/axiomatization and its exact axioms, policy and parent, the
    exposure root it ran under, its resource account hash, and every admitted lemma with
    a run-bound uid (``research.lemma_uid``), statement, proof-object hash, direct
    dependencies and premise binding (in prover input order), all by uid. Local names
    such as ``L0`` are display only and cannot carry a lemma from one run into another.

Scored-target record (``genesis-scored-target-v1``)
    task identity, exact statement, the prover's status, budget eligibility, the proof
    object's hash, premise uids in input order, used lemmas and their dependency closure,
    and the manifest it was scored against.

Proof objects live in a content-addressed directory (:class:`ObjectStore`); failed and
malformed attempts may be stored too, without becoming theorems.

Three metrics are always reported separately (:func:`score`):
    prover_reported   E said THEOREM and produced a proof object
    checked           that proof, with its full lemma chain, replayed in Lean against the
                      pinned axioms and bound to the requested statement
    eligible          checked, from an attempt within its budget reservation, on material
                      admitted by the exposure policy, with no revoked ancestor
A checker timeout is CHECK_INCOMPLETE (never falsity, never credit); an infrastructure
failure is CHECK_INFRASTRUCTURE_ERROR and is reported as missing coverage, which a frozen
endpoint may treat as invalidating the run.
"""
import hashlib
from pathlib import Path

from ..common import digest
from . import equational as Q
from .research import lemma_uid, used_inputs

MANIFEST_SCHEMA = 'genesis-successor-manifest-v1'
TARGET_SCHEMA = 'genesis-scored-target-v1'
CHECK_STATUSES = ('CHECKED', 'CHECK_FAILED', 'CHECK_INCOMPLETE', 'CHECK_UNSUPPORTED', 'CHECK_INFRASTRUCTURE_ERROR',
                  'REJECTED_CUSTODY', 'NOT_A_SUCCESS', 'NOT_CHECKED')


def _sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


class ObjectStore:
    """Content-addressed proof objects: ``root/<sha256>``. Reads verify the hash."""

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data):
        data = data if isinstance(data, bytes) else data.encode()
        h = _sha(data)
        p = self.root / h
        if not p.exists():
            tmp = p.with_name(f'.{h}.tmp')
            tmp.write_bytes(data)
            tmp.replace(p)
        return h

    def get(self, h):
        data = (self.root / str(h)).read_bytes()
        if _sha(data) != h:
            raise ValueError('object corruption')
        return data

    def has(self, h):
        try:
            self.get(h)
            return True
        except (OSError, ValueError):
            return False


def checker_identity():
    """Identity of the replay route: pinned Lean, formal workspace pins and the translator."""
    import json
    root = Path(__file__).resolve().parents[3]
    pins = json.loads((root / 'toolchain' / 'PINS.json').read_text())
    ws = json.loads((root / 'toolchain' / 'FORMAL_WORKSPACE.json').read_text())
    translator = (root / 'src' / 'genesis' / 'formal_research' / 'fof_lean.py').read_bytes()
    checker = (root / 'src' / 'genesis' / 'formal_research' / 'checker.py').read_bytes()
    ident = {'lean': pins['lean'], 'workspace': digest(ws), 'translator_sha256': _sha(translator),
             'checker_sha256': _sha(checker)}
    return dict(ident, identity=digest(ident))


def _formula_text(f):
    from ..fol import to_tptp
    return to_tptp(f)


def _eq_of(text):
    from ..fol import parse
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    return (f[1], f[2])


# ---------------------------------------------------------------- building records

def successor_manifest(run, objects, *, parent='initial-empty-library', policy_identity=None, exposure_root=None):
    """Freeze a research run's successor into a manifest; proof objects go to ``objects``."""
    system = run['system']
    axioms = [_formula_text(a) for a in Q.axioms(system)]
    lemmas = []
    for lem in run['library']:
        psha = objects.put(lem['proof'])
        if lem.get('proof_sha256') not in (None, psha):
            raise ValueError('library proof hash does not match its proof object')
        lemmas.append({'uid': lem['uid'], 'local': lem['id'], 'statement': lem['text'], 'proof_sha256': psha,
                       'uses_uids': list(lem['uses_uids']), 'premise_uids': list(lem['premise_uids']),
                       'attempt_id': lem.get('attempt_id')})
    acct = run.get('account') or {}
    body = {'schema': MANIFEST_SCHEMA, 'run_id': run['run_id'], 'system': system, 'axioms': axioms,
            'axioms_sha256': digest(axioms), 'policy': run['policy'], 'policy_identity': policy_identity,
            'parent': parent, 'exposure_root': exposure_root, 'account_sha256': acct.get('account_sha256'),
            'budget_sha256': acct.get('budget_sha256'), 'lemmas': lemmas, 'revocation_context': []}
    return dict(body, manifest_id=digest(body))


def closure(manifest, uids):
    by = {l['uid']: l for l in manifest['lemmas']}
    seen, stack = set(), list(uids)
    while stack:
        u = stack.pop()
        if u in seen or u not in by:
            continue
        seen.add(u)
        stack += by[u]['uses_uids']
    return sorted(seen)


def target_records(evaluation, manifest, objects, *, panel_id, task_ids=None, exposure_ok=True):
    """One custody record per scored target of ``evaluation`` (from research.evaluate_successor)."""
    by_local = {l['local']: l['uid'] for l in manifest['lemmas']}
    out = []
    for n, row in enumerate(evaluation['rows']):
        reported = row['status'] in ('PROVED', 'PROVED_NOT_CREDITED') and bool(row.get('proof'))
        psha = objects.put(row['proof']) if reported else None
        prem = [by_local.get(p) for p in row.get('premise_ids', [])]
        used = [by_local.get(p) for p in row.get('lemmas_used', [])]
        body = {'schema': TARGET_SCHEMA, 'panel_id': panel_id,
                'task_id': (task_ids[n] if task_ids else row.get('task_id', n)), 'statement': row['target'],
                'statement_sha256': _sha(row['target']), 'prover_status': row['status'], 'prover_reported': reported,
                'budget_eligible': bool(row.get('eligible')) and reported, 'exposure_ok': bool(exposure_ok),
                'attempt_id': row.get('attempt_id'), 'proof_sha256': psha, 'premise_uids': prem,
                'lemmas_used_uids': used, 'closure_uids': closure(manifest, [u for u in used if u]),
                'manifest_id': manifest['manifest_id']}
        out.append(dict(body, record_id=digest(body)))
    return out


# ---------------------------------------------------------------- pure validation

def _p(code, **kw):
    return dict({'code': code}, **kw)


def successor_problems(manifest, objects, trust_context=None):
    """Structural custody check of a successor manifest; no tool runs. Returns problems."""
    tc = trust_context or {}
    out = []
    if not isinstance(manifest, dict) or manifest.get('schema') != MANIFEST_SCHEMA:
        return [_p('UNKNOWN_MANIFEST')]
    body = {k: v for k, v in manifest.items() if k != 'manifest_id'}
    if digest(body) != manifest.get('manifest_id'):
        out.append(_p('MANIFEST_ID_MISMATCH'))
    system = manifest.get('system')
    if system not in Q.SYSTEMS:
        return out + [_p('UNKNOWN_SYSTEM')]
    if manifest['axioms'] != [_formula_text(a) for a in Q.axioms(system)]:
        out.append(_p('DISALLOWED_AXIOMS', detail='manifest axioms differ from the pinned system axioms'))
    seen_local, seen_uid, earlier = set(), set(), set()
    all_uids = {x['uid'] for x in manifest['lemmas']}
    revoked = set(tc.get('revoked_uids', ()))
    for i, lem in enumerate(manifest['lemmas']):
        if lem['local'] in seen_local:
            out.append(_p('DUPLICATE_LOCAL_NAME', index=i))
        if lem['uid'] in seen_uid:
            out.append(_p('DUPLICATE_UID', index=i))
        seen_local.add(lem['local'])
        seen_uid.add(lem['uid'])
        try:
            objects.get(lem['proof_sha256'])
            present = True
        except (OSError, ValueError):
            out.append(_p('PROOF_MISSING_OR_ALTERED', index=i, uid=lem['uid']))
            present = False
        if present and lemma_uid(manifest['run_id'], lem['local'], lem['statement'],
                                 lem['proof_sha256']) != lem['uid']:
            out.append(_p('UID_MISMATCH', index=i, uid=lem['uid']))
        try:
            if not Q.holds(_eq_of(lem['statement']), Q.SYSTEMS[system]['decider']):
                out.append(_p('FALSE_LEMMA', index=i, uid=lem['uid']))
        except Exception:
            out.append(_p('MALFORMED_STATEMENT', index=i))
        for u in lem['premise_uids']:
            if u not in earlier:
                out.append(_p('FOREIGN_OR_LATER_PREMISE' if u not in all_uids else 'CYCLE_OR_FORWARD_REFERENCE',
                              index=i, uid=u))
        if not set(lem['uses_uids']) <= set(lem['premise_uids']):
            out.append(_p('USE_OUTSIDE_PREMISES', index=i, uid=lem['uid']))
        earlier.add(lem['uid'])
    for i, lem in enumerate(manifest['lemmas']):
        bad = (set(closure(manifest, [lem['uid']])) | {lem['uid']}) & revoked
        if bad:
            out.append(_p('REVOKED_ANCESTOR', index=i, uid=lem['uid'], revoked=sorted(bad)))
    return out


def target_problems(record, manifest, *, task_statement, objects, trust_context=None):
    """Binding and custody check of one scored-target record against its manifest."""
    tc = trust_context or {}
    out = []
    body = {k: v for k, v in record.items() if k != 'record_id'}
    if record.get('schema') != TARGET_SCHEMA or digest(body) != record.get('record_id'):
        out.append(_p('RECORD_ID_MISMATCH'))
    if record.get('manifest_id') != manifest.get('manifest_id'):
        out.append(_p('WRONG_MANIFEST'))
    if record['statement'] != task_statement:
        out.append(_p('WRONG_TARGET'))
    if not record['prover_reported']:
        return out
    try:
        proof = objects.get(record['proof_sha256']).decode()
    except (OSError, ValueError, TypeError):
        return out + [_p('PROOF_MISSING_OR_ALTERED')]
    uids = {l['uid'] for l in manifest['lemmas']}
    for u in record['premise_uids']:
        if u not in uids:
            out.append(_p('FOREIGN_OR_MISSING_PREMISE', uid=u))
    n_ax = len(manifest['axioms'])
    used_idx = [i for i in used_inputs(proof, n_ax + len(record['premise_uids'])) if i >= n_ax]
    used = [record['premise_uids'][i - n_ax] for i in used_idx]
    if sorted(map(str, used)) != sorted(map(str, record['lemmas_used_uids'])):
        out.append(_p('USED_LEMMAS_DO_NOT_MATCH_PROOF'))
    if closure(manifest, [u for u in used if u]) != record['closure_uids']:
        out.append(_p('CLOSURE_MISMATCH'))
    bad = set(record['closure_uids']) & set(tc.get('revoked_uids', ()))
    if bad:
        out.append(_p('REVOKED_ANCESTOR', revoked=sorted(bad)))
    return out


# ---------------------------------------------------------------- replay

def lean_entries(manifest, objects, record):
    """The lemma chain for ``fof_lean.replay`` built from the manifest and stored objects only."""
    from ..fol import parse
    by = {l['uid']: l for l in manifest['lemmas']}
    proof = objects.get(record['proof_sha256']).decode()
    n_ax = len(manifest['axioms'])
    used_idx = [i for i in used_inputs(proof, n_ax + len(record['premise_uids'])) if i >= n_ax]
    goal_uids = [record['premise_uids'][i - n_ax] for i in used_idx]
    order, index = [], {}

    def visit(u, stack=()):
        if u in index:
            return
        if u in stack:
            raise ValueError('cyclic lemma dependency')
        for d in by[u]['uses_uids']:
            visit(d, stack + (u,))
        index[u] = len(order)
        order.append(u)
    for g in goal_uids:
        visit(g)
    entries = []
    for u in order:
        lem = by[u]
        deps = [index[d] for d in lem['uses_uids']]
        pos = [n_ax + lem['premise_uids'].index(d) for d in lem['uses_uids']]
        entries.append((parse(lem['statement']), objects.get(lem['proof_sha256']).decode(), deps, pos))
    return proof, entries, [index[g] for g in goal_uids], used_idx


def replay_target(record, manifest, objects, *, task_statement, trust_context=None, replay_fn=None, name=None):
    """Replay one scored target from custody: validation first, then Lean on the chain."""
    from ..fol import parse
    if not record['prover_reported']:
        return {'status': 'NOT_A_SUCCESS', 'record_id': record['record_id']}
    problems = successor_problems(manifest, objects, trust_context) + \
        target_problems(record, manifest, task_statement=task_statement, objects=objects, trust_context=trust_context)
    if problems:
        return {'status': 'REJECTED_CUSTODY', 'record_id': record['record_id'],
                'problems': sorted({p['code'] for p in problems})}
    if replay_fn is None:
        from ..formal_research.fof_lean import replay as replay_fn
    try:
        proof, entries, gd, gp = lean_entries(manifest, objects, record)
    except (KeyError, ValueError) as exc:
        return {'status': 'REJECTED_CUSTODY', 'record_id': record['record_id'], 'problems': [type(exc).__name__]}
    axioms = [parse(a) for a in manifest['axioms']]
    try:
        r = replay_fn(name or f'cust-{record["record_id"][:16]}', axioms, parse(record['statement']), proof,
                      lemmas=entries, goal_deps=gd, goal_positions=gp)
    except Exception as exc:                       # the checker route itself failed
        return {'status': 'CHECK_INFRASTRUCTURE_ERROR', 'record_id': record['record_id'],
                'reason': type(exc).__name__}
    if r.get('status') == 'THEOREM_CHECKED':
        status = 'CHECKED'
    elif r.get('outcome') == 'TIMEOUT':
        status = 'CHECK_INCOMPLETE'
    elif r.get('outcome') == 'CHECKER_FAILURE':
        status = 'CHECK_INFRASTRUCTURE_ERROR'
    elif r.get('outcome') is None:
        status = 'CHECK_UNSUPPORTED'               # the translation could not express this proof
    else:
        status = 'CHECK_FAILED'
    return {'status': status, 'record_id': record['record_id'], 'chain_lemmas': len(entries),
            'lean_status': r.get('lean_status'), 'reason': r.get('reason'),
            'checker': (trust_context or {}).get('checker_identity')}


# ---------------------------------------------------------------- scoring

def score(records, checks, *, trust_context=None):
    """The three metrics plus coverage. ``checks``: {record_id: replay result}."""
    tc = trust_context or {}
    revoked = set(tc.get('revoked_uids', ()))
    current = tc.get('checker_identity')
    revoked_checkers = set(tc.get('revoked_checkers', ()))
    reported = [r for r in records if r['prover_reported']]
    checked, eligible, incomplete, env_changed = [], [], [], []
    for r in reported:
        c = checks.get(r['record_id'])
        if c is None:
            continue
        if c.get('checker') in revoked_checkers:
            env_changed.append(r['record_id'])
            continue
        if current is not None and c.get('checker') not in (None, current):
            env_changed.append(r['record_id'])
            continue
        if c['status'] in ('CHECK_INCOMPLETE', 'CHECK_INFRASTRUCTURE_ERROR'):
            incomplete.append(r['record_id'])
        if c['status'] != 'CHECKED' or set(r['closure_uids']) & revoked:
            continue
        checked.append(r)
        if r['budget_eligible'] and r['exposure_ok']:
            eligible.append(r)
    attempted = sum(1 for r in reported if r['record_id'] in checks)
    return {'targets': len(records), 'prover_reported': len(reported), 'checked': len(checked),
            'eligible': len(eligible), 'replay_attempted': attempted,
            'replay_coverage': round(attempted / len(reported), 4) if reported else None,
            'check_incomplete': len(incomplete), 'needs_recheck_environment': len(env_changed),
            'endpoint_note': 'eligible = checked AND within budget AND exposure-admitted AND no revoked ancestor'}


__all__ = ['ObjectStore', 'successor_manifest', 'target_records', 'successor_problems', 'target_problems',
           'replay_target', 'lean_entries', 'score', 'closure', 'checker_identity', 'MANIFEST_SCHEMA',
           'TARGET_SCHEMA', 'CHECK_STATUSES']
