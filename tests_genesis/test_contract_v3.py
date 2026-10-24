"""The candidate feedback contract version 3 (research plane, `autonomy/contract_v3.py`; adopted nowhere): the protected
judge untouched; with version 2's calibration the copy is the protected search exactly; version 3 makes the same
search; its calibration programs; its tau follows the noise of near programs; no release without signal; a real
effect released."""
import hashlib
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import contract_v3 as V3  # noqa: E402
from genesis.autonomy import feedback as FB  # noqa: E402

PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'


def toy_ops(width=10, values=5):
    return {'random': lambda rng: {'d': [rng.randrange(values) for _ in range(width)]},
            'mutate': lambda p, rng: {'d': [x if rng.random() > 0.3 else rng.randrange(values) for x in p['d']]},
            'crossover': lambda a, b, rng: {'d': [rng.choice(pair) for pair in zip(a['d'], b['d'])]},
            'size': lambda p: 1}


def keyed(signal=1.0, noise=0.5, b_scale=10, log=None):
    """An evaluation that depends only on (program, split, occurrence)."""
    occ = {}

    def ev(p, s):
        k = json.dumps(p, sort_keys=True)
        n = occ[(k, s)] = occ.get((k, s), -1) + 1
        if log is not None:
            log.append((k, s, n))
        q = signal * sum(p['d']) / (1 if s == 'A' else b_scale)
        return q + random.Random(f'{k}|{s}|{n}').gauss(0, noise)
    return ev


class ProtectedJudge(unittest.TestCase):
    def test_the_protected_module_is_untouched(self):
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/autonomy/feedback.py').read_bytes()).hexdigest(),
                         PROTECTED_FEEDBACK_SHA256)
        with self.assertRaises(ValueError):
            FB.Judge(lambda p, s: 0.0, [{'d': [0]}] * 4, {'d': [1]}, calibrate='local')

    def test_with_v2_calibration_the_copy_is_the_protected_search(self):
        for seed, budget, cost in ((1, 300, None), (2, 600, {'B': 3, 'C': 3}), (3, 900, None), (4, 450, {'B': 2})):
            a = FB.steady_state_search(toy_ops(), keyed(), budget, seed, contract=True, calibrate='BC', cost=cost)
            b = V3.steady_state_search(toy_ops(), keyed(), budget, seed, calibration='BC', cost=cost)
            self.assertEqual(a, b)

    def test_constants_match_selfimprove_s_process(self):
        from genesis.autonomy import selfimprove as SI
        a = SI.search(SI.ORIGINAL, toy_ops(), keyed(), 400, 5, contract=True, calibrate='BC')
        b = V3.steady_state_search(toy_ops(), keyed(), 400, 5, calibration='BC')
        self.assertEqual(a, b)
        with self.assertRaises(ValueError):
            V3.steady_state_search(toy_ops(), keyed(), 400, 5, calibration='AB')


class Version3(unittest.TestCase):
    def test_same_search_until_one_stops(self):
        logs = {'BC': [], 'local': []}
        for cal in logs:
            V3.steady_state_search(toy_ops(), keyed(log=logs[cal]), 500, 3, calibration=cal)
        a = {cal: [x for x in v if x[1] == 'A'] for cal, v in logs.items()}
        n = min(len(v) for v in a.values())
        self.assertGreater(n, 100)
        self.assertEqual(a['BC'][:n], a['local'][:n])

    def test_local_calibration(self):
        inc = {'d': [1] * 10}
        a = V3.local_calibration(toy_ops(), inc, 5)
        self.assertEqual(a, V3.local_calibration(toy_ops(), inc, 5))
        self.assertNotEqual(a, V3.local_calibration(toy_ops(), inc, 6))
        keys = [json.dumps(p, sort_keys=True) for p in a]
        self.assertEqual(len(a), V3.LOCAL_CALIBRATION)
        self.assertEqual(len(set(keys)), len(keys))
        self.assertNotIn(json.dumps(inc, sort_keys=True), keys)
        with self.assertRaises(ValueError):
            V3.local_calibration({'mutate': lambda p, rng: dict(p)}, inc, 5)

    def test_tau_follows_the_noise_of_near_programs(self):
        rng = random.Random(3)
        quirk = {}

        def ev(p, s):                        # far programs carry large split quirks, near ones small
            k = json.dumps(p, sort_keys=True)
            far = sum(x != 1 for x in p['d']) > 4
            return quirk.setdefault((k, s), rng.gauss(0, 1.0 if far else 0.05)) + rng.gauss(0, 0.01)
        inc = {'d': [1] * 10}
        near = V3.local_calibration({'mutate': lambda p, r: {'d': [x if r.random() > 0.1 else r.randrange(5)
                                                                   for x in p['d']]}}, inc, 1)
        far = [{'d': [rng.randrange(5) for _ in range(10)]} for _ in range(32)]
        self.assertLess(FB.Judge(ev, near, inc, calibrate='BC').tau * 5, FB.Judge(ev, far, inc, calibrate='BC').tau)

    def test_rarely_releases_without_signal(self):
        released = 0
        for s in range(40):
            _, r = V3.steady_state_search(toy_ops(), keyed(signal=0.0, noise=1.0), 300, s, calibration='local')
            released += r['judge']['releases'] > 0
        self.assertLessEqual(released, 4)

    def test_releases_a_real_effect(self):
        _, r = V3.steady_state_search(toy_ops(), keyed(signal=1.0, noise=1.0, b_scale=1), 1500, 2, calibration='local')
        self.assertGreaterEqual(r['judge']['releases'], 1)


if __name__ == '__main__':
    unittest.main()
