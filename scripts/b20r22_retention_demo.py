#!/usr/bin/env python3
"""B20_R22 (H08 s20.6): retention and negative transfer measured on a real DEV campaign lineage.

    b20r22_retention_demo.py OUT_DIR

Fixed before running:
  * campaign: c4_host_v2, seed 20262301, 4 generations, 4 tasks per panel, 2 proposals per epoch,
    8 research trials (a small DEV configuration);
  * the retention protocol is frozen in the campaign store BEFORE the campaign runs, with PROTECTED
    material in OUT_DIR/private (0700): legacy = 8 c4 erdos n12 p0.4 + 8 c4 bipartite n12 p0.5 hosts
    (DEV, seeds 20262311/20262312); transfer = 8 triangle-free erdos n12 p0.45 hosts (DEV, seed
    20262313); margin 0.5, level 0.9, 2000 resamples, the campaign's limits; budget = 5;
  * measured after the run: every forward step of the active-version pointer (versions.py), then the
    initial version against the final active version (cumulative legacy retention), within budget;
  * verdicts are the protocol's (RETAINED / NEGATIVE_TRANSFER / INCONCLUSIVE). A demonstration on DEV
    material: it licenses no claim and moves no pointer.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import retention as RT  # noqa: E402
from genesis import versions as VS  # noqa: E402
from genesis.campaign import Campaign  # noqa: E402
from genesis.common import code_identity  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import Config  # noqa: E402


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    c4, tf = ADAPTERS['c4_host_v2'], ADAPTERS['triangle_free_host_v1']
    legacy, seen, _ = c4.generate(20262311, 8, 'DEV', 'erdos', {'n': 12, 'p': 0.4})
    legacy2, _, _ = c4.generate(20262312, 8, 'DEV', 'bipartite', {'n': 12, 'p': 0.5}, excluded=seen)
    transfer, _, _ = tf.generate(20262313, 8, 'DEV', 'erdos', {'n': 12, 'p': 0.45})
    root = out / 'campaign'
    cfg = Config(domain='c4_host_v2', seed=20262301, generations=4, tasks_per_panel=4, proposals_per_epoch=2,
                 research_trials=8)
    Campaign.initialize(root, cfg)
    with Campaign(root) as c:
        proto = RT.freeze(c.store, {'legacy': legacy + legacy2, 'transfer': transfer}, limits=cfg.limits, budget=5,
                          material='PROTECTED', private_root=out / 'private')
        log(f'protocol frozen before the run: {json.dumps({k: v["tasks"] for k, v in proto["panels"].items()})}')
        summary = c.run()
        hist = VS.pointer_history(c.store)
        log(f'campaign: {len(summary["generations"])} generations, pointer {[r["kind"] for r in hist]}')
        steps = [(r['previous'], r['version']) for r in hist if r['kind'] == 'ACTIVATE' and r['previous']]
        pairs = steps + ([(hist[0]['version'], hist[-1]['version'])] if len(steps) > 1 else [])
        results = []
        for a, b in pairs[:proto['budget']]:
            m = RT.measure(c.store, a, b, private_root=out / 'private')
            results.append({'from': a, 'to': b, 'verdict': m['verdict'],
                            'panels': {k: {x: v[x] for x in ('mean', 'interval', 'verdict', 'wins_ties_losses')}
                                       for k, v in m['panels'].items()}})
            log(f'{a[:10]} -> {b[:10]}: {m["verdict"]} {json.dumps(results[-1]["panels"])}')
        status = VS.status(c.store)
    summary_out = {'schema': 'genesis-b20r22-retention-demo-v1', 'protocol_sha256': __import__('genesis.common', fromlist=['digest']).digest(proto),
                   'protocol': {k: v for k, v in proto.items() if k != 'panels'},
                   'panels': {k: v['tasks'] for k, v in proto['panels'].items()},
                   'pointer': [{k: r[k] for k in ('seq', 'kind', 'version', 'previous', 'reason')} for r in hist],
                   'measurements': results, 'version_status': status,
                   'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV demonstration; licenses no claim'}
    (out / 'summary.json').write_text(json.dumps(summary_out, indent=1, sort_keys=True) + '\n')
    log('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
