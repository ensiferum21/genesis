#!/usr/bin/env python3
"""F6: build_index and CLAIMS.json history carry stale or forged levels; phase is plain mutable state.

(a) kernel/index.py fills the `evidence` table (claim, artifact, axis, status)
    from every stored `promotion` entity, never re-derived: a revoked claim keeps
    status WITNESS_VALID there while the `claims` table says UNCHECKED.
(b) promotion_history() accepts any `promotion` entity, so a record saved with
    Store.save (never passing promote()) appears in the index as
    CONFIRMED_TRANSFER and in CLAIMS.json historical.recorded_levels; verify_bundle
    accepts it.
(c) phases.advance is bypassed by Store.set_state('phase', 'RELEASED'); the index
    `campaigns.status` reports RELEASED with no signed release decision.
Run: PYTHONPATH=src python3 -W ignore audit/redteam_b14/f6_index_and_history_stale.py
"""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file  # noqa: E402

from genesis.common import code_identity, utcnow  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.kernel.index import build_index  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

SRC = 'a' * 64
with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = d / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(REPO)['sha256'])
        s.set_state('campaign_id', 'campaign-1')
        k = EvidenceKernel(s)
        run = k.record('execution_receipt', {'run': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
        chk = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash=SRC,
                       verdict='VALID', verifier='dual-predicates')
        k.create_claim('revoked', 'value 7 witnessed', 'host H', [chk])
        k.promote('revoked', 'math', 'WITNESS_VALID')
        k.revoke(chk, 'checker receipt found faulty', 'auditor')
        k.create_claim('forged', 'the solver transfers to triangle-free hosts', 'all hosts', [run])
        s.save('promotion', 'f' * 64, {'claim': 'forged', 'axis': 'utility', 'level': 'CONFIRMED_TRANSFER',
                                       'dependencies': [run], 'evidence_used': [], 'evaluations': [],
                                       'registry': 'external-board', 'at': utcnow()})
        s.set_state('phase', 'RELEASED')   # no phases.advance, no signature
        print('kernel levels:', {c: k.levels(c)['math' if c == 'revoked' else 'utility'] for c in ('revoked', 'forged')})
        build_index(s, d / 'index.sqlite3')
    db = sqlite3.connect(d / 'index.sqlite3')
    print('index claims  :', {c: (json.loads(v)['math'], json.loads(v)['utility']) for c, v in
                               db.execute('SELECT claim_id, current_levels FROM claims')})
    print('index evidence:', db.execute('SELECT claim_id, axis, status FROM evidence').fetchall())
    print('index campaigns:', db.execute('SELECT campaign_id, status FROM campaigns').fetchall())
    build_bundle(root, d / 'release.zip')
    c = {x['claim_id']: x for x in json.loads(bundle_file(d / 'release.zip', 'CLAIMS.json'))['claims']}
    print('CLAIMS.json forged historical:', c['forged']['historical']['recorded_levels']['utility'],
          c['forged']['historical']['promotions'])
    r = verify_bundle(d / 'release.zip')
    print('verify ok:', r['ok'], r['problems'])
