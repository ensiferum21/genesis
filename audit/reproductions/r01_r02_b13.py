#!/usr/bin/env python3
"""Reproduce the reviewer's R-01 and R-02 findings against a given source tree.

Uses the B13 fixture-registry hook (`kernel._load_roles = ...`), exactly as the
shipped B13 unit tests did. Prints one JSON line per attack with
ATTACK_SUCCEEDED (defect present) or ATTACK_BLOCKED. Exit 1 if any attack
succeeded. Kept unchanged after the repair so the original log stays meaningful.
"""
import base64
import json
from pathlib import Path
import sys
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.kernel.signing import sign
from genesis.store import Store

SRC = 'a' * 64


def key(d, name):
    k = Ed25519PrivateKey.generate(); p = Path(d) / f'{name}.pem'
    p.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
    return p, base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                           serialization.PublicFormat.Raw)).decode()


def attempt(fn):
    try:
        fn()
        return 'ATTACK_SUCCEEDED'
    except (PromotionRejected, PermissionError, ValueError, TypeError, KeyError) as exc:
        return f'ATTACK_BLOCKED ({type(exc).__name__})'


def main():
    results = []
    with tempfile.TemporaryDirectory() as d:
        auditor, auditor_pub = key(d, 'auditor'); cust, cust_pub = key(d, 'custodian')
        registry = {'pins': {'custodian_key': cust_pub, 'prereg_key': 'p', 'auditor_key': auditor_pub,
                             'release_key': 'r', 'release_authority_id': 'board'}}
        with Store(Path(d) / 'store') as s:
            from genesis.common import code_identity
            s.set_state('source_hash', code_identity(Path(__file__).resolve().parents[2])['sha256'])
            k = EvidenceKernel(s)
            k._load_roles = lambda: (registry, [])     # B13 test hook
            run = k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign', source_hash=SRC,
                           verdict='VALID')
            note = sign({'campaign': 'some-other-campaign', 'result': 'FAILED', 'note': 'audit memo'}, auditor)
            n1 = k.record('sealed_evaluation', {'signing_role': 'auditor_key', 'signed_envelope': note},
                          parents=[run], route='genesis.custodian.evaluate', source_hash=SRC, verdict='SUPPORTED')
            k.create_claim('r01-a', 'better solver', 'graph wedge', [n1])
            results.append({'attack': 'R-01a unrelated auditor-signed failed note -> CONFIRMED_SAME_DOMAIN',
                            'result': attempt(lambda: k.promote('r01-a', 'utility', 'CONFIRMED_SAME_DOMAIN'))})
            gens = [k.record('sealed_generation_evaluation', {'signing_role': 'auditor_key', 'signed_envelope': note,
                                                              'generation': i},
                             parents=[run], route='genesis.custodian.evaluate', source_hash=SRC, verdict='SUPPORTED')
                    for i in range(3)]
            k.create_claim('r01-b', 'multigen', 'graph wedge', gens)
            results.append({'attack': 'R-01b one envelope in three wrapper nodes -> MULTIGEN_CONFIRMED',
                            'result': attempt(lambda: k.promote('r01-b', 'improver', 'MULTIGEN_CONFIRMED'))})
            # R-02: revoke a dependency of a promoted claim, then export.
            w = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash=SRC,
                         verdict='VALID', verifier='dual-predicates')
            k.create_claim('r02', 'value 7 witnessed', 'host H', [w])
            k.promote('r02', 'math', 'WITNESS_VALID')
            k.revoke(run, 'reproduction: dependency revoked', 'reviewer')
        from genesis.release_bundle import build_bundle, verify_bundle
        import zipfile
        bundle = Path(d) / 'bundle.zip'
        build_bundle(Path(d) / 'store', bundle)
        with zipfile.ZipFile(bundle) as z:
            name = next(n for n in z.namelist() if n.endswith('/CLAIMS.json'))
            claims = json.loads(z.read(name))['claims']
        exported = next(c for c in claims if c['claim_id'] == 'r02')
        levels = exported.get('levels') or exported.get('effective_levels') or {}
        stale = levels.get('math') == 'WITNESS_VALID'
        verdict = verify_bundle(bundle)
        results.append({'attack': 'R-02 revoked claim exported with a valid level and accepted by verify_bundle',
                        'exported_math_level': levels.get('math'), 'verify_ok': verdict['ok'],
                        'verify_problems': verdict['problems'][:3],
                        'result': 'ATTACK_SUCCEEDED' if stale and verdict['ok'] else 'ATTACK_BLOCKED'})
    for r in results:
        print(json.dumps(r))
    return 1 if any(r['result'] == 'ATTACK_SUCCEEDED' for r in results) else 0


if __name__ == '__main__':
    sys.exit(main())
