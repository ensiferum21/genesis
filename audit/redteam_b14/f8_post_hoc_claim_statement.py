#!/usr/bin/env python3
"""F8: a confirmation level attaches to a claim statement written after the receipt (R-01).

Evaluation requests, anchors and receipts bind claim_id, but never the claim's
statement or scope (priority adjudications do bind statement_hash and scope).
create_claim runs after the receipt exists, so the research side picks any
text. build_bundle lints only report.md, never claim statements, so the
exported CLAIMS.json carries the inflated statement at CONFIRMED_SAME_DOMAIN and
verify_bundle accepts it. Production trust root; run as root:
  PYTHONPATH=src python3 -W ignore audit/redteam_b14/f8_post_hoc_claim_statement.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file, production_setup, run_research  # noqa: E402

from genesis.common import code_identity, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402
from genesis.kernel.stats import sign_test  # noqa: E402
from genesis.models import Limits, SolverProgram  # noqa: E402

STATEMENT = ('The solver is statistically significantly better than every published solver, '
             'generalises to every graph family and transfers to all domains.')


def parent():
    from genesis.custodian import validate_request
    base, keys, trust, work = production_setup()
    req = {'schema': R.REQUEST, 'campaign_id': 'a' * 64, 'claim_id': 'claim-1', 'evidence_kind': 'sealed_evaluation',
           'generation_transition': None, 'transfer_source_domain': None, 'candidate_version': 'b' * 64,
           'campaign_export_sha256': 'e' * 64, 'source_hash': 'c' * 64,
           'programs': {'baseline': SolverProgram(rounds=1).model_dump(mode='json'),
                        'candidate': SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')},
           'limits': Limits().model_dump(mode='json'), 'seed': 1, 'task_count': 40, 'domain': 'c4_host_v2',
           'analysis': dict(R.ANALYSIS_V1), 'exposed_graph_fingerprints': [], 'expected_evaluator_hash': 'c' * 64}
    validate_request(req)
    anchor = sign({'schema': R.PREREG_ANCHOR, 'request_hash': digest(req), 'claim_id': 'claim-1',
                   'evidence_kind': 'sealed_evaluation', 'registered_at': '2026-10-10T00:00:00+00:00',
                   'operator_id': 'custodian-op', 'exposure_registry_root': 'd' * 64, 'exposure_graphs': 10,
                   'declaration_unscreenable_graphs': 0, 'panel_commitment': '5' * 64}, keys['prereg'][0])
    p = {'schema': R.SCIENTIFIC_RECEIPT, 'evidence_kind': 'sealed_evaluation', 'claim_id': 'claim-1',
         'campaign_id': 'a' * 64, 'request_hash': digest(req), 'anchor_hash': digest(anchor),
         'candidate_version': 'b' * 64, 'baseline_version': digest(req['programs']['baseline']),
         'source_hash': 'c' * 64, 'evaluator_hash': 'c' * 64, 'analysis': dict(R.ANALYSIS_V1), 'domain': 'c4_host_v2',
         'domain_contract_hash': R.domain_contract_hash('c4_host_v2'), 'transfer_source_domain': None,
         'generation_transition': None, 'panel_commitment': '5' * 64, 'task_count': 40, 'raw_evidence_root': '6' * 64,
         'raw_evidence_complete': True, 'expected_rows': 80, 'completed_rows': 80, 'execution_failures': 0,
         'wins': 30, 'losses': 5, 'ties': 5, 'paired_p': sign_test(30, 5), 'family_p': 0.01, 'outcome': None,
         'operator_id': 'custodian-op', 'registered_at': '2026-10-10T00:00:00+00:00',
         'completed_at': '2026-10-10T01:00:00+00:00', 'screen': 'CUSTODIAN_BUILT_REGISTRY_ISOMORPHISM_AND_NEAR_DUPLICATE',
         'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
    p['outcome'] = R.derive_outcome(p)
    run_research(__file__, trust, work, {'request': req, 'anchor': anchor, 'receipt': sign(p, keys['custodian'][0])})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.kernel.wording import lint
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())
    root = work / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate', source_hash='c' * 64)
        r = k.record_signed('sealed_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                            source_hash='c' * 64)
        # The statement and scope are chosen now, after the signed receipt is in hand.
        k.create_claim('claim-1', STATEMENT, 'every graph family, every domain', [r],
                       binding=R.binding_from_requests([e['request']]))
        k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
    build_bundle(root, work / 'release.zip', trust_root=trust)
    c = json.loads(bundle_file(work / 'release.zip', 'CLAIMS.json'))
    claim = c['claims'][0]
    print('exported:', claim['statement'], '| scope:', claim['scope'], '|', claim['effective_levels']['utility'])
    print('wording gate on that statement would flag:', [v['phrase'] for v in lint(STATEMENT, c['ceiling'])])
    r = verify_bundle(work / 'release.zip', trust_root=trust)
    print('verify ok:', r['ok'], r['problems'])
    print('ATTACK_SUCCEEDED' if r['ok'] and claim['effective_levels']['utility'] == 'CONFIRMED_SAME_DOMAIN'
          else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
