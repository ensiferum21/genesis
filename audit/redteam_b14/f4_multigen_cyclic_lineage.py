#!/usr/bin/env python3
"""F4: MULTIGEN_CONFIRMED from a cyclic "lineage" that evaluates one program three times (R-01).

Generation versions are free labels: custodian.validate_request never ties
candidate_version or generation_transition.from_version to the evaluated
programs, and receipts.generation_chain() stops on reaching the final version
again without rejecting the cycle. Three requests with IDENTICAL programs and
transitions F->Y (1), Y->X (2), X->F (3) validate, are signed by the custodian
exactly as evaluate() would sign them, and license MULTIGEN_CONFIRMED in
promote, levels, build_bundle and verify_bundle (production trust root).
Run as root:
  PYTHONPATH=src python3 -W ignore audit/redteam_b14/f4_multigen_cyclic_lineage.py
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

F, Y, X = '1' * 64, '2' * 64, '3' * 64
PROGRAMS = {'baseline': SolverProgram(rounds=1).model_dump(mode='json'),
            'candidate': SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')}  # same program every time


def request(index, frm, to, seed):
    return {'schema': R.REQUEST, 'campaign_id': 'a' * 64, 'claim_id': 'mg', 'evidence_kind': 'sealed_generation_evaluation',
            'generation_transition': {'index': index, 'from_version': frm, 'to_version': to},
            'transfer_source_domain': None, 'candidate_version': to, 'campaign_export_sha256': 'e' * 64,
            'source_hash': 'c' * 64, 'programs': PROGRAMS, 'limits': Limits().model_dump(mode='json'), 'seed': seed,
            'task_count': 40, 'domain': 'c4_host_v2', 'analysis': dict(R.ANALYSIS_V1),
            'exposed_graph_fingerprints': [], 'expected_evaluator_hash': 'c' * 64}


def receipt_payload(req, anchor, i):
    wins, losses, ties = 30, 5, 5
    p = {'schema': R.SCIENTIFIC_RECEIPT, 'evidence_kind': req['evidence_kind'], 'claim_id': req['claim_id'],
         'campaign_id': req['campaign_id'], 'request_hash': digest(req), 'anchor_hash': digest(anchor),
         'candidate_version': req['candidate_version'], 'baseline_version': digest(req['programs']['baseline']),
         'source_hash': req['source_hash'], 'evaluator_hash': req['expected_evaluator_hash'],
         'analysis': req['analysis'], 'domain': req['domain'], 'domain_contract_hash': R.domain_contract_hash(req['domain']),
         'transfer_source_domain': None, 'generation_transition': req['generation_transition'],
         'panel_commitment': anchor['payload']['panel_commitment'], 'task_count': 40,
         'raw_evidence_root': digest({'raw': i}), 'raw_evidence_complete': True, 'expected_rows': 80,
         'completed_rows': 80, 'execution_failures': 0, 'wins': wins, 'losses': losses, 'ties': ties,
         'paired_p': sign_test(wins, losses), 'family_p': 0.01, 'outcome': None, 'operator_id': 'custodian-op',
         'registered_at': anchor['payload']['registered_at'], 'completed_at': f'2026-10-10T01:00:0{i}+00:00',
         'screen': 'CUSTODIAN_BUILT_REGISTRY_ISOMORPHISM_AND_NEAR_DUPLICATE',
         'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
    p['outcome'] = R.derive_outcome(p)
    assert R.check_receipt(p, req['evidence_kind']) == [], R.check_receipt(p, req['evidence_kind'])
    return p


def parent():
    from genesis.custodian import validate_request
    base, keys, trust, work = production_setup()
    reqs = [request(1, F, Y, 1), request(2, Y, X, 2), request(3, X, F, 3)]   # F -> Y -> X -> F
    for r in reqs:
        validate_request(r)  # the custodian's own schema/binding check accepts every request
    print('custodian.validate_request accepted all 3; identical programs:',
          len({digest(r['programs']) for r in reqs}) == 1)
    out = []
    for i, r in enumerate(reqs):
        anchor = sign({'schema': R.PREREG_ANCHOR, 'request_hash': digest(r), 'claim_id': 'mg',
                       'evidence_kind': r['evidence_kind'], 'registered_at': f'2026-10-10T00:00:0{i}+00:00',
                       'operator_id': 'custodian-op', 'exposure_registry_root': 'd' * 64, 'exposure_graphs': 10,
                       'declaration_unscreenable_graphs': 0, 'panel_commitment': digest({'panel': i})},
                      keys['prereg'][0])
        out.append({'request': r, 'anchor': anchor, 'receipt': sign(receipt_payload(r, anchor, i), keys['custodian'][0])})
    run_research(__file__, trust, work, {'evaluations': out})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    evals = json.loads((work / 'inputs.json').read_bytes())['evaluations']
    root = work / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s, trust_root=trust)
        nodes = []
        for e in evals:
            a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                                source_hash='c' * 64)
            nodes.append(k.record_signed('sealed_generation_evaluation', e['receipt'], parents=[a],
                                         route='genesis.custodian.evaluate', source_hash='c' * 64))
        k.create_claim('mg', 'the improver produced three successive improving generations', 'c4_host_v2', nodes,
                       binding=R.binding_from_requests([e['request'] for e in evals]))
        d = k.promote('mg', 'improver', 'MULTIGEN_CONFIRMED')
        print('promoted MULTIGEN_CONFIRMED, registry', d['registry'][:12], '| levels:', k.levels('mg')['improver'])
        chain = R.generation_chain([e['receipt']['payload'] for e in evals], F)
        print('chain used:', [(p['generation_transition']['from_version'][:1] + '->' +
                               p['generation_transition']['to_version'][:1]) for p in chain])
    build_bundle(root, work / 'release.zip', report='The improver is recursively self-improving.', trust_root=trust)
    exported = json.loads(bundle_file(work / 'release.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['improver']
    r = verify_bundle(work / 'release.zip', trust_root=trust)
    print('exported:', exported, '| verify ok:', r['ok'], r['problems'])
    print('ATTACK_SUCCEEDED' if exported == 'MULTIGEN_CONFIRMED' and r['ok'] else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
