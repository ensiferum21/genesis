"""Fail-closed interface for a separately operated sealed evaluator.

This module is NOT a custodian. It validates a signed receipt created outside
this repository, never loads the sealed pool or executes a candidate.
"""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path

FIELDS = ('candidate_sha256','prereg_sha256','pool_sha256','evaluator_sha256',
          'results_sha256','manifest_sha256','custodian_id','protocol_version')
HEX = set('0123456789abcdef')


def canonical_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def verify_receipt(receipt: dict, trusted_public_key_b64: str) -> dict:
    """Verify Ed25519 signature with a pinned key from independent custody.

    The caller must source the pinned key out-of-band. A self-declared key in
    the receipt is never trusted. Verification alone does not prove isolation.
    """
    if not isinstance(receipt, dict) or set(receipt) != {'claims','signature_b64'}:
        raise ValueError('receipt shape invalid')
    claims = receipt['claims']
    if not isinstance(claims, dict) or set(claims) != set(FIELDS):
        raise ValueError('claim set invalid')
    for k in FIELDS[:6]:
        v = claims[k]
        if not isinstance(v,str) or len(v)!=64 or any(c not in HEX for c in v):
            raise ValueError(f'invalid hash: {k}')
    if claims['protocol_version'] != 'genesis-custody-v1':
        raise ValueError('unsupported protocol')
    if not isinstance(claims['custodian_id'],str) or not claims['custodian_id'].strip():
        raise ValueError('missing custodian identity')
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key = base64.b64decode(trusted_public_key_b64, validate=True)
    sig = base64.b64decode(receipt['signature_b64'], validate=True)
    Ed25519PublicKey.from_public_bytes(key).verify(sig,canonical_bytes(claims))
    return {'signature_valid':True, 'custody_isolation_proven':False,
            'receipt_sha256':hashlib.sha256(canonical_bytes(receipt)).hexdigest()}


def promotion_custody_preflight(receipt: dict | None, trusted_public_key_b64: str | None,
                                isolation_audit_approved: bool = False, *,
                                expected_digests: dict[str, str] | None = None,
                                expected_custodian_id: str | None = None) -> dict:
    """Fail-closed evidence inspection; never certify independent custody.

    The *caller* must obtain all six expected hashes, the key, and custodian ID
    from a separately controlled preregistration/custody authority. A signature
    on unrelated run data is not a valid receipt for this campaign. In particular,
    a caller-provided boolean ``isolation_audit_approved`` is not an independently
    authenticated audit and must never turn this into an admission gate.
    """
    reasons = []
    signature_valid = False
    hashes_match = False
    identity_match = False
    if not receipt or not trusted_public_key_b64:
        reasons.append('missing signed receipt or independently pinned public key')
    else:
        try:
            verify_receipt(receipt, trusted_public_key_b64)
            signature_valid = True
        except Exception as exc:
            # Only the diagnostic class is exported; no untrusted receipt text.
            reasons.append('invalid receipt signature/claims: ' + type(exc).__name__)
    if (not isinstance(expected_digests, dict)
            or set(expected_digests) != set(FIELDS[:6])
            or any(not isinstance(v, str) or len(v) != 64 or any(c not in HEX for c in v)
                   for v in expected_digests.values())):
        reasons.append('six frozen externally expected digests required')
    elif signature_valid:
        hashes_match = all(receipt['claims'][k] == expected_digests[k] for k in FIELDS[:6])
        if not hashes_match:
            reasons.append('signed receipt does not match externally frozen experiment digests')
    if not isinstance(expected_custodian_id, str) or not expected_custodian_id.strip():
        reasons.append('independently pinned custodian identity required')
    elif signature_valid:
        identity_match = receipt['claims']['custodian_id'] == expected_custodian_id
        if not identity_match:
            reasons.append('signed receipt custodian identity mismatch')
    # Even if caller asserts an audit has passed, a bare bool is self-attestation.
    # This protocol has no authenticated, independently signed isolation audit.
    reasons.append('separate authenticated operational isolation audit not verified')
    return {
        'status': 'BLOCK',
        'signature_valid': signature_valid,
        'expected_digests_match': hashes_match,
        'expected_custodian_id_match': identity_match,
        'isolation_audit_boolean_not_trusted': bool(isolation_audit_approved),
        'independent_custody_proven': False,
        'promotion_allowed': False,
        'reasons': reasons,
    }
