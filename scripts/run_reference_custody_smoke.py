#!/usr/bin/env python3
"""Synthetic-only custody protocol smoke; no sealed mathematics or external claims.

All private pool and key material is ephemeral and not copied into output.
"""
from __future__ import annotations
import base64
import json
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from custody_reference.evaluator import (ARMS, SCHEMA, canonical, evaluate_frozen,
                                         file_sha, verify_bundle)


def smoke(output: Path) -> dict:
    if output.exists():
        raise FileExistsError('refuse to overwrite existing evidence')
    with tempfile.TemporaryDirectory(prefix='genesis-private-synthetic-') as private:
        root=Path(private)
        pool=root/'pool.json'
        pool.write_bytes(canonical([{'id':f'private-dev-{i}', 'features':{'x':i},
                                     'answer':2*i} for i in range(1,11)]))
        candidates={}
        for arm in ARMS:
            path=root/f'{arm}.json'
            expr=({'op':'mul','a':{'op':'input','name':'x'},
                   'b':{'op':'const','value':2}} if arm=='V2p'
                  else {'op':'const','value':0})
            path.write_bytes(canonical({'expr':expr}))
            candidates[arm]=path
        prereg=root/'prereg.json'
        hashes={arm:file_sha(path) for arm,path in candidates.items()}
        prereg.write_bytes(canonical({'protocol':SCHEMA,'pool_sha256':file_sha(pool),
                                     'candidate_sha256':hashes,
                                     'evaluation_budget_per_arm':10,
                                     'campaign_id':'SYNTHETIC_SMOKE_NO_SCIENCE'}))
        key=Ed25519PrivateKey.generate()
        private_key=root/'key.pem'
        private_key.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()))
        public=base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        reservations=root/'reservations';reservations.mkdir(mode=0o700); reservations.chmod(0o700)
        from custody_reference.private_evidence import configure_semantics
        configure_semantics(reservations,domain='synthetic-linear-v1',required_features=['x'],ignored_features=['unused'])
        result=evaluate_frozen(pool,candidates,prereg,private_key,output,
            custodian_id='LOCAL_TEST_ONLY_NOT_INDEPENDENT',reservation_dir=reservations)
        verification=verify_bundle(output,public,
            expected_prereg_sha256=file_sha(prereg),expected_pool_sha256=file_sha(pool),
            expected_candidate_hashes=hashes,
            expected_task_count=10, expected_campaign_id='SYNTHETIC_SMOKE_NO_SCIENCE',
            expected_custodian_id='LOCAL_TEST_ONLY_NOT_INDEPENDENT',
            expected_prereg_budget_per_arm=10, expected_prereg_bytes=prereg.read_bytes(), expected_evaluator_sha256=result['manifest']['evaluator_sha256'])
        repeat_blocked=False
        try:
            evaluate_frozen(pool,candidates,prereg,private_key,root/'second',
                custodian_id='LOCAL_TEST_ONLY_NOT_INDEPENDENT',reservation_dir=reservations)
        except FileExistsError:
            repeat_blocked=True
        if not repeat_blocked:
            raise AssertionError('one-shot reservation not enforced')
        summary={'status':'SYNTHETIC_DEV_SMOKE_PASS','signature_valid':verification['signature_valid'],
                 'hashes_valid':verification['bundle_hashes_valid'],
                 'repeat_blocked':repeat_blocked,
                 'independent_custody_proven':False,'mathematical_discovery_proven':False,
                 'task_count':10,'arms':result['aggregate']['arms']}
        (output/'smoke_summary.json').write_bytes(canonical(summary))
        return summary

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(json.dumps(smoke(args.output),indent=2))
