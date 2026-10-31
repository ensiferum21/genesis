"""B20_R181 (SR-1a3, `scripts/b20r181_repair_bench_3.py`), the invented operators' benchmark: its design, checked
without running the loop on any held-out defect.
  * the script is the preregistered one (its digest), and so are the three catalogues;
  * the development defects are the first two catalogues, the held-out ones the third; every held-out defect
    interrupts every job and the verifier tells its correct source from its defective one;
  * the fixed constants: budget, arms (the frozen predecessor loop_v2 among them), comparators, the invention class,
    the twelve components, job seeds and version;
  * the sign test and the rule for 'repaired'."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r181_repair_bench_3 as S  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = '0e0ecc7'         # the commit that preregisters it
SHA256 = 'b0417fc5e7e7a9748a143eaa76cb6515fd9506a1831fe2446ae0c3b78cbb6dbb'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogues_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r181_repair_bench_3.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects.py'), S.DEFECTS_SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects2.py'), S.DEFECTS2_SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects3.py'), S.DEFECTS3_SHA256)

    def test_the_splits(self):
        self.assertEqual(sorted(S.DEV), sorted(d['id'] for d in DF.DEFECTS + DF2.DEFECTS))
        self.assertEqual(S.HELDOUT, [d['id'] for d in DF3.DEFECTS])
        self.assertTrue(set(S.INVENTION_CLASS) <= set(S.HELDOUT))
        self.assertTrue(set(S.INVENTION_CLASS_REHEARSAL) <= set(S.DEV_REHEARSAL))
        self.assertEqual(S.TARGETS, sorted(TG.SOURCES_ANY))
        self.assertFalse(set(S.DEV) & set(S.HELDOUT))
        self.assertTrue(set(S.DEV_REHEARSAL) <= set(S.DEV))
        self.assertEqual({d['target'] for d in DF3.DEFECTS}, {'lease', 'graph', 'bimap'})

    def test_every_held_out_defect_interrupts_every_job_and_the_verifier_tells_right_from_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == 1:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.SOURCES_ANY[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF3.source(did, TG.SOURCES_ANY) + '\n#\n')['accepted'], did)

    def test_the_fixed_constants(self):
        self.assertEqual(S.BUDGET, 300)
        self.assertEqual(S.ARMS, ('loop', 'loop_v2', 'nolocal', 'random', 'enum'))
        self.assertEqual(S.COMPARATORS, ('loop_v2', 'nolocal', 'random', 'enum'))
        self.assertEqual(S.INVENTION_CLASS, ['E1', 'E2', 'N1', 'N2'])
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
