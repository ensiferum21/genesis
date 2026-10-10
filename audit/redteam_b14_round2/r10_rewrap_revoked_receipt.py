#!/usr/bin/env python3
"""R10 (LOW, R-02): node revocation of a signed receipt retires the *wrapper*, not the
envelope. Inside one store the re-wrap cannot be reused (claims are immutable and
the receipt names its claim id; shown below as rejected). But a later revocation
feed that names the old node id is skipped as "unknown" by any store/bundle that
wraps the same envelope differently (e.g. the campaign re-recorded into a fresh
store with another eligible route string), so the confirmation survives there.
Only revoke_evaluation() reaches every copy.

Kernel logic with fixture keys (the registry seam does not matter here: the
revocation and the re-wrap are both store operations).
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round2/r10_rewrap_revoked_receipt.py
"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402,F401
from genesis.common import digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.store import Store  # noqa: E402
from tests_genesis.signed_fixtures import SignedFixture  # noqa: E402

d = Path(tempfile.mkdtemp())
fx = SignedFixture(d)
req = fx.request(claim_id='c-1')
anc = fx.anchor(req)
rec = fx.receipt(req, anc)
with Store(d / 's') as s:
    k = EvidenceKernel.with_fixture_registry(s, fx.registry)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash='c' * 64, verdict='VALID')
    a = k.record_signed('preregistration_anchor', anc, route='genesis.custodian.evaluate', source_hash='c' * 64)
    n1 = k.record_signed('sealed_evaluation', rec, parents=[a], route='genesis.custodian.evaluate', source_hash='c' * 64)
    k.create_claim('c-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [n1], binding=R.binding_from_requests([req]))
    k.promote('c-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
    k.revoke(n1, 'auditor: this sealed evaluation is unreliable', 'auditor')
    print('after revoking receipt node', n1[:12], '-> c-1:', k.levels('c-1').get('invalidated') and 'INVALIDATED')
    n2 = k.record_signed('sealed_evaluation', rec, parents=[a, run], route='genesis.custodian.evaluate',
                         source_hash='c' * 64)          # same envelope, new wrapper id
    print('same envelope re-wrapped as', n2[:12], '| same evaluation identity:',
          R.evaluation_identity(rec['payload']) is not None, '| node revoked:', n2 in k._revoked('node'))
    # claim ids are free text and the custodian's slot rule is not visible to the kernel
    k.create_claim('c-1 ', SignedFixture.STATEMENT, SignedFixture.SCOPE, [n2],
                   binding=R.binding_from_requests([req]))
    try:
        k.promote('c-1 ', 'utility', 'CONFIRMED_SAME_DOMAIN')
        lvl = k.levels('c-1 ')['utility']
    except Exception as e:
        lvl = f'rejected: {e}'
    print("claim 'c-1 ' (receipt names 'c-1'):", lvl)
    # The binding check compares receipt claim_id exactly, so use the receipt's claim id in a fresh store instead.
with Store(d / 's2') as s:
    k = EvidenceKernel.with_fixture_registry(s, fx.registry)
    a = k.record_signed('preregistration_anchor', anc, route='genesis.custodian.evaluate', source_hash='c' * 64)
    n3 = k.record_signed('sealed_evaluation', rec, parents=[a], route='genesis.custodian.evaluate.v2',
                         source_hash='c' * 64)
    k.create_claim('c-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [n3], binding=R.binding_from_requests([req]))
    k.promote('c-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
    feed = [{'target_type': 'node', 'artifact': n1, 'reason': 'auditor: unreliable evaluation', 'actor': 'auditor'}]
    applied = k.apply_revocations(feed)
    print('second store, same envelope (wrapper', n3[:12] + '); later feed revoking', n1[:12], '->',
          {'applied': len(applied['applied']), 'skipped_unknown': len(applied['skipped_unknown'])},
          '| c-1 level:', k.levels('c-1')['utility'])
    ok = k.levels('c-1')['utility'] == 'CONFIRMED_SAME_DOMAIN'
print('ATTACK_SUCCEEDED' if ok else 'ATTACK_BLOCKED')
