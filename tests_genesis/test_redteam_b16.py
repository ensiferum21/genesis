"""B16 internal red-team pass (same operator; not independent review).

R1  family shopping: a requester naming a fresh hypothesis family per candidate.
R2  plan swap: a result computed under one plan presented with another.
R3  registration-log chain rewritten and re-signed by the custodian key.
R4  evidence store extended after sealing, then handed to the judge.
R5  legacy (ANALYSIS_V1) receipts in a family with several registrations.
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from genesis import custody_records as CR
from genesis.common import canonical, digest
from genesis.custodian import evaluate, registration_log, sign, verify
from genesis.judge import recompute
from genesis.kernel import receipts as R
from genesis.kernel.analysis import analyze
from genesis.store import Store
import tests_genesis.test_evaluator_readiness as ER   # module import: its own test classes are not re-run here

frozen_plan_and_record = ER.frozen_plan_and_record


class R1FamilyShopping(ER.CustodianV2Flow):
    def test_requester_cannot_choose_its_own_family(self):
        plan, record = frozen_plan_and_record(family_id='candidate-7-private-family', family_size=1)
        req, export = self.request('a' * 64, 'shop', plan)
        with self.assertRaisesRegex(ValueError, 'assigned by the custodian'):
            self.reg(req, export, record)

    # inherited flow tests run in test_evaluator_readiness
    test_full_v2_evaluation_is_recomputable_and_logged = None
    test_family_size_outstanding_and_holm_inputs = None
    test_family_size_cannot_be_redeclared = None

    def test_r3_rewritten_log_chain_is_detected_even_when_signed(self):
        plan, record = frozen_plan_and_record()
        req, export = self.request('a' * 64, 'chain', plan)
        self.reg(req, export, record)
        log = registration_log(self.root, self.cust[0])
        entries = copy.deepcopy(log['payload']['entries'])
        entries[0]['claim_id'] = 'renamed-after-the-fact'
        resigned = sign({**log['payload'], 'entries': entries}, self.cust[0])
        payload, problems = CR.check_log(resigned, self.cust[1], verify)
        self.assertTrue(any('head does not match' in p or 'breaks the chain' in p for p in problems), problems)

    def test_r4_evidence_extended_after_sealing_is_detected_by_the_judge(self):
        plan, record = frozen_plan_and_record()
        req, export = self.request('a' * 64, 'extended', plan)
        self.reg(req, export, record)
        rid = digest(req)
        receipt = evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')
        copy_dir = Path(self.tmp.name) / 'tampered'
        shutil.copytree(self.root / 'evaluations' / rid, copy_dir)
        with Store(copy_dir) as s:
            s.event('LATE_EDIT', {'note': 'appended after the receipt was signed'})
        out = recompute(copy_dir, req, receipt)
        self.assertFalse(out['agrees'])
        self.assertIn('the evidence store does not end at the signed raw_evidence_root', out['problems'])


class R2PlanSwap(ER.KernelV3):
    def test_result_from_another_plan_contradicts(self):
        lenient, _ = frozen_plan_and_record(family_size=1)
        lenient = dict(lenient, minimum_useful_effect=0.1, design_effect=0.2)

        def swap(p):
            rows = [{'task_id': f'a-{i}', 'stratum': 'a', 'status': 'SCORED',
                     'candidate': {'value': 21, 'run': 'SUCCESS', 'cpu_ns': 1},
                     'baseline': {'value': 20, 'run': 'SUCCESS', 'cpu_ns': 1}} for i in range(10)]
            p['analysis_result'] = analyze(rows, lenient)
            p['outcome'] = 'SUPPORTED'
        p = self.promote('swapped', {'a': [0, 1, -1, 0, 1], 'b': [1, -1, 0, 0, -1]}, tamper=swap)
        self.assertNotEqual(R.derive_outcome(p), 'SUPPORTED')
        self.assertTrue(R.check_receipt(p, 'sealed_evaluation'))

    test_supported_v3_receipt_licenses_confirmation = None
    test_not_supported_v3_receipt_does_not = None
    test_signed_but_internally_forged_result_is_rejected = None


class R5LegacyFamilies(ER.ReleasePreflightV3):
    def test_v1_receipt_in_a_crowded_family_is_blocked(self):
        req = self.fx.request(claim_id='legacy', task_count=40)
        anchor = self.fx.anchor(req)
        receipt = self.fx.receipt(req, anchor, wins=35, losses=1, ties=4, family_p=0.001)
        audit = sign({'request_hash': digest(req), 'receipt_hash': digest(receipt), 'status': 'PASS',
                      'open_critical': 0, 'independent_operation_verified': True, 'raw_replay_verified': True,
                      'formal_replay_verified': True}, self.keys['auditor'][0])
        entries = []
        other = dict(req, claim_id='legacy-sibling', candidate_version='e' * 64)
        for r in (req, other):
            entries.append(CR.new_entry(entries, 'REGISTERED', {'request_hash': digest(r), 'family': CR.family_of(r),
                                                                'family_size': CR.family_size_of(r)}))
        entries.append(CR.new_entry(entries, 'PUBLISHED', {'request_hash': digest(req), 'family': CR.family_of(req),
                                                           'receipt_sha256': digest(receipt), 'outcome': 'SUPPORTED',
                                                           'p_value': 0.001}))
        log = CR.export_log(entries, sign, self.keys['custodian'][0])
        out = self.preflight(req, anchor, receipt, audit, registration_log=log,
                             control_declarations=self.declarations())
        self.assertTrue(any('ANALYSIS_V1 has no multiplicity correction' in r for r in out['reasons']), out['reasons'])
        self.assertEqual(out['registration_family']['outstanding'], [digest(other)])

    test_ready_only_with_log_and_independent_declarations = None
    test_shared_control_is_limited_and_disclosed = None
    test_missing_log_or_declarations_block = None
    test_multiplicity_inputs_must_match_the_log = None
    test_log_signed_by_another_key_blocks = None


if __name__ == '__main__':
    unittest.main()
