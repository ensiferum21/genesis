"""B20_R178 (SR-1, `scripts/b20r178_repair_bench.py`), the first self-repair benchmark: its design, checked without
running the loop on any held-out defect.
  * the script is the preregistered one (its digest), and so is the sealed defect catalogue;
  * its development and held-out lists are the catalogue's, disjoint, and every held-out defect interrupts its jobs;
  * the fixed constants: budget, arms, comparators, job seeds, controls;
  * the sign test and the rule for 'repaired' (verified, promoted, resumed where it was interrupted, finished);
  * the verdict's precedence (isolation, then controls, then the milestone) on synthetic inputs is in the script's
    `main`; the rehearsal (every phase on development defects) is its dry run, kept with the evidence."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r178_repair_bench as S  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402

PREREGISTRATION = None              # the commit that preregisters it (filled in by the next commit)
SHA256 = None


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogue_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r178_repair_bench.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects.py'), S.DEFECTS_SHA256)

    def test_the_splits_are_the_catalogues_and_disjoint(self):
        self.assertEqual(S.DEV, [d['id'] for d in DF.DEFECTS if d['split'] == 'dev'])
        self.assertEqual(S.HELDOUT, [d['id'] for d in DF.DEFECTS if d['split'] == 'heldout'])
        self.assertFalse(set(S.DEV) & set(S.HELDOUT))
        self.assertEqual((len(S.DEV), len(S.HELDOUT)), (8, 13))

    def test_every_held_out_defect_interrupts_every_job(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}')
                    self.assertEqual(job.run()['status'], 'failed', (did, s))

    def test_the_fixed_constants(self):
        self.assertEqual(S.BUDGET, 300)
        self.assertEqual(S.ARMS, ('loop', 'novault', 'nolocal', 'random', 'enum', 'retrieval'))
        self.assertEqual(S.COMPARATORS, ('nolocal', 'random', 'enum', 'retrieval'))
        self.assertEqual(S.JOB_SEEDS, (1, 2, 3))
        self.assertEqual((S.SEARCH_SEED, S.CONTROL_SEED, S.FAULT_AT), (0, 4, 700))

    def test_the_sign_test(self):
        self.assertEqual(S.sign_test(0, 0), 1.0)
        self.assertAlmostEqual(S.sign_test(6, 0), 2 / 64)
        self.assertAlmostEqual(S.sign_test(5, 0), 2 / 32)
        self.assertEqual(S.sign_test(3, 3), 1.0)
        self.assertAlmostEqual(S.sign_test(9, 1), S.sign_test(1, 9))

    def test_repaired_means_verified_promoted_resumed_where_interrupted_and_finished(self):
        ok = {'outcome': 'repaired', 'verified': True, 'promoted': True, 'finished': 'done', 'resumed_from': 400,
              'interrupted_at': 400}
        self.assertTrue(S.repaired(ok))
        for k, v in (('verified', False), ('promoted', False), ('finished', 'failed'), ('resumed_from', 0),
                     ('outcome', 'false-repair')):
            self.assertFalse(S.repaired(dict(ok, **{k: v})), k)


if __name__ == '__main__':
    unittest.main()
