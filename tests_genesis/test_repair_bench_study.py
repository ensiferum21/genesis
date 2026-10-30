"""B20_R178 (SR-1, `scripts/b20r178_repair_bench.py`), the first self-repair benchmark: its design, checked without
running the loop on any held-out defect.
  * the script is the preregistered one (its digest), and so is the sealed defect catalogue;
  * its development and held-out lists are the catalogue's, disjoint, and every held-out defect interrupts its jobs;
  * the fixed constants: budget, arms, comparators, job seeds, controls;
  * the sign test and the rule for 'repaired' (verified, promoted, resumed where it was interrupted, finished);
  * the verdict's precedence (isolation, then controls, then the milestone) on synthetic inputs is in the script's
    `main`; the rehearsal (every phase on development defects) is its dry run, kept with the evidence."""
import hashlib
import json
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

PREREGISTRATION = '0e5d46f'         # the commit that preregisters it
SHA256 = 'c259d0e6972f7f4d7f9fbdefd883afdfc3d35247a5b50aef189b4b4b25e81468'


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


R178 = ROOT / 'evidence' / 'repair_bench_b20r178'


class RecordB20R178(unittest.TestCase):
    """The record of SR-1a (B20_R178) on its evidence: the script and the sealed catalogue; the verdicts and tables
    recomputed from the rows and the isolation report; every promoted component source verified again by the kernel
    verifier on a rebuilt job; no control proposed or changed anything; nothing outside a job's component promoted."""
    DIR = R178

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())

    def test_the_script_and_the_catalogue(self):
        if self.DIR == R178:
            self.assertEqual(digest(ROOT / 'scripts/b20r178_repair_bench.py'), SHA256)
        self.assertEqual(self.result['defects_sha256'], S.DEFECTS_SHA256)

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.result['retention']['vault_entries_dev'],
                        self.result['retention']['vault_entries_grown'])
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'obstacles', 'milestone_obstacles', 'per_arm',
                  'comparison', 'reuse', 'retention', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_promoted_source_verifies_again(self):
        from genesis.repairkernel import verify as VF
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'))
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 2]
        self.assertEqual(len(controls), 12)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])


if __name__ == '__main__':
    unittest.main()
