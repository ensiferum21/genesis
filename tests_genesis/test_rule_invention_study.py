"""B20_R182 (SR-2a, `scripts/b20r182_rule_invention.py`): Genesis inventing its own repair rules. Its design,
checked without running the loop on any held-out defect:
  * the script is the preregistered one (its digest), and so is the fourth sealed catalogue;
  * the curriculum is the three earlier catalogues (development data), the held-out set the fourth; disjoint;
  * every held-out defect interrupts every job and the verifier tells its correct source from its defective one;
    the homologue flags are as computed when the catalogue was sealed;
  * the fixed constants (budgets, arms, comparators, the fifteen components, job seeds and version);
  * the sign test."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r182_rule_invention as S  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import defects4 as DF4  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = None              # the commit that preregisters it (filled in by the next commit)
SHA256 = None


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogue_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r182_rule_invention.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects4.py'), S.DEFECTS4_SHA256)

    def test_the_curriculum_and_the_held_out_set(self):
        self.assertEqual(S.CURRICULUM, [d['id'] for d in DF.DEFECTS + DF2.DEFECTS + DF3.DEFECTS])
        self.assertEqual(S.HELDOUT, [d['id'] for d in DF4.DEFECTS])
        self.assertFalse(set(S.CURRICULUM) & set(S.HELDOUT))
        self.assertTrue(set(S.CURRICULUM_REHEARSAL) <= set(S.CURRICULUM))
        self.assertTrue(set(S.HELDOUT_REHEARSAL) <= set(S.CURRICULUM))
        self.assertEqual(S.TARGETS, sorted(TG.KERNEL_SOURCES))
        self.assertEqual({d['target'] for d in DF4.DEFECTS}, {'stock', 'calendar', 'bag'})
        self.assertEqual([d['id'] for d in DF4.DEFECTS if DF4.homologue(d['id'], TG.KERNEL_SOURCES)],
                         ['X1', 'X4', 'C2'])

    def test_every_held_out_defect_interrupts_every_job_and_the_verifier_tells_right_from_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == 1:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.KERNEL_SOURCES[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF4.source(did, TG.KERNEL_SOURCES) + '\n#\n')['accepted'])

    def test_the_fixed_constants(self):
        self.assertEqual((S.BUDGET, S.DREAM_BUDGET, S.PROBE_BUDGET), (300, 1000, 120))
        self.assertEqual(S.ARMS, ('loop', 'loop_v3', 'dream_online', 'enum'))
        self.assertEqual(S.COMPARATORS, ('loop_v3', 'dream_online', 'enum'))
        self.assertEqual((S.JOB_SEEDS, S.JOB_VERSION), ((1, 2, 3), 2))
        self.assertEqual((S.SEARCH_SEED, S.CONTROL_SEED, S.FAULT_AT), (0, 4, 700))

    def test_the_sign_test(self):
        self.assertEqual(S.sign_test(0, 0), 1.0)
        self.assertAlmostEqual(S.sign_test(6, 0), 2 / 64)


if __name__ == '__main__':
    unittest.main()
