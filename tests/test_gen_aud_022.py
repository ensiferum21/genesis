"""GEN-AUD-022: public proof/digest substitution after valid admission."""
import unittest

from gap_engine.adapters.induction.checker import LemmaStore, CheckError, _proof_digest
from gap_engine.adapters.induction.theory import Theory, Equation


class ProofDigestTamperTest(unittest.TestCase):
    def setUp(self):
        self.store = LemmaStore(Theory.default())
        self.eq = Equation(('Z',), ('Z',))
        self.good = {'rule': 'rewrite', 'left': [], 'right': []}
        self.forged = {'rule': 'rewrite', 'left': [],
                       'right': [((), ('lemma', 'not_admitted'), 1, {})]}
        self.assertTrue(self.store.verify('valid', self.eq, self.good))

    def test_forged_proof_and_public_digest_not_acknowledged(self):
        self.store.proofs['valid'] = self.forged
        self.store.proof_digests['valid'] = _proof_digest(self.forged)
        with self.assertRaises(CheckError):
            self.store.verify('valid', self.eq, self.forged)

    def test_forged_evidence_cannot_admit_other_lemma(self):
        self.store.proofs['valid'] = self.forged
        self.store.proof_digests['valid'] = _proof_digest(self.forged)
        with self.assertRaises(CheckError):
            self.store.verify('other', self.eq, self.good)

    def test_order_mutation_blocks_all_new_admissions(self):
        self.store.order.append('valid')
        with self.assertRaises(CheckError):
            self.store.verify('other', self.eq, self.good)

    def test_digest_mutation_blocks_even_correct_idempotent(self):
        self.store.proof_digests['valid'] = '0' * 64
        with self.assertRaises(CheckError):
            self.store.verify('valid', self.eq, self.good)

    def test_unmodified_idempotence_and_replay(self):
        self.assertTrue(self.store.verify('valid', self.eq, self.good))
        self.assertTrue(self.store.replay_all())

    def test_legacy_without_trusted_digest_requires_replay(self):
        import pickle
        restored = pickle.loads(pickle.dumps(self.store))
        state = restored.__dict__.copy()
        state.pop('_trusted_proof_digests')
        restored.__setstate__(state)
        with self.assertRaises(CheckError):
            restored.verify('valid', self.eq, self.good)
        restored.replay_legacy()
        self.assertTrue(restored.verify('valid', self.eq, self.good))
        self.assertTrue(restored.replay_all())

if __name__ == '__main__':
    unittest.main()
