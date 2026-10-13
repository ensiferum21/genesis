"""B20_R16 (H08, s20.6): active version, rollback, version revocation and the resume gate.

Rollback changes the active pointer and records why; it never erases the failed child. A revoked
version takes its descendants with it, the kernel claims that depend on them are invalidated, and a
campaign resumes only from a version that is still active and valid. Real campaigns and a real crash
for the integration; fixture versions for the rules.
"""
from pathlib import Path
import tempfile
import unittest

from genesis import versions as VS
from genesis.campaign import Campaign
from genesis.common import digest
from genesis.kernel.evidence import EvidenceKernel
from genesis.models import Config
from genesis.store import Store
from tests_genesis.test_crash_consistency import crash

CFG = dict(seed=20261101, generations=2, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8)


def doc(generation, parent, tag=''):
    return {'generation': generation, 'parent': parent, 'solver': {'tag': tag or f'g{generation}'}}


class Rules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.s = Store(self.tmp.name + '/store'); self.addCleanup(self.s.close)
        self.v = {}
        self.v['v0'] = self.save(doc(-1, None))
        self.v['v1'] = self.save(doc(0, self.v['v0']))
        self.v['v2'] = self.save(doc(1, self.v['v1']))
        self.v['v1b'] = self.save(doc(0, self.v['v0'], 'side'))

    def save(self, d):
        vid = digest(d)
        self.s.save('system_version', vid, d)
        return vid

    def code(self, fn, *a, **kw):
        with self.assertRaises(VS.VersionError) as ctx:
            fn(*a, **kw)
        return ctx.exception.code

    def test_forward_rollback_and_status(self):
        v = self.v
        first = VS.activate(self.s, v['v0'], reason='initial', actor='op')
        self.assertEqual((first['kind'], first['previous']), ('ACTIVATE', None))
        self.assertEqual(VS.activate(self.s, v['v2'], reason='g1 retained', actor='op')['kind'], 'ACTIVATE')
        back = VS.rollback(self.s, v['v1'], reason='g1 regressed on retention', actor='op')
        self.assertEqual((back['kind'], back['previous'], back['reason']), ('ROLLBACK', v['v2'], 'g1 regressed on retention'))
        self.assertEqual(VS.active(self.s), v['v1'])
        self.assertEqual(self.s.state('active_version'), v['v1'])
        st = VS.status(self.s)
        self.assertEqual((st[v['v0']], st[v['v1']], st[v['v2']], st[v['v1b']]),
                         ('RETAINED', 'ACTIVE', 'ROLLED_BACK', 'INACTIVE'))
        self.assertIn(v['v2'], VS.versions(self.s))                       # the failed child is not erased
        self.assertEqual([r['kind'] for r in VS.pointer_history(self.s)], ['ACTIVATE', 'ACTIVATE', 'ROLLBACK'])
        self.assertIsNone(VS.activate(self.s, v['v1'], reason='again', actor='op'))   # no-op, no record
        self.assertEqual(len(VS.pointer_history(self.s)), 3)

    def test_refusals(self):
        v = self.v
        VS.activate(self.s, v['v1'], reason='initial', actor='op')
        self.assertEqual(self.code(VS.activate, self.s, v['v1b'], reason='switch', actor='op'), 'NOT_ON_PATH')
        self.assertEqual(self.code(VS.activate, self.s, v['v2'], reason=' ', actor='op'), 'UNEXPLAINED')
        self.assertEqual(self.code(VS.activate, self.s, v['v2'], reason='x', actor=''), 'UNEXPLAINED')
        self.assertEqual(self.code(VS.activate, self.s, '0' * 64, reason='x', actor='op'), 'VERSION_MISSING')
        forged = doc(2, v['v2'], 'forged')
        self.s.save('system_version', '1' * 64, forged)
        self.assertEqual(self.code(VS.activate, self.s, '1' * 64, reason='x', actor='op'), 'VERSION_ID_MISMATCH')
        orphan = self.save(doc(3, '2' * 64))
        self.assertEqual(self.code(VS.activate, self.s, orphan, reason='x', actor='op'), 'BROKEN_CHAIN')
        # The pointer records are immutable entities: a rewrite of history is refused by the store.
        rec = VS.pointer_history(self.s)[0]
        with self.assertRaises(ValueError):
            self.s.save(VS.POINTER, 'p000000', dict(rec, reason='rewritten'))

    def test_revocation_is_inherited_and_blocks_resume_until_a_rollback(self):
        v = self.v
        VS.activate(self.s, v['v0'], reason='initial', actor='op')
        VS.activate(self.s, v['v2'], reason='retained', actor='op')
        self.assertEqual(VS.resume_problems(self.s), [])
        affected = VS.revoke(self.s, v['v1'], reason='retained capability found unsound', actor='auditor')
        self.assertEqual(set(affected), {v['v1'], v['v2']})
        st = VS.status(self.s)
        self.assertEqual((st[v['v1']], st[v['v2']], st[v['v0']]), ('REVOKED', 'REVOKED_ANCESTOR', 'RETAINED'))
        self.assertTrue(VS.resume_problems(self.s)[0].startswith('INVALID REVOKED'))
        self.assertEqual(self.code(VS.activate, self.s, v['v1'], reason='x', actor='op'), 'REVOKED')
        self.assertEqual(self.code(VS.revoke, self.s, v['v1'], reason='', actor='op'), 'UNEXPLAINED')
        VS.rollback(self.s, v['v0'], reason='revocation of g0', actor='op')
        self.assertEqual(VS.resume_problems(self.s), [])
        VS.activate(self.s, v['v1b'], reason='new branch from the valid ancestor', actor='op')
        self.assertEqual(VS.status(self.s)[v['v1b']], 'ACTIVE')

    def test_revocation_reaches_kernel_claims(self):
        v = self.v
        k = EvidenceKernel(self.s)
        cap = k.record('execution_receipt', {'status': 'SUCCESS', 'version': v['v2']}, route='genesis.campaign',
                       source_hash='a' * 64, verdict='VALID')
        other = k.record('execution_receipt', {'status': 'SUCCESS', 'version': v['v1b']}, route='genesis.campaign',
                         source_hash='a' * 64, verdict='VALID')
        k.create_claim('uses-v2', 'a capability of v2 executes', 'fixture', [cap])
        k.create_claim('uses-v1b', 'a capability of v1b executes', 'fixture', [other])
        self.assertEqual(VS.dependent_nodes(k, {v['v1'], v['v2']}), [cap])
        VS.revoke(self.s, v['v1'], reason='unsound', actor='auditor', kernel=k)
        self.assertTrue(k.invalidation('uses-v2'))
        self.assertFalse(k.invalidation('uses-v1b'))


class CampaignIntegration(unittest.TestCase):
    def test_campaign_moves_the_pointer_with_retained_generations(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(**CFG))
            with Campaign(root) as c:
                summary = c.run()
                hist = VS.pointer_history(c.store)
                progress = c.store.state('dev_progress')
                self.assertEqual(VS.active(c.store), progress['parent_version'])
                retained = sum(g['retained_in_dev'] for g in summary['generations'])
                self.assertEqual([r['kind'] for r in hist], ['ACTIVATE'] * (1 + retained))
                self.assertEqual(hist[0]['reason'], 'initial version of the campaign')
                st = VS.status(c.store)
                self.assertEqual(st[VS.active(c.store)], 'ACTIVE')
                self.assertEqual(VS.resume_problems(c.store), [])

    def test_resume_refuses_a_revoked_or_changed_active_version(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(**CFG))
            crash(self, '''
                from genesis.campaign import Campaign
                with Campaign(P['root']) as c: c.run()
            ''', 'campaign.generation', root=str(root))
            with Store(root) as s:
                act = VS.active(s)
                self.assertIsNotNone(act)
                VS.revoke(s, act, reason='fixture: revoked while the campaign was interrupted', actor='auditor')
            with Campaign(root) as c:
                with self.assertRaisesRegex(RuntimeError, 'ACTIVE_VERSION_CHANGED|cannot resume'):
                    c.run(resume=True)


if __name__ == '__main__':
    unittest.main()
