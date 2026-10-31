"""The fifth catalogue (`src/genesis/repairkernel/defects5.py`, B20_R185) and the sixth (`defects6.py`, B20_R186) are
what their rules produce: random mutants, not defects chosen by hand (`genesis.repairkernel.mutants`,
`scripts/b20r185_make_mutant_catalogue.py`, `scripts/b20r186_make_mutant_catalogue.py`).
  * the mutation operators on a source written for the test;
  * a mutant becomes a catalogue entry whose 'old' occurs once and whose replacement gives the mutant;
  * re-running the selection gives the sealed file byte for byte (the seed, the job seeds, the rules);
  * every entry is a real obstacle: it interrupts every job of the study's seeds, and the verifier rejects it;
  * no entry is a hand-written catalogue's defect; the kernel can build its jobs; the executor cannot read it."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r185_make_mutant_catalogue as MK  # noqa: E402
import b20r186_make_mutant_catalogue as MK6  # noqa: E402
import b20r187_make_mutant_catalogue as MK7  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects5 as DF5  # noqa: E402
from genesis.repairkernel import defects6 as DF6  # noqa: E402
from genesis.repairkernel import defects7 as DF7  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import mutants as MU  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

DEFECTS5_SHA256 = '59c4fc31a2500a4976a007f8f7fd66f548404f379a2600eba395f7eb910e3baa'
DEFECTS6_SHA256 = 'a4cb0c9976022378c70ce6b4ecf0cab8f1203a7b8c67af4893a6bae20feeca5e'
DEFECTS7_SHA256 = '9836c54d9be1738def9f04089f45857e35c8e852b0666645a264aa66741c9572'

TOY = '''class Toy:
    def __init__(self):
        self.a = {}
        self.b = {}
        self.n = 0

    def put(self, k, v):
        self.a[k] = v
        self.n += 1
        if self.n > 3:
            self.b[k] = max(v, 0)
'''


class Operators(unittest.TestCase):
    def test_each_operator_on_a_toy(self):
        got = MU.enumerate_mutants('toy', TOY)
        ops = {op for op, _, _ in got}
        self.assertEqual(ops, {'delete', 'arith', 'compare', 'constant', 'swap', 'attribute', 'call'})
        texts = {m for _, _, m in got}
        self.assertIn(TOY.replace('        self.n += 1\n', ''), texts)                      # delete
        self.assertIn(TOY.replace('self.n += 1', 'self.n -= 1'), texts)                     # arith
        self.assertIn(TOY.replace('self.n > 3', 'self.n >= 3'), texts)                      # compare
        self.assertIn(TOY.replace('self.n > 3', 'self.n > 4'), texts)                       # constant
        self.assertIn(TOY.replace('max(v, 0)', 'max(0, v)'), texts)                         # swap
        self.assertIn(TOY.replace('self.a[k] = v', 'self.b[k] = v'), texts)                 # attribute
        self.assertIn(TOY.replace('max(v, 0)', 'min(v, 0)'), texts)                         # call
        self.assertNotIn(TOY.replace('        self.a = {}\n', ''), texts)                   # never __init__
        self.assertNotIn(TOY.replace('            self.b[k] = max(v, 0)\n', ''), texts)     # blocks kept non-empty
        self.assertEqual(len(texts), len(got))
        for _, _, m in got:
            old, new = MU.as_defect(TOY, m)
            self.assertEqual(TOY.count(old), 1)
            self.assertEqual(TOY.replace(old, new), m)


class Catalogue(unittest.TestCase):
    def test_the_sealed_file(self):
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/repairkernel/defects5.py').read_bytes()).hexdigest(),
                         DEFECTS5_SHA256)
        self.assertEqual([d['id'] for d in DF5.DEFECTS], [f'Q{i:02d}' for i in range(1, 25)])
        self.assertEqual({d['split'] for d in DF5.DEFECTS}, {'heldout5'})

    def test_the_rules_reproduce_it(self):
        path = ROOT / 'src/genesis/repairkernel/defects5.py'
        sealed = path.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            try:
                MK.main([d])
                self.assertEqual(path.read_bytes(), sealed)
            finally:
                path.write_bytes(sealed)

    def test_every_entry_is_a_real_obstacle_and_none_is_hand_written(self):
        hand = MK.hand_written_sources()
        with tempfile.TemporaryDirectory() as tmp:
            for d in DF5.DEFECTS:
                bad = DF5.source(d['id'], TG.KERNEL_SOURCES)
                self.assertNotIn((d['target'], bad), hand, d['id'])
                self.assertIsNone(MK.examine(d['target'], bad, Path(tmp) / d['id']), d['id'])
                job, _ = BN.make(d['id'], MK.JOB_SEEDS[0], Path(tmp) / f"{d['id']}-make", version=2)
                self.assertEqual(job.file.read_text(), bad)
                self.assertEqual(job.run()['status'], 'failed')
                self.assertFalse(VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, bad)['accepted'])

    def test_the_executor_cannot_read_it(self):
        self.assertIn('defects5.py', FD.HIDDEN_FROM_EXECUTOR)


class Catalogue6(unittest.TestCase):
    def test_the_sealed_file(self):
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/repairkernel/defects6.py').read_bytes()).hexdigest(),
                         DEFECTS6_SHA256)
        self.assertEqual([d['id'] for d in DF6.DEFECTS], [f'V{i:02d}' for i in range(1, 37)])
        self.assertEqual({d['split'] for d in DF6.DEFECTS}, {'heldout6'})
        self.assertNotEqual((MK6.SEED, MK6.JOB_SEEDS), (MK.SEED, MK.JOB_SEEDS))

    def test_the_rules_reproduce_it(self):
        path = ROOT / 'src/genesis/repairkernel/defects6.py'
        sealed = path.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            try:
                MK6.main([d])
                self.assertEqual(path.read_bytes(), sealed)
            finally:
                path.write_bytes(sealed)

    def test_every_entry_is_a_real_obstacle_and_none_was_drawn_before(self):
        before = MK6.excluded()
        with tempfile.TemporaryDirectory() as tmp:
            for d in DF6.DEFECTS:
                bad = DF6.source(d['id'], TG.KERNEL_SOURCES)
                self.assertNotIn((d['target'], bad), before, d['id'])
                self.assertIsNone(MK6.examine(d['target'], bad, Path(tmp) / d['id']), d['id'])
                job, _ = BN.make(d['id'], MK6.JOB_SEEDS[0], Path(tmp) / f"{d['id']}-make", version=2)
                self.assertEqual(job.file.read_text(), bad)

    def test_the_executor_cannot_read_it(self):
        self.assertIn('defects6.py', FD.HIDDEN_FROM_EXECUTOR)


class Catalogue7(unittest.TestCase):
    def test_the_sealed_file(self):
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/repairkernel/defects7.py').read_bytes()).hexdigest(),
                         DEFECTS7_SHA256)
        self.assertEqual([d['id'] for d in DF7.DEFECTS], [f'Z{i:02d}' for i in range(1, 37)])
        self.assertEqual({d['split'] for d in DF7.DEFECTS}, {'heldout7'})
        self.assertEqual(len({MK.SEED, MK6.SEED, MK7.SEED}), 3)
        self.assertFalse(set(MK7.JOB_SEEDS) & (set(MK.JOB_SEEDS) | set(MK6.JOB_SEEDS)))

    def test_the_rules_reproduce_it(self):
        path = ROOT / 'src/genesis/repairkernel/defects7.py'
        sealed = path.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            try:
                MK7.main([d])
                self.assertEqual(path.read_bytes(), sealed)
            finally:
                path.write_bytes(sealed)

    def test_every_entry_is_a_real_obstacle_and_none_was_drawn_before(self):
        before = MK7.excluded()
        with tempfile.TemporaryDirectory() as tmp:
            for d in DF7.DEFECTS:
                bad = DF7.source(d['id'], TG.KERNEL_SOURCES)
                self.assertNotIn((d['target'], bad), before, d['id'])
                self.assertIsNone(MK7.examine(d['target'], bad, Path(tmp) / d['id']), d['id'])
                job, _ = BN.make(d['id'], MK7.JOB_SEEDS[0], Path(tmp) / f"{d['id']}-make", version=2)
                self.assertEqual(job.file.read_text(), bad)

    def test_the_executor_cannot_read_it(self):
        self.assertIn('defects7.py', FD.HIDDEN_FROM_EXECUTOR)


if __name__ == '__main__':
    unittest.main()
