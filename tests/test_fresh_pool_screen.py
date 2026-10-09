import json
from pathlib import Path
import tempfile
import unittest
from scripts.screen_fresh_pool import screen


class TestFreshPoolScreen(unittest.TestCase):
    def test_old_tasks_are_rejected_without_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            old = p / 'old.json'
            new = p / 'new.json'
            old.write_text(json.dumps({'tasks': ['plus (S (S Z)) Z = Z']}))
            new.write_text(json.dumps({'tasks': ['plus (S (S Z)) Z = Z',
                                                       'len (Cons Z Nil) = Z']}))
            r = screen(new, [old], minimum=1)
            self.assertEqual(r['prior_pool_rejected'], 1)
            self.assertEqual(r['fresh_count'], 1)
            self.assertEqual(r['status'], 'DEV_FRESHNESS_THRESHOLD_MET_UNVERIFIED')
            self.assertFalse(r['preregistration_allowed'])


if __name__ == '__main__':
    unittest.main()

class TestStructuralLeakage(unittest.TestCase):
    def test_equation_swap_and_alpha_renaming(self):
        from scripts.screen_fresh_pool import _parsed, _same_family
        from gap_engine.adapters.induction.theory import Theory
        p = Theory.default().parser()
        old = _parsed('plus (len xs) (len ys) = len (app xs ys)', p)
        new = _parsed('len (app zs xs) = plus (len zs) (len xs)', p)
        self.assertTrue(_same_family(old, new))

    def test_substitution_instance(self):
        from scripts.screen_fresh_pool import _parsed, _same_family
        from gap_engine.adapters.induction.theory import Theory
        p = Theory.default().parser()
        old = _parsed('len (rev xs) = len xs', p)
        new = _parsed('len (rev (app ys zs)) = len (app ys zs)', p)
        self.assertTrue(_same_family(old, new))

    def test_shared_substitution_prevents_false_match(self):
        from scripts.screen_fresh_pool import _parsed, _instance_of
        from gap_engine.adapters.induction.theory import Theory
        p = Theory.default().parser()
        a = _parsed('plus x x = double x', p)
        b = _parsed('plus x y = double x', p)
        self.assertFalse(_instance_of(a, b))


class TestGenAud014FailClosed(unittest.TestCase):
    def _screen(self, statements, minimum=300):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'candidate.json').write_text(json.dumps({'tasks': statements}))
            (p/'history.json').write_text(json.dumps({'tasks': []}))
            return screen(p/'candidate.json', [p/'history.json'], minimum=minimum)

    def test_300_unparseable_strings_cannot_trigger_prereg(self):
        r=self._screen([f'nonsense_{i}' for i in range(300)])
        self.assertEqual(r['fresh_count'],0)
        self.assertEqual(r['invalid_or_trivial_rejected'],300)
        self.assertEqual(r['status'],'INSUFFICIENT_FRESH_TASKS')
        self.assertFalse(r['preregistration_allowed'])

    def test_valid_syntax_false_equation_never_implies_proof(self):
        r=self._screen(['plus Z Z = S Z'],minimum=1)
        self.assertEqual(r['fresh_count'],1)
        self.assertEqual(r['status'],'DEV_FRESHNESS_THRESHOLD_MET_UNVERIFIED')
        self.assertFalse(r['preregistration_allowed'])
        self.assertFalse(r['proofs_independently_replayed'])

    def test_trivial_and_ill_sorted_statements_excluded(self):
        r=self._screen(['plus x Z = plus x Z', 'plus Z Z = Nil', 'rev xs = Z'],minimum=1)
        self.assertEqual(r['fresh_count'],0)
        self.assertEqual(r['invalid_or_trivial_rejected'],3)

    def test_nonstring_and_bad_configuration_rejected(self):
        with self.assertRaises(ValueError):
            self._screen([1])
        with self.assertRaises(ValueError):
            self._screen(['plus x Z = x'],minimum=0)
