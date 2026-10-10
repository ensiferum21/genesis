#!/usr/bin/env python3
"""R6 (F11 bypass): the one-registration-per-slot rule is keyed by claim_id, which the
requester chooses freely, so the same statement, scope, candidate and campaign can
be preregistered again under a new claim_id after a failed evaluation; only the
successful one is cited and exported.

The slot is digest(claim_id, kind, domain, transfer source, generation index). It
does not include statement_hash, candidate or campaign, and the custodian keeps no
public per-campaign registration list that a bundle must account for. The real
register() and evaluate() run for both attempts. (Attempt 1 uses 4 tasks, which
cannot reach alpha, to force a failure deterministically; the same works with an
identical design and a lucky panel.)
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r6_reregister_under_new_claim_id.py
"""
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from r7_transfer_label_without_transfer import pool  # noqa: E402
from genesis.common import bytes_hash, canonical, code_identity, digest  # noqa: E402


def parent():
    from genesis.custodian import evaluate, register
    base, keys, trust, work = _r2.production_setup()
    private = base / 'private'; private.mkdir(mode=0o700)
    manifest = private / 'manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []})); manifest.chmod(0o600)
    export = base / 'export.zip'
    with zipfile.ZipFile(export, 'w') as z:
        z.writestr('MANIFEST.json', canonical({'files': {}, 'scope': 'public offline campaign'}))
    ident = code_identity(_r2.REPO)['sha256']
    common = dict(source=ident, evaluator=ident, export_sha=bytes_hash(export.read_bytes()))
    out = {}
    for name, claim_id, n, seed in (('first', 'claim-1', 4, 11), ('retry', 'claim-1', 12, 12),
                                    ('renamed', 'claim-1 (v2)', 12, 13)):
        req = _r2.request(claim_id=claim_id, task_count=n, seed=seed, **common)
        pool_path = base / f'pool-{name}.json'
        pool_path.write_bytes(canonical([t.model_dump(mode='json') for t in pool(n, seed)]))
        try:
            anchor = register(private, req, keys['prereg'][0], 'custodian-op', exposure_manifest=manifest,
                              campaign_export=export, pool=pool_path)
        except ValueError as e:
            print(f'{name:8} register({claim_id!r}): REFUSED ({str(e)[:60]}...)')
            continue
        receipt = evaluate(private, digest(req), pool_path, keys['custodian'][0], 'custodian-op')
        print(f'{name:8} register({claim_id!r}): accepted -> evaluate: {receipt["payload"]["outcome"]}'
              f' | statement/scope/candidate/campaign identical to the first: '
              f'{all(req[k] == out.get("first", {"request": req})["request"][k] for k in ("statement_hash", "scope", "candidate_version", "campaign_id"))}')
        out[name] = {'request': req, 'anchor': anchor, 'receipt': receipt}
    _r2.run_research(__file__, trust, work, {'good': out['renamed']})


def child(trust, work):
    from genesis.kernel import receipts as R
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())['good']
    root = work / 'campaign'
    with Store(root) as s:
        s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                            source_hash=e['request']['source_hash'])
        r = k.record_signed('sealed_evaluation', e['receipt'], parents=[a], route='genesis.custodian.evaluate',
                            source_hash=e['request']['source_hash'])
        k.create_claim('claim-1 (v2)', _r2.STATEMENT, _r2.SCOPE, [r], binding=R.binding_from_requests([e['request']]))
        k.promote('claim-1 (v2)', 'utility', 'CONFIRMED_SAME_DOMAIN')
    build_bundle(root, work / 'release.zip', trust_root=trust)
    claims = json.loads(_r2.bundle_file(work / 'release.zip', 'CLAIMS.json'))['claims']
    v = verify_bundle(work / 'release.zip', trust_root=trust)
    print('exported claims:', [(c['claim_id'], c['effective_levels']['utility']) for c in claims],
          '| verify ok:', v['ok'], v['problems'])
    print('ATTACK_SUCCEEDED' if v['ok'] and claims[0]['effective_levels']['utility'] == 'CONFIRMED_SAME_DOMAIN'
          else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
