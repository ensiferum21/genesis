"""Fail-closed verification of an *external* evaluator custody attestation.

The private signing key must never exist in the research repository, process,
or its checkpoints. A valid signature attests a custodian's declaration; it
cannot by itself prove the custodian enforced isolation. External operational
review remains mandatory. This module does NOT replace the legacy SealedStore.
"""
from __future__ import annotations

import base64
import hashlib
import json


class CustodyError(ValueError):
    pass


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def verify_external_attestation(attestation: dict, public_key_pem: bytes,
                                expected: dict[str, str]) -> str:
    """Verify an Ed25519-signed declaration and bind it to frozen experiment hashes.

    `expected` must be obtained from a separately frozen preregistration and
    independent raw-evidence manifest, not from fields in the attestation itself.
    Returns the public-key SHA256 fingerprint. No private-key handling is provided.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(attestation, dict):
        raise CustodyError('attestation must be an object')
    try:
        sig = base64.b64decode(attestation['signature_ed25519_base64'], validate=True)
        payload = attestation['payload']
        if not isinstance(payload, dict):
            raise CustodyError('payload must be an object')
        if payload['schema'] != 'genesis-external-custody-v1':
            raise CustodyError('unknown custody schema')
        if payload['research_read_access_to_sealed'] is not False:
            raise CustodyError('research access to sealed material is not denied')
        if payload['evaluator_isolated_from_research'] is not True:
            raise CustodyError('evaluator not declared isolated')
        if not payload.get('custodian_id') or not payload.get('issued_at_utc'):
            raise CustodyError('custodian identity or timestamp missing')
        for k in ('candidate_sha256', 'preregistration_sha256', 'pool_sha256',
                  'results_manifest_root_sha256', 'evaluator_sha256'):
            if k not in expected or not isinstance(expected[k], str) or len(expected[k]) != 64:
                raise CustodyError(f'missing frozen expected digest: {k}')
            if payload.get(k) != expected[k]:
                raise CustodyError(f'custody hash mismatch: {k}')
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise CustodyError('expected Ed25519 custodian key')
        key.verify(sig, _canonical(payload))
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        if isinstance(exc, CustodyError):
            raise
        raise CustodyError(f'invalid custody attestation: {exc}') from exc
    return hashlib.sha256(key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)).hexdigest()
