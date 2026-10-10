"""Ed25519 envelopes shared by the evaluator, release gate and evidence kernel."""
import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from ..common import canonical


def sign(payload, key_path):
    key = serialization.load_pem_private_key(Path(key_path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Ed25519 private key required')
    return {'payload': payload, 'signature': base64.b64encode(key.sign(canonical(payload))).decode()}


def verify(envelope, public_key_b64):
    if not isinstance(envelope, dict) or set(envelope) != {'payload', 'signature'}:
        raise ValueError('signed envelope schema')
    key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True))
    key.verify(base64.b64decode(envelope['signature'], validate=True), canonical(envelope['payload']))
    return envelope['payload']
