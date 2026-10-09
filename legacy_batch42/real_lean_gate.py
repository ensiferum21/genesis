"""Fail-closed external Lean execution gate. Does not confer scientific promotion."""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, sys, time

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def run(project, expected_exe_hash, expected_manifest_hash, manifest_path=None, timeout=120, evidence_dir=None):
    out={'manifest_sha256':expected_manifest_hash,'schema':'genesis-real-lean-attempt-v1','status':'BLOCKED','promotion_allowed':False,'proof_replayed':False,'checks':{},'evidence':{}}
    if not re.fullmatch('[0-9a-f]{64}',expected_exe_hash or '') or not re.fullmatch('[0-9a-f]{64}',expected_manifest_hash or ''):
        out['reason']='external SHA256 pins missing or malformed';return out
    exe=shutil.which('lean');out['checks']['lean_available']=bool(exe)
    if not exe:out['reason']='Lean executable unavailable';return out
    exe=pathlib.Path(exe).resolve()
    out['evidence']['lean_path']=str(exe)
    out['evidence']['lean_sha256']=sha(exe)
    if out['evidence']['lean_sha256']!=expected_exe_hash:out['reason']='Lean executable hash mismatch';return out
    root=pathlib.Path(project).resolve()
    manifest=pathlib.Path(manifest_path) if manifest_path else root.parent/'manifest.json'
    if not manifest.is_file() or manifest.is_symlink() or sha(manifest)!=expected_manifest_hash:
        out['reason']='externally pinned project manifest missing or mismatched';return out
    from replay_package import audit
    try:out['checks']['package']=audit(root,manifest.read_bytes(),expected_manifest_hash)
    except Exception as e:out['reason']='package audit rejected: '+str(e);return out
    from bounded_process import execute
    try:
        p=execute([str(exe),'Main.lean'],str(root),timeout=timeout)
    except (OSError,ValueError) as e:
        out['reason']='Lean invocation failed: '+type(e).__name__;return out
    if p['status']!='EXIT':
        out['reason']='Lean invocation '+p['status'];return out
    if evidence_dir is not None:
        evidence_root=pathlib.Path(evidence_dir)
        if evidence_root.exists():
            out['reason']='evidence directory must be new';return out
        evidence_root.mkdir(mode=0o700,parents=False)
        (evidence_root/'stdout.bin').write_bytes(p['stdout'])
        (evidence_root/'stderr.bin').write_bytes(p['stderr'])
    out['evidence'].update(exit_code=p['exit_code'],stdout_sha256=hashlib.sha256(p['stdout']).hexdigest(),stderr_sha256=hashlib.sha256(p['stderr']).hexdigest(),stdout_bytes=p['stdout_bytes'],stderr_bytes=p['stderr_bytes'])
    out['proof_replayed']=p['exit_code']==0
    out['status']='DEV_REPLAY_PASS' if p['exit_code']==0 else 'REPLAY_REJECTED'
    out['reason']='Local execution only; independent attestation and full dependency custody remain outstanding'
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--lean-sha256',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',required=True);p.add_argument('--manifest',required=True);p.add_argument('--evidence-dir');a=p.parse_args()
    result=run(a.project,a.lean_sha256,a.manifest_sha256,a.manifest,evidence_dir=a.evidence_dir)
    pathlib.Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True));sys.exit(0 if result['status']=='DEV_REPLAY_PASS' else 2)
