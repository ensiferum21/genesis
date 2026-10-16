"""B20_R42: registry v2 and the generated-rows reference wired into the custodian path. The wiring
is built for review and opt-in.

**Requests.**
  * A v5 request is a v4 request plus a closed `reference` route.
  * Arms go through `candidate_registry`: v1 descriptors take exactly the v1 path, v2 descriptors
    the v2 path.
  * v4 requests keep their meaning: v1 arms only, and the joint reference.

**Baselines.** An exact registry-v2 baseline can be a comparator only under a calibration rule
that names it. Today that is the DRAFT `e1-hard-v3-draft`, which the code knows, so records can be
checked, but no study has adopted.

**Reference.** The triangle-free adapter computes the generated-rows reference with custody, and
the C4 adapter refuses it.

**End to end.** With fixture keys and a synthetic calibration record, a custodian selects among
DSL and MIP baselines, evaluates a v5 request with the rows reference, and the judge agrees.
Nothing here is independent custody or an adopted rule.
"""
import json
from pathlib import Path
import sqlite3
import unittest
from unittest import mock

from genesis import calibration as CAL
from genesis import candidate_registry as CREG
from genesis import candidates as C1
from genesis import candidates_v2 as C2
from genesis import custodian as CU
from genesis.common import canonical, digest
from genesis.domains import ADAPTERS, Unsupported
from genesis.dsl import baseline_programs
from genesis.kernel import receipts as R
from genesis.store import Store
from genesis.verification import certificates_rows as CROWS
from tests_genesis.test_candidate_custody import Base, dsl_descriptor, rr_descriptor
from tests_genesis.test_evaluator_readiness import frozen_plan_and_record

ROOT = Path(__file__).resolve().parents[1]
TF, C4 = 'triangle_free_host_v1', 'c4_host_v2'
FAMILY = f'sealed_evaluation:{TF}'
PKG = json.loads((ROOT / 'evidence' / 'generator_v2_b20r37' / 'package.json').read_text())
REF = {'route': 'generated-rows-v1', 'package_sha256': digest(PKG), 'seconds': 60, 'separation_seconds': 15,
       'max_rows': 50000, 'max_total': 80000, 'order': 'dense-first', 'enumerator': 'fast', 'lp_rounding_seconds': 1.0}


def mip(rp, budget=0.5):
    return C2.build_descriptor('milp-highs-v1', TF, {'cpu_seconds': budget}, **rp)


def k(n, tid='t-k'):
    from genesis.models import GraphTask
    return GraphTask(task_id=tid, domain=TF, family='test', split='DEV', n=n,
                     edges=tuple((a, b) for a in range(n) for b in range(a + 1, n)))


def synthetic_record(rule, family='erdos', params=None):
    """A structurally valid calibration record (synthetic test fixture, not a measurement)."""
    rows = [{'task_id': f'syn-{i}', 'edges': 33, 'baselines': {'b': 20}, 'reference_seconds': 5.0,
             'reference': {'status': 'FINITE_CERTIFIED', 'value': 22}} for i in range(4)]
    summary = CAL.summarize(rows, rule)
    setting = {'index': 0, 'family': family, 'params': params or {'n': 12, 'p': 0.5}, 'rows': rows, 'summary': summary,
               'ineligible_because': CAL.eligible(summary, rule)}
    return {'schema': CAL.SCHEMA, 'domain': TF, 'splits_used': ['DEV'], 'rule': rule, 'settings': [setting],
            'selected': CAL.select([setting], rule), 'note': 'synthetic test fixture'}


class Dispatcher(unittest.TestCase):
    def test_v1_descriptors_take_the_v1_path_unchanged(self):
        d = rr_descriptor()
        self.assertIs(CREG.registry_of(d), C1)
        self.assertEqual(CREG.descriptor_problems(d, domain=TF), C1.descriptor_problems(d, domain=TF))
        self.assertEqual(CREG.descriptor_problems(d, domain=TF), [])
        frozen = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
        self.assertEqual(CREG.descriptor_problems(frozen, domain=TF), [])

    def test_v2_descriptors_take_the_v2_path_and_unknowns_are_refused(self):
        d2 = mip(rr_descriptor()['resource_profile'])
        self.assertIs(CREG.registry_of(d2), C2)
        self.assertEqual(CREG.descriptor_problems(d2, domain=TF), [])
        self.assertEqual(CREG.descriptor_problems(d2, domain=C4), ['descriptor domain differs from the task domain'])
        self.assertNotEqual(CREG.descriptor_problems({'schema': 'x'}), [])
        self.assertEqual(CREG.run(k(5), {'schema': 'x'}, seed=0)['status'], 'REFUSED')
        self.assertEqual(CREG.run(k(5), d2, seed=0, context={'manifest': {}})['status'], 'REFUSED')
        r = CREG.run(k(6), d2, seed=0, isolation='process')
        self.assertEqual((r['status'], r['result']['value'], r['registry']), ('SUCCESS', 9, C2.SCHEMA))

    def test_exact_baselines_only_under_a_rule_that_names_them(self):
        rp = rr_descriptor()['resource_profile']
        d2, dsl = mip(rp), dsl_descriptor('multistart', rp)
        self.assertTrue(CREG.is_conventional(dsl))
        self.assertFalse(CREG.is_conventional(d2))
        for rule in ('e1-hard-v2', 'e1-hard-v1', None):
            self.assertFalse(CREG.is_exact_baseline(d2, rule))
        self.assertTrue(CREG.is_exact_baseline(d2, 'e1-hard-v3-draft'))
        self.assertFalse(CREG.is_exact_baseline(dsl, 'e1-hard-v3-draft'))


class SchemaV5(unittest.TestCase):
    def setUp(self):
        self.desc = rr_descriptor()
        self.mip = mip(self.desc['resource_profile'])
        self.plan, _ = frozen_plan_and_record(family_id=FAMILY, family_size=3)
        self.req = {'schema': R.REQUEST_V5, 'campaign_id': 'a' * 64, 'claim_id': 'c', 'evidence_kind': 'sealed_evaluation',
                    'statement_hash': '5' * 64, 'scope': 's', 'generation_transition': None, 'transfer_source_domain': None,
                    'campaign_export_sha256': 'e' * 64, 'candidate_version': 'b' * 64, 'source_hash': 'c' * 64,
                    'arms': {'candidate': self.desc, 'baseline': self.mip}, 'seed': 1, 'task_count': 6, 'domain': TF,
                    'analysis': self.plan, 'exposed_graph_fingerprints': [], 'expected_evaluator_hash': 'c' * 64,
                    'reference': dict(REF)}

    def test_v5_takes_v2_arms_and_v4_does_not(self):
        arms = CU.validate_request(self.req)
        self.assertEqual(arms['baseline']['descriptor_id'], self.mip['descriptor_id'])
        self.assertTrue(R.descriptor_arms(self.req))
        self.assertEqual(R.check_request(self.req), [])
        v4 = {k: v for k, v in self.req.items() if k != 'reference'}
        v4['schema'] = R.REQUEST_V4
        with self.assertRaisesRegex(ValueError, 'candidate descriptor for arm baseline'):
            CU.validate_request(v4)
        with self.assertRaisesRegex(ValueError, 'evaluation request schema'):
            CU.validate_request(dict(v4, reference=dict(REF)))
        with self.assertRaisesRegex(ValueError, 'evaluation request schema'):
            CU.validate_request({k: v for k, v in self.req.items() if k != 'reference'})
        v4['arms'] = {'candidate': self.desc, 'baseline': dsl_descriptor('multistart', self.desc['resource_profile'])}
        self.assertEqual(set(CU.validate_request(v4)), {'candidate', 'baseline'})       # v4 unchanged

    def test_the_reference_route_is_closed(self):
        self.assertEqual(CU.reference_problems(REF), [])
        self.assertEqual(CU.reference_problems(dict(REF, lp_rounding_seconds=None)), [])
        for bad in ({'route': 'obstruction-v1'}, {'package_sha256': '0' * 64}, {'package_sha256': 'x'},
                    {'seconds': 0}, {'seconds': True}, {'separation_seconds': 601}, {'max_rows': 0},
                    {'max_total': 1.5}, {'order': 'random'}, {'enumerator': 'magic'}, {'lp_rounding_seconds': 0},
                    {'extra': 1}):
            self.assertNotEqual(CU.reference_problems(dict(REF, **bad)), [], bad)
        self.assertNotEqual(CU.reference_problems({k: v for k, v in REF.items() if k != 'order'}), [])
        with self.assertRaisesRegex(ValueError, 'reference route'):
            CU.validate_request(dict(self.req, reference=dict(REF, route='other')))

    def test_reference_options_follow_the_request_version(self):
        self.assertEqual(CU.reference_options(self.req, ADAPTERS[TF]), {'joint': True, 'rows': REF})
        with self.assertRaisesRegex(ValueError, 'offers no generated-rows-v1 reference'):
            CU.reference_options(dict(self.req, domain=C4), ADAPTERS[C4])
        v4 = dict({k: v for k, v in self.req.items() if k != 'reference'}, schema=R.REQUEST_V4)
        self.assertEqual(CU.reference_options(v4, ADAPTERS[TF]), {'joint': True})

    def test_the_draft_rule_checks_records_but_no_study_adopts_it(self):
        rule = CAL.SELECTION_RULE_E1_HARD_V3_DRAFT
        self.assertNotIn(rule, CAL.RULES)
        self.assertNotIn('e1-hard-v3-draft', CAL.RULES_BY_NAME)
        self.assertEqual(CAL.record_problems(synthetic_record(rule)), [])
        self.assertNotEqual(CAL.record_problems(synthetic_record(dict(rule, ceiling_rate_max=1.0))), [])
        cfg = json.loads((ROOT / CAL.CONFIG).read_text())
        adopted = {e.get('rule') for s in cfg.get('studies', {}).values() for e in s.values()}
        self.assertNotIn('e1-hard-v3-draft', adopted)
        import b20r41_e1d_readiness as M
        self.assertEqual(M.RULE, rule)


class RowsReference(unittest.TestCase):
    def test_triangle_free_adapter_computes_it_with_custody(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, Store(Path(d) / 'ev') as s:
            out = ADAPTERS[TF].reference(k(8), evidence=s, joint=True, rows=REF)
            self.assertEqual((out['status'], out['value']), ('FINITE_CERTIFIED', 16))       # Turán on K8
            self.assertTrue(out['method'].startswith('GENERATED_ROWS_'))
            self.assertEqual((out['route'], out['package_sha256']), (REF['route'], REF['package_sha256']))
            bundle = s.get(out['certificate_bundle'])
            if bundle['schema'] == CROWS.SCHEMA:
                rep = CROWS.replay(bundle, s.get_bytes)
            else:
                from genesis.verification.certificates import replay
                rep = replay(bundle, s.get_bytes)
            self.assertEqual((rep['lower'], rep['upper']), ('VALID', 'VALID'), rep)

    def test_small_hosts_keep_exact_search_and_c4_refuses(self):
        out = ADAPTERS[TF].reference(k(6), rows=REF)
        self.assertEqual((out['value'], out['method']), (9, 'DUAL_EXACT_SEARCH'))
        from genesis.models import GraphTask
        c4 = GraphTask(task_id='c', domain=C4, family='test', split='DEV', n=8,
                       edges=tuple((a, b) for a in range(8) for b in range(a + 1, 8)))
        self.assertIsInstance(ADAPTERS[C4].reference(c4, rows=REF), Unsupported)
        out = ADAPTERS[TF].reference(k(8), rows=dict(REF, package_sha256='0' * 64))
        self.assertIsInstance(out, Unsupported)


class EndToEndV5(Base):
    """Fixture keys and a synthetic calibration record: protocol behaviour only."""

    def setUp(self):
        super().setUp()
        a = ADAPTERS[TF]
        self.tasks, _, _ = a.generate(4242, 6, 'CONFIRM', 'erdos', {'n': 12, 'p': 0.5})   # the fixture plan needs 6
        self.assertTrue(all(len(t.edges) > ADAPTERS[TF].EXACT_MAX_EDGES for t in self.tasks))
        self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in self.tasks]))
        rp = self.desc['resource_profile']
        self.baselines = {f'{n}_tm': C1.build_descriptor('dsl-time-matched-v1', TF,
                                                         {'program': baseline_programs()[n].model_dump(mode='json'),
                                                          'cpu_seconds': 0.3}, **rp) for n in ('multistart', 'exchange')}
        self.baselines['milp_highs_tm'] = mip(rp, 0.3)

    def test_an_adopted_rule_refuses_the_exact_baseline(self):
        base, _ = self.export('base.zip')
        with mock.patch('genesis.calibration.load', return_value=synthetic_record(CAL.SELECTION_RULE_E1_HARD_V2)):
            with self.assertRaisesRegex(ValueError, 'milp_highs_tm is not a valid conventional baseline'):
                CU.select_comparator(self.root, base, self.baselines, self.cust[0], 'FIXTURE',
                                     exposure_manifest=self.manifest, task_count=3, study='fixture')

    def test_v5_evaluation_with_an_exact_baseline_and_the_rows_reference(self):
        from genesis import custody_records as CR
        from genesis.judge import recompute
        base, _ = self.export('base.zip')
        with mock.patch('genesis.calibration.load', return_value=synthetic_record(CAL.SELECTION_RULE_E1_HARD_V3_DRAFT)):
            env = CU.select_comparator(self.root, base, self.baselines, self.cust[0], 'FIXTURE',
                                       exposure_manifest=self.manifest, task_count=3, study='fixture')
        p = CU.verify(env, self.cust[1])
        self.assertEqual(set(p['baselines']), set(self.baselines))
        self.assertEqual(p['calibration']['rule'], 'e1-hard-v3-draft')
        export, frozen = self.export('selected.zip', selection=env)
        chosen = p['baselines'][p['selected']]
        arms = {'candidate': self.desc, 'baseline': chosen}
        if p['selected'] != 'milp_highs_tm':
            arms['milp_highs_tm'] = p['baselines']['milp_highs_tm']
        req = dict(self.request(export, frozen, arms=arms, claim='v5-claim'), schema=R.REQUEST_V5, reference=dict(REF))
        v4 = {k: v for k, v in req.items() if k != 'reference'}
        v4.update(schema=R.REQUEST_V4, claim_id='v4-with-v2-arm')
        with self.assertRaisesRegex(ValueError, 'candidate descriptor'):
            self.reg(v4, export)                      # a v4 request still takes registry-v1 arms only
        self.reg(req, export)
        rid = digest(req)
        receipt = CU.evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')
        q = CU.verify(receipt, self.cust[1])
        self.assertEqual((q['schema'], q['completed_rows'], q['expected_rows']),
                         (R.SCIENTIFIC_RECEIPT_V4, 6 * len(arms), 6 * len(arms)))
        self.assertEqual(q['baseline_descriptor_id'], chosen['descriptor_id'])
        log, problems = CR.check_log(CU.registration_log(self.root, self.cust[0]), self.cust[1], CU.verify)
        self.assertEqual(problems, [])
        judged = recompute(self.root / 'evaluations' / rid, req, receipt, registration_log_entries=log['entries'])
        self.assertTrue(judged['agrees'], judged['problems'])
        with Store(self.root / 'evaluations' / rid) as s:
            optima = v2_runs = 0
            for _, req_h, rec_h in s.db.execute('SELECT status,request,receipt FROM attempts'):
                a, r = s.get(req_h), s.get(rec_h)
                if a.get('kind') == 'exact-check':
                    optima += 1
                    self.assertTrue(r['result']['method'].startswith('GENERATED_ROWS_'), r['result'])
                    self.assertEqual(r['result']['package_sha256'], REF['package_sha256'])
                    bundle = s.get(r['result']['certificate_bundle'])
                    if bundle['schema'] == CROWS.SCHEMA:
                        self.assertEqual(CROWS.replay(bundle, s.get_bytes)['upper'], 'VALID')
                elif a.get('kind') == 'solver' and a['descriptor']['schema'] == C2.SCHEMA:
                    v2_runs += 1
                    self.assertEqual((r['status'], r['isolation'], r['registry']), ('SUCCESS', R.ISOLATION_V4, C2.SCHEMA))
            self.assertEqual((optima, v2_runs), (6, 6))
        db = sqlite3.connect(self.root / 'custody.sqlite3')
        self.assertEqual(db.execute('SELECT state FROM requests WHERE id=?', (rid,)).fetchone()[0], 'COMPLETE')
        db.close()
        with self.assertRaisesRegex(FileExistsError, 'consumed'):
            CU.evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')          # no second draw


if __name__ == '__main__':
    unittest.main()
