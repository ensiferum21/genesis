"""Strict replay-package audit. DEV; never confers proof or promotion."""
from pathlib import Path
import hashlib,json,re,stat

class PackageError(ValueError):pass

def sha(b):return hashlib.sha256(b).hexdigest()

def audit(root,manifest_bytes,expected_manifest_hash):
    root=Path(root)
    if not isinstance(expected_manifest_hash,str) or not re.fullmatch('[0-9a-f]{64}',expected_manifest_hash) or sha(manifest_bytes)!=expected_manifest_hash:
        raise PackageError('externally pinned manifest mismatch')
    try:m=json.loads(manifest_bytes)
    except (ValueError,TypeError):raise PackageError('invalid manifest')
    if not isinstance(m,dict) or set(m)!={'schema','files','toolchain','command'} or m['schema']!='genesis-lean-package-v1':raise PackageError('invalid schema')
    files=m['files']
    if not isinstance(files,dict) or not files or not {'Main.lean','lean-toolchain','lakefile.toml'}.issubset(files):raise PackageError('missing required files')
    if m['command']!=['Main.lean']:raise PackageError('unapproved command')
    if not isinstance(m['toolchain'],str) or not re.fullmatch(r'leanprover/lean4:v[0-9]+\.[0-9]+\.[0-9]+(?:-rc[0-9]+)?',m['toolchain']):raise PackageError('unpinned toolchain declaration')
    if (root/'lean-toolchain').read_text('utf-8').strip()!=m['toolchain']:raise PackageError('toolchain file mismatch')
    expected=set()
    for name,digest in files.items():
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.\-/]+',name) or name.startswith('/') or any(part in ('.','..','') for part in name.split('/')):raise PackageError('unsafe path')
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise PackageError('invalid digest')
        expected.add(name)
        p=root/name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root.resolve()):raise PackageError('unsafe member')
        if sha(p.read_bytes())!=digest:raise PackageError('file mismatch')
    found=set()
    for p in root.rglob('*'):
        if p.is_symlink():raise PackageError('symlink anywhere')
        if p.is_file():
            if not p.resolve().is_relative_to(root.resolve()):raise PackageError('escaped root')
            found.add(p.relative_to(root).as_posix())
        elif not p.is_dir():raise PackageError('special filesystem entry')
    if found!=expected:raise PackageError('unlisted or missing files')
    return {'verified':True,'file_count':len(files),'package_sha256':expected_manifest_hash,'promotion_allowed':False}
