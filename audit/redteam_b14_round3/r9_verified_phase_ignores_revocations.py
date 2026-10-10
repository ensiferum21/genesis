#!/usr/bin/env python3
"""R9: verified_phase (used by `genesis campaign status` and build_index's campaigns.status)
keeps reporting RELEASED, consistent, after the judged receipt's node AND its
evaluation identity are revoked in the same store (the kernel invalidates the
claim). _open() applies key revocations only; node/evaluation revocations of the
phase envelopes are never consulted.

In-process with the fixture registry patched into kernel.phases and the
evidence kernel (the documented test seam); fixture keys prove protocol
behaviour only.
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r9_verified_phase_ignores_revocations.py
"""
from pathlib import Path
import sys
import tempfile
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from genesis.common import digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.kernel.index import build_index  # noqa: E402
from genesis.kernel.phases import advance, verified_phase  # noqa: E402
from genesis.store import Store  # noqa: E402
from tests_genesis.signed_fixtures import SignedFixture, fixture_campaign  # noqa: E402


def main():
    d = Path(tempfile.mkdtemp(prefix='r3-r9-'))
    fx = SignedFixture(d)
    root, request = fixture_campaign(d, fx)
    with mock.patch('genesis.kernel.phases.load_role_registry', return_value=(fx.registry, [])), \
            mock.patch('genesis.kernel.evidence.load_role_registry',
                       return_value=(dict(fx.registry, root_key_sha256='f' * 64), [])), \
            Store(root) as s:
        for p in ('VALIDATED_CONFIG', 'DEV_RUNNING', 'CANDIDATE_FROZEN'):
            advance(s, p)
        anchor = fx.anchor(request)
        receipt = fx.receipt(request, anchor)
        for target, env in (('LEAK_SCAN_PASSED', anchor), ('SEALED_RUNNING', receipt), ('JUDGED', receipt)):
            advance(s, target, envelope=env)
        advance(s, 'RELEASED', envelope=fx.sign({'schema': 'genesis-release-decision-v1', 'request_hash': digest(request),
                                                 'decision': 'RELEASE', 'receipt_hash': digest(receipt)}, 'release'))
        k = EvidenceKernel(s)
        a = k.record_signed('preregistration_anchor', anchor, route='genesis.custodian.evaluate', source_hash='c' * 64)
        r = k.record_signed('sealed_evaluation', receipt, parents=[a], route='genesis.custodian.evaluate',
                            source_hash='c' * 64)
        k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [r],
                       binding=R.binding_from_requests([request]))
        k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        print('before revocation: phase', verified_phase(s)['phase'], '| claim', k.levels('claim-1')['utility'])
        k.revoke(r, 'sealed evaluation found faulty', 'auditor')
        v = verified_phase(s)
        print('after revocation: kernel', 'invalidated' if k.levels('claim-1').get('invalidated') else 'valid',
              '| verified_phase', v['phase'], 'consistent', v['consistent'], v['problems'])
        build_index(s, d / 'index.sqlite3')
    import sqlite3
    db = sqlite3.connect(d / 'index.sqlite3')
    print('index campaigns.status:', db.execute('SELECT status FROM campaigns').fetchone()[0],
          '| index claims.current_levels:', db.execute('SELECT current_levels FROM claims').fetchone()[0][:60])
    print('ATTACK_SUCCEEDED' if v['phase'] == 'RELEASED' and v['consistent'] else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    main()
