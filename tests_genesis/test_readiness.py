"""B19: E1/E2 readiness records are DEV-only drafts, consistent with their plan."""
import json
from pathlib import Path
import unittest

from genesis import decision_record as DR
from genesis.common import digest

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'readiness_b19'


@unittest.skipUnless((EVIDENCE / 'summary.json').exists(), 'B19 readiness evidence not generated')
class Readiness(unittest.TestCase):
    def load(self, *parts):
        return json.loads(EVIDENCE.joinpath(*parts).read_text())

    def test_e1_is_a_consistent_dev_draft(self):
        rows = self.load('e1', 'pilot_rows.json')
        self.assertTrue(rows and all(r['split'] == 'DEV' for r in rows))
        draft = self.load('e1', 'decision_record_DRAFT.json')
        self.assertEqual(draft['status'], 'DRAFT')
        self.assertEqual(DR.problems(draft), [])
        self.assertTrue(DR.problems(draft, require_frozen=True))              # cannot be registered as is
        power = self.load('e1', 'power_analysis.json')
        self.assertEqual(power['headroom_reference'], 'centred')
        self.assertEqual(power['pilot_rows_sha256'], digest(rows))
        self.assertEqual(self.load('e1', 'power_analysis_b16_model.json')['status'], 'INFEASIBLE')
        s = self.load('summary.json')['e1']
        self.assertEqual(s['assumptions_fixed_before_pilot'], {'minimum_useful_effect': 0.5, 'design_effect': 1.0})

    def test_e2_is_a_design_draft(self):
        d = self.load('e2', 'design_DRAFT.json')
        self.assertEqual(d['status'], 'DRAFT')
        self.assertEqual(d['dev_results']['concept']['proved'], 8)
        self.assertIn('placebo', d['dev_results'])
        self.assertIn('not claimed', d['separation']['new_mathematics'])


if __name__ == '__main__':
    unittest.main()
