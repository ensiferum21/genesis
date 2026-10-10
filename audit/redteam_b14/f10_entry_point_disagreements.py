#!/usr/bin/env python3
"""F10: release_preflight and phases.advance accept receipts the kernel refuses (R-01 shared semantics).

(a) A receipt whose source_hash is in eligibility.REVOKED_SOURCES: the kernel
    refuses it ("revoked source"); release_preflight returns
    EXTERNAL_RELEASE_REVIEW_READY (it never calls eligibility.source_status).
(b) An evidence_kind='external_reproduction' receipt signed by the CUSTODIAN key
    (KIND_ROLES says replicator_key): phases.advance verifies SEALED_RUNNING/JUDGED
    with the custodian pin and check_receipt(payload, payload['evidence_kind']),
    so the campaign reaches RELEASED; the kernel and preflight refuse the receipt.
Production trust root; run as root:
  PYTHONPATH=src python3 -W ignore audit/redteam_b14/f10_entry_point_disagreements.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, production_setup, run_research  # noqa: E402

from genesis.common import digest  # noqa: E402
from genesis.eligibility import REVOKED_SOURCES  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402
from genesis.kernel.stats import sign_test  # noqa: E402
from genesis.models import Limits, SolverProgram  # noqa: E402

REVOKED = next(iter(REVOKED_SOURCES))


def bundle(keys, claim_id, kind, source, signer):
    req = {'schema': R.REQUEST, 'campaign_id': 'a' * 64, 'claim_id': claim_id, 'evidence_kind': kind,
           'generation_transition': None, 'transfer_source_domain': None, 'candidate_version': 'b' * 64,
           'campaign_export_sha256': 'e' * 64, 'source_hash': source,
           'programs': {'baseline': SolverProgram(rounds=1).model_dump(mode='json'),
                        'candidate': SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')},
           'limits': Limits().model_dump(mode='json'), 'seed': 1, 'task_count': 40, 'domain': 'c4_host_v2',
           'analysis': dict(R.ANALYSIS_V1), 'exposed_graph_fingerprints': [], 'expected_evaluator_hash': 'c' * 64}
    from genesis.custodian import validate_request
    validate_request(req)
    anchor = sign({'schema': R.PREREG_ANCHOR, 'request_hash': digest(req), 'claim_id': claim_id, 'evidence_kind': kind,
                   'registered_at': '2026-10-10T00:00:00+00:00', 'operator_id': 'op', 'exposure_registry_root': 'd' * 64,
                   'exposure_graphs': 10, 'declaration_unscreenable_graphs': 0, 'panel_commitment': digest(req)},
                  keys['prereg'][0])
    p = {'schema': R.SCIENTIFIC_RECEIPT, 'evidence_kind': kind, 'claim_id': claim_id, 'campaign_id': 'a' * 64,
         'request_hash': digest(req), 'anchor_hash': digest(anchor), 'candidate_version': 'b' * 64,
         'baseline_version': digest(req['programs']['baseline']), 'source_hash': source, 'evaluator_hash': 'c' * 64,
         'analysis': dict(R.ANALYSIS_V1), 'domain': 'c4_host_v2', 'domain_contract_hash': R.domain_contract_hash('c4_host_v2'),
         'transfer_source_domain': None, 'generation_transition': None, 'panel_commitment': digest(req),
         'task_count': 40, 'raw_evidence_root': digest({'raw': claim_id}), 'raw_evidence_complete': True,
         'expected_rows': 80, 'completed_rows': 80, 'execution_failures': 0, 'wins': 30, 'losses': 5, 'ties': 5,
         'paired_p': sign_test(30, 5), 'family_p': 0.01, 'outcome': None, 'operator_id': 'op',
         'registered_at': '2026-10-10T00:00:00+00:00', 'completed_at': '2026-10-10T01:00:00+00:00',
         'screen': 'x', 'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
    p['outcome'] = R.derive_outcome(p)
    receipt = sign(p, keys[signer][0])
    audit = sign({'request_hash': digest(req), 'receipt_hash': digest(receipt), 'status': 'PASS', 'open_critical': 0,
                  'independent_operation_verified': True, 'raw_replay_verified': True, 'formal_replay_verified': True},
                 keys['auditor'][0])
    decision = sign({'schema': 'genesis-release-decision-v1', 'request_hash': digest(req), 'decision': 'RELEASE',
                     'receipt_hash': digest(receipt)}, keys['release'][0])
    return {'request': req, 'anchor': anchor, 'receipt': receipt, 'audit': audit, 'decision': decision}


def parent():
    base, keys, trust, work = production_setup()
    run_research(__file__, trust, work, {
        'revoked_source': bundle(keys, 'claim-a', 'sealed_evaluation', REVOKED, 'custodian'),
        'custodian_reproduction': bundle(keys, 'claim-b', 'external_reproduction', 'c' * 64, 'custodian')})


def child(trust, work):
    from genesis.custodian import release_preflight
    from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
    from genesis.kernel.phases import advance
    from genesis.store import Store
    inputs = json.loads((work / 'inputs.json').read_bytes())
    with Store(work / 'kernel') as s:
        k = EvidenceKernel(s, trust_root=trust)
        for name, axis, level in (('revoked_source', 'utility', 'CONFIRMED_SAME_DOMAIN'),
                                  ('custodian_reproduction', 'replication', 'EXTERNAL_REPRODUCTION')):
            e = inputs[name]
            pre = release_preflight(e['request'], e['anchor'], e['receipt'], e['audit'], trust_root=trust)
            a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                                source_hash='c' * 64)
            r = k.record_signed(e['request']['evidence_kind'], e['receipt'], parents=[a],
                                route='genesis.custodian.evaluate', source_hash='c' * 64)
            k.create_claim(e['request']['claim_id'], 'x', 's', [r], binding=R.binding_from_requests([e['request']]))
            try:
                k.promote(e['request']['claim_id'], axis, level); verdict = 'GRANTED'
            except PromotionRejected as exc:
                verdict = 'REJECTED: ' + exc.args[0][0][:110]
            print(f'{name}: preflight={pre["status"]} {pre["reasons"][:1]} | kernel {level}: {verdict}')
    e = inputs['custodian_reproduction']
    with Store(work / 'phases') as s:
        s.set_state('frozen_request_hash', digest(e['request']))
        steps = [('VALIDATED_CONFIG', None), ('DEV_RUNNING', None), ('CANDIDATE_FROZEN', None),
                 ('LEAK_SCAN_PASSED', e['anchor']), ('SEALED_RUNNING', e['receipt']), ('JUDGED', e['receipt']),
                 ('RELEASED', e['decision'])]
        for target, env in steps:
            advance(s, target, envelope=env, trust_root=trust)
        print('phases with a custodian-signed external_reproduction receipt reached:', s.state('phase'))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
