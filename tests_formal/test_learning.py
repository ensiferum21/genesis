"""B20: the equational research environment, policies, macros and memory (W18–W20)."""
import json
from pathlib import Path
import random
import unittest

from genesis.fol import parse
from genesis.learning import equational as Q
from genesis.learning import macros as M
from genesis.learning import memory as MEM
from genesis.learning import research as RS
from genesis.verification.tools import ToolUnavailable, tool

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'learning_b20'


def eq(text):
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    return (f[1], f[2])


def _eprover():
    try:
        tool('eprover')
        return True
    except ToolUnavailable:
        return False


class Deciders(unittest.TestCase):
    def test_axioms_hold_in_their_variety(self):
        for name, spec in Q.SYSTEMS.items():
            for a in spec['axioms']:
                self.assertTrue(Q.holds(eq(a), spec['decider']), (name, a))

    def test_known_truths_and_falsehoods(self):
        self.assertTrue(Q.holds(eq('![X,Y]: s(X,Y) = s(Y,X)'), 'nand'))
        self.assertFalse(Q.holds(eq('![X]: s(X,X) = X'), 'nand'))
        self.assertTrue(Q.holds(eq('![X,Y]: inv(mul(X,Y)) = mul(inv(Y),inv(X))'), 'free_group'))
        self.assertFalse(Q.holds(eq('![X,Y]: mul(X,Y) = mul(Y,X)'), 'free_group'))
        self.assertTrue(Q.holds(eq('![X,Y]: div(X,div(Y,Y)) = X'), 'free_group'))
        self.assertTrue(Q.holds(eq('![X]: plus(X,X) = zero'), 'xor_and'))
        self.assertTrue(Q.holds(eq('![X,Y,Z]: join(X,meet(Y,Z)) = meet(join(X,Y),join(X,Z))'), 'lattice2'))

    def test_pools_are_exact_and_canonical(self):
        T = Q.true_equations('ba_sheffer', 4, per_bucket=3)
        F = Q.false_equations('ba_sheffer', 4, 8, seed=1)
        self.assertTrue(all(Q.holds(e, 'nand') for e in T))
        self.assertFalse(any(Q.holds(e, 'nand') for e in F))
        self.assertEqual(len({Q.canon(e) for e in T}), len(T))
        self.assertEqual(Q.canon(eq('![A,B]: s(B,A) = s(A,B)')), Q.canon(eq('![X,Y]: s(X,Y) = s(Y,X)')))

    def test_targets_avoid_the_pool(self):
        pool = Q.true_equations('ba_sheffer', 4, per_bucket=3)
        T = Q.sample_targets('ba_sheffer', 10, min_total=5, max_total=8, seed=3, exclude=pool)
        self.assertEqual(len(T), 10)
        self.assertFalse({Q.canon(e) for e in T} & {Q.canon(e) for e in pool})
        self.assertTrue(all(5 <= Q.size(a) + Q.size(b) <= 8 for a, b in T))


class Policies(unittest.TestCase):
    def setUp(self):
        self.pool = Q.true_equations('ba_sheffer', 4, per_bucket=3)
        self.dev = Q.sample_targets('ba_sheffer', 4, min_total=5, max_total=8, seed=1, exclude=self.pool)

    def test_choices_are_deterministic_and_from_the_untried_set(self):
        for P in (RS.Fixed(), RS.Random(3), RS.Heuristic(), RS.Bandit(), RS.Learned([0.1] * 6)):
            P.reset(self.pool, self.dev)
            untried = set(self.pool[:10])
            a = P.choose(untried)
            self.assertIn(a, untried)
            P2 = type(P)([0.1] * 6) if isinstance(P, RS.Learned) else type(P)(3 if isinstance(P, RS.Random) else 0)
            P2.reset(self.pool, self.dev)
            self.assertEqual(P2.choose(untried), a)

    def test_logistic_fit_separates_a_separable_set(self):
        rng = random.Random(0)
        X = [[1.0, rng.random()] for _ in range(60)]
        y = [int(x[1] > 0.5) for x in X]
        w = RS.fit_logistic(X, y, steps=800)
        acc = sum((RS.predict(w, x) > 0.5) == bool(t) for x, t in zip(X, y)) / len(y)
        self.assertGreater(acc, 0.9)

    def test_proof_premise_extraction(self):
        proof = "fof(ax0, axiom, a, file('/t/p.p', ax0)).\nfof(ax3, axiom, b, file('/t/p.p', ax3))."
        self.assertEqual(RS.used_inputs(proof, 3), [0])
        self.assertEqual(RS.used_inputs(proof, 4), [0, 3])


class MacrosAndMemory(unittest.TestCase):
    def macro(self):
        mk = lambda t, d: {'schema': eq(t), 'text': t, 'depends_on': d, 'budget_s': 1, 'source_lemma': 'L'}
        return {'schema': M.SCHEMA, 'name': 'm', 'source_system': 'ba_sheffer', 'precondition': {'ops': {'s': 2}},
                'steps': [mk('![X,Y]: s(X,Y) = s(Y,X)', []), mk('![X]: s(s(X,X),s(X,X)) = X', [0]),
                          mk('![X,Y]: s(X,s(Y,s(Y,Y))) = s(X,X)', [1]), mk('![X]: s(X,s(X,X)) = s(X,s(X,X))', [])],
                'revoked': [], 'resource_bound_s': 4, 'macro_sha256': 'x'}

    def test_revocation_invalidates_dependents_transitively(self):
        m = M.revoke(self.macro(), 0, 'test')
        self.assertEqual([s['text'] for s in m['steps']], ['![X]: s(X,s(X,X)) = s(X,s(X,X))'])
        self.assertEqual(m['revoked'][0]['invalidated'], [0, 1, 2])
        m2 = M.revoke(self.macro(), 2, 'test')
        self.assertEqual(len(m2['steps']), 3)
        self.assertEqual(m2['steps'][2]['depends_on'], [])

    def test_preconditions(self):
        self.assertTrue(M.applicable(self.macro(), 'ba_wolfram'))
        self.assertFalse(M.applicable(self.macro(), 'ba_huntington'))

    def test_contamination_screen(self):
        exact = eq('![X,Y]: s(s(X,Y),s(X,Y)) = s(s(Y,X),s(Y,X))')
        inst = eq('![X,Y]: s(s(X,X),Y) = s(Y,s(X,X))')                 # commutativity, instantiated
        mem = [{'eq': Q.canon(exact), 'text': 'exact', 'id': 'a'},
               {'eq': eq('![X,Y]: s(X,Y) = s(Y,X)'), 'text': 'general', 'id': 'b'},
               {'eq': eq('![X]: s(s(X,X),s(X,X)) = X'), 'text': 'unrelated', 'id': 'c'}]
        keep, excluded = MEM.screen(mem, [exact, inst])
        self.assertEqual([m['id'] for m in keep], ['c'])
        self.assertEqual(sorted(x['reason'] for x in excluded), ['EXACT', 'INSTANCE'])

    def test_curriculum_variants_are_valid_and_easier(self):
        t = eq('![X,Y]: s(X,s(Y,s(Y,Y))) = s(X,X)')
        vs = MEM.variants(t, 'nand')
        self.assertTrue(vs)
        for v in vs:
            self.assertEqual(v['valid'], Q.holds(v['eq'], 'nand'))
            self.assertEqual(v['source'], Q.text(t))


@unittest.skipUnless(_eprover(), 'E prover unavailable')
class Runs(unittest.TestCase):
    def test_a_short_run_and_its_successor(self):
        pool = Q.true_equations('ba_sheffer', 4, per_bucket=3) + Q.false_equations('ba_sheffer', 4, 5, seed=2)
        dev = Q.sample_targets('ba_sheffer', 3, min_total=5, max_total=7, seed=4, exclude=pool)
        res = RS.run('ba_sheffer', RS.Fixed(), pool, budget_s=2.0, dev_targets=dev, prove_s=1)
        self.assertTrue(res['library'])
        self.assertTrue(all(Q.holds(l['eq'], 'nand') for l in res['library']))     # only true lemmas enter
        # B20_R1 (Repair B): the repaired loop also records a chosen conjecture it could not
        # afford (NOT_ATTEMPTED, last step only, with the stop reason) and proofs from attempts
        # that were not eligible for credit (PROVED_NOT_CREDITED). SCREENED_OUT needs a screen.
        outcomes = [t['outcome'] for t in res['trajectory']]
        self.assertTrue(set(outcomes) <= {'PROVED', 'UNPROVED', 'FALSE', 'PROVED_NOT_CREDITED', 'NOT_ATTEMPTED'})
        self.assertNotIn('NOT_ATTEMPTED', outcomes[:-1])
        if outcomes[-1] == 'NOT_ATTEMPTED':
            self.assertEqual(res['trajectory'][-1]['reason'], res['account']['stop_reason'])
        self.assertLessEqual(res['account']['cpu_ns_total'], 2 * 10 ** 9)
        self.assertEqual(len(res['library']), outcomes.count('PROVED'))
        ev = RS.evaluate_successor('ba_sheffer', res['library'], dev, eval_s=1)
        self.assertEqual(ev['targets'], 3)
        lab = RS.usefulness_labels(res, ev)
        self.assertEqual(set(lab), {t['eq'] for t in res['trajectory']})

    def test_macro_induction_and_faithful_replay(self):
        pool = Q.true_equations('ba_sheffer', 4, per_bucket=3)
        dev = Q.sample_targets('ba_sheffer', 4, min_total=5, max_total=7, seed=5, exclude=pool)
        res = RS.run('ba_sheffer', RS.Fixed(), pool, budget_s=3.0, dev_targets=dev, prove_s=1)
        ev = RS.evaluate_successor('ba_sheffer', res['library'], dev, eval_s=1)
        macro = M.induce(res, ev, name='t')
        self.assertLessEqual(len(macro['steps']), len(res['library']))
        if macro['steps']:
            self.assertTrue(M.replay_faithful(macro)['faithful'])


def _lean():
    try:
        from genesis import sandbox
        from genesis.formal_research import workspace as W
        W.environment()
        return sandbox.available()
    except Exception:
        return False


@unittest.skipUnless(_eprover() and _lean(), 'E prover or formal workspace unavailable')
class LemmaChains(unittest.TestCase):
    def test_a_target_proof_with_library_lemmas_replays_in_lean(self):
        from genesis.formal_research import fof_lean as F
        s = 'ba_sheffer'
        pool = Q.true_equations(s, 4, per_bucket=3)
        T = Q.sample_targets(s, 6, min_total=6, max_total=8, seed=9, exclude=pool)
        res = RS.run(s, RS.Fixed(), pool, budget_s=1000, dev_targets=T, prove_s=1)      # exhausts the pool
        ev = RS.evaluate_successor(s, res['library'], T, eval_s=1)
        row = next(r for r in ev['rows'] if r['status'] == 'PROVED' and r['lemmas_used'])
        entries, gd, gp = RS.lean_chain(res['library'], row['proof'], row['premise_ids'], len(Q.axioms(s)))
        self.assertTrue(entries)
        rec = F.replay('t-chain-b20', Q.axioms(s), Q.closed(row['eq']), row['proof'], lemmas=entries,
                       goal_deps=gd, goal_positions=gp)
        self.assertEqual(rec['status'], 'THEOREM_CHECKED', rec)
        # a chain whose first lemma is swapped for another true equation does not replay
        other = Q.closed(eq('![X,Y]: s(X,Y) = s(Y,X)'))
        if other != entries[0][0]:
            tampered = [(other,) + tuple(entries[0][1:])] + entries[1:]
            bad = F.replay('t-chain-b20-bad', Q.axioms(s), Q.closed(row['eq']), row['proof'], lemmas=tampered,
                           goal_deps=gd, goal_positions=gp)
            self.assertEqual(bad['status'], 'NOT_REPLAYED')

    def test_chain_structure_is_checked(self):
        from genesis.formal_research import fof_lean as F
        ax = Q.axioms('ba_sheffer')
        g = Q.closed(eq('![X,Y]: s(X,Y) = s(Y,X)'))
        self.assertIn('not earlier', F.proof_module('t', ax, g, 'x', lemmas=[(g, 'x', [0])])[1])
        self.assertIn('unknown lemma', F.proof_module('t', ax, g, 'x', lemmas=[], goal_deps=[0])[1])


@unittest.skipUnless((EVIDENCE / 'summary.json').exists(), 'B20 evidence not generated')
class Evidence(unittest.TestCase):
    def test_recorded(self):
        from genesis.common import digest
        s = json.loads((EVIDENCE / 'summary.json').read_text())
        self.assertIn('UNESTABLISHED', s['e3']['claim'])
        pol = json.loads((EVIDENCE / 'train' / 'policy.json').read_text())
        self.assertTrue(pol['frozen_before_evaluation'])
        self.assertEqual(digest(pol['weights']), pol['weights_sha256'])
        self.assertEqual(s['policy_weights_sha256'], pol['weights_sha256'])
        self.assertTrue(all(m['faithful'] for m in s['w18']['macros'].values()))
        self.assertGreaterEqual(s['lean']['checked'], s['lean']['target_proofs_with_lemmas'] - 1)

    def test_hard_system_records(self):
        pol = json.loads((EVIDENCE / 'train' / 'policy.json').read_text())
        for f in sorted((EVIDENCE / 'e3_hard').glob('seed_*.json')):
            r = json.loads(f.read_text())
            self.assertEqual(r['policy_weights_sha256'], pol['weights_sha256'])     # the frozen policy, unchanged
            self.assertEqual(set(r['policies']), {'fixed', 'random', 'heuristic', 'bandit', 'learned'})
        cc = json.loads((EVIDENCE / 'curriculum_control.json').read_text())
        for row in cc['rows']:
            self.assertEqual(set(row['scores']), {'plain', 'curriculum', 'both'})
            self.assertEqual(row['empty'], 0)


if __name__ == '__main__':
    unittest.main()
