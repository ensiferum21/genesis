#!/usr/bin/env python3
"""R1: the custodian signs a SUPPORTED receipt for "frozen candidate V of campaign C"
although the program it evaluated is not C's frozen candidate, and the same
claim (same claim_id, statement, candidate_version) can be preregistered again
and again by perturbing the candidate program.

`candidate_version` is a free label in the request. Neither custodian.register()
nor evaluate() nor the kernel ties it (or programs['candidate']) to the campaign
export (`latest_program`, the frozen version, the candidate's lineage). The
registration slot is keyed by the candidate *program*, so a second, third ...
request for the SAME claim id / statement / candidate_version with a slightly
different program is a new slot (F11 one-draw-per-claim regressed by H2).

Flow (real custodian, production trust path with a UID-65534 research child):
  campaign C exports latest_program = P_frozen (a weak program);
  request A: candidate = stock 'exchange' program (never produced by C), label V;
  request B: candidate = P_frozen (the honest one), same claim/statement/label V;
  request C: candidate = exchange with rounds=31, same claim/statement/label V;
  all three register; A is SUPPORTED, B is not; the claim bound to A only is
  promoted to CONFIRMED_SAME_DOMAIN and the release bundle verifies.
  PYTHONPATH=src:. GENESIS_TOOLCHAIN=/home/claude/toolchain python3 -W ignore \
      audit/redteam_b14_round3/r1_candidate_not_bound_to_campaign.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.common import bytes_hash, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402

CAMPAIGN = '5eed' * 16
P_FROZEN = SolverProgram(weights=(0, 0, 0, -8), rounds=1).model_dump(mode='json')  # what C actually froze
P_SWAP = SolverProgram(rounds=32, exchange=True).model_dump(mode='json')            # stock baseline, not from C
P_SWAP2 = SolverProgram(rounds=31, exchange=True).model_dump(mode='json')
BASELINE = SolverProgram(rounds=1).model_dump(mode='json')
V = digest({'program': P_FROZEN, 'source': _r3.IDENT})                              # label as cli.request_bundle builds it
STATEMENT = f'frozen candidate {V[:12]} has a higher paired edge count than the frozen baseline on the sealed c4_host_v2 panel'
SCOPE = 'c4_host_v2 hosts in one sealed panel of 24 tasks'
CLAIM = f'utility:{V[:16]}'


def parent():
    from genesis.custodian import evaluate, register
    base, keys, trust, work = _r3.production_setup()
    private, manifest = _r3.custodian_dirs(base)
    root, export = _r3.campaign_store(work / 'campaign', campaign_id=CAMPAIGN, latest_program=P_FROZEN)
    reqs, receipts = {}, {}
    for tag, prog, seed in (('A', P_SWAP, 11), ('B', P_FROZEN, 12), ('C', P_SWAP2, 13)):
        req = _r3._r2.request(claim_id=CLAIM, campaign=CAMPAIGN, candidate=V, cand_program=prog, baseline=BASELINE,
                              task_count=24, statement=STATEMENT, scope=SCOPE, source=_r3.IDENT,
                              evaluator=_r3.IDENT, export_sha=bytes_hash(export.read_bytes()))
        pool = _r3.write_pool(base / f'pool{tag}.json', _r3.pool(seed))
        anchor = register(private, req, keys['prereg'][0], 'custodian-op', exposure_manifest=manifest,
                          campaign_export=export, pool=pool)
        print(f'register {tag}: accepted | claim {req["claim_id"]} | candidate_version {V[:12]} | candidate program '
              f'{R.program_identity(prog)[:12]} | slot {anchor["payload"]["registration_slot"][:12]}')
        receipt = evaluate(private, digest(req), pool, keys['custodian'][0], 'custodian-op')
        p = receipt['payload']
        print(f'evaluate {tag}: {p["outcome"]} wins={p["wins"]} losses={p["losses"]} ties={p["ties"]} '
              f'family_p={p["family_p"]:.4f} | signed candidate_version {p["candidate_version"][:12]} '
              f'candidate_program_hash {p["candidate_program_hash"][:12]}')
        reqs[tag], receipts[tag] = req, (anchor, receipt)
    print('campaign latest_program identity', R.program_identity(P_FROZEN)[:12],
          '| program evaluated in A', R.program_identity(P_SWAP)[:12])
    _r3.chown_tree(root)
    _r3.run_research(__file__, trust, work, {'request': reqs['A'], 'anchor': receipts['A'][0],
                                             'receipt': receipts['A'][1]})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())
    root = work / 'campaign'
    with Store(root) as s:
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                            source_hash=_r3.IDENT)
        r = k.record_signed('sealed_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                            source_hash=_r3.IDENT)
        k.create_claim(CLAIM, STATEMENT, SCOPE, [r], binding=R.binding_from_requests([e['request']]))
        d = k.promote(CLAIM, 'utility', 'CONFIRMED_SAME_DOMAIN')
        print('child (uid 65534, real trust root): promoted', d['level'], '| effective', k.levels(CLAIM)['utility'])
        print('store latest_program identity', R.program_identity(s.state('latest_program'))[:12],
              '!= receipt candidate_program_hash', e['receipt']['payload']['candidate_program_hash'][:12])
    build_bundle(root, work / 'release.zip', trust_root=trust, report='Sealed evaluation of the frozen candidate.')
    level = json.loads(_r3.bundle_file(work / 'release.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['utility']
    v = verify_bundle(work / 'release.zip', trust_root=trust)
    print('exported:', level, '| verify_bundle ok:', v['ok'], v['problems'][:3])
    print('ATTACK_SUCCEEDED' if v['ok'] and level == 'CONFIRMED_SAME_DOMAIN' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
