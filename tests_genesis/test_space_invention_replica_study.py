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

PREREGISTRATION = '56b414a'         # the commit that preregisters it
SHA256 = '3fa647254aadd6317a6f35d08672b71a2253101e467550d89c469a42aeba6097'


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


R186 = ROOT / 'evidence' / 'space_invention_b20r186'


class RecordB20R186(unittest.TestCase):
    """The record of SR-2c' (B20_R186) on its evidence: the script, the catalogue and the seeds; the verdict, the
    generations, the tables, the three questions with Holm's adjustment, the invented reach and the replication table
    recomputed; every admitted transformation admitted by a family it (and its parents) did not come from, in a probe
    row naming it; generation 1's admissions kept; the test vaults differ in their transformations only; every
    promoted source verified again; the 30 controls."""
    DIR = R186

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        cls.g1 = S._store(cls.DIR / 'genesis_g1', 'transforms.jsonl')
        cls.g2 = S._store(cls.DIR / 'genesis_g2', 'transforms.jsonl')
        p = cls.DIR / 'genesis_g2' / 'deriver.json'
        cls.deriver = json.loads(p.read_text()) if p.exists() else {}

    def test_the_script_the_catalogue_and_the_seeds(self):
        if self.DIR == R186:
            self.assertEqual(digest(ROOT / 'scripts/b20r186_space_invention_replica.py'), SHA256)
            self.assertEqual(self.result['script_sha256'], SHA256)
        self.assertEqual(self.result['defects6_sha256'], S.DEFECTS6_SHA256)
        self.assertEqual(self.result['job_seeds'], [14, 15, 16])
        self.assertEqual(self.result['seeds'], {'detect1': 31, 'probe1': 32, 'learn2': 33, 'probe2': 34, 'controls': 35})
        self.assertTrue(all(r['seed'] in (14, 15, 16, 31, 32, 33, 34, 35) for r in self.rows))

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.g1, self.g2, self.deriver)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'generations', 'obstacles', 'per_arm', 'questions',
                  'secondary', 'invented_reach', 'replication', 'replicated', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_transformation_was_admitted_by_a_family_it_did_not_come_from(self):
        for t in self.g2:
            if t['status'] != 'admitted':
                continue
            own = {t['provenance'].get('family')} | set(t['provenance'].get('derived_from_families', []))
            self.assertTrue(t['admitted_by'])
            self.assertFalse(own & set(t['admitted_by']), t['id'])
            probes = [x for x in self.rows if x['phase'].startswith('probe') and x['transform']
                      and x['transform']['id'] == t['id'] and x['transform']['after'] == 'admitted']
            self.assertTrue(any(S.repaired(x) and x['name'] in t['admitted_by'] for x in probes), t['id'])
        ids1 = {t['id'] for t in self.g1 if t['status'] == 'admitted'}
        ids2 = {t['id'] for t in self.g2 if t['status'] == 'admitted'}
        self.assertTrue(ids1 <= ids2)

    def test_the_test_vaults_differ_in_their_transformations_only(self):
        a, b = self.DIR / 'test_vault_g1', self.DIR / 'test_vault_g2'
        names = sorted(f.name for f in a.iterdir())
        self.assertEqual(names, sorted(f.name for f in b.iterdir()))
        for n in names:
            if n != 'transforms.jsonl':
                self.assertEqual((a / n).read_bytes(), (b / n).read_bytes(), n)
        self.assertEqual(S._store(a, 'transforms.jsonl'), self.g1)
        self.assertEqual(S._store(b, 'transforms.jsonl'), self.g2)

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
