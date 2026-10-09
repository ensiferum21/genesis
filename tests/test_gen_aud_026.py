"""GEN-AUD-026: frozen prereg budget must match signed run's pinned prereg.

Synthetic signer and task pool only. No external custody, no sealed experiment.
"""
import json
from custody_reference.evaluator import canonical
from tests.test_gen_aud_025 import SignedPartialRunTests


class FrozenBudgetTests(SignedPartialRunTests):
    def test_valid_receipt_wrong_claimed_budget_rejected(self):
        with self.assertRaisesRegex(ValueError, 'budget differs'):
            self.verify(expected_prereg_budget_per_arm=999)

    def test_prereg_bytes_missing_rejected(self):
        with self.assertRaisesRegex(ValueError, 'bytes required'):
            self.verify(expected_prereg_bytes=None)

    def test_forged_budget_bytes_rejected_by_hash(self):
        modified=json.loads(self.prereg.read_bytes())
        modified['evaluation_budget_per_arm']=999
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.verify(expected_prereg_bytes=canonical(modified), expected_prereg_budget_per_arm=999)

    def test_noncanonical_prereg_bytes_rejected(self):
        original=self.prereg.read_bytes()
        with self.assertRaisesRegex(ValueError, 'noncanonical'):
            self.verify(expected_prereg_bytes=original+b' ')

    def test_wrong_campaign_in_pinned_document_rejected(self):
        with self.assertRaisesRegex(ValueError, 'campaign differs'):
            self.verify(expected_campaign_id='wrong-campaign')

    def test_original_budget_and_frozen_document_pass_only_dev(self):
        result=self.verify()
        self.assertTrue(result['expected_prereg_budget_matched'])
        self.assertFalse(result['independent_custody_proven'])
        self.assertFalse(result['promotion_allowed'])
