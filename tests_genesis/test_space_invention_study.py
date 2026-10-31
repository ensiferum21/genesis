"""B20_R185 (SR-2c, `scripts/b20r185_space_invention.py`): Genesis grows its own repair space. Its design, checked
without running the loop on any held-out defect:
  * the script is the preregistered one (its digest), and the fifth catalogue is the sealed one;
  * the curriculum is the four hand-written catalogues, the held-out set the fifth (random mutants); disjoint; the
    rehearsal's sets are development defects;
  * the test's job seeds are the ones the catalogue's real obstacles were drawn for;
  * the fixed constants: budgets, seeds, arms (and the generation of each arm's transformations), the questions;
  * the isolation it requires covers every catalogue, and the probe measures it;
  * the loop has the arms the study names;
  * the sign test and Holm's adjustment."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r185_make_mutant_catalogue as MK  # noqa: E402
import b20r185_space_invention as S  # noqa: E402
from genesis.repair import loop as LP  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import defects4 as DF4  # noqa: E402
from genesis.repairkernel import defects5 as DF5  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = '4f399e8'         # the commit that preregisters it
SHA256 = 'efab4a990a50f4bf7307098019f73874750aa86dae94f270415fb87a5e60b8d6'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogue_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r185_space_invention.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects5.py'), S.DEFECTS5_SHA256)

    def test_the_curriculum_and_the_held_out_set(self):
        self.assertEqual(S.CURRICULUM, [d['id'] for d in DF.DEFECTS + DF2.DEFECTS + DF3.DEFECTS + DF4.DEFECTS])
        self.assertEqual(len(S.CURRICULUM), 57)
        self.assertEqual(S.HELDOUT, [f'Q{i:02d}' for i in range(1, 25)])
        self.assertFalse(set(S.CURRICULUM) & set(S.HELDOUT))
        self.assertTrue(set(S.CURRICULUM_REHEARSAL) <= set(S.CURRICULUM))
        self.assertTrue(set(S.HELDOUT_REHEARSAL) <= set(S.CURRICULUM))
        self.assertFalse(set(S.CURRICULUM_REHEARSAL) & set(S.HELDOUT_REHEARSAL))
        self.assertEqual(S.TARGETS, sorted(TG.KERNEL_SOURCES))

    def test_every_held_out_defect_interrupts_every_job_and_the_verifier_tells_right_from_wrong(self):
        self.assertEqual(S.JOB_SEEDS, MK.JOB_SEEDS)
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == S.JOB_SEEDS[0]:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.KERNEL_SOURCES[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF5.source(did, TG.KERNEL_SOURCES))['accepted'], did)

    def test_the_fixed_constants(self):
        self.assertEqual((S.BUDGET, S.DREAM_BUDGET, S.PROBE_BUDGET, S.SLICE_S), (300, 1000, 200, 6600))
        self.assertEqual(S.ARMS, {'loop_v3': ('loop_v3', 'g1'), 'analogy_g1': ('analogy', 'g1'),
                                  'analogy_g2': ('analogy', 'g2'), 'dream_online': ('dream_online', 'g1'),
                                  'enum': ('enum', None)})
        self.assertEqual({q: v[:2] for q, v in S.QUESTIONS.items()},
                         {'P1': ('analogy_g1', 'loop_v3'), 'P2': ('analogy_g2', 'analogy_g1'),
                          'P3': ('analogy_g2', 'dream_online')})
        self.assertEqual(S.SEEDS, {'detect1': 21, 'probe1': 22, 'learn2': 23, 'probe2': 24, 'controls': 25})
        self.assertFalse(set(S.SEEDS.values()) & set(S.JOB_SEEDS))
        self.assertEqual((S.JOB_SEEDS, S.JOB_VERSION, S.SEARCH_SEED, S.FAULT_AT), ((11, 12, 13), 2, 2, 700))

    def test_the_isolation_covers_every_catalogue(self):
        self.assertIn('read any defect catalogue (own view)', S.RESEARCH_MUST_FAIL)
        self.assertIn('read any defect catalogue (own view)', S.EXECUTOR_MUST_FAIL)
        self.assertIn("attempt('read any defect catalogue (own view)'", FD.ISOLATION_PROBE)
        self.assertIn('defects5.py', FD.CATALOGUES)

    def test_the_loop_has_the_arms(self):
        for a in ('v3learn', 'analogy', 'probe_t', 'probe_t2', 'dream', 'dream_online', 'loop_v3'):
            self.assertIn(a, LP.DIAG)
        self.assertEqual(LP.LEARN_T, {'v3learn': 1, 'dream': 1, 'analogy': 2})
        self.assertEqual(LP.PROBE_T, ('probe_t', 'probe_t2'))

    def test_the_sign_test_and_holm(self):
        self.assertEqual(S.sign_test(0, 0), 1.0)
        self.assertAlmostEqual(S.sign_test(6, 0), 2 / 64)
        self.assertEqual(S.holm({'a': 0.01, 'b': 0.04, 'c': 0.03}), {'a': 0.03, 'b': 0.06, 'c': 0.06})
        self.assertEqual(S.holm({'a': 0.5, 'b': 0.6}), {'a': 1.0, 'b': 1.0})

    def test_a_pause_stops_before_an_episode_and_keeps_the_rows(self):
        with tempfile.TemporaryDirectory() as d:
            rows = S.Rows(Path(d) / 'rows.jsonl', deadline=0)
            with self.assertRaises(S.Pause):
                S.run_episode(Path(d), rows, 'k/1', 'p', 'defect', 'E3', 1, 'loop_v3')
            self.assertFalse((Path(d) / 'rows.jsonl').exists())
            (Path(d) / 'rows.jsonl').write_text(json.dumps({'key': 'k/1', 'x': 1}) + '\n')
            rows = S.Rows(Path(d) / 'rows.jsonl', deadline=0)
            self.assertEqual(S.run_episode(Path(d), rows, 'k/1', 'p', 'defect', 'E3', 1, 'loop_v3')['x'], 1)


if __name__ == '__main__':
    unittest.main()
