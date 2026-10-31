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

PREREGISTRATION = '884713e'         # the commit that preregisters it
SHA256 = '72275f94e3e4f034d367f5bcb49d7baeceb402467ab10b4743480fb6aeff7572'


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


R182 = ROOT / 'evidence' / 'rule_invention_b20r182'


class RecordB20R182(unittest.TestCase):
    """The record of SR-2a (B20_R182) on its evidence: the script and the catalogue; the verdicts and tables recomputed
    from the rows, the isolation report and Genesis's frozen library; every admitted rule admitted by a verified
    repair of another family, in a probe row that names it; every promoted component source verified again; the
    30 controls."""
    DIR = R182

    @classmethod
    def setUpClass(cls):
        import json
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        lib = cls.DIR / 'genesis_library'
        cls.library = [json.loads(x) for x in (lib / 'rules.jsonl').read_text().splitlines() if x.strip()] \
            if (lib / 'rules.jsonl').exists() else []
        cls.inventor = json.loads((lib / 'inventor.json').read_text()) if (lib / 'inventor.json').exists() else {}

    def test_the_script_and_the_catalogue(self):
        if self.DIR == R182:
            self.assertEqual(digest(ROOT / 'scripts/b20r182_rule_invention.py'), SHA256)
        self.assertEqual(self.result['defects4_sha256'], S.DEFECTS4_SHA256)

    def test_the_verdicts_recompute(self):
        import json
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.library, self.inventor)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'invention', 'obstacles', 'milestone',
                  'milestone_obstacles', 'per_arm', 'comparison', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_rule_was_admitted_by_another_familys_verified_repair(self):
        for r in self.library:
            if r['status'] != 'admitted':
                continue
            self.assertTrue(r['admitted_by'])
            self.assertNotIn(r['provenance']['family'], r['admitted_by'])
            probes = [x for x in self.rows if x['phase'].startswith('admit') and x['rule'] and x['rule']['id'] == r['id']
                      and x['rule']['after'] == 'admitted']
            self.assertTrue(probes, r['id'])
            self.assertTrue(any(S.repaired(x) and x['name'] in r['admitted_by'] for x in probes), r['id'])

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 'controls']
        self.assertEqual(len(controls), 30)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])


if __name__ == '__main__':
    unittest.main()
