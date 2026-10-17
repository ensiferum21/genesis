"""B20_R56: the sum-free certification study. Design: the preregistered constants; the hosts are deterministic, valid
checker records, distinct, and of the two settings; the conventional route is the empty registry (the ablation); the
soundness rule and the verdict follow B20_R35/R48's rule.

Record (B20_R56): the hosts are the script's; the verdict recomputes from the rows (NO_CERTIFICATION_UTILITY: 26 vs 28
certified, 0/2 discordant, wall saving interval includes 0); every witness is sum-free with its value; the kept
certificates (hosts certified by one route only) re-check VALID with their bound and digest."""
from pathlib import Path
import sys
import unittest

from genesis.discovery import generated_bnb_sf as GB
from genesis.verification import lp_dual_tree_sf as VT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r56_sf_tree_certification as M  # noqa: E402


class Design(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(M.SETTINGS, ((300, 0.6), (360, 0.6)))
        self.assertEqual((M.PER, M.SEEDS, M.SECONDS, M.WITNESS_S), (20, (20265601, 20265611), 60, 10))
        self.assertEqual(M.SEPARATION, {'rounds': 30, 'per_round': 400})
        self.assertEqual(GB.empty_registry({'schema': 's', 'package_sha256': 'p', 'patterns': {'x': 1}})['patterns'], {})

    def test_hosts(self):
        a, b = M.make_hosts(), M.make_hosts()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 40)
        self.assertEqual(len({tuple(t['elements']) for t in a}), 40)
        for t in a:
            self.assertEqual(VT.task_problems(M.task_of(t)), [])
            N = int(t['task_id'].split('_')[1][1:])
            self.assertTrue(set(t['elements']) <= set(range(1, N + 1)))
            self.assertGreater(len(t['elements']), N * 0.5)
        self.assertEqual([t['family'] for t in a], [M.setting_name(*M.SETTINGS[0])] * 20 + [M.setting_name(*M.SETTINGS[1])] * 20)


def side(lower, upper, wall, *, valid=True):
    return {'lower': lower, 'upper': upper, 'wall_s': wall, 'check': {'verdict': 'VALID' if valid else 'REJECTED',
                                                                     'bound': upper},
            'witness_valid': True, 'witness_value': lower, 'root_bound': upper + 2, 'nodes': 10,
            'check_s': 0.1, 'certificate_bytes': 100}


def rows(spec):
    out = []
    for i, (a, c) in enumerate(spec):
        out.append({'task_id': f't{i}', 'stratum': 's0' if i % 2 else 's1', 'witness': {'mip_optimal': False},
                    'a': side(*a), 'c': side(*c)})
    return out


class Verdict(unittest.TestCase):
    def test_rule(self):
        good = [((5, 9, 60.0), (9, 9, 10.0))] * 8 + [((9, 9, 30.0), (9, 9, 12.0))] * 12
        v = M.verdict_of(rows(good))
        self.assertEqual(v['verdict'], 'CERTIFICATION_UTILITY', v['passes'])
        slow = [((5, 9, 60.0), (9, 9, 50.0))] * 8 + [((9, 9, 10.0), (9, 9, 40.0))] * 12
        v = M.verdict_of(rows(slow))
        self.assertEqual(v['verdict'], 'NO_CERTIFICATION_UTILITY')
        self.assertEqual(v['passes'], {'sound': True, 'coverage': True, 'mcnemar': True, 'time': False})
        few = [((5, 9, 60.0), (9, 9, 10.0))] * 2 + [((9, 9, 30.0), (9, 9, 12.0))] * 18
        self.assertFalse(M.verdict_of(rows(few))['passes']['mcnemar'])
        r = rows(good)
        r[3]['c']['check']['verdict'] = 'REJECTED'
        self.assertEqual(M.verdict_of(r)['verdict'], 'DEFECT_FOUND')
        r = rows(good)
        r[1]['a'] = side(8, 8, 1.0)
        self.assertEqual(M.verdict_of(r)['verdict'], 'DEFECT_FOUND')     # values disagree when both certify


EV = ROOT / 'evidence' / 'sf_tree_certification_b20r56'
VERDICT = 'NO_CERTIFICATION_UTILITY'


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.summary = json.loads((EV / 'summary.json').read_text())
        cls.hosts = json.loads((EV / 'hosts.json').read_text())['tasks']

    def test_hosts_are_the_scripts(self):
        self.assertEqual(self.hosts, M.make_hosts())
        self.assertEqual(sorted(r['task_id'] for r in self.rows), sorted(t['task_id'] for t in self.hosts))

    def test_the_verdict_recomputes(self):
        v = M.verdict_of(self.rows)
        for k in ('verdict', 'passes', 'pooled', 'mcnemar_p_one_sided', 'wall_saving_a_minus_c', 'unsound_rows'):
            self.assertEqual(v[k], self.summary[k], k)
        self.assertEqual(v['verdict'], VERDICT)

    def test_witnesses_and_kept_certificates_recheck(self):
        import gzip
        import json
        from genesis.common import digest
        by = {t['task_id']: t for t in self.hosts}
        reg = GB.load_registry()
        regs = {'a': GB.empty_registry(reg), 'c': reg}
        for r in self.rows:
            task = M.task_of(by[r['task_id']])
            self.assertEqual(VT.check_witness(task, r['witness']['elements']), r['witness']['value'])
        kept = sorted((EV / 'certificates').glob('*.json.gz'))
        for path in kept:
            tid, side = path.name[:-len('.json.gz')].rsplit('.', 1)
            cert = json.loads(gzip.decompress(path.read_bytes()))
            row = next(r for r in self.rows if r['task_id'] == tid)
            self.assertEqual(digest(cert), row[side]['certificate_sha256'])
            v = VT.check_certificate(M.task_of(by[tid]), cert, regs[side])
            self.assertEqual((v['verdict'], v['bound']), ('VALID', row[side]['upper']), path.name)


if __name__ == '__main__':
    unittest.main()
