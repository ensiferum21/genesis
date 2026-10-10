#!/usr/bin/env python3
"""F5: promote/levels/build_index/build_bundle grant OPTIMALITY_CHECKED for a false certificate (R-03).

EvidenceKernel._bound_state_problems only checks custody (schema, objects
present, a self-recorded checker_verdict == 'VALID'). It never checks that a
HOST_EDGE_COUNT bound equals the host edge count, nor runs the proof checker.
Only verify_bundle(replay_proofs=True) replays. K5 (10 edges) has C4-free
optimum 6; we certify "optimum = 4" (A: HOST_EDGE_COUNT value 4; B: SAT_DRAT
with a garbage proof). Every producer-side entry point shows OPTIMALITY_CHECKED,
the wording gate lets "optimal" ship, and verify_bundle(replay_proofs=False)
says ok.
Run: GENESIS_TOOLCHAIN=/home/claude/toolchain PYTHONPATH=src python3 -W ignore audit/redteam_b14/f5_optimality_on_custody_only.py
"""
from itertools import combinations
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file  # noqa: E402

from genesis.common import code_identity, digest  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.kernel.index import build_index  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.verification.certificates import REPLAY, SCHEMA  # noqa: E402
from genesis.verification.sat import ENCODING, encode  # noqa: E402

SRC = 'a' * 64
TASK = GraphTask(task_id='K5', n=5, edges=tuple(combinations(range(5), 2)), family='complete')
STAR = [[0, 1], [0, 2], [0, 3], [0, 4]]          # valid C4-free witness with 4 edges (true optimum is 6)
assert check_witness(TASK, STAR)['value'] == 4


def certify(s, k, variant):
    tj = TASK.model_dump(mode='json'); sha = digest(tj)
    run = k.record('execution_receipt', {'variant': variant}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
    w = k.record('witness_check', {'task': 'K5', 'task_sha256': sha, 'value': 4, 'witness': STAR, 'v': variant},
                 parents=[run], route='genesis.campaign', source_hash=SRC, verdict='VALID', verifier='dual-predicates')
    if variant == 'A':
        upper = {'method': 'HOST_EDGE_COUNT', 'value': 4, 'justification': 'every subgraph has at most all host edges'}
    else:
        cnf = encode(TASK, 5); proof = b'this is not a DRAT proof\n'
        upper = {'method': 'SAT_DRAT', 'value': 4, 'encoding': ENCODING, 'cnf_sha256': s.put_bytes(cnf),
                 'proof_sha256': s.put_bytes(proof), 'proof_bytes': len(proof), 'producer': 'cadical',
                 'checker': 'drat-trim', 'checker_verdict': 'VALID', 'checker_output_tail': 's VERIFIED'}
    bundle = {'schema': SCHEMA, 'problem': {'domain': TASK.domain, 'task': tj, 'task_sha256': sha},
              'lower': {'value': 4, 'witness': STAR, 'checker': 'genesis.graphs.check_witness (dual predicates)'},
              'upper': upper, 'gap': 0, 'status': 'OPTIMALITY_CHECKED', 'replay': REPLAY}
    b = k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': 'K5', 'task_sha256': sha, 'lower': 4,
                                 'upper': 4, 'gap': 0, 'lower_evidence': w, 'certificate_bundle': s.put(bundle)},
                 parents=[w], route='genesis.verification.sat', source_hash=SRC, verdict='VALID',
                 verifier='host-edge-count' if variant == 'A' else 'drat-trim')
    claim = f'optimum-K5-{variant}'
    k.create_claim(claim, 'the C4-free optimum of K5 is 4', 'K5 only', [b])
    k.promote(claim, 'math', 'OPTIMALITY_CHECKED')
    return claim


with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = d / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s)
        claims = [certify(s, k, v) for v in ('A', 'B')]
        print('promote + levels:', {c: k.levels(c)['math'] for c in claims})
        build_index(s, d / 'index.sqlite3')
    rows = dict(sqlite3.connect(d / 'index.sqlite3').execute('SELECT claim_id, current_levels FROM claims'))
    print('build_index claims table:', {c: json.loads(v)['math'] for c, v in rows.items()})
    build_bundle(root, d / 'release.zip', report='This construction is optimal.')
    exported = {c['claim_id']: c['effective_levels']['math']
                for c in json.loads(bundle_file(d / 'release.zip', 'CLAIMS.json'))['claims']}
    print('build_bundle shipped (report "This construction is optimal." passed the gate):', exported)
    print('verify_bundle(replay_proofs=False):', verify_bundle(d / 'release.zip', replay_proofs=False)['ok'])
    r = verify_bundle(d / 'release.zip')
    print('verify_bundle(replay_proofs=True): ok', r['ok'], [p[:90] for p in r['problems']])
    print('ATTACK_SUCCEEDED (producer-side entry points)' if set(exported.values()) == {'OPTIMALITY_CHECKED'}
          else 'ATTACK_BLOCKED')
