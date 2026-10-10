#!/usr/bin/env python3
"""F1: verify_bundle accepts a CLAIMS.json that asserts unsupported levels (R-02).

_compare_claims only compares a dict {claim_id: effective_levels} (last entry
wins), the claim-id set and the revocation head. Everything else a reader sees
is unchecked: a duplicate entry for the same claim, `ceiling`, `statement`,
`scope`, `historical`, `invalidated_by`; report.md is never linted against the
recomputed ceiling; MANIFEST.source_hash is never compared with the store; the
certificates/ files are never compared with the rebuilt evidence graph.
Run: PYTHONPATH=src python3 -W ignore audit/redteam_b14/f1_claims_json_unchecked_fields.py
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import REPO, bundle_file, rewrite_bundle  # noqa: E402

from genesis.common import canonical, code_identity  # noqa: E402
from genesis.kernel.evidence import AXES, EvidenceKernel  # noqa: E402
from genesis.kernel.wording import lint  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

TOP = {axis: levels[-1] for axis, levels in AXES.items()}
REPORT = ('The solver is confirmed and statistically significant, transfers to new domains, is a novel discovery, '
          'was independently reproduced, is recursively self-improving, and is proved optimal.')

with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = d / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', 'f' * 64)           # campaign NOT produced by the shipped code
        k = EvidenceKernel(s)
        run = k.record('execution_receipt', {'run': 1}, route='genesis.campaign', source_hash='a' * 64, verdict='VALID')
        chk = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash='a' * 64,
                       verdict='VALID', verifier='dual-predicates')
        k.create_claim('w', 'host H has a C4-free subgraph with 7 edges', 'host H', [chk])
        k.promote('w', 'math', 'WITNESS_VALID')
    honest = d / 'honest.zip'
    build_bundle(root, honest)
    print('honest bundle verify:', verify_bundle(honest)['ok'], verify_bundle(honest)['problems'])

    def lie(files, manifest):
        c = json.loads(files['CLAIMS.json'])
        real = c['claims'][0]
        fake = json.loads(json.dumps(real))
        fake['effective_levels'] = dict(TOP)                       # every axis at its top level
        fake['statement'] = 'Our solver beats every known solver on every graph family'
        fake['historical']['recorded_levels'] = dict(TOP)
        real['statement'] = 'Our solver is optimal on every host'   # honest entry's text rewritten too
        real['invalidated_by'] = []
        c['claims'] = [fake, real]                                 # duplicate claim_id; last one is compared
        c['ceiling'] = dict(TOP)
        files['CLAIMS.json'] = canonical(c)
        files['report.md'] = REPORT.encode()
        manifest['source_hash'] = manifest['shipped_code_identity']  # hide the source mismatch
        for name in [n for n in files if n.startswith('certificates/')]:
            cert = json.loads(files[name]); cert['payload']['value'] = 999
            files[name] = canonical(cert)

    lying = d / 'lying.zip'
    rewrite_bundle(honest, lying, lie)
    result = verify_bundle(lying)
    claims = json.loads(bundle_file(lying, 'CLAIMS.json'))
    print('lying bundle verify ok:', result['ok'], 'problems:', result['problems'])
    print('first CLAIMS.json entry for "w":', claims['claims'][0]['statement'], claims['claims'][0]['effective_levels'])
    print('bundled ceiling:', claims['ceiling'])
    print('report.md lint against bundled ceiling:', lint(REPORT, claims['ceiling']))
    print('report.md lint against real ceiling   :', len(lint(REPORT, {'math': 'WITNESS_VALID'})), 'violations')
    print('certificates/*.json value now:', [json.loads(bundle_file(lying, n))['payload']['value']
                                             for n in ['certificates/' + chk + '.json']])
    print('ATTACK_SUCCEEDED' if result['ok'] else 'ATTACK_BLOCKED')
