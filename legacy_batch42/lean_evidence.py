"""Conservative Lean replay receipt verifier. Not an independent proof checker."""
import hashlib,json,pathlib,re
HEX=re.compile(r'^[0-9a-f]{64}$')

def sha(b):return hashlib.sha256(b).hexdigest()
def verify(receipt_path,stdout_path,stderr_path,expected_exe_sha,expected_manifest_sha):
    def reject(reason):return {'status':'BLOCKED','promotion_allowed':False,'reason':reason}
    if not all(isinstance(x,str) and HEX.fullmatch(x) for x in (expected_exe_sha,expected_manifest_sha)):
        return reject('missing external pins')
    try:
        r=json.loads(pathlib.Path(receipt_path).read_bytes())
        if not isinstance(r,dict):return reject('invalid receipt')
        e=r['evidence'];a=pathlib.Path(stdout_path);b=pathlib.Path(stderr_path)
        if a.is_symlink() or b.is_symlink() or not a.is_file() or not b.is_file():return reject('missing or symlinked streams')
        if a.stat().st_size>1024*1024 or b.stat().st_size>1024*1024:return reject('oversized streams')
        stdout=a.read_bytes();stderr=b.read_bytes()
        if e.get('stdout_sha256')!=sha(stdout) or e.get('stderr_sha256')!=sha(stderr):return reject('stream digest mismatch')
        if e.get('stdout_bytes')!=len(stdout) or e.get('stderr_bytes')!=len(stderr):return reject('stream size mismatch')
        if e.get('lean_sha256')!=expected_exe_sha:return reject('binary pin mismatch')
        if r.get('manifest_sha256')!=expected_manifest_sha:return reject('project pin missing or mismatch')
        if r.get('schema')!='genesis-real-lean-attempt-v1':return reject('receipt schema mismatch')
        if r.get('status')!='DEV_REPLAY_PASS' or r.get('proof_replayed') is not True or e.get('exit_code')!=0:return reject('replay unsuccessful')
        if r.get('promotion_allowed') is not False:return reject('promotion field unsafe')
    except (OSError,ValueError,TypeError,KeyError) as exc:return reject('invalid or unreadable evidence')
    return {'status':'DEV_RECEIPT_CONSISTENT','promotion_allowed':False,'reason':'hash-consistent local receipt; not independent attestation or mathematical verification'}
