"""Authority invariant (spec §2.4): branching cannot multiply budgets or permissions."""
import tempfile
import unittest

from genesis.kernel.authority import AuthorityError, GrantLedger, BUDGET_FIELDS
from genesis.store import Store

ROOT = {'cpu_seconds': 100, 'wall_seconds': 200, 'attempts': 10, 'output_bytes': 10_000, 'paid_api_usd': 0}


class Authority(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.s = Store(self.tmp.name); self.addCleanup(self.s.close)
        self.g = GrantLedger(self.s)
        self.root = self.g.root_grant(ROOT, {'execute_fixed_dsl', 'execute_sandboxed_code'}, issuer='campaign-config')

    def test_children_lease_from_the_parent_and_cannot_exceed_it(self):
        a = self.g.child(self.root, {'cpu_seconds': 60, 'attempts': 6}, {'execute_fixed_dsl'}, purpose='world-a')
        b = self.g.child(self.root, {'cpu_seconds': 40, 'attempts': 4}, {'execute_fixed_dsl'}, purpose='world-b')
        with self.assertRaisesRegex(AuthorityError, 'exceeds parent remaining'):
            self.g.child(self.root, {'cpu_seconds': 1}, {'execute_fixed_dsl'}, purpose='world-c')
        with self.assertRaisesRegex(AuthorityError, 'exceeds parent remaining'):
            self.g.child(a, {'cpu_seconds': 61}, {'execute_fixed_dsl'}, purpose='grandchild')
        leased = sum(self.s.state(f'grant:{x}')['budgets']['cpu_seconds'] for x in (a, b))
        self.assertLessEqual(leased, self.g.total_authority()['cpu_seconds'])

    def test_children_cannot_gain_permissions(self):
        a = self.g.child(self.root, {'cpu_seconds': 1}, {'execute_fixed_dsl'}, purpose='w')
        with self.assertRaisesRegex(AuthorityError, 'permissions its parent lacks'):
            self.g.child(a, {'cpu_seconds': 1}, {'execute_sandboxed_code'}, purpose='escalate')

    def test_network_release_and_provider_need_external_authorization(self):
        with tempfile.TemporaryDirectory() as d, Store(d) as s:
            with self.assertRaisesRegex(AuthorityError, 'external authorization'):
                GrantLedger(s).root_grant(ROOT, {'network'}, issuer='self')

    def test_root_grant_cannot_be_reissued(self):
        with self.assertRaisesRegex(AuthorityError, 'already has a root grant'):
            self.g.root_grant(ROOT, {'execute_fixed_dsl'}, issuer='again')

    def test_charges_are_recorded_and_exhaustion_blocks(self):
        a = self.g.child(self.root, {'cpu_seconds': 5, 'attempts': 1}, {'execute_fixed_dsl'}, purpose='w')
        self.g.require(a, 'execute_fixed_dsl', cpu_seconds=5, attempts=1)
        remaining = self.g.charge(a, 'r' * 64, cpu_seconds=7, attempts=1)  # overshoot is recorded, not hidden
        self.assertEqual(remaining['cpu_seconds'], 0)
        with self.assertRaisesRegex(AuthorityError, 'exhausted'):
            self.g.require(a, 'execute_fixed_dsl', cpu_seconds=1)
        events = [r[0] for r in self.s.db.execute("SELECT body FROM events")]
        self.assertTrue(any(b'"GRANT_CHARGED"' in e for e in events))
        self.s.verify()

    def test_sandbox_refuses_without_permission(self):
        from genesis.sandbox import run_python
        a = self.g.child(self.root, {'cpu_seconds': 60, 'attempts': 1}, {'execute_fixed_dsl'}, purpose='no-sandbox')
        with self.assertRaisesRegex(AuthorityError, 'execute_sandboxed_code'):
            run_python('print(1)', grant=a, ledger=self.g)


if __name__ == '__main__':
    unittest.main()
