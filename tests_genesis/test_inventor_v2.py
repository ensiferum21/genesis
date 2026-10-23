"""B20_R112: the inventor under contract v2 (design): fresh seed, the A/B/C split by cell, the refusal before B20_R111
has finished, and the registered output."""
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r112_inventor_v2 as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r112_inventor_v2.py':
                self.assertIsNone(re.search(rf'\b{M.HOST_SEED}\b', path.read_text()), path.name)

    def test_splits_take_one_host_per_cell_each(self):
        tasks = [f'c{i % 4}-{i // 4}' for i in range(12)]          # qet's cell-interleaved order
        s = M.splits(tasks, 4)
        self.assertEqual(s['A'], ['c0-0', 'c1-0', 'c2-0', 'c3-0'])
        self.assertEqual(s['C'], ['c0-2', 'c1-2', 'c2-2', 'c3-2'])
        self.assertFalse(set(s['A']) & set(s['B']) or set(s['B']) & set(s['C']))

    def test_refuses_before_b20r111(self):
        with mock.patch.object(M, 'R111', ROOT / 'evidence' / 'does_not_exist'):
            with self.assertRaises(SystemExit):
                M.main([str(ROOT / 'evidence' / 'inventor_v2_b20r112')])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])



class RecordB20R112(unittest.TestCase):
    """B20_R112's record: the test recomputes from the held-out values against B20_R111's recorded champion; the
    reported program is the judge's start program (no release) and a known template's statements."""

    def test_recomputes(self):
        import json
        import b20r111_invention_test as M111
        ev = ROOT / 'evidence' / 'inventor_v2_b20r112'
        s = json.loads((ev / 'summary.json').read_text())
        r111 = json.loads((M.R111 / 'summary.json').read_text())
        hs = sorted(s['held_out_values'])
        self.assertEqual(hs, sorted(r111['held_out'][r111['champion']]))
        test = M111.sign([s['held_out_values'][h] for h in hs], [r111['held_out'][r111['champion']][h] for h in hs], M.ALPHA)
        self.assertEqual(json.loads(json.dumps(test)), s['test'])
        self.assertEqual((s['verdict'], s['test']['label'], s['search']['judge']['releases']),
                         ('NOT_DEMONSTRATED', 'BEHIND_PRIOR_ART', 0))
        self.assertEqual(M111.core_label(M111.signature(s['program'])), ('KNOWN_CORE', s['known_as_template']))
        trace = [json.loads(l) for l in (ev / 'trace.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual(sum(x['split'] == 'A' for x in trace) + sum(x['split'] in 'BC' for x in trace), len(trace))


if __name__ == '__main__':
    unittest.main()
