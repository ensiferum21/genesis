"""B20_R183 (SR-2b, `scripts/b20r183_rule_invention_replica.py`): B20_R182 repeated with fresh seeds, plus the arm
that tests step 6. Its design, checked without running the loop on any held-out defect:
  * the script is the preregistered one (its digest), and so is the fourth sealed catalogue;
  * it is B20_R182's script but for the seeds, the added 'dream' arm, the step-6 comparison and the replication
    table (the rest of the file is the same text);
  * the seeds are all fresh (none is one of B20_R182's job or search seeds);
  * every held-out defect interrupts every job of the new seeds, and the verifier tells its correct source from its
    defective one;
  * B20_R182's outcomes, the ones it is compared with, are the recorded ones;
  * the step-6 rule on invented rows."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r182_rule_invention as S0  # noqa: E402
import b20r183_rule_invention_replica as S  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects4 as DF4  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = '229ca10'         # the commit that preregisters it
SHA256 = '3ca48cda3d542bd090084e4afa3fd28ae603844fb248d3f02b51498709c65728'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def row(rep, first):
    return {'outcome': 'repaired' if rep else 'not-repaired', 'verified': rep, 'promoted': rep,
            'finished': 'done' if rep else None, 'resumed_from': 5 if rep else None, 'interrupted_at': 9,
            'first_solution': first}


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogue_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r183_rule_invention_replica.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects4.py'), S.DEFECTS4_SHA256)
        self.assertEqual(S.DEFECTS4_SHA256, S0.DEFECTS4_SHA256)

    def test_it_is_b20r182_but_for_the_seeds_and_the_added_arm(self):
        for k in ('CURRICULUM', 'HELDOUT', 'CURRICULUM_REHEARSAL', 'HELDOUT_REHEARSAL', 'TARGETS', 'COMPARATORS',
                  'JOB_VERSION', 'BUDGET', 'DREAM_BUDGET', 'PROBE_BUDGET', 'FAULT_AT', 'TIMEOUT', 'BLOCKED',
                  'RESEARCH_MUST_FAIL', 'EXECUTOR_MUST_FAIL'):
            self.assertEqual(getattr(S, k), getattr(S0, k), k)
        self.assertEqual(S.ARMS, S0.ARMS + ('dream',))
        for f in ('repaired', 'isolation_passes', 'control_passes', 'sign_test', '_lib_state'):
            self.assertEqual(getattr(S, f).__code__.co_code, getattr(S0, f).__code__.co_code, f)
        a = (ROOT / 'scripts/b20r182_rule_invention.py').read_text()
        b = (ROOT / 'scripts/b20r183_rule_invention_replica.py').read_text()
        body = lambda t, name: t[t.index(f'def {name}('):].split('\n\n\n')[0]  # noqa: E731
        self.assertEqual(body(a, 'run_episode'), body(b, 'run_episode'))

    def test_the_seeds_are_fresh(self):
        self.assertEqual((S.JOB_SEEDS, S.DETECT_SEED, S.ADMIT_SEED, S.SEARCH_SEED, S.CONTROL_SEED),
                         ((6, 7, 8), 4, 5, 1, 9))
        used = set(S0.JOB_SEEDS) | {1, 2}                  # B20_R182's test jobs, its detection and probe jobs
        self.assertFalse(set(S.JOB_SEEDS) & used)
        self.assertFalse({S.DETECT_SEED, S.ADMIT_SEED} & used)
        self.assertNotEqual(S.SEARCH_SEED, S0.SEARCH_SEED)
        self.assertNotEqual(S.CONTROL_SEED, S0.CONTROL_SEED)

    def test_every_held_out_defect_interrupts_every_new_job_and_the_verifier_tells_right_from_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == S.JOB_SEEDS[0]:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.KERNEL_SOURCES[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF4.source(did, TG.KERNEL_SOURCES) + '\n#\n')['accepted'])

    def test_b20r182s_outcomes_are_the_recorded_ones(self):
        p = ROOT / 'evidence/rule_invention_b20r182/result.json'
        if not p.exists():
            self.skipTest('B20_R182 not recorded in this tree')
        r = json.loads(p.read_text())
        self.assertEqual(S.B20R182['verdict'], r['verdict'])
        self.assertEqual(S.B20R182['comparison'], {k: v['verdict'] for k, v in r['comparison'].items()})
        self.assertEqual(S.B20R182['repaired'], {k: v['repaired'] for k, v in r['per_arm'].items()})

    def test_the_step_6_rule(self):
        same = [(row(True, 10), row(True, 10))] * 9
        self.assertEqual(S.compare_inventor(same)['verdict'], 'NO_DIFFERENCE_SHOWN')
        more = [(row(True, 50), row(False, None))] * 6
        self.assertEqual(S.compare_inventor(more)['verdict'], 'INVENTOR_IMPROVED')
        self.assertEqual(S.compare_inventor([(y, x) for x, y in more])['verdict'], 'INVENTOR_WORSE')
        faster = [(row(True, 5), row(True, 40))] * 6
        got = S.compare_inventor(faster)
        self.assertEqual((got['verdict'], got['dream_earlier'], got['mean_first']), ('INVENTOR_IMPROVED', 6, [5.0, 40.0]))
        self.assertEqual(S.compare_inventor([(y, x) for x, y in faster])['verdict'], 'INVENTOR_WORSE')
        # the repair count decides first: one more repair is not significant, so the speed decides
        mixed = [(row(True, 5), row(True, 40))] * 6 + [(row(False, None), row(True, 3))]
        self.assertEqual(S.compare_inventor(mixed)['verdict'], 'INVENTOR_IMPROVED')
        self.assertEqual(S.compare_inventor([(row(True, None), row(True, 4))])['both_repaired'], 0)


if __name__ == '__main__':
    unittest.main()
