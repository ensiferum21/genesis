#!/usr/bin/env python3
"""R1: verified_phase (and the index built from it) reports RELEASED without the intended signed chain.

phases.verified_phase re-derives the phase from the event history but, for each
scientific phase, only calls _open() (signature + schema under the role); it
never runs _check_payload(). So it does not check that
  * the RELEASED envelope is a RELEASE decision (a signed REJECT works),
  * the decision references the judged receipt, or that the receipt is SUPPORTED,
  * SEALED_RUNNING/JUDGED receipts are for the frozen request.
In addition, neither advance() nor verified_phase ties the frozen request to the
campaign (request.campaign_id vs state campaign_id), so another campaign's
public request + envelopes replay verbatim, through advance() itself.

Production trust path: root holds the keys, the research child runs as UID 65534.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r1_phase_released_without_chain.py
"""
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402


def parent():
    base, keys, trust, work = _r2.production_setup()
    # Campaign A (attacker's own): a genuine NOT_SUPPORTED evaluation and a signed REJECT.
    req_a = _r2.request(claim_id='claim-A', campaign='a' * 64)
    anc_a = _r2.anchor(keys, req_a)
    rec_a = _r2.receipt(keys, req_a, anc_a, wins=5, losses=30, ties=5)
    reject_a = sign({'schema': 'genesis-release-decision-v1', 'request_hash': digest(req_a), 'decision': 'REJECT',
                     'receipt_hash': digest(rec_a)}, keys['release'][0])
    # Campaign X (someone else's, released, all public): request, anchor, SUPPORTED receipt, RELEASE.
    req_x = _r2.request(claim_id='claim-X', campaign='f' * 64, candidate='9' * 64)
    anc_x = _r2.anchor(keys, req_x)
    rec_x = _r2.receipt(keys, req_x, anc_x)
    release_x = sign({'schema': 'genesis-release-decision-v1', 'request_hash': digest(req_x), 'decision': 'RELEASE',
                      'receipt_hash': digest(rec_x)}, keys['release'][0])
    print('outcomes: own campaign', rec_a['payload']['outcome'], '| other campaign', rec_x['payload']['outcome'])
    _r2.run_research(__file__, trust, work, {'a': [req_a, anc_a, rec_a, reject_a], 'x': [req_x, anc_x, rec_x, release_x]})


def child(trust, work):
    from genesis.kernel.index import build_index
    from genesis.kernel.phases import PhaseError, advance, verified_phase
    from genesis.store import Store
    data = json.loads((work / 'inputs.json').read_bytes())
    eng = ['VALIDATED_CONFIG', 'DEV_RUNNING', 'CANDIDATE_FROZEN']

    def frozen(s, campaign_id, req):
        s.set_state('campaign_id', campaign_id)
        s.save('frozen_request', digest(req), req)
        s.set_state('frozen_request_hash', digest(req))

    # (a) own campaign: NOT_SUPPORTED, release authority signed REJECT.
    req, anc, rec, reject = data['a']
    with Store(work / 'campaign_a') as s:
        for t in eng:
            advance(s, t)
        frozen(s, 'campaign-A', req)
        for t, env in (('LEAK_SCAN_PASSED', anc), ('SEALED_RUNNING', rec), ('JUDGED', rec)):
            advance(s, t, envelope=env, trust_root=trust)
        try:
            advance(s, 'RELEASED', envelope=reject, trust_root=trust)
            print('(a) advance RELEASED with REJECT: accepted (!)')
        except PhaseError as e:
            print('(a) advance RELEASED with REJECT: refused by advance():', str(e)[:70])
        s.set_state('phase_receipt:RELEASED', reject)   # the producer writes its own store
        s.set_state('phase', 'RELEASED')
        print('(a) verified_phase:', {k: v for k, v in verified_phase(s, trust_root=trust).items()})
        build_index(s, work / 'index_a.sqlite3', trust_root=trust)
    print('(a) index campaigns:', sqlite3.connect(work / 'index_a.sqlite3').execute('SELECT campaign_id, status FROM campaigns').fetchall())

    # (b) campaign B never evaluated anything: replay campaign X's public request and envelopes.
    req, anc, rec, release = data['x']
    with Store(work / 'campaign_b') as s:
        for t in eng:
            advance(s, t)
        frozen(s, 'campaign-B', req)
        out = []
        for t, env in (('LEAK_SCAN_PASSED', anc), ('SEALED_RUNNING', rec), ('JUDGED', rec), ('RELEASED', release)):
            advance(s, t, envelope=env, trust_root=trust); out.append(t)
        print('(b) advance() accepted for campaign-B:', out, '| request campaign_id', req['campaign_id'][:8])
        vp = verified_phase(s, trust_root=trust)
        print('(b) verified_phase:', vp)
        build_index(s, work / 'index_b.sqlite3', trust_root=trust)
    print('(b) index campaigns:', sqlite3.connect(work / 'index_b.sqlite3').execute('SELECT campaign_id, status FROM campaigns').fetchall())
    a_ok = sqlite3.connect(work / 'index_a.sqlite3').execute('SELECT status FROM campaigns').fetchone()[0] == 'RELEASED'
    b_ok = vp['phase'] == 'RELEASED' and vp['consistent']

    # (c) `genesis campaign status` still prints the mutable phase: no envelope at all.
    import contextlib, io
    from genesis.campaign import Campaign
    from genesis.cli import main
    from genesis.models import Config
    Campaign.initialize(work / 'campaign_c', Config(generations=1, tasks_per_panel=3))
    with Store(work / 'campaign_c') as s:
        s.set_state('phase', 'RELEASED')
        vp_c = verified_phase(s, trust_root=trust); print('(c) verified_phase:', vp_c['phase'], vp_c['consistent'], vp_c['problems'])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main(['campaign', 'status', str(work / 'campaign_c')])
    c_phase = json.loads(buf.getvalue())['phase']
    print('(c) `genesis campaign status` phase:', c_phase)
    print('ATTACK_SUCCEEDED' if a_ok and b_ok and c_phase == 'RELEASED' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
