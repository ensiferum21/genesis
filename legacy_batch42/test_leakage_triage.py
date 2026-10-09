import unittest
from leakage_triage import tokenize, fingerprint, triage
class TestLeakageTriage(unittest.TestCase):
    def test_token_equal(self):
        r=triage([{'id':'p','statement':'theorem foo : Nat = Nat'}],[{'id':'s','statement':'theorem  foo : Nat = Nat'}]); self.assertIn('TOKEN_EQUAL',r['flags'][0]['reasons'])
    def test_alpha(self):
        r=triage([{'id':'p','statement':'∀ x : Nat, x = x'}],[{'id':'s','statement':'∀ y : Nat, y = y'}]); self.assertIn('ALPHA_HEURISTIC',r['flags'][0]['reasons'])
    def test_no_clearance(self):
        r=triage([{'id':'p','statement':'P'}],[{'id':'s','statement':'Q'}]); self.assertFalse(r['semantic_leakage_cleared']); self.assertFalse(r['promotion_allowed'])
    def test_id(self):
        r=triage([{'id':'same','statement':'P'}],[{'id':'same','statement':'Q'}]); self.assertIn('ID_COLLISION',r['flags'][0]['reasons'])
    def test_malformed(self):
        with self.assertRaises(ValueError): triage([{'id':'p'}],[])
    def test_empty_statement(self):
        with self.assertRaises(ValueError): tokenize(' ')
    def test_stable(self):
        a=[{'id':'a','statement':'∀ x, x = x'}]; b=[{'id':'b','statement':'∀ y, y = y'}]
        self.assertEqual(triage(a,b),triage(a,b))
    def test_not_claiming_lean_ast(self):
        self.assertNotIn('semantic_leakage_cleared',triage([],[])['flags'])
if __name__=='__main__':unittest.main()
