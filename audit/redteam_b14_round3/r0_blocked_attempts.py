#!/usr/bin/env python3
"""R0: attempts that were BLOCKED on this tree (for the record).
  PYTHONPATH=src:. GENESIS_TOOLCHAIN=/home/claude/toolchain python3 -W ignore audit/redteam_b14_round3/r0_blocked_attempts.py
"""
import json
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from genesis.common import canonical, digest  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.verification.certificates import build, persist  # noqa: E402
from genesis.verification.sat import certified_bounds  # noqa: E402

K4 = GraphTask(task_id='k4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='complete')


def attempt(label, fn):
    try:
        out = fn()
        print(f'NOT BLOCKED  {label}: {out}')
    except PromotionRejected as exc:
        print(f'BLOCKED      {label}: {exc.args[0][0][:110]}')
    except Exception as exc:
        print(f'BLOCKED      {label}: {type(exc).__name__}: {str(exc)[:110]}')


def main():
    d = Path(tempfile.mkdtemp(prefix='r3-r0-'))
    s = Store(d / 's'); s.set_state('source_hash', 'c' * 64)
    k = EvidenceKernel(s)

    def witness(task_bytes_sha, edges, value, cid):
        n = k.record('witness_check', {'schema': 'genesis-witness-check-v2', 'task': 'k4', 'task_sha256': task_bytes_sha,
                                       'witness': edges, 'value': value}, route='genesis.campaign',
                     source_hash='c' * 64, verdict='VALID')
        k.create_claim(cid, 'host k4 has a C4-free subgraph', 'this host', [n])
        return k.promote(cid, 'math', 'WITNESS_VALID')['level']

    good = K4.model_dump(mode='json')
    variant = s.put_bytes(json.dumps(good, indent=1).encode())          # same task, other bytes
    attempt('task stored with non-canonical bytes', lambda: witness(variant, [[0, 1]], 1, 'v1'))
    sha = s.put(good)
    attempt('witness edge outside the host', lambda: witness(sha, [[0, 1], [0, 4]], 2, 'v2'))
    attempt('witness containing a 4-cycle', lambda: witness(sha, [[0, 1], [1, 2], [2, 3], [0, 3]], 4, 'v3'))
    attempt('recorded value larger than the witness', lambda: witness(sha, [[0, 1]], 5, 'v4'))
    attempt('GraphTask with unsorted/duplicate edges or a self-loop',
            lambda: GraphTask(task_id='x', n=4, edges=((1, 0), (1, 1)), family='x'))
    # Certificate bundle whose embedded task is a different domain than the bound task.
    tri = K4.model_copy(update={'domain': 'triangle_free_host_v1'})
    bounds = certified_bounds(tri, seconds=30, start_witness=((0, 2), (0, 3), (1, 2), (1, 3)))
    bundle, blobs = build(tri, bounds)
    ref = persist(s, bundle, blobs)
    w = k.record('witness_check', {'schema': 'genesis-witness-check-v2', 'task': 'k4', 'task_sha256': sha,
                                   'witness': [[0, 1], [0, 2], [1, 2], [0, 3]], 'value': 4}, route='genesis.campaign',
                 source_hash='c' * 64, verdict='VALID')
    b = k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': 'k4', 'task_sha256': sha, 'lower': 4,
                                 'upper': 4, 'gap': 0, 'lower_evidence': w, 'certificate_bundle': ref}, parents=[w],
                 route='genesis.verification.sat', source_hash='c' * 64, verdict='VALID')
    k.create_claim('o1', 'optimum of k4', 'this host', [b], problem={'task_sha256': sha, 'value': 4})
    attempt('certificate of the triangle-free K4 bound to the C4 K4 problem',
            lambda: k.promote('o1', 'math', 'OPTIMALITY_CHECKED')['level'])
    # Custodian export with a path escape.
    from genesis.custodian import campaign_facts
    z = d / 'evil.zip'
    with zipfile.ZipFile(z, 'w') as f:
        f.writestr('events.jsonl', b''); f.writestr('../x.json', b'{}')
    attempt('campaign export with ../ path', lambda: campaign_facts(z))
    s.close()


if __name__ == '__main__':
    main()
