#!/usr/bin/env python3
"""R8 (LOW; F4 variant): program identity is digest(raw request dict), not the program.

SolverProgram fills defaults, so {'rounds': 1}, {'rounds': 1, 'exchange': False}
and the full model_dump() are one program with three hashes. Hence
  * check_request's "candidate and baseline are the same program" is bypassed and
    custodian.validate_request accepts a self-comparison;
  * generation_chain's "no repeated programs" accepts the 2-program cycle
    P0 -> P1 -> P0' -> P1' as three distinct successive improvements.
Honest deterministic evaluation of identical programs gives ties (NOT_SUPPORTED),
and the cycle needs P1>P0, P0>P1, P1>P0 on three panels, so this is LOW unless
execution is noisy. Kernel logic shown with fixture keys.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r8_program_identity_by_encoding.py
"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402,F401
from genesis.common import digest  # noqa: E402
from genesis.custodian import validate_request  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402
from genesis.store import Store  # noqa: E402
from tests_genesis.signed_fixtures import SignedFixture, record_evaluation  # noqa: E402

from genesis.common import canonical  # noqa: E402


def prog(x):  # exactly how custodian.validate_request parses an arm
    return SolverProgram.model_validate_json(canonical(x))


a, b = {'rounds': 1}, SolverProgram(rounds=1).model_dump(mode='json')
same = prog(a) == prog(b)
fx = SignedFixture(tempfile.mkdtemp())
req = fx.request(baseline_program=b, candidate_program=a)
print('same program:', same, '| digests differ:', digest(a) != digest(b), '| check_request:', R.check_request(req),
      '| validate_request ok:', bool(validate_request(req)))

p0 = [{'rounds': 1}, SolverProgram(rounds=1).model_dump(mode='json')]
p1 = [{'rounds': 2}, SolverProgram(rounds=2).model_dump(mode='json')]
progs = [p0[0], p1[0], p0[1], p1[1]]                     # P0, P1, P0', P1'
v = ['1' * 64, '2' * 64, '3' * 64, '4' * 64]
reqs = [fx.request(claim_id='cyc', kind='sealed_generation_evaluation', candidate=v[i + 1], seed=i,
                   transition={'index': i + 1, 'from_version': v[i], 'to_version': v[i + 1]},
                   baseline_program=progs[i], candidate_program=progs[i + 1]) for i in range(3)]
with Store(Path(tempfile.mkdtemp()) / 's') as s:
    k = EvidenceKernel.with_fixture_registry(s, fx.registry)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash='c' * 64, verdict='VALID')
    nodes = [record_evaluation(k, fx, r, [run])[1] for r in reqs]
    k.create_claim('cyc', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes, binding=R.binding_from_requests(reqs))
    k.promote('cyc', 'improver', 'MULTIGEN_CONFIRMED')
    print('distinct real programs in the lineage:', len({prog(p) for p in progs}),
          '| kernel levels:', k.levels('cyc')['improver'])
    ok = k.levels('cyc')['improver'] == 'MULTIGEN_CONFIRMED'
print('ATTACK_SUCCEEDED (logic only)' if ok and same else 'ATTACK_BLOCKED')
