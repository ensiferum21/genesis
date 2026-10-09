"""Offline Lean executable admission. Does not attest dependency closure or provenance."""
import hashlib, json, os, pathlib, re, subprocess

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def admit(executable,expected_sha256,expected_version=None):
    result={'status':'BLOCKED','promotion_allowed':False,'reason':None}
    p=pathlib.Path(executable)
    if not re.fullmatch(r'[a-f0-9]{64}',expected_sha256 or ''):
        result['reason']='invalid externally supplied SHA256';return result
    if p.is_symlink() or not p.is_file() or not os.access(p,os.X_OK):
        result['reason']='missing, symlinked, or nonexecutable Lean';return result
    if digest(p)!=expected_sha256:
        result['reason']='Lean binary hash mismatch';return result
    try:
        proc=subprocess.run([str(p.resolve()),'--version'],env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent'},capture_output=True,timeout=10)
    except (OSError,subprocess.TimeoutExpired):
        result['reason']='version command failed';return result
    if proc.returncode!=0 or len(proc.stdout)>4096 or len(proc.stderr)>4096:
        result['reason']='version command unsuccessful';return result
    version=proc.stdout.decode('utf-8','replace').strip()
    if not re.match(r'^Lean \(version [0-9]+\.[0-9]+\.[0-9]+',version):
        result['reason']='not a recognizable Lean version response';return result
    if expected_version is not None and version!=expected_version:
        result['reason']='version mismatch';return result
    result.update(status='DEV_BINARY_ADMITTED',reason='binary fingerprint matched; not proof of Lean provenance',binary_sha256=expected_sha256,version=version)
    return result
