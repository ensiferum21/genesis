"""Operator-facing Lean canary workflow. Local DEV evidence only.

Never auto-generates the trust anchor. Caller must supply an independently
established SHA256 of the Lean executable and an exact toolchain label.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from lean_canary import POSITIVE, NEGATIVE, make_project, check_pair
from canary_receipts import verify_pair

HEX = re.compile(r'^[0-9a-f]{64}$')
TOOLCHAIN = re.compile(r'^leanprover/lean4:v[0-9]+\.[0-9]+\.[0-9]+(?:-rc[0-9]+)?$')


def execute(workdir, toolchain, trusted_lean_sha256):
    """Create a fresh run and locally cross-check raw receipts; never promote."""
    root = Path(workdir)
    if not TOOLCHAIN.fullmatch(toolchain):
        raise ValueError('exact Lean release toolchain label required')
    if not HEX.fullmatch(trusted_lean_sha256):
        raise ValueError('externally attested executable SHA256 required')
    if root.exists() or root.is_symlink():
        raise ValueError('fresh, nonexistent workdir required')
    root.mkdir(mode=0o700, parents=True)
    pm, ph = make_project(root/'positive', toolchain, POSITIVE)
    nm, nh = make_project(root/'negative', toolchain, NEGATIVE)
    pair = check_pair(root/'positive',root/'negative',trusted_lean_sha256,
                      ph,nh,pm,nm,root/'evidence')
    (root/'pair.json').write_text(json.dumps(pair,sort_keys=True,indent=2)+'\n')
    if pair['status']=='DEV_CANARY_PAIR_PASS':
        receipt = verify_pair(pair,root/'evidence',trusted_lean_sha256,ph,nh)
    else:
        receipt = {'status':'BLOCKED','reason':'pair did not pass','promotion_allowed':False}
    (root/'verification.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    summary={'schema':'genesis-operator-handoff-v1','pair_status':pair['status'],
             'receipt_status':receipt['status'],'promotion_allowed':False,
             'trusted_hash_supplied_externally':True,
             'independent_binary_provenance_verified':False,
             'independent_proof_replay_verified':False,
             'research_claim':'NONE',
             'artifacts':['positive/','negative/','positive.manifest.json',
                          'negative.manifest.json','pair.json','verification.json','evidence/']}
    (root/'SUMMARY.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    return summary


def main(argv=None):
    p=argparse.ArgumentParser(description='Genesis external Lean canary operator handoff')
    p.add_argument('--workdir',required=True)
    p.add_argument('--toolchain',required=True)
    p.add_argument('--trusted-lean-sha256',required=True,
                   help='SHA256 obtained from a separate trusted channel, NOT derived automatically')
    a=p.parse_args(argv)
    try: summary=execute(a.workdir,a.toolchain,a.trusted_lean_sha256)
    except (ValueError,OSError) as e:
        print(json.dumps({'status':'BLOCKED','reason':str(e),'promotion_allowed':False}))
        return 2
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0 if summary['pair_status']=='DEV_CANARY_PAIR_PASS' and summary['receipt_status']=='DEV_CANARY_RECEIPTS_CONSISTENT' else 2

if __name__=='__main__':sys.exit(main())
