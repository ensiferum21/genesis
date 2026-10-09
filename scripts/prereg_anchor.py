"""External preregistration-anchor verifier (DEV integration, NOT a custodian).

A local prereg JSON and its .lock can be rewritten together. This verifier
requires a signed, out-of-band anchor, an independently pinned public key,
independently expected experiment digests, and a trusted evaluation start time.
Even a valid signature cannot prove that the signer is independent, that the
clock is trustworthy, or that the sealed pool is protected. Promotion is never
authorized here. Do not generate signing keys in the research process.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from gap_engine.experiments.prereg import PreregViolation, load_verified
from gap_engine.kernel.ledger import _canonical, sha256_hex

REQUIRED_DIGESTS = ('preregistration_sha256', 'candidate_sha256',
                    'evaluator_sha256', 'pool_sha256')
CLAIMS = set(REQUIRED_DIGESTS) | {'schema', 'custodian_id', 'issued_at_utc'}
HEX = set('0123456789abcdef')


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise PreregViolation('invalid anchor timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise PreregViolation('invalid anchor timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise PreregViolation('anchor timestamp must be UTC')
    return parsed.astimezone(timezone.utc)


def verify_prereg_anchor(prereg_path: Path, anchor: dict,
                         independently_pinned_public_key_pem: bytes,
                         expected_digests: dict[str, str],
                         evaluation_start_utc: str) -> dict:
    """Verify a signed declaration without treating it as independent custody.

    `expected_digests`, public key and evaluation_start_utc must be supplied
    by a *separate* release/custody authority, not derived from this anchor.
    Returns descriptive evidence only; never approval to use a sealed pool.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(anchor, dict) or set(anchor) != {'payload', 'signature_ed25519_base64'}:
        raise PreregViolation('invalid anchor envelope')
    payload = anchor['payload']
    if not isinstance(payload, dict) or set(payload) != CLAIMS:
        raise PreregViolation('invalid anchor claims')
    if payload['schema'] != 'genesis-prereg-anchor-v1':
        raise PreregViolation('unsupported anchor schema')
    if not isinstance(payload['custodian_id'], str) or not payload['custodian_id'].strip():
        raise PreregViolation('missing custodian identity')
    for key in REQUIRED_DIGESTS:
        expected = expected_digests.get(key)
        if not isinstance(expected, str) or len(expected) != 64 or any(x not in HEX for x in expected):
            raise PreregViolation('invalid independently expected digest: ' + key)
        if payload[key] != expected:
            raise PreregViolation('anchor digest mismatch: ' + key)
    plan = load_verified(str(prereg_path))  # local consistency is necessary, not sufficient
    local_digest = sha256_hex(_canonical(plan))
    if local_digest != expected_digests['preregistration_sha256']:
        raise PreregViolation('prereg differs from external anchor')
    if _utc(payload['issued_at_utc']) >= _utc(evaluation_start_utc):
        raise PreregViolation('anchor is not earlier than evaluation start')
    if not isinstance(independently_pinned_public_key_pem, bytes):
        raise PreregViolation('no pinned external public key')
    try:
        key = serialization.load_pem_public_key(independently_pinned_public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise PreregViolation('not an Ed25519 key')
        sig = base64.b64decode(anchor['signature_ed25519_base64'], validate=True)
        key.verify(sig, json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=True, allow_nan=False).encode('utf-8'))
    except (ValueError, TypeError) as exc:
        raise PreregViolation('invalid external anchor signature or key') from exc
    except Exception as exc:
        # Includes cryptography.exceptions.InvalidSignature; no data leaked.
        raise PreregViolation('invalid external anchor signature or key') from exc
    return {
        'status': 'SIGNED_PREREG_ANCHOR_MATCHES_NOT_CUSTODY_PROOF',
        'preregistration_sha256': local_digest,
        'signer_key_sha256': hashlib.sha256(independently_pinned_public_key_pem).hexdigest(),
        'signature_valid': True,
        'independent_custody_proven': False,
        'promotion_allowed': False,
        'note': 'External key identity, clock and custody require independent operational audit.',
    }
