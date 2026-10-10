#!/usr/bin/env python3
"""R2: WITNESS_VALID / FINITE_CERTIFIED / THEOREM_CHECKED (and causality, internal replication)
are licensed by producer-written `verdict` fields; nothing replays them, and verify_bundle accepts.

R-03 made OPTIMALITY_CHECKED replay its certificate. The other math levels still
come from `_licensing`'s generic branch: a node of the right kind whose
self-declared verdict is in PASSING, with an eligible *source hash* (the route
is not even checked for non-confirmation levels) and a verifier that is either
None or merely not REVOKED/CIRCULAR (UNREGISTERED is fine). The bundle verifier
re-derives levels with the same logic, so it re-derives the forged ones.

Demo problem: host K4 (6 edges). The claim says it has a C4-free subgraph with 7
edges (impossible: more than the host has), that 7 is the certified optimum and
that this was formally proved. No checker ever ran.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r2_math_levels_from_declared_verdicts.py
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402,F401
from genesis.common import code_identity, digest  # noqa: E402
from genesis.graphs import certified_optimum  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

d = Path(tempfile.mkdtemp())
k4 = GraphTask(task_id='K4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='complete')
sha = digest(k4.model_dump(mode='json'))
print('true C4-free optimum of K4:', certified_optimum(k4)['value'], '| claimed: 7 (host has 6 edges)')
SRC = 'c' * 64
with Store(d / 'c') as s:
    s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
    k = EvidenceKernel(s)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
    w = k.record('witness_check', {'task_sha256': sha, 'value': 7}, parents=[run], route='genesis.campaign',
                 source_hash=SRC, verdict='VALID', verifier=None)
    e1 = k.record('exact_check', {'task_sha256': sha, 'value': 7}, parents=[w], route='genesis.campaign',
                  source_hash=SRC, verdict='VALID', verifier='made-up-checker-1')
    e2 = k.record('exact_check', {'task_sha256': sha, 'value': 7}, parents=[w], route='genesis.campaign',
                  source_hash=SRC, verdict='VALID', verifier='made-up-checker-2')
    f = k.record('formal_check', {'statement': 'opt(K4)=7', 'proof': None}, parents=[e1, e2], route='genesis.campaign',
                 source_hash=SRC, verdict='VALID', verifier=None)
    ab = k.record('ablation', {'delta': 1}, parents=[run], route='genesis.campaign', source_hash=SRC, verdict='PASS')
    pl = k.record('placebo', {'delta': 0}, parents=[run], route='genesis.campaign', source_hash=SRC, verdict='PASS')
    rp = k.record('internal_replication', {}, parents=[run], route='genesis.campaign', source_hash=SRC, verdict='PASS')
    k.create_claim('k4', 'We proved the theorem that the C4-free optimum of K4 is 7; this value is optimal, and the '
                   'weighting causes the gain.', 'host K4', [f, ab, pl, rp], problem={'task_sha256': sha, 'value': 7})
    for axis, level in (('math', 'WITNESS_VALID'), ('math', 'FINITE_CERTIFIED'), ('math', 'THEOREM_CHECKED'),
                        ('causality', 'PLACEBO_CONTROLLED'), ('replication', 'INTERNAL_INDEPENDENT')):
        k.promote('k4', axis, level)
    print('kernel levels:', {a: v for a, v in k.levels('k4').items() if v not in ('NOT_TESTED', 'UNKNOWN', 'NONE')})
build_bundle(d / 'c', d / 'b.zip', report='We proved the theorem: K4 has an optimal C4-free subgraph with 7 edges. '
                                          'The weighting causes the gain.')
r = verify_bundle(d / 'b.zip')
claims = json.loads(_r2.bundle_file(d / 'b.zip', 'CLAIMS.json'))['claims'][0]
print('exported effective levels:', claims['effective_levels'])
print('verify_bundle ok:', r['ok'], r['problems'], '| certificate replays:', r.get('certificate_replays'))
ok = r['ok'] and claims['effective_levels']['math'] == 'THEOREM_CHECKED'

# (b) Checker revocation only reaches nodes that chose to name the checker (verifier is optional).
with Store(d / 'r') as s:
    s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
    k = EvidenceKernel(s)
    reg = k.register_verifier('dual-predicates', 'e' * 64)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
    named = k.record('witness_check', {'value': 7, 'n': 1}, parents=[run], route='genesis.campaign', source_hash=SRC,
                     verdict='VALID', verifier='dual-predicates')
    silent = k.record('witness_check', {'value': 7, 'n': 2}, parents=[run], route='genesis.campaign', source_hash=SRC,
                      verdict='VALID', verifier=None)       # same checker, producer just leaves the field empty
    for cid, node in (('named', named), ('silent', silent)):
        k.create_claim(cid, f'host H{cid} has a valid subgraph with 7 edges', 'host H', [node])
        k.promote(cid, 'math', 'WITNESS_VALID')
build_bundle(d / 'r', d / 'release1.zip', report='')
with Store(d / 'r') as s:
    EvidenceKernel(s).revoke(reg, 'dual-predicates accepts 4-cycles', 'auditor')
build_bundle(d / 'r', d / 'release2.zip', report='')
feed = d / 'REVOCATIONS.json'; feed.write_bytes(_r2.bundle_file(d / 'release2.zip', 'REVOCATIONS.json'))
later = verify_bundle(d / 'release1.zip', later_revocations=feed)
now = {c['claim_id']: c['effective_levels']['math'] for c in later['current']['claims']}
print('(b) after revoking the checker: current levels', now, '| downgraded_since_release',
      later['current']['downgraded_since_release'], '| release2 verify ok', verify_bundle(d / 'release2.zip')['ok'])
ok = ok and now['silent'] == 'WITNESS_VALID'
print('ATTACK_SUCCEEDED' if ok else 'ATTACK_BLOCKED')
