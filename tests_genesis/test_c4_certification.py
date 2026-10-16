"""B20_R47: the preregistered C4 certification-coverage study. Design: the settings, seeds, budgets and
route limits are the preregistered ones; the analysis applies B20_R35's four-part rule and the secondary
gap-closure diagnostic. Record: the verdict recomputes from the rows, the kept certificates re-check
VALID, and the hosts are fresh and in the exposure addenda."""
import json
from pathlib import Path
import sys
import unittest

from genesis.common import canonical, digest
from genesis.discovery import generated_certify_c4 as GC4
from genesis.models import GraphTask
from genesis.verification import lp_dual_rows_c4 as V4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r47_c4_certification as R47  # noqa: E402

EVIDENCE = ROOT / 'evidence' / 'c4_certification_b20r47'


def row(tid, stratum, a, b, wa, wb, la, lb):
    side = lambda lu, w, lp, m: {'lower': lu[0], 'upper': lu[1], 'method': m, 'wall_s': w,
                                 'lp_step': {'bound': lp, 'verdict': 'VALID'}}
    return {'task_id': tid, 'stratum': stratum, 'a': side(a, wa, la, 'SAT_DRAT'), 'b': side(b, wb, lb, 'SAT_DRAT')}


class Design(unittest.TestCase):
    def test_preregistered_constants(self):
        self.assertEqual(R47.SETTINGS, [('erdos', {'n': 30, 'p': 0.2}), ('erdos', {'n': 36, 'p': 0.17})])
        self.assertEqual((R47.PER, R47.SEEDS, R47.SECONDS), (20, (20264701, 20264711), 60))
        self.assertEqual(R47.ROUTE, {'separation_seconds': 15, 'max_rows': 50000, 'max_total': 80000,
                                     'order': 'dense-first', 'lp_rounding_seconds': 1.0})
        self.assertEqual(R47.C4, 'c4_host_v2')

    def test_tally_and_gap_closure(self):
        rows = [row('t1', 's', (60, 60), (60, 60), 3.0, 4.0, 63, 61),
                row('t2', 's', (62, 66), (62, 63), 60.0, 60.0, 66, 63),
                row('t3', 's', (77, 77), (77, 77), 30.0, 31.0, 80, 77)]
        t = R47.tally(rows)
        self.assertEqual((t['certified_a'], t['certified_b'], t['certified_b_not_a']), (2, 2, 0))
        g = t['gap_closure']
        self.assertEqual((g['hosts_with_optimum'], g['hosts_with_lp_gap'], g['rows_lp_meets_optimum']), (2, 2, 1))
        self.assertAlmostEqual(g['mean_fraction_closed'], (2 / 3 + 1) / 2, places=4)


class Record(unittest.TestCase):
    """The B20_R47 run: the verdict recomputes from the rows, kept certificates re-check VALID against the
    registry, the registry is B20_R46's, and the hosts are fresh and in the exposure addenda."""
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
        self.assertEqual(R47.tally(rows), s['pooled'])
        p = s['pooled']
        mc = R32.mcnemar_one_sided(p['certified_b_not_a'], p['certified_a_not_b'])
        self.assertAlmostEqual(s['mcnemar_p_one_sided'], round(mc, 8))
        sound = not s['disagreements'] and not s['invalid_certificates']
        passes = {'sound': sound, 'coverage': p['certified_b'] >= p['certified_a'], 'mcnemar': mc < 0.05,
                  'time': s['wall_saving_a_minus_b']['interval_90'][0] > 0}
        self.assertEqual(s['passes'], passes)
        want = ('DEFECT_FOUND' if not sound else 'CERTIFICATION_UTILITY' if all(passes.values())
                else 'NO_CERTIFICATION_UTILITY')
        self.assertEqual(s['verdict'], want)

    def test_kept_certificates_recheck(self):
        reg = GC4.load_registry()
        self.assertEqual(self.s['registry']['package_sha256'], reg['package_sha256'])
        self.assertEqual(self.s['registry']['sha256'], digest(reg))
        by_id = {r['task_id']: r for r in self.rows}
        for path in sorted((EVIDENCE / 'certificates').glob('*.json')):
            v = V4.check_certificate(self.tasks[path.stem], json.loads(path.read_text()), reg)
            self.assertEqual((v['verdict'], v['bound']), ('VALID', by_id[path.stem]['b']['upper']), path.name)

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        for d in ('dense_certification_b20r35', 'generator_v2_b20r37'):
            other = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())['tasks']
            self.assertFalse(set(self.tasks) & {t['task_id'] for t in other})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(set(self.tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
