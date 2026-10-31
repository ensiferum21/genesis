"""B20_R187 (SR-2d, `scripts/b20r187_third_generation.py`): does the inventor's improvement compound? Its design,
checked without running the loop on any held-out defect:
  * the script is the preregistered one (its digest), and the seventh catalogue is the sealed one;
  * the curriculum is B20_R185's; the held-out mutants are new, and every seed is fresh;
  * B20_R185's constants, functions and episode runner, and its first two generations, unchanged;
  * the arms (the generation of each arm's transformations), the questions, the third generation's probe;
  * every held-out mutant interrupts every job and the verifier tells right from wrong."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r185_space_invention as S0  # noqa: E402
import b20r186_space_invention_replica as S1  # noqa: E402
import b20r187_make_mutant_catalogue as MK7  # noqa: E402
import b20r187_third_generation as S  # noqa: E402
from genesis.repair import loop as LP  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects7 as DF7  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

PREREGISTRATION = '0e56949'         # the commit that preregisters it
SHA256 = 'e2f3473716639e77da543098ec3a78a2bed4b647b41468e553d67d931b631f7d'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Design(unittest.TestCase):
    def test_the_script_and_the_catalogue_are_the_preregistered_ones(self):
        if SHA256:
            self.assertEqual(digest(ROOT / 'scripts/b20r187_third_generation.py'), SHA256)
        self.assertEqual(digest(ROOT / 'src/genesis/repairkernel/defects7.py'), S.DEFECTS7_SHA256)

    def test_the_curriculum_the_mutants_and_the_seeds(self):
        self.assertEqual(S.CURRICULUM, S0.CURRICULUM)
        self.assertEqual(S.HELDOUT, [f'Z{i:02d}' for i in range(1, 37)])
        self.assertFalse(set(S.HELDOUT) & (set(S0.HELDOUT) | set(S1.HELDOUT) | set(S.CURRICULUM)))
        before = MK7.excluded()
        for d in DF7.DEFECTS:
            self.assertNotIn((d['target'], DF7.source(d['id'], TG.KERNEL_SOURCES)), before, d['id'])
        old = set()
        for m in (S0, S1):
            old |= set(m.JOB_SEEDS) | set(m.SEEDS.values()) | {m.SEARCH_SEED}
        self.assertFalse((set(S.JOB_SEEDS) | set(S.SEEDS.values()) | {S.SEARCH_SEED}) & old)
        self.assertEqual(S.JOB_SEEDS, MK7.JOB_SEEDS)

    def test_b20r185s_parts_unchanged(self):
        for k in ('CURRICULUM_REHEARSAL', 'HELDOUT_REHEARSAL', 'TARGETS', 'JOB_VERSION', 'BUDGET', 'DREAM_BUDGET',
                  'PROBE_BUDGET', 'FAULT_AT', 'SLICE_S', 'TIMEOUT', 'BLOCKED', 'RESEARCH_MUST_FAIL', 'EXECUTOR_MUST_FAIL'):
            self.assertEqual(getattr(S, k), getattr(S0, k), k)
        for f in ('repaired', 'isolation_passes', 'control_passes', 'sign_test', 'holm', '_store', '_counts', 'freeze'):
            self.assertEqual(getattr(S, f).__code__.co_code, getattr(S0, f).__code__.co_code, f)
        a = (ROOT / 'scripts/b20r185_space_invention.py').read_text()
        b = (ROOT / 'scripts/b20r187_third_generation.py').read_text()
        body = lambda t, name: t[t.index(f'def {name}('):].split('\n\n\n')[0]  # noqa: E731
        self.assertEqual(body(a, 'run_episode'), body(b, 'run_episode'))
        gen1 = lambda t: t[t.index('    # generation 1'):t.index("    freeze(genesis, out / 'genesis_g1')")]  # noqa: E731
        self.assertEqual(gen1(a), gen1(b))

    def test_the_arms_the_questions_and_the_third_generation(self):
        self.assertEqual(S.ARMS, dict(S0.ARMS, analogy_g3=('analogy', 'g3')))
        self.assertEqual({q: v[:2] for q, v in S.QUESTIONS.items()},
                         {'P1': ('analogy_g3', 'analogy_g2'), 'P2': ('analogy_g2', 'analogy_g1'),
                          'P3': ('analogy_g3', 'dream_online')})
        self.assertEqual(S.QUESTIONS['P2'], S0.QUESTIONS['P2'])
        self.assertIn('probe_t3', LP.PROBE_T)
        self.assertIn('probe_t3', LP.DIAG)
        src = (ROOT / 'src/genesis/repair/loop.py').read_text()
        self.assertIn("AN.derive([t for t in tl.admitted() if t.get('generation') in (1, 2)], generation=3)", src)

    def test_every_held_out_mutant_interrupts_every_job_and_the_verifier_tells_right_from_wrong(self):
        with tempfile.TemporaryDirectory() as d:
            for did in S.HELDOUT:
                for s in S.JOB_SEEDS:
                    job, _ = BN.make(did, s, Path(d) / f'{did}-{s}', version=S.JOB_VERSION)
                    self.assertEqual(job.run()['status'], 'failed', (did, s))
                    if s == S.JOB_SEEDS[0]:
                        args = (job.dir, job.target, s, job.n_ops, job.every)
                        self.assertTrue(VF.verify(*args, TG.KERNEL_SOURCES[job.target])['accepted'], did)
                        self.assertFalse(VF.verify(*args, DF7.source(did, TG.KERNEL_SOURCES))['accepted'], did)


import json  # noqa: E402

R187 = ROOT / 'evidence' / 'third_generation_b20r187'


class RecordB20R187(unittest.TestCase):
    """The record of SR-2d (B20_R187) on its evidence: the script, the catalogue and the seeds; the verdict, the three
    generations, the tables, the questions with Holm's adjustment and the invented reach recomputed; every admitted
    transformation admitted by a family it (and its parents) did not come from, in a probe row naming it; each
    generation's admissions kept in the next; the test vaults differ in their transformations only; every promoted
    source verified again; the 30 controls."""
    DIR = R187

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        cls.g = {g: S._store(cls.DIR / f'genesis_{g}', 'transforms.jsonl') for g in ('g1', 'g2', 'g3')}
        p = cls.DIR / 'genesis_g3' / 'deriver.json'
        cls.deriver = json.loads(p.read_text()) if p.exists() else {}

    def test_the_script_the_catalogue_and_the_seeds(self):
        if self.DIR == R187:
            self.assertEqual(digest(ROOT / 'scripts/b20r187_third_generation.py'), SHA256)
            self.assertEqual(self.result['script_sha256'], SHA256)
        self.assertEqual(self.result['defects7_sha256'], S.DEFECTS7_SHA256)
        self.assertEqual(self.result['job_seeds'], [17, 18, 19])
        self.assertTrue(all(r['seed'] in set(S.JOB_SEEDS) | set(S.SEEDS.values()) for r in self.rows))

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.g['g1'], self.g['g2'], self.g['g3'],
                        self.deriver)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'generations', 'obstacles', 'per_arm', 'questions',
                  'secondary', 'invented_reach', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_transformation_was_admitted_by_a_family_it_did_not_come_from(self):
        for t in self.g['g3']:
            if t['status'] != 'admitted':
                continue
            own = {t['provenance'].get('family')} | set(t['provenance'].get('derived_from_families', []))
            self.assertTrue(t['admitted_by'])
            self.assertFalse(own & set(t['admitted_by']), t['id'])
            probes = [x for x in self.rows if x['phase'].startswith('probe') and x['transform']
                      and x['transform']['id'] == t['id'] and x['transform']['after'] == 'admitted']
            self.assertTrue(any(S.repaired(x) and x['name'] in t['admitted_by'] for x in probes), t['id'])
        ids = {g: {t['id'] for t in self.g[g] if t['status'] == 'admitted'} for g in self.g}
        self.assertTrue(ids['g1'] <= ids['g2'] <= ids['g3'])

    def test_the_test_vaults_differ_in_their_transformations_only(self):
        vs = {g: self.DIR / f'test_vault_{g}' for g in ('g1', 'g2', 'g3')}
        names = sorted(f.name for f in vs['g3'].iterdir())
        for g, v in vs.items():
            self.assertEqual(sorted(f.name for f in v.iterdir()), names, g)
            for n in names:
                if n != 'transforms.jsonl':
                    self.assertEqual((v / n).read_bytes(), (vs['g3'] / n).read_bytes(), (g, n))
            self.assertEqual(S._store(v, 'transforms.jsonl'), self.g[g])

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
