"""Run a positive and a negative Lean canary against the same externally pinned binary.

DEV diagnostic only: passing canaries do not authenticate the binary or establish
independent proof checking. Both projects must be independently manifest-pinned.
"""
import hashlib
import json
from pathlib import Path
from real_lean_gate import run


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pair(positive_project, negative_project, exe_sha256, positive_manifest_sha256,
               negative_manifest_sha256, positive_manifest, negative_manifest,
               evidence_root=None):
    result = {'schema':'genesis-lean-canary-pair-v1', 'status':'BLOCKED',
              'promotion_allowed':False, 'reason':'not executed'}
    if Path(positive_project).resolve() == Path(negative_project).resolve():
        result['reason']='positive and negative projects must differ'
        return result
    if positive_manifest_sha256 == negative_manifest_sha256:
        result['reason']='distinct externally pinned manifests required'
        return result
    from canary_identity import verify
    identity = verify(positive_project,negative_project,positive_manifest,negative_manifest,positive_manifest_sha256,negative_manifest_sha256)
    if identity['status'] != 'DEV_CANARY_SOURCES_VERIFIED':
        result['reason']='canary identity blocked: '+identity['reason']
        return result
    root = Path(evidence_root) if evidence_root is not None else None
    if root is not None:
        if root.exists():
            result['reason']='evidence root must not exist'
            return result
        root.mkdir(mode=0o700, parents=True)
    pos = run(positive_project, exe_sha256, positive_manifest_sha256,
              positive_manifest, evidence_dir=str(root/'positive') if root else None)
    result['positive']=pos
    if pos['status'] != 'DEV_REPLAY_PASS':
        result['reason']='positive proof not accepted'
        return result
    neg = run(negative_project, exe_sha256, negative_manifest_sha256,
              negative_manifest, evidence_dir=str(root/'negative') if root else None)
    result['negative']=neg
    if neg['status'] != 'REPLAY_REJECTED' or neg.get('evidence',{}).get('exit_code') in (None,0):
        result['reason']='negative proof was not rejected by executable'
        return result
    result.update(status='DEV_CANARY_PAIR_PASS',reason='local positive/negative control passed; binary provenance and independent verification unresolved')
    return result


def make_project(path, toolchain, source):
    """Create a simple mathlib-free Lean project; returns manifest path and SHA256."""
    root=Path(path)
    root.mkdir(parents=True,exist_ok=False)
    content={'Main.lean':source.encode('utf-8'),
             'lean-toolchain':(toolchain+'\n').encode('utf-8'),
             'lakefile.toml':b'name = "genesis_canary"\nversion = "0.1.0"\n'}
    for name, data in content.items():
        (root/name).write_bytes(data)
    manifest={'schema':'genesis-lean-package-v1',
              'files':{k:hashlib.sha256(v).hexdigest() for k,v in sorted(content.items())},
              'toolchain':toolchain,'command':['Main.lean']}
    manifest_path=root.parent/(root.name+'.manifest.json')
    manifest_path.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return str(manifest_path),digest(manifest_path)


POSITIVE='theorem genesis_canary_positive : (2 : Nat) + 2 = 4 := by decide\n'
NEGATIVE='theorem genesis_canary_negative : (2 : Nat) + 2 = 5 := by decide\n'

if __name__ == '__main__':
    import argparse, shutil
    parser=argparse.ArgumentParser(description='Run externally pinned positive/negative Lean canaries')
    parser.add_argument('--toolchain',required=True,help='Exact leanprover/lean4:vX.Y.Z')
    parser.add_argument('--lean-sha256',required=True,help='Externally trusted Lean executable hash')
    parser.add_argument('--workdir',required=True,help='New directory for canary packages and evidence')
    args=parser.parse_args()
    base=Path(args.workdir)
    if base.exists():parser.error('workdir already exists; choose a new path')
    base.mkdir(parents=True)
    pm,ph=make_project(base/'positive',args.toolchain,POSITIVE)
    nm,nh=make_project(base/'negative',args.toolchain,NEGATIVE)
    result=check_pair(base/'positive',base/'negative',args.lean_sha256,ph,nh,pm,nm,base/'evidence')
    (base/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(0 if result['status']=='DEV_CANARY_PAIR_PASS' else 2)
