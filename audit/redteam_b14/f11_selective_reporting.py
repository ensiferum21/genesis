#!/usr/bin/env python3
"""F11: repeated preregistration under one claim_id + selective citation yields confirmation (R-01).

custodian.register keys requests by digest(request) only, so the same claim_id
can be preregistered any number of times (change the seed). Each evaluation is
bound to that claim, but the kernel only looks at receipts the claim cites:
a NOT_SUPPORTED receipt for the same claim, stored in the same evidence store,
is ignored if left out of the dependencies. With k tries a null candidate
reaches alpha=0.05 with probability 1-0.95^k.
Here register() runs for real (anchors signed by the prereg key); the two
custodian receipts are signed in exactly evaluate()'s schema with the counts a
lucky and an unlucky panel would give. Production trust root; run as root:
  PYTHONPATH=src python3 -W ignore audit/redteam_b14/f11_selective_reporting.py
"""
from itertools import combinations
import json
import os
from pathlib import Path
import random
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file, production_setup, run_research  # noqa: E402

from genesis.common import bytes_hash, canonical, code_identity, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402
from genesis.kernel.stats import sign_test  # noqa: E402
from genesis.models import GraphTask, Limits, SolverProgram  # noqa: E402


def pool(seed, count=5):
    rng = random.Random(seed); out = []
    while len(out) < count:
        edges = tuple(e for e in combinations(range(10), 2) if rng.random() < 0.3)
        if 12 <= len(edges) <= 20:
            out.append(GraphTask(task_id=f's{seed}-{len(out)}', n=10, edges=edges, family='fresh10', split='CONFIRM'))
    return out


def parent():
    from genesis.custodian import register
    base, keys, trust, work = production_setup()
    private = base / 'private'; private.mkdir(mode=0o700)
    manifest = private / 'manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []})); manifest.chmod(0o600)
    export = base / 'campaign_export.zip'
    with zipfile.ZipFile(export, 'w') as z:
        z.writestr('MANIFEST.json', canonical({'files': {}, 'scope': 'public offline campaign'}))
    evaluator = code_identity(REPO)['sha256']
    out = []
    for seed, (w, l, t) in ((1, (1, 2, 2)), (2, (5, 0, 0))):          # unlucky panel, lucky panel (5 tasks)
        req = {'schema': R.REQUEST, 'campaign_id': 'a' * 64, 'claim_id': 'claim-1', 'evidence_kind': 'sealed_evaluation',
               'generation_transition': None, 'transfer_source_domain': None, 'candidate_version': 'b' * 64,
               'campaign_export_sha256': bytes_hash(export.read_bytes()), 'source_hash': evaluator,
               'programs': {'baseline': SolverProgram(rounds=1).model_dump(mode='json'),
                            'candidate': SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')},
               'limits': Limits().model_dump(mode='json'), 'seed': seed, 'task_count': 5, 'domain': 'c4_host_v2',
               'analysis': dict(R.ANALYSIS_V1), 'exposed_graph_fingerprints': [], 'expected_evaluator_hash': evaluator}
        pool_path = base / f'pool{seed}.json'
        pool_path.write_bytes(canonical([x.model_dump(mode='json') for x in pool(seed)]))
        anchor = register(private, req, keys['prereg'][0], 'custodian-op', exposure_manifest=manifest,
                          campaign_export=export, pool=pool_path)               # the real custodian call
        print(f'custodian.register accepted request seed={seed} for claim_id', anchor['payload']['claim_id'])
        p = {'schema': R.SCIENTIFIC_RECEIPT, 'evidence_kind': 'sealed_evaluation', 'claim_id': 'claim-1',
             'campaign_id': 'a' * 64, 'request_hash': digest(req), 'anchor_hash': digest(anchor),
             'candidate_version': 'b' * 64, 'baseline_version': digest(req['programs']['baseline']),
             'source_hash': evaluator, 'evaluator_hash': evaluator, 'analysis': dict(R.ANALYSIS_V1),
             'domain': 'c4_host_v2', 'domain_contract_hash': R.domain_contract_hash('c4_host_v2'),
             'transfer_source_domain': None, 'generation_transition': None,
             'panel_commitment': anchor['payload']['panel_commitment'], 'task_count': w + l + t,
             'raw_evidence_root': digest({'raw': seed}), 'raw_evidence_complete': True,
             'expected_rows': 2 * (w + l + t), 'completed_rows': 2 * (w + l + t), 'execution_failures': 0,
             'wins': w, 'losses': l, 'ties': t, 'paired_p': sign_test(w, l), 'family_p': sign_test(w, l),
             'outcome': None, 'operator_id': 'custodian-op', 'registered_at': anchor['payload']['registered_at'],
             'completed_at': '2099-01-01T00:00:00+00:00', 'screen': 'CUSTODIAN_BUILT_REGISTRY_ISOMORPHISM_AND_NEAR_DUPLICATE',
             'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
        p['outcome'] = R.derive_outcome(p)
        out.append({'request': req, 'anchor': anchor, 'receipt': sign(p, keys['custodian'][0])})
    run_research(__file__, trust, work, {'evaluations': out})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    bad, good = json.loads((work / 'inputs.json').read_bytes())['evaluations']
    root = work / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s, trust_root=trust)
        nodes = {}
        for name, e in (('bad', bad), ('good', good)):
            a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                                source_hash=e['request']['source_hash'])
            nodes[name] = k.record_signed('sealed_evaluation', e['receipt'], parents=[a],
                                          route='genesis.custodian.evaluate', source_hash=e['request']['source_hash'])
        print('same store holds a', bad['receipt']['payload']['outcome'], 'receipt for claim-1 and a',
              good['receipt']['payload']['outcome'], 'one')
        k.create_claim('claim-1', 'candidate beats baseline on c4 hosts', 'c4_host_v2', [nodes['good']],
                       binding=R.binding_from_requests([good['request']]))
        k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        print('levels:', k.levels('claim-1')['utility'])
    build_bundle(root, work / 'release.zip', trust_root=trust)
    exported = json.loads(bundle_file(work / 'release.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['utility']
    r = verify_bundle(work / 'release.zip', trust_root=trust)
    print('exported:', exported, '| verify ok:', r['ok'], r['problems'])
    print('ATTACK_SUCCEEDED' if r['ok'] and exported == 'CONFIRMED_SAME_DOMAIN' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
