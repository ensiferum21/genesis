#!/usr/bin/env python3
"""Spec §40 end-to-end walkthrough with real components.

Steps 1-10 run the research side for real (public DEV). Steps 11-13 run the
evaluator side with FIXTURE roles: keys generated here, a trust root owned by
root, and the research-side phase changes executed by a child process dropped
to UID 65534. This demonstrates the protocol mechanics only; it is not
independent custody. Step 14 (release) requires an external release authority
and is deliberately NOT performed. Must run as root (for the UID drop).
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

from genesis.campaign import Campaign  # noqa: E402
from genesis.cli import request_bundle  # noqa: E402
from genesis.common import canonical, digest, load_json  # noqa: E402
from genesis.custodian import evaluate, register, release_preflight  # noqa: E402
from genesis.kernel.signing import sign  # noqa: E402
from genesis.kernel.wording import require_clean  # noqa: E402
from genesis.macros import cognitive_compile, gap_engine  # noqa: E402
from genesis.models import Config, SolverProgram  # noqa: E402
from genesis.panels import make_hard_panel  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.verification.lean import check_witness_formally  # noqa: E402
from genesis.worldstep import LoopConfig, ResearchLoop  # noqa: E402

NOBODY = 65534


def keypair(d, name):
    k = Ed25519PrivateKey.generate(); p = Path(d) / f'{name}.pem'
    p.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
    return p, base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                           serialization.PublicFormat.Raw)).decode()


def research_as_nobody(campaign, trust, steps):
    code = ('import json,sys\nfrom genesis.store import Store\nfrom genesis.kernel.phases import advance\n'
            'steps=json.loads(sys.stdin.read());out=[]\n'
            f'with Store({str(campaign)!r}) as s:\n'
            '    for target,env in steps:\n'
            '        try:out.append(["OK",advance(s,target,envelope=env,trust_root=' + repr(str(trust)) + ')])\n'
            '        except Exception as e:out.append([type(e).__name__,str(e)])\n'
            '    out.append(["PHASE",s.state("phase")])\nprint(json.dumps(out))\n')
    proc = subprocess.run([sys.executable, '-c', code], input=json.dumps(steps), capture_output=True, text=True,
                          env={'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'},
                          user=NOBODY, group=NOBODY, extra_groups=[], cwd='/', timeout=600)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    return json.loads(proc.stdout)


def main(out_dir):
    if os.geteuid() != 0:
        raise SystemExit('run as root: the walkthrough drops the research side to an unprivileged UID')
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False); out.chmod(0o755)
    steps = []; t0 = time.time()

    def step(n, name, **detail):
        steps.append({'step': n, 'action': name, **detail}); print(json.dumps(steps[-1])[:300], flush=True)

    campaign = out / 'campaign'
    Campaign.initialize(campaign, Config(generations=2, tasks_per_panel=4, proposals_per_epoch=4, research_trials=16))
    step(1, 'initialize campaign and validate config', phase='VALIDATED_CONFIG', evidence='L0 only')
    with Campaign(campaign) as c:
        summary = c.run()
        step(2, 'load DEV tasks and contracts', tasks=c.store.db.execute("SELECT count(*) FROM entities WHERE kind='task'").fetchone()[0])
        step(3, 'run baselines', comparisons=[g['solver_comparison'] for g in summary['generations']])
        step(8, 'causal comparison (DEV ablation/placebo)', controls=[g['causal_controls'] for g in summary['generations']])
        request = load_json(request_bundle(c, 3))
        step(10, 'freeze selected successor', phase=c.store.state('phase'), request=digest(request)[:16])
    # 4-7, 9, 15: world loop on a hard public DEV panel
    loop_root = out / 'world_loop'
    with ResearchLoop(loop_root, LoopConfig(tasks=4, epochs=3, cpu_budget_per_epoch=40, verify_seconds=20)) as loop:
        ls = loop.run()
    hard, _ = make_hard_panel(20261013, 2, 'c4_host_v2', 'DEV', certify=False)
    g = gap_engine(hard[0], SolverProgram(rounds=8), [{'optimum': 40, 'value': 35, 'family': 'f', 'status': 'SUCCESS'}])
    step(4, 'diagnose gap', hypotheses=g['hypotheses'], next_experiment=g['next_experiment'])
    step(5, 'spawn bounded worlds', worlds={k[:8]: v['state'] for k, v in ls['worlds'].items()})
    step(6, 'builder/barrier execute (barrier_escape macro under grants)',
         funded=[len(e.get('realized', [])) for e in ls['epochs']])
    step(7, 'independent check', optimality_checked=ls['optimality_checked'], of=len(ls['tasks']))
    with Store(loop_root) as s:
        best = s.state(f'best:{hard[0].task_id}')
    from genesis.verification.sat import certified_bounds
    bounds = certified_bounds(hard[0], seconds=60)
    lean = check_witness_formally(hard[0], bounds['witness'])
    step(7, 'formal check of one witness (pinned Lean, sandboxed)', lean=lean['status'], axioms=lean.get('axioms'))
    comp = cognitive_compile(hard, SolverProgram(rounds=8))
    step(9, 'compile useful mechanism', status=comp['status'], evidence=comp['evidence'])
    step(15, 'meta-analysis', calibration_error=ls['calibration_error'],
         meta_gap_candidates=[e.get('meta_gap_candidates') for e in ls['epochs']])
    # 11-13 with FIXTURE roles
    secrets_dir = out / 'fixture_secrets'; secrets_dir.mkdir(mode=0o700)
    keys = {n: keypair(secrets_dir, n) for n in ('prereg', 'custodian', 'auditor', 'release', 'root')}
    private = out / 'fixture_private'; private.mkdir(mode=0o700); private.chmod(0o700)
    manifest = private / 'exposure_manifest.json'
    reference = json.loads((ROOT / 'custody_reference' / 'public_exposure_manifest.json').read_text())
    reference['sources'] = [s for s in reference['sources'] if s['kind'] != 'campaign_store']
    manifest.write_text(json.dumps(reference)); manifest.chmod(0o600)
    anchor = register(private, request, keys['prereg'][0], 'FIXTURE_OPERATOR_NOT_INDEPENDENT',
                      exposure_manifest=manifest, campaign_export=campaign / 'exports' / 'campaign_export.zip')
    step(11, 'leak scan / registration (custodian-built exposure registry)',
         exposure_graphs=anchor['payload']['exposure_graphs'], roles='FIXTURE')
    pool_tasks, _ = make_hard_panel(int.from_bytes(os.urandom(4), 'big'), 3, 'c4_host_v2', 'CONFIRM', certify_seconds=60)
    pool = private / 'pool.json'; pool.write_bytes(canonical([t.model_dump(mode='json') for t in pool_tasks]))
    receipt = evaluate(private, digest(request), pool, keys['custodian'][0], 'FIXTURE_OPERATOR_NOT_INDEPENDENT')
    p = receipt['payload']
    step(12, 'execute sealed panel (fixture operator, hard CONFIRM hosts, SAT-certified optima)',
         rows=p['completed_rows'], wins=p['wins'], losses=p['losses'], ties=p['ties'])
    trust = out / 'fixture_trust'; trust.mkdir()
    (trust / 'root.pub').write_text(keys['root'][1])
    roles = {'custodian_key': keys['custodian'][1], 'prereg_key': keys['prereg'][1], 'auditor_key': keys['auditor'][1],
             'release_key': keys['release'][1], 'release_authority_id': 'FIXTURE_RELEASE_BOARD'}
    (trust / 'roles.json').write_bytes(canonical(sign({'schema': 'genesis-role-registry-v1', 'roles': roles},
                                                      keys['root'][0])))
    for f in (trust / 'root.pub', trust / 'roles.json'):
        f.chmod(0o444)
    for dirpath, _, files in os.walk(campaign):
        os.chown(dirpath, NOBODY, NOBODY)
        for f in files:
            os.chown(os.path.join(dirpath, f), NOBODY, NOBODY)
    phases = research_as_nobody(campaign, trust, [['LEAK_SCAN_PASSED', anchor], ['SEALED_RUNNING', receipt],
                                                  ['JUDGED', receipt]])
    step(13, 'independent judge (signed receipts verified against the role registry)', phases=phases)
    audit = sign({'request_hash': digest(request), 'receipt_hash': digest(receipt), 'status': 'PASS',
                  'open_critical': 0, 'independent_operation_verified': False, 'raw_replay_verified': False,
                  'formal_replay_verified': False}, keys['auditor'][0])
    pre_code = ('import json,sys;from genesis.custodian import release_preflight;a=json.loads(sys.stdin.read());'
                f'print(json.dumps(release_preflight(*a,trust_root={str(trust)!r})))')
    pre = subprocess.run([sys.executable, '-c', pre_code], input=json.dumps([request, anchor, receipt, audit]),
                         capture_output=True, text=True, user=NOBODY, group=NOBODY, extra_groups=[], cwd='/',
                         env={'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'})
    preflight = json.loads(pre.stdout)
    step(14, 'release or reject — NOT PERFORMED (needs an external release authority)',
         preflight=preflight['status'], reasons=preflight['reasons'][:6], promotion_allowed=preflight['promotion_allowed'])
    report = ['# End-to-end walkthrough (spec §40)', '',
              'Steps 1–10 and 15 ran on public DEV material. Steps 11–13 used FIXTURE roles generated in this run '
              '(not independent custody). Step 14 was not performed: it needs an external release authority.', '',
              '| Step | Action | Key result |', '|---:|---|---|']
    for s_ in sorted(steps, key=lambda x: x['step']):
        detail = {k: v for k, v in s_.items() if k not in ('step', 'action')}
        report.append(f"| {s_['step']} | {s_['action']} | `{json.dumps(detail)[:160]}` |")
    report += ['', f'Elapsed: {round(time.time() - t0, 1)} s. Promotion allowed: no.', '']
    text = require_clean('\n'.join(report), {'math': 'OPTIMALITY_CHECKED', 'utility': 'DEV_ONLY',
                                             'causality': 'CORRELATED', 'improver': 'NOT_TESTED',
                                             'novelty': 'UNKNOWN', 'replication': 'NONE'})
    (out / 'walkthrough.md').write_text(text)
    (out / 'walkthrough.json').write_bytes(canonical({'steps': steps, 'fixture_roles': True,
                                                      'release_performed': False}))
    print(f'wrote {out / "walkthrough.md"}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='genesis-e2e-'))
