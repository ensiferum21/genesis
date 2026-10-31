"""B20_R189 (`scripts/b20r189_verifier_adequacy.py`, blueprint WP-4, weakness C1): the verifier's mutation adequacy.
Its design: the script is the preregistered one; it covers every mutant of every component; the classes (killed,
gap, possibly equivalent) and the score from invented rows; a killed mutant and a correct source behave as they must."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r189_verifier_adequacy as S  # noqa: E402
from genesis.repairkernel import mutants as MU  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

PREREGISTRATION = 'ea06ce8'         # the commit that preregisters it
SHA256 = 'c9b35aecc5f45066690c357a7f68f6262fa2a0fe29ba2db548b631b63c8645f4'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_is_the_preregistered_one(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r189_verifier_adequacy.py'), SHA256)

    def test_it_covers_every_mutant_of_every_component(self):
        self.assertEqual(S.TARGETS, sorted(TG.KERNEL_SOURCES))
        n = sum(len(MU.enumerate_mutants(t, TG.KERNEL_SOURCES[t])) for t in S.TARGETS)
        self.assertEqual(n, 437)
        self.assertEqual((S.JOB_SEED, S.DIFF_WORKLOADS, S.DIFF_OPS, S.JOB_VERSION), (51, 20, 5000, 2))

    def test_the_classes_and_the_score(self):
        rows = [{'target': 'a', 'operator': 'delete', 'what': '1', 'job_interrupted': True, 'accepted': False,
                 'divergence': None, 'class': 'killed'},
                {'target': 'a', 'operator': 'constant', 'what': '2', 'job_interrupted': False, 'accepted': True,
                 'divergence': 'workload 3: Divergence', 'class': 'gap'},
                {'target': 'b', 'operator': 'constant', 'what': '3', 'job_interrupted': False, 'accepted': True,
                 'divergence': None, 'class': 'possibly-equivalent'}]
        got = S.analyse(rows)
        self.assertEqual((got['killed'], got['gaps'], got['possibly_equivalent'], got['mutation_score']), (1, 1, 1, 0.5))
        self.assertEqual(got['by_target']['a'], {'killed': 1, 'gap': 1, 'possibly-equivalent': 0})
        self.assertEqual(got['gap_list'][0]['what'], '2')

    def test_the_probe_passes_the_boundary_and_a_correct_source_is_accepted(self):
        # B20R188-BOUNDARY: a patch identical to the job's source changes no line and is always refused
        import genesis.repairkernel.bench as BN
        import genesis.repairkernel.verify as VF
        with tempfile.TemporaryDirectory() as d:
            job = BN.Job(Path(d) / 'j', 'bag', S.JOB_SEED, source=TG.KERNEL_SOURCES['bag'], version=2)
            job.run()
            v = VF.verify(job.dir, 'bag', S.JOB_SEED, job.n_ops, job.every, TG.KERNEL_SOURCES['bag'] + S.PROBE)
            self.assertTrue(v['accepted'], v['checks'])
            same = VF.verify(job.dir, 'bag', S.JOB_SEED, job.n_ops, job.every, TG.KERNEL_SOURCES['bag'])
            self.assertFalse(same['checks']['boundary']['ok'])

    def test_a_mutant_is_killed_and_the_correct_source_never_diverges(self):
        op, what, m = MU.enumerate_mutants('bag', TG.KERNEL_SOURCES['bag'])[0]
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(S.examine('bag', op, what, m, d)['class'], 'killed')
        self.assertIsNone(S.differential('bag', TG.KERNEL_SOURCES['bag']))


if __name__ == '__main__':
    unittest.main()
