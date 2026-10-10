#!/usr/bin/env python3
"""R6: OPTIMALITY_CHECKED for a FALSE statement, with a genuine certificate that
verify_bundle replays with drat-trim.

The claim's `problem` is {task_sha256, value}; the forbidden-subgraph domain lives
inside the hashed task, never in anything the statement is checked against. The
problem here is K6 in the triangle-free domain (optimum 9 by Mantel, certified by
a real CaDiCaL/DRAT certificate replayed by drat-trim). The task is labelled
'k6-c4' and the claim statement says the C4-free optimum of K6 is 9; the true
C4-free optimum of K6 is 7 (dual exact solvers below). Every check passes:
witness replay, certificate replay, problem binding, wording gate, bundle
verification.
  PYTHONPATH=src:. GENESIS_TOOLCHAIN=/home/claude/toolchain python3 -W ignore \
      audit/redteam_b14_round3/r6_optimality_checked_false_statement.py
"""
import json
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.graphs import certified_optimum  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.verification.certificates import build, persist  # noqa: E402
from genesis.verification.sat import certified_bounds  # noqa: E402

K6 = GraphTask(task_id='k6-c4', domain='triangle_free_host_v1', n=6,
               edges=tuple((u, v) for u in range(6) for v in range(u + 1, 6)), family='complete-c4-host')
STATEMENT = 'the optimum for host k6-c4 is 9: the largest C4-free subgraph of K6 has exactly 9 edges'


def main():
    tmp = Path(tempfile.mkdtemp(prefix='r3-r6-'))
    root = tmp / 'campaign'
    bounds = certified_bounds(K6, seconds=60, start_witness=tuple((u, v) for u in range(3) for v in range(3, 6)))
    print('certified_bounds:', bounds['status'], 'lower', bounds['lower'], 'upper', bounds['upper'],
          'method', bounds['upper_certificate']['method'])
    with Store(root) as s:
        s.set_state('campaign_id', 'c' * 64); s.set_state('source_hash', _r3.IDENT)
        k = EvidenceKernel(s)
        sha = s.put(K6.model_dump(mode='json'))
        w = k.record('witness_check', {'schema': 'genesis-witness-check-v2', 'task': K6.task_id, 'task_sha256': sha,
                                       'witness': [list(e) for e in bounds['witness']], 'value': bounds['lower']},
                     route='genesis.campaign', source_hash=_r3.IDENT, verdict='VALID', verifier='dual-predicates')
        cert = persist(s, *build(K6, bounds))
        b = k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': K6.task_id, 'task_sha256': sha,
                                     'lower': bounds['lower'], 'upper': bounds['upper'], 'gap': 0,
                                     'lower_evidence': w, 'certificate_bundle': cert},
                     parents=[w], route='genesis.verification.sat', source_hash=_r3.IDENT, verdict='VALID',
                     verifier='drat-trim')
        k.create_claim('optimum:k6-c4:9', STATEMENT, 'this finite host only', [b],
                       problem={'task_sha256': sha, 'value': 9})
        k.promote('optimum:k6-c4:9', 'math', 'OPTIMALITY_CHECKED')
        print('effective:', k.levels('optimum:k6-c4:9')['math'])
    print('true C4-free optimum of K6 (dual exact solvers):',
          certified_optimum(K6.model_copy(update={'domain': 'c4_host_v2'}))['value'])
    build_bundle(root, tmp / 'release.zip', report='The optimum for host k6-c4 is 9.')
    with zipfile.ZipFile(tmp / 'release.zip') as z:
        c = json.loads(z.read(next(n for n in z.namelist() if n.endswith('/CLAIMS.json'))))['claims'][0]
    v = verify_bundle(tmp / 'release.zip')
    print('exported', c['effective_levels']['math'], '|', c['statement'])
    print('verify_bundle ok:', v['ok'], v['problems'][:2], '| certificate replays:',
          [(r['status'], r['upper']) for r in v['certificate_replays']])
    print('ATTACK_SUCCEEDED' if v['ok'] and c['effective_levels']['math'] == 'OPTIMALITY_CHECKED' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    main()
