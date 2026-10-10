"""Round-2 red-team helpers (test-side only; nothing in src/ imports this).

Builds v3 requests, prereg anchors and scientific receipts in exactly the shape
custodian.register()/evaluate() sign, with the production-path keys created by
audit/redteam_b14/_harness.production_setup(). Signing with those keys models
an honest custodian/prereg/release operator; the research child never sees a
private key.
"""
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'redteam_b14'))
from _harness import NOBODY, REPO, bundle_file, production_setup, rewrite_bundle, run_research  # noqa: E402,F401

from genesis.common import digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402
from genesis.kernel.stats import sign_test  # noqa: E402
from genesis.models import Limits, SolverProgram  # noqa: E402

STATEMENT = 'the frozen candidate has a higher paired edge count than the frozen baseline on the sealed panel'
SCOPE = 'c4_host_v2 sealed panel'
_tick = [0]


def ts():
    _tick[0] += 1
    return f'2026-10-10T01:{_tick[0] // 60:02d}:{_tick[0] % 60:02d}+00:00'


def request(claim_id='claim-1', kind='sealed_evaluation', *, campaign='a' * 64, candidate='b' * 64,
            domain='c4_host_v2', transfer=None, transition=None, seed=1, task_count=40,
            baseline=None, cand_program=None, statement=STATEMENT, scope=SCOPE, source='c' * 64,
            evaluator='c' * 64, export_sha='e' * 64):
    return {'schema': R.REQUEST, 'campaign_id': campaign, 'claim_id': claim_id, 'evidence_kind': kind,
            'statement_hash': digest(statement), 'scope': scope, 'generation_transition': transition,
            'transfer_source_domain': transfer, 'candidate_version': candidate, 'campaign_export_sha256': export_sha,
            'source_hash': source,
            'programs': {'baseline': baseline or SolverProgram(rounds=1).model_dump(mode='json'),
                         'candidate': cand_program or SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')},
            'limits': Limits().model_dump(mode='json'), 'seed': seed, 'task_count': task_count, 'domain': domain,
            'analysis': dict(R.ANALYSIS_V1), 'exposed_graph_fingerprints': [], 'expected_evaluator_hash': evaluator}


def anchor(keys, req, *, panel=None):
    return sign({'schema': R.PREREG_ANCHOR, 'request_hash': digest(req), 'claim_id': req['claim_id'],
                 'statement_hash': req['statement_hash'], 'scope': req['scope'], 'evidence_kind': req['evidence_kind'],
                 'registration_slot': R.registration_slot(req), 'registered_at': ts(), 'operator_id': 'custodian-op',
                 'exposure_registry_root': 'd' * 64, 'exposure_graphs': 10, 'declaration_unscreenable_graphs': 0,
                 'panel_commitment': panel or digest({'panel': digest(req)})}, keys['prereg'][0])


def receipt(keys, req, anc, *, wins=30, losses=5, ties=5, raw=None):
    n = wins + losses + ties
    p = {'schema': R.SCIENTIFIC_RECEIPT, 'evidence_kind': req['evidence_kind'], 'claim_id': req['claim_id'],
         'statement_hash': req['statement_hash'], 'scope': req['scope'], 'campaign_id': req['campaign_id'],
         'request_hash': digest(req), 'anchor_hash': digest(anc), 'candidate_version': req['candidate_version'],
         'candidate_program_hash': digest(req['programs']['candidate']),
         'baseline_version': digest(req['programs']['baseline']), 'source_hash': req['source_hash'],
         'evaluator_hash': req['expected_evaluator_hash'], 'analysis': dict(req['analysis']), 'domain': req['domain'],
         'domain_contract_hash': R.domain_contract_hash(req['domain']),
         'transfer_source_domain': req['transfer_source_domain'], 'generation_transition': req['generation_transition'],
         'panel_commitment': anc['payload']['panel_commitment'], 'task_count': n,
         'raw_evidence_root': raw or digest({'raw': digest(req)}), 'raw_evidence_complete': True,
         'expected_rows': 2 * n, 'completed_rows': 2 * n, 'execution_failures': 0, 'wins': wins, 'losses': losses,
         'ties': ties, 'paired_p': sign_test(wins, losses), 'family_p': sign_test(wins, losses), 'outcome': None,
         'operator_id': 'custodian-op', 'registered_at': anc['payload']['registered_at'], 'completed_at': ts(),
         'screen': 'CUSTODIAN_BUILT_REGISTRY_ISOMORPHISM_AND_NEAR_DUPLICATE',
         'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
    p['outcome'] = R.derive_outcome(p)
    return sign(p, keys['custodian'][0])


def chown_tree(root):
    for dirpath, _, files in os.walk(root):
        os.chown(dirpath, NOBODY, NOBODY)
        for f in files:
            os.chown(os.path.join(dirpath, f), NOBODY, NOBODY)
