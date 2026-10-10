#!/usr/bin/env python3
"""R7: the kernel's campaign binding (round-2 C1) compares the claim binding with the
store's CURRENT `campaign_id`/`source_hash` state only. A different campaign B
(own id, own history, a source that is not the one in the receipts) relabels
itself as campaign A with two STATE_UPDATED writes, records A's signed
anchor+receipt, and its release bundle exports CONFIRMED_SAME_DOMAIN; verify_bundle
accepts. The phase machine (H1) requires the frozen request's bound export to
be a prefix of this store's history; the kernel and verify_bundle do not, and
the relabelling stays visible in events.jsonl without anyone looking.

Production trust path (keys held by the root parent; UID-65534 child).
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r7_campaign_binding_by_mutable_label.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402

A = 'a' * 64
B = 'b0' * 32


def parent():
    base, keys, trust, work = _r3.production_setup()
    req = _r3._r2.request(claim_id='claim-1', campaign=A, source=_r3.IDENT)
    anc = _r3._r2.anchor(keys, req)
    rec = _r3._r2.receipt(keys, req, anc)
    _r3.run_research(__file__, trust, work, {'request': req, 'anchor': anc, 'receipt': rec})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.kernel.phases import _frozen_request
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())
    root = work / 'campaign_b'
    with Store(root) as s:
        s.set_state('campaign_id', B)                                  # campaign B's own identity and history
        s.set_state('source_hash', digest('some other source tree'))
        s.save('config', 'resolved', {'domain': 'c4_host_v2', 'profile': 'campaign-b'})
        s.event('GENERATION_STARTED', {'generation': 0, 'public_panels': True})
        s.set_state('campaign_id', A)                                  # relabel
        s.set_state('source_hash', _r3.IDENT)
        s.save('frozen_request', digest(e['request']), e['request'])
        s.set_state('frozen_request_hash', digest(e['request']))
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate', source_hash=_r3.IDENT)
        r = k.record_signed('sealed_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                            source_hash=_r3.IDENT)
        k.create_claim('claim-1', _r3._r2.STATEMENT, _r3._r2.SCOPE, [r], binding=R.binding_from_requests([e['request']]))
        print('kernel:', k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')['level'])
        try:
            _frozen_request(s)
            print('phase-machine binding: accepted')
        except Exception as exc:
            print('phase-machine binding refuses the same request:', exc)
        history = [s.get(json.loads(b)['payload'])['value'] for (b,) in s.db.execute('SELECT body FROM events ORDER BY seq')
                   if json.loads(b)['kind'] == 'STATE_UPDATED' and s.get(json.loads(b)['payload'])['key'] == 'campaign_id']
        print('campaign_id history in events.jsonl:', [h[:8] for h in history])
    build_bundle(root, work / 'b.zip', trust_root=trust, report='Sealed evaluation.')
    v = verify_bundle(work / 'b.zip', trust_root=trust)
    lvl = json.loads(_r3.bundle_file(work / 'b.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['utility']
    print('exported:', lvl, '| verify_bundle ok:', v['ok'], v['problems'][:2])
    print('ATTACK_SUCCEEDED' if v['ok'] and lvl == 'CONFIRMED_SAME_DOMAIN' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
