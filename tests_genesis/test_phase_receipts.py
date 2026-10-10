"""End-to-end: a frozen campaign reaches JUDGED/RELEASED only through verified signed receipts.

The custodian steps run with fixture keys; the research-side phase changes run
in a child process dropped to UID 65534 against a root-owned trust root, which
is what "externally controlled" means on a single machine. Fixture signatures
prove protocol behaviour only, not operator independence.
"""
import base64
from itertools import combinations
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.campaign import Campaign
from genesis.cli import request_bundle
from genesis.common import canonical, digest, load_json
from genesis.custodian import register, evaluate
from genesis.kernel.phases import advance, PhaseError
from genesis.kernel.signing import sign
from genesis.models import Config, GraphTask
from genesis.store import Store

SRC = Path(__file__).resolve().parents[1] / 'src'
NOBODY = 65534


def keypair(directory, name):
    k = Ed25519PrivateKey.generate()
    path = Path(directory) / f'{name}.pem'
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    return path, base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                              serialization.PublicFormat.Raw)).decode()


def fresh_pool(count=2, seed=4242):
    rng = random.Random(seed); out = []
    while len(out) < count:
        edges = tuple(e for e in combinations(range(10), 2) if rng.random() < 0.3)
        if 12 <= len(edges) <= 20:
            out.append(GraphTask(task_id=f'confirm-{len(out)}', n=10, edges=edges, family='fresh10', split='CONFIRM'))
    return out


@unittest.skipUnless(os.geteuid() == 0, 'needs root to create an unprivileged research child')
class SignedPhases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name); base.chmod(0o755)
        secrets = base / 'secrets'; secrets.mkdir(mode=0o700)
        cls.keys = {n: keypair(secrets, n) for n in ('prereg', 'custodian', 'auditor', 'release', 'root')}
        # Research side: a real (small) DEV campaign, frozen, with its request bundle.
        cls.campaign = base / 'campaign'
        Campaign.initialize(cls.campaign, Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2,
                                                 research_trials=8))
        with Campaign(cls.campaign) as c:
            c.run()
            request = load_json(request_bundle(c, 2))
        # Custodian side: registration and sealed evaluation with distinct keys.
        private = base / 'private'; private.mkdir(mode=0o700); private.chmod(0o700)
        manifest = private / 'manifest.json'
        manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []})); manifest.chmod(0o600)
        cls.anchor = register(private, request, cls.keys['prereg'][0], 'fixture-operator',
                              exposure_manifest=manifest, campaign_export=cls.campaign / 'exports/campaign_export.zip')
        pool = base / 'pool.json'
        pool.write_bytes(canonical([t.model_dump(mode='json') for t in fresh_pool()]))
        cls.receipt = evaluate(private, digest(request), pool, cls.keys['custodian'][0], 'fixture-operator')
        cls.decision = sign({'schema': 'genesis-release-decision-v1', 'request_hash': digest(request),
                             'decision': 'RELEASE', 'receipt_hash': digest(cls.receipt)}, cls.keys['release'][0])
        # External trust root, owned by root and read-only.
        trust = base / 'trust'; trust.mkdir()
        (trust / 'root.pub').write_text(cls.keys['root'][1])
        roles = {'custodian_key': cls.keys['custodian'][1], 'prereg_key': cls.keys['prereg'][1],
                 'auditor_key': cls.keys['auditor'][1], 'release_key': cls.keys['release'][1],
                 'release_authority_id': 'external-board'}
        (trust / 'roles.json').write_bytes(canonical(sign({'schema': 'genesis-role-registry-v1', 'roles': roles},
                                                          cls.keys['root'][0])))
        for p in (trust / 'root.pub', trust / 'roles.json'):
            p.chmod(0o444)
        cls.trust = trust
        # Hand the campaign directory to the research UID.
        for dirpath, dirnames, filenames in os.walk(cls.campaign):
            os.chown(dirpath, NOBODY, NOBODY)
            for f in filenames:
                os.chown(os.path.join(dirpath, f), NOBODY, NOBODY)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def research(self, steps):
        """Run phase advances as the unprivileged research UID; return results per step."""
        code = ('import json,sys\nfrom genesis.store import Store\nfrom genesis.kernel.phases import advance\n'
                'steps=json.loads(sys.stdin.read());out=[]\n'
                f'with Store({str(self.campaign)!r}) as s:\n'
                '    for target,env in steps:\n'
                '        try:out.append(["OK",advance(s,target,envelope=env,trust_root=' + repr(str(self.trust)) + ')])\n'
                '        except Exception as e:out.append([type(e).__name__,str(e)])\n'
                '    out.append(["PHASE",s.state("phase")])\nprint(json.dumps(out))\n')
        proc = subprocess.run([sys.executable, '-c', code], input=json.dumps(steps), capture_output=True, text=True,
                              env={'PYTHONPATH': str(SRC), 'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'},
                              user=NOBODY, group=NOBODY, extra_groups=[], cwd='/', timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_1_wrong_role_and_skipped_gates_are_refused(self):
        forged = sign(self.receipt['payload'], self.keys['prereg'][0])  # right content, wrong role key
        out = self.research([['SEALED_RUNNING', self.receipt], ['LEAK_SCAN_PASSED', forged],
                             ['RELEASED', self.decision]])
        self.assertEqual(out[0][0], 'PhaseError')            # cannot skip LEAK_SCAN_PASSED
        self.assertEqual(out[1][0], 'PhaseError')            # anchor schema/role mismatch
        self.assertEqual(out[2][0], 'PhaseError')            # cannot jump to RELEASED
        self.assertEqual(out[-1], ['PHASE', 'CANDIDATE_FROZEN'])

    def test_2_full_signed_path_reaches_released(self):
        out = self.research([['LEAK_SCAN_PASSED', self.anchor], ['SEALED_RUNNING', self.receipt],
                             ['JUDGED', self.receipt], ['RELEASED', self.decision]])
        self.assertEqual([o[0] for o in out[:4]], ['OK'] * 4, out)
        self.assertEqual(out[-1], ['PHASE', 'RELEASED'])
        with Store(self.campaign) as s:
            s.verify()
            self.assertEqual(s.state('phase_receipt:JUDGED'), self.receipt)

    def test_3_root_research_process_cannot_advance(self):
        root = Path(self.tmp.name) / 'copy'
        with tempfile.TemporaryDirectory() as d:
            Campaign.initialize(Path(d) / 'c', Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2,
                                                      research_trials=8))
            with Store(Path(d) / 'c') as s:
                s.set_state('phase', 'CANDIDATE_FROZEN'); s.set_state('frozen_request_hash', 'a' * 64)
                with self.assertRaises(PermissionError):
                    advance(s, 'LEAK_SCAN_PASSED', envelope=self.anchor, trust_root=self.trust)
                advance(s, 'INVALIDATED', reason='unauthorized mutation found in test')
                self.assertEqual(s.state('phase'), 'INVALIDATED')
                with self.assertRaises(PhaseError):
                    advance(s, 'RELEASED', envelope=self.decision, trust_root=self.trust)


if __name__ == '__main__':
    unittest.main()
