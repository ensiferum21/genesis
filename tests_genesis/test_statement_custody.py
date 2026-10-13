"""B20_R7 (handoff s13.3; B20R5-OPEN-1): sealed statement panels and frozen research successors.

The custodian generates an equational statement panel itself, after the research froze, from a
preregistered spec and a private seed; screens it against everything the research saw and
everything already sealed; runs each arm's frozen successor (formal-research-successor-v1) in
the OCI sandbox; and replays every claimed proof in Lean from custody. The judge recomputes the
analysis and replays every claim again from the raw store alone. Fixture keys prove protocol
behaviour only; nothing here is independent custody or a scientific result.
"""
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from genesis import candidates as C
from genesis import custody_records as CR
from genesis import sandbox as S
from genesis.common import bytes_hash, canonical, code_identity, digest
from genesis.custodian import (evaluate, evaluate_statements, recover, register, register_statements, registration_log,
                               screen_for_research, statement_export_problems, campaign_facts, validate_request, verify)
from genesis.judge import recompute
from genesis.kernel import receipts as R
from genesis.learning import custody as CU
from genesis.learning import equational as Q
from genesis.learning import research as RS
from genesis.learning import research_export as RX
from genesis.learning import statement_panels as SP
from genesis.learning.budget import Account, StudyBudget
from tests_genesis.test_crash_consistency import crash
from tests_genesis.test_evaluator_readiness import frozen_plan_and_record, keyfile

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = 'ba_huntington'
DOMAIN = SP.statement_domain(SYSTEM)
FAMILY = f'sealed_evaluation:{DOMAIN}'


def spec(**over):
    s = {'schema': SP.SPEC_SCHEMA, 'system': SYSTEM, 'ranges': [[7, 10], [9, 12]], 'per_range': 3, 'max_term': 5,
         'inclusion': 'valid-screened', 'trivial_limit_s': None}
    s.update(over)
    return s


class Research:
    """One small fixed-policy research run and the empty-library successor, frozen per test case."""

    @classmethod
    def build(cls, root, campaign='a' * 64, name='research'):
        pool = Q.true_equations(SYSTEM, 4, per_bucket=3, seed=5)
        budget = StudyBudget.from_seconds(4, attempt_s=1, enforcement='OUTER_SUPERVISED', quantum_ns=100_000_000)
        run = RS.run(SYSTEM, RS.Fixed(), pool, account=Account(budget, label='fixed'), prove_s=1, premise_k=8,
                     run_id=f'{name}-fixed')
        objs = CU.ObjectStore(Path(root) / f'{name}-objects')
        cand = CU.successor_manifest(run, objs)
        base = CU.successor_manifest({'run_id': f'{name}-empty', 'system': SYSTEM, 'library': [], 'policy': 'empty',
                                      'account': {}}, objs)
        source = code_identity(ROOT)['sha256']
        frozen = RX.freeze(Path(root) / name, Path(root) / f'{name}.zip', campaign_id=campaign, source_hash=source,
                           candidate=cand, baseline=base, objects=objs,
                           exposure=[('pool', Q.text(e)) for e in pool], origin='B20_R7 fixture', premise_k=8,
                           prove_seconds=1)
        return {'frozen': frozen, 'pool': pool, 'candidate': cand, 'baseline': base, 'objects': objs,
                'source': source, 'campaign': campaign}


class Base(unittest.TestCase):
    def setUp(self):
        if not S.available():
            self.fail('B20_R7 statement custody needs the OCI sandbox (root with runc); the release matrix runs as root')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.root.chmod(0o700)
        self.prereg = keyfile(self.root, 'prereg'); self.cust = keyfile(self.root, 'custodian')
        self.manifest = self.root / 'exposure_manifest.json'
        self.manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
        self.manifest.chmod(0o600)
        self.r = Research.build(self.root)
        self.plan, self.record = frozen_plan_and_record(family_id=FAMILY, family_size=2)

    def request(self, r=None, *, panel_spec=None, claim='st-claim', **over):
        r = r or self.r
        req = RX.statement_request(r['frozen'], campaign_id=r['campaign'], source_hash=r['source'], analysis=self.plan,
                                   panel_spec=panel_spec or spec(), seed=7, claim_id=claim,
                                   statement='the frozen successor proves more sealed statements than the baseline',
                                   scope='fixture statement panel')
        req.update(over)
        return req

    def reg(self, req, export=None):
        return register_statements(self.root, req, self.prereg[0], 'FIXTURE', exposure_manifest=self.manifest,
                                   campaign_export=export or self.r['frozen']['export'], decision_record=self.record)

    def state(self, rid):
        db = sqlite3.connect(self.root / 'custody.sqlite3')
        try:
            row = db.execute('SELECT state FROM requests WHERE id=?', (rid,)).fetchone()
            return row[0] if row else None
        finally:
            db.close()

    def panel(self, rid):
        return json.loads((self.root / 'statement_panels' / f'{rid}.json').read_text())['panel']


class PanelGenerator(unittest.TestCase):
    def test_spec_is_exact_and_bound_to_the_domain_and_count(self):
        self.assertEqual(SP.spec_problems(spec(), domain=DOMAIN, task_count=6), [])
        for bad in (dict(spec(), extra=1), spec(system='nope'), spec(ranges=[[9, 7]]), spec(ranges=[]),
                    spec(per_range=0), spec(max_term=9), spec(inclusion='cherry-picked'),
                    spec(inclusion='valid-screened-nontrivial'), spec(trivial_limit_s=1)):
            self.assertTrue(SP.spec_problems(bad), bad)
        self.assertTrue(SP.spec_problems(spec(), domain='eq_ba_sheffer_v1'))
        self.assertTrue(SP.spec_problems(spec(), task_count=5))

    def test_same_seed_same_panel_and_exposure_is_screened(self):
        a, rec = SP.generate(spec(), private_seed='11' * 16, exposure=[])
        b, _ = SP.generate(spec(), private_seed='11' * 16, exposure=[])
        self.assertEqual(a, b)
        self.assertEqual(SP.panel_problems(a), [])
        self.assertEqual(rec['statements'], 6)
        self.assertIn('residual_pretraining_exposure', rec)
        seen = [(SYSTEM, SP.eq_of(x['statement']), 'pool') for x in a['statements']]
        c, rec2 = SP.generate(spec(), private_seed='11' * 16, exposure=seen)
        self.assertFalse({x['structural_sha256'] for x in a['statements']} & {x['structural_sha256'] for x in c['statements']})
        rejected = sum(sum(v['rejected_counts'].values()) for v in rec2['per_stratum'].values())
        self.assertGreaterEqual(rejected, 1)
        # Theory is variety + signature: Huntington exposure also screens a Robbins panel.
        r_seen = [('ba_huntington', SP.eq_of(x['statement']), 'pool') for x in a['statements']]
        d, rec3 = SP.generate(spec(system='ba_robbins'), private_seed='11' * 16, exposure=r_seen)
        self.assertFalse({x['structural_sha256'] for x in a['statements']} & {x['structural_sha256'] for x in d['statements']})

    def test_insufficient_material_refuses_instead_of_shrinking(self):
        with self.assertRaises(SP.PanelError) as ctx:
            SP.generate(spec(ranges=[[2, 2]], per_range=200), private_seed='22' * 16, exposure=[])
        self.assertEqual(ctx.exception.code, 'INSUFFICIENT_DISTINCT_MATERIAL')

    def test_tampered_panel_is_detected(self):
        a, _ = SP.generate(spec(), private_seed='33' * 16, exposure=[])
        b = copy.deepcopy(a); b['statements'][0]['statement'] = '![X]: (plus(X,X) = n(X))'
        self.assertTrue(SP.panel_problems(b))


class Runner(Base):
    def test_formal_kind_contract(self):
        desc = self.r['frozen']['candidate']
        task = {'task_id': 'T1', 'statement': Q.text(Q.sample_targets(SYSTEM, 1, min_total=7, max_total=10, seed=3)[0]),
                'domain': DOMAIN}
        self.assertEqual(C.run(task, desc, seed=1, isolation='process',
                               context={'manifest': self.r['candidate']})['problems'], ['ISOLATION_REQUIRED'])
        self.assertEqual(C.run(task, desc, seed=1, isolation='runc', context={'manifest': self.r['baseline']})['problems'],
                         ['MANIFEST_MISMATCH'])
        self.assertIn('DOMAIN_MISMATCH', C.run(dict(task, domain='eq_ba_sheffer_v1'), desc, seed=1, isolation='runc',
                                                context={'manifest': self.r['candidate']})['problems'])
        seen = []
        real = S.run

        def spy(files, argv, policy=None, **kw):
            seen.append((dict(files), kw))
            return real(files, argv, policy, **kw)
        with mock.patch.object(S, 'run', side_effect=spy):
            r = C.run(task, desc, seed=1, isolation='runc', context={'manifest': self.r['candidate']})
        self.assertEqual((r['status'], r['isolation']), ('SUCCESS', R.ISOLATION_V4))
        self.assertIn(r['result']['claim'], ('PROOF', 'NO_PROOF'))
        files, kw = seen[0]
        child = json.loads(files['request.json'])
        self.assertEqual(set(child), {'view', 'kind', 'parameters', 'library', 'cpu_seconds', 'queries', 'seed'})
        self.assertEqual(set(child['view']), {'domain', 'statement'})
        self.assertNotIn('T1', files['request.json'].decode())
        self.assertEqual(set(kw['ro_mounts']), {C.SOURCE_MOUNT, C.TOOLCHAIN_MOUNT, C.TOOLS_MOUNT})
        self.assertNotIn(str(self.root), json.dumps(kw))

    def test_formal_output_is_decoded_strictly(self):
        uids = {'u1'}
        good = json.dumps({'status': 'THEOREM', 'proof': 'p', 'premise_uids': ['u1']})
        self.assertEqual(C.decode_formal_output(good, uids)['status'], 'THEOREM')
        for bad in ('x', json.dumps({'status': 'THEOREM', 'proof': None, 'premise_uids': []}),
                    json.dumps({'status': 'RESOURCE_OUT', 'proof': 'p', 'premise_uids': []}),
                    json.dumps({'status': 'PROVED', 'proof': 'p', 'premise_uids': []}),
                    json.dumps({'status': 'THEOREM', 'proof': 'p', 'premise_uids': ['foreign']}),
                    json.dumps({'status': 'THEOREM', 'proof': 'p', 'premise_uids': ['u1', 'u1']}),
                    json.dumps({'status': 'THEOREM', 'proof': 'p', 'premise_uids': [], 'value': 1})):
            with self.assertRaises(C.CandidateError):
                C.decode_formal_output(bad, uids)


class Refusals(Base):
    def test_routes_and_schemas_do_not_mix(self):
        req = self.request()
        self.assertEqual(validate_request(req)['candidate']['kind'], 'formal-research-successor-v1')
        with self.assertRaisesRegex(ValueError, 'register_statements'):
            register(self.root, req, self.prereg[0], 'FIXTURE', exposure_manifest=self.manifest,
                     campaign_export=self.r['frozen']['export'], pool=self.root / 'none.json')
        v4 = {k: v for k, v in req.items() if k != 'panel_spec'}
        v4.update(schema=R.REQUEST_V4, exposed_graph_fingerprints=[])
        with self.assertRaisesRegex(ValueError, 'statement domains are evaluated only through statement'):
            validate_request(v4)
        with self.assertRaisesRegex(ValueError, 'panel spec'):
            validate_request(self.request(task_count=5))                      # task_count differs from the spec
        swapped = dict(req, arms={'candidate': req['arms']['baseline'], 'baseline': req['arms']['candidate']})
        with self.assertRaisesRegex(ValueError, 'NOT_THE_FROZEN_CANDIDATE'):
            self.reg(swapped)

    def test_export_custody_is_rebuilt_not_trusted(self):
        req = self.request()
        facts = campaign_facts(Path(self.r['frozen']['export']))
        self.assertEqual(statement_export_problems(req, facts), [])
        lem = self.r['candidate']['lemmas'][0]
        altered = copy.deepcopy(facts)
        altered['proof_objects'][lem['proof_sha256']]['text'] += ' '
        self.assertTrue(statement_export_problems(req, altered))
        missing = copy.deepcopy(facts); missing['successor_manifests'].pop(self.r['candidate']['manifest_id'])
        self.assertTrue(any('not in the export' in p for p in statement_export_problems(req, missing)))
        false = copy.deepcopy(facts)
        false['successor_manifests'][self.r['candidate']['manifest_id']]['lemmas'][0]['statement'] = '![X]: (plus(X,X) = n(X))'
        self.assertTrue(any('fails custody' in p for p in statement_export_problems(req, false)))
        rewritten = dict(facts, descriptor_rewritten=True)
        self.assertTrue(any('rewritten' in p for p in statement_export_problems(req, rewritten)))
        with self.assertRaisesRegex(ValueError, 'export does not match'):
            self.reg(self.request(campaign_export_sha256='8' * 64))

    def test_insufficient_material_registers_nothing(self):
        req = self.request(panel_spec=spec(ranges=[[2, 2]], per_range=100))
        with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_DISTINCT_MATERIAL'):
            self.reg(req)
        self.assertIsNone(self.state(digest(req)))

    def test_no_sandbox_no_reservation_and_a_tampered_panel_is_refused(self):
        req = self.request()
        self.reg(req)
        rid = digest(req)
        with mock.patch.object(S, 'available', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'ISOLATION_UNAVAILABLE'):
                evaluate_statements(self.root, rid, self.cust[0], 'FIXTURE')
        self.assertEqual(self.state(rid), 'REGISTERED')
        path = self.root / 'statement_panels' / f'{rid}.json'
        doc = json.loads(path.read_text())
        doc['panel']['statements'] = doc['panel']['statements'][:-1]
        path.write_bytes(canonical(doc))
        with self.assertRaisesRegex(ValueError, 'commitment'):
            evaluate_statements(self.root, rid, self.cust[0], 'FIXTURE')
        self.assertEqual(self.state(rid), 'REGISTERED')


class EndToEnd(Base):
    def test_sealed_statement_evaluation_is_recomputable_and_never_reused(self):
        req = self.request(panel_spec=spec(inclusion='valid-screened-nontrivial', trivial_limit_s=1))
        anchor = self.reg(req)
        rid = digest(req)
        self.assertEqual(anchor['payload']['exposure_graphs'], 0)
        doc = json.loads((self.root / 'statement_panels' / f'{rid}.json').read_text())
        rec = doc['record']
        self.assertEqual(rec['statements'], 6)
        self.assertEqual(rec['spec'], req['panel_spec'])
        # Nothing the research saw is in the panel.
        seen = {SP.eq_of(Q.text(e)) for e in self.r['pool']} | {SP.eq_of(l['statement']) for l in self.r['candidate']['lemmas']}
        self.assertFalse(seen & {SP.eq_of(x['statement']) for x in doc['panel']['statements']})
        # Research can no longer insert a sealed statement.
        sealed = doc['panel']['statements'][0]['statement']
        screen = screen_for_research(self.root, [{'kind': 'lemma', 'text': sealed}], self.cust[0], 'FIXTURE')
        self.assertEqual(verify(screen, self.cust[1])['decisions'][0]['decision'], 'BLOCK')
        receipt = evaluate_statements(self.root, rid, self.cust[0], 'FIXTURE')
        p = verify(receipt, self.cust[1])
        self.assertEqual(p['schema'], R.SCIENTIFIC_RECEIPT_V4)
        self.assertEqual(R.check_receipt(p, 'sealed_evaluation'), [])
        self.assertEqual((p['domain'], p['completed_rows'], p['expected_rows'], p['isolation']), (DOMAIN, 12, 12, R.ISOLATION_V4))
        self.assertEqual(p['outcome'], R.derive_outcome(p))
        log, problems = CR.check_log(registration_log(self.root, self.cust[0]), self.cust[1], verify)
        self.assertEqual(problems, [])
        self.assertEqual(CR.receipt_log_problems(log['entries'], req, receipt)[0], [])
        judged = recompute(self.root / 'evaluations' / rid, req, receipt, registration_log_entries=log['entries'])
        self.assertTrue(judged['agrees'], judged['problems'])
        self.assertEqual(judged['proofs_replayed'], judged['proof_claims'])
        acct = judged['resource_account']
        self.assertEqual(acct['verification']['attempts'], judged['proof_claims'])
        self.assertEqual(acct['verification']['cpu_unknown'], 0)          # B20R7-OPEN-1: checker CPU metered
        self.assertEqual({a: v['attempts'] for a, v in acct['inference']['by_arm'].items()}, {'baseline': 6, 'candidate': 6})
        # The judge is not fooled by a forged replay status in the raw store's interpretation.
        edited = copy.deepcopy(receipt); edited['payload']['analysis_result']['estimate'] = 99.0
        self.assertFalse(recompute(self.root / 'evaluations' / rid, req, edited, registration_log_entries=log['entries'],
                                   replay=False)['agrees'])
        with self.assertRaisesRegex(FileExistsError, 'consumed'):
            evaluate_statements(self.root, rid, self.cust[0], 'FIXTURE')
        # A second registration at this custodian never re-draws a sealed statement.
        r2 = Research.build(self.root, campaign='b' * 64, name='research2')
        req2 = self.request(r2, claim='st-claim-2')
        self.reg(req2, export=r2['frozen']['export'])
        first = {x['structural_sha256'] for x in doc['panel']['statements']}
        self.assertFalse(first & {x['structural_sha256'] for x in self.panel(digest(req2))['statements']})


class InterruptedReservation(Base):
    def test_crash_after_rows_recovers_to_an_invalid_receipt_and_never_retries(self):
        req = self.request()
        self.reg(req)
        rid = digest(req)
        crash(self, '''
            from pathlib import Path
            from genesis.custodian import evaluate_statements
            evaluate_statements(Path(P['root']), P['rid'], Path(P['key']), 'FIXTURE')
        ''', 'custodian.evaluate:3', root=str(self.root), rid=rid, key=str(self.cust[0]))
        self.assertEqual(self.state(rid), 'CONSUMED_NO_RETRY')
        with self.assertRaisesRegex(FileExistsError, 'consumed'):
            evaluate_statements(self.root, rid, self.cust[0], 'FIXTURE')
        receipt = recover(self.root, rid, None, self.cust[0], 'FIXTURE')
        p = verify(receipt, self.cust[1])
        self.assertEqual((p['schema'], p['raw_evidence_complete'], p['outcome']),
                         (R.SCIENTIFIC_RECEIPT_V4, False, 'INVALID'))
        self.assertEqual(self.state(rid), 'COMPLETE')


class ResearchScreen(Base):
    """B20R7-OPEN-2: research asks the custodian before inserting a statement; sealed statements and
    their renamings are blocked; nothing reserved leaks; an unverifiable answer blocks."""

    def test_custodian_screen_blocks_sealed_statements_and_research_uses_it(self):
        from genesis.custodian import screen_statements_for_research
        from genesis.learning import partitions as P
        req = self.request()
        self.reg(req)
        sealed = self.panel(digest(req))['statements']
        eq = SP.eq_of(sealed[0]['statement'])
        renamed = Q.text(Q.canon(eq))
        swap = {'X': 'Z', 'Y': 'X', 'Z': 'Y'}
        renamed = ''.join(swap.get(c, c) for c in renamed)          # an alpha-variant of a sealed statement
        unrelated = Q.text(Q.sample_targets(SYSTEM, 1, min_total=3, max_total=4, max_term=3, seed=1)[0])
        items = [{'route': 'lemma', 'system': SYSTEM, 'statement': x}
                 for x in (sealed[0]['statement'], renamed, unrelated, 'not a statement')]
        env = screen_statements_for_research(self.root, items, self.cust[0], 'FIXTURE')
        p = verify(env, self.cust[1])
        self.assertEqual(p['decisions'], ['BLOCK', 'BLOCK', 'ALLOW', 'BLOCK'])
        self.assertEqual(p['items_sha256'], digest(items))
        text = json.dumps(p)
        for x in sealed:
            self.assertNotIn(x['statement'], text)
        self.assertTrue((self.root / 'statement_screening_ledger.jsonl').read_text().strip())
        query = lambda its: screen_statements_for_research(self.root, its, self.cust[0], 'FIXTURE')
        screen = P.CustodianStatementScreen(query, self.cust[1], verify=verify)
        self.assertEqual(screen('lemma', SYSTEM, eq)['decision'], 'BLOCK')
        self.assertEqual(screen('lemma', SYSTEM, SP.eq_of(unrelated))['decision'], 'ALLOW')
        forged = P.CustodianStatementScreen(lambda its: screen_statements_for_research(
            self.root, its, self.prereg[0], 'FIXTURE'), self.cust[1], verify=verify)       # wrong signer
        self.assertEqual(forged('lemma', SYSTEM, SP.eq_of(unrelated))['decision'], 'BLOCK')
        other = P.CustodianStatementScreen(lambda its: query([dict(its[0], route='pool')]), self.cust[1], verify=verify)
        self.assertEqual(other('lemma', SYSTEM, SP.eq_of(unrelated))['decision'], 'BLOCK')
        broken = P.CustodianStatementScreen(lambda its: 1 / 0, self.cust[1], verify=verify)
        self.assertEqual(broken('lemma', SYSTEM, SP.eq_of(unrelated))['decision'], 'BLOCK')
        # A research run that would prove a sealed statement does not admit it.
        from genesis.verification.eprover import prove
        provable = [SP.eq_of(x['statement']) for x in sealed
                    if prove(Q.axioms(SYSTEM), Q.closed(SP.eq_of(x['statement'])), seconds=1)['status'] == 'THEOREM']
        self.assertTrue(provable, 'fixture: some sealed statement is provable from the axioms in 1 s')
        pool = provable[:1] + Q.true_equations(SYSTEM, 3, per_bucket=2, seed=3)
        budget = StudyBudget.from_seconds(6, attempt_s=1, enforcement='OUTER_SUPERVISED', quantum_ns=100_000_000)
        run = RS.run(SYSTEM, RS.Fixed(), pool, account=Account(budget, label='screened'), prove_s=1, premise_k=8,
                     run_id='screened', screen=P.both(P.allow_all, screen))
        self.assertNotIn(Q.text(provable[0]), [l['text'] for l in run['library']])
        self.assertIn(Q.text(provable[0]), run['screened_out'])


if __name__ == '__main__':
    unittest.main()
