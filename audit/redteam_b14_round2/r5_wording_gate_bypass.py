#!/usr/bin/env python3
"""R5: the export wording gate (report.md, claim statements, scopes) is bypassed with plain prose.

kernel.wording.lint suppresses a match when any NEGATIONS word ("no", "not",
"without", "zero", "needs", "until", ...) occurs 60 chars before or 25 after it,
strips `code spans`, "[cited: ...]" and UPPER_SNAKE tokens, and matches ASCII
words only (a zero-width space or soft hyphen inside "optimal" renders the same).
build_bundle refuses overclaiming text and verify_bundle re-lints it (F1/F8
repairs); both accept the texts below for a claim whose only level is WITNESS_VALID.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r5_wording_gate_bypass.py
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import code_identity  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.kernel.wording import lint  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

LEVELS = {'math': 'WITNESS_VALID', 'utility': 'NOT_TESTED', 'causality': 'NOT_TESTED', 'improver': 'NOT_TESTED',
          'novelty': 'UNKNOWN', 'replication': 'NONE'}
REPORT = '\n'.join([
    'Not surprisingly, this construction is optimal.',
    'The result was replicated, no doubt.',
    'There is no doubt this is a novel discovery.',
    'Zero caveats: the modification causes the gain.',
    'Not only that: the solver generalises to every family.',
    'It needs saying: we have proved the theorem, and the result is statistically significant.',
    'The construction is opti​mal.',                                     # zero-width space
    'The solver is recursively self-impro­ving.',                       # soft hyphen
    '`Our solver is optimal, replicated and confirmed.`',
    '[cited: our solver generalises to all domains and is a new discovery]',
])
STATEMENT = 'Its witness is optimal, no question, and the candidate generalises to every family, no doubt.'
SCOPE = 'all hosts [cited: transfers to every domain]'
print('control (plain overclaim) lint:', [p['phrase'] for p in lint('This construction is optimal and replicated.', LEVELS)])
for line in REPORT.splitlines() + [STATEMENT, SCOPE]:
    print(f'  lint={lint(line, LEVELS)!s:4} {line!r}'[:150])

d = Path(tempfile.mkdtemp())
with Store(d / 'c') as s:
    s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
    k = EvidenceKernel(s)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash='c' * 64, verdict='VALID')
    w = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash='c' * 64,
                 verdict='VALID', verifier='dual-predicates')
    k.create_claim('w', STATEMENT, SCOPE, [w])
    k.promote('w', 'math', 'WITNESS_VALID')
build_bundle(d / 'c', d / 'b.zip', report=REPORT)
r = verify_bundle(d / 'b.zip')
c = json.loads(_r2.bundle_file(d / 'b.zip', 'CLAIMS.json'))
print('build_bundle accepted; ceiling:', {a: v for a, v in c['ceiling'].items() if v != LEVELS[a] or a == 'math'})
print('verify ok:', r['ok'], r['problems'])


def unlinted(files, manifest):  # LIMITATIONS.md and REPRODUCE.md are never linted or re-derived
    files['LIMITATIONS.md'] += b'\nThis construction is optimal; we proved the theorem and the result was replicated.\n'
    files['REPRODUCE.md'] = b'# Reproduce\n\nThe result is confirmed and statistically significant; just run ./verify.sh\n'


_r2.rewrite_bundle(d / 'b.zip', d / 'b2.zip', unlinted)
r2 = verify_bundle(d / 'b2.zip')
print('plain overclaims in LIMITATIONS.md / REPRODUCE.md: verify ok:', r2['ok'], r2['problems'])
print('ATTACK_SUCCEEDED' if r['ok'] and r2['ok'] else 'ATTACK_BLOCKED')
