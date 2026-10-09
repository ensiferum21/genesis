"""Adversarial DEV tests for GEN-AUD-009 and legacy theory pinning."""
import unittest
from gap_engine.adapters.induction.theory import Theory, Equation
from gap_engine.adapters.induction.checker import LemmaStore, CheckError, check_proof
from gap_engine.adapters.induction.terms import V


class TheorySnapshotGateTests(unittest.TestCase):
    def setUp(self):
        self.th = Theory.default()
        self.st = LemmaStore(self.th)
        self.false = Equation(*self.th.parser().parse_eq('plus Z Z = S Z'))
        self.forge = {'rule':'rewrite','left':[((),('def','plus',0),1,{'y':('Z',)})],'right':[]}

    def test_exact_independent_audit_mutation_rejected(self):
        original = self.th.defs['plus'][0].rhs
        try:
            self.th.defs['plus'][0].rhs = ('S', V('y'))
            with self.assertRaisesRegex(CheckError,'theory differs'):
                self.st.verify('FORGED',self.false,self.forge)
        finally:
            self.th.defs['plus'][0].rhs = original
        self.assertNotIn('FORGED',self.st.lemmas)
        with self.assertRaises(CheckError):
            self.st.verify('FORGED2',self.false,{'rule':'rewrite','left':[((),('lemma','FORGED'),1,{'y':('Z',)})],'right':[]})

    def test_mutating_signature_detected(self):
        self.th.funs['plus'] = (('List','Nat'),'Nat')
        with self.assertRaisesRegex(CheckError,'theory differs'):
            self.st.verify('L',Equation(('Z',),('Z',)),{'rule':'rewrite','left':[],'right':[]})

    def test_mutating_trusted_snapshot_detected(self):
        self.st._trusted_theory.defs['plus'][0].rhs = ('S', V('y'))
        with self.assertRaisesRegex(CheckError,'theory differs'):
            self.st.verify('L',Equation(('Z',),('Z',)),{'rule':'rewrite','left':[],'right':[]})

    def test_separate_counterfactual_world_works(self):
        world=self.th.copy()
        world.defs['plus'][0].rhs=('S',V('y'))
        other=LemmaStore(world)
        self.assertTrue(other.verify('COUNTERFACTUAL',self.false,self.forge))
        with self.assertRaises(CheckError):
            self.st.verify('FALSE_BASE',self.false,self.forge)
        self.assertNotIn('COUNTERFACTUAL',self.st.lemmas)

    def test_full_replay_catches_forged_trusted_registry(self):
        refl={'rule':'rewrite','left':[],'right':[]}
        self.st.verify('L',Equation(('Z',),('Z',)),refl)
        self.assertTrue(self.st.replay_all())
        self.st.lemmas['L']=self.false
        self.st._trusted_lemmas['L']=self.false
        with self.assertRaises(CheckError):
            self.st.replay_all()

    def test_full_replay_catches_mutated_proof(self):
        refl={'rule':'rewrite','left':[],'right':[]}
        self.st.verify('L',Equation(('Z',),('Z',)),refl)
        self.st.proofs['L']['rule']='induction'
        with self.assertRaises(CheckError):
            self.st.replay_all()

    def test_full_replay_catches_order_injection(self):
        self.st.verify('L',Equation(('Z',),('Z',)),{'rule':'rewrite','left':[],'right':[]})
        self.st.order.append('L')
        with self.assertRaisesRegex(CheckError,'evidence registry mismatch'):
            self.st.replay_all()

    def test_unpinned_pickle_fails_closed(self):
        refl={'rule':'rewrite','left':[],'right':[]}
        self.st.verify('L',Equation(('Z',),('Z',)),refl)
        state=dict(self.st.__dict__)
        for key in ('_trusted_lemmas','_trusted_theory','_pinned_theory_sha256'):
            state.pop(key,None)
        restored=LemmaStore.__new__(LemmaStore)
        restored.__setstate__(state)
        with self.assertRaisesRegex(CheckError,'trusted original theory required'):
            restored.replay_legacy()
        with self.assertRaisesRegex(CheckError,'legacy lemma registry requires'):
            restored.verify('X',Equation(('Z',),('Z',)),refl)
        restored.replay_legacy(trusted_theory=Theory.default())
        self.assertTrue(restored.verify('X',Equation(('Z',),('Z',)),refl))

    def test_unpinned_legacy_rejects_changed_theory(self):
        refl={'rule':'rewrite','left':[],'right':[]}
        self.st.verify('L',Equation(('Z',),('Z',)),refl)
        state=dict(self.st.__dict__)
        for key in ('_trusted_lemmas','_trusted_theory','_pinned_theory_sha256'):
            state.pop(key,None)
        restored=LemmaStore.__new__(LemmaStore)
        restored.__setstate__(state)
        restored.theory.defs['plus'][0].rhs=('S',V('y'))
        with self.assertRaisesRegex(CheckError,'legacy theory differs'):
            restored.replay_legacy(trusted_theory=Theory.default())

    def test_prepopulated_store_does_not_bootstrap_trust(self):
        st=LemmaStore(Theory.default(),lemmas={'FAKE':self.false})
        with self.assertRaisesRegex(CheckError,'requires full proof replay'):
            st.verify('L',self.false,self.forge)


if __name__=='__main__': unittest.main()
