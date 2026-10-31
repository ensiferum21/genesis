"""B20_R186 (SR-2c', `scripts/b20r186_space_invention_replica.py`): B20_R185 repeated with fresh seeds on a fresh draw
of random mutants. Its design, checked without running the loop on any held-out defect:
  * the script is the preregistered one (its digest), and the sixth catalogue is the sealed one;
  * it is B20_R185's script but for the catalogue, the seeds and the replication table: the constants, the functions
    and the episode runner are the same;
  * every seed is fresh, and the held-out mutants are disjoint from every earlier catalogue's;
  * every held-out mutant interrupts every job and the verifier tells right from wrong;
  * B20_R185's verdicts, the ones it is compared with, are the recorded ones."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r185_space_invention as S0  # noqa: E402
import b20r186_make_mutant_catalogue as MK6  # noqa: E402
import b20r186_space_invention_replica as S  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects6 as DF6  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = ''                # the commit that preregisters it
SHA256 = ''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogue_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r186_space_invention_replica.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects6.py'), S.DEFECTS6_SHA256)

    def test_it_is_b20r185_but_for_the_catalogue_the_seeds_and_the_replication(self):
        for k in ('CURRICULUM', 'CURRICULUM_REHEARSAL', 'HELDOUT_REHEARSAL', 'TARGETS', 'ARMS', 'QUESTIONS',
                  'SECONDARY', 'JOB_VERSION', 'BUDGET', 'DREAM_BUDGET', 'PROBE_BUDGET', 'FAULT_AT', 'SLICE_S',
                  'TIMEOUT', 'BLOCKED', 'RESEARCH_MUST_FAIL', 'EXECUTOR_MUST_FAIL'):
            self.assertEqual(getattr(S, k), getattr(S0, k), k)
        for f in ('repaired', 'isolation_passes', 'control_passes', 'sign_test', 'holm', '_store', '_counts',
                  'freeze', 'test_vault'):
            self.assertEqual(getattr(S, f).__code__.co_code, getattr(S0, f).__code__.co_code, f)
        a = (ROOT / 'scripts/b20r185_space_invention.py').read_text()
        b = (ROOT / 'scripts/b20r186_space_invention_replica.py').read_text()
        body = lambda t, name: t[t.index(f'def {name}('):].split('\n\n\n')[0]  # noqa: E731
        self.assertEqual(body(a, 'run_episode'), body(b, 'run_episode'))
        cycle = lambda t: t[t.index('    # generation 1'):t.index('    result = dict(meta')]  # noqa: E731
        self.assertEqual(cycle(a), cycle(b))                        # the invention cycle and the test, unchanged
        self.assertGreater(len(cycle(a)), 1500)

    def test_every_seed_is_fresh_and_the_mutants_are_new(self):
        old = set(S0.JOB_SEEDS) | set(S0.SEEDS.values()) | {S0.SEARCH_SEED}
        self.assertFalse((set(S.JOB_SEEDS) | set(S.SEEDS.values())) & old)
        self.assertNotEqual(S.SEARCH_SEED, S0.SEARCH_SEED)
        self.assertEqual(S.JOB_SEEDS, MK6.JOB_SEEDS)
        self.assertEqual(S.HELDOUT, [f'V{i:02d}' for i in range(1, 37)])
        self.assertFalse(set(S.HELDOUT) & (set(S0.HELDOUT) | set(S.CURRICULUM)))
        before = MK6.excluded()
        for d in DF6.DEFECTS:
            self.assertNotIn((d['target'], DF6.source(d['id'], TG.KERNEL_SOURCES)), before, d['id'])

    def test_every_held_out_mutant_interrupts_every_job_and_the_verifier_tells_right_from_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == S.JOB_SEEDS[0]:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.KERNEL_SOURCES[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF6.source(did, TG.KERNEL_SOURCES))['accepted'], did)

    def test_b20r185s_verdicts_are_the_recorded_ones(self):
        p = ROOT / 'evidence/space_invention_b20r185/result.json'
        if not p.exists():
            self.skipTest('B20_R185 not recorded in this tree')
        r = json.loads(p.read_text())
        self.assertEqual(S.B20R185, {'verdict': r['verdict'], **{q: v['verdict'] for q, v in r['questions'].items()}})


if __name__ == '__main__':
    unittest.main()
