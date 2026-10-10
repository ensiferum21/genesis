#!/usr/bin/env python3
"""R8: the wording gate (kernel/wording.py) misses ordinary overclaim phrasings, so a
release whose every claim is at the floor ships a report and claim statements that
assert optimality, confirmation, transfer, causation, novelty and self-improvement,
and verify_bundle accepts it. (Round-2 M2 fixed encoding/idiom bypasses; these are
plain-English variants the patterns never cover.)
  PYTHONPATH=src:. python3 -W ignore audit/redteam_b14_round3/r8_wording_gate_vocabulary.py
"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.kernel.evidence import FLOOR, EvidenceKernel  # noqa: E402
from genesis.kernel.wording import lint  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

PHRASES = [
    'This is an optimal solver.',                                 # "is an optimal"
    'The construction is provably optimal.',                      # adverb between
    'We found the optimum and the maximum for every host.',       # optimum / maximum
    'Its gains transferred to triangle-free hosts.',              # transferred
    'The result is generalizable and verified on sealed data.',   # generalizable / verified
    'The sealed evaluation confirms a real improvement.',         # confirms
    'The exchange step drives the improvement.',                  # causal verb
    'This is a previously unknown result, the first ever of its kind.',  # novelty
    'The system improves itself across generations.',             # self-improvement
    'Independently reproduced by a second lab.',                  # replication (adverb form ok? see output)
]


def main():
    for p in PHRASES:
        print(f'{"CAUGHT " if lint(p, FLOOR) else "MISSED "} {p}')
    tmp = Path(tempfile.mkdtemp(prefix='r3-r8-'))
    with Store(tmp / 'c') as s:
        s.set_state('campaign_id', 'c' * 64); s.set_state('source_hash', _r3.IDENT)
        k = EvidenceKernel(s)
        run = k.record('execution_receipt', {'note': 'nothing'}, route='genesis.campaign', source_hash=_r3.IDENT)
        k.create_claim('c1', 'The candidate is an optimal solver whose gains transferred to every domain; '
                             'the sealed evaluation confirms it.', 'all hosts', [run])
        print('claim levels:', {a: l for a, l in k.levels('c1').items() if l != FLOOR[a]} or 'all at floor')
    missed = [p for p in PHRASES if not lint(p, FLOOR)]
    build_bundle(tmp / 'c', tmp / 'b.zip', report=' '.join(missed))
    v = verify_bundle(tmp / 'b.zip')
    print('verify_bundle ok:', v['ok'], v['problems'][:2])
    print('ATTACK_SUCCEEDED' if v['ok'] and missed else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    main()
