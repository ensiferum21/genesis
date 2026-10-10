"""GI6-11: release readiness requires an externally controlled role registry.

The audit showed that locally minted keys passed as caller-controlled pins
produced EXTERNAL_RELEASE_REVIEW_READY. Pins are no longer arguments; they are
read from a trust root the research process cannot write and that must not be
run as root. The positive path is exercised in a child process that drops to
an unprivileged UID, which is the only way to make "external control" real on
one machine. Fixture keys still prove protocol behaviour, not independence.
"""
import base64
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.common import canonical, digest
from genesis.custodian import release_preflight, sign, load_role_registry
from tests_genesis.signed_fixtures import SignedFixture

SRC = Path(__file__).resolve().parents[1] / 'src'
NOBODY = 65534


def keypair(directory, name):
    k = Ed25519PrivateKey.generate()
    path = Path(directory) / f'{name}.pem'
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    pub = base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                       serialization.PublicFormat.Raw)).decode()
    return path, pub


def fabricated_release(keys):
    """A fully self-consistent signed bundle, as the audit's attacker built (current schemas)."""
    fx = SignedFixture.__new__(SignedFixture)
    fx.keys, fx._tick = keys, 0
    request = fx.request(task_count=300)
    anchor = fx.anchor(request)
    receipt = fx.receipt(request, anchor, wins=300, losses=0, ties=0, family_p=0.001)
    audit = sign({'request_hash': digest(request), 'receipt_hash': digest(receipt), 'status': 'PASS',
                  'open_critical': 0, 'independent_operation_verified': True, 'raw_replay_verified': True,
                  'formal_replay_verified': True}, keys['auditor'][0])
    return request, anchor, receipt, audit


def write_trust_root(path, keys, root_key, roles_override=None):
    path.mkdir()
    (path / 'root.pub').write_text(root_key[1])
    roles = roles_override or {'custodian_key': keys['custodian'][1], 'prereg_key': keys['prereg'][1],
                               'auditor_key': keys['auditor'][1], 'release_key': keys['release'][1],
                               'release_authority_id': 'external-release-board'}
    (path / 'roles.json').write_bytes(canonical(sign({'schema': 'genesis-role-registry-v1', 'roles': roles}, root_key[0])))


class RoleRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.base.chmod(0o755)
        self.secrets = self.base / 'secrets'; self.secrets.mkdir(mode=0o700)
        self.keys = {name: keypair(self.secrets, name) for name in ('custodian', 'prereg', 'auditor', 'release')}
        self.root_key = keypair(self.secrets, 'trust-root')

    def test_pins_are_no_longer_a_caller_argument(self):
        self.assertNotIn('pins', inspect.signature(release_preflight).parameters)
        request, anchor, receipt, audit = fabricated_release(self.keys)
        with self.assertRaises(TypeError):
            release_preflight(request, anchor, receipt, audit, pins={})

    def test_gi6_11_self_minted_trust_root_is_blocked(self):
        # The research account (this process) creates and owns the trust root.
        trust = self.base / 'trust'
        write_trust_root(trust, self.keys, self.root_key)
        result = release_preflight(*fabricated_release(self.keys), trust_root=trust)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(result['promotion_allowed'])
        joined = ' '.join(result['reasons'])
        self.assertTrue('runs as root' in joined or 'owned by the research account' in joined, joined)

    def test_default_trust_root_absent_blocks(self):
        result = release_preflight(*fabricated_release(self.keys), trust_root=self.base / 'nope')
        self.assertEqual(result['status'], 'BLOCKED')

    def _run_as_nobody(self, trust):
        if os.geteuid() != 0:
            self.skipTest('needs root to drop to an unprivileged UID; isolation not demonstrated')
        payload = json.dumps(list(fabricated_release(self.keys)))
        code = ('import json,sys;from genesis.custodian import release_preflight;'
                'a=json.loads(sys.stdin.read());'
                f'print(json.dumps(release_preflight(*a,trust_root={str(trust)!r})))')
        proc = subprocess.run([sys.executable, '-c', code], input=payload, capture_output=True, text=True,
                              env={'PYTHONPATH': str(SRC), 'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'},
                              user=NOBODY, group=NOBODY, extra_groups=[], cwd='/', timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def _externalize(self, trust):
        for p in (trust / 'root.pub', trust / 'roles.json'):
            os.chown(p, 0, 0); p.chmod(0o444)
        os.chown(trust, 0, 0); trust.chmod(0o755)

    def test_ready_only_when_trust_root_is_outside_the_research_account(self):
        trust = self.base / 'trust'
        write_trust_root(trust, self.keys, self.root_key)
        self._externalize(trust)
        result = self._run_as_nobody(trust)
        self.assertEqual(result['status'], 'EXTERNAL_RELEASE_REVIEW_READY', result['reasons'])
        self.assertFalse(result['promotion_allowed'])
        self.assertEqual(result['next_authority'], 'external-release-board')

    def test_registry_signed_by_a_different_root_is_rejected(self):
        trust = self.base / 'trust'
        write_trust_root(trust, self.keys, self.root_key)
        other = keypair(self.secrets, 'other-root')
        (trust / 'root.pub').write_text(other[1])  # registry no longer verifies under the pinned root
        self._externalize(trust)
        result = self._run_as_nobody(trust)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('signature invalid', ' '.join(result['reasons']))

    def test_root_key_cannot_double_as_a_role_key(self):
        trust = self.base / 'trust'
        roles = {'custodian_key': self.root_key[1], 'prereg_key': self.keys['prereg'][1],
                 'auditor_key': self.keys['auditor'][1], 'release_key': self.keys['release'][1],
                 'release_authority_id': 'board'}
        write_trust_root(trust, self.keys, self.root_key, roles_override=roles)
        self._externalize(trust)
        result = self._run_as_nobody(trust)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('independent role identities', ' '.join(result['reasons']))

    def test_research_writable_trust_root_is_blocked_even_for_unprivileged_process(self):
        trust = self.base / 'trust'
        write_trust_root(trust, self.keys, self.root_key)
        self._externalize(trust)
        if os.geteuid() == 0:
            os.chown(trust / 'roles.json', NOBODY, NOBODY)  # now owned by the research UID
        result = self._run_as_nobody(trust)
        self.assertEqual(result['status'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
