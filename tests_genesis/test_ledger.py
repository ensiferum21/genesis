"""W01: every specification section, roadmap item and catalogue entry has a checked disposition."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('build_ledger', ROOT / 'scripts' / 'build_ledger.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


class Ledger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load()
        cls.rows, cls.problems = cls.mod.build()

    def test_every_reference_resolves_and_every_row_has_a_disposition(self):
        self.assertEqual(self.problems, [])

    def test_coverage(self):
        ids = {r['id'] for r in self.rows}
        self.assertEqual({f'SPEC-{s}' for s, _, _ in self.mod.spec_toc()} - ids, set())
        self.assertEqual(sum(i.startswith('CAT-') for i in ids), 137)
        for prefix, n in (('W', 28), ('GV', 9), ('E', 8)):
            self.assertEqual(sum(i.startswith(prefix) and i[len(prefix):].isdigit() for i in ids), n, prefix)
        self.assertTrue({'R-01', 'R-02', 'R-03', 'R-04'} <= ids)

    def test_nothing_is_accepted_without_an_external_record(self):
        self.assertFalse([r for r in self.rows if r['acceptance']['decision'] not in
                          ('PENDING_INDEPENDENT_ACCEPTANCE', 'N/A')])

    def test_committed_ledger_is_current(self):
        committed = json.loads((ROOT / 'ledger' / 'requirements_ledger.json').read_text())['rows']
        strip = lambda rs: [{k: v for k, v in r.items()} for r in rs]
        self.assertEqual(strip(committed), json.loads(json.dumps(strip(self.rows))),
                         'regenerate with: python3 scripts/build_ledger.py')


if __name__ == '__main__':
    unittest.main()
