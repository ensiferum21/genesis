#!/usr/bin/env python3
"""R9 (LOW): load_role_registry's "independent role identities" guard compares base64
strings, not keys. A 32-byte key has 4 base64 spellings (2 unused bits in the last
symbol) that b64decode(validate=True) accepts, so one key can be pinned as
custodian_key AND prereg_key (or as a role key and the root key) and the registry
still loads. (receipts.normalize_key already canonicalises for revocation.)
Needs a root-signed registry, so this is a guard bypass for a misconfigured or
careless root operator, not a research-side attack.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r9_registry_key_aliasing.py
"""
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import canonical  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402

ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def alias(b64):
    i = ALPHA.index(b64[-2])
    return b64[:-2] + ALPHA[i ^ 1] + '='


def parent():
    base, keys, trust, work = _r2.production_setup()
    cust = keys['custodian'][1]
    print('alias decodes to the same key:', base64.b64decode(alias(cust), validate=True) == base64.b64decode(cust),
          '| strings differ:', alias(cust) != cust)
    roles = {'custodian_key': cust, 'prereg_key': alias(cust), 'auditor_key': keys['auditor'][1],
             'release_key': alias(keys['root'][1]), 'release_authority_id': 'external-board'}
    p = trust / 'roles.json'; p.chmod(0o644)
    p.write_bytes(canonical(sign({'schema': 'genesis-role-registry-v1', 'roles': roles}, keys['root'][0])))
    p.chmod(0o444)
    _r2.run_research(__file__, trust, work, {})


def child(trust, work):
    from genesis.kernel.roles import load_role_registry
    reg, why = load_role_registry(trust)
    print('registry loaded:', reg is not None, why, '| prereg == custodian key, release == root key (aliased)')
    print('ATTACK_SUCCEEDED' if reg is not None else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
