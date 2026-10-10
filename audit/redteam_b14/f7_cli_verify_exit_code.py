#!/usr/bin/env python3
"""F7: `genesis verify-bundle` exits 0 for a bundle it rejects (CLI entry point).

cli.main prints verify_bundle's result and returns normally, so any script or CI
gate that relies on the exit status accepts a bundle asserting stale levels.
Run: PYTHONPATH=src python3 -W ignore audit/redteam_b14/f7_cli_verify_exit_code.py
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, SRC, rewrite_bundle  # noqa: E402

from genesis.common import canonical, code_identity  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.release_bundle import build_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = d / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s)
        run = k.record('execution_receipt', {'run': 1}, route='genesis.campaign', source_hash='a' * 64, verdict='VALID')
        chk = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash='a' * 64,
                       verdict='VALID', verifier='dual-predicates')
        k.create_claim('c', 'value 7 witnessed', 'host H', [chk])
        k.promote('c', 'math', 'WITNESS_VALID')
        k.revoke(chk, 'checker receipt found faulty', 'auditor')
    build_bundle(root, d / 'after.zip')

    def stale(files, manifest):
        c = json.loads(files['CLAIMS.json'])
        for claim in c['claims']:
            claim['effective_levels'] = claim['historical']['recorded_levels']
        files['CLAIMS.json'] = canonical(c)

    rewrite_bundle(d / 'after.zip', d / 'stale.zip', stale)
    proc = subprocess.run([sys.executable, '-W', 'ignore', '-m', 'genesis', 'verify-bundle', str(d / 'stale.zip')],
                          capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(SRC)})
    out = json.loads(proc.stdout)
    print('cli exit code:', proc.returncode, '| ok:', out['ok'], '| problems:', [p[:80] for p in out['problems']])
    print('ATTACK_SUCCEEDED' if proc.returncode == 0 and not out['ok'] else 'ATTACK_BLOCKED')
