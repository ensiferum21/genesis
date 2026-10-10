#!/usr/bin/env python3
"""R2: WITNESS_VALID for false mathematical statements, exported and accepted by verify_bundle.

The witness check is genuinely replayed, but nothing ties what was replayed to
what the claim says:
  (a) `problem` is optional below OPTIMALITY_CHECKED, so ANY replayable witness
      check in the closure licenses WITNESS_VALID for a statement about any host;
  (b) with `problem` present, the free-text statement is still unconstrained
      (the problem value is 3, the statement says 30);
  (c) the wording gate knows "optimal"/"optimality" but not "optimum",
      "maximum", "largest", "extremal number", so a lower bound is exported as
      "the optimum is 3" although the true optimum (certified here) is 4.
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r2_witness_valid_false_statements.py
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
from tests_genesis.signed_fixtures import path4, witness_payload  # noqa: E402

K4 = GraphTask(task_id='k4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='complete')
# (d) domain confusion: the stored problem is the TRIANGLE-free domain on K6; the statement speaks of C4.
K6_TRI = GraphTask(task_id='k6-c4', domain='triangle_free_host_v1', n=6,
                   edges=tuple((u, v) for u in range(6) for v in range(u + 1, 6)), family='complete')
K33 = [[u, v] for u in range(3) for v in range(3, 6)]   # 9 edges, triangle-free, full of 4-cycles
CLAIMS = {
    'a-unbound': ('host K63 (the complete graph on 63 vertices) has a C4-free subgraph with 1000 edges, '
                  'so ex(63, C4) >= 1000', None, 'path4'),
    'b-mismatch': ('host k4 has a C4-free subgraph with 30 edges', 'k4', 'k4'),
    'c-optimum': ('the optimum for host k4 is 3: the maximum C4-free subgraph of k4 has exactly 3 edges '
                  'and no larger one exists', 'k4', 'k4'),
    'd-domain': ('host k6-c4 (K6) has a C4-free subgraph with 9 edges', 'k6', 'k6'),
}
REPORT = ('The optimum for host k4 is 3 and the largest C4-free subgraph of K63 has at least 1000 edges; '
          'the extremal number ex(63, C4) is at least 1000.')


def main():
    tmp = Path(tempfile.mkdtemp(prefix='r3-r2-'))
    root = tmp / 'campaign'
    with Store(root) as s:
        s.set_state('campaign_id', 'c' * 64)
        s.set_state('source_hash', _r3.IDENT)
        k = EvidenceKernel(s)
        nodes = {}
        for name, task, witness in (('path4', path4(), None), ('k4', K4, [[0, 1], [0, 2], [1, 2]]),
                                    ('k6', K6_TRI, K33)):
            run = k.record('execution_receipt', {'ir_program': None, 'attempt': None, 'task': name},
                           route='genesis.campaign', source_hash=_r3.IDENT, verdict='VALID')
            payload = witness_payload(s, task, witness)
            nodes[name] = (k.record('witness_check', payload, parents=[run], route='genesis.campaign',
                                    source_hash=_r3.IDENT, verdict='VALID', verifier='dual-predicates'), payload)
        for cid, (statement, prob, dep) in CLAIMS.items():
            nid, payload = nodes[dep]
            problem = {'task_sha256': payload['task_sha256'], 'value': payload['value']} if prob else None
            k.create_claim(cid, statement, 'this finite host only', [nid], problem=problem)
            k.promote(cid, 'math', 'WITNESS_VALID')
            print(f'{cid}: effective math={k.levels(cid)["math"]} | problem={problem and problem["value"]} '
                  f'| replayed witness value={payload["value"]} on task {payload["task"]}')
    print('true optimum of k4 (dual exact solvers):', certified_optimum(K4)['value'],
          '| true C4-free optimum of K6:', certified_optimum(K6_TRI.model_copy(update={'domain': 'c4_host_v2'}))['value'])
    build_bundle(root, tmp / 'release.zip', report=REPORT)
    with zipfile.ZipFile(tmp / 'release.zip') as z:
        claims = json.loads(z.read(next(n for n in z.namelist() if n.endswith('/CLAIMS.json'))))
    for c in claims['claims']:
        print('exported', c['claim_id'], c['effective_levels']['math'], '|', c['statement'][:80])
    v = verify_bundle(tmp / 'release.zip')
    print('verify_bundle ok:', v['ok'], v['problems'][:3])
    ok = v['ok'] and all(c['effective_levels']['math'] == 'WITNESS_VALID' for c in claims['claims'])
    print('ATTACK_SUCCEEDED' if ok else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    main()
