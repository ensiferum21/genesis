"""B20_R22 (H08 s20.6): legacy retention and negative transfer under a frozen protocol.

A protocol is frozen once, before measuring; each version pair is measured at most once within a
budget; protected material stays out of the campaign store and is checked against its salted
commitment; a real loss is NEGATIVE_TRANSFER and a real gain RETAINED. Executions are real.
"""
import copy
import os
from pathlib import Path
import tempfile
import unittest

from genesis import retention as RT
from genesis.common import digest
from genesis.domains import ADAPTERS
from genesis.models import Limits, SolverProgram
from genesis.store import Store

STRONG = SolverProgram(weights=(0, 0, 0, 1), rounds=32, exchange=True)
WEAK = SolverProgram(rounds=1)


def version(store, generation, parent, program):
    doc = {'generation': generation, 'parent': parent, 'solver': program.model_dump(mode='json')}
    vid = digest(doc)
    store.save('system_version', vid, doc)
    return vid


class Retention(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c4, tf = ADAPTERS['c4_host_v2'], ADAPTERS['triangle_free_host_v1']
        cls.legacy, _, _ = c4.generate(91, 6, 'DEV', 'erdos', {'n': 16, 'p': 0.4})
        cls.transfer, _, _ = tf.generate(92, 6, 'DEV', 'erdos', {'n': 14, 'p': 0.45})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.s = Store(self.tmp.name + '/store'); self.addCleanup(self.s.close)
        self.v0 = version(self.s, -1, None, WEAK)
        self.v1 = version(self.s, 0, self.v0, STRONG)
        self.v2 = version(self.s, 1, self.v1, WEAK)

    def panels(self):
        return {'legacy': list(self.legacy), 'transfer': list(self.transfer)}

    def test_gain_is_retained_and_loss_is_negative_transfer(self):
        RT.freeze(self.s, self.panels(), limits=Limits(), budget=3)
        up = RT.measure(self.s, self.v0, self.v1)
        self.assertEqual(up['verdict'], 'RETAINED', up['panels'])
        down = RT.measure(self.s, self.v1, self.v2)
        self.assertEqual(down['verdict'], 'NEGATIVE_TRANSFER', down['panels'])
        self.assertEqual(down['panels']['legacy']['verdict'], 'NEGATIVE_TRANSFER')
        self.assertEqual([m['sequence'] for m in RT.measurements(self.s)], [0, 1])
        self.assertIn('task_id', up['rows'][0])

    def test_frozen_once_measured_once_within_budget(self):
        RT.freeze(self.s, self.panels(), limits=Limits(), budget=2)
        with self.assertRaisesRegex(RT.RetentionError, 'already has a frozen'):
            RT.freeze(self.s, self.panels(), limits=Limits())
        RT.measure(self.s, self.v0, self.v1)
        with self.assertRaisesRegex(RT.RetentionError, 'already measured'):
            RT.measure(self.s, self.v0, self.v1)
        RT.measure(self.s, self.v1, self.v2)
        with self.assertRaisesRegex(RT.RetentionError, 'all are used'):
            RT.measure(self.s, self.v0, self.v2)
        with self.assertRaisesRegex(RT.RetentionError, 'not a stored system version'):
            RT.measure(self.s, self.v0, '0' * 64)

    def test_public_panels_are_checked_against_their_commitment(self):
        rec = RT.freeze(self.s, self.panels(), limits=Limits())
        bad = copy.deepcopy(rec)
        bad['panels']['legacy']['task_list'][0]['edges'] = bad['panels']['legacy']['task_list'][0]['edges'][1:]
        with self.assertRaisesRegex(RT.RetentionError, 'differs from its commitment'):
            RT.panels(bad)
        for kw in ({'margin': 0}, {'budget': 0}, {'material': 'SECRET'}, {'level': 0.4}):
            with self.assertRaises(RT.RetentionError):
                RT.freeze(Store(self.tmp.name + f'/other{len(kw)}{list(kw)[0]}'), self.panels(), limits=Limits(), **kw)

    def test_protected_material_stays_out_of_the_store(self):
        private = Path(self.tmp.name) / 'private'
        rec = RT.freeze(self.s, self.panels(), limits=Limits(), material='PROTECTED', private_root=private)
        self.assertNotIn('task_list', rec['panels']['legacy'])
        dump = b''.join(p.read_bytes() for p in (Path(self.tmp.name) / 'store' / 'objects').rglob('*') if p.is_file())
        self.assertNotIn(self.legacy[0].task_id.encode(), dump)
        self.assertEqual(os.stat(private).st_mode & 0o777, 0o700)
        with self.assertRaisesRegex(RT.RetentionError, 'needs the private root'):
            RT.measure(self.s, self.v0, self.v1)
        m = RT.measure(self.s, self.v0, self.v1, private_root=private)
        self.assertIn('task_sha256', m['rows'][0])
        self.assertNotIn('task_id', m['rows'][0])
        path = private / 'retention_material.json'
        path.chmod(0o644)
        with self.assertRaisesRegex(RT.RetentionError, 'private'):
            RT.panels(rec, private)
        path.chmod(0o600)
        data = path.read_text().replace(self.legacy[0].task_id, 'swapped-task')
        path.write_text(data); path.chmod(0o600)
        with self.assertRaisesRegex(RT.RetentionError, 'differs from its commitment'):
            RT.panels(rec, private)


if __name__ == '__main__':
    unittest.main()
