"""B20_R57: the hardness-enriched sum-free certification study. Design: B20_R56's settings, witness, budget and
separation with fresh seeds; the screen runs route a alone for 20 s, includes a candidate only when a does not certify
it, stops at 20 per setting (or 80 candidates), saves every outcome and resumes from it; the primary verdict is
B20_R56's rule and the secondary bound rule is as preregistered.

Record (B20_R57): the screen's included hosts are the script's candidates and route a's 20 s outcome decided each;
both verdicts recompute from the rows (CERTIFICATION_UTILITY: 14 vs 22, 0/8, p 0.0039, saving +6.02 s [2.50, 9.88];
BOUND_UTILITY: +6.875 [5.375, 8.475]); every witness is sum-free; the kept certificates re-check VALID."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r56_sf_tree_certification as R56  # noqa: E402
import b20r57_sf_hard_certification as M  # noqa: E402


class Design(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(M.SETTINGS, R56.SETTINGS)
        self.assertEqual((M.SECONDS, M.WITNESS_S, M.SEPARATION), (R56.SECONDS, R56.WITNESS_S, R56.SEPARATION))
        self.assertEqual((M.SEEDS, M.PER, M.MAX_CANDIDATES, M.SCREEN_S, M.BOUND_MIN),
                         ((20265701, 20265711), 20, 80, 20, 2))
        self.assertFalse(set(M.SEEDS) & set(R56.SEEDS))
        r56 = {tuple(t['elements']) for t in R56.make_hosts()}
        for seed, (N, p) in zip(M.SEEDS, M.SETTINGS):
            for i in range(M.MAX_CANDIDATES):
                self.assertNotIn(tuple(M.candidate(seed, i, N, p)['elements']), r56)

    def test_the_screen_runs_route_a_only_and_resumes(self):
        calls = []

        def fake_mip(task, seconds):
            return {'witness': [task['elements'][-1]], 'optimal': False, 'wall_s': 0.0, 'value': 1}

        def fake_tree(task, w, reg, seconds, **kw):
            calls.append((task['task_id'], seconds, bool(reg['patterns']), kw))
            hard = int(task['task_id'].rsplit('_', 1)[1]) % 3 == 0
            return {'lower': 1, 'upper': 2 if hard else 1, 'wall_s': 0.1}
        reg = {'schema': 's', 'package_sha256': 'p', 'patterns': {'x': {}}}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(M.GB, 'mip', fake_mip), \
                mock.patch.object(M.GB, 'certify_with_tree', fake_tree):
            inc = M.screen(Path(d), reg, lambda m: None)
            self.assertEqual(len(inc), 40)
            self.assertTrue(all(s['included'] for _, s in inc))
            self.assertTrue(all(sec == M.SCREEN_S and not pats and not kw for _, sec, pats, kw in calls))
            n = len(calls)
            lines = (Path(d) / 'screen.jsonl').read_text().splitlines()
            self.assertEqual(len(lines), n)
            self.assertEqual(sum(json.loads(l)['included'] for l in lines), 40)
            inc2 = M.screen(Path(d), reg, lambda m: None)            # resume: nothing re-screened
            self.assertEqual(len(calls), n)
            self.assertEqual([t['task_id'] for t, _ in inc2], [t['task_id'] for t, _ in inc])


def side(lower, upper, wall):
    return {'lower': lower, 'upper': upper, 'wall_s': wall, 'check': {'verdict': 'VALID', 'bound': upper},
            'witness_valid': True, 'witness_value': lower, 'root_bound': upper + 2, 'nodes': 10, 'check_s': 0.1,
            'certificate_bytes': 100}


def rows(spec):
    return [{'task_id': f't{i}', 'stratum': 's0' if i % 2 else 's1', 'witness': {'mip_optimal': False},
             'a': side(*a), 'c': side(*c)} for i, (a, c) in enumerate(spec)]


class Verdicts(unittest.TestCase):
    def test_bound_rule(self):
        v = M.bound_verdict(rows([((80, 100, 60.0), (80, 95, 60.0))] * 10 + [((90, 90, 30.0), (90, 90, 25.0))] * 10))
        self.assertEqual((v['verdict'], v['mean']), ('BOUND_UTILITY', 2.5))
        v = M.bound_verdict(rows([((80, 100, 60.0), (80, 99, 60.0))] * 20))
        self.assertEqual(v['verdict'], 'NO_BOUND_UTILITY')                 # mean 1 < 2
        bad = rows([((80, 100, 60.0), (80, 95, 60.0))] * 20)
        bad[0]['c']['check']['verdict'] = 'REJECTED'
        self.assertEqual(M.bound_verdict(bad)['verdict'], 'NO_BOUND_UTILITY')

    def test_primary_is_b20r56s_rule(self):
        spec = [((80, 100, 60.0), (95, 95, 20.0))] * 8 + [((90, 90, 40.0), (90, 90, 30.0))] * 12
        v = M.verdict_of(rows(spec))
        self.assertEqual(v['verdict'], 'CERTIFICATION_UTILITY')
        self.assertEqual(v['bound']['verdict'], 'BOUND_UTILITY')
        self.assertEqual(R56.BOOT_SEED, 20265699)                           # restored after the call



EV = ROOT / 'evidence' / 'sf_hard_certification_b20r57'


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.screen = [json.loads(l) for l in (EV / 'screen.jsonl').read_text().splitlines() if l.strip()]
        cls.summary = json.loads((EV / 'summary.json').read_text())

    def test_screen(self):
        self.assertEqual(len(self.screen), 72)
        inc = [s for s in self.screen if s['included']]
        self.assertEqual(len(inc), 40)
        for s in self.screen:
            self.assertEqual(s['included'], s['screen_lower'] != s['screen_upper'])
            seed = int(s['task_id'].rsplit('_', 1)[1]) - s['index']
            N, p = M.SETTINGS[M.SEEDS.index(seed)]
            self.assertEqual(M.candidate(seed, s['index'], N, p)['task_id'], s['task_id'])
        self.assertEqual(sorted(r['task_id'] for r in self.rows), sorted(s['task_id'] for s in inc))

    def test_verdicts_recompute(self):
        v = M.verdict_of(self.rows)
        for k in ('verdict', 'passes', 'pooled', 'mcnemar_p_one_sided', 'wall_saving_a_minus_c', 'bound'):
            self.assertEqual(v[k], self.summary[k], k)
        self.assertEqual((v['verdict'], v['bound']['verdict']), ('CERTIFICATION_UTILITY', 'BOUND_UTILITY'))
        self.assertEqual((v['pooled']['certified_a'], v['pooled']['certified_c'], v['pooled']['certified_a_not_c']),
                         (14, 22, 0))

    def test_witnesses_and_kept_certificates(self):
        import gzip
        from genesis.common import digest
        from genesis.discovery import generated_bnb_sf as GB
        from genesis.verification import lp_dual_tree_sf as VT
        by = {s['task_id']: s for s in self.screen}
        reg = GB.load_registry()
        regs = {'a': GB.empty_registry(reg), 'c': reg}

        def task(tid):
            s = by[tid]
            seed = int(tid.rsplit('_', 1)[1]) - s['index']
            N, p = M.SETTINGS[M.SEEDS.index(seed)]
            return R56.task_of(M.candidate(seed, s['index'], N, p))
        for r in self.rows:
            self.assertEqual(VT.check_witness(task(r['task_id']), r['witness']['elements']), r['witness']['value'])
        kept = sorted((EV / 'certificates').glob('*.json.gz'))
        self.assertEqual(len(kept), 8)
        for path in kept:
            tid, side = path.name[:-len('.json.gz')].rsplit('.', 1)
            cert = json.loads(gzip.decompress(path.read_bytes()))
            row = next(r for r in self.rows if r['task_id'] == tid)
            self.assertEqual(digest(cert), row[side]['certificate_sha256'])
            v = VT.check_certificate(task(tid), cert, regs[side])
            self.assertEqual((v['verdict'], v['bound']), ('VALID', row[side]['upper']), path.name)


if __name__ == '__main__':
    unittest.main()
