"""ARA's own settings as an object (`ara.DEFAULT_CONFIG`, `ara.config_of`; 29 Oct 2026, for B20_R144): the defaults
reproduce ARA-1 exactly (the battery equals ARA-1's, and four cycle traces, diagnosed and blind, equal digests
recorded from the code before the change); settings outside the space are refused; the battery, the exact repeats,
the material fraction and the ranking change what ARA does; a hint replaces the ladder's localisation without
changing its terms."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import ara as A  # noqa: E402
from genesis.architecture import diagnose as D  # noqa: E402
from genesis.architecture import judge as J  # noqa: E402

BEFORE = {'50001': 'c20a12693f30a41ec260a26ef678a7b43fd0da6dfcca281996fb49f6800d2fbc',
          '50002': '84205037df8ba0574091c62a9ac692a5e16348026b5c2d759b6f56786f55b64a',
          '50003': '15da57c9051035561ef88232ba29fac6884888c3d72a7fa9ea2a66d3c5251ce2',
          '50004': 'cc521c1bb4f7e1b2fca2a5491c28edcc68f7bf751c5c724c7eb4550da39eaf52'}
CASES = ((50001, 'GLOBAL_ONLY'), (50002, 'SENSE_BLIND'), (50003, 'NULL'), (50004, 'EVAL_NOISY'))


class Defaults(unittest.TestCase):
    def test_the_defaults_are_ara_1(self):
        self.assertEqual(len(D.battery(0)), 56)
        self.assertEqual(A.config_of(None), A.DEFAULT_CONFIG)
        H = J.Harness(sealed_seed=777123)
        for index, cls in CASES:
            view = H.open(index, cls)
            tr = A.cycle(view, seed=index, budget=4 * view.budget, max_variants=2)
            tr2 = A.cycle(H.open(index, cls), seed=index, budget=4 * view.budget, diagnose=False, max_variants=2)
            got = hashlib.sha256(json.dumps([tr, tr2], sort_keys=True, default=str).encode()).hexdigest()
            self.assertEqual(got, BEFORE[str(index)], cls)
            tr3 = A.cycle(H.open(index, cls), seed=index, budget=4 * view.budget, config=dict(A.DEFAULT_CONFIG,
                                                                                               max_variants=2))
            self.assertEqual(json.dumps(tr3, sort_keys=True, default=str), json.dumps(tr, sort_keys=True, default=str))

    def test_refusals(self):
        with self.assertRaises(ValueError):
            A.config_of({'max_variants': 3})
        with self.assertRaises(ValueError):
            A.config_of({'oracle': True})
        self.assertEqual(A.config_of({'ranking': 'blind'})['ranking'], 'blind')


class Settings(unittest.TestCase):
    def test_battery_settings(self):
        b = D.battery(3, 24, ('mean', 'sd', 'frac_pos', 'cv'))
        self.assertEqual(len(b), 56 + 12 + 6)
        self.assertIn(['frac_pos_e', 'w'], b)
        self.assertNotIn(['frac_pos_e', 'w'], D.battery(3))

    def test_settings_change_the_cycle(self):
        H = J.Harness(sealed_seed=777123)
        index, cls = 50002, 'SENSE_BLIND'
        base = A.cycle(H.open(index, cls), seed=index, config={'max_variants': 2})
        more = A.cycle(H.open(index, cls), seed=index, config={'max_variants': 2, 'exact_repeats': 12,
                                                                'battery_random': 24})
        self.assertNotEqual(base['units']['view'], more['units']['view'])        # 12 repeats cost more units
        blind = A.cycle(H.open(index, cls), seed=index, config={'max_variants': 2, 'ranking': 'blind'})
        self.assertIsNone(blind['diagnosis'])

    def test_a_hint_moves_the_localisation_only(self):
        H = J.Harness(sealed_seed=777123)
        index, cls = 50001, 'GLOBAL_ONLY'
        a = A.cycle(H.open(index, cls), seed=index, config={'max_variants': 2})
        b = A.cycle(H.open(index, cls), seed=index, config={'max_variants': 2}, hint=['Search'])
        self.assertEqual(a['diagnosis']['terms'], b['diagnosis']['terms'])
        self.assertEqual(b['diagnosis']['located'], ['Search'])

    def test_a_prior_orders_the_implicated_rewrites(self):
        from genesis.architecture import rewrite as R
        H = J.Harness(sealed_seed=777123)
        view = H.open(50001, 'GLOBAL_ONLY')
        inc = view.incumbent
        rws = R.generate(inc)
        lad = {'located': ['Policy'], 'diagnosis': 'expressiveness'}
        plain = A.rank(inc, rws, lad, 0)
        ops = [r['op'] for r in plain if R.role_of(inc, r) == 'Policy']
        last = ops[-1]
        pri = A.rank(inc, rws, lad, 0, prior={'expressiveness': {last: 5.0}})
        self.assertEqual(pri[0]['op'], last)
        self.assertEqual(sorted(map(json.dumps, pri)), sorted(map(json.dumps, plain)))


if __name__ == '__main__':
    unittest.main()
