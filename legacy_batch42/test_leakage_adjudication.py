import unittest
from leakage_triage import triage
from leakage_adjudication import review

P=[{'id':'p','statement':'theorem foo (x : Nat) : x = x'}]
S=[{'id':'s','statement':'theorem foo (y : Nat) : y = y'}]

class TestReview(unittest.TestCase):
    def run_review(self, p=P, s=S, ds=None, digest=None, reviewer='reviewer', custodian='custodian'):
        if digest is None: digest=triage(p,s)['receipt_sha256']
        return review(p,s,[] if ds is None else ds,reviewer,custodian,digest)
    def decision(self, value='NOT_EQUIVALENT', rationale='Reviewed manually; distinct theorem meanings.'):
        return [{'sealed_id':'s','public_id':'p','decision':value,'rationale':rationale}]
    def test_unreviewed_blocks(self): self.assertEqual(self.run_review()['status'],'BLOCKED_INCOMPLETE_REVIEW')
    def test_confirmed_blocks(self): self.assertEqual(self.run_review(ds=self.decision('LEAK_CONFIRMED'))['status'],'BLOCKED_CONFIRMED_LEAK')
    def test_unresolved_blocks(self): self.assertEqual(self.run_review(ds=self.decision('UNRESOLVED'))['status'],'BLOCKED_UNRESOLVED')
    def test_review_does_not_promote(self):
        r=self.run_review(ds=self.decision()); self.assertEqual(r['status'],'DEV_REVIEWED_HEURISTIC_FLAGS'); self.assertFalse(r['semantic_leakage_cleared']); self.assertFalse(r['promotion_allowed'])
    def test_changed_tasks_blocks(self): self.assertEqual(self.run_review(s=[{'id':'s','statement':'True'}],digest=triage(P,S)['receipt_sha256'])['status'],'BLOCKED_TRIAGE_CHANGED')
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): self.run_review(ds=self.decision()*2)
    def test_unknown_rejected(self):
        with self.assertRaises(ValueError): self.run_review(ds=[{'sealed_id':'bad','public_id':'p','decision':'NOT_EQUIVALENT','rationale':'Definitely not equivalent'}])
    def test_bad_decision_rejected(self):
        with self.assertRaises(ValueError): self.run_review(ds=self.decision('SAFE'))
    def test_short_rationale_rejected(self):
        with self.assertRaises(ValueError): self.run_review(ds=self.decision(rationale='fine'))
    def test_same_reviewer_rejected(self):
        with self.assertRaises(ValueError): self.run_review(reviewer='custodian')
    def test_no_flags_not_clean(self):
        r=self.run_review(s=[{'id':'s','statement':'False'}]); self.assertEqual(r['status'],'DEV_NO_HEURISTIC_FLAGS'); self.assertFalse(r['semantic_leakage_cleared'])
    def test_hash_reproducible(self): self.assertEqual(self.run_review(ds=self.decision()),self.run_review(ds=self.decision()))

if __name__=='__main__': unittest.main()
