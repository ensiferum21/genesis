"""B19 / W16: Lean replay of E proof objects, translation faithfulness, the Ghost Census
diagnostic and its preregistered decision rule."""
import json
from pathlib import Path
import unittest

from genesis import sandbox
from genesis.discovery import ghost_census as G
from genesis.fol import parse
from genesis.formal_research import checker
from genesis.formal_research import fof_lean as F
from genesis.formal_research import workspace as W
from genesis.verification.tools import ToolUnavailable, tool

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'ghost_census_b19' / 'run2'
GROUP = [parse(a) for a in G.THEORIES['group']]

# E 3.5.1 --auto, group axioms, goal ![X]: mul(X,inv(X)) = e (kept so the parser and the
# replay are tested on a fixed proof object, independent of the prover's run).
RIGHT_INV_PROOF = '''SZS output start CNFRefutation
fof(ax0, axiom, ![X1, X2, X3]:(mul(mul(X1,X2),X3)=mul(X1,mul(X2,X3))), file('p.p', ax0)).
fof(ax2, axiom, ![X1]:(mul(inv(X1),X1)=e), file('p.p', ax2)).
fof(ax1, axiom, ![X1]:(mul(e,X1)=X1), file('p.p', ax1)).
fof(goal, conjecture, ![X1]:(mul(X1,inv(X1))=e), file('p.p', goal)).
fof(c_0_4, plain, ![X4, X5, X6]:(mul(mul(X4,X5),X6)=mul(X4,mul(X5,X6))), inference(variable_rename,[status(thm)],[ax0])).
fof(c_0_5, plain, ![X8]:(mul(inv(X8),X8)=e), inference(variable_rename,[status(thm)],[ax2])).
fof(c_0_6, plain, ![X7]:(mul(e,X7)=X7), inference(variable_rename,[status(thm)],[ax1])).
cnf(c_0_7, plain, (mul(mul(X1,X2),X3)=mul(X1,mul(X2,X3))), inference(split_conjunct,[status(thm)],[c_0_4])).
cnf(c_0_8, plain, (mul(inv(X1),X1)=e), inference(split_conjunct,[status(thm)],[c_0_5])).
cnf(c_0_9, plain, (mul(e,X1)=X1), inference(split_conjunct,[status(thm)],[c_0_6])).
cnf(c_0_10, plain, (mul(inv(X1),mul(X1,X2))=X2), inference(rw,[status(thm)],[inference(spm,[status(thm)],[c_0_7, c_0_8]), c_0_9])).
cnf(c_0_11, plain, (mul(inv(inv(X1)),e)=X1), inference(spm,[status(thm)],[c_0_10, c_0_8])).
cnf(c_0_12, plain, (mul(inv(inv(X1)),X2)=mul(X1,X2)), inference(spm,[status(thm)],[c_0_10, c_0_10])).
fof(c_0_13, negated_conjecture, ~(![X1]:(mul(X1,inv(X1))=e)), inference(assume_negation,[status(cth)],[goal])).
cnf(c_0_14, plain, (mul(X1,e)=X1), inference(rw,[status(thm)],[c_0_11, c_0_12])).
fof(c_0_15, negated_conjecture, mul(esk1_0,inv(esk1_0))!=e, inference(fof_nnf,[status(thm)],[inference(skolemize,[status(esa)],[inference(variable_rename,[status(thm)],[inference(fof_nnf,[status(thm)],[c_0_13])])])])).
cnf(c_0_16, plain, (inv(inv(X1))=X1), inference(rw,[status(thm)],[inference(spm,[status(thm)],[c_0_12, c_0_14]), c_0_14])).
cnf(c_0_17, negated_conjecture, (mul(esk1_0,inv(esk1_0))!=e), inference(split_conjunct,[status(thm)],[c_0_15])).
cnf(c_0_18, plain, (mul(X1,inv(X1))=e), inference(spm,[status(thm)],[c_0_8, c_0_16])).
cnf(c_0_19, negated_conjecture, ($false), inference(cn,[status(thm)],[inference(rw,[status(thm)],[c_0_17, c_0_18])]), ['proof']).
% SZS output end CNFRefutation
'''
RIGHT_INV = parse('![X]: mul(X,inv(X)) = e')


def _ready():
    try:
        W.environment()
        return sandbox.available()
    except Exception:
        return False


READY = _ready()


def _eprover():
    try:
        tool('eprover')
        return True
    except ToolUnavailable:
        return False


class ProofObjects(unittest.TestCase):
    def test_tstp_parse(self):
        steps = F.tstp_steps(RIGHT_INV_PROOF)
        self.assertEqual(len(steps), 20)          # 4 inputs and 16 inferences
        by = {s['name']: s for s in steps}
        self.assertEqual(by['c_0_10']['parents'], ['c_0_7', 'c_0_8', 'c_0_9'])
        self.assertEqual(by['c_0_13']['parents'], ['goal'])
        self.assertEqual(by['c_0_19']['formula'], ('const', False))
        self.assertTrue(by['ax0']['input'])

    def test_statement_is_generated_from_the_problem(self):
        mod, spec, _ = F.statement_module('t', GROUP, RIGHT_INV)
        self.assertTrue(mod['trusted'])
        self.assertIn('[Nonempty U]', mod['source'])
        self.assertIn('∀ v_X : U, ((s_mul v_X (s_inv v_X)) = s_e)', mod['source'])
        pm, reason, _ = F.proof_module('t', GROUP, RIGHT_INV, RIGHT_INV_PROOF)
        self.assertIsNone(reason)
        self.assertFalse(pm['trusted'])
        self.assertIsNone(checker.prescreen(pm['source'], permitted={mod['name']}))

    def test_unsupported_shapes_are_reported(self):
        no_end = RIGHT_INV_PROOF.replace("($false)", "(mul(e,e)=e)")
        self.assertIsNone(F.proof_module('t', GROUP, RIGHT_INV, no_end)[0])
        self.assertIn('skolem functions', F.proof_module('t', GROUP, RIGHT_INV, RIGHT_INV_PROOF.replace(
            'esk1_0', 'esk1_1(esk9_0)'))[1])

    def test_ground_hints_find_the_superposition_instance(self):
        # c_0_16: inv(inv(X)) = X from mul(inv(inv(X1)),X2) = mul(X1,X2) and mul(X1,e) = X1
        h0 = F._shape(parse('mul(inv(inv(X1)),X2) = mul(X1,X2)'), 'cnf')
        h1 = F._shape(parse('mul(X1,e) = X1'), 'cnf')
        concl = F._shape(parse('inv(inv(X1)) = X1'), 'cnf')
        hints = F.ground_hints([h0, h1], concl, [('fn', 'e', ())])
        self.assertTrue(hints)
        self.assertIsNone(F.ground_hints([h1], concl, [('fn', 'e', ())]))      # not derivable from h1 alone

    def test_congruence_closure(self):
        a, b, c = (('fn', x, ()) for x in 'abc')
        f = lambda x: ('fn', 'f', (x,))
        self.assertTrue(F._unsat([[(True, a, b)], [(False, f(a), f(b))]]))
        self.assertFalse(F._unsat([[(True, a, b)], [(False, f(a), f(c))]]))
        self.assertTrue(F._unsat([[(True, a, b), (True, a, c)], [(False, f(a), f(b))], [(False, a, c)]]))


@unittest.skipUnless(READY, 'formal workspace or sandbox unavailable')
class LeanReplay(unittest.TestCase):
    def test_replay_checks_a_real_proof_object(self):
        rec = F.replay('t-right-inv', GROUP, RIGHT_INV, RIGHT_INV_PROOF)
        self.assertEqual(rec['status'], 'THEOREM_CHECKED', rec)
        self.assertTrue(set(rec['axioms'] or []) <= {'propext', 'Classical.choice', 'Quot.sound'})

    def test_a_proof_cannot_be_bound_to_another_goal(self):
        other = parse('![X,Y]: mul(X,Y) = mul(Y,X)')
        self.assertEqual(F.replay('t-wrong-goal', GROUP, other, RIGHT_INV_PROOF)['status'], 'NOT_REPLAYED')

    def test_a_tampered_step_is_rejected(self):
        bad = RIGHT_INV_PROOF.replace('cnf(c_0_16, plain, (inv(inv(X1))=X1)', 'cnf(c_0_16, plain, (inv(X1)=X1)')
        self.assertEqual(F.replay('t-tampered', GROUP, RIGHT_INV, bad)['status'], 'NOT_REPLAYED')

    def test_translation_agrees_with_the_independent_evaluator(self):
        items, src = G.translation_checks(7, per_statement=1)
        rc = checker.accept([{'name': 'GCTruthT', 'source': src.replace('GCTruth', 'GCTruthT'), 'trusted': True}], [])
        self.assertEqual(rc['modules'][0]['result'], 'COMPILED')
        f, m, expected = items[0]
        wrong = F.truth_table_module('GCWrong', [(f, m, not expected)])
        rc = checker.accept([{'name': 'GCWrong', 'source': wrong, 'trusted': True}], [])
        self.assertNotEqual(rc['modules'][0]['result'], 'COMPILED')        # the check has teeth

    @unittest.skipUnless(_eprover(), 'E prover unavailable')
    def test_lemma_chain_replay(self):
        from genesis.verification.eprover import prove
        lem = [parse(G.STATEMENTS['right_inv']), parse(G.STATEMENTS['inv_inv'])]
        goal = parse(G.STATEMENTS['inv_mul'])
        lp = [(l, prove(GROUP, l, seconds=5)['proof']) for l in lem]
        g = prove(GROUP + lem, goal, seconds=5)
        rec = F.replay('t-chain', GROUP, goal, g['proof'], lemmas=lp)
        self.assertEqual(rec['status'], 'THEOREM_CHECKED', rec)
        self.assertEqual(rec['lemmas_replayed'], 2)


def _cadical():
    try:
        tool('cadical')
        return True
    except ToolUnavailable:
        return False


@unittest.skipUnless(_cadical(), 'CaDiCaL unavailable')
class ModelFinderBudget(unittest.TestCase):
    def test_one_second_budget_reaches_beyond_size_one(self):
        """Regression (B19 run 1): a total budget of one second used to stop after size 1."""
        from genesis.modelfind import find_model
        ax = [parse(a) for a in G.THEORIES['ring']]
        model, rec = find_model(ax + [('not', parse(G.STATEMENTS['neg_self']))], max_size=6, seconds=1,
                                total_seconds=1.0)
        self.assertEqual(rec['status'], 'MODEL_FOUND')
        self.assertEqual(rec['size'], 3)


class DecisionRule(unittest.TestCase):
    def rows(self, settled):
        """settled: {arm: number of problems settled out of 20}"""
        rows = []
        for arm in G.PLAN['arms']:
            for i in range(20):
                rows.append({'problem': f'p{i}', 'arm': arm, 'budget': 8.0, 'cpu_s': 1.0, 'log': [],
                             'status': 'PROVED' if i < settled[arm] else 'UNSETTLED'})
        return rows

    def problems(self):
        return [{'problem_id': f'p{i}', 'theory': 'group', 'goal': 'comm'} for i in range(20)]

    def decide(self, settled, labels=None):
        plan = dict(G.PLAN, budgets_cpu_s=[8.0])
        labels = labels or {('group', 'comm'): {'label': 'UNKNOWN'}}
        return G.summarize(plan, self.problems(), self.rows(settled), labels)

    def test_decisions(self):
        base = {'portfolio_auto': 10, 'portfolio': 12, 'lemmas_unfiltered': 11}
        s = self.decide(dict(base, ghost_lemmas=12, ghost_lemmas_lean=12, oracle_lemmas=12))
        self.assertEqual(s['decision'], 'RETIRE_NO_HEADROOM')
        s = self.decide(dict(base, ghost_lemmas=12, ghost_lemmas_lean=12, oracle_lemmas=16))
        self.assertEqual(s['decision'], 'RETIRE_MECHANISM_GAP')
        s = self.decide(dict(base, ghost_lemmas=14, ghost_lemmas_lean=12, oracle_lemmas=16))
        self.assertEqual(s['decision'], 'PLAUSIBLE_BENEFIT')
        self.assertEqual(s['margin'], 1)

    def test_label_contradiction_is_a_harness_error(self):
        base = {a: 12 for a in G.PLAN['arms']}
        s = self.decide(base, labels={('group', 'comm'): {'label': 'FALSE'}})
        self.assertEqual(s['decision'], 'HARNESS_ERROR')

    def test_family_is_deterministic_and_in_vocabulary(self):
        labels = {(th, n): {'label': 'UNKNOWN'} for th, ns in G.pools().items() for n in ns}
        a, b = G.family(labels, 5), G.family(labels, 5)
        self.assertEqual(a, b)
        for p in a:
            self.assertNotIn(p['goal'], p['lemmas'])
            self.assertTrue(set(p['lemmas']) <= set(G.pools()[p['theory']]))


@unittest.skipUnless((EVIDENCE / 'summary.json').exists(), 'B19 Ghost Census evidence not generated')
class Evidence(unittest.TestCase):
    def test_recorded_diagnostic(self):
        s = json.loads((EVIDENCE / 'summary.json').read_text())
        plan = json.loads((EVIDENCE / 'plan.json').read_text())
        self.assertEqual(s['plan_sha256'], plan['plan_sha256'])
        self.assertIn(s['decision'], ('RETIRE_NO_HEADROOM', 'RETIRE_MECHANISM_GAP', 'PLAUSIBLE_BENEFIT'))
        self.assertEqual(s['contradictions'], [])
        v = json.loads((EVIDENCE / 'validation.json').read_text())
        self.assertEqual(v['translation']['lean_module'], 'COMPILED')
        self.assertEqual(v['parser_round_trip_failures'], [])
        rows = json.loads((EVIDENCE / 'rows.json').read_text())
        replays = json.loads((EVIDENCE / 'replays.json').read_text())['replays']
        for r in rows:
            if r['status'] == 'PROVED':
                self.assertEqual(r['replay'], replays[r['replay_key']]['status'])


if __name__ == '__main__':
    unittest.main()
