#!/usr/bin/env python3
"""Deterministic reference computations for second-machine reproduction (R-04).

  reference_run.py WORK_DIR [--write-expected]

Runs a fixed set of computations whose outputs must be identical on every
supported host, prints them as JSON, and compares them with
deployment/EXPECTED_RESULTS.json (exit 1 on any difference). Timing,
paths and host names are excluded by construction.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'src'))

from genesis.common import digest  # noqa: E402

EXPECTED = HERE / 'EXPECTED_RESULTS.json'
DETERMINISTIC = ('selected_policy', 'baseline', 'solver_comparison', 'better_improver_diagnostic',
                 'causal_controls', 'transfer', 'retained_in_dev')


def campaign(work):
    from genesis.backup import backup, restore
    from genesis.campaign import Campaign
    from genesis.models import Config
    root = work / 'reference-campaign'
    Campaign.initialize(root, Config(seed=20261010, generations=2, tasks_per_panel=3, proposals_per_epoch=2,
                                     research_trials=8))
    with Campaign(root) as c:
        summary = c.run()
        program = c.store.state('latest_program')
        replay = c.replay(limit=5)
    restored = restore(backup(root, work / 'reference-backup.zip')['backup'], work / 'reference-restored')
    with Campaign(work / 'reference-restored') as r:
        same = r.store.state('summary') == summary
    generations = [{k: g[k] for k in DETERMINISTIC} for g in summary['generations']]
    return {'generations_sha256': digest(generations), 'latest_program': program,
            'total_attempts': summary['total_attempts'], 'replay_all_matched': replay['all_matched'],
            'backup_restore_same_summary': same, 'restored_events': restored['events']}


def certificate():
    from genesis.research import make_panel
    from genesis.verification.certificates import build, checker_only, replay
    from genesis.verification.sat import certified_bounds
    task = make_panel(4242, 1, 'c4_host_v2', 'DEV', set(), 18)[0][0]
    bounds = certified_bounds(task, seconds=60)
    bundle, blobs = build(task, bounds)
    with checker_only():                        # the producer (CaDiCaL) cannot run during replay
        replayed = replay(bundle, blobs.__getitem__)
    return {'task_sha256': digest(task.model_dump(mode='json')), 'status': bounds['status'],
            'lower': bounds['lower'], 'upper': bounds['upper'], 'method': bundle['upper']['method'],
            'cnf_sha256': bundle['upper'].get('cnf_sha256'), 'replay': replayed['status'],
            'replay_problems': replayed['problems']}


def lean():
    from genesis.models import GraphTask
    from genesis.verification.lean import check_witness_formally
    task = GraphTask(task_id='reference', family='reference', domain='c4_host_v2', n=4,
                     edges=((0, 1), (0, 3), (1, 2), (2, 3)), split='DEV')
    r = check_witness_formally(task, [[0, 1], [1, 2], [2, 3]])
    return {'status': r['status'], 'axioms': r.get('axioms')}


def known_answers():
    sys.path.insert(0, str(HERE.parent / 'toolchain'))
    from known_answers import known_answers as ka
    from genesis.verification.tools import toolchain_root
    r = ka(toolchain_root())
    return {'ok': r['ok'], 'cases': {c['case']: c['pass'] for c in r['cases']}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('work', type=Path)
    ap.add_argument('--write-expected', action='store_true')
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=False)
    results = {'schema': 'genesis-reference-results-v1', 'campaign': campaign(a.work), 'certificate': certificate(),
               'lean': lean(), 'known_answers': known_answers()}
    if a.write_expected:
        EXPECTED.write_text(json.dumps(results, indent=1, sort_keys=True) + '\n')
    expected = json.loads(EXPECTED.read_text())
    differences = sorted(f'{section}.{key}' for section in expected if isinstance(expected[section], dict)
                         for key in set(expected[section]) | set(results.get(section, {}))
                         if expected[section].get(key) != results.get(section, {}).get(key))
    print(json.dumps({'results': results, 'differences': differences, 'match': not differences}, sort_keys=True))
    return 0 if not differences else 1


if __name__ == '__main__':
    sys.exit(main())
