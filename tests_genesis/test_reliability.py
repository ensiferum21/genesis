"""W23 (handoff s21.3): heterogeneous evidence routes, quarantine on disagreement, no majority vote.

Python-only routes and fake routes (no external tools); the SAT route is exercised in the
certificates suite and the Lean kernel route in the formal suite.
"""
import tempfile
import unittest
from unittest import mock

from genesis import graphs as G
from genesis.common import digest
from genesis.domains import ADAPTERS
from genesis.models import GraphTask
from genesis.store import Store
from genesis.verification import reliability as RL

C4 = GraphTask(task_id='rl-c4', domain='c4_host_v2', n=5,
               edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 4), (3, 4)), family='fixture')
FREE = ((0, 1), (0, 2), (1, 2), (2, 4))          # a triangle plus a pendant edge: C4-free
CYCLE = ((0, 1), (1, 2), (0, 3), (2, 4), (3, 4))  # 0-1-2-4-3-0 is a 5-cycle, C4-free
SQUARE = ((0, 2), (0, 3), (1, 2), (1, 3))         # 0-2-1-3-0: a 4-cycle


def fake(name, answer, *, impl=None, trust='fake-trust', **factors):
    f = {'implementation': impl or name, 'language': 'python', 'arithmetic': 'exact', 'trust_base': trust,
         'translation': None, 'assumptions': 'A'}
    f.update(factors)
    return RL.Route(name, 'q', f, lambda _: {'status': 'DECIDED', 'answer': answer} if not callable(answer)
                    else answer(_))


class Routes(unittest.TestCase):
    def test_python_routes_agree_but_are_correlated(self):
        for edges, want in ((FREE, True), (CYCLE, True), (SQUARE, False)):
            c = RL.check_witness_routes(C4, edges, lean=False)
            self.assertEqual(c['verdict'], 'CORRELATED')        # one trust base: no independence claim
            self.assertEqual(c['answer'], want)
            self.assertEqual(c['diverse_pairs'], [])

    def test_diverse_routes_agree(self):
        c = RL.cross_check('q', 's', None, [fake('a', 3, trust='t1'), fake('b', 3, trust='t2')])
        self.assertEqual((c['verdict'], c['answer'], c['diverse_pairs']), ('AGREE', 3, [('a', 'b')]))

    def test_copies_of_one_implementation_are_not_diverse(self):
        c = RL.cross_check('q', 's', None, [fake('a', 3, impl='x', trust='t1'), fake('b', 3, impl='x', trust='t2')])
        self.assertEqual(c['verdict'], 'CORRELATED')

    def test_failures_are_outcomes_not_verdicts(self):
        def boom(_):
            raise ZeroDivisionError('x')

        def limit(_):
            raise G.SearchLimit('cap')
        c = RL.cross_check('q', 's', None, [fake('a', boom), fake('b', limit),
                                             RL.Route('c', 'q', fake('c', 0).factors,
                                                      lambda _: {'status': 'UNSUPPORTED', 'reason': 'n'})])
        self.assertEqual(c['verdict'], 'UNSETTLED')
        self.assertEqual([c['outcomes'][k]['status'] for k in 'abc'], ['ERROR', 'RESOURCE_OUT', 'UNSUPPORTED'])

    def test_undeclared_factors_and_wrong_question_are_refused(self):
        bad = RL.Route('a', 'q', {'implementation': 'x'}, lambda _: None)
        with self.assertRaisesRegex(ValueError, 'does not declare'):
            RL.cross_check('q', 's', None, [bad])
        with self.assertRaisesRegex(ValueError, 'answers'):
            RL.cross_check('other', 's', None, [fake('a', 1)])

    def test_cause_vocabulary(self):
        cases = [({'translation': 'fof->lean'}, 'PARSER_TRANSLATION'), ({'arithmetic': 'float'}, 'NUMERIC_APPROXIMATION'),
                 ({'assumptions': 'B'}, 'DIFFERENT_ASSUMPTIONS')]
        for factors, cause in cases:
            c = RL.cross_check('q', 's', None, [fake('a', 1, trust='t1'), fake('b', 2, trust='t2', **factors)])
            self.assertEqual(c['verdict'], 'DISAGREE')
            self.assertIn(cause, c['candidate_causes'])
            self.assertEqual(c['candidate_causes'][-1], 'CHECKER_DEFECT')
        partial = RL.Route('p', 'q', fake('p', 0).factors, lambda _: {'status': 'DECIDED', 'answer': 0, 'partial': True})
        rule = RL.Route('r', 'q', dict(fake('r', 0).factors, trust_base='lean'),
                        lambda _: {'status': 'DECIDED', 'answer': 5, 'unsupported_rule': True})
        c = RL.cross_check('q', 's', None, [fake('a', 1, trust='t1'), partial, rule])
        self.assertIn('RESOURCE_FAILURE', c['candidate_causes'])
        self.assertIn('UNSUPPORTED_PROOF_RULE', c['candidate_causes'])


class QuarantineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.q = RL.Quarantine(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def disagreement(self):
        """An injected faulty bitset predicate: the explicit enumeration says C4-free, it says not."""
        with mock.patch.object(G, 'forbidden_b', lambda task, edges: True):
            return RL.check_witness_routes(C4, FREE, lean=False)

    def test_disagreement_is_quarantined_with_inputs_and_both_results(self):
        c = self.disagreement()
        self.assertEqual(c['verdict'], 'DISAGREE')
        self.assertEqual(c['input']['edges'], [list(e) for e in FREE])
        self.assertEqual({k: v['answer'] for k, v in c['outcomes'].items()},
                         {'explicit-motifs-v1': True, 'neighbor-bitsets-v1': False})
        rid = self.q.record(c)
        self.assertTrue(self.q.problems(c['subject']))
        with self.assertRaises(RL.QuarantineError):
            self.q.require_clear(c['subject'])
        self.assertEqual(self.q.problems('another subject'), [])
        self.assertEqual(self.q.get(rid)['check']['check_id'], c['check_id'])

    def test_quarantine_survives_restart(self):
        c = self.disagreement()
        self.q.record(c)
        self.store.close()
        self.store = Store(self.tmp.name)
        self.q = RL.Quarantine(self.store)
        self.assertTrue(self.q.problems(c['subject']))

    def test_no_majority_vote(self):
        """Two copies of a wrong routine against one correct route: still a disagreement."""
        copy1 = fake('bitsets-1', False, impl='bitset', trust='py')
        copy2 = fake('bitsets-2', False, impl='bitset', trust='py')
        right = fake('enumeration', True, impl='enum', trust='lean')
        c = RL.cross_check('q', 'subj', None, [copy1, copy2, right])
        self.assertEqual(c['verdict'], 'DISAGREE')
        self.assertNotIn('answer', c)
        rid = self.q.record(c)
        # Marking the lone route faulty because it is outnumbered needs evidence like any other.
        with self.assertRaisesRegex(RL.QuarantineError, 'evidence'):
            self.q.adjudicate(rid, cause='CHECKER_DEFECT', faulty_routes=['enumeration'], evidence=[],
                              adjudicator='reviewer')

    def test_adjudication_rules(self):
        c = self.disagreement()
        rid = self.q.record(c)
        rec = self.q.get(rid)
        proof = self.store.put({'reproduction': 'forbidden_b was patched to a constant'})
        attempts = [
            (dict(cause='MAJORITY', faulty_routes=['neighbor-bitsets-v1'], evidence=[proof]), 'cause must be'),
            (dict(cause='CHECKER_DEFECT', faulty_routes=[], evidence=[proof]), 'faulty route'),
            (dict(cause='CHECKER_DEFECT', faulty_routes=['explicit-motifs-v1', 'neighbor-bitsets-v1'],
                  evidence=[proof]), 'nothing is left'),
            (dict(cause='CHECKER_DEFECT', faulty_routes=['nope'], evidence=[proof]), 'not decided'),
            (dict(cause='CHECKER_DEFECT', faulty_routes=['neighbor-bitsets-v1'], evidence=rec['outcome_digests']),
             'not evidence'),
            (dict(cause='CHECKER_DEFECT', faulty_routes=['neighbor-bitsets-v1'], evidence=['ab' * 32]),
             'not in the store'),
            (dict(cause='CHECKER_DEFECT', faulty_routes=['neighbor-bitsets-v1'], evidence=[proof], adjudicator=' '),
             'adjudicator'),
        ]
        for kw, msg in attempts:
            kw.setdefault('adjudicator', 'reviewer')
            with self.assertRaisesRegex(RL.QuarantineError, msg):
                self.q.adjudicate(rid, **kw)
        self.assertTrue(self.q.problems(c['subject']))
        aid = self.q.adjudicate(rid, cause='CHECKER_DEFECT', faulty_routes=['neighbor-bitsets-v1'], evidence=[proof],
                                adjudicator='reviewer', note='fault injected by the test')
        self.assertEqual(self.q.problems(c['subject']), [])
        adj = self.q.adjudications(rid)[aid]
        self.assertEqual((adj['resolved_answer'], adj['intervention'], adj['surviving_routes']),
                         (True, 'HUMAN_INTERVENTION', ['explicit-motifs-v1']))
        self.assertEqual(self.q.get(rid)['status'], 'QUARANTINED')     # history is kept
        self.assertEqual(self.q.open(), {})

    def test_routes_left_must_agree(self):
        c = RL.cross_check('q', 's3', None, [fake('a', 1, trust='t1'), fake('b', 2, trust='t2'),
                                              fake('c', 3, trust='t3')])
        rid = self.q.record(c)
        ev = self.store.put({'x': 1})
        with self.assertRaisesRegex(RL.QuarantineError, 'still disagree'):
            self.q.adjudicate(rid, cause='CHECKER_DEFECT', faulty_routes=['a'], evidence=[ev], adjudicator='r')

    def test_only_disagreements_are_quarantined(self):
        with self.assertRaises(ValueError):
            self.q.record(RL.check_witness_routes(C4, FREE, lean=False))
        c = self.disagreement()
        c['verdict'] = 'DISAGREE'
        c['outcomes']['explicit-motifs-v1']['answer'] = False         # tampered after the fact
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.q.record(c)


class CheckerSites(unittest.TestCase):
    def test_predicate_disagreement_carries_both_results(self):
        with mock.patch.object(G, 'forbidden_b', lambda task, edges: True):
            with self.assertRaises(G.CheckerDisagreement) as cm:
                G.check_witness(C4, FREE)
            self.assertIsInstance(cm.exception, RuntimeError)          # existing handlers still catch it
            self.assertEqual(cm.exception.results, {'explicit-motifs-v1': True, 'neighbor-bitsets-v1': False})
            v = ADAPTERS['c4_host_v2'].validate(C4, FREE)
        self.assertEqual(v['status'], 'CHECKER_ERROR')
        self.assertEqual(v['disagreement']['inputs']['edges'], [list(e) for e in FREE])

    def test_exact_optimizer_disagreement_carries_both_values(self):
        real = G.exact_checker

        def off_by_one(task, *a, **k):
            r = real(task, *a, **k)
            return dict(r, value=r['value'] - 1)
        with mock.patch.object(G, 'exact_checker', off_by_one):
            with self.assertRaises(G.CheckerDisagreement) as cm:
                G.certified_optimum(C4)
        res = cm.exception.results
        self.assertEqual(res['motif-hitting-set'] - res['incremental-branch-bound'], 1)

    def test_python_optimum_routes(self):
        c = RL.check_optimum_routes(C4, sat=False)
        self.assertEqual(c['verdict'], 'CORRELATED')
        self.assertEqual(c['answer'], G.certified_optimum(C4)['value'])
        self.assertEqual(c['subject'], digest(C4.model_dump(mode='json')))


if __name__ == '__main__':
    unittest.main()
