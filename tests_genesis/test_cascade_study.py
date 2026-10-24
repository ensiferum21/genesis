"""B20_R131: the cascade on a real case (design): fresh, disjoint seeds; the archive step (every evaluated rule
dormant with an inferred, scored failed_due_to edge) and the trigger's selection on a toy trace; the refusals."""
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r131_cascade as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh_and_disjoint(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r131_cascade.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r129_adaptive_scientist as R129
        import b20r130_choice_instrument_interpretation as R130
        import b20r133_problem_compiler as R133
        mine = [(M.SEED + o, M.SEED + o + n) for o, n in M.SETS.values()]
        others = [(R129.SEED + o, R129.SEED + o + n) for o, n, _ in R129.SETS.values()]
        others += [(R130.SEED + o, R130.SEED + o + n) for o, n, _ in R130.SETS.values()]
        others += [(R133.SEED, R133.SEED + 4000)]
        for a0, a1 in mine:
            for b0, b1 in others:
                self.assertTrue(a1 <= b0 or b1 <= a0)
        with self.assertRaises(ValueError):
            M.world('test', 200)
        self.assertEqual(M.FUEL, 24)

    def test_archive_and_trigger_on_a_toy_trace(self):
        from genesis import vault as V
        trace = [(0, 0, {'agg': 'sum', 'expr': 'eig'}, 'A', -5.0), (0, 1, {'agg': 'sum', 'expr': 'dec'}, 'A', -4.0),
                 (0, 2, {'agg': 'sum', 'expr': 'eig'}, 'B', -5.5), (1, 3, {'agg': 'max', 'expr': 'pf'}, 'A', -6.0)]
        with tempfile.TemporaryDirectory() as d, V.Vault(Path(d) / 'v') as v:
            ids, ev = M.archive(v, trace, lambda m: None)
            self.assertEqual(len(ids), 3)
            for a in ids:
                st = v.status(a)
                self.assertEqual((st['status'], st['failure']), ('dormant', 'context_limited'))
            trig = v.put(V.Vault.record('CapabilityRecord', {'name': 't', 'unlocks': ['interpretation']},
                                        domain='causal', creator={'process': 'test'}))
            opps = v.opportunities(trig, 2)
            texts = [v.get(a)['content']['text'] for a in opps]
            self.assertEqual(texts, ['sum dec', 'sum eig'])                 # best stored training score first
            self.assertEqual(v.get(ids[0])['contracts']['scores'], {'A': -5.0, 'B': -5.5})

    def test_refusals(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
