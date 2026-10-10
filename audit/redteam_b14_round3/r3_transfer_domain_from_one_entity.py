#!/usr/bin/env python3
"""R3: CONFIRMED_TRANSFER c4 -> triangle-free for a candidate that was developed ONLY on
triangle-free hosts (the C1 consequence, reached again through campaign_facts).

custodian.campaign_facts() takes the campaign domain from the first `config`
entity of the export and nothing else. Campaign.run() takes its domain from the
mutable file resolved_config.json, which is never compared with that entity.
Here a REAL campaign is initialised as c4_host_v2, resolved_config.json is then
edited to triangle_free_host_v1 and the real Campaign.run() performs all DEV and
SELECT research on triangle-free hosts. The export's own history says so
(every DEV/SELECT task entity, every system_version.resolved_config), but the
custodian reads `config` = c4_host_v2, accepts a transfer request
"source c4_host_v2 -> target triangle_free_host_v1", evaluates on a sealed
triangle-free panel (the domain the candidate was tuned on) and signs SUPPORTED;
the kernel licenses CONFIRMED_TRANSFER and verify_bundle (trust root) accepts.
  PYTHONPATH=src:. GENESIS_TOOLCHAIN=/home/claude/toolchain python3 -W ignore \
      audit/redteam_b14_round3/r3_transfer_domain_from_one_entity.py
"""
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r3  # noqa: E402
from genesis.common import bytes_hash, canonical, digest  # noqa: E402
from genesis.kernel import receipts as R  # noqa: E402
from genesis.models import Config, GraphTask, SolverProgram  # noqa: E402

STATEMENT = ('the frozen candidate developed on c4_host_v2 transfers to triangle_free_host_v1: higher paired edge '
             'count than the baseline on the sealed triangle-free panel')
SCOPE = 'triangle_free_host_v1 sealed panel of 24 tasks'
CLAIM = 'transfer:c4-to-triangle'


def parent():
    from genesis.campaign import Campaign
    from genesis.cli import export_replication
    from genesis.custodian import campaign_facts, evaluate, register
    from genesis.exposure import campaign_hosts
    from genesis.graphs import canonical_graph
    from genesis.store import Store
    base, keys, trust, work = _r3.production_setup()
    private, manifest = _r3.custodian_dirs(base)
    root = work / 'campaign'
    cfg = Config(domain='c4_host_v2', generations=1, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8)
    Campaign.initialize(root, cfg)
    edited = cfg.model_copy(update={'domain': 'triangle_free_host_v1'})
    (root / 'resolved_config.json').write_bytes(canonical(edited.model_dump(mode='json')))
    with Campaign(root) as c:
        c.run()
        s = c.store
        tasks = Counter((s.get(h)['domain'], s.get(h)['split'])
                        for _, h in s.db.execute("SELECT id, object_hash FROM entities WHERE kind='task'"))
        cid, source, program = s.state('campaign_id'), s.state('source_hash'), s.state('latest_program')
        print('real Campaign.run(): phase', s.state('phase'), '| task entities by (domain, split):', dict(tasks))
    export = root / 'exports' / 'campaign_export.zip'
    export_replication(root, export)
    facts = campaign_facts(export)
    print('custodian campaign_facts domain:', facts['domain'])
    declared = sorted({canonical_graph(GraphTask(task_id='x', n=k, edges=es, family='x'))
                       for k, es in campaign_hosts(export)})
    req = _r3._r2.request(claim_id=CLAIM, kind='sealed_transfer_evaluation', campaign=cid, domain='triangle_free_host_v1',
                          transfer='c4_host_v2', candidate=digest({'program': program, 'source': source}),
                          cand_program=program, baseline=SolverProgram(rounds=1).model_dump(mode='json'),
                          task_count=24, statement=STATEMENT, scope=SCOPE, source=source, evaluator=_r3.IDENT,
                          export_sha=bytes_hash(export.read_bytes()))
    req['exposed_graph_fingerprints'] = declared
    pool = _r3.write_pool(base / 'pool.json', _r3.pool(21, domain='triangle_free_host_v1'))
    anchor = register(private, req, keys['prereg'][0], 'custodian-op', exposure_manifest=manifest,
                      campaign_export=export, pool=pool)
    print('register: accepted transfer', req['transfer_source_domain'], '->', req['domain'])
    receipt = evaluate(private, digest(req), pool, keys['custodian'][0], 'custodian-op')
    p = receipt['payload']
    print(f'evaluate: {p["outcome"]} wins={p["wins"]} losses={p["losses"]} ties={p["ties"]} family_p={p["family_p"]:.4f}')
    _r3.chown_tree(root)
    _r3.run_research(__file__, trust, work, {'request': req, 'anchor': anchor, 'receipt': receipt})


def child(trust, work):
    from genesis.kernel.evidence import EvidenceKernel
    from genesis.release_bundle import build_bundle, verify_bundle
    from genesis.store import Store
    e = json.loads((work / 'inputs.json').read_bytes())
    root = work / 'campaign'
    with Store(root) as s:
        k = EvidenceKernel(s, trust_root=trust)
        a = k.record_signed('preregistration_anchor', e['anchor'], route='genesis.custodian.evaluate',
                            source_hash=e['request']['source_hash'])
        r = k.record_signed('sealed_transfer_evaluation', e['receipt'], parents=[a],
                            route='genesis.custodian.evaluate', source_hash=e['request']['source_hash'])
        k.create_claim(CLAIM, STATEMENT, SCOPE, [r], binding=R.binding_from_requests([e['request']]))
        d = k.promote(CLAIM, 'utility', 'CONFIRMED_TRANSFER')
        print('child (uid 65534, real trust root): promoted', d['level'])
    build_bundle(root, work / 'release.zip', trust_root=trust,
                 report='The candidate transfers from c4_host_v2 to triangle_free_host_v1.')
    level = json.loads(_r3.bundle_file(work / 'release.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['utility']
    v = verify_bundle(work / 'release.zip', trust_root=trust)
    print('exported:', level, '| verify_bundle ok:', v['ok'], v['problems'][:3])
    print('ATTACK_SUCCEEDED' if v['ok'] and level == 'CONFIRMED_TRANSFER' else 'ATTACK_BLOCKED')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parent()
