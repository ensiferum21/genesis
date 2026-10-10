#!/usr/bin/env python3
"""R1b (kernel side of R1): one claim is CONFIRMED_SAME_DOMAIN on program P1 and
EXTERNAL_REPRODUCTION on a different program P2, because the claim binding and
binding_mismatches() identify the candidate only by the free `candidate_version`
label (baselines are bound by program identity, candidates are not), and
binding_from_requests() accepts requests that evaluate different candidate
programs under one label.

In-process with the fixture registry (documented test seam; fixture keys).
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r1b_reproduction_of_another_program.py
"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from genesis.kernel import receipts as R  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402
from genesis.store import Store  # noqa: E402
from tests_genesis.signed_fixtures import SignedFixture, record_evaluation  # noqa: E402

P1 = SolverProgram(rounds=32, exchange=True).model_dump(mode='json')
P2 = SolverProgram(weights=(0, 0, 0, -8), rounds=2).model_dump(mode='json')


def main():
    d = Path(tempfile.mkdtemp(prefix='r3-r1b-'))
    fx = SignedFixture(d)
    sealed = fx.request(candidate_program=P1, seed=1)
    repro = fx.request(kind='external_reproduction', candidate_program=P2, seed=2)   # same claim, same label
    with Store(d / 's') as s:
        s.set_state('campaign_id', 'a' * 64); s.set_state('source_hash', 'c' * 64)
        k = EvidenceKernel.with_fixture_registry(s, fx.registry)
        _, n1 = record_evaluation(k, fx, sealed)
        a2 = fx.anchor(repro)
        _, n2 = record_evaluation(k, fx, repro, anchor=a2, receipt=fx.receipt(repro, a2, role='replicator'))
        k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [n1, n2],
                       binding=R.binding_from_requests([sealed, repro]))
        k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        k.promote('claim-1', 'replication', 'EXTERNAL_REPRODUCTION')
        lv = k.levels('claim-1')
        print('levels:', lv['utility'], lv['replication'])
        print('sealed evaluation candidate program', R.program_identity(P1)[:12],
              '| reproduction candidate program', R.program_identity(P2)[:12],
              '| both under candidate_version', sealed['candidate_version'][:12])
    ok = lv['utility'] == 'CONFIRMED_SAME_DOMAIN' and lv['replication'] == 'EXTERNAL_REPRODUCTION'
    print('ATTACK_SUCCEEDED' if ok else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    main()
