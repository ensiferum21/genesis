"""Frozen, data-only candidate DSL and private sealed evaluation.

No arbitrary Python candidate is executed; no raw sealed task reaches a candidate.
The public result contains aggregate statistics, never task IDs or answers.
This module is a reference implementation, not evidence of external custody.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

SCHEMA = 'genesis-reference-evaluator-v1'
ARMS = ('D', 'U', 'V2n', 'V2p')
MAX_AST_NODES = 128
MAX_AST_DEPTH = 12
MAX_TASKS = 100_000
MAX_ABS_INT = 10**12
OPS = {'const', 'input', 'add', 'sub', 'mul', 'eq', 'lt', 'if', 'min', 'max'}


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _int(v: Any) -> int:
    if type(v) is not int or abs(v) > MAX_ABS_INT:
        raise ValueError('integer type/range violation')
    return v


def validate_expr(node: Any, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_AST_NODES or depth > MAX_AST_DEPTH:
        raise ValueError('candidate expression exceeds bounds')
    if not isinstance(node, dict) or node.get('op') not in OPS:
        raise ValueError('invalid candidate expression')
    op = node['op']
    expected = {'const': {'op', 'value'}, 'input': {'op', 'name'},
                'if': {'op', 'test', 'yes', 'no'}}.get(op, {'op', 'a', 'b'})
    if set(node) != expected:
        raise ValueError('unexpected candidate fields')
    if op == 'const':
        _int(node['value'])
    elif op == 'input':
        if not isinstance(node['name'], str) or not node['name'].isidentifier() or len(node['name']) > 40:
            raise ValueError('invalid input name')
    elif op == 'if':
        for k in ('test', 'yes', 'no'):
            validate_expr(node[k], depth+1, counter)
    else:
        for k in ('a', 'b'):
            validate_expr(node[k], depth+1, counter)


def eval_expr(node: dict, features: dict[str, int]) -> int | bool:
    op = node['op']
    if op == 'const':
        return _int(node['value'])
    if op == 'input':
        return _int(features[node['name']])
    if op == 'if':
        test = eval_expr(node['test'], features)
        if type(test) is not bool:
            raise ValueError('if condition must be boolean')
        return eval_expr(node['yes'] if test else node['no'], features)
    a, b = eval_expr(node['a'], features), eval_expr(node['b'], features)
    if type(a) is not int or type(b) is not int:
        raise ValueError('arithmetic/comparison operands must be integers')
    if op == 'add': return _int(a+b)
    if op == 'sub': return _int(a-b)
    if op == 'mul': return _int(a*b)
    if op == 'eq': return a == b
    if op == 'lt': return a < b
    if op == 'min': return min(a,b)
    if op == 'max': return max(a,b)
    raise ValueError('unknown operator')


def _validate_pool(pool: Any) -> None:
    if not isinstance(pool, list) or not (1 <= len(pool) <= MAX_TASKS):
        raise ValueError('invalid sealed pool size')
    ids = set()
    for task in pool:
        if not isinstance(task, dict) or set(task) != {'id', 'features', 'answer'}:
            raise ValueError('invalid sealed task shape')
        tid = task['id']
        if not isinstance(tid, str) or not tid or len(tid) > 128 or tid in ids:
            raise ValueError('invalid/duplicate sealed task ID')
        ids.add(tid)
        if not isinstance(task['features'], dict) or len(task['features']) > 32:
            raise ValueError('invalid feature map')
        for k,v in task['features'].items():
            if not isinstance(k,str) or not k.isidentifier() or len(k)>40:
                raise ValueError('invalid feature name')
            _int(v)
        _int(task['answer'])


def _validate_prereg(prereg: Any, pool_hash: str, candidate_hashes: dict[str,str]) -> None:
    if not isinstance(prereg, dict) or set(prereg) != {'protocol','pool_sha256','candidate_sha256',
                                                      'evaluation_budget_per_arm','campaign_id'}:
        raise ValueError('invalid preregistration shape')
    if prereg['protocol'] != SCHEMA or prereg['pool_sha256'] != pool_hash:
        raise ValueError('preregistration does not bind sealed pool')
    if prereg['candidate_sha256'] != candidate_hashes:
        raise ValueError('preregistration does not bind all candidate arms')
    if type(prereg['evaluation_budget_per_arm']) is not int or prereg['evaluation_budget_per_arm'] <= 0:
        raise ValueError('invalid evaluation budget')
    if not isinstance(prereg['campaign_id'],str) or not prereg['campaign_id']:
        raise ValueError('invalid campaign ID')


def evaluate_frozen(pool_path: Path, candidate_paths: dict[str,Path], prereg_path: Path,
                    key_path: Path, out_dir: Path, *, custodian_id: str,
                    reservation_dir: Path | None = None) -> dict:
    """Run only under a trusted custodian. Output aggregate, receipt, manifest.

    No sealed task identifiers, inputs, answers, or per-task outcomes are exported.
    A signature authenticates a key holder, NOT its independence or OS isolation.
    """
    if set(candidate_paths) != set(ARMS):
        raise ValueError('must supply exactly four matched arms')
    if not isinstance(custodian_id,str) or not custodian_id.strip():
        raise ValueError('missing custodian ID')
    pool_bytes = pool_path.read_bytes()
    pool = json.loads(pool_bytes)
    _validate_pool(pool)
    programs = {}
    candidate_hashes = {}
    for arm in ARMS:
        data = candidate_paths[arm].read_bytes()
        program = json.loads(data)
        if not isinstance(program,dict) or set(program) != {'expr'}:
            raise ValueError('invalid candidate shape')
        validate_expr(program['expr'])
        programs[arm] = program['expr']
        candidate_hashes[arm] = sha256(data)
    prereg_bytes = prereg_path.read_bytes()
    prereg = json.loads(prereg_bytes)
    _validate_prereg(prereg, sha256(pool_bytes), candidate_hashes)
    if prereg['evaluation_budget_per_arm'] < len(pool):
        raise ValueError('pre-registered budget insufficient for all sealed tasks')
    # GEN-AUD-027: sealed task evaluation MUST have a durable custodian-side
    # reservation. The old optional path allowed unlimited reruns. Moreover,
    # reserving only prereg_sha256 allowed the same pool to be evaluated again
    # under a changed campaign, budget, candidate, task order, or task ID.
    # Reserve the actual *task contents* (features + answer, excluding ID) in
    # one SQLite transaction before any prediction is executed. A task that
    # overlaps any prior attempt is rejected even if its pool/prereg differs.
    # This is local replay protection, NOT independently controlled custody.
    if reservation_dir is None:
        raise ValueError('custodian reservation directory required; unreserved evaluation forbidden')
    if not reservation_dir.is_dir() or reservation_dir.is_symlink():
        raise ValueError('custodian reservation directory must preexist and not be a symlink')
    st = reservation_dir.stat()
    if os.name == 'posix' and (st.st_uid != os.geteuid() or st.st_mode & (stat.S_IRWXG | stat.S_IRWXO)):
        raise ValueError('custodian reservation directory must be owner-controlled')
    # Contents are hashed only inside the custodian process; neither the raw
    # tasks nor these low-entropy fingerprints are exported to research.
    fingerprints = [sha256(canonical({'features':task['features'], 'answer':task['answer']}))
                    for task in pool]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError('duplicate sealed task contents in one pool')
    db_path = reservation_dir / 'sealed_attempts.sqlite3'
    if db_path.is_symlink():
        raise ValueError('reservation database symlink forbidden')
    db = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS reservations ('
                   'task_sha256 TEXT PRIMARY KEY, prereg_sha256 TEXT NOT NULL, '
                   'pool_sha256 TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS attempts ('
                   'prereg_sha256 TEXT PRIMARY KEY, pool_sha256 TEXT NOT NULL, '
                   'task_count INTEGER NOT NULL, state TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT INTO attempts VALUES (?,?,?,?)',
                   (sha256(prereg_bytes), sha256(pool_bytes), len(pool),
                    'RESERVED_NO_AUTOMATIC_RETRY'))
        db.executemany('INSERT INTO reservations VALUES (?,?,?)',
                       [(f, sha256(prereg_bytes), sha256(pool_bytes)) for f in fingerprints])
        db.execute('COMMIT')
    except sqlite3.IntegrityError as exc:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise FileExistsError('sealed task or preregistration already reserved; do not rerun') from exc
    except BaseException:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise
    finally:
        db.close()
    # Entire pool evaluated once, with identical task order and budget for each arm.
    aggregates = {}
    for arm in ARMS:
        correct, failures = 0, 0
        for task in pool:
            try:
                predicted = eval_expr(programs[arm], task['features'])
                if type(predicted) is not int:
                    failures += 1
                elif predicted == task['answer']:
                    correct += 1
            except (ValueError, KeyError, OverflowError, TypeError):
                failures += 1
        aggregates[arm] = {'tasks':len(pool),'correct':correct,'execution_failures':failures,
                           'budget_charged':len(pool)}
    public = {'schema':SCHEMA,'campaign_id':prereg['campaign_id'],
              'prereg_sha256':sha256(prereg_bytes), 'pool_sha256':sha256(pool_bytes),
              'candidate_sha256':candidate_hashes, 'arms':aggregates,
              'sealed_task_payloads_exported':False, 'independent_custody_proven':False}
    public_bytes = canonical(public)
    evaluator_hash = file_sha(Path(__file__))
    manifest = {'schema':SCHEMA,'prereg_sha256':sha256(prereg_bytes),
                'pool_sha256':sha256(pool_bytes),'candidate_sha256':candidate_hashes,
                'evaluator_sha256':evaluator_hash,'results_sha256':sha256(public_bytes),
                'independent_custody_proven':False}
    manifest_bytes = canonical(manifest)
    # Only a trusted custodian should possess this private key; no key is exported.
    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError('Ed25519 signing key required')
    from scripts.external_custody_protocol import FIELDS, canonical_bytes
    # Multi-arm receipt: candidate hash is of canonical map of the four pinned arm hashes.
    claims = {'candidate_sha256':sha256(canonical(candidate_hashes)),
              'prereg_sha256':sha256(prereg_bytes),'pool_sha256':sha256(pool_bytes),
              'evaluator_sha256':evaluator_hash,'results_sha256':sha256(public_bytes),
              'manifest_sha256':sha256(manifest_bytes),'custodian_id':custodian_id,
              'protocol_version':'genesis-custody-v1'}
    if set(claims) != set(FIELDS):
        raise ValueError('custody receipt schema mismatch')
    receipt = {'claims':claims,'signature_b64':base64.b64encode(
        private_key.sign(canonical_bytes(claims))).decode()}
    out_dir.mkdir(parents=True,exist_ok=False)
    (out_dir/'aggregate.json').write_bytes(public_bytes)
    (out_dir/'manifest.json').write_bytes(manifest_bytes)
    (out_dir/'receipt.json').write_bytes(canonical(receipt))
    return {'aggregate':public,'manifest':manifest,'receipt':receipt}


def _validate_public_bundle(public: Any, manifest: Any) -> None:
    """Check internal accounting, never claim that reported scores are true.

    A signature on an impossible aggregate (e.g. 999 correct out of 1 task)
    cannot count as even internally consistent evidence. Only an independent
    evaluator with its private task data can attest actual outcomes.
    """
    if not isinstance(public, dict) or set(public) != {
            'schema', 'campaign_id', 'prereg_sha256', 'pool_sha256',
            'candidate_sha256', 'arms', 'sealed_task_payloads_exported',
            'independent_custody_proven'}:
        raise ValueError('invalid aggregate schema')
    if public['schema'] != SCHEMA or not isinstance(public['campaign_id'], str) or not public['campaign_id']:
        raise ValueError('invalid aggregate campaign/schema')
    if public['sealed_task_payloads_exported'] is not False or public['independent_custody_proven'] is not False:
        raise ValueError('untrusted aggregate custody/export claim')
    arms = public['arms']
    if not isinstance(arms, dict) or set(arms) != set(ARMS):
        raise ValueError('missing or unexpected comparison arm')
    task_counts = set()
    for arm in ARMS:
        counts = arms[arm]
        if not isinstance(counts, dict) or set(counts) != {
                'tasks', 'correct', 'execution_failures', 'budget_charged'}:
            raise ValueError('invalid per-arm accounting schema')
        if any(type(v) is not int or v < 0 for v in counts.values()):
            raise ValueError('invalid per-arm accounting values')
        n = counts['tasks']
        if not 1 <= n <= MAX_TASKS or counts['budget_charged'] != n:
            raise ValueError('per-arm budget/task mismatch')
        if counts['correct'] + counts['execution_failures'] > n:
            raise ValueError('impossible per-arm score')
        task_counts.add(n)
    if len(task_counts) != 1:
        raise ValueError('unequal per-arm task counts')
    if not isinstance(manifest, dict) or set(manifest) != {
            'schema', 'prereg_sha256', 'pool_sha256', 'candidate_sha256',
            'evaluator_sha256', 'results_sha256', 'independent_custody_proven'}:
        raise ValueError('invalid results manifest schema')
    if manifest['schema'] != SCHEMA or manifest['independent_custody_proven'] is not False:
        raise ValueError('untrusted results manifest custody claim')


def verify_bundle(out_dir: Path, trusted_public_key_b64: str, *, expected_prereg_sha256: str,
                  expected_pool_sha256: str, expected_candidate_hashes: dict[str,str],
                  expected_evaluator_sha256: str, expected_task_count: int,
                  expected_campaign_id: str, expected_custodian_id: str,
                  expected_prereg_budget_per_arm: int,
                  expected_prereg_bytes: bytes) -> dict:
    """Research-side consistency checks against independently pinned expectations.

    GEN-AUD-025: A valid signer can sign a partial 1-of-300 aggregate or an
    unrelated campaign/custodian. A signature alone never establishes that the
    full expected evaluation was performed. All expected fields must come from
    an out-of-band custodian/release authority; the signer may still lie, and
    this method NEVER certifies independent custody or correct mathematics.
    """
    if type(expected_task_count) is not int or not 1 <= expected_task_count <= MAX_TASKS:
        raise ValueError('independently expected task count required')
    if (type(expected_prereg_budget_per_arm) is not int
            or expected_prereg_budget_per_arm < expected_task_count):
        raise ValueError('independently expected per-arm budget required')
    if not isinstance(expected_campaign_id, str) or not expected_campaign_id.strip():
        raise ValueError('independently expected campaign ID required')
    if not isinstance(expected_custodian_id, str) or not expected_custodian_id.strip():
        raise ValueError('independently expected custodian ID required')
    # GEN-AUD-026: the claimed external budget must be checked against the
    # actual, hash-pinned preregistration document. Checking only budget >= N
    # allowed a 1-task preregistration to pass with an expected budget of 999.
    # The caller must obtain these bytes from the separately frozen prereg;
    # a local copy alone does not establish an out-of-band timestamp.
    if type(expected_prereg_bytes) is not bytes:
        raise ValueError('frozen preregistration bytes required to verify budget')
    try:
        frozen_prereg = json.loads(expected_prereg_bytes)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('invalid frozen preregistration document') from exc
    if canonical(frozen_prereg) != expected_prereg_bytes:
        raise ValueError('noncanonical frozen preregistration document')
    if sha256(expected_prereg_bytes) != expected_prereg_sha256:
        raise ValueError('frozen preregistration hash differs from independently expected hash')
    _validate_prereg(frozen_prereg, expected_pool_sha256, expected_candidate_hashes)
    if frozen_prereg['campaign_id'] != expected_campaign_id:
        raise ValueError('frozen preregistration campaign differs from expected campaign')
    if frozen_prereg['evaluation_budget_per_arm'] != expected_prereg_budget_per_arm:
        raise ValueError('frozen preregistration budget differs from independently expected budget')
    from scripts.external_custody_protocol import verify_receipt
    public_bytes = (out_dir/'aggregate.json').read_bytes()
    manifest_bytes = (out_dir/'manifest.json').read_bytes()
    public = json.loads(public_bytes)
    manifest = json.loads(manifest_bytes)
    receipt = json.loads((out_dir/'receipt.json').read_bytes())
    _validate_public_bundle(public, manifest)
    if public['campaign_id'] != expected_campaign_id:
        raise ValueError('aggregate campaign ID differs from independently expected campaign')
    for arm in ARMS:
        if public['arms'][arm]['tasks'] != expected_task_count:
            raise ValueError('partial or unexpected per-arm task count')
        if public['arms'][arm]['budget_charged'] != expected_task_count:
            raise ValueError('partial or unexpected per-arm resource charge')
    if canonical(public) != public_bytes or canonical(manifest) != manifest_bytes:
        raise ValueError('noncanonical public evidence')
    claims = receipt['claims']
    if claims.get('custodian_id') != expected_custodian_id:
        raise ValueError('receipt custodian ID differs from independently expected custodian')
    if (claims['results_sha256'] != sha256(public_bytes)
            or claims['manifest_sha256'] != sha256(manifest_bytes)
            or claims['candidate_sha256'] != sha256(canonical(expected_candidate_hashes))
            or claims['prereg_sha256'] != expected_prereg_sha256
            or claims['pool_sha256'] != expected_pool_sha256
            or claims['evaluator_sha256'] != expected_evaluator_sha256):
        raise ValueError('receipt not bound to frozen expected inputs')
    if (manifest['results_sha256'] != claims['results_sha256']
            or manifest['candidate_sha256'] != expected_candidate_hashes
            or manifest['prereg_sha256'] != expected_prereg_sha256
            or manifest['pool_sha256'] != expected_pool_sha256
            or manifest['evaluator_sha256'] != claims['evaluator_sha256']):
        raise ValueError('manifest inconsistency')
    if (public['prereg_sha256'] != expected_prereg_sha256
            or public['pool_sha256'] != expected_pool_sha256
            or public['candidate_sha256'] != expected_candidate_hashes):
        raise ValueError('aggregate inconsistent with frozen inputs')
    if public.get('independent_custody_proven') is not False:
        raise ValueError('local reference cannot claim independent custody')
    verified = verify_receipt(receipt, trusted_public_key_b64)
    return {'signature_valid':verified['signature_valid'], 'bundle_hashes_valid':True,
            'expected_task_count_matched':True, 'expected_campaign_id_matched':True,
            'expected_custodian_id_matched':True,
            'expected_prereg_budget_matched':True,
            'independent_custody_proven':False, 'promotion_allowed':False}
