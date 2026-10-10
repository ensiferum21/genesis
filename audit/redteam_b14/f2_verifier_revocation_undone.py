#!/usr/bin/env python3
"""F2: a revoked verifier is un-revoked by registering the same identity again (R-02).

Checks name their verifier by an identity string; `revoked_verifiers()` treats
an identity as revoked only if ALL of its registration nodes are revoked. Any
writer can add a fresh registration node for the identity after the auditor
revoked it (A), or register it twice up front so that a later revocation feed
never downgrades anything (B). Export and the independent verifier agree with
the stale level.
Run: PYTHONPATH=src python3 -W ignore audit/redteam_b14/f2_verifier_revocation_undone.py
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file  # noqa: E402

from genesis.common import code_identity  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

SRC = 'a' * 64


def campaign(root, *, double_registration):
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s)
        reg = k.register_verifier('revocable-checker', 'e' * 64)
        if double_registration:
            k.register_verifier('revocable-checker', 'e' * 64, generated=True)  # same identity, second node
        run = k.record('execution_receipt', {'run': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
        chk = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash=SRC,
                       verdict='VALID', verifier='revocable-checker')
        k.create_claim('c', 'host H has a C4-free subgraph with 7 edges', 'host H', [chk])
        k.promote('c', 'math', 'WITNESS_VALID')
        return reg


def exported(bundle):
    return {c['claim_id']: c['effective_levels']['math'] for c in json.loads(bundle_file(bundle, 'CLAIMS.json'))['claims']}


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    # A: revoke, then re-register the identity.
    root = d / 'a'
    reg = campaign(root, double_registration=False)
    with Store(root) as s:
        k = EvidenceKernel(s)
        k.revoke(reg, 'verifier bug: accepts a 4-cycle', 'auditor')
        print('A after revocation      :', k.levels('c')['math'], k.invalidation('c'))
        k.register_verifier('revocable-checker', 'e' * 64, generated=True)   # research re-registers
        print('A after re-registration :', k.levels('c')['math'], k.invalidation('c'),
              'revocation still recorded:', [r['reason'] for r in k.revocations()])
    build_bundle(root, d / 'a.zip')
    r = verify_bundle(d / 'a.zip')
    print('A exported effective math:', exported(d / 'a.zip'), '| verify ok:', r['ok'], r['problems'])

    # B: register twice up front; the auditor's later feed revokes the registration it knows about.
    root = d / 'b'
    reg = campaign(root, double_registration=True)
    build_bundle(root, d / 'b_release.zip')
    feed = d / 'REVOCATIONS.json'
    with tempfile.TemporaryDirectory() as e:
        # The auditor's feed (built in a copy of the store, as the later release would carry it).
        import shutil
        shutil.copytree(root, Path(e) / 'copy', ignore=shutil.ignore_patterns('writer.lock'))
        with Store(Path(e) / 'copy') as s:
            EvidenceKernel(s).revoke(reg, 'verifier bug: accepts a 4-cycle', 'auditor')
            from genesis.common import canonical
            feed.write_bytes(canonical({'schema': 'genesis-revocations-v1', 'records': EvidenceKernel(s).revocations()}))
    r = verify_bundle(d / 'b_release.zip', later_revocations=feed)
    print('B later feed applied:', r['current']['applied'], '| downgraded_since_release:',
          r['current']['downgraded_since_release'], '| current math:',
          {c['claim_id']: c['effective_levels']['math'] for c in r['current']['claims']}, '| ok:', r['ok'])
    print('ATTACK_SUCCEEDED' if exported(d / 'a.zip')['c'] == 'WITNESS_VALID' and r['current']['applied'] == 1
          and not r['current']['downgraded_since_release'] else 'ATTACK_BLOCKED')
