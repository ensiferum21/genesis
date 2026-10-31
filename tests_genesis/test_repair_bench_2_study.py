"""B20_R180 (SR-1a2, `scripts/b20r180_repair_bench_2.py`), the second self-repair benchmark: its design, checked
without running the loop on any held-out defect.
  * the script is the preregistered one (its digest), and so are both catalogues;
  * the development defects are the whole first catalogue, the held-out ones the second, and every held-out defect
    interrupts every job (version 2) and is accepted by the verifier with the correct source and refused with its own;
  * the fixed constants: budget, arms (the frozen predecessor among them), comparators, job seeds, job version;
  * the sign test and the rule for 'repaired' (now: resumed at or before the interruption, after a rollback)."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r180_repair_bench_2 as S  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = '9305178'         # the commit that preregisters it
SHA256 = 'bfe117a72569dc14df2093af60f53c96574a2c9ad40af70f0547b012601e3097'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogues_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r180_repair_bench_2.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects.py'), S.DEFECTS_SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects2.py'), S.DEFECTS2_SHA256)

    def test_the_splits(self):
        self.assertEqual(sorted(S.DEV), sorted(d['id'] for d in DF.DEFECTS))
        self.assertEqual(S.HELDOUT, [d['id'] for d in DF2.DEFECTS])
        self.assertFalse(set(S.DEV) & set(S.HELDOUT))
        self.assertTrue(set(S.DEV_REHEARSAL) <= set(S.DEV))
        self.assertEqual({d['target'] for d in DF2.DEFECTS}, {'ttl', 'pq', 'ledger'})

    def test_every_held_out_defect_interrupts_every_job_and_the_verifier_tells_right_from_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == 1:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.ALL_SOURCES[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF2.source(did, TG.ALL_SOURCES) + '\n#\n')['accepted'], did)

    def test_the_fixed_constants(self):
        self.assertEqual(S.BUDGET, 300)
        self.assertEqual(S.ARMS, ('loop', 'loop_v1', 'nolocal', 'random', 'enum', 'retrieval'))
        self.assertEqual(S.COMPARATORS, ('loop_v1', 'nolocal', 'random', 'enum', 'retrieval'))
        self.assertEqual((S.JOB_SEEDS, S.JOB_VERSION), ((1, 2, 3), 2))
        self.assertEqual((S.SEARCH_SEED, S.CONTROL_SEED, S.FAULT_AT), (0, 4, 700))

    def test_the_sign_test(self):
        self.assertEqual(S.sign_test(0, 0), 1.0)
        self.assertAlmostEqual(S.sign_test(6, 0), 2 / 64)

    def test_repaired_allows_a_rollback_but_not_a_resume_past_the_interruption(self):
        ok = {'outcome': 'repaired', 'verified': True, 'promoted': True, 'finished': 'done', 'resumed_from': 400,
              'interrupted_at': 400}
        self.assertTrue(S.repaired(ok))
        self.assertTrue(S.repaired(dict(ok, resumed_from=0)))
        for k, v in (('verified', False), ('promoted', False), ('finished', 'failed'), ('resumed_from', 600),
                     ('resumed_from', None), ('outcome', 'false-repair')):
            self.assertFalse(S.repaired(dict(ok, **{k: v})), k)


if __name__ == '__main__':
    unittest.main()
