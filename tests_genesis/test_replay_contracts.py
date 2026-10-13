"""B20_R8 (B14-OPEN-4; handoff s12.2): replay contracts for exact, formal and DEV evidence.

Each newly reachable level has a genuine positive example and negative, binding, tampering and
revocation fixtures. A producer-written verdict still licenses nothing: the kernel re-runs the
check (two exhaustive optimizers, a Lean replay from custody, the DEV analysis).
"""
import copy
from pathlib import Path
import tempfile
import unittest

from genesis import graphs
from genesis.kernel import replay_contracts as RC
from genesis.kernel.analysis import analyze
from genesis.kernel.evidence import THEOREM_SCOPE, EvidenceKernel, PromotionRejected
from genesis.learning import custody as CU
from genesis.learning import equational as Q
from genesis.learning import research as RS
from genesis.learning.budget import Account, StudyBudget
from genesis.models import GraphTask
from genesis.store import Store
from tests_genesis.signed_fixtures import math_claim, path4
from tests_genesis.test_evaluator_readiness import base_plan, pilot_rows

SRC = 'a' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name + '/store'); self.addCleanup(self.store.close)
        self.store.set_state('campaign_id', 'a' * 64); self.store.set_state('source_hash', 'c' * 64)
        self.k = EvidenceKernel(self.store)
        self.run = self.k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign',
                                 source_hash=SRC, verdict='VALID', effects=['UNCHECKED_PROPOSAL'])

    def node(self, kind, payload, verdict='VALID'):
        return self.k.record(kind, payload, parents=[self.run], route='genesis.campaign', source_hash=SRC,
                             verdict=verdict)

    def rejects(self, claim, axis, level, fragment):
        with self.assertRaises(PromotionRejected) as ctx:
            self.k.promote(claim, axis, level)
        self.assertTrue(any(fragment in r for r in ctx.exception.args[0]), ctx.exception.args[0])


class FiniteCertified(Base):
    def exact(self, task, method, value):
        return self.node('exact_check', {'schema': RC.EXACT_SCHEMA, 'task_sha256': self.store.put(task.model_dump(mode='json')),
                                         'value': value, 'method': method})

    def test_two_different_methods_that_replay_certify_the_optimum(self):
        task = path4()
        opt = graphs.certified_optimum(task)['value']
        a, b = self.exact(task, 'exact-producer', opt), self.exact(task, 'exact-checker', opt)
        math_claim(self.k, 'one', [a], value=opt, claim='optimum')
        self.rejects('one', 'math', 'FINITE_CERTIFIED', 'by different methods')
        math_claim(self.k, 'two', [a, b], value=opt, claim='optimum')
        self.k.promote('two', 'math', 'FINITE_CERTIFIED')
        self.assertEqual(self.k.levels('two')['math'], 'FINITE_CERTIFIED')
        self.assertIn('two exhaustive computations', self.k.current_wording('two')['current_statement'])

    def test_wrong_value_other_problem_bound_claim_and_limits_fail(self):
        task = path4()
        opt = graphs.certified_optimum(task)['value']
        a, b = self.exact(task, 'exact-producer', opt + 1), self.exact(task, 'exact-checker', opt + 1)
        math_claim(self.k, 'inflated', [a, b], value=opt + 1, claim='optimum')
        self.rejects('inflated', 'math', 'FINITE_CERTIFIED', 'does not replay to the recorded value')
        a, b = self.exact(task, 'exact-producer', opt), self.exact(task, 'exact-checker', opt)
        math_claim(self.k, 'bound', [a, b], value=opt, claim='lower_bound')
        self.rejects('bound', 'math', 'FINITE_CERTIFIED', 'certifies the optimum')
        other = GraphTask(task_id='tri', n=3, edges=((0, 1), (0, 2), (1, 2)), family='t')
        math_claim(self.k, 'other', [a, b], value=opt, claim='optimum', task=other)
        self.rejects('other', 'math', 'FINITE_CERTIFIED', 'different problem or value')
        big = GraphTask(task_id='k8', n=8, edges=tuple((i, j) for i in range(8) for j in range(i + 1, 8)), family='k')
        c, d = self.exact(big, 'exact-producer', 10), self.exact(big, 'exact-checker', 10)
        math_claim(self.k, 'big', [c, d], value=10, claim='optimum', task=big)
        self.rejects('big', 'math', 'FINITE_CERTIFIED', 'exhaustive limit')
        unknown = self.node('exact_check', {'schema': RC.EXACT_SCHEMA, 'task_sha256': self.store.put(task.model_dump(mode='json')),
                                            'value': opt, 'method': 'trust-me'})
        math_claim(self.k, 'unknown', [unknown, b], value=opt, claim='optimum')
        self.rejects('unknown', 'math', 'FINITE_CERTIFIED', 'unknown exact method')


class DevOnly(Base):
    def dev(self, rows=None, plan=None, result=None):
        plan = plan or base_plan()
        rows = rows if rows is not None else pilot_rows()
        result = result if result is not None else analyze(rows, plan)
        return self.node('dev_comparison', {'schema': RC.DEV_SCHEMA, 'plan': plan, 'rows': rows, 'result': result},
                         verdict='PASS')

    def claim(self, cid, nodes):
        return self.k.create_claim(cid, 'the candidate improves on DEV material (DEV only)', 'DEV panels', nodes)

    def test_dev_analysis_replays_and_stays_dev(self):
        n = self.dev()
        self.claim('dev', [n])
        self.k.promote('dev', 'utility', 'DEV_ONLY')
        self.k.promote('dev', 'causality', 'CORRELATED')
        self.assertEqual(self.k.levels('dev')['utility'], 'DEV_ONLY')
        with self.assertRaises(PromotionRejected):
            self.k.promote('dev', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertIsNone(self.k.current_wording('dev')['current_statement'])

    def test_forged_unsupported_or_non_dev_results_fail(self):
        forged = analyze(pilot_rows(), base_plan()); forged = dict(forged, estimate=99.0)
        self.claim('forged', [self.dev(result=forged)])
        self.rejects('forged', 'utility', 'DEV_ONLY', 'differs from the kernel')
        sealed = [dict(r, split='CONFIRM') for r in pilot_rows()]
        self.claim('sealed', [self.dev(rows=sealed)])
        self.rejects('sealed', 'utility', 'DEV_ONLY', 'marked split DEV')
        flat = [dict(r, candidate=dict(r['candidate'], value=r['baseline']['value'])) for r in pilot_rows()]
        self.claim('flat', [self.dev(rows=flat)])
        self.rejects('flat', 'utility', 'DEV_ONLY', 'not SUPPORTED')


class TheoremChecked(Base):
    """A real equational proof with its lemma chain, replayed in Lean by the kernel."""

    @classmethod
    def setUpClass(cls):
        cls.ctmp = tempfile.TemporaryDirectory()
        system = 'ba_huntington'
        pool = Q.true_equations(system, 4, per_bucket=3, seed=5)
        budget = StudyBudget.from_seconds(4, attempt_s=1, enforcement='OUTER_SUPERVISED', quantum_ns=100_000_000)
        run = RS.run(system, RS.Fixed(), pool, account=Account(budget, label='r8'), prove_s=1, premise_k=8,
                     run_id='r8-fixed')
        objs = CU.ObjectStore(Path(cls.ctmp.name) / 'objects')
        manifest = CU.successor_manifest(run, objs)
        # A lemma-using proof whose Lean replay the translator can carry (B19-OPEN-5 limits some steps).
        tc = {'checker_identity': CU.checker_identity()['identity']}
        for seed in range(30):
            target = Q.sample_targets(system, 1, min_total=7, max_total=10, seed=seed, exclude=pool)[0]
            ev = RS.evaluate_successor(system, run['library'], [target], eval_s=1, label='r8-target')
            if ev['rows'][0]['status'] != 'PROVED' or not ev['rows'][0]['lemmas_used']:
                continue
            record = CU.target_records(ev, manifest, objs, panel_id='r8')[0]
            replayed = CU.replay_target(record, manifest, objs, task_statement=record['statement'], trust_context=tc)
            if replayed['status'] == 'CHECKED':
                assert type(replayed['cpu_ns']) is int and replayed['cpu_ns'] > 0     # B20R7-OPEN-1: checker CPU metered
                break
        else:
            raise AssertionError('no replayable lemma-using proof found for the fixture')
        needed = [l['proof_sha256'] for l in manifest['lemmas']] + [record['proof_sha256']]
        cls.system, cls.manifest, cls.record = system, manifest, record
        cls.statement = record['statement']
        cls.proofs = {h: objs.get(h).decode() for h in needed}

    @classmethod
    def tearDownClass(cls):
        cls.ctmp.cleanup()

    def theorem(self, statement=None, system=None):
        return self.store.put(RC.theorem_object(system or self.system, statement or self.statement))

    def formal(self, tsha, **over):
        payload = {'schema': RC.FORMAL_SCHEMA, 'route': 'equational-custody-v1', 'theorem_sha256': tsha,
                   'manifest': self.manifest, 'record': self.record, 'proof_objects': dict(self.proofs)}
        payload.update(over)
        return self.node('formal_check', payload)

    def claim(self, cid, nodes, tsha):
        problem = {'theorem_sha256': tsha, 'claim': 'theorem'}
        return self.k.create_claim(cid, self.k.math_statement(problem), THEOREM_SCOPE, nodes, problem=problem)

    def test_proof_with_its_lemma_chain_replays_in_lean(self):
        tsha = self.theorem()
        self.claim('thm', [self.formal(tsha)], tsha)
        self.k.promote('thm', 'math', 'THEOREM_CHECKED')
        self.assertEqual(self.k.levels('thm')['math'], 'THEOREM_CHECKED')
        self.assertIn(self.statement, self.k.current_wording('thm')['current_statement'])
        self.rejects('thm', 'math', 'WITNESS_VALID', 'no finite-problem levels')
        # Revoking the Lean replay route lowers the claim (the kernel replays again, under revocation).
        reg = self.k.register_verifier(CU.checker_identity()['identity'], 'f' * 64)
        self.k.revoke(reg, 'fixture: the replay route is withdrawn', 'FIXTURE')
        self.rejects('thm', 'math', 'THEOREM_CHECKED', 'is revoked')

    def test_binding_and_tampering_fail(self):
        tsha = self.theorem()
        other = self.theorem(statement='![X]: (plus(X,X) = X)')
        self.claim('other', [self.formal(tsha)], other)
        self.rejects('other', 'math', 'THEOREM_CHECKED', 'different statement')
        bad = dict(self.proofs); h = self.record['proof_sha256']; bad[h] = bad[h] + '\n'
        self.claim('tampered', [self.formal(tsha, proof_objects=bad)], tsha)
        self.rejects('tampered', 'math', 'THEOREM_CHECKED', 'do not hash')
        missing = {k: v for k, v in self.proofs.items() if k != self.manifest['lemmas'][0]['proof_sha256']}
        self.claim('missing', [self.formal(tsha, proof_objects=missing)], tsha)
        self.rejects('missing', 'math', 'THEOREM_CHECKED', 'fails custody')
        forged = dict(self.record, statement=self.statement + ' ')
        self.claim('forged', [self.formal(tsha, record=forged)], tsha)
        self.rejects('forged', 'math', 'THEOREM_CHECKED', 'fails custody')
        with self.assertRaisesRegex(ValueError, 'pinned axioms'):
            obj = dict(RC.theorem_object(self.system, self.statement), axioms=['![X]: (X = X)'])
            problem = {'theorem_sha256': self.store.put(obj), 'claim': 'theorem'}
            self.k.create_claim('wrong-axioms', 'x', THEOREM_SCOPE, [self.run], problem=problem)


if __name__ == '__main__':
    unittest.main()
