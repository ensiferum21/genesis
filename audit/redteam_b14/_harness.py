"""Shared helpers for the B14 red-team reproductions (test-side only, not imported by src/).

`production_setup` builds what "externally controlled" means on one machine:
role keys held by root, a root-owned read-only trust root (role registry v2),
and a work directory owned by the research UID 65534. `run_research` runs the
calling script's child mode as that UID, so `load_role_registry` really loads
the registry (it refuses to run as root). Fixture keys prove protocol
behaviour only, not operator independence.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'src'
NOBODY = 65534
ROLES = ('prereg', 'custodian', 'auditor', 'release', 'root', 'replicator', 'priority_reviewer')


def keypair(directory, name):
    k = Ed25519PrivateKey.generate()
    path = Path(directory) / f'{name}.pem'
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    pub = base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                       serialization.PublicFormat.Raw)).decode()
    return path, pub


def production_setup():
    from genesis.common import canonical
    from genesis.kernel.signing import sign
    assert os.geteuid() == 0, 'run the parent as root; the research child drops to UID 65534'
    base = Path(tempfile.mkdtemp(prefix='redteam-b14-')); base.chmod(0o755)
    secrets = base / 'secrets'; secrets.mkdir(mode=0o700)
    keys = {n: keypair(secrets, n) for n in ROLES}
    trust = base / 'trust'; trust.mkdir(mode=0o755)
    (trust / 'root.pub').write_text(keys['root'][1])
    roles = {'custodian_key': keys['custodian'][1], 'prereg_key': keys['prereg'][1],
             'auditor_key': keys['auditor'][1], 'release_key': keys['release'][1],
             'replicator_key': keys['replicator'][1], 'priority_reviewer_key': keys['priority_reviewer'][1],
             'release_authority_id': 'external-board'}
    (trust / 'roles.json').write_bytes(canonical(sign({'schema': 'genesis-role-registry-v2', 'roles': roles},
                                                      keys['root'][0])))
    for p in (trust / 'root.pub', trust / 'roles.json'):
        p.chmod(0o444)
    work = base / 'work'; work.mkdir(mode=0o755); os.chown(work, NOBODY, NOBODY)
    return base, keys, trust, work


def run_research(script, trust, work, data):
    """Run `script child <trust> <work>` as the research UID; inputs.json carries signed envelopes."""
    from genesis.common import canonical
    inputs = Path(work) / 'inputs.json'
    inputs.write_bytes(canonical(data)); os.chown(inputs, NOBODY, NOBODY)
    proc = subprocess.run([sys.executable, '-W', 'ignore', str(script), 'child', str(trust), str(work)],
                          capture_output=True, text=True, user=NOBODY, group=NOBODY, extra_groups=[], cwd='/',
                          env={'PYTHONPATH': f'{SRC}:{REPO}', 'PATH': '/usr/bin:/bin', 'HOME': str(work),
                               'PYTHONDONTWRITEBYTECODE': '1',
                               'GENESIS_TOOLCHAIN': os.environ.get('GENESIS_TOOLCHAIN', '/home/claude/toolchain')},
                          timeout=900)
    sys.stdout.write(proc.stdout)
    if proc.returncode:
        sys.stdout.write('CHILD FAILED:\n' + proc.stderr[-4000:])
    return proc


def rewrite_bundle(bundle, out, change):
    """change(files: dict relpath->bytes) mutates the bundle; MANIFEST is re-hashed (a producer that lies consistently)."""
    from genesis.common import canonical
    with zipfile.ZipFile(bundle) as zin:
        names = zin.namelist(); base = names[0].split('/')[0] + '/'
        files = {n[len(base):]: zin.read(n) for n in names}
    manifest = json.loads(files.pop('MANIFEST.json'))
    change(files, manifest)
    manifest['files'] = {n: hashlib.sha256(v).hexdigest() for n, v in sorted(files.items())}
    with zipfile.ZipFile(out, 'w') as zout:
        for n, v in files.items():
            zout.writestr(base + n, v)
        zout.writestr(base + 'MANIFEST.json', canonical(manifest))


def bundle_file(bundle, rel):
    with zipfile.ZipFile(bundle) as z:
        name = next(n for n in z.namelist() if n.split('/', 1)[1] == rel)
        return z.read(name)
