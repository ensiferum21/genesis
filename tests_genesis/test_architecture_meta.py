"""ARA applied to ARA (`architecture/meta.py`; B20_R144's machinery) on synthetic evaluators: the meta-ladder finds
the component whose stand-in helps, and NONE on noise; neighbours move one setting one step, the located
component's first; the meta-cycle adopts a better setting only by MATERIAL on its choice environments; the
tuning-only control spends the same evaluations; the operator prior is learned from traces; every evaluation is
counted."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import ara as A  # noqa: E402
from genesis.architecture import meta as M  # noqa: E402


def synthetic(planted, noise=0.01):
    """gains per environment: 0.3 base, + 0.1 when the planted setting is at or above `planted`'s threshold, + noise."""
    calls = []

    def evaluate(cfg, envs, hint):
        calls.append((cfg, len(envs), hint))
        out = []
        for e in envs:
            rng = random.Random(f'{e}|{sorted(cfg.items())}|{hint}')
            g = 0.3 + rng.gauss(0, noise)
            if planted == 'evaluation' and cfg['exact_repeats'] >= 8:
                g += 0.1
            if planted == 'localisation' and (hint or cfg['ranking'] == 'localised_prior'):
                g += 0.1
            out.append(g)
        return out
    return evaluate, calls


class Ladder(unittest.TestCase):
    def test_finds_the_component(self):
        ev, calls = synthetic('evaluation')
        lad = M.ladder(ev, None, list(range(20)))
        self.assertEqual(lad['diagnosis'], 'evaluation')
        self.assertEqual(lad['evaluations'], 20 * 5)
        self.assertEqual(sum(n for _, n, _ in calls), 100)
        ev2, _ = synthetic('localisation')
        self.assertEqual(M.ladder(ev2, None, list(range(20)))['diagnosis'], 'localisation')

    def test_none_on_noise(self):
        ev, _ = synthetic(None, noise=0.05)
        self.assertEqual(M.ladder(ev, None, list(range(20)))['diagnosis'], 'NONE')

    def test_standins(self):
        s = M.standins(None)
        self.assertTrue(s['localisation'][1])
        self.assertEqual(s['exploration'][0]['max_variants'], 20)
        self.assertEqual(s['evaluation'][0]['exact_repeats'], 12)
        self.assertEqual(s['observation'][0]['edge_aggs'], A.CONFIG_SPACE['edge_aggs'][-1])


class Cycle(unittest.TestCase):
    def test_neighbours(self):
        nb = M.neighbours(None, 'evaluation')
        self.assertEqual(nb[0]['changed'], 'exact_repeats')
        for c in nb:
            diff = [k for k in A.DEFAULT_CONFIG if c['settings'][k] != A.DEFAULT_CONFIG[k]]
            self.assertEqual(diff, [c['changed']])
        self.assertEqual(len({str(sorted(c['settings'].items())) for c in nb}), len(nb))

    def test_the_default_order_is_b20r144s(self):
        nb = M.neighbours(None)
        self.assertEqual([c['changed'] for c in nb[:6]],
                         ['battery_random', 'battery_random', 'depth', 'depth', 'edge_aggs', 'exact_repeats'])
        self.assertEqual(nb, M.neighbours(None, None, first=(), interleave=False))

    def test_interleaved_order_covers_every_setting_first(self):
        nb = M.neighbours(None, None, first=('max_variants', 'depth'), interleave=True)
        n = len(A.CONFIG_SPACE)
        self.assertEqual([c['changed'] for c in nb[:2]], ['max_variants', 'depth'])
        self.assertEqual(len({c['changed'] for c in nb[:n]}), n)
        self.assertEqual(sorted(str(sorted(c['settings'].items())) for c in nb),
                         sorted(str(sorted(c['settings'].items())) for c in M.neighbours(None)))

    def test_ladder_fallback_tries_what_the_ladder_ranks_first(self):
        """Planted: more variants help by 0.03 and a deeper search costs 0.02, so the exploration stand-in (20
        variants, depth 3) gains only 0.01 and the ladder locates nothing; the alphabetical fall-back never reaches
        max_variants within six candidates, the ladder's order tries it first."""
        def evaluate(cfg, envs, hint):
            out = []
            for e in envs:
                g = 0.3 + random.Random(f'env{e}').gauss(0, 0.05)
                g += 0.03 if cfg['max_variants'] >= 4 else 0.0
                g -= 0.02 if cfg['depth'] >= 3 else 0.0
                out.append(g)
            return out
        v1 = {'max_variants': 2}                       # B20_R144's ARA_v1
        lad = M.ladder(evaluate, v1, list(range(20)))
        self.assertEqual(lad['diagnosis'], 'NONE')
        self.assertEqual(M.ladder_order(lad)[:2], ['max_variants', 'depth'])
        r0 = M.improve(evaluate, v1, list(range(20)), list(range(100, 120)))
        self.assertFalse(r0['adopted'])
        self.assertNotIn('max_variants', [c['changed'] for c in r0['candidates']])
        r1 = M.improve(evaluate, v1, list(range(20)), list(range(100, 120)), fallback='ladder')
        self.assertTrue(r1['adopted'])
        self.assertEqual(r1['settings']['max_variants'], 4)
        self.assertEqual(r1['evaluations'], r0['evaluations'])
        with self.assertRaises(ValueError):
            M.improve(evaluate, None, [0], [1], fallback='other')

    def test_adopts_only_by_material(self):
        ev, _ = synthetic('evaluation')
        r = M.improve(ev, None, list(range(20)), list(range(100, 120)))
        self.assertTrue(r['adopted'])
        self.assertGreaterEqual(r['settings']['exact_repeats'], 8)
        self.assertEqual(r['located'], 'evaluation')
        self.assertEqual(r['evaluations'], 20 * 5 + 20 * (1 + len(r['candidates'])))
        ev2, _ = synthetic(None, noise=0.005)
        r2 = M.improve(ev2, None, list(range(20)), list(range(100, 120)))
        self.assertFalse(r2['adopted'])
        self.assertEqual(r2['settings'], A.DEFAULT_CONFIG)

    def test_tuning_control_spends_the_same(self):
        ev, calls = synthetic('evaluation')
        t = M.tune(ev, None, list(range(20)), 220)
        self.assertLessEqual(t['evaluations'], 220)
        self.assertGreater(t['evaluations'], 220 - 20)
        self.assertEqual(sum(n for _, n, _ in calls), t['evaluations'])

    def test_prior_from_traces(self):
        traces = [{'diagnosis': {'diagnosis': 'expressiveness'}, 'variants': [
            {'rewrite': {'op': 'GENERALISE'}, 'gain': 0.2}, {'rewrite': {'op': 'INSERT'}, 'gain': 0.0}]},
            {'diagnosis': {'diagnosis': 'expressiveness'}, 'variants': [{'rewrite': {'op': 'GENERALISE'}, 'gain': 0.4}]},
            {'diagnosis': {'diagnosis': 'NONE'}, 'variants': [{'rewrite': {'op': 'SUBSTITUTE'}, 'gain': 9.0}]},
            {'diagnosis': None, 'variants': []}]
        p = M.learn_prior(traces)
        self.assertEqual(p, {'expressiveness': {'GENERALISE': 0.30000000000000004, 'INSERT': 0.0}})


if __name__ == '__main__':
    unittest.main()
