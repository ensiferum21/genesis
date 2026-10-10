#!/usr/bin/env python3
"""F3: revoke_evaluation() does not retire an external priority adjudication (R-02).

receipts.evaluation_identity() defines an identity for priority adjudications
and promote() records it under `evaluations`, but invalidation() only matches
payloads with a panel_commitment and _signed_support()'s priority branch never
consults the revoked-evaluation set. EXTERNALLY_CHECKED_NOVEL survives the
revocation in levels(), build_bundle (CLAIMS.json), verify_bundle, and a later
revocation feed reports nothing downgraded.
Production path: root holds the keys and a root-owned trust root; the research
side runs as UID 65534. Run as root:
  PYTHONPATH=src python3 -W ignore audit/redteam_b14/f3_priority_evaluation_revocation_ignored.py
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file, production_setup, run_research  # noqa: E402

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402

STATEMENT = 'construction X is new for hosts of family F'


def parent():
    base, keys, trust, work = production_setup()
    adjudication = sign({'schema': R.PRIORITY_ADJUDICATION, 'evidence_kind': 'external_priority_adjudication',
                         'claim_id': 'nov', 'statement_hash': digest(STATEMENT), 'scope': 'family F only',
                         'reviewer_id': 'external-priority-board', 'search_record_root': '3' * 64,
                         'decided_at': '2026-10-10T00:00:00+00:00', 'outcome': 'NOVEL_IN_SCOPE'},
                        keys['priority_reviewer'][0])
    run_research(__file__, trust, work, {'adjudication': adjudication})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    env = json.loads((work / 'inputs.json').read_bytes())['adjudication']
    root = work / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s, trust_root=trust)
        run = k.record('execution_receipt', {'run': 1}, route='genesis.campaign', source_hash='a' * 64, verdict='VALID')
        node = k.record_signed('external_priority_adjudication', env, parents=[run],
                               route='genesis.custodian.evaluate', source_hash='a' * 64)
        k.create_claim('nov', STATEMENT, 'family F only', [node])
        decision = k.promote('nov', 'novelty', 'EXTERNALLY_CHECKED_NOVEL')
        print('promoted with registry root', decision['registry'][:12], 'evaluations', decision['evaluations'])
    build_bundle(root, work / 'release.zip', trust_root=trust)
    with Store(root) as s:
        k = EvidenceKernel(s, trust_root=trust)
        ident = R.evaluation_identity(env['payload'])
        assert ident in decision['evaluations']
        k.revoke_evaluation(ident, 'priority search record found incomplete', 'priority-board')
        print('after revoke_evaluation: levels', k.levels('nov')['novelty'], '| invalidation', k.invalidation('nov'),
              '| revocations', [(r['target_type'], r['artifact'][:12]) for r in k.revocations()])
    build_bundle(root, work / 'after.zip', trust_root=trust)
    exported = json.loads(bundle_file(work / 'after.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['novelty']
    r = verify_bundle(work / 'after.zip', trust_root=trust)
    print('exported after revocation:', exported, '| verify ok:', r['ok'], r['problems'])
    (work / 'feed.json').write_bytes(bundle_file(work / 'after.zip', 'REVOCATIONS.json'))
    r = verify_bundle(work / 'release.zip', trust_root=trust, later_revocations=work / 'feed.json')
    print('older release + later feed: applied', r['current']['applied'], '| downgraded_since_release',
          r['current']['downgraded_since_release'], '| current novelty',
          r['current']['claims'][0]['effective_levels']['novelty'])
    print('ATTACK_SUCCEEDED' if exported == 'EXTERNALLY_CHECKED_NOVEL' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
