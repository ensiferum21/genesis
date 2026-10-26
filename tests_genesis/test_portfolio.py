"""The portfolio of discovery processes and its allocators (Genesis Ω², B20_R148): harnesses, arms, budgets,
validation, metrics, G3's tuning and the three task domains."""
from pathlib import Path
import random
import statistics
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.autonomy import portfolio as P  # noqa: E402
from genesis.autonomy import portfolio_tasks as PT  # noqa: E402


def toy(peak=37, n=64, deceptive=False, calls=None):
    """Programs are integers 0..n-1; the score is -|x - peak| (smooth), or a needle at `peak` on a flat floor
    (deceptive: local search cannot climb). `calls` counts evaluations per split."""
    def evaluate(x, split, rep):
        if calls is not None:
            calls[split] = calls.get(split, 0) + 1
        if deceptive:
            return 1.0 if x == peak else 0.0
        return -abs(x - peak) + (0.001 if split == 'V' else 0.0)
    return P.Task(name='toy', domain='toy', family='deceptive' if deceptive else 'smooth',
                  random=lambda rng: rng.randrange(n), mutate=lambda x, rng: max(0, min(n - 1, x + rng.choice((-1, 1)))),
                  crossover=lambda a, b, rng: (a + b) // 2, size=lambda x: 1, descriptor=lambda x: x // 8,
                  evaluate=evaluate)


class Harnesses(unittest.TestCase):
    def test_each_harness_is_resumable_and_deterministic(self):
        t = toy()
        for name, cls in P.CLASSES.items():
            a, b = cls(t, random.Random(5)), cls(t, random.Random(5))
            seq_a, seq_b = [], []
            for _ in range(200):
                pa, pb = a.propose(), b.propose()
                seq_a.append(pa)
                seq_b.append(pb)
                a.feed(t.evaluate(pa, 'A', a.reps(pa)))
                b.feed(t.evaluate(pb, 'A', b.reps(pb)))
            self.assertEqual(seq_a, seq_b, name)
            self.assertEqual(a.evals, 200)
            best = max(a.stats.values(), key=lambda s: s[0] / s[1])
            self.assertEqual(a.mean(a.incumbent()), best[0] / best[1], name)

    def test_local_search_climbs_a_smooth_task(self):
        t = toy()
        for name in ('hill_climb', 'evolution', 'anneal'):
            h = P.CLASSES[name](t, random.Random(1), horizon=300)
            for _ in range(300):
                p = h.propose()
                h.feed(t.evaluate(p, 'A', 0))
            self.assertEqual(h.incumbent(), 37, name)


class Arms(unittest.TestCase):
    def test_every_arm_spends_its_budget_and_validates_its_answer(self):
        for arm in P.ARMS:
            calls = {}
            t = toy(calls=calls)
            marks = []
            r = P.run_arm(t, arm, 256, 3, on_checkpoint=lambda m, a, run: marks.append((m, run.used, a)))
            self.assertLessEqual(r.used, 256, arm)
            self.assertGreaterEqual(r.used, 250, arm)
            self.assertEqual(calls.get('A', 0) + calls.get('V', 0), r.used, arm)    # every evaluation charged
            self.assertNotIn('T', calls, arm)                                       # the arm never sees T
            self.assertEqual([m for m, _, _ in marks], P.checkpoints(256), arm)
            for m, used, a in marks:
                self.assertIn(P.key(a), r.v, arm)                                  # the answer was validated
            self.assertEqual(r.answer(), max(r.v.values(), key=lambda v: v[0])[1], arm)

    def test_portfolio_arms_share_common_random_numbers(self):
        t = toy()
        first = {}
        for arm in ('uniform', 'halving', 'bandit'):
            r = P.run_arm(t, arm, 512, 9)
            first[arm] = r.trace[0]['answer']
        self.assertEqual(len(set(first.values())), 1)

    def test_halving_keeps_one_harness_with_equal_shares(self):
        t = toy()
        r = P.run_arm(t, 'halving', 1800, 2)
        self.assertEqual(len(r.live), 1)
        self.assertEqual(P.ETA, 3)
        first_stage = 1800 // 3 // 6
        self.assertTrue(all(v >= first_stage - 1 for v in r.alloc.values()))       # every harness had its share
        self.assertGreater(r.alloc[r.live[0]], 1800 // 3)                          # the survivor ran the last stage

    def test_bandit_reserves_exploration(self):
        t = toy()
        r = P.run_arm(t, 'bandit', 2048, 4)
        rounds = 2048 // 32
        self.assertTrue(all(v >= 32 for v in r.alloc.values()))
        self.assertGreaterEqual(sum(1 for v in r.alloc.values() if v > 0), 6)
        self.assertLess(max(r.alloc.values()), 2048 - (rounds // 10) * 32 + 64)

    def test_the_allocators_find_the_harness_that_works(self):
        # deceptive needle: only sampling-based harnesses can find it; smooth: everything climbs
        t = toy(deceptive=True, n=400, peak=123)
        hits = {arm: sum(P.run_arm(t, arm, 1024, s).answer() == 123 for s in range(6))
                for arm in ('single:hill_climb', 'single:best_of_n', 'halving')}
        self.assertGreaterEqual(hits['single:best_of_n'], 4)
        self.assertGreater(hits['single:best_of_n'], hits['single:hill_climb'])
        self.assertGreaterEqual(hits['halving'], 3)              # the portfolio keeps the harness that finds it


class Metrics(unittest.TestCase):
    def test_normalise_and_audc(self):
        self.assertEqual(P.normalise(5, 0, 10), 0.5)
        self.assertEqual(P.normalise(3, 3, 3), 1.0)
        self.assertEqual(P.audc([0.0, 1.0]), 0.5)
        self.assertAlmostEqual(P.audc([0.0, 0.5, 1.0, 1.0]), (0 + 0.5 + 1.0 + 0.5) / 3)
        self.assertEqual(P.audc_of([None, 10.0], 0.0, 10.0), 0.5)
        self.assertEqual(P.checkpoints(512), [16, 32, 64, 128, 256, 512])

    def test_cpu_counts_child_processes(self):
        import subprocess
        c0 = P.cpu_now()
        subprocess.run([sys.executable, '-c', 'sum(i * i for i in range(3_000_000))'], check=True)
        self.assertGreater(P.cpu_now() - c0, 0.05)

    def test_measure_averages_a_noisy_task(self):
        seen = []
        t = toy()
        t.noisy = True
        ev = t.evaluate
        t.evaluate = lambda x, s, rep: seen.append(rep) or ev(x, s, rep)
        P.measure(t, 5)
        self.assertEqual(seen, list(range(P.T_REPS_NOISY)))

    def test_tuning_prefers_defaults_on_ties_and_sees_only_dev_tasks(self):
        t = toy()
        chosen, report = P.tune_params([t], 128, [0], {'toy': P.reference_low(t)}, candidates_per_harness=2)
        self.assertEqual(set(chosen), set(P.HARNESSES))
        self.assertEqual(chosen['best_of_n'], P.DEFAULTS['best_of_n'])
        for h, rep in report.items():
            self.assertEqual(rep['settings'][0], P.DEFAULTS[h])
            for s in rep['settings']:
                self.assertTrue(all(s[k] in P.PARAM_SPACE[h][k] for k in P.PARAM_SPACE[h]))


class Domains(unittest.TestCase):
    def test_formula_task_has_its_optimum_in_the_language(self):
        splits = {s: PT.formula_items(91919400 + i, 120) for i, s in enumerate('AVT')}
        for fam, target in PT.FORMULA_TARGETS.items():
            t = PT.formula_task(fam, splits)
            self.assertAlmostEqual(t.evaluate(target, 'T', 0), 1.0)
            rng = random.Random(1)
            self.assertLess(statistics.median(t.evaluate(t.random(rng), 'T', 0) for _ in range(20)), 0.9)

    def test_acquire_task_scores_minus_experiments_needed(self):
        rows = PT.acquire_worlds('base', 91919500, 3)
        t = PT.acquire_task('base', {'A': rows[:1], 'V': rows[1:2], 'T': rows[2:]})
        for name, prog in t.info['references'].items():
            v = t.evaluate(prog, 'T', 0)
            self.assertLessEqual(v, 0)
            self.assertGreaterEqual(v, -rows[2]['prep']['p'])
        self.assertEqual(t.evaluate(t.info['references']['eig'], 'A', 0), t.evaluate(t.info['references']['eig'], 'A', 5))

    def test_mcx_task_is_relative_to_rex_and_checked(self):
        from genesis.candidate_kinds import mcx2 as K
        if K.binary_digest() != K.BINARY_SHA256:
            self.skipTest('the pinned mcx2 binary is not installed')
        gs = PT.mcx_graphs('torus', 91919600, 3)
        t = PT.mcx_task('torus', {'A': gs[:1], 'V': gs[1:2], 'T': gs[2:]}, seconds=0.01)
        self.assertTrue(t.noisy)
        v = t.evaluate(dict(K.DEFAULT), 'A', 0)
        self.assertGreater(v, 0.95)
        self.assertLess(v, 1.05)


if __name__ == '__main__':
    unittest.main()
