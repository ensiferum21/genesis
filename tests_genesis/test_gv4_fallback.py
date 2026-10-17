"""B20_R60: the GV4 fallback claim DRAFT.

Checks that the draft says only what the committed evidence says:
  * every number it quotes renders, from the cited file and key, to text that appears in the draft verbatim;
  * `attempt_family.json` is what the script derives from the evidence summaries (Benjamini-Yekutieli at q 0.1);
  * the BY statements in the draft match that family;
  * the draft is labelled DRAFT, adopts nothing, and does not claim a better improver.
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r60_gv4_fallback as M  # noqa: E402

TEXT = M.DRAFT.read_text()


class Citations(unittest.TestCase):
    def test_every_quoted_number_comes_from_the_evidence(self):
        missing = [(what, s) for what, s in M.rendered() if s not in TEXT]
        self.assertEqual(missing, [])
        self.assertGreaterEqual(len(M.rendered()), 25)

    def test_cited_files_exist(self):
        for _, rel, _, _ in M.CITATIONS:
            self.assertTrue((ROOT / rel).is_file(), rel)


class Family(unittest.TestCase):
    def setUp(self):
        self.fam = M.by_family()

    def test_the_family_file_is_derived_from_the_evidence(self):
        self.assertEqual(json.loads(M.OUT.read_text()), json.loads(json.dumps(self.fam)))

    def test_by_step_up(self):
        self.assertEqual(M.by_rejections([0.001, 0.2, 0.9]), {0})
        self.assertEqual(M.by_rejections([0.5, 0.6]), set())
        # step-up: the second p fails its own threshold alone, but the third passes and carries it
        m, c = 3, M.harmonic(3)
        p = [0.0, 2 * 0.1 / (m * c) + 1e-9, 3 * 0.1 / (m * c)]
        self.assertEqual(M.by_rejections(p), {0, 1, 2})
        self.assertIsNone(M.max_family_size(0.5, 1))

    def test_the_attempts_and_survivors(self):
        self.assertEqual(self.fam['family_size'], 13)
        self.assertEqual(sum(r['kind'] == 'construction' for r in self.fam['attempts']), 6)
        self.assertTrue(all(r['p_one_sided'] is None and r['verdict'] == 'NO_UTILITY_AFTER_COST'
                            for r in self.fam['attempts'] if r['kind'] == 'construction'))
        self.assertEqual(self.fam['survivors'], ['B20_R35', 'B20_R48', 'B20_R57'])
        up = {r['batch']: r['survives_up_to_family_size'] for r in self.fam['attempts'] if r['survives_by']}
        self.assertEqual(up['B20_R35'], M.FAMILY_CAP)
        self.assertIn(f'up to {up["B20_R48"]} attempts', TEXT)
        self.assertIn(f'B20_R57 up to {up["B20_R57"]}', TEXT)
        self.assertIn(f'all {self.fam["family_size"]}', TEXT)
        self.assertIn(f'up to {M.FAMILY_CAP:,}', TEXT)
        self.assertTrue(set(M.NOT_ATTEMPTS).isdisjoint(r['batch'] for r in self.fam['attempts']))


class Wording(unittest.TestCase):
    def test_draft_status_and_ceiling(self):
        self.assertIn('DRAFT', TEXT.splitlines()[0])
        self.assertIn('**Not adopted.**', TEXT)
        self.assertIn('A better improver (GV4).', TEXT)
        self.assertIn('not established; fallback taken', TEXT)
        self.assertIn('**not replicated**', TEXT)


if __name__ == '__main__':
    unittest.main()
