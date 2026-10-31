"""`genesis.wire` (B20R184-PICKLE): the tagged JSON that replaced pickle in the obstacle loop's wire and job checkpoints.
  * every kind of value round-trips, with shared and cyclic references kept;
  * a class or function the caller did not name, an unknown tag or a malformed value is refused;
  * every component's job state round-trips as it did under pickle (the comparison uses pickle here, in a test only);
  * a job interrupted, checkpointed and resumed on the new format ends as an uninterrupted one;
  * nothing in the shipped code unpickles (the GI6-02 rule)."""
from collections import OrderedDict
import pickle
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import wire as W  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402


class Thing:
    pass


def helper():
    return 1


class RoundTrip(unittest.TestCase):
    def test_values_sharing_and_cycles(self):
        shared = [1, 2]
        t = Thing()
        t.a, t.b = shared, {(1, 'x'): frozenset({3})}
        v = {'n': None, 'b': True, 'i': -7, 'f': 0.1, 's': 'é', 'l': shared, 'm': shared, 't': (1, (2,)),
             'set': {1, (2, 3)}, 'od': OrderedDict([(2, 'b'), (1, 'a')]), 3: 'int key', (4, 5): 'tuple key',
             'obj': t, 'fn': helper, 'nan': float('inf')}
        cyc = [0]
        cyc.append(cyc)
        v['cyc'] = cyc
        back = W.loads(W.dumps(v, (Thing, helper)), (Thing, helper))
        for k in ('n', 'b', 'i', 'f', 's', 't', 'set', 3, (4, 5), 'nan'):
            self.assertEqual(back[k], v[k], k)
            self.assertIs(type(back[k]), type(v[k]), k)
        self.assertEqual(list(back['od'].items()), [(2, 'b'), (1, 'a')])
        self.assertIs(type(back['od']), OrderedDict)
        self.assertIs(back['l'], back['m'])                     # aliasing kept
        self.assertIs(back['obj'].a, back['l'])
        self.assertEqual(back['obj'].b, {(1, 'x'): frozenset({3})})
        self.assertIs(type(back['obj']), Thing)
        self.assertIs(back['fn'], helper)
        self.assertIs(back['cyc'][1], back['cyc'])               # a cycle kept

    def test_refusals(self):
        with self.assertRaises(W.WireError):
            W.dumps(Thing())                                     # a class not named
        with self.assertRaises(W.WireError):
            W.dumps(helper)
        t = Thing()
        text = W.dumps({'x': t}, (Thing,))
        with self.assertRaises(W.WireError):
            W.loads(text)                                        # the reader did not name it
        for bad in ('[1, 2]', '{"x": 1}', '{"r": 5}', '{"o": [0, "os", {}]}', '{"fn": "system"}',
                    '{"l": [0, [{"r": 0}]], "d": [1, []]}', '{"l": ["a", []]}'):
            with self.assertRaises(W.WireError, msg=bad):
                W.loads(bad)


class Jobs(unittest.TestCase):
    def test_every_components_state_round_trips_as_under_pickle(self):
        for t in sorted(TG.KERNEL_SOURCES):
            with tempfile.TemporaryDirectory() as d:
                job = BN.Job(Path(d), t, 3, source=TG.KERNEL_SOURCES[t], version=2)
                state, _ = BN.execute(t, job.module(), job.cargs, job.ckw, job.ops[:1200], 0, None)
                ours = W.loads(W.dumps(state, BN.WIRE_ALLOWED), BN.WIRE_ALLOWED)
                theirs = pickle.loads(pickle.dumps(state))
                self.assertEqual(W.dumps(ours, BN.WIRE_ALLOWED), W.dumps(theirs, BN.WIRE_ALLOWED), t)

    def test_an_interrupted_and_resumed_job_ends_as_an_uninterrupted_one(self):
        with tempfile.TemporaryDirectory() as d:
            job, _ = BN.make('D3', 1, Path(d) / 'd3', version=2)      # the ledger's undo: interrupted at op 2,000
            first = job.run()
            self.assertEqual((first['status'], first['op']), ('failed', 2000))
            self.assertTrue((job.dir / BN.STATE).exists())
            self.assertEqual(len(list((job.dir / 'checkpoints').glob('*.json'))), 10)
            self.assertFalse(list(job.dir.rglob('*.pkl')))
            job.file.write_text(TG.KERNEL_SOURCES['ledger'])
            again = job.run(resume=True)
            self.assertEqual(again['status'], 'done')
            self.assertLessEqual(again['started'], first['op'])
            clean, _ = BN.make_clean('ledger', 1, Path(d) / 'clean', version=2)
            self.assertEqual(clean.run()['status'], 'done')
        self.assertIn('M1', DF.BY_ID)

    def test_nothing_shipped_unpickles(self):
        for f in ('repairkernel/bench.py', 'repairkernel/executor.py', 'repairkernel/foundry.py', 'repair/remote.py'):
            text = (ROOT / 'src/genesis' / f).read_text()
            self.assertNotIn('pickle.load', text, f)
            self.assertNotIn('Unpickler', text, f)


if __name__ == '__main__':
    unittest.main()
