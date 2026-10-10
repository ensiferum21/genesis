"""Campaign state machine with externally verified scientific transitions (spec §33).

    CREATED -> VALIDATED_CONFIG -> DEV_RUNNING -> CANDIDATE_FROZEN
      -> LEAK_SCAN_PASSED -> SEALED_RUNNING -> JUDGED -> RELEASED | REJECTED
    Any state -> ABORTED; any post-freeze state -> INVALIDATED.

Engineering transitions are local. Every scientific transition needs a signed
envelope from the role the registry assigns to it, bound to this campaign's
frozen request; the envelope is stored before the phase changes, so a crash
cannot skip a gate. ABORTED and INVALIDATED only lower what may be claimed,
so they need a recorded reason but no signature.
"""
import json

from ..common import digest
from . import receipts as R
from .roles import load_role_registry
from .signing import verify

TRANSITIONS = {
    'CREATED': {'VALIDATED_CONFIG', 'ABORTED'},
    'VALIDATED_CONFIG': {'DEV_RUNNING', 'ABORTED'},
    'DEV_RUNNING': {'CANDIDATE_FROZEN', 'ABORTED'},
    'CANDIDATE_FROZEN': {'LEAK_SCAN_PASSED', 'INVALIDATED', 'ABORTED'},
    'LEAK_SCAN_PASSED': {'SEALED_RUNNING', 'INVALIDATED', 'ABORTED'},
    'SEALED_RUNNING': {'JUDGED', 'INVALIDATED', 'ABORTED'},
    'JUDGED': {'RELEASED', 'REJECTED', 'INVALIDATED', 'ABORTED'},
    'RELEASED': {'INVALIDATED'}, 'REJECTED': set(), 'INVALIDATED': set(), 'ABORTED': set()}
SCIENTIFIC = {'LEAK_SCAN_PASSED': 'prereg_key', 'SEALED_RUNNING': 'custodian_key', 'JUDGED': 'custodian_key',
              'RELEASED': 'release_key', 'REJECTED': 'release_key'}
LOWERING = {'ABORTED', 'INVALIDATED'}


class PhaseError(ValueError):
    pass


def _check_payload(target, payload, envelope, *, request_hash, receipts):
    """Phase-specific binding. `receipts` holds the envelopes recorded for earlier phases at
    the time of this transition (live state in `advance`, replayed history in `verified_phase`)."""
    if not request_hash:
        raise PhaseError('no frozen evaluation request recorded for this campaign')
    if not isinstance(payload, dict) or payload.get('request_hash') != request_hash:
        raise PhaseError('receipt is bound to a different evaluation request')
    if target == 'LEAK_SCAN_PASSED':
        problems = R.check_anchor(payload)
        if problems:
            raise PhaseError('LEAK_SCAN_PASSED needs a custodian registration anchor with an exposure registry '
                             'root and a panel commitment: ' + '; '.join(problems))
    elif target == 'SEALED_RUNNING':
        anchor = receipts.get('LEAK_SCAN_PASSED')
        if not isinstance(anchor, dict):
            raise PhaseError('no registered anchor precedes the sealed run')
        problems = R.anchor_mismatches(payload, anchor['payload'], anchor)
        if problems:
            raise PhaseError('sealed receipt does not reference the registered anchor: ' + '; '.join(problems))
    elif target == 'JUDGED':
        if payload.get('raw_evidence_complete') is not True or payload.get('completed_rows') != payload.get('expected_rows'):
            raise PhaseError('judgement needs complete raw evidence')
        if receipts.get('SEALED_RUNNING') != envelope:
            raise PhaseError('judgement must use the same signed receipt as the sealed run')
    else:  # RELEASED / REJECTED
        receipt = receipts.get('JUDGED')
        if not isinstance(receipt, dict):
            raise PhaseError('no judged receipt precedes the decision')
        decision = 'RELEASE' if target == 'RELEASED' else 'REJECT'
        if payload.get('schema') != 'genesis-release-decision-v1' or payload.get('decision') != decision:
            raise PhaseError(f'{target} needs a signed {decision} decision')
        if payload.get('receipt_hash') != digest(receipt):
            raise PhaseError('release decision does not reference the judged receipt')
        if target == 'RELEASED' and receipt['payload'].get('outcome') != 'SUPPORTED':
            raise PhaseError('a release needs a judged receipt whose signed outcome is SUPPORTED')


def _frozen_request(store, request_hash=None):
    """The frozen request, which must belong to THIS campaign: same campaign_id, and its bound
    export must be a prefix of this store's own event history (no replay from another campaign)."""
    import zipfile
    from ..common import bytes_hash
    rid = request_hash or store.state('frozen_request_hash')
    row = store.db.execute("SELECT object_hash FROM entities WHERE kind='frozen_request' AND id=?", (rid,)).fetchone()
    if row is None:
        raise PhaseError('the frozen evaluation request is not recorded as an immutable entity')
    request = store.get(row[0])
    if digest(request) != rid:
        raise PhaseError('frozen request does not hash to its recorded identity')
    if request.get('campaign_id') != store.state('campaign_id'):
        raise PhaseError('frozen request names another campaign')
    export = store.root / 'exports' / 'campaign_export.zip'
    if not export.is_file() or bytes_hash(export.read_bytes()) != request.get('campaign_export_sha256'):
        raise PhaseError('the export bound to the frozen request is not this campaign\'s export')
    with zipfile.ZipFile(export) as z:
        exported = z.read('events.jsonl') if 'events.jsonl' in z.namelist() else None
    if exported is None or not (store.root / 'events.jsonl').read_bytes().startswith(exported):
        raise PhaseError('the bound export is not a prefix of this campaign\'s event history')
    return request


def _revoked_keys(store):
    from .evidence import EvidenceKernel
    return EvidenceKernel(store).revoked_keys()


def _open(store, target, envelope, pins, *, request_hash=None):
    """Verify a phase envelope with the same acceptance function the kernel uses."""
    if target in ('RELEASED', 'REJECTED'):
        if R.normalize_key(pins['release_key']) in {R.normalize_key(k) for k in _revoked_keys(store)}:
            raise PhaseError('the pinned release_key is revoked')
        try:
            return verify(envelope, pins['release_key'])
        except Exception as exc:
            raise PhaseError(f'{target} decision is not signed by the pinned release_key: {type(exc).__name__}')
    request = _frozen_request(store, request_hash)
    kind = 'preregistration_anchor' if target == 'LEAK_SCAN_PASSED' else request['evidence_kind']
    payload, problems = R.accept_receipt(envelope, kind, pins, revoked_keys=_revoked_keys(store))
    if problems:
        raise PhaseError(f'{target} envelope rejected: ' + '; '.join(problems[:3]))
    if target == 'LEAK_SCAN_PASSED':
        if payload['registration_slot'] != R.registration_slot(request) or any(
                payload[k] != request[k] for k in ('claim_id', 'statement_hash', 'scope', 'evidence_kind')):
            raise PhaseError('anchor registers a different claim slot than the frozen request')
    return payload


def advance(store, target, *, envelope=None, reason=None, trust_root=None):
    current = store.state('phase', 'CREATED')
    if target not in TRANSITIONS[current]:
        raise PhaseError(f'illegal phase transition {current} -> {target}')
    if target in LOWERING:
        if not isinstance(reason, str) or not reason.strip():
            raise PhaseError(f'{target} needs a recorded reason')
        store.event('PHASE_LOWERED', {'from': current, 'to': target, 'reason': reason})
    elif target in SCIENTIFIC:
        registry, problems = load_role_registry(trust_root)
        if registry is None:
            raise PermissionError('scientific phases need an externally controlled role registry: ' + '; '.join(problems))
        payload = _open(store, target, envelope, registry['pins'])
        receipts = {k: store.state(f'phase_receipt:{k}') for k in SCIENTIFIC}
        _check_payload(target, payload, envelope, request_hash=store.state('frozen_request_hash'), receipts=receipts)
        store.set_state(f'phase_receipt:{target}', envelope)  # persisted before the phase changes
    store.set_state('phase', target)
    return {'from': current, 'to': target}


def verified_phase(store, *, trust_root=None):
    """Re-derive the campaign phase from the event history instead of trusting the mutable
    `phase` state. Every recorded transition must be legal; every scientific one must be
    preceded by its envelope, which must verify now under the trust root (signature, role,
    key revocations) AND pass the same binding checks `advance` applies, against the
    envelopes and frozen request recorded before it. The frozen request may not change
    once LEAK_SCAN_PASSED is reached. Returns {'phase', 'recorded_phase', 'consistent', 'problems'}."""
    registry, reg_problems = load_role_registry(trust_root)
    phase, latest, accepted, problems = 'CREATED', {}, {}, []
    frozen, frozen_at_scan = None, None
    for (raw,) in store.db.execute('SELECT body FROM events ORDER BY seq'):
        body = json.loads(raw)
        if body['kind'] != 'STATE_UPDATED':
            continue
        update = store.get(body['payload'])
        key, value = update['key'], update['value']
        if key == 'frozen_request_hash':
            if frozen_at_scan is not None and value != frozen_at_scan:
                problems.append('frozen request changed after LEAK_SCAN_PASSED')
                break
            frozen = value
        elif key.startswith('phase_receipt:'):
            latest[key.split(':', 1)[1]] = value
        elif key == 'phase':
            if value == phase:
                continue  # idempotent write (e.g. initialization writes CREATED)
            if value not in TRANSITIONS.get(phase, set()):
                problems.append(f'illegal recorded transition {phase} -> {value}')
                break
            if value in SCIENTIFIC:
                if registry is None:
                    problems.append(f'{value} cannot be verified without a trust root: ' + '; '.join(reg_problems[:2]))
                    break
                envelope = latest.get(value)
                try:
                    payload = _open(store, value, envelope, registry['pins'], request_hash=frozen)
                    _check_payload(value, payload, envelope, request_hash=frozen, receipts=accepted)
                except Exception as exc:
                    problems.append(f'{value} envelope does not verify: {exc}')
                    break
                accepted[value] = envelope
                if value == 'LEAK_SCAN_PASSED':
                    frozen_at_scan = frozen
            phase = value
    recorded = store.state('phase', 'CREATED')
    return {'phase': phase, 'recorded_phase': recorded, 'consistent': not problems and phase == recorded,
            'problems': problems}
