"""B20_R5 (H05, handoff s12.1 and s13): executable candidates through the custodian.

Evaluation request v4 names its arms as candidate descriptors; the custodian rebuilds them from
the campaign's frozen export, runs every arm in the OCI sandbox through the trusted runner, and
signs scientific receipt v4; the judge recomputes the analysis and re-checks every witness.

The s13.3 acceptance list, each failing safely: wrong candidate digest, swapped domain, mutated
artifact after freeze, malformed output, attempted filesystem/network access, exposed reference
fields, resource overrun, interrupted private reservation and inconsistent export; and a valid
frozen non-DSL candidate executes and yields a raw receipt the judge independently recomputes.
Fixture keys prove protocol behaviour only; nothing here is independent custody.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from genesis import candidates as C
from genesis import custody_records as CR
from genesis import sandbox as S
from genesis.common import bytes_hash, canonical, code_identity, digest
from genesis.custodian import evaluate, recover, register, registration_log, validate_request, verify
from genesis.domains import ADAPTERS
from genesis.dsl import baseline_programs
from genesis.judge import recompute
from genesis.kernel import receipts as R
from genesis.kernel.analysis import analyze
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.store import Store
from tests_genesis.signed_fixtures import SignedFixture, campaign_export, record_evaluation
from tests_genesis.test_crash_consistency import crash
from tests_genesis.test_evaluator_readiness import frozen_plan_and_record, keyfile

ROOT = Path(__file__).resolve().parents[1]
TF = 'triangle_free_host_v1'
FAMILY = f'sealed_evaluation:{TF}'


def rr_descriptor(rep='cross_2', domain=TF, **profile):
    return C.build_descriptor('represent-and-repair-v1', domain, {'representation': rep, 'cpu_seconds': 0.3, 'seed': 5},
                              cpu_seconds=profile.pop('cpu_seconds', 1), **profile)


def dsl_descriptor(name, rp, domain=TF):
    return C.build_descriptor('dsl-program-v1', domain, {'program': baseline_programs()[name].model_dump(mode='json')},
                              **rp)


def tf_tasks(seed=41):
    a = ADAPTERS[TF]
    t1, seen, _ = a.generate(seed, 3, 'CONFIRM', 'erdos', {'n': 9, 'p': 0.5})
    t2, _, _ = a.generate(seed + 1, 3, 'CONFIRM', 'erdos', {'n': 10, 'p': 0.45}, excluded=seen)
    return t1 + t2


class Base(unittest.TestCase):
    def setUp(self):
        if not S.available():
            self.fail('B20_R5 custody tests need the OCI sandbox (root with runc); the release matrix runs as root')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.root.chmod(0o700)
        self.prereg = keyfile(self.root, 'prereg'); self.cust = keyfile(self.root, 'custodian')
        self.source = code_identity(ROOT)['sha256']
        self.manifest = self.root / 'exposure_manifest.json'
        self.manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
        self.manifest.chmod(0o600)
        self.tasks = tf_tasks()
        self.pool = self.root / 'pool.json'
        self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in self.tasks]))
        self.desc = rr_descriptor()
        self.plan, self.record = frozen_plan_and_record(family_id=FAMILY, family_size=3)

    def export(self, name='export.zip', *, descriptor='frozen', domain=TF, campaign='a' * 64, **kw):
        desc = self.desc if descriptor == 'frozen' else descriptor
        path, frozen = campaign_export(self.root, campaign_id=campaign, source_hash=self.source, domain=domain,
                                       name=name, descriptor=desc, **kw)
        return path, frozen

    def request(self, export, frozen, *, arms=None, domain=TF, claim='rr-claim', **over):
        rp = self.desc['resource_profile']
        req = {'schema': R.REQUEST_V4, 'campaign_id': frozen['campaign_id'], 'claim_id': claim,
               'evidence_kind': 'sealed_evaluation', 'statement_hash': '5' * 64, 'scope': 'fixture panel',
               'generation_transition': None, 'transfer_source_domain': None,
               'campaign_export_sha256': bytes_hash(Path(export).read_bytes()),
               'candidate_version': frozen['candidate_version'], 'source_hash': self.source,
               'arms': arms or {'candidate': self.desc, 'baseline': dsl_descriptor('multistart', rp, domain)},
               'seed': 42, 'task_count': len(self.tasks), 'domain': domain, 'analysis': self.plan,
               'exposed_graph_fingerprints': [], 'expected_evaluator_hash': self.source}
        req.update(over)
        return req

    def reg(self, req, export):
        return register(self.root, req, self.prereg[0], 'FIXTURE', exposure_manifest=self.manifest,
                        campaign_export=export, pool=self.pool, decision_record=self.record)

    def state(self, rid):
        db = sqlite3.connect(self.root / 'custody.sqlite3')
        try:
            return db.execute('SELECT state FROM requests WHERE id=?', (rid,)).fetchone()[0]
        finally:
            db.close()


class Schema(unittest.TestCase):
    """Reviewed schema extension (s12.1): exact field sets, old readers refuse new forms."""

    def setUp(self):
        self.desc = rr_descriptor()
        self.base = dsl_descriptor('multistart', self.desc['resource_profile'])
        self.plan, _ = frozen_plan_and_record(family_id=FAMILY, family_size=3)
        self.req = {'schema': R.REQUEST_V4, 'campaign_id': 'a' * 64, 'claim_id': 'c', 'evidence_kind': 'sealed_evaluation',
                    'statement_hash': '5' * 64, 'scope': 's', 'generation_transition': None, 'transfer_source_domain': None,
                    'campaign_export_sha256': 'e' * 64, 'candidate_version': 'b' * 64, 'source_hash': 'c' * 64,
                    'arms': {'candidate': self.desc, 'baseline': self.base}, 'seed': 1, 'task_count': 6, 'domain': TF,
                    'analysis': self.plan, 'exposed_graph_fingerprints': [], 'expected_evaluator_hash': 'c' * 64}

    def test_valid_v4_request_validates_to_descriptors(self):
        arms = validate_request(self.req)
        self.assertEqual({k: v['descriptor_id'] for k, v in arms.items()},
                         {'candidate': self.desc['descriptor_id'], 'baseline': self.base['descriptor_id']})
        self.assertEqual(R.arm_identity(self.req, 'candidate'), self.desc['descriptor_id'])

    def test_mixed_or_extra_fields_are_refused(self):
        for bad in (dict(self.req, programs={}), dict(self.req, limits={}), dict(self.req, schema=R.REQUEST),
                    {k: v for k, v in self.req.items() if k != 'arms'}):
            with self.assertRaisesRegex(ValueError, 'schema'):
                validate_request(bad)

    def test_v4_needs_a_v2_plan_and_supports_sealed_evaluation_only(self):
        self.assertTrue(any('plan v2' in p for p in R.check_request(dict(self.req, analysis=dict(R.ANALYSIS_V1)))))
        for kind in ('sealed_transfer_evaluation', 'sealed_generation_evaluation', 'sealed_improver_evaluation'):
            self.assertTrue(any('v4 request supports' in p for p in R.check_request(dict(self.req, evidence_kind=kind))))

    def test_arms_share_one_resource_profile(self):
        other = dsl_descriptor('multistart', dict(self.desc['resource_profile'], cpu_seconds=2))
        with self.assertRaisesRegex(ValueError, 'one resource profile'):
            validate_request(dict(self.req, arms={'candidate': self.desc, 'baseline': other}))

    def test_same_descriptor_on_both_arms_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'same program'):
            validate_request(dict(self.req, arms={'candidate': self.desc, 'baseline': self.desc}))

    def test_request_descriptor_is_rebuilt_not_trusted(self):
        tampered = copy.deepcopy(self.desc)
        tampered['parameters']['cpu_seconds'] = 5          # identity left as it was
        with self.assertRaisesRegex(ValueError, 'DESCRIPTOR_ID_MISMATCH'):
            validate_request(dict(self.req, arms={'candidate': tampered, 'baseline': self.base}))
        code = copy.deepcopy(self.desc)
        code['parameters'] = {'representation': 'cross_2', 'cpu_seconds': 0.3, 'seed': 5, 'module': 'os'}
        code['descriptor_id'] = digest({k: v for k, v in code.items() if k != 'descriptor_id'})
        with self.assertRaisesRegex(ValueError, 'MALFORMED_PARAMETERS'):
            validate_request(dict(self.req, arms={'candidate': code, 'baseline': self.base}))

    def test_v4_receipt_schema_is_exact_and_old_schemas_keep_their_meaning(self):
        self.assertEqual(R.RECEIPT_FIELDS_V4 - R.RECEIPT_FIELDS_V3,
                         {'candidate_descriptor_id', 'baseline_descriptor_id', 'arms_sha256', 'isolation'})
        self.assertFalse({'candidate_program_hash', 'baseline_version'} & R.RECEIPT_FIELDS_V4)
        self.assertEqual(R.receipt_arm_ids({'schema': R.SCIENTIFIC_RECEIPT, 'candidate_program_hash': 'x',
                                            'baseline_version': 'y'}), ('x', 'y'))


class EndToEnd(Base):
    def test_valid_frozen_candidate_executes_and_the_judge_recomputes(self):
        export, frozen = self.export()
        req = self.request(export, frozen)
        anchor = self.reg(req, export)
        rid = digest(req)
        receipt = evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')
        p = verify(receipt, self.cust[1])
        self.assertEqual(p['schema'], R.SCIENTIFIC_RECEIPT_V4)
        self.assertEqual(R.check_receipt(p, 'sealed_evaluation'), [])
        self.assertEqual((p['candidate_descriptor_id'], p['baseline_descriptor_id'], p['arms_sha256'], p['isolation']),
                         (self.desc['descriptor_id'], req['arms']['baseline']['descriptor_id'], digest(req['arms']),
                          R.ISOLATION_V4))
        self.assertEqual((p['outcome'], p['completed_rows'], p['expected_rows']),
                         (R.derive_outcome(p), 12, 12))
        self.assertEqual(p['anchor_hash'], digest(anchor))
        log, problems = CR.check_log(registration_log(self.root, self.cust[0]), self.cust[1], verify)
        self.assertEqual(problems, [])
        self.assertEqual(CR.receipt_log_problems(log['entries'], req, receipt)[0], [])
        judged = recompute(self.root / 'evaluations' / rid, req, receipt, registration_log_entries=log['entries'])
        self.assertTrue(judged['agrees'], judged['problems'])
        self.assertEqual(judged['witnesses_rechecked'], 12)
        self.assertEqual((judged['fairness']['problems'], judged['fairness']['paired_tasks']), ([], 6))
        self.assertTrue(all(v['attempts'] == 6 for v in judged['resource_account']['inference']['by_arm'].values()))
        # The raw store: every arm ran its request descriptor inside the sandbox, metered by cgroup.
        with Store(self.root / 'evaluations' / rid) as s:
            seen = 0
            for _, req_h, rec_h in s.db.execute("SELECT status,request,receipt FROM attempts"):
                a, r = s.get(req_h), s.get(rec_h)
                if a.get('kind') != 'solver':
                    continue
                seen += 1
                self.assertEqual(a['descriptor'], req['arms'][a['arm']])
                self.assertEqual((r['isolation'], r['meter'], r['status']), (R.ISOLATION_V4, 'cgroup', 'SUCCESS'))
                self.assertIsInstance(r['cpu_ns'], int)
            self.assertEqual(seen, 12)
        # The judge is not fooled by an edited result, nor by an edited witness in the raw store.
        edited = copy.deepcopy(receipt); edited['payload']['analysis_result']['estimate'] = 99.0
        self.assertFalse(recompute(self.root / 'evaluations' / rid, req, edited,
                                   registration_log_entries=log['entries'])['agrees'])
        # No second draw for the same claim or candidate.
        with self.assertRaisesRegex(FileExistsError, 'consumed'):
            evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')


class Refusals(Base):
    def test_wrong_candidate_digest(self):
        export, frozen = self.export()
        rp = self.desc['resource_profile']
        other = rr_descriptor('ordered_2')
        req = self.request(export, frozen, arms={'candidate': other, 'baseline': dsl_descriptor('multistart', rp)})
        with self.assertRaisesRegex(ValueError, 'NOT_THE_FROZEN_CANDIDATE'):
            self.reg(req, export)

    def test_swapped_domain(self):
        export, frozen = self.export()
        with self.assertRaisesRegex(ValueError, 'DOMAIN_MISMATCH'):
            validate_request(self.request(export, frozen, domain='c4_host_v2'))
        c4_export, c4_frozen = self.export('c4.zip', domain='c4_host_v2')
        with self.assertRaisesRegex(ValueError, 'domain differs from the campaign export'):
            self.reg(self.request(c4_export, c4_frozen), c4_export)

    def test_mutated_artifact_after_freeze(self):
        # The campaign froze a descriptor whose reviewed implementation has since changed.
        stale = copy.deepcopy(self.desc)
        stale['implementation'] = dict(stale['implementation'], **{'candidates.py': '0' * 64})
        stale['descriptor_id'] = digest({k: v for k, v in stale.items() if k != 'descriptor_id'})
        export, frozen = self.export('stale.zip', descriptor=stale)
        with self.assertRaisesRegex(ValueError, 'no longer valid: IMPLEMENTATION_CHANGED'):
            self.reg(self.request(export, frozen), export)
        rp = self.desc['resource_profile']
        with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_CHANGED'):
            validate_request(self.request(export, frozen, arms={'candidate': stale,
                                                                'baseline': dsl_descriptor('multistart', rp)}))

    def test_inconsistent_export(self):
        plain, frozen = self.export('plain.zip', descriptor=None)
        with self.assertRaisesRegex(ValueError, 'no frozen candidate descriptor'):
            self.reg(self.request(plain, frozen), plain)
        rewritten, frozen = self.export('rewritten.zip', descriptor_rewrites=[rr_descriptor('adjacent_2')])
        with self.assertRaisesRegex(ValueError, 'rewritten in the export history'):
            self.reg(self.request(rewritten, frozen), rewritten)
        good, frozen = self.export('good.zip')
        with self.assertRaisesRegex(ValueError, 'candidate_version is not a frozen version'):
            self.reg(self.request(good, frozen, candidate_version='9' * 64), good)
        with self.assertRaisesRegex(ValueError, 'export does not match'):
            self.reg(self.request(good, frozen, campaign_export_sha256='8' * 64), good)

    def test_baseline_and_extra_arms_come_from_the_campaign(self):
        export, frozen = self.export()
        rp = self.desc['resource_profile']
        weaker = {'candidate': self.desc, 'baseline': dsl_descriptor('exchange', rp)}
        with self.assertRaisesRegex(ValueError, 'strongest conventional baseline'):
            self.reg(self.request(export, frozen, arms=weaker), export)
        extra = {'candidate': self.desc, 'baseline': dsl_descriptor('multistart', rp), 'other': rr_descriptor('adjacent_2')}
        with self.assertRaisesRegex(ValueError, 'arm other is not a conventional baseline'):
            self.reg(self.request(export, frozen, arms=extra), export)

    def test_no_sandbox_means_no_reservation(self):
        export, frozen = self.export()
        req = self.request(export, frozen)
        self.reg(req, export)
        with mock.patch.object(S, 'available', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'ISOLATION_UNAVAILABLE'):
                evaluate(self.root, digest(req), self.pool, self.cust[0], 'FIXTURE')
        self.assertEqual(self.state(digest(req)), 'REGISTERED')       # the panel was not burned


class FailuresAreNotScores(Base):
    def test_malformed_output_and_overrun_are_failures(self):
        export, frozen = self.export()
        req = self.request(export, frozen)
        self.reg(req, export)
        real = S.run
        calls = {'n': 0}

        def fake(files, argv, policy=None, **kw):
            child = json.loads(files['request.json'])
            if child['kind'] != 'represent-and-repair-v1':
                return real(files, argv, policy, **kw)
            calls['n'] += 1
            if calls['n'] % 2:   # claims a value its (malformed) output cannot support
                return {'status': 'SUCCESS', 'stdout': json.dumps({'selected': [[0, 1, 2]], 'value': 99}),
                        'cpu_ns': 1, 'wall_ns': 1, 'sandbox': R.ISOLATION_V4}
            return {'status': 'CPU_LIMIT', 'stdout': '', 'stderr': 'killed', 'cpu_ns': 2 * 10 ** 9, 'wall_ns': 3 * 10 ** 9,
                    'sandbox': R.ISOLATION_V4}
        with mock.patch.object(S, 'run', side_effect=fake):
            receipt = evaluate(self.root, digest(req), self.pool, self.cust[0], 'FIXTURE')
        p = receipt['payload']
        self.assertEqual(calls['n'], 6)
        self.assertEqual((p['execution_failures'], p['completed_rows']), (6, 12))
        self.assertNotEqual(p['outcome'], 'SUPPORTED')
        log, _ = CR.check_log(registration_log(self.root, self.cust[0]), self.cust[1], verify)
        judged = recompute(self.root / 'evaluations' / digest(req), req, receipt, registration_log_entries=log['entries'])
        self.assertTrue(judged['agrees'], judged['problems'])
        self.assertEqual(judged['witnesses_rechecked'], 6)               # baseline rows only
        with Store(self.root / 'evaluations' / digest(req)) as s:
            statuses = sorted(s.get(r)['status'] for _, q, r in s.db.execute('SELECT status,request,receipt FROM attempts')
                              if s.get(q).get('arm') == 'candidate')
            self.assertEqual(statuses, ['CHECKER_ERROR'] * 3 + ['CPU_LIMIT'] * 3)
            for _, q, r in s.db.execute('SELECT status,request,receipt FROM attempts'):
                if s.get(q).get('arm') == 'candidate':
                    self.assertNotIn('result', s.get(r))           # never a score


class Isolation(Base):
    def test_the_child_sees_only_the_candidate_view(self):
        seen = []
        real = S.run

        def spy(files, argv, policy=None, **kw):
            seen.append((dict(files), list(argv), kw))
            return real(files, argv, policy, **kw)
        with mock.patch.object(S, 'run', side_effect=spy):
            r = C.run(self.tasks[0], self.desc, seed=3, isolation='runc')
        self.assertEqual(r['status'], 'SUCCESS')
        files, argv, kw = seen[0]
        self.assertEqual(set(files), {'request.json'})
        child = json.loads(files['request.json'])
        self.assertEqual(set(child), {'view', 'kind', 'parameters', 'cpu_seconds', 'queries', 'seed'})
        self.assertEqual(set(child['view']), {'domain', 'n', 'edges'})
        raw = files['request.json'].decode()
        for secret in (self.tasks[0].task_id, self.tasks[0].family, self.tasks[0].split):
            self.assertNotIn(secret, raw)
        self.assertEqual(kw['ro_mounts'], {C.SOURCE_MOUNT: str(ROOT / 'src')})
        self.assertEqual(set(kw['env']), {'PYTHONPATH', 'PYTHONHASHSEED'})
        self.assertNotIn(str(self.root), json.dumps([argv, kw]))

    def test_filesystem_and_network_access_fail_inside_the_runner_sandbox(self):
        (self.root / 'custody.sqlite3').write_bytes(b'private')
        probe = f'''
import json, os, socket
out = {{}}
def attempt(name, fn):
    try:
        fn(); out[name] = 'ALLOWED'
    except Exception as exc:
        out[name] = type(exc).__name__
attempt('read_private_root', lambda: open({str(self.root / 'custody.sqlite3')!r}, 'rb').read())
attempt('write_source_tree', lambda: open('{C.SOURCE_MOUNT}/genesis/planted.py', 'w').write('x'))
attempt('write_root', lambda: open('/planted', 'w').write('x'))
def net():
    s = socket.create_connection(('1.1.1.1', 443), timeout=2); s.close()
attempt('network', net)
def dns():
    socket.getaddrinfo('pypi.org', 443)
attempt('dns', dns)
attempt('environment_secrets', lambda: [None for k in os.environ if 'PROXY' in k.upper() or 'TOKEN' in k.upper()][0])
print(json.dumps(out))
'''
        r = S.run({'probe.py': probe.encode()}, [S.PYTHON, '-I', '-B', '/work/src/probe.py'],
                  C.sandbox_policy(self.desc['resource_profile']), ro_mounts=C.sandbox_mounts(),
                  env={'PYTHONPATH': C.SOURCE_MOUNT, 'PYTHONHASHSEED': '0'})
        self.assertEqual(r['status'], 'SUCCESS', r.get('stderr'))
        out = json.loads(r['stdout'])
        self.assertEqual(set(out), {'read_private_root', 'write_source_tree', 'write_root', 'network', 'dns',
                                    'environment_secrets'})
        self.assertNotIn('ALLOWED', out.values(), out)
        self.assertFalse((ROOT / 'src/genesis/planted.py').exists())


class InterruptedReservation(Base):
    def test_crash_after_rows_recovers_to_an_invalid_receipt_and_never_retries(self):
        export, frozen = self.export()
        req = self.request(export, frozen)
        self.reg(req, export)
        rid = digest(req)
        crash(self, '''
            from pathlib import Path
            from genesis.custodian import evaluate
            evaluate(Path(P['root']), P['rid'], Path(P['pool']), Path(P['key']), 'FIXTURE')
        ''', 'custodian.evaluate:3', root=str(self.root), rid=rid, pool=str(self.pool), key=str(self.cust[0]))
        self.assertEqual(self.state(rid), 'CONSUMED_NO_RETRY')
        with self.assertRaisesRegex(FileExistsError, 'consumed'):
            evaluate(self.root, rid, self.pool, self.cust[0], 'FIXTURE')
        receipt = recover(self.root, rid, self.pool, self.cust[0], 'FIXTURE')
        p = verify(receipt, self.cust[1])
        self.assertEqual((p['schema'], p['raw_evidence_complete'], p['outcome']),
                         (R.SCIENTIFIC_RECEIPT_V4, False, 'INVALID'))
        self.assertEqual(R.check_receipt(p, 'sealed_evaluation'), [])
        self.assertEqual(self.state(rid), 'COMPLETE')


class ComparatorSelection(Base):
    """B20_R12 (E1 design): time-matched conventional baselines and the custodian's SELECT-panel
    comparator rule."""

    def time_matched(self, name, budget=0.5):
        return C.build_descriptor('dsl-time-matched-v1', TF, {'program': baseline_programs()[name].model_dump(mode='json'),
                                                               'cpu_seconds': budget}, **self.desc['resource_profile'])

    def test_time_matched_baselines_spend_their_budget(self):
        d = self.time_matched('multistart')
        self.assertEqual(C.descriptor_problems(d, domain=TF), [])
        for bad in ({'program': {'weights': [9, 0, 0, 0]}, 'cpu_seconds': 0.5},
                    {'program': baseline_programs()['multistart'].model_dump(mode='json')},
                    {'program': baseline_programs()['multistart'].model_dump(mode='json'), 'cpu_seconds': 0}):
            with self.assertRaises(Exception):
                C.build_descriptor('dsl-time-matched-v1', TF, bad, **self.desc['resource_profile'])
        r = C.run(self.tasks[0], d, seed=3, isolation='runc')
        self.assertEqual((r['status'], r['isolation']), ('SUCCESS', R.ISOLATION_V4))
        self.assertGreaterEqual(r['cpu_ns'], int(0.5e9))
        plain = C.run(self.tasks[0], dsl_descriptor('multistart', self.desc['resource_profile']), seed=3, isolation='runc')
        self.assertGreaterEqual(r['result']['value'], plain['result']['value'])

    def test_custodian_selects_the_comparator_and_registration_enforces_it(self):
        from genesis.custodian import select_comparator
        base, frozen = self.export('base.zip')
        baselines = {n: self.time_matched(n) for n in baseline_programs()}
        env = select_comparator(self.root, base, baselines, self.cust[0], 'FIXTURE', exposure_manifest=self.manifest,
                                task_count=4)
        p = verify(env, self.cust[1])
        self.assertEqual((p['schema'], p['task_count'], p['domain']), ('genesis-comparator-selection-v1', 4, TF))
        self.assertIn(p['selected'], baselines)
        self.assertEqual(p['selected'], max(p['totals'], key=lambda n: (p['totals'][n], n)))
        db = sqlite3.connect(self.root / 'custody.sqlite3')
        reserved = db.execute("SELECT count(*) FROM reservations WHERE request_id LIKE 'select:%'").fetchone()[0]
        db.close()
        self.assertEqual(reserved, 4)                     # the SELECT hosts are never reused
        export, frozen = self.export('selected.zip', selection=env)
        chosen = p['baselines'][p['selected']]
        other = next(d for n, d in p['baselines'].items() if n != p['selected'])
        with self.assertRaisesRegex(ValueError, 'not the comparator this custodian selected'):
            self.reg(self.request(export, frozen, arms={'candidate': self.desc, 'baseline': other}, claim='sel-wrong'), export)
        with self.assertRaisesRegex(ValueError, 'not the comparator this custodian selected'):
            self.reg(self.request(export, frozen, claim='sel-old-rule'), export)         # the campaign-strongest rule no longer applies
        req = self.request(export, frozen, arms={'candidate': self.desc, 'baseline': chosen}, claim='sel-ok')
        self.reg(req, export)
        receipt = evaluate(self.root, digest(req), self.pool, self.cust[0], 'FIXTURE')
        q = verify(receipt, self.cust[1])
        self.assertEqual((q['baseline_descriptor_id'], q['completed_rows']), (chosen['descriptor_id'], 12))
        # A selection this custodian did not make is refused.
        forged = self.export('forged.zip', selection=dict(env, signature='0' * 88))
        with self.assertRaisesRegex(ValueError, 'not made by this custodian'):
            self.reg(self.request(forged[0], forged[1], arms={'candidate': self.desc, 'baseline': chosen},
                                  claim='sel-forged'), forged[0])


class ConstructPipeline(Base):
    """B20_R23: construct-pipeline-v1, a data-only pipeline over trusted construction components."""

    def pipe(self, domain=TF, **over):
        params = dict({'init': 'lp_greedy', 'frac': 1.0, 'finish': 'none', 'cpu_seconds': 0.5, 'seed': 3}, **over)
        return C.build_descriptor('construct-pipeline-v1', domain, params, **self.desc['resource_profile'])

    def test_parameters_are_typed_and_bounded(self):
        for bad in ({'init': 'os.system'}, {'init': 'rep:cross_3'}, {'frac': 0.5, 'finish': 'none'},
                    {'frac': 1, 'finish': 'none'}, {'finish': 'sat_climb', 'frac': 0.25}, {'cpu_seconds': 0},
                    {'cpu_seconds': 61}, {'seed': 1.5}):
            with self.assertRaises(C.CandidateError, msg=bad):
                self.pipe(**bad)
        with self.assertRaises(C.CandidateError):
            self.pipe('c4_host_v2', init='rep:cross_2')                      # no licensed representation on C4
        with self.assertRaises(C.CandidateError):
            C.build_descriptor('construct-pipeline-v1', TF, {'init': 'lp_greedy', 'frac': 1.0, 'finish': 'none',
                                                             'cpu_seconds': 0.5, 'seed': 3, 'code': 'x'},
                               **self.desc['resource_profile'])
        self.assertIn('discovery/construct.py', self.pipe()['implementation'])

    def test_pipelines_run_in_the_sandbox_with_checked_witnesses(self):
        from genesis.graphs import check_witness
        for domain, params, task in ((TF, {}, self.tasks[3]),
                                     (TF, {'init': 'rep:cross_2', 'frac': 0.5, 'finish': 'lp_restarts'}, self.tasks[4]),
                                     ('c4_host_v2', {'init': 'dsl:low_cycle', 'frac': 0.25, 'finish': 'lp_restarts'},
                                      ADAPTERS['c4_host_v2'].generate(7, 1, 'CONFIRM', 'erdos', {'n': 10, 'p': 0.5})[0][0])):
            d = self.pipe(domain, **params)
            r = C.run(task, d, seed=5, expected_id=d['descriptor_id'], isolation='runc')
            self.assertEqual((r['status'], r['isolation'], r['meter']), ('SUCCESS', R.ISOLATION_V4, 'cgroup'), r)
            self.assertEqual(check_witness(task, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])
            self.assertGreaterEqual(r['cpu_ns'], int(0.5e9))                # the budget is spent and charged
        p = C.run(self.tasks[3], self.pipe(), seed=5, isolation='process')
        self.assertEqual(p['status'], 'SUCCESS', p)

    def test_lp_guidance_has_a_registered_ablation_and_placebo(self):
        from genesis.kernel import replay_contracts as RC
        cand, abl, plc = self.pipe(), self.pipe(init='random_greedy'), self.pipe(init='lp_shuffled_greedy')
        self.assertEqual(RC.intervention_problems('ablation', cand, abl), ([], ('init',)))
        self.assertEqual(RC.intervention_problems('placebo', cand, plc), ([], ('init',)))
        cases = [('placebo', cand, abl, 'is not the registered placebo'),
                 ('ablation', cand, plc, 'is not the registered ablation'),
                 ('ablation', self.pipe(init='dsl:low_cycle'), abl, 'does not change'),
                 ('ablation', cand, self.pipe(init='random_greedy', seed=4), 'differ in 2 components'),
                 ('ablation', cand, self.pipe(frac=0.5, finish='lp_restarts'), 'differ in 2 components'),
                 ('ablation', cand, self.pipe(seed=4), 'no registered ablation for component seed')]
        for kind, full, altered, fragment in cases:
            why, _ = RC.intervention_problems(kind, full, altered)
            self.assertTrue(any(fragment in w for w in why), (fragment, why))
        r = C.run(self.tasks[3], plc, seed=5, expected_id=plc['descriptor_id'], isolation='runc')
        self.assertEqual(r['status'], 'SUCCESS', r)
        from genesis.graphs import check_witness
        self.assertEqual(check_witness(self.tasks[3], [tuple(e) for e in r['result']['selected']])['value'],
                         r['result']['value'])
        self.assertGreaterEqual(r['cpu_ns'], int(0.5e9))


class CausalAndReplicationCustody(Base):
    """B20_R15 (B14-OPEN-4): the custodian registers ablation/placebo requests only for a registered
    intervention of the frozen candidate, and an internal replicator accepts another custodian's
    comparator selection only under a public key its operator names."""

    def program(self, **kw):
        from genesis.models import SolverProgram
        base = {'weights': (0, 0, 0, 1), 'rounds': 8, 'exchange': True}
        base.update(kw)
        return C.build_descriptor('dsl-program-v1', TF, {'program': SolverProgram(**base).model_dump(mode='json')},
                                  **self.desc['resource_profile'])

    def register_as(self, root, req, export, record, prereg, **kw):
        root.mkdir(exist_ok=True); root.chmod(0o700)
        manifest = root / 'exposure_manifest.json'
        if not manifest.exists():
            manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
            manifest.chmod(0o600)
        return register(root, req, prereg, 'FIXTURE', exposure_manifest=manifest, campaign_export=export,
                        pool=self.pool, decision_record=record, **kw)

    def test_ablation_registers_and_runs_only_for_a_registered_intervention(self):
        cand = self.program()
        export, frozen = self.export('causal.zip', descriptor=cand)
        plan, record = frozen_plan_and_record(family_id=f'ablation:{TF}', family_size=3)
        wrong = self.request(export, frozen, arms={'candidate': cand, 'baseline': self.program(weights=(0, 0, 1, 0))},
                             evidence_kind='ablation', analysis=plan, claim='abl-wrong')
        with self.assertRaisesRegex(ValueError, 'not a registered ablation of the frozen candidate'):
            self.register_as(self.root, wrong, export, record, self.prereg[0])
        req = self.request(export, frozen, arms={'candidate': cand, 'baseline': self.program(weights=(0, 0, 0, 0))},
                           evidence_kind='ablation', analysis=plan, claim='abl-ok')
        self.register_as(self.root, req, export, record, self.prereg[0])
        p = verify(evaluate(self.root, digest(req), self.pool, self.cust[0], 'FIXTURE'), self.cust[1])
        self.assertEqual((p['evidence_kind'], p['schema'], p['arms_sha256'], p['completed_rows']),
                         ('ablation', R.SCIENTIFIC_RECEIPT_V4, digest(req['arms']), 12))
        self.assertEqual(R.check_receipt(p, 'ablation'), [])

    def test_internal_replicator_accepts_a_selection_only_under_a_named_key(self):
        from genesis.kernel.signing import sign
        chosen = dsl_descriptor('low_cycle', self.desc['resource_profile'])
        payload = {'schema': 'genesis-comparator-selection-v1', 'campaign_id': 'a' * 64, 'source_hash': self.source,
                   'domain': TF, 'baselines': {'low_cycle': chosen,
                                               'multistart': dsl_descriptor('multistart', self.desc['resource_profile'])},
                   'totals': {'low_cycle': 9, 'multistart': 8}, 'selected': 'low_cycle',
                   'resource_profile': self.desc['resource_profile'], 'task_count': 4}
        selection = sign(payload, self.cust[0])                     # made by custodian A (self.root)
        export, frozen = self.export('replicate.zip', selection=selection)
        plan, record = frozen_plan_and_record(family_id=f'internal_replication:{TF}', family_size=3)
        req = self.request(export, frozen, arms={'candidate': self.desc, 'baseline': chosen},
                           evidence_kind='internal_replication', analysis=plan, claim='rep')
        b_root = self.root / 'replicator'
        b_prereg = keyfile(self.root, 'replicator_prereg')
        with self.assertRaisesRegex(ValueError, 'not made by this custodian'):
            self.register_as(b_root, req, export, record, b_prereg[0])
        outsider = keyfile(self.root, 'outsider')
        with self.assertRaisesRegex(ValueError, 'not made by this custodian'):
            self.register_as(b_root, req, export, record, b_prereg[0], accepted_selection_keys=[outsider[1]])
        sealed_plan, sealed_record = frozen_plan_and_record(family_id=f'sealed_evaluation:{TF}', family_size=3)
        sealed = self.request(export, frozen, arms={'candidate': self.desc, 'baseline': chosen}, analysis=sealed_plan,
                              claim='rep')
        with self.assertRaisesRegex(ValueError, 'not made by this custodian'):     # only replications accept it
            self.register_as(b_root, sealed, export, sealed_record, b_prereg[0], accepted_selection_keys=[self.cust[1]])
        anchor = self.register_as(b_root, req, export, record, b_prereg[0], accepted_selection_keys=[self.cust[1]])
        self.assertEqual(anchor['payload']['evidence_kind'], 'internal_replication')


class KernelV4(unittest.TestCase):
    """A v4 receipt supports a claim only through a v2 (descriptor) binding of the same arms."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name + '/store'); self.addCleanup(self.store.close)
        self.fx = SignedFixture(self.tmp.name)
        self.fx.bind_store(self.store)
        self.k = EvidenceKernel.with_fixture_registry(self.store, self.fx.registry)
        self.run = self.k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign',
                                 source_hash='c' * 64, verdict='VALID', effects=['UNCHECKED_PROPOSAL'])
        self.plan, _ = frozen_plan_and_record(family_id=FAMILY, family_size=1)
        self.desc = rr_descriptor()
        self.base = dsl_descriptor('multistart', self.desc['resource_profile'])

    def request(self, claim, desc=None):
        v3 = self.fx.request(claim_id=claim, domain=TF, scope=SignedFixture.SCOPE)
        req = {k: v for k, v in v3.items() if k not in ('programs', 'limits')}
        req.update(schema=R.REQUEST_V4, arms={'candidate': desc or self.desc, 'baseline': self.base},
                   analysis=self.plan)
        self.assertEqual(R.check_request(req), [])
        return req

    def receipt(self, request, anchor, diffs):
        rows = [{'task_id': f'{s}-{i}', 'stratum': s, 'status': 'SCORED',
                 'candidate': {'value': 20 + d, 'run': 'SUCCESS', 'cpu_ns': 1},
                 'baseline': {'value': 20, 'run': 'SUCCESS', 'cpu_ns': 1}}
                for s, ds in diffs.items() for i, d in enumerate(ds)]
        result = analyze(rows, self.plan)
        a = anchor['payload']
        p = {'schema': R.SCIENTIFIC_RECEIPT_V4, 'evidence_kind': 'sealed_evaluation', 'claim_id': request['claim_id'],
             'statement_hash': request['statement_hash'], 'scope': request['scope'],
             'campaign_id': request['campaign_id'], 'request_hash': digest(request), 'anchor_hash': digest(anchor),
             'candidate_version': request['candidate_version'],
             'candidate_descriptor_id': R.arm_identity(request, 'candidate'),
             'baseline_descriptor_id': R.arm_identity(request, 'baseline'), 'arms_sha256': digest(request['arms']),
             'isolation': R.ISOLATION_V4, 'source_hash': request['source_hash'],
             'evaluator_hash': request['expected_evaluator_hash'], 'analysis': self.plan, 'analysis_result': result,
             'domain': TF, 'domain_contract_hash': R.domain_contract_hash(TF), 'transfer_source_domain': None,
             'generation_transition': None, 'panel_commitment': a['panel_commitment'], 'task_count': len(rows),
             'raw_evidence_root': digest({'raw': digest(request)}), 'raw_evidence_complete': True,
             'expected_rows': 2 * len(rows), 'completed_rows': 2 * len(rows), 'execution_failures': 0,
             'wins': result['wins'], 'losses': result['losses'], 'ties': result['ties'],
             'paired_p': R.sign_test(result['wins'], result['losses']), 'family_p': result['p_value'],
             'outcome': None, 'operator_id': 'FIXTURE_OPERATOR_NOT_INDEPENDENT', 'registered_at': a['registered_at'],
             'completed_at': '2026-10-10T23:59:59+00:00', 'screen': 'FIXTURE',
             'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
        p['outcome'] = R.derive_outcome(p)
        self.assertEqual(R.check_receipt(p, 'sealed_evaluation'), [])
        return self.fx.sign(p, 'custodian')

    def promote(self, claim, diffs, *, bind_with=None):
        request = self.request(claim)
        anchor = self.fx.anchor(request)
        receipt = self.receipt(request, anchor, diffs)
        _, node = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor, receipt=receipt)
        binding = R.binding_from_requests([bind_with or request])
        self.k.create_claim(claim, SignedFixture.STATEMENT, SignedFixture.SCOPE, [node], binding=binding)
        return receipt['payload'], binding

    def test_supported_v4_receipt_licenses_confirmation_through_a_v2_binding(self):
        p, binding = self.promote('v4-yes', {'a': [3, 2, 3, 2, 3], 'b': [2, 3, 3, 2, 2]})
        self.assertEqual((p['outcome'], binding['schema']), ('SUPPORTED', R.CLAIM_BINDING_V2))
        self.assertEqual(binding['candidate_descriptor'], self.desc['descriptor_id'])
        self.k.promote('v4-yes', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertEqual(self.k.levels('v4-yes')['utility'], 'CONFIRMED_SAME_DOMAIN')

    def test_a_binding_for_another_descriptor_does_not_support(self):
        other = self.request('v4-other', rr_descriptor('ordered_2'))
        self.promote('v4-other', {'a': [3, 2, 3, 2, 3], 'b': [2, 3, 3, 2, 2]}, bind_with=other)
        with self.assertRaises(PromotionRejected):
            self.k.promote('v4-other', 'utility', 'CONFIRMED_SAME_DOMAIN')

    def test_one_claim_is_not_bound_by_both_forms(self):
        v3 = self.fx.request(claim_id='mixed', domain=TF)
        with self.assertRaisesRegex(ValueError, 'not both'):
            R.binding_from_requests([dict(v3, analysis=self.plan), self.request('mixed')])
        self.assertEqual(R.check_binding(R.binding_from_requests([self.request('solo')])), [])


if __name__ == '__main__':
    unittest.main()
