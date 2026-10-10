#!/usr/bin/env python3
"""R5: release_preflight says EXTERNAL_RELEASE_REVIEW_READY for a receipt that the evidence
kernel has stopped counting (its evaluation, its receipt node and its signing key
are all revoked).

release_preflight(request, anchor, receipt, audit, trust_root) calls
receipts.accept_receipt WITHOUT revoked_keys and has no input for the store's
revocations (node, evaluation, key) or a later REVOCATIONS.json feed, so the
"single acceptance function" (F10) disagrees with the kernel and the phase
machine as soon as anything is revoked.

Production trust path (root parent holds keys; UID-65534 child).
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r5_preflight_ignores_revocations.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402

CAMPAIGN = 'a' * 64


def parent():
    base, keys, trust, work = _r3.production_setup()
    req = _r3._r2.request(claim_id='claim-1', campaign=CAMPAIGN, source=_r3.IDENT, task_count=40,
                          cand_program=SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json'))
    anc = _r3._r2.anchor(keys, req)
    rec = _r3._r2.receipt(keys, req, anc)
    audit = sign({'request_hash': digest(req), 'receipt_hash': digest(rec), 'status': 'PASS', 'open_critical': 0,
                  'independent_operation_verified': True, 'raw_replay_verified': True,
                  'formal_replay_verified': True}, keys['auditor'][0])
    _r3.run_research(__file__, trust, work, {'request': req, 'anchor': anc, 'receipt': rec, 'audit': audit,
                                             'custodian_pub': keys['custodian'][1]})


def child(trust, work):
    from genesis.custodian import release_preflight
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())
    print('preflight before revocation:', release_preflight(e['request'], e['anchor'], e['receipt'], e['audit'],
                                                             trust_root=trust)['status'])
    with Store(work / 's') as s:
        s.set_state('campaign_id', CAMPAIGN); s.set_state('source_hash', _r3.IDENT)
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                            source_hash=_r3.IDENT)
        r = k.record_signed('sealed_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                            source_hash=_r3.IDENT)
        k.create_claim('claim-1', _r3._r2.STATEMENT, _r3._r2.SCOPE, [r], binding=R.binding_from_requests([e['request']]))
        k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        k.revoke(r, 'custodian evaluation found faulty', 'auditor')
        k.revoke_key(e['custodian_pub'], 'custodian signing key compromised', 'auditor')
        print('kernel after revocation:', k.levels('claim-1'), '| revocations:',
              sorted({x['target_type'] for x in k.revocations()}))
        accepted, why = R.accept_receipt(e['receipt'], 'sealed_evaluation', {'custodian_key': e['custodian_pub']},
                                         revoked_keys=k.revoked_keys())
        print('accept_receipt with the store\'s revoked keys:', accepted is not None, why[:1])
    p = release_preflight(e['request'], e['anchor'], e['receipt'], e['audit'], trust_root=trust)
    print('preflight after revocation:', p['status'], p['reasons'][:2])
    print('ATTACK_SUCCEEDED' if p['status'] == 'EXTERNAL_RELEASE_REVIEW_READY' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
