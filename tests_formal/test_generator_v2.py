"""B20_R37: the generator-v2 package replays from its sources, its registry admits exactly the
CHECKED patterns, and the coverage study keeps its contract. The verdict follows from the rows,
the kept certificates re-check VALID, and the hosts are fresh and in the exposure addenda. Needs
the formal workspace; the formal suite accepts no skips."""
import copy
import json
from pathlib import Path
import sys
import unittest

from genesis.common import canonical
from genesis.formal_research import theory_package as TP
from genesis.formal_research.triangle_theory import DEFS_SOURCE
from genesis.invention import cuts_v2 as C2
from genesis.models import GraphTask
from genesis.verification import lp_dual_rows as V

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'generator_v2_b20r37'
sys.path.insert(0, str(ROOT / 'scripts'))


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.a = json.loads((EVIDENCE / 'part_a.json').read_text())
        cls.b = json.loads((EVIDENCE / 'part_b.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'part_b_rows.jsonl').read_text().splitlines() if l.strip()]
        cls.tasks = {t['task_id']: GraphTask.model_validate_json(canonical(t))
                     for t in json.loads((EVIDENCE / 'hosts.json').read_text())['tasks']}

    def test_package_replays_and_registry_is_the_checked_patterns(self):
        self.assertEqual(self.a['patterns'], [p['id'] for p in C2.generate()])
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        self.assertEqual(TP.replay(self.pkg)['verdict'], 'REPLAYED')
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')
        reg = V.registry_from_package(self.pkg, defs_source=DEFS_SOURCE)
        self.assertEqual(sorted(reg['patterns']), sorted(f'pc_{p}' for p in self.a['usable']))

    def test_verdict_follows_from_the_rows(self):
        import b20r32_generated_certification as R32
        import b20r37_generator_v2 as R37
        self.assertEqual(len(self.rows), 40)
        self.assertEqual(self.b['pooled'], R37.tally(self.rows))
        p = self.b['pooled']
        mc = R32.mcnemar_one_sided(p['certified_v2_not_v1'], p['certified_v1_not_v2'])
        self.assertAlmostEqual(self.b['mcnemar_p_one_sided'], round(mc, 8))
        want = ('DEFECT_FOUND' if not self.b['sound'] else 'V2_EXTENDS_COVERAGE'
                if p['certified_v2'] >= p['certified_v1'] and mc < 0.05 else 'NO_COVERAGE_GAIN')
        self.assertEqual(self.b['verdict'], want)

    def test_kept_certificates_recheck(self):
        reg = V.registry_from_package(self.pkg, defs_source=DEFS_SOURCE)
        by_id = {r['task_id']: r for r in self.rows}
        for path in sorted((EVIDENCE / 'certificates').glob('*.json')):
            v = V.check_certificate(self.tasks[path.stem], json.loads(path.read_text()), reg)
            self.assertEqual((v['verdict'], v['bound']), ('VALID', by_id[path.stem]['v2']['upper']))

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        r35 = json.loads((ROOT / 'evidence' / 'dense_certification_b20r35' / 'hosts.json').read_text())['tasks']
        self.assertFalse(set(self.tasks) & {t['task_id'] for t in r35})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(set(self.tasks) <= listed)


if __name__ == '__main__':
    unittest.main()
