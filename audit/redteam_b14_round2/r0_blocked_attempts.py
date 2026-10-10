#!/usr/bin/env python3
"""R0: attacks tried in round 2 that the current tree blocks (kernel logic with fixture
keys; production-path blocks are shown in r1/r6/r7 outputs).
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round2/r0_blocked_attempts.py
"""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.verification.certificates import build, persist  # noqa: E402
from tests_genesis.signed_fixtures import SignedFixture, record_evaluation  # noqa: E402

d = Path(tempfile.mkdtemp())
fx = SignedFixture(d)
results = []


def attempt(name, fn):
    try:
        out = fn()
        results.append((name, 'NOT BLOCKED', out))
    except (PromotionRejected, ValueError, RuntimeError, KeyError) as e:
        msg = e.args[0] if e.args else ''
        results.append((name, 'blocked', (' | '.join(msg) if isinstance(msg, list) else str(msg))[:110]))


s = Store(d / 's')
k = EvidenceKernel.with_fixture_registry(s, fx.registry)
run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash='c' * 64, verdict='VALID')


def anchor_swap():
    r1, r2 = fx.request(claim_id='swap', seed=1), fx.request(claim_id='swap', seed=2)
    a1 = fx.anchor(r1)
    rec = fx.receipt(r2, a1)                       # receipt for r2 citing r1's anchor
    _, node = record_evaluation(k, fx, r2, [run], anchor=a1, receipt=rec)
    k.create_claim('swap', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node], binding=R.binding_from_requests([r2]))
    return k.promote('swap', 'utility', 'CONFIRMED_SAME_DOMAIN')


def malleated_copies():
    req_a = fx.request(claim_id='mall', kind='sealed_improver_evaluation', seed=3)
    anc = fx.anchor(req_a); rec = fx.receipt(req_a, anc)
    sig = rec['signature']; alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    alt = dict(rec, signature=sig[:-3] + alpha[alpha.index(sig[-3]) ^ 1] + '==')
    assert base64.b64decode(alt['signature'], validate=True) == base64.b64decode(sig) and alt != rec
    a = k.record_signed('preregistration_anchor', anc, route='genesis.custodian.evaluate', source_hash='c' * 64)
    nodes = [k.record_signed('sealed_improver_evaluation', e, parents=[a, run], route='genesis.custodian.evaluate',
                             source_hash='c' * 64) for e in (rec, alt)]
    k.create_claim('mall', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes, binding=R.binding_from_requests([req_a]))
    from genesis.kernel.evidence import _Context
    _, used = k._licensing(k.claim('mall'), 'improver', 'SAME_DOMAIN_CONFIRMED', _Context(k))
    print(f'  [malleated] wrapper nodes {len(nodes)}, distinct envelopes {len({canonical(e) for e in (rec, alt)})}, '
          f'counted evaluations {len(used["evaluations"])}')
    return k.promote('mall', 'improver', 'CROSS_DOMAIN_CONFIRMED')


def json_numbers():
    req = fx.request(claim_id='num')
    anc = fx.anchor(req)
    bad = []
    for field, value in (('wins', 30.0), ('ties', True), ('paired_p', -0.0), ('task_count', 40.0)):
        p = fx.receipt_payload(req, anc); p[field] = value
        payload, why = R.accept_receipt(fx.sign(p, 'custodian'), 'sealed_evaluation', fx.registry['pins'])
        bad.append((field, payload is None))
    if all(b for _, b in bad):
        raise ValueError(f'all rejected: {bad}')
    return bad


def fork_chain():
    v = [f'{i}' * 64 for i in range(1, 6)]
    from genesis.models import SolverProgram
    P = [SolverProgram(rounds=i + 1).model_dump(mode='json') for i in range(5)]
    reqs = [fx.request(claim_id='fork', kind='sealed_generation_evaluation', candidate=v[i + 1], seed=10 + i,
                       transition={'index': i + 1, 'from_version': v[i], 'to_version': v[i + 1]},
                       baseline_program=P[i], candidate_program=P[i + 1]) for i in range(3)]
    reqs.append(fx.request(claim_id='fork', kind='sealed_generation_evaluation', candidate=v[2], seed=20,
                           transition={'index': 2, 'from_version': v[4], 'to_version': v[2]},
                           baseline_program=P[4], candidate_program=P[2]))   # second, ambiguous parent of v2
    nodes = [record_evaluation(k, fx, r, [run])[1] for r in reqs]
    k.create_claim('fork', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes, binding=R.binding_from_requests(reqs))
    return k.promote('fork', 'improver', 'MULTIGEN_CONFIRMED')


def replay_cache_after_object_tamper():
    from genesis.verification.sat import certified_bounds
    k4 = GraphTask(task_id='K4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='complete')
    bounds = certified_bounds(k4, seconds=60)
    bundle, blobs = build(k4, bounds)
    ref = persist(s, bundle, blobs)
    sha = digest(k4.model_dump(mode='json'))
    wn = k.record('witness_check', {'task_sha256': sha, 'value': bounds['lower']}, parents=[run],
                  route='genesis.campaign', source_hash='c' * 64, verdict='VALID')
    bn = k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': 'K4', 'task_sha256': sha,
                                  'lower': bounds['lower'], 'upper': bounds['upper'], 'gap': 0, 'lower_evidence': wn,
                                  'certificate_bundle': ref}, parents=[wn], route='genesis.verification.sat',
                  source_hash='c' * 64, verdict='VALID')
    k.create_claim('opt', 'the C4-free optimum of K4 is 4', 'host K4', [bn], problem={'task_sha256': sha, 'value': 4})
    k.promote('opt', 'math', 'OPTIMALITY_CHECKED')
    before = k.levels('opt')['math']
    proof = s.root / 'objects/sha256' / bundle['upper']['proof_sha256']
    os.chmod(proof, 0o600); proof.write_bytes(b'd 1 2 0\n')         # alter the proof after the replay is cached
    after = k.levels('opt')['math']
    if after != 'OPTIMALITY_CHECKED':
        raise RuntimeError(f'cached replay not reused: {before} -> {after} ({bundle["upper"]["method"]})')
    return before, after


def later_feed_unknown_type():
    with Store(d / 'b') as t:
        t.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
    build_bundle(d / 'b', d / 'b.zip', report='')
    feed = d / 'feed.json'; feed.write_bytes(canonical({'records': [{'target_type': 'claim', 'artifact': 'x', 'reason': 'r'}]}))
    r = verify_bundle(d / 'b.zip', later_revocations=feed)
    if not r['ok']:
        raise ValueError(f"fails closed: {r['problems'][0][:80]}")
    return r


def zip_slip():
    with zipfile.ZipFile(d / 'b.zip') as z, zipfile.ZipFile(d / 'slip.zip', 'w') as o:
        for n in z.namelist():
            o.writestr(n, z.read(n))
        o.writestr('release_x/../../../tmp/evil.txt', b'x')
    return verify_bundle(d / 'slip.zip')


def claims_nan():
    def ch(files, m):
        files['CLAIMS.json'] = files['CLAIMS.json'].replace(b'"claims":[]', b'"claims":[],"x":NaN')
    _r2.rewrite_bundle(d / 'b.zip', d / 'nan.zip', ch)
    r = verify_bundle(d / 'nan.zip')
    if not r['ok']:
        raise ValueError(f"rejected: {r['problems'][0][:80]}")
    return r


for name, fn in (('receipt cites another request\'s anchor', anchor_swap),
                 ('two signature spellings of one receipt for CROSS_DOMAIN', malleated_copies),
                 ('JSON number edge cases in signed counts/probabilities', json_numbers),
                 ('generation chain with an ambiguous fork', fork_chain),
                 ('later revocation feed with an unknown target_type', later_feed_unknown_type),
                 ('zip-slip entry name', zip_slip),
                 ('CLAIMS.json carrying NaN', claims_nan),
                 ('replay cache vs proof object altered after caching', replay_cache_after_object_tamper)):
    attempt(name, fn)
s.close()
for name, status, info in results:
    print(f'{status:12} {name}: {info}')
