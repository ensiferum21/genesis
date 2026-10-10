#!/usr/bin/env python3
"""R4: revoking a preregistration ANCHOR does not follow its envelope (L2 fixed this for
receipts only), so a voided preregistration comes back by re-wrapping.

`revoke(nid)` retires the evaluation identity only when the revoked node carries
one; an anchor payload has a panel commitment but no raw-evidence root, so
`evaluation_identity(anchor) is None` and only the node id is revoked. The node
id depends on route/source/parents, so a store that wraps the SAME signed anchor
and receipt in fresh nodes does not see the revocation: `apply_revocations`
skips it as an unknown node, and verify_bundle(..., later_revocations=feed)
reports nothing downgraded. The same feed revoking the RECEIPT node does
downgrade (control), which is the asymmetry.

Production trust path: role keys held by the root parent, research child as UID 65534.
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r4_anchor_revocation_does_not_follow.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.common import canonical, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402

CAMPAIGN = 'a' * 64
CLAIM = 'claim-1'


def parent():
    base, keys, trust, work = _r3.production_setup()
    req = _r3._r2.request(claim_id=CLAIM, campaign=CAMPAIGN, source=_r3.IDENT)
    anc = _r3._r2.anchor(keys, req)
    rec = _r3._r2.receipt(keys, req, anc)
    _r3.run_research(__file__, trust, work, {'request': req, 'anchor': anc, 'receipt': rec})


def store(k_cls, root, trust, e, route_suffix):
    from genesis.store import Store
    s = Store(root)
    s.set_state('campaign_id', CAMPAIGN); s.set_state('source_hash', _r3.IDENT)
    k = k_cls(s, trust_root=trust)
    a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate' + route_suffix,
                        source_hash=_r3.IDENT)
    r = k.record_signed('sealed_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                        source_hash=_r3.IDENT)
    k.create_claim(CLAIM, _r3._r2.STATEMENT, _r3._r2.SCOPE, [r], binding=R.binding_from_requests([e['request']]))
    k.promote(CLAIM, 'utility', 'CONFIRMED_SAME_DOMAIN')
    return s, k, a, r


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    e = json.loads((work / 'inputs.json').read_bytes())
    # S1: the original release store. The anchor (preregistration) is later found void.
    s1, k1, a1, r1 = store(EvidenceKernel, work / 's1', trust, e, '')
    k1.revoke(a1, 'preregistration void: exposure registry was incomplete at registration', 'auditor')
    print('S1 after anchor revocation:', k1.levels(CLAIM).get('invalidated') and 'invalidated', '| records:',
          [r['target_type'] for r in k1.revocations()])
    feed = work / 'feed_anchor.json'
    feed.write_bytes(canonical({'schema': 'genesis-revocations-v1', 'records': k1.revocations()}))
    s1.close()
    # S2: same signed anchor + receipt, fresh wrapper nodes.
    s2, k2, a2, r2 = store(EvidenceKernel, work / 's2', trust, e, '.rewrap')
    print('S2 anchor node', a2[:12], '!= S1 anchor node', a1[:12], '| S2 level', k2.levels(CLAIM)['utility'])
    s2.close()
    build_bundle(work / 's2', work / 'b2.zip', trust_root=trust, report='Sealed evaluation.')
    v = verify_bundle(work / 'b2.zip', trust_root=trust, later_revocations=feed)
    cur = v['current']
    lvl = cur['claims'][0]['effective_levels']['utility']
    print('verify_bundle(S2 bundle, later anchor revocation): ok', v['ok'], '| applied', cur['applied'],
          'skipped', cur['skipped_unknown'], '| downgraded', cur['downgraded_since_release'], '| current', lvl)
    # Control: the same experiment revoking the RECEIPT node instead is followed (L2).
    s3, k3, a3, r3 = store(EvidenceKernel, work / 's3', trust, e, '')
    k3.revoke(r3, 'receipt void', 'auditor')
    feed_r = work / 'feed_receipt.json'
    feed_r.write_bytes(canonical({'schema': 'genesis-revocations-v1', 'records': k3.revocations()}))
    s3.close()
    v2 = verify_bundle(work / 'b2.zip', trust_root=trust, later_revocations=feed_r)
    print('control (receipt revocation feed): downgraded', v2['current']['downgraded_since_release'])
    ok = v['ok'] and lvl == 'CONFIRMED_SAME_DOMAIN' and not cur['downgraded_since_release'] \
        and v2['current']['downgraded_since_release'] == [CLAIM]
    print('ATTACK_SUCCEEDED' if ok else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
