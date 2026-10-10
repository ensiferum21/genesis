#!/usr/bin/env python3
"""F9: an OPTIMALITY_CHECKED claim is not bound to the problem its certificate certifies (R-03).

_bound_state_problems compares the certificate with the bound state's own
task_sha256 (producer-chosen) but never with the bound state's `task` label, the
witness check's task, or anything in the claim. A genuinely replayable
certificate for a 3-edge path (HOST_EDGE_COUNT) supports "the optimum for host
K6 is 3" (true C4-free optimum of K6 is 7); verify_bundle replays it
successfully and returns ok.
Run: GENESIS_TOOLCHAIN=/home/claude/toolchain PYTHONPATH=src python3 -W ignore audit/redteam_b14/f9_optimality_problem_unbound.py
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file  # noqa: E402

from genesis.common import code_identity, digest  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.verification.certificates import REPLAY, SCHEMA  # noqa: E402

SRC = 'a' * 64
PATH = GraphTask(task_id='K6', n=4, edges=((0, 1), (1, 2), (2, 3)), family='complete')  # a path, labelled K6
tj = PATH.model_dump(mode='json'); sha = digest(tj)
with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = d / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        k = EvidenceKernel(s)
        run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
        w = k.record('witness_check', {'task': 'K6', 'value': 3}, parents=[run], route='genesis.campaign',
                     source_hash=SRC, verdict='VALID', verifier='dual-predicates')   # no task_sha256: defaults to match
        bundle = {'schema': SCHEMA, 'problem': {'domain': 'c4_host_v2', 'task': tj, 'task_sha256': sha},
                  'lower': {'value': 3, 'witness': [list(e) for e in PATH.edges], 'checker': 'dual predicates'},
                  'upper': {'method': 'HOST_EDGE_COUNT', 'value': 3, 'justification': 'all host edges'},
                  'gap': 0, 'status': 'OPTIMALITY_CHECKED', 'replay': REPLAY}
        b = k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': 'K6', 'task_sha256': sha, 'lower': 3,
                                     'upper': 3, 'gap': 0, 'lower_evidence': w, 'certificate_bundle': s.put(bundle)},
                     parents=[w], route='genesis.verification.sat', source_hash=SRC, verdict='VALID',
                     verifier='host-edge-count')
        k.create_claim('optimum:K6:3', 'the C4-free optimum of the complete graph K6 is 3', 'K6', [b])
        k.promote('optimum:K6:3', 'math', 'OPTIMALITY_CHECKED')
    build_bundle(root, d / 'release.zip')
    r = verify_bundle(d / 'release.zip')
    c = json.loads(bundle_file(d / 'release.zip', 'CLAIMS.json'))['claims'][0]
    print('exported:', c['statement'], c['effective_levels']['math'])
    print('verify ok:', r['ok'], r['problems'], '| replays:', [(x['status'], x['lower'], x['upper'])
                                                              for x in r['certificate_replays']])
    print('ATTACK_SUCCEEDED' if r['ok'] and c['effective_levels']['math'] == 'OPTIMALITY_CHECKED' else 'ATTACK_BLOCKED')
