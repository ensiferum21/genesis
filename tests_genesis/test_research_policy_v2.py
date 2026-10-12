"""B20_R3 (B20R-OPEN-1): the cost-aware learned research policy.

Checks the redesign's two claims at unit level: preparation is linear in the pool (the B20_R2
policy recomputed development-target subterms for every pool equation), and the ranking is
expected useful lemmas per CPU second under a frozen, hash-checked model. Uses a deterministic
fake prover; no proof tool is needed.
"""
import unittest
from unittest import mock

from genesis.learning import equational as Q
from genesis.learning import research as RS
from genesis.learning.budget import Account, StudyBudget

FAKE_PROOF = "fof(c, plain, $false, inference(x, [], [file('p.p', ax0)])).\n"


def instant_prover(cpu_ns=1_000_000):
    def prover(axioms, goal, *, res, label):
        return {'status': 'THEOREM', 'proof': FAKE_PROOF,
                'resource': {'termination': 'EXITED', 'exit_code': 0, 'cpu_ns': cpu_ns, 'wall_ns': cpu_ns,
                             'meter': {'kind': 'fake', 'lower_bound': False}}}
    return prover


def pool():
    return Q.true_equations('ba_huntington', 4, per_bucket=3, seed=5)


def dev():
    return Q.sample_targets('ba_huntington', 6, min_total=6, max_total=8, max_term=4, seed=9, exclude=pool())


def neutral_model(**over):
    body = {'schema': RS.MODEL_V2, 'features': RS.FEATURE_NAMES_V2, 'w_prove': [0.0] * 8, 'w_use': [0.0] * 8,
            'cost_ok': 0.02, 'cost_ok_by_size': {}, 'cost_fail': 1.0, 'cost_floor': 0.005, 'examples': 0,
            'proved': 0, 'used': 0}
    body.update(over)
    body.pop('model_sha256', None)
    return dict(body, model_sha256=RS.digest(body))


class Features(unittest.TestCase):
    def test_shape_and_determinism(self):
        ctx = RS.dev_context(dev())
        for e in pool()[:10]:
            x = RS.features_v2(e, ctx)
            self.assertEqual(len(x), len(RS.FEATURE_NAMES_V2))
            self.assertEqual(x, RS.features_v2(e, RS.dev_context(dev())))
            self.assertTrue(0.0 <= x[6] <= 1.0)

    def test_preparation_is_linear_in_the_pool(self):
        """Development targets are decomposed once per reset, not once per pool equation."""
        p, d = pool(), dev()
        calls = []
        real = RS.eq_subterms
        with mock.patch.object(RS, 'eq_subterms', side_effect=lambda e: calls.append(e) or real(e)):
            RS.CostAware(neutral_model()).reset(p, d)
        self.assertLessEqual(len(calls), len(p) + len(d))
        calls.clear()
        with mock.patch.object(RS, 'eq_subterms', side_effect=lambda e: calls.append(e) or real(e)):
            RS.Learned([0.0] * 6).reset(p, d)
        self.assertGreaterEqual(len(calls), len(p) * len(d))      # the B20_R2 policy, for contrast


class Model(unittest.TestCase):
    def examples(self):
        ctx = RS.dev_context(dev())
        out = []
        for i, e in enumerate(pool()):
            n = Q.size(e[0]) + Q.size(e[1])
            out.append({'x': RS.features_v2(e, ctx), 'size': n, 'proved': int(n <= 3), 'cpu_s': 0.01 * n if n <= 3 else 1.0,
                        'used': int(n <= 2 and i % 2 == 0)})
        return out

    def test_fit_is_deterministic_and_hashed(self):
        a, b = RS.fit_cost_aware(self.examples()), RS.fit_cost_aware(self.examples())
        self.assertEqual(a, b)
        self.assertEqual(RS.model_problems(a), [])
        self.assertGreater(a['cost_fail'], a['cost_ok'])

    def test_tampered_or_foreign_model_is_refused(self):
        m = RS.fit_cost_aware(self.examples())
        bad = dict(m, w_use=[9.0] * 8)
        self.assertIn('MODEL_HASH', RS.model_problems(bad))
        with self.assertRaises(ValueError):
            RS.CostAware(bad)
        self.assertEqual(RS.model_problems({'weights': [1]}), ['MODEL_SCHEMA'])
        short = neutral_model(w_prove=[0.0] * 3)
        self.assertIn('MODEL_W_PROVE_SHAPE', RS.model_problems(short))


class Ranking(unittest.TestCase):
    def test_cheaper_first_when_value_is_equal(self):
        p = pool()
        m = neutral_model(cost_ok_by_size={str(n): 0.001 * n for n in range(12)}, cost_fail=0.5)
        pol = RS.CostAware(m)
        pol.reset(p, dev())
        sizes = [Q.size(e[0]) + Q.size(e[1]) for e in pol.order]
        self.assertEqual(sizes, sorted(sizes))

    def test_value_per_cost_beats_size(self):
        """A model that predicts use only for variable-side laws ranks them first."""
        w_use = [-4.0, 0, 0, 0, 8.0, 0, 0, 0]
        pol = RS.CostAware(neutral_model(w_use=w_use))
        pol.reset(pool(), dev())
        first = pol.order[0]
        self.assertTrue(first[0][0] == 'var' or first[1][0] == 'var')

    def test_choose_visits_each_untried_once(self):
        p = pool()
        pol = RS.CostAware(neutral_model())
        pol.reset(p, dev())
        untried, seen = set(p), []
        while untried:
            e = pol.choose(untried)
            self.assertIn(e, untried)
            untried.discard(e)
            seen.append(e)
        self.assertEqual(len(seen), len(set(p)))


class Labels(unittest.TestCase):
    def test_needed_lemmas_are_transitive_and_eligible_only(self):
        lib = [{'id': 'L0', 'uses': []}, {'id': 'L1', 'uses': ['L0']}, {'id': 'L2', 'uses': []}]
        ev = {'rows': [{'status': 'PROVED', 'lemmas_used': ['L1']},
                       {'status': 'PROVED_NOT_CREDITED', 'lemmas_used': ['L2']}]}
        self.assertEqual(RS.needed_lemmas(lib, ev), {'L0', 'L1'})

    def test_training_examples_from_a_run(self):
        p, d = pool()[:8], dev()
        a = Account(StudyBudget.from_seconds(5, attempt_s=1), label='t')
        res = RS.run('ba_huntington', RS.Fixed(), p, account=a, prover=instant_prover())
        lib = res['library']
        ev = {'rows': [{'status': 'PROVED', 'lemmas_used': [lib[1]['id']]}]}
        ex = RS.training_examples_v2(res, ev, d, {Q.text(e): e for e in p})
        self.assertEqual(len(ex), len(lib))
        used = {x['text'] for x in ex if x['used']}
        self.assertIn(lib[1]['text'], used)
        self.assertTrue(all(len(x['x']) == 8 and x['proved'] == 1 for x in ex))


class Run(unittest.TestCase):
    def test_preparation_charged_and_run_completes(self):
        p, d = pool(), dev()
        a = Account(StudyBudget.from_seconds(5, attempt_s=1), label='cost-aware')
        res = RS.run('ba_huntington', RS.CostAware(neutral_model()), p, account=a, dev_targets=d,
                     prover=instant_prover())
        self.assertEqual(res['policy'], 'learned2')
        self.assertGreater(res['account']['cpu_ns_by_category']['preparation'], 0)
        self.assertTrue(res['account']['within_cap'])
        self.assertEqual(len(res['library']), sum(Q.holds(e, 'or_not') for e in p))


if __name__ == '__main__':
    unittest.main()
