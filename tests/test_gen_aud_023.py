"""GEN-AUD-023: downstream solvers must not trust mutable public lemma registry."""
import unittest

from gap_engine.adapters.induction.adapter import InductionWorld
from gap_engine.adapters.induction.checker import LemmaStore, CheckError, check_proof
from gap_engine.adapters.induction.theory import Theory, Equation
from gap_engine.kernel.sealed import SealedStore
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.u4.dsl import ResearchContext


class PublicLemmaPremiseBypassTests(unittest.TestCase):
    def setUp(self):
        self.th = Theory.default()
        self.store = LemmaStore(self.th)
        self.refl = Equation(('Z',), ('Z',))
        self.false = Equation(('Z',), ('S', ('Z',)))
        self.store.verify('L', self.refl, {'rule': 'rewrite', 'left': [], 'right': []})
        self.world = InductionWorld('audit', self.th, self.store, ['L'], [],
                                    {'DEV': [self.false], 'SELECT': [], 'CONFIRM': []},
                                    SealedStore())

    def test_baseline_false_theorem_unsolved(self):
        self.assertEqual(self.world.run_library([], 'DEV', 1).tolist(), [0])

    def test_mutated_public_lemma_cannot_forge_solved_task(self):
        self.store.lemmas['L'] = self.false
        with self.assertRaises(CheckError):
            self.world.run_library([], 'DEV', 1)

    def test_direct_solver_rejects_forged_library(self):
        with self.assertRaises(CheckError):
            self.world.solve(self.false, {'L': self.false}, 1)

    def test_research_context_rejects_forged_library(self):
        ctx = ResearchContext(self.th, self.store, {'L': self.false}, BudgetBroker(total=10))
        with self.assertRaises(CheckError):
            ctx.lib()

    def test_mutating_other_lemma_fails_all_subsets(self):
        self.store.verify('OTHER', self.refl, {'rule': 'rewrite', 'left': [], 'right': []})
        self.store.lemmas['OTHER'] = self.false
        with self.assertRaises(CheckError):
            self.store.verified_subset(['L'])

    def test_raw_replay_requires_trusted_lemma_inputs(self):
        # This low-level API proves a *conditional* statement under premises.
        # It is NOT a trusted standalone proof admission interface.
        forged = {'rule': 'rewrite', 'left': [((), ('lemma', 'fake'), 1, {})], 'right': []}
        self.assertTrue(check_proof(self.th, {'fake': self.false}, self.false, forged))
        with self.assertRaises(CheckError):
            self.store.verified_subset(['fake'])

    def test_detached_world_theory_cannot_rewrite_false_statement(self):
        self.world.theory = self.th.copy()
        self.world.theory.defs['plus'][0].rhs = ('S', ('?', 'y'))
        false_def = Equation(*self.th.parser().parse_eq('plus Z Z = S Z'))
        self.world.tasks['DEV'] = [false_def]
        with self.assertRaisesRegex(CheckError, 'solver theory differs'):
            self.world.run_library([], 'DEV', 1)

    def test_research_context_theory_mismatch_fails_closed(self):
        other = self.th.copy()
        other.defs['plus'][0].rhs = ('S', ('?', 'y'))
        ctx = ResearchContext(other, self.store, {}, BudgetBroker(total=10))
        with self.assertRaisesRegex(CheckError, 'solver theory differs'):
            ctx.lib()

    def test_no_premise_substitution_after_replay(self):
        self.assertTrue(self.store.replay_all())
        self.assertEqual(self.store.verified_subset(['L']), {'L': self.refl})


if __name__ == '__main__':
    unittest.main()
