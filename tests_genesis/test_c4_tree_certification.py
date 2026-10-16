"""B20_R48: the preregistered C4 tree-certification study. Design: the settings, seeds, budgets and route
limits are the preregistered ones (B20_R47's settings and limits, fresh seeds); soundness needs a VALID
certificate with the claimed bound, a C4-free witness of the reported value, and agreement when both routes
certify; the tally and the calibration-limit check. Record: the verdict recomputes from the rows, every kept
certificate re-checks VALID with the recorded bound and digest, and the hosts are fresh and in the exposure
addenda."""
import gzip
import json
from pathlib import Path
import sys
import unittest

from genesis.common import canonical, digest
from genesis.discovery import generated_certify_c4 as GC4
from genesis.models import GraphTask
from genesis.verification import lp_dual_tree_c4 as VT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r47_c4_certification as R47  # noqa: E402
import b20r48_c4_tree_certification as R48  # noqa: E402

EVIDENCE = ROOT / 'evidence' / 'c4_tree_certification_b20r48'


def row(tid, a, c, *, verdict='VALID', bound=None, wvalid=True, wvalue=None, method='LP_DUAL_TREE_C4_EXACT'):
    return {'task_id': tid, 'stratum': 's',
            'a': {'lower': a[0], 'upper': a[1], 'method': 'SAT_DRAT', 'wall_s': 10.0},
            'c': {'lower': c[0], 'upper': c[1], 'method': method, 'wall_s': 5.0, 'nodes': 9, 'check_s': 0.1,
                  'certificate_bytes': 100, 'check': {'verdict': verdict, 'bound': c[1] if bound is None else bound},
                  'witness_valid': wvalid, 'witness_value': c[0] if wvalue is None else wvalue}}


class Design(unittest.TestCase):
    def test_preregistered_constants(self):
        self.assertEqual(R48.SETTINGS, R47.SETTINGS)
        self.assertEqual((R48.PER, R48.SEEDS, R48.SECONDS), (20, (20264801, 20264811), 60))
        self.assertEqual(R48.ROUTE, R47.ROUTE)
        self.assertEqual(R48.CALIBRATION_LIMIT, 0.9)
        self.assertFalse(set(R48.SEEDS) & set(R47.SEEDS))

    def test_soundness_rule(self):
        self.assertTrue(R48.sound_row(row('t', (60, 60), (60, 60))))
        self.assertTrue(R48.sound_row(row('t', (60, 64), (60, 60))))
        self.assertFalse(R48.sound_row(row('t', (60, 60), (61, 61))))                  # values disagree
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), verdict='REJECTED')))
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), bound=61)))
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), wvalid=False)))
        self.assertFalse(R48.sound_row(row('t', (60, 64), (60, 60), wvalue=59)))

    def test_tally(self):
        rows = [row('t1', (60, 60), (60, 60)), row('t2', (60, 64), (61, 61)), row('t3', (60, 64), (60, 63))]
        t = R48.tally(rows)
        self.assertEqual((t['certified_a'], t['certified_c'], t['certified_c_not_a'], t['certified_a_not_c']), (1, 2, 1, 0))
        self.assertAlmostEqual(t['rate_c'], 2 / 3, places=4)
        self.assertEqual(t['by_method_c'], {'LP_DUAL_TREE_C4_EXACT': 2})


class Record(unittest.TestCase):
    """The B20_R48 run: the verdict recomputes from the rows, every kept certificate re-checks VALID with the
    recorded bound, and the hosts are fresh and in the exposure addenda."""
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.tasks = {t['task_id']: GraphTask.model_validate_json(canonical(t))
                     for t in json.loads((EVIDENCE / 'hosts.json').read_text())['tasks']}

    def test_verdict_recomputes_from_the_rows(self):
        import b20r32_generated_certification as R32
        s, rows = self.s, self.rows
        self.assertEqual(len(rows), 40)
        self.assertEqual({r['task_id'] for r in rows}, set(self.tasks))
        self.assertEqual(R48.tally(rows), s['pooled'])
        unsound = [r['task_id'] for r in rows if not R48.sound_row(r)]
        self.assertEqual(unsound, s['unsound_rows'])
        p = s['pooled']
        mc = R32.mcnemar_one_sided(p['certified_c_not_a'], p['certified_a_not_c'])
        self.assertAlmostEqual(s['mcnemar_p_one_sided'], round(mc, 8))
        passes = {'sound': not unsound, 'coverage': p['certified_c'] >= p['certified_a'], 'mcnemar': mc < 0.05,
                  'time': s['wall_saving_a_minus_c']['interval_90'][0] > 0}
        self.assertEqual(s['passes'], passes)
        want = ('DEFECT_FOUND' if unsound else 'CERTIFICATION_UTILITY' if all(passes.values())
                else 'NO_CERTIFICATION_UTILITY')
        self.assertEqual(s['verdict'], want)

    def test_kept_certificates_recheck(self):
        reg = GC4.load_registry()
        self.assertEqual(self.s['registry']['sha256'], digest(reg))
        by_id = {r['task_id']: r for r in self.rows}
        kept = sorted((EVIDENCE / 'certificates').glob('*.json.gz'))
        self.assertEqual(len(kept), self.s['pooled']['certified_c_not_a'])
        for path in kept:
            tid = path.name[:-len('.json.gz')]
            cert = json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(digest(cert), by_id[tid]['c']['certificate_sha256'])
            v = VT.check_certificate(self.tasks[tid], cert, reg)
            self.assertEqual((v['verdict'], v['bound']), ('VALID', by_id[tid]['c']['upper']), tid)

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        r47 = json.loads((ROOT / 'evidence' / 'c4_certification_b20r47' / 'hosts.json').read_text())['tasks']
        self.assertFalse(set(self.tasks) & {t['task_id'] for t in r47})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(set(self.tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
