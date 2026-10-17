"""B20_R61: the statistician's brief (B19-OPEN-4).

Checks that the brief says only what the committed files say:
  * every stored power analysis a package relies on reproduces exactly from its pilot rows (digest and result);
  * each draft decision record's sample-size justification is the stored power analysis it names;
  * the brief's two tables are the derived tables, verbatim;
  * every derived number in the findings (recomputations under the custodian's families, 10,000-simulation
    checks, pilot ranges) appears in the brief verbatim;
  * the family each analysis is bound to is read from its plan-core digest, and the mismatches are the four
    causal analyses the brief names.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r61_statistician_brief as M  # noqa: E402
from genesis.common import digest  # noqa: E402

TEXT = M.BRIEF.read_text()


class Reproduction(unittest.TestCase):
    def test_every_stored_power_analysis_reproduces_from_its_pilot_rows(self):
        for a in M.ANALYSES:
            stored = M._load(a[1])
            self.assertEqual(digest(M.pilot_rows(a)), stored['pilot_rows_sha256'], a[0])
            self.assertEqual(M.recompute(a), stored, a[0])

    def test_decision_records_carry_their_power_analysis(self):
        names = {a[0]: a for a in M.ANALYSES}
        for name, rel in M.DECISION_RECORDS.items():
            ssj = M._load(rel)['sample_size_justification']
            stored = M._load(names[name][1])
            for k in ('chosen', 'pilot_rows_sha256', 'design_effect', 'minimum_useful_effect', 'power_target'):
                self.assertEqual(ssj[k], stored[k], (name, k))


class Brief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = M.findings()

    def test_tables_are_the_derived_tables(self):
        self.assertIn(M.power_markdown(), TEXT)
        self.assertIn(M.rehearsal_markdown(), TEXT)

    def test_findings_numbers_appear_verbatim(self):
        missing = {k: v for k, v in self.findings.items() if v not in TEXT}
        self.assertEqual(missing, {})
        self.assertEqual({k for k in self.findings if k.startswith('rebound ')},
                         {'rebound E1b ablation', 'rebound E1b placebo', 'rebound E1b-C4 ablation',
                          'rebound E1b-C4 placebo'})
        self.assertEqual({k for k in self.findings if k.startswith('10k ')}, {'10k E1b-C4 placebo', '10k E1d'})

    def test_families_and_floor(self):
        mism = [a[0] for a in M.ANALYSES if M.family_check(a)[0] != M.family_check(a)[1]]
        self.assertEqual(mism, ['E1b ablation', 'E1b placebo', 'E1b-C4 ablation', 'E1b-C4 placebo'])
        for name, t, s, u, strata, k, lp, floor in M.rehearsal_rows():
            self.assertGreaterEqual(lp, floor - 1e-9, name)
            self.assertGreater(floor, 0.05, name)

    def test_borderline_rule(self):
        self.assertTrue(M.borderline(0.800))
        self.assertTrue(M.borderline(0.814))
        self.assertFalse(M.borderline(0.841))
        self.assertAlmostEqual(M.mc_se(0.8), 0.012649, places=5)

    def test_status(self):
        self.assertIn('Nothing here is signed off', TEXT)
        self.assertIn('B19-OPEN-4', TEXT.splitlines()[0])


if __name__ == '__main__':
    unittest.main()
