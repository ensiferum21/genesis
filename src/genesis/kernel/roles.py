"""Externally governed role registry (spec §3.2, §15.3): who may sign what.

Layout: <trust_root>/root.pub (base64 Ed25519 public key) and
<trust_root>/roles.json (envelope signed by that root key). The research
process must not be root and must not be able to write either file or the
directory. Pins are never accepted as function arguments.
"""
import os
from pathlib import Path
from ..common import bytes_hash, load_json
from .signing import verify

TRUST_ROOT_ENV='GENESIS_TRUST_ROOT'
DEFAULT_TRUST_ROOT='/etc/genesis-trust'
ROLE_FIELDS={'custodian_key','prereg_key','auditor_key','release_key','release_authority_id'}
# Registry v2 may additionally pin these; a kind whose role is not pinned can never be accepted.
OPTIONAL_ROLE_FIELDS={'replicator_key','priority_reviewer_key'}


def _externally_controlled(path,euid):
    """True only if the research process cannot modify `path` or its directory."""
    path=Path(path)
    if path.is_symlink() or not path.exists():return False,'missing or symlinked trust file'
    st=path.stat()
    if st.st_uid==euid:return False,f'{path.name} is owned by the research account'
    if st.st_mode&0o022:return False,f'{path.name} is group/world writable'
    if os.access(path,os.W_OK):return False,f'{path.name} is writable by the research account'
    return True,None


def load_role_registry(trust_root=None):
    """Return ({'pins', 'root_key_sha256', 'trust_root'}, []) or (None, reasons)."""
    trust_root=Path(trust_root or os.environ.get(TRUST_ROOT_ENV,DEFAULT_TRUST_ROOT))
    euid=os.geteuid();reasons=[]
    if euid==0:reasons.append('research process runs as root; external control cannot be established')
    for p in (trust_root,trust_root/'root.pub',trust_root/'roles.json'):
        ok,why=_externally_controlled(p,euid)
        if not ok:reasons.append(why)
    # Every ancestor must also be outside the research account's control, or the trust
    # directory could be swapped between this check and the read (sticky dirs are fine
    # because entries owned by another account cannot be renamed there).
    for parent in Path(os.path.abspath(trust_root)).parents:
        try:st=parent.stat()
        except OSError:reasons.append(f'cannot stat trust-root ancestor {parent}');break
        if parent.is_symlink() or st.st_uid==euid:
            reasons.append(f'trust-root ancestor {parent} is controlled by the research account');break
        if os.access(parent,os.W_OK) and not st.st_mode&0o1000:
            reasons.append(f'trust-root ancestor {parent} is writable by the research account');break
    if reasons:return None,reasons
    root_key=(trust_root/'root.pub').read_text().strip()
    try:
        roles=verify(load_json(trust_root/'roles.json'),root_key)
    except Exception as exc:
        return None,['role registry signature invalid: '+type(exc).__name__]
    if not isinstance(roles,dict) or not isinstance(roles.get('roles'),dict):
        return None,['role registry schema']
    fields=set(roles['roles'])
    if not ((roles.get('schema')=='genesis-role-registry-v1' and fields==ROLE_FIELDS) or
            (roles.get('schema')=='genesis-role-registry-v2' and ROLE_FIELDS<=fields<=ROLE_FIELDS|OPTIONAL_ROLE_FIELDS)):
        return None,['role registry schema']
    pins=roles['roles']
    keys=[pins[k] for k in sorted(fields) if k.endswith('_key')]
    if not pins['release_authority_id'] or len(set(keys))<len(keys) or root_key in keys \
            or not all(isinstance(k,str) and k for k in keys):
        return None,['independent role identities required (distinct keys, root key not a role key)']
    return {'pins':pins,'root_key_sha256':bytes_hash(root_key.encode()),'trust_root':str(trust_root)},[]


