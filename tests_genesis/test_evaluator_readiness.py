"""B16 evaluator readiness (W05-W07) end to end, with fixture roles.

Fixture keys prove protocol behaviour only; nothing here is independent custody.
"""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from genesis import custody_records as CR
from genesis import decision_record as DR
from genesis.common import canonical, code_identity, digest
from genesis.custodian import evaluate, register, registration_log, sign, verify
from genesis.domains import ADAPTERS
from genesis.judge import recompute
from genesis.kernel import receipts as R
from genesis.kernel.analysis import PLAN_SCHEMA, SENSITIVITY, analyze, plan_core
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.models import Limits
from genesis.power import required_sample
from genesis.store import Store
from tests_genesis.signed_fixtures import SignedFixture, campaign_export, record_evaluation

ROOT = Path(__file__).resolve().parents[1]
SRC = 'c' * 64


def base_plan(family_id='sealed_evaluation:c4_host_v2', family_size=2):
    return {'schema': PLAN_SCHEMA, 'primary': 'paired-edge-difference', 'estimand': 'mean-of-stratum-means',
            'strata': 'family', 'minimum_useful_effect': 1.0, 'design_effect': 2.0, 'alpha': 0.05,
            'power_target': 0.8, 'test': 'stratified-sign-flip',
            'interval': {'method': 'stratified-bootstrap-percentile', 'level': 0.9, 'resamples': 2000},
            'multiplicity': {'method': 'holm', 'family_id': family_id, 'family_size': family_size},
            'stopping': {'rule': 'single-analysis'}, 'failures': 'score-zero', 'unsupported': 'exclude-and-report',
            'max_unsupported_fraction': 0.2, 'cost': {'measure': 'cpu_ns', 'max_ratio': None},
            'regression': {'max_stratum_loss': None}, 'sensitivity': list(SENSITIVITY),
            'decision_rule': 'superiority-with-minimum-useful-effect', 'decision_record_sha256': '0' * 64}


def pilot_rows():
    rows = []
    for s, diffs in (('dev-a', [2, 3, 2, 2, 3, 2]), ('dev-b', [2, 2, 3, 2, 2, 3])):
        for i, d in enumerate(diffs):
            rows.append({'task_id': f'{s}-{i}', 'stratum': s, 'status': 'SCORED', 'split': 'DEV', 'optimum': 26,
                         'candidate': {'value': 20 + d, 'run': 'SUCCESS', 'cpu_ns': 1},
                         'baseline': {'value': 20, 'run': 'SUCCESS', 'cpu_ns': 1}})
    return rows


def frozen_plan_and_record(**plan_kw):
    plan = base_plan(**plan_kw)
    # Fixture panels are tiny, so the fixture states a floor of 2 tasks per family (a recorded design choice).
    power = required_sample(pilot_rows(), plan, sims=60, min_tasks_per_stratum=2, grid=(2, 3, 4, 6, 8))
    record = DR.build(plan_core_dict=plan_core(plan), power=power,
                      exact_claim='frozen candidate beats the frozen baseline on sealed c4 hosts (fixture)',
                      capability_changes='none beyond the frozen candidate program (fixture)',
                      permissible_information='public DEV panels only; no sealed task visible (fixture)',
                      baselines={'baseline': 'strongest frozen DEV baseline'},
                      total_budget={'queries_per_run': Limits().queries, 'arms': 2},
                      exposure_policy='custodian-built registry plus campaign export; panel retired after use',
                      raw_evidence_custody='custodian private store; judge recomputes from raw receipts',
                      roles={'custodian': 'fixture', 'auditor': 'fixture', 'release_authority': 'fixture'},
                      rejection_criteria='any plan check failing, or the registered decision rule not met',
                      allowed_conclusion='a scoped better-solver statement on this sealed panel only')
    frozen, h = DR.freeze(record)
    plan['decision_record_sha256'] = h
    return plan, frozen


class DecisionRecord(unittest.TestCase):
    def test_consistent_record_passes_and_inconsistencies_fail(self):
        plan, frozen = frozen_plan_and_record()
        self.assertEqual(DR.problems(frozen, plan, task_count=100, require_frozen=True), [])
        draft = dict(frozen, status='DRAFT')
        self.assertTrue(any('FROZEN' in p for p in DR.problems(draft, plan, require_frozen=True)))
        other = dict(plan, alpha=0.01, interval=dict(plan['interval'], level=0.98))
        self.assertTrue(any('differs from the one embedded' in p for p in DR.problems(frozen, other)))
        self.assertTrue(any('below the' in p for p in DR.problems(frozen, plan, task_count=1)))
        vague = dict(frozen, allowed_conclusion='ok')
        self.assertTrue(any('allowed_conclusion' in p for p in DR.problems(vague)))
        wrong_power = copy.deepcopy(frozen)
        wrong_power['sample_size_justification']['plan_core_sha256'] = '1' * 64
        self.assertTrue(any('different plan' in p for p in DR.problems(wrong_power)))


class KernelV3(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name + '/store'); self.addCleanup(self.store.close)
        self.fx = SignedFixture(self.tmp.name)
        self.fx.bind_store(self.store)
        self.k = EvidenceKernel.with_fixture_registry(self.store, self.fx.registry)
        self.run = self.k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign',
                                 source_hash=SRC, verdict='VALID', effects=['UNCHECKED_PROPOSAL'])
        self.plan, _ = frozen_plan_and_record(family_size=1)

    def v3(self, request, anchor, diffs):
        rows = [{'task_id': f'{s}-{i}', 'stratum': s, 'status': 'SCORED',
                 'candidate': {'value': 20 + d, 'run': 'SUCCESS', 'cpu_ns': 1},
                 'baseline': {'value': 20, 'run': 'SUCCESS', 'cpu_ns': 1}}
                for s, ds in diffs.items() for i, d in enumerate(ds)]
        result = analyze(rows, self.plan)
        p = self.fx.receipt_payload(request, anchor, wins=result['wins'], losses=result['losses'],
                                    ties=result['ties'], family_p=result['p_value'])
        p.update(schema=R.SCIENTIFIC_RECEIPT_V3, analysis=self.plan, analysis_result=result,
                 expected_rows=2 * len(rows), completed_rows=2 * len(rows), task_count=len(rows))
        p['outcome'] = R.derive_outcome(p)
        return p

    def promote(self, claim, diffs, *, tamper=None):
        request = self.fx.request(claim_id=claim)
        request['analysis'] = self.plan
        self.assertEqual(R.check_request(request), [])
        anchor = self.fx.anchor(request)
        payload = self.v3(request, anchor, diffs)
        if tamper:
            tamper(payload)
        receipt = self.fx.sign(payload, 'custodian')
        _, node = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor, receipt=receipt)
        self.k.create_claim(claim, SignedFixture.STATEMENT, SignedFixture.SCOPE, [node],
                            binding=R.binding_from_requests([request]))
        return payload

    def test_supported_v3_receipt_licenses_confirmation(self):
        p = self.promote('v3-yes', {'a': [3, 2, 3, 2, 3], 'b': [2, 3, 3, 2, 2]})
        self.assertEqual((p['outcome'], R.check_receipt(p, 'sealed_evaluation')), ('SUPPORTED', []))
        self.k.promote('v3-yes', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertEqual(self.k.levels('v3-yes')['utility'], 'CONFIRMED_SAME_DOMAIN')

    def test_not_supported_v3_receipt_does_not(self):
        p = self.promote('v3-no', {'a': [0, 1, -1, 0, 1], 'b': [1, -1, 0, 0, -1]})
        self.assertEqual(p['outcome'], 'NOT_SUPPORTED')
        with self.assertRaises(PromotionRejected):
            self.k.promote('v3-no', 'utility', 'CONFIRMED_SAME_DOMAIN')

    def test_signed_but_internally_forged_result_is_rejected(self):
        def forge(p):
            p['analysis_result']['checks'] = {k: True for k in p['analysis_result']['checks']}
            p['outcome'] = 'SUPPORTED'
        p = self.promote('v3-forged', {'a': [0, 1, -1, 0, 1], 'b': [1, -1, 0, 0, -1]}, tamper=forge)
        self.assertTrue(any('contradicts' in x for x in R.check_receipt(p, 'sealed_evaluation')))
        with self.assertRaises(PromotionRejected):
            self.k.promote('v3-forged', 'utility', 'CONFIRMED_SAME_DOMAIN')


def keyfile(directory, name):
    k = Ed25519PrivateKey.generate()
    path = Path(directory) / f'{name}.pem'
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    return path, base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                              serialization.PublicFormat.Raw)).decode()


class CustodianV2Flow(unittest.TestCase):
    """Real register -> evaluate -> publish -> judge, with a v2 plan and decision record."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.root.chmod(0o700)
        self.prereg = keyfile(self.root, 'prereg'); self.cust = keyfile(self.root, 'custodian')
        self.source = code_identity(ROOT)['sha256']
        self.manifest = self.root / 'exposure_manifest.json'
        self.manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
        self.manifest.chmod(0o600)
        a = ADAPTERS['c4_host_v2']
        t1, seen, _ = a.generate(41, 3, 'CONFIRM', 'erdos', {'n': 9, 'p': 0.5})
        t2, seen, _ = a.generate(42, 3, 'CONFIRM', 'erdos', {'n': 10, 'p': 0.45}, excluded=seen)
        self.tasks = t1 + t2
        self.pool = self.root / 'pool.json'
        self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in self.tasks]))

    def request(self, campaign, claim, plan):
        export, frozen = campaign_export(self.root, campaign_id=campaign, source_hash=self.source,
                                         name=f'export-{campaign[:4]}.zip')
        from genesis.common import bytes_hash
        req = {'schema': 'genesis-evaluation-request-v3', 'campaign_id': campaign,
               'candidate_version': frozen['candidate_version'], 'claim_id': claim,
               'evidence_kind': 'sealed_evaluation', 'generation_transition': None,
               'statement_hash': '5' * 64, 'scope': 'fixture panel', 'transfer_source_domain': None,
               'campaign_export_sha256': bytes_hash(export.read_bytes()), 'source_hash': self.source,
               'programs': frozen['programs'], 'limits': Limits().model_dump(mode='json'), 'seed': 42,
               'task_count': len(self.tasks), 'domain': 'c4_host_v2', 'analysis': plan,
               'exposed_graph_fingerprints': [], 'expected_evaluator_hash': self.source}
        return req, export

    def reg(self, req, export, record):
        return register(self.root, req, self.prereg[0], 'FIXTURE', exposure_manifest=self.manifest,
                        campaign_export=export, pool=self.pool, decision_record=record)

    def test_full_v2_evaluation_is_recomputable_and_logged(self):
        plan, record = frozen_plan_and_record()
        req, export = self.request('a' * 64, 'v2-claim', plan)
        with self.assertRaisesRegex(ValueError, 'decision record'):
            self.reg(req, export, None)
        with self.assertRaisesRegex(ValueError, 'FROZEN'):
            self.reg(req, export, dict(record, status='DRAFT'))
        anchor = self.reg(req, export, record)
        rid = digest(req)
        receipt = evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')
        p = verify(receipt, self.cust[1])
        self.assertEqual(p['schema'], R.SCIENTIFIC_RECEIPT_V3)
        self.assertEqual(R.check_receipt(p, 'sealed_evaluation'), [])
        self.assertEqual(p['outcome'], R.derive_outcome(p))
        result = p['analysis_result']
        self.assertEqual((result['strata'], result['scored'], result['family_p_values']), (2, 6, []))
        self.assertEqual(p['outcome'], result['decision'])
        log = registration_log(self.root, self.cust[0])
        payload, problems = CR.check_log(log, self.cust[1], verify)
        self.assertEqual(problems, [])
        self.assertEqual([e['kind'] for e in payload['entries']], ['REGISTERED', 'RESERVED', 'PUBLISHED'])
        self.assertEqual(CR.receipt_log_problems(payload['entries'], req, receipt)[0], [])
        judged = recompute(self.root / 'evaluations' / rid, req, receipt, registration_log_entries=payload['entries'])
        self.assertTrue(judged['agrees'], judged['problems'])
        self.assertEqual(judged['recomputed_outcome'], p['outcome'])
        # W07 resources: ground truth is accounted separately from both arms, and the arms were paired.
        acct = judged['resource_account']
        self.assertEqual(acct['ground_truth']['attempts'], 6)
        self.assertFalse(acct['ground_truth']['charged_to_arm'])
        self.assertEqual(sorted(acct['inference']['by_arm']), ['baseline', 'candidate'])
        self.assertEqual({a: v['attempts'] for a, v in acct['inference']['by_arm'].items()},
                         {'baseline': 6, 'candidate': 6})
        self.assertEqual((judged['fairness']['problems'], judged['fairness']['paired_tasks']), ([], 6))
        # A judge is not fooled by an edited (unsigned) result.
        edited = copy.deepcopy(receipt); edited['payload']['analysis_result']['estimate'] = 99.0
        self.assertFalse(recompute(self.root / 'evaluations' / rid, req, edited,
                                   registration_log_entries=payload['entries'])['agrees'])
        self.assertEqual(json.loads(json.dumps(anchor))['payload']['request_hash'], rid)

    def test_family_size_outstanding_and_holm_inputs(self):
        plan, record = frozen_plan_and_record(family_size=2)
        first, ex1 = self.request('a' * 64, 'fam-1', plan)
        second, ex2 = self.request('b' * 64, 'fam-2', plan)
        third, ex3 = self.request('d' * 64, 'fam-3', plan)
        self.reg(first, ex1, record)
        a = ADAPTERS['c4_host_v2']
        t3, seen, _ = a.generate(51, 3, 'CONFIRM', 'erdos', {'n': 9, 'p': 0.5})
        t4, _, _ = a.generate(52, 3, 'CONFIRM', 'erdos', {'n': 10, 'p': 0.45}, excluded=seen)
        pool2 = self.root / 'pool2.json'
        pool2.write_bytes(canonical([t.model_dump(mode='json') for t in t3 + t4]))
        register(self.root, second, self.prereg[0], 'FIXTURE', exposure_manifest=self.manifest,
                 campaign_export=ex2, pool=pool2, decision_record=record)
        with self.assertRaisesRegex(ValueError, 'already holds 2 of its declared 2'):
            self.reg(third, ex3, record)
        r1 = evaluate(self.root, digest(first), self.pool, self.cust[0], 'FIXTURE')
        log, _ = CR.check_log(registration_log(self.root, self.cust[0]), self.cust[1], verify)
        state = CR.family_state(log['entries'], 'sealed_evaluation:c4_host_v2')
        self.assertEqual(state['outstanding'], [digest(second)])     # B15-OPEN-1: visible to everyone
        p1 = r1['payload']['analysis_result'].get('p_value')
        r2 = evaluate(self.root, digest(second), pool2, self.cust[0], 'FIXTURE')
        used = r2['payload']['analysis_result'].get('family_p_values')
        if p1 is not None and r2['payload']['analysis_result']['decision'] != 'INVALID':
            self.assertEqual(used, [round(p1, 10)])                    # Holm saw the published first result
        log, _ = CR.check_log(registration_log(self.root, self.cust[0]), self.cust[1], verify)
        self.assertEqual(CR.family_state(log['entries'], 'sealed_evaluation:c4_host_v2')['outstanding'], [])
        for req, rec in ((first, r1), (second, r2)):
            self.assertEqual(CR.receipt_log_problems(log['entries'], req, rec)[0], [])

    def test_family_size_cannot_be_redeclared(self):
        plan, record = frozen_plan_and_record(family_size=2)
        req, ex = self.request('a' * 64, 'fam-x', plan)
        self.reg(req, ex, record)
        plan3, record3 = frozen_plan_and_record(family_size=3)
        req3, ex3 = self.request('b' * 64, 'fam-y', plan3)
        with self.assertRaisesRegex(ValueError, 'was declared with size'):
            self.reg(req3, ex3, record3)


class ReleasePreflightV3(unittest.TestCase):
    """Preflight with signed log and control declarations, run as an unprivileged child against an
    externally owned trust root (the only way to make 'external control' real on one machine)."""

    def setUp(self):
        if os.geteuid() != 0:
            self.skipTest('needs root to drop to an unprivileged UID')
        self.tmp = tempfile.TemporaryDirectory(dir='/tmp'); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.base.chmod(0o755)
        secrets = self.base / 'secrets'; secrets.mkdir(mode=0o700)
        self.keys = {n: keyfile(secrets, n) for n in ('custodian', 'prereg', 'auditor', 'release', 'root')}
        trust = self.base / 'trust'; trust.mkdir()
        (trust / 'root.pub').write_text(self.keys['root'][1])
        roles = {'custodian_key': self.keys['custodian'][1], 'prereg_key': self.keys['prereg'][1],
                 'auditor_key': self.keys['auditor'][1], 'release_key': self.keys['release'][1],
                 'release_authority_id': 'external-release-board'}
        (trust / 'roles.json').write_bytes(canonical(sign({'schema': 'genesis-role-registry-v1', 'roles': roles},
                                                          self.keys['root'][0])))
        for p in (trust / 'root.pub', trust / 'roles.json'):
            os.chown(p, 0, 0); p.chmod(0o444)
        os.chown(trust, 0, 0); trust.chmod(0o755)
        self.trust = trust
        fx = SignedFixture.__new__(SignedFixture)
        fx.keys = {'custodian': self.keys['custodian'], 'prereg': self.keys['prereg'],
                   'auditor': self.keys['auditor'], 'release': self.keys['release']}
        fx._tick = 0
        self.fx = fx
        self.plan, _ = frozen_plan_and_record(family_size=1)

    def release(self, diffs, *, family_p=()):
        req = self.fx.request(claim_id='release-v3', task_count=sum(len(d) for d in diffs.values()))
        req['analysis'] = self.plan
        anchor = self.fx.anchor(req)
        rows = [{'task_id': f'{s}-{i}', 'stratum': s, 'status': 'SCORED',
                 'candidate': {'value': 20 + d, 'run': 'SUCCESS', 'cpu_ns': 1},
                 'baseline': {'value': 20, 'run': 'SUCCESS', 'cpu_ns': 1}}
                for s, ds in diffs.items() for i, d in enumerate(ds)]
        result = analyze(rows, self.plan, family_p_values=family_p)
        p = self.fx.receipt_payload(req, anchor, wins=result['wins'], losses=result['losses'], ties=result['ties'],
                                    family_p=result['p_value'])
        p.update(schema=R.SCIENTIFIC_RECEIPT_V3, analysis=self.plan, analysis_result=result,
                 expected_rows=2 * len(rows), completed_rows=2 * len(rows), task_count=len(rows))
        p['outcome'] = R.derive_outcome(p)
        receipt = self.fx.sign(p, 'custodian')
        audit = sign({'request_hash': digest(req), 'receipt_hash': digest(receipt), 'status': 'PASS',
                      'open_critical': 0, 'independent_operation_verified': True, 'raw_replay_verified': True,
                      'formal_replay_verified': True}, self.keys['auditor'][0])
        entries = []
        entries.append(CR.new_entry(entries, 'REGISTERED', {
            'request_hash': digest(req), 'family': CR.family_of(req), 'family_size': CR.family_size_of(req)}))
        entries.append(CR.new_entry(entries, 'PUBLISHED', {
            'request_hash': digest(req), 'family': CR.family_of(req), 'receipt_sha256': digest(receipt),
            'outcome': p['outcome'], 'p_value': result['p_value']}))
        log = CR.export_log(entries, sign, self.keys['custodian'][0])
        return req, anchor, receipt, audit, log

    def declarations(self, shared=False):
        decl = {}
        for role, key in (('custodian', 'custodian'), ('auditor', 'auditor'), ('release_authority', 'release')):
            controller = 'one-operator' if shared else f'{role}-org'
            payload = CR.declaration(role, controller, machines=[f'{role}-host'], keys=[self.keys[key][1]],
                                     data=[f'{role}-data'], analysis=[f'{role}-analysis'],
                                     research_operator='research-lab' if role == 'custodian' else None)
            decl[role] = sign(payload, self.keys[key][0])
        return decl

    def preflight(self, *args, **kw):
        code = ('import json,sys;from genesis.custodian import release_preflight;a=json.loads(sys.stdin.read());'
                f'print(json.dumps(release_preflight(*a["args"],trust_root={str(self.trust)!r},**a["kw"])))')
        proc = subprocess.run([sys.executable, '-c', code], input=json.dumps({'args': list(args), 'kw': kw}),
                              capture_output=True, text=True, cwd='/', timeout=120, user=65534, group=65534,
                              extra_groups=[], env={'PYTHONPATH': str(ROOT / 'src'), 'PATH': '/usr/bin:/bin',
                                                    'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    STRONG = {'a': [3, 2, 3, 2, 3], 'b': [2, 3, 3, 2, 2]}

    def test_ready_only_with_log_and_independent_declarations(self):
        req, anchor, receipt, audit, log = self.release(self.STRONG)
        out = self.preflight(req, anchor, receipt, audit, registration_log=log,
                             control_declarations=self.declarations())
        self.assertEqual(out['status'], 'EXTERNAL_RELEASE_REVIEW_READY', out['reasons'])
        self.assertEqual(out['independence']['status'], 'INDEPENDENT')
        self.assertEqual(out['registration_family']['outstanding'], [])

    def test_shared_control_is_limited_and_disclosed(self):
        req, anchor, receipt, audit, log = self.release(self.STRONG)
        out = self.preflight(req, anchor, receipt, audit, registration_log=log,
                             control_declarations=self.declarations(shared=True))
        self.assertEqual(out['status'], 'LIMITED_SAME_OPERATOR')
        self.assertIn('operator-attested', out['independence']['limitation'])

    def test_missing_log_or_declarations_block(self):
        req, anchor, receipt, audit, log = self.release(self.STRONG)
        out = self.preflight(req, anchor, receipt, audit, control_declarations=self.declarations())
        self.assertIn('a v3 receipt needs the custodian-signed public registration log', out['reasons'])
        out = self.preflight(req, anchor, receipt, audit, registration_log=log)
        self.assertTrue(any('control declarations' in r for r in out['reasons']))

    def test_multiplicity_inputs_must_match_the_log(self):
        # The receipt claims a family p-value that the public log never published.
        req, anchor, receipt, audit, log = self.release(self.STRONG, family_p=[0.5])
        out = self.preflight(req, anchor, receipt, audit, registration_log=log,
                             control_declarations=self.declarations())
        self.assertIn('the multiplicity correction did not use exactly the family results published before it',
                      out['reasons'])

    def test_log_signed_by_another_key_blocks(self):
        req, anchor, receipt, audit, log = self.release(self.STRONG)
        forged = CR.export_log(log['payload']['entries'], sign, self.keys['auditor'][0])
        out = self.preflight(req, anchor, receipt, audit, registration_log=forged,
                             control_declarations=self.declarations())
        self.assertTrue(any('registration log signature' in r for r in out['reasons']))


if __name__ == '__main__':
    unittest.main()
