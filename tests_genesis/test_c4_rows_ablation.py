"""B20_R49: the preregistered ablation of the transferred rows in the tree route. Design: fresh seeds, B20_R48's
settings, budget and limits; the ablation is the same route with an empty registry (4-cycle rows only) and
its certificates are checked against that registry; soundness needs both arms sound and agreeing; the tally.
Record: the verdict recomputes from the rows, the kept certificates re-check VALID, and the hosts are fresh and in
the exposure addenda."""
import gzip
import json
from pathlib import Path
import sys
import unittest

from genesis.common import canonical, digest
from genesis.discovery import generated_bnb_c4 as GB
from genesis.discovery import generated_certify_c4 as GC4
from genesis.models import GraphTask
from genesis.verification import lp_dual_tree_c4 as VT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r47_c4_certification as R47  # noqa: E402
import b20r48_c4_tree_certification as R48  # noqa: E402
import b20r49_c4_rows_ablation as R49  # noqa: E402

EVIDENCE = ROOT / 'evidence' / 'c4_rows_ablation_b20r49'


def side(lu, verdict='VALID', wvalid=True):
    return {'lower': lu[0], 'upper': lu[1], 'method': 'LP_DUAL_TREE_C4_EXACT', 'wall_s': 5.0, 'nodes': 9,
            'check': {'verdict': verdict, 'bound': lu[1]}, 'witness_valid': wvalid, 'witness_value': lu[0]}


class Design(unittest.TestCase):
    def test_preregistered_constants(self):
        self.assertEqual(R49.SEEDS, (20264901, 20264911))
        self.assertFalse(set(R49.SEEDS) & (set(R48.SEEDS) | set(R47.SEEDS)))
        self.assertEqual((R48.SETTINGS, R48.SECONDS, R48.ROUTE), (R47.SETTINGS, 60, R47.ROUTE))

    def test_the_ablation_is_the_empty_registry_and_is_checked_against_it(self):
        reg = GC4.load_registry()
        empty = R49.empty_registry(reg)
        self.assertEqual(empty['patterns'], {})
        self.assertNotEqual(digest(empty), digest(reg))
        t = GraphTask(task_id='k5', domain='c4_host_v2', family='test', split='DEV', n=5,
                      edges=tuple((u, v) for u in range(5) for v in range(u + 1, 5)))
        rec = GB.certify_with_tree(t, [], empty, seconds=30, lp_rounding_seconds=None)
        self.assertEqual(rec['upper'], 6)                                      # ex(K5, C4) = 6
        self.assertEqual(VT.check_certificate(t, rec['certificate'], empty)['verdict'], 'VALID')
        self.assertEqual(VT.check_certificate(t, rec['certificate'], reg)['verdict'], 'REJECTED')

    def test_soundness_and_tally(self):
        ok = {'task_id': 't', 'stratum': 's', 'c': side((60, 60)), 'c0': side((60, 64))}
        self.assertTrue(R49.sound_row(ok))
        self.assertFalse(R49.sound_row(dict(ok, c0=side((61, 61)))))
        self.assertFalse(R49.sound_row(dict(ok, c0=side((60, 64), verdict='REJECTED'))))
        self.assertFalse(R49.sound_row(dict(ok, c=side((60, 60), wvalid=False))))
        t = R49.tally([ok, dict(ok, task_id='u', c0=side((60, 60))), dict(ok, task_id='v', c=side((59, 62)))])
        self.assertEqual((t['certified_c'], t['certified_c0'], t['certified_c_not_c0'], t['certified_c0_not_c']),
                         (2, 1, 1, 0))


class Record(unittest.TestCase):
    """The B20_R49 run: the verdict recomputes from the rows, every kept certificate re-checks VALID against the
    full registry with the recorded bound and digest, and the hosts are fresh and in the exposure addenda."""
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
        self.assertEqual(R49.tally(rows), s['pooled'])
        unsound = [r['task_id'] for r in rows if not R49.sound_row(r)]
        self.assertEqual(unsound, s['unsound_rows'])
        p = s['pooled']
        mc = R32.mcnemar_one_sided(p['certified_c_not_c0'], p['certified_c0_not_c'])
        self.assertAlmostEqual(s['mcnemar_p_one_sided'], round(mc, 8))
        passes = {'sound': not unsound, 'coverage': p['certified_c'] >= p['certified_c0'], 'mcnemar': mc < 0.05}
        self.assertEqual(s['passes'], passes)
        self.assertEqual(s['verdict'], 'DEFECT_FOUND' if unsound else 'ROWS_RESPONSIBLE' if all(passes.values())
                         else 'NO_ROWS_EFFECT')
        self.assertEqual(s['ablation_registry_sha256'], digest(R49.empty_registry(GC4.load_registry())))

    def test_kept_certificates_recheck(self):
        reg = GC4.load_registry()
        by_id = {r['task_id']: r for r in self.rows}
        kept = sorted((EVIDENCE / 'certificates').glob('*.json.gz'))
        self.assertEqual(len(kept), self.s['pooled']['certified_c_not_c0'])
        for path in kept:
            tid = path.name[:-len('.json.gz')]
            cert = json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(digest(cert), by_id[tid]['c']['certificate_sha256'])
            v = VT.check_certificate(self.tasks[tid], cert, reg)
            self.assertEqual((v['verdict'], v['bound']), ('VALID', by_id[tid]['c']['upper']), tid)

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        for d in ('c4_certification_b20r47', 'c4_tree_certification_b20r48'):
            other = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())['tasks']
            self.assertFalse(set(self.tasks) & {t['task_id'] for t in other})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(set(self.tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
