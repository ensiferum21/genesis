#!/usr/bin/env python3
"""R7 (B14-OPEN-1 made concrete): CONFIRMED_TRANSFER for a candidate that never saw the
declared source domain, through the REAL custodian register() and evaluate().

The custodian checks only that the request's campaign_export_sha256 matches the
zip it is handed. It never checks the request's campaign_id, source_hash or
transfer_source_domain against that export. A sealed_transfer_evaluation is run
exactly like a same-domain evaluation (pool in `domain`), so declaring
transfer_source_domain='triangle_free_host_v1' turns an ordinary c4 result into
CONFIRMED_TRANSFER, which in turn licenses "transfers"/"generalises" wording.
Here the campaign export is an empty zip, campaign_id is arbitrary, and the
request's source_hash names a tree the campaign never ran; the exporting store's
campaign_id and source_hash (== MANIFEST source == shipped code identity) differ
from the receipt's, and neither the kernel nor verify_bundle compares them, so a
campaign produced by a revoked source can carry confirmations whose receipts
name a clean source (by code reading; a revoked identity cannot be forged here).

Production trust path (root custodian, UID 65534 research child). The panel is a
fresh random c4 panel; the candidate genuinely beats the baseline on it.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r7_transfer_label_without_transfer.py
"""
from itertools import combinations
import json
from pathlib import Path
import random
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import bytes_hash, canonical, code_identity, digest  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

STATEMENT = ('the candidate developed on triangle_free_host_v1 transfers to c4_host_v2: higher paired edge count '
             'than the baseline on the sealed c4 panel')
SCOPE = 'c4_host_v2 sealed panel'


def pool(count=12, seed=1):
    rng = random.Random(seed); out = []
    while len(out) < count:
        edges = tuple(e for e in combinations(range(11), 2) if rng.random() < 0.35)
        if 16 <= len(edges) <= 22:
            out.append(GraphTask(task_id=f'p{len(out)}', n=11, edges=edges, family=f'fam{len(out)}', split='CONFIRM'))
    return out


def parent():
    from genesis.custodian import evaluate, register
    base, keys, trust, work = _r2.production_setup()
    private = base / 'private'; private.mkdir(mode=0o700)
    manifest = private / 'manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []})); manifest.chmod(0o600)
    export = base / 'unrelated_export.zip'
    with zipfile.ZipFile(export, 'w') as z:          # no hosts, no domain, nothing from any campaign
        z.writestr('MANIFEST.json', canonical({'files': {}, 'scope': 'public offline campaign'}))
    ident = code_identity(_r2.REPO)['sha256']
    req = _r2.request(claim_id='transfer-1', kind='sealed_transfer_evaluation', transfer='triangle_free_host_v1',
                      campaign='0123456789abcdef' * 4, task_count=12, statement=STATEMENT, scope=SCOPE,
                      source=digest('a source tree this campaign never ran'), evaluator=ident,
                      export_sha=bytes_hash(export.read_bytes()))
    pool_path = base / 'pool.json'
    pool_path.write_bytes(canonical([t.model_dump(mode='json') for t in pool()]))
    anchor = register(private, req, keys['prereg'][0], 'custodian-op', exposure_manifest=manifest,
                      campaign_export=export, pool=pool_path)
    print('custodian.register accepted: kind', req['evidence_kind'], '| domain', req['domain'],
          '| declared source', req['transfer_source_domain'], '| export hosts: 0')
    receipt = evaluate(private, digest(req), pool_path, keys['custodian'][0], 'custodian-op')
    p = receipt['payload']
    print('custodian.evaluate signed:', p['outcome'], f"wins={p['wins']} losses={p['losses']} ties={p['ties']}",
          '| panel domain', p['domain'], '| tasks in source domain: 0')
    _r2.run_research(__file__, trust, work, {'request': req, 'anchor': anchor, 'receipt': receipt})


def child(trust, work):
    from genesis.kernel import receipts as R
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())
    root = work / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
        s.set_state('campaign_id', 'some-other-campaign')
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                            source_hash=e['request']['source_hash'])
        r = k.record_signed('sealed_transfer_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                            source_hash=e['request']['source_hash'])
        k.create_claim('transfer-1', STATEMENT, SCOPE, [r], binding=R.binding_from_requests([e['request']]))
        d = k.promote('transfer-1', 'utility', 'CONFIRMED_TRANSFER')
        print('promoted', d['level'], 'registry', d['registry'][:12], '| levels:', k.levels('transfer-1')['utility'])
        print('store campaign_id', s.state('campaign_id'), 'vs receipt', e['receipt']['payload']['campaign_id'][:16],
              '| store source_hash', s.state('source_hash')[:12], 'vs receipt source_hash',
              e['receipt']['payload']['source_hash'][:12])
    build_bundle(root, work / 'release.zip', trust_root=trust,
                 report='The candidate transfers across domains and generalises beyond its development domain.')
    level = json.loads(_r2.bundle_file(work / 'release.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['utility']
    v = verify_bundle(work / 'release.zip', trust_root=trust)
    print('exported:', level, '| verify ok:', v['ok'], v['problems'])
    print('ATTACK_SUCCEEDED' if v['ok'] and level == 'CONFIRMED_TRANSFER' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
